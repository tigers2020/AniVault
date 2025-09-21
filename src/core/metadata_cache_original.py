"""Metadata caching system for AniVault application.

This module provides an in-memory cache system for storing and retrieving
anime metadata (ParsedAnimeInfo and TMDBAnime) with LRU eviction policy,
statistics tracking, and thread-safe operations.
"""

from __future__ import annotations

import heapq
import logging
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from .cache_key_generator import get_cache_key_generator
from .cache_metrics_exporter import update_cache_metrics, update_cache_size, update_memory_usage
from .cache_tracker import CacheMetrics, get_cache_tracker
from .compression import compression_manager
from .smart_cache_matcher import smart_cache_matcher
from .database import DatabaseManager
from .database_health import HealthStatus, get_database_health_status
from .incremental_sync import IncrementalSyncManager
from .logging_utils import log_operation_error
from .models import ParsedAnimeInfo, TMDBAnime
from .sync_monitoring import SyncOperationStatus, SyncOperationType, sync_monitor
from .transaction_manager import transactional

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    cache_size: int = 0
    memory_usage_bytes: int = 0
    expirations: int = 0  # Number of entries expired due to TTL (legacy)
    ttl_expirations: int = 0  # Number of entries expired due to TTL
    ttl_hits: int = 0  # Number of hits on non-expired entries
    ttl_misses: int = 0  # Number of misses due to TTL expiration

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.misses / self.total_requests) * 100

    @property
    def ttl_hit_rate(self) -> float:
        """Calculate TTL hit rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.ttl_hits / self.total_requests) * 100

    @property
    def ttl_miss_rate(self) -> float:
        """Calculate TTL miss rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.ttl_misses / self.total_requests) * 100

    @property
    def expiration_rate(self) -> float:
        """Calculate TTL expiration rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.ttl_expirations / self.total_requests) * 100

    def reset(self) -> None:
        """Reset all statistics to zero."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_requests = 0
        self.cache_size = 0
        self.memory_usage_bytes = 0
        self.expirations = 0
        self.ttl_expirations = 0
        self.ttl_hits = 0
        self.ttl_misses = 0


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata."""

    key: str
    value: ParsedAnimeInfo | TMDBAnime
    created_at: float
    last_accessed: float
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: int | None = None  # Per-entry TTL
    expires_at: float | None = None  # Calculated expiration timestamp

    def update_access(self) -> None:
        """Update access statistics."""
        self.last_accessed = time.time()
        self.access_count += 1

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() > self.expires_at if self.expires_at else False

    def get_remaining_ttl(self) -> int:
        """Get the remaining time-to-live for the entry in seconds."""
        if self.expires_at is None:
            return -1  # Indicates no expiration
        remaining = self.expires_at - time.time()
        return max(0, int(remaining))


class MetadataCache:
    """Thread-safe in-memory cache for anime metadata with LRU eviction policy.

    This cache provides fast access to frequently used metadata while
    managing memory usage through configurable size limits and LRU eviction.
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        ttl_seconds: int | None = None,
        db_manager: DatabaseManager | None = None,
        enable_db: bool = True,
    ) -> None:
        """Initialize the metadata cache with optional database integration.

        Args:
            max_size: Maximum number of entries in the cache
            max_memory_mb: Maximum memory usage in megabytes
            ttl_seconds: Time-to-live for cache entries (None for no expiration)
            db_manager: Database manager for persistence (optional)
            enable_db: Whether to enable database persistence
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.ttl_seconds = ttl_seconds
        self.db_manager = db_manager
        self.enable_db = enable_db and db_manager is not None

        # Thread-safe cache storage using OrderedDict for LRU behavior
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # Initialize cache key generator
        self._key_generator = get_cache_key_generator()

        # Initialize optimized cache tracker
        self._cache_tracker = get_cache_tracker("metadata_cache")

        # Legacy statistics tracking (for backward compatibility)
        self._stats = CacheStats()

        # Memory usage tracking
        self._current_memory_bytes = 0

        # Cache configuration
        self._enabled = True
        self._auto_cleanup = True
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

        # Cache-only mode for database failures
        self._cache_only_mode = False
        self._cache_only_reason = ""

        # Incremental synchronization
        self._incremental_sync_enabled = True
        self._incremental_sync_manager = None
        if self.enable_db and self.db_manager:
            self._incremental_sync_manager = IncrementalSyncManager(self.db_manager, self)

        # TTL optimization: Min-heap for efficient expiry tracking
        self._expiry_heap: list[tuple[float, str]] = []  # (expiry_timestamp, key)
        self._heap_lock = threading.Lock()  # Separate lock for heap operations

        # Background cleanup configuration
        self._background_cleanup_enabled = True
        self._cleanup_executor: ThreadPoolExecutor | None = None
        self._cleanup_timer: threading.Timer | None = None
        self._cleanup_batch_size = 100  # Maximum items to clean per batch
        self._cleanup_delay = 0.001  # Delay between cleanup batches (1ms)

    def get(
        self, key: str, default: ParsedAnimeInfo | TMDBAnime | None = None
    ) -> ParsedAnimeInfo | TMDBAnime | None:
        """Retrieve a value from the cache with read-through to database.

        Args:
            key: Cache key
            default: Default value to return if key not found

        Returns:
            Cached value or default if not found
        """
        if not self._enabled:
            return default

        with self._lock:
            self._stats.total_requests += 1

            # Check if key exists in cache
            if key not in self._cache:
                self._stats.misses += 1
                self._cache_tracker.track_miss()  # Optimized tracking
                logger.debug(f"Cache miss for key: {key}")

                # Log cache miss
                sync_monitor.log_cache_miss(key, SyncOperationType.READ_THROUGH)

                # Try to load from database (read-through) only if not in cache-only mode
                if not self._cache_only_mode and self.enable_db and self.db_manager:
                    db_value = self._load_from_database(key)
                    if db_value is not None:
                        # Store in cache for future use
                        self._store_in_cache(key, db_value)
                        self._stats.hits += 1
                        self._cache_tracker.track_hit()  # Optimized tracking
                        logger.debug(f"Read-through successful for key: {key}")
                        return db_value
                    else:
                        logger.debug(f"Database miss for key: {key}")
                elif self._cache_only_mode:
                    logger.debug(f"Cache-only mode: skipping database read for key: {key}")

                return default

            entry = self._cache[key]

            # Check TTL expiration using the new per-entry TTL logic (lazy deletion)
            if entry.is_expired():
                logger.debug(f"Cache entry expired for key: {key}")
                self._remove_entry(key)
                self._stats.misses += 1
                self._stats.ttl_expirations += 1
                self._stats.ttl_misses += 1
                self._cache_tracker.track_miss()  # Optimized tracking

                # Log cache miss due to expiration
                sync_monitor.log_cache_miss(key, SyncOperationType.READ_THROUGH)

                # Try to reload from database only if not in cache-only mode
                if not self._cache_only_mode and self.enable_db and self.db_manager:
                    db_value = self._load_from_database(key)
                    if db_value is not None:
                        self._store_in_cache(key, db_value)
                        self._stats.hits += 1
                        self._cache_tracker.track_hit()  # Optimized tracking
                        logger.debug(f"Read-through after expiration successful for key: {key}")
                        return db_value
                    else:
                        logger.debug(f"Database miss after expiration for key: {key}")
                elif self._cache_only_mode:
                    logger.debug(
                        f"Cache-only mode: skipping database reload for expired key: {key}"
                    )

                return default

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.update_access()

            self._stats.hits += 1
            self._stats.ttl_hits += 1
            self._cache_tracker.track_hit()  # Optimized tracking
            self._stats.cache_size = len(self._cache)
            logger.debug(f"Cache hit for key: {key}")

            # Log cache hit
            sync_monitor.log_cache_hit(key, SyncOperationType.READ_THROUGH)

            # Decompress value if it was compressed
            decompressed_value = self._decompress_if_needed(entry.value)
            return decompressed_value

    def get_smart(
        self, 
        key: str, 
        default: ParsedAnimeInfo | TMDBAnime | None = None,
        enable_smart_matching: bool = True
    ) -> ParsedAnimeInfo | TMDBAnime | None:
        """Retrieve a value from the cache with smart matching capabilities.

        This method first attempts a direct cache lookup. If that fails and
        smart matching is enabled, it will search for similar cache keys
        using fuzzy matching and phonetic algorithms.

        Args:
            key: Cache key
            default: Default value to return if key not found
            enable_smart_matching: Whether to enable smart matching for similar queries

        Returns:
            Cached value, similar cached value, or default if not found
        """
        if not self._enabled:
            return default

        with self._lock:
            self._stats.total_requests += 1

            # First, try direct cache lookup
            if key in self._cache:
                entry = self._cache[key]
                
                # Check TTL expiration
                if entry.is_expired():
                    logger.debug(f"Cache entry expired for key: {key}")
                    self._remove_entry(key)
                    self._stats.misses += 1
                    self._stats.ttl_expirations += 1
                    self._stats.ttl_misses += 1
                    self._cache_tracker.track_miss()
                else:
                    # Move to end (most recently used)
                    self._cache.move_to_end(key)
                    entry.update_access()
                    
                    self._stats.hits += 1
                    self._stats.ttl_hits += 1
                    self._cache_tracker.track_hit()
                    self._stats.cache_size = len(self._cache)
                    logger.debug(f"Cache hit for key: {key}")
                    
                    # Log cache hit
                    sync_monitor.log_cache_hit(key, SyncOperationType.READ_THROUGH)
                    
                    # Decompress value if it was compressed
                    decompressed_value = self._decompress_if_needed(entry.value)
                    return decompressed_value

            # If direct lookup failed and smart matching is enabled
            if enable_smart_matching and smart_cache_matcher.should_use_smart_matching(key):
                logger.debug(f"Attempting smart matching for key: {key}")
                
                # Get all existing cache keys
                existing_keys = list(self._cache.keys())
                
                # Find similar keys using the enhanced key generator
                similar_keys = self._key_generator.find_similar_cache_keys(
                    key, existing_keys
                )
                
                if similar_keys:
                    # Use the best match (highest similarity score)
                    best_match_key, similarity_score = similar_keys[0]
                    logger.debug(f"Found similar key: {best_match_key} (score: {similarity_score})")
                    
                    # Get the value from the similar key
                    if best_match_key in self._cache:
                        entry = self._cache[best_match_key]
                        
                        # Check TTL expiration for the similar key
                        if entry.is_expired():
                            logger.debug(f"Similar cache entry expired for key: {best_match_key}")
                            self._remove_entry(best_match_key)
                            self._stats.misses += 1
                            self._stats.ttl_expirations += 1
                            self._stats.ttl_misses += 1
                            self._cache_tracker.track_miss()
                        else:
                            # Move to end (most recently used)
                            self._cache.move_to_end(best_match_key)
                            entry.update_access()
                            
                            self._stats.hits += 1
                            self._stats.ttl_hits += 1
                            self._cache_tracker.track_hit()
                            self._stats.cache_size = len(self._cache)
                            logger.debug(f"Smart cache hit for key: {key} -> {best_match_key}")
                            
                            # Log smart cache hit
                            sync_monitor.log_cache_hit(key, SyncOperationType.READ_THROUGH)
                            
                            # Decompress value if it was compressed
                            decompressed_value = self._decompress_if_needed(entry.value)
                            return decompressed_value

            # If smart matching also failed, try database read-through
            self._stats.misses += 1
            self._cache_tracker.track_miss()
            logger.debug(f"Cache miss for key: {key}")

            # Log cache miss
            sync_monitor.log_cache_miss(key, SyncOperationType.READ_THROUGH)

            # Try to load from database (read-through) only if not in cache-only mode
            if not self._cache_only_mode and self.enable_db and self.db_manager:
                db_value = self._load_from_database(key)
                if db_value is not None:
                    # Store in cache for future use
                    self._store_in_cache(key, db_value)
                    self._stats.hits += 1
                    self._cache_tracker.track_hit()
                    logger.debug(f"Read-through successful for key: {key}")
                    return db_value
                else:
                    logger.debug(f"Database miss for key: {key}")
            elif self._cache_only_mode:
                logger.debug(f"Cache-only mode: skipping database read for key: {key}")

            return default

    @transactional
    def put(
        self, 
        key: str, 
        value: ParsedAnimeInfo | TMDBAnime, 
        session: Session | None = None,
        ttl_seconds: int | None = None
    ) -> None:
        """Store a value in the cache with write-through to database.

        This method implements the write-through pattern by updating both
        the cache and database within a transactional context. Large objects
        are automatically compressed to reduce memory usage.

        Args:
            key: Cache key
            value: Value to cache
            session: Database session (automatically provided by decorator)
            ttl_seconds: Per-entry TTL override (None to use global TTL)
        """
        if not self._enabled:
            return

        # Monitor the write-through operation
        with sync_monitor.monitor_operation(
            SyncOperationType.WRITE_THROUGH,
            cache_hit=False,
            key=key,
            value_type=type(value).__name__,
        ) as metrics:
            with self._lock:
                # Store in database first (write-through) with transactional context
                # Skip database write if in cache-only mode
                if not self._cache_only_mode and self.enable_db and self.db_manager:
                    try:
                        self._store_in_database(key, value)
                        logger.debug(f"Stored {type(value).__name__} in database: {key}")
                    except Exception as e:
                        log_operation_error("store in database", e)
                        metrics.complete(
                            SyncOperationStatus.FAILED,
                            error_message=str(e),
                            additional_context={"key_type": key.split(":")[0]},
                        )
                        # Continue with cache storage even if DB fails
                        # This maintains backward compatibility
                elif self._cache_only_mode:
                    logger.debug(f"Cache-only mode: skipping database write for key: {key}")

                # Update cache after successful database write (or in cache-only mode)
                self._store_in_cache(key, value, ttl_seconds)
                
                # Store additional similarity keys for smart matching
                self._store_similarity_keys(key, value, ttl_seconds)

                # Update metrics with success
                metrics.complete(
                    SyncOperationStatus.SUCCESS,
                    affected_records=1,
                    additional_context={
                        "key_type": key.split(":")[0],
                        "cache_only_mode": self._cache_only_mode,
                    },
                )

                # Perform cleanup if needed
                if self._auto_cleanup and self._should_cleanup():
                    self._cleanup_expired_entries()

    @transactional
    def delete(self, key: str, session: Session | None = None) -> bool:
        """Remove a value from the cache and database.

        This method implements the write-through pattern by removing data
        from both cache and database within a transactional context.

        Args:
            key: Cache key to remove
            session: Database session (automatically provided by decorator)

        Returns:
            True if key was found and removed, False otherwise
        """
        with self._lock:
            # Remove from database first
            if self.enable_db and self.db_manager:
                try:
                    self._delete_from_database(key)
                    logger.debug(f"Deleted from database: {key}")
                except Exception as e:
                    log_operation_error("delete from database", e)
                    # Continue with cache deletion even if DB fails

            # Remove from cache
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()
            self._current_memory_bytes = 0
            self._stats.cache_size = 0
            self._stats.memory_usage_bytes = 0

    def invalidate_pattern(self, pattern: str) -> int:
        """Remove all entries matching a pattern.

        Args:
            pattern: Pattern to match (supports wildcards)

        Returns:
            Number of entries removed
        """
        import fnmatch

        with self._lock:
            keys_to_remove = [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]

            for key in keys_to_remove:
                self._remove_entry(key)

            return len(keys_to_remove)

    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        with self._lock:
            # Get optimized metrics from tracker
            optimized_metrics = self._cache_tracker.get_metrics()

            # Update current stats with optimized data
            self._stats.cache_size = len(self._cache)
            self._stats.memory_usage_bytes = self._current_memory_bytes

            # Use optimized metrics if available, fall back to legacy stats
            hits = optimized_metrics.hits if optimized_metrics.hits > 0 else self._stats.hits
            misses = (
                optimized_metrics.misses if optimized_metrics.misses > 0 else self._stats.misses
            )
            total_requests = (
                optimized_metrics.total_requests
                if optimized_metrics.total_requests > 0
                else self._stats.total_requests
            )
            evictions = (
                optimized_metrics.evictions
                if optimized_metrics.evictions > 0
                else self._stats.evictions
            )

            # Update Prometheus metrics
            hit_rate = (hits / max(total_requests, 1)) * 100
            sync_monitor.update_cache_metrics(
                hit_rate=hit_rate,
                size=self._stats.cache_size,
                memory_bytes=self._stats.memory_usage_bytes,
            )

            # Update optimized Prometheus metrics
            optimized_metrics = CacheMetrics(
                hits=hits,
                misses=misses,
                evictions=evictions,
                total_requests=total_requests,
                last_updated=time.time(),
            )
            update_cache_metrics("metadata_cache", optimized_metrics)
            update_cache_size("metadata_cache", self._stats.cache_size)
            update_memory_usage("metadata_cache", self._stats.memory_usage_bytes)

            return CacheStats(
                hits=hits,
                misses=misses,
                evictions=evictions,
                total_requests=total_requests,
                cache_size=self._stats.cache_size,
                memory_usage_bytes=self._stats.memory_usage_bytes,
                ttl_expirations=self._stats.ttl_expirations,
                ttl_hits=self._stats.ttl_hits,
                ttl_misses=self._stats.ttl_misses,
            )

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self._stats.reset()
            self._cache_tracker.reset_metrics()  # Reset optimized tracking

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in megabytes."""
        with self._lock:
            return self._current_memory_bytes / (1024 * 1024)

    def is_enabled(self) -> bool:
        """Check if cache is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable the cache."""
        self._enabled = True

    def disable(self) -> None:
        """Disable the cache."""
        self._enabled = False

    def set_max_size(self, max_size: int) -> None:
        """Set maximum cache size."""
        with self._lock:
            self.max_size = max_size
            self._ensure_capacity(0)  # Evict if necessary

    def set_max_memory_mb(self, max_memory_mb: int) -> None:
        """Set maximum memory usage in megabytes."""
        with self._lock:
            self.max_memory_bytes = max_memory_mb * 1024 * 1024
            self._ensure_capacity(0)  # Evict if necessary

    def enable_cache_only_mode(self, reason: str = "Database unavailable") -> None:
        """Enable cache-only mode when database is unavailable.

        Args:
            reason: Reason for entering cache-only mode
        """
        with self._lock:
            self._cache_only_mode = True
            self._cache_only_reason = reason
            logger.warning(f"Cache-only mode enabled: {reason}")
            
            # Start background cleanup when entering cache-only mode
            if self._background_cleanup_enabled and self._cleanup_executor is None:
                self.start_background_cleanup()

    def disable_cache_only_mode(self) -> None:
        """Disable cache-only mode and return to normal operation."""
        with self._lock:
            self._cache_only_mode = False
            self._cache_only_reason = ""
            logger.info("Cache-only mode disabled, returning to normal operation")
            
            # Continue background cleanup even in normal mode for TTL management
            if self._background_cleanup_enabled and self._cleanup_executor is None:
                self.start_background_cleanup()

    def __del__(self) -> None:
        """Cleanup resources when the cache is destroyed."""
        try:
            self.stop_background_cleanup()
        except Exception:
            # Ignore errors during cleanup
            pass

    def is_cache_only_mode(self) -> bool:
        """Check if cache is operating in cache-only mode.

        Returns:
            True if in cache-only mode, False otherwise
        """
        return self._cache_only_mode

    def get_cache_only_reason(self) -> str:
        """Get the reason for cache-only mode.

        Returns:
            Reason string for cache-only mode
        """
        return self._cache_only_reason

    def enable_auto_cache_only_mode(self) -> None:
        """Enable automatic cache-only mode based on database health status."""

        def health_status_callback(old_status: HealthStatus, new_status: HealthStatus) -> None:
            """Callback for database health status changes."""
            if new_status == HealthStatus.UNHEALTHY:
                self.enable_cache_only_mode(f"Database unhealthy: {new_status.value}")
            elif new_status == HealthStatus.HEALTHY and self.is_cache_only_mode():
                self.disable_cache_only_mode()

        # Get the global health checker and register callback
        from .database_health import get_database_health_checker

        health_checker = get_database_health_checker()
        if health_checker:
            health_checker.add_status_change_callback(health_status_callback)
            logger.info("Enabled automatic cache-only mode based on database health")
        else:
            logger.warning("No database health checker available for auto cache-only mode")

    def check_database_health_and_adapt(self) -> None:
        """Check current database health and adapt cache mode accordingly."""
        current_status = get_database_health_status()

        if current_status == HealthStatus.UNHEALTHY and not self.is_cache_only_mode():
            self.enable_cache_only_mode(f"Database unhealthy: {current_status.value}")
        elif current_status == HealthStatus.HEALTHY and self.is_cache_only_mode():
            self.disable_cache_only_mode()

    def get_entries_info(self) -> list[dict[str, Any]]:
        """Get information about all cache entries.

        Returns:
            List of dictionaries with entry information
        """
        with self._lock:
            return [
                {
                    "key": entry.key,
                    "type": type(entry.value).__name__,
                    "created_at": entry.created_at,
                    "last_accessed": entry.last_accessed,
                    "access_count": entry.access_count,
                    "size_bytes": entry.size_bytes,
                    "age_seconds": time.time() - entry.created_at,
                }
                for entry in self._cache.values()
            ]

    def get_ttl_info(self) -> dict[str, Any]:
        """Get TTL information for all cache entries.

        Returns:
            Dictionary with TTL statistics and entry details
        """
        with self._lock:
            current_time = time.time()
            ttl_info = {
                "global_ttl_seconds": self.ttl_seconds,
                "total_entries": len(self._cache),
                "expired_entries": 0,
                "entries_with_ttl": 0,
                "entries_without_ttl": 0,
                "average_remaining_ttl": 0,
                "min_remaining_ttl": None,
                "max_remaining_ttl": None,
                "entry_details": []
            }
            
            remaining_ttls = []
            
            for key, entry in self._cache.items():
                is_expired = entry.is_expired(self.ttl_seconds)
                remaining_ttl = entry.get_remaining_ttl(self.ttl_seconds)
                
                if is_expired:
                    ttl_info["expired_entries"] += 1
                else:
                    if remaining_ttl is not None:
                        remaining_ttls.append(remaining_ttl)
                        ttl_info["entries_with_ttl"] += 1
                    else:
                        ttl_info["entries_without_ttl"] += 1
                
                ttl_info["entry_details"].append({
                    "key": key,
                    "is_expired": is_expired,
                    "remaining_ttl": remaining_ttl,
                    "per_entry_ttl": entry.ttl_seconds,
                    "age_seconds": current_time - entry.created_at,
                    "access_count": entry.access_count
                })
            
            if remaining_ttls:
                ttl_info["average_remaining_ttl"] = sum(remaining_ttls) / len(remaining_ttls)
                ttl_info["min_remaining_ttl"] = min(remaining_ttls)
                ttl_info["max_remaining_ttl"] = max(remaining_ttls)
            
            return ttl_info

    def set_ttl(self, key: str, ttl_seconds: int | None) -> bool:
        """Set TTL for a specific cache entry.

        Args:
            key: Cache key
            ttl_seconds: New TTL in seconds (None to remove TTL)

        Returns:
            True if entry was found and updated, False otherwise
        """
        with self._lock:
            if key in self._cache:
                self._cache[key].ttl_seconds = ttl_seconds
                logger.debug(f"Updated TTL for key {key}: {ttl_seconds} seconds")
                return True
            return False

    def get_remaining_ttl(self, key: str) -> int | None:
        """Get remaining TTL for a specific cache entry.

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds, or None if not found or no TTL set
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                return entry.get_remaining_ttl(self.ttl_seconds)
            return None

    def cleanup_expired_entries_manual(self) -> int:
        """Manually trigger cleanup of expired entries.

        Returns:
            Number of entries cleaned up
        """
        with self._lock:
            before_count = len(self._cache)
            self._cleanup_expired_entries()
            after_count = len(self._cache)
            cleaned_count = before_count - after_count
            
            if cleaned_count > 0:
                logger.info(f"Manually cleaned up {cleaned_count} expired cache entries")
            
            return cleaned_count

    def _remove_entry(self, key: str) -> None:
        """Remove an entry from the cache and expiry heap."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._current_memory_bytes -= entry.size_bytes
            
            # Remove from heap if it has an expiration time
            if entry.expires_at is not None:
                with self._heap_lock:
                    # Find and remove the entry from heap
                    # Note: This is O(n) but necessary for correctness
                    # In practice, this is acceptable as heap size is typically small
                    self._expiry_heap = [(exp_time, k) for exp_time, k in self._expiry_heap if k != key]
                    heapq.heapify(self._expiry_heap)  # Re-heapify after removal
            
            # Note: We don't remove from heap here as it would be O(n)
            # Stale heap entries are handled during cleanup by checking
            # if the entry still exists and has the same expiry timestamp

    def _remove_entry_from_cache_only(self, key: str) -> None:
        """Remove an entry from the cache only (without heap operations).
        
        This method is used during cleanup to avoid deadlocks.
        """
        if key in self._cache:
            entry = self._cache.pop(key)
            self._current_memory_bytes -= entry.size_bytes

    def _calculate_entry_size(self, key: str, value: ParsedAnimeInfo | TMDBAnime) -> int:
        """Calculate the memory size of a cache entry."""
        # Base size for key and entry metadata
        base_size = len(key.encode("utf-8")) + 100  # Approximate overhead

        # Calculate value size based on type
        if isinstance(value, ParsedAnimeInfo):
            value_size = self._calculate_parsed_info_size(value)
        else:  # isinstance(value, TMDBAnime)
            value_size = self._calculate_tmdb_anime_size(value)

        return base_size + value_size

    def _calculate_parsed_info_size(self, info: ParsedAnimeInfo) -> int:
        """Calculate memory size of ParsedAnimeInfo."""
        size = 0
        size += len(info.title.encode("utf-8")) if info.title else 0
        size += len(info.episode_title.encode("utf-8")) if info.episode_title else 0
        size += len(info.resolution.encode("utf-8")) if info.resolution else 0
        size += len(info.video_codec.encode("utf-8")) if info.video_codec else 0
        size += len(info.audio_codec.encode("utf-8")) if info.audio_codec else 0
        size += len(info.release_group.encode("utf-8")) if info.release_group else 0
        size += len(info.file_extension.encode("utf-8")) if info.file_extension else 0
        size += len(info.source.encode("utf-8")) if info.source else 0
        size += len(str(info.raw_data).encode("utf-8")) if info.raw_data else 0
        return size + 50  # Base object overhead

    def _calculate_tmdb_anime_size(self, anime: TMDBAnime) -> int:
        """Calculate memory size of TMDBAnime."""
        size = 0
        size += len(anime.title.encode("utf-8")) if anime.title else 0
        size += len(anime.original_title.encode("utf-8")) if anime.original_title else 0
        size += len(anime.korean_title.encode("utf-8")) if anime.korean_title else 0
        size += len(anime.overview.encode("utf-8")) if anime.overview else 0
        size += len(anime.poster_path.encode("utf-8")) if anime.poster_path else 0
        size += len(anime.backdrop_path.encode("utf-8")) if anime.backdrop_path else 0
        size += len(anime.status.encode("utf-8")) if anime.status else 0
        size += len(str(anime.genres).encode("utf-8")) if anime.genres else 0
        size += len(str(anime.networks).encode("utf-8")) if anime.networks else 0
        size += len(str(anime.raw_data).encode("utf-8")) if anime.raw_data else 0
        return size + 100  # Base object overhead

    def _ensure_capacity(self, new_entry_size: int) -> None:
        """Ensure cache has capacity for a new entry."""
        # Check size limit
        while len(self._cache) >= self.max_size:
            self._evict_lru()

        # Check memory limit
        while (
            self._current_memory_bytes + new_entry_size > self.max_memory_bytes
            and len(self._cache) > 0
        ):
            self._evict_lru()

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if self._cache:
            # Remove the first (oldest) entry
            _key, entry = self._cache.popitem(last=False)
            self._current_memory_bytes -= entry.size_bytes
            self._stats.evictions += 1
            self._cache_tracker.track_eviction()  # Optimized tracking

    def _should_cleanup(self) -> bool:
        """Check if cleanup should be performed."""
        return (time.time() - self._last_cleanup) > self._cleanup_interval

    def _cleanup_expired_entries(self) -> int:
        """Remove expired entries from the cache using optimized heap-based approach.
        
        This method now uses a min-heap to efficiently find expired entries
        instead of scanning the entire cache (O(log N) vs O(N)).
        """
        current_time = time.time()
        cleaned_count = 0
        expired_keys = []
        
        # First, collect expired keys from heap (without holding locks)
        with self._heap_lock:
            while self._expiry_heap and self._expiry_heap[0][0] <= current_time:
                expiry_timestamp, key = heapq.heappop(self._expiry_heap)
                expired_keys.append((expiry_timestamp, key))
        
        # Then, process expired keys with main lock
        with self._lock:
            for expiry_timestamp, key in expired_keys:
                if key in self._cache:
                    entry = self._cache[key]
                    # Verify this is the same entry (not updated with new TTL)
                    if entry.expires_at == expiry_timestamp:
                        # Entry is genuinely expired and hasn't been updated
                        self._remove_entry_from_cache_only(key)
                        cleaned_count += 1
                        self._stats.expirations += 1
                        self._stats.ttl_expirations += 1
                    # If expiry_timestamp doesn't match, the entry was updated
                    # and the new entry is already in the heap
                # If key not in cache, it was already removed by lazy deletion

        self._last_cleanup = current_time
        
        if cleaned_count > 0:
            logger.debug(f"Optimized cleanup removed {cleaned_count} expired cache entries")
        
        return cleaned_count

    def _background_cleanup_worker(self) -> None:
        """Background worker for periodic cache cleanup.
        
        This method runs in a separate thread to perform cleanup
        without blocking the main application.
        """
        try:
            cleaned_count = self._cleanup_expired_entries()
            
            # Log performance metrics
            if cleaned_count > 0:
                logger.debug(f"Background cleanup completed: {cleaned_count} entries removed")
                
        except Exception as e:
            logger.error(f"Error in background cleanup: {e}")
        finally:
            # Reschedule the next cleanup
            if self._background_cleanup_enabled:
                self._schedule_next_cleanup()

    def _schedule_next_cleanup(self) -> None:
        """Schedule the next background cleanup task."""
        if not self._background_cleanup_enabled:
            return
            
        try:
            self._cleanup_timer = threading.Timer(
                self._cleanup_interval, 
                self._background_cleanup_worker
            )
            self._cleanup_timer.daemon = True  # Allow program to exit
            self._cleanup_timer.start()
        except Exception as e:
            logger.error(f"Failed to schedule background cleanup: {e}")

    def start_background_cleanup(self) -> None:
        """Start the background cleanup process.
        
        This creates a dedicated thread pool executor for cleanup tasks
        and schedules the first cleanup.
        """
        if not self._background_cleanup_enabled:
            return
            
        try:
            # Create dedicated cleanup executor
            self._cleanup_executor = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="CacheCleanup"
            )
            
            # Schedule first cleanup
            self._schedule_next_cleanup()
            
            logger.info("Background cache cleanup started")
            
        except Exception as e:
            logger.error(f"Failed to start background cleanup: {e}")

    def stop_background_cleanup(self) -> None:
        """Stop the background cleanup process."""
        self._background_cleanup_enabled = False
        
        # Cancel pending timer
        if self._cleanup_timer and self._cleanup_timer.is_alive():
            self._cleanup_timer.cancel()
            self._cleanup_timer = None
        
        # Shutdown executor
        if self._cleanup_executor:
            self._cleanup_executor.shutdown(wait=True)
            self._cleanup_executor = None
            
        logger.info("Background cache cleanup stopped")

    def _batch_cleanup_expired_entries(self, max_items: int = None) -> int:
        """Perform batch cleanup of expired entries with throttling.
        
        Args:
            max_items: Maximum number of items to clean in this batch
            
        Returns:
            Number of items cleaned
        """
        if max_items is None:
            max_items = self._cleanup_batch_size
            
        current_time = time.time()
        cleaned_count = 0
        
        expired_keys = []
        
        # First, collect expired keys from heap (without holding locks)
        with self._heap_lock:
            while (self._expiry_heap and 
                   self._expiry_heap[0][0] <= current_time and 
                   len(expired_keys) < max_items):
                
                expiry_timestamp, key = heapq.heappop(self._expiry_heap)
                expired_keys.append((expiry_timestamp, key))
        
        # Then, process expired keys with main lock
        with self._lock:
            for expiry_timestamp, key in expired_keys:
                if key in self._cache:
                    entry = self._cache[key]
                    if entry.expires_at == expiry_timestamp:
                        self._remove_entry_from_cache_only(key)
                        cleaned_count += 1
                        self._stats.expirations += 1
                        self._stats.ttl_expirations += 1
                        
                # Small delay to prevent overwhelming the system (only for large batches)
                if cleaned_count > 0 and cleaned_count % 50 == 0 and len(expired_keys) > 100:
                    time.sleep(self._cleanup_delay)

        return cleaned_count

    def _store_in_database(self, key: str, value: ParsedAnimeInfo | TMDBAnime) -> None:
        """Store a value in the database based on key type within a transaction.

        This method implements the write-through pattern by persisting data
        to the database within a transactional context.

        Args:
            key: Cache key
            value: Value to store in database
        """
        if not self.enable_db or not self.db_manager:
            logger.debug(f"Database not enabled, cannot store key: {key}")
            return

        # Monitor the write-through operation
        with sync_monitor.monitor_operation(
            SyncOperationType.WRITE_THROUGH,
            cache_hit=False,
            key=key,
            value_type=type(value).__name__,
        ) as metrics:
            try:
                affected_records = 0

                if key.startswith("tmdb:") and isinstance(value, TMDBAnime):
                    # Store TMDB metadata
                    logger.debug(f"Storing TMDB metadata in database: {value.title}")
                    self.db_manager.create_anime_metadata(value)
                    affected_records = 1
                    logger.debug(f"Successfully stored TMDB metadata: {key}")

                elif key.startswith("file:") and isinstance(value, ParsedAnimeInfo):
                    # For file keys, we need additional file information
                    # This is a simplified version - in practice, you'd need file path info
                    logger.warning(f"Cannot store ParsedAnimeInfo without file context: {key}")

                else:
                    logger.warning(f"Unknown key type or value type: {key}, {type(value)}")

                # Update metrics with success information
                metrics.complete(
                    SyncOperationStatus.SUCCESS,
                    affected_records=affected_records,
                    additional_context={"key_type": key.split(":")[0]},
                )

            except Exception as e:
                logger.error(f"Failed to store in database for key {key}: {e}")
                metrics.complete(
                    SyncOperationStatus.FAILED,
                    error_message=str(e),
                    additional_context={"key_type": key.split(":")[0]},
                )
                raise

    @transactional
    def bulk_store_tmdb_metadata(self, session: Session, anime_list: list[TMDBAnime]) -> int:
        """Bulk store multiple TMDB anime metadata records using batch operations.

        Args:
            session: Database session (automatically provided by decorator)
            anime_list: List of TMDBAnime objects to store

        Returns:
            Number of records stored

        Raises:
            Exception: If bulk store fails
        """
        if not self.enable_db or not self.db_manager:
            logger.warning("Database not enabled, cannot bulk store metadata")
            return 0

        # Monitor the bulk insert operation
        with sync_monitor.monitor_operation(
            SyncOperationType.BULK_INSERT,
            cache_hit=False,
            record_count=len(anime_list),
            operation_subtype="tmdb_metadata",
        ) as metrics:
            try:
                # Log bulk operation start
                sync_monitor.log_bulk_operation_start(
                    SyncOperationType.BULK_INSERT,
                    len(anime_list),
                    operation_subtype="tmdb_metadata",
                )

                # Use bulk upsert for efficiency
                inserted_count, updated_count = self.db_manager.bulk_upsert_anime_metadata(
                    anime_list
                )
                total_stored = inserted_count + updated_count

                # Store in cache as well
                cache_hits = 0
                for anime in anime_list:
                    cache_key = self._key_generator.generate_tmdb_anime_key(anime.tmdb_id)
                    self._store_in_cache(cache_key, anime)
                    cache_hits += 1

                # Log bulk operation completion
                sync_monitor.log_bulk_operation_complete(
                    SyncOperationType.BULK_INSERT,
                    len(anime_list),
                    metrics.duration_ms or 0,
                    total_stored,
                    inserted_count=inserted_count,
                    updated_count=updated_count,
                    operation_subtype="tmdb_metadata",
                )

                logger.info(
                    f"Bulk stored {total_stored} TMDB metadata records ({inserted_count} inserted, {updated_count} updated)"
                )

                # Update metrics with results
                metrics.complete(
                    SyncOperationStatus.SUCCESS,
                    affected_records=total_stored,
                    additional_context={
                        "inserted_count": inserted_count,
                        "updated_count": updated_count,
                        "cache_entries_updated": cache_hits,
                    },
                )

                return total_stored

            except Exception as e:
                log_operation_error("bulk store TMDB metadata", e)
                metrics.complete(
                    SyncOperationStatus.FAILED,
                    error_message=str(e),
                    additional_context={"operation_subtype": "tmdb_metadata"},
                )
                raise

    @transactional
    def bulk_store_parsed_files(
        self,
        session: Session,
        file_data_list: list[
            tuple[str, str, int, datetime, datetime, ParsedAnimeInfo, str | None, int | None]
        ],
    ) -> int:
        """Bulk store multiple parsed file records using batch operations.

        Args:
            session: Database session (automatically provided by decorator)
            file_data_list: List of tuples containing (file_path, filename, file_size,
                          created_at, modified_at, parsed_info, file_hash, metadata_id)

        Returns:
            Number of records stored

        Raises:
            Exception: If bulk store fails
        """
        if not self.enable_db or not self.db_manager:
            logger.warning("Database not enabled, cannot bulk store files")
            return 0

        # Monitor the bulk insert operation
        with sync_monitor.monitor_operation(
            SyncOperationType.BULK_INSERT,
            cache_hit=False,
            record_count=len(file_data_list),
            operation_subtype="parsed_files",
        ) as metrics:
            try:
                # Log bulk operation start
                sync_monitor.log_bulk_operation_start(
                    SyncOperationType.BULK_INSERT,
                    len(file_data_list),
                    operation_subtype="parsed_files",
                )

                # Use bulk insert for efficiency
                inserted_count = self.db_manager.bulk_insert_parsed_files(file_data_list)

                # Store in cache as well
                cache_hits = 0
                for (
                    file_path,
                    _filename,
                    _file_size,
                    _created_at,
                    _modified_at,
                    parsed_info,
                    _file_hash,
                    _metadata_id,
                ) in file_data_list:
                    cache_key = self._key_generator.generate_file_key(file_path)
                    self._store_in_cache(cache_key, parsed_info)
                    cache_hits += 1

                # Log bulk operation completion
                sync_monitor.log_bulk_operation_complete(
                    SyncOperationType.BULK_INSERT,
                    len(file_data_list),
                    metrics.duration_ms or 0,
                    inserted_count,
                    operation_subtype="parsed_files",
                )

                logger.info(f"Bulk stored {inserted_count} parsed file records")

                # Update metrics with results
                metrics.complete(
                    SyncOperationStatus.SUCCESS,
                    affected_records=inserted_count,
                    additional_context={
                        "cache_entries_updated": cache_hits,
                        "operation_subtype": "parsed_files",
                    },
                )

                return inserted_count

            except Exception as e:
                log_operation_error("bulk store parsed files", e)
                metrics.complete(
                    SyncOperationStatus.FAILED,
                    error_message=str(e),
                    additional_context={"operation_subtype": "parsed_files"},
                )
                raise

    @transactional
    def bulk_update_tmdb_metadata(self, session: Session, updates: list[dict]) -> int:
        """Bulk update multiple TMDB anime metadata records using batch operations.

        Args:
            session: Database session (automatically provided by decorator)
            updates: List of dictionaries containing updates. Each dict must include
                    the primary key (tmdb_id) and fields to update.

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not self.enable_db or not self.db_manager:
            logger.warning("Database not enabled, cannot bulk update metadata")
            return 0

        try:
            # Update database
            updated_count = self.db_manager.bulk_update_anime_metadata(updates)

            # Update cache entries
            for update in updates:
                if "tmdb_id" in update:
                    cache_key = self._key_generator.generate_tmdb_anime_key(update["tmdb_id"])
                    # Remove from cache to force reload from database
                    if cache_key in self._cache:
                        self._remove_entry(cache_key)

            logger.info(f"Bulk updated {updated_count} TMDB metadata records")
            return updated_count

        except Exception as e:
            log_operation_error("bulk update TMDB metadata", e)
            raise

    @transactional
    def bulk_update_parsed_files(self, session: Session, updates: list[dict]) -> int:
        """Bulk update multiple parsed file records using batch operations.

        Args:
            session: Database session (automatically provided by decorator)
            updates: List of dictionaries containing updates. Each dict must include
                    the primary key (id) and fields to update.

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not self.enable_db or not self.db_manager:
            logger.warning("Database not enabled, cannot bulk update files")
            return 0

        try:
            # Update database
            updated_count = self.db_manager.bulk_update_parsed_files(updates)

            # Note: For parsed files, we can't easily update cache without file path info
            # The cache will be refreshed on next access via read-through

            logger.info(f"Bulk updated {updated_count} parsed file records")
            return updated_count

        except Exception as e:
            log_operation_error("bulk update parsed files", e)
            raise

    @transactional
    def bulk_update_tmdb_metadata_by_ids(
        self, session: Session, tmdb_ids: list[int], update_data: dict
    ) -> int:
        """Bulk update TMDB metadata records by TMDB IDs with the same update data.

        Args:
            session: Database session (automatically provided by decorator)
            tmdb_ids: List of TMDB IDs to update
            update_data: Dictionary of fields to update (excluding tmdb_id)

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not self.enable_db or not self.db_manager:
            logger.warning("Database not enabled, cannot bulk update metadata")
            return 0

        try:
            # Update database
            updated_count = self.db_manager.bulk_update_anime_metadata_by_tmdb_ids(
                tmdb_ids, update_data
            )

            # Remove updated entries from cache to force reload
            for tmdb_id in tmdb_ids:
                cache_key = self._key_generator.generate_tmdb_anime_key(tmdb_id)
                if cache_key in self._cache:
                    self._remove_entry(cache_key)

            logger.info(f"Bulk updated {updated_count} TMDB metadata records by IDs")
            return updated_count

        except Exception as e:
            log_operation_error("bulk update TMDB metadata by IDs", e)
            raise

    @transactional
    def bulk_update_parsed_files_by_paths(
        self, session: Session, file_paths: list[str], update_data: dict
    ) -> int:
        """Bulk update parsed file records by file paths with the same update data.

        Args:
            session: Database session (automatically provided by decorator)
            file_paths: List of file paths to update
            update_data: Dictionary of fields to update (excluding file_path)

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not self.enable_db or not self.db_manager:
            logger.warning("Database not enabled, cannot bulk update files")
            return 0

        try:
            # Update database
            updated_count = self.db_manager.bulk_update_parsed_files_by_paths(
                file_paths, update_data
            )

            # Remove updated entries from cache to force reload
            for file_path in file_paths:
                cache_key = self._key_generator.generate_file_key(file_path)
                if cache_key in self._cache:
                    self._remove_entry(cache_key)

            logger.info(f"Bulk updated {updated_count} parsed file records by paths")
            return updated_count

        except Exception as e:
            log_operation_error("bulk update parsed files by paths", e)
            raise

    def _load_from_database(self, key: str) -> ParsedAnimeInfo | TMDBAnime | None:
        """Load a value from the database based on key type.

        This method implements the read-through pattern by fetching data
        from the database when it's not found in the cache.

        Args:
            key: Cache key to load from database

        Returns:
            Loaded value from database or None if not found
        """
        if not self.enable_db or not self.db_manager:
            logger.debug(f"Database not enabled, cannot load key: {key}")
            return None

        # Monitor the read-through operation
        with sync_monitor.monitor_operation(
            SyncOperationType.READ_THROUGH, cache_hit=False, key=key
        ) as metrics:
            try:
                result = None
                affected_records = 0

                if key.startswith("tmdb:"):
                    # Extract TMDB ID from key
                    tmdb_id_str = key.replace("tmdb:", "")
                    try:
                        tmdb_id = int(tmdb_id_str)
                        logger.debug(f"Loading TMDB metadata from database: tmdb_id={tmdb_id}")
                        metadata = self.db_manager.get_anime_metadata(tmdb_id)
                        if metadata:
                            result = metadata.to_tmdb_anime()
                            affected_records = 1
                            logger.debug(f"Successfully loaded TMDB metadata: {result.title}")
                        else:
                            logger.debug(f"TMDB metadata not found in database: tmdb_id={tmdb_id}")
                    except ValueError as e:
                        logger.warning(f"Invalid TMDB ID in key: {key}, error: {e}")

                elif key.startswith("file:"):
                    # For file keys, we'd need to implement file loading
                    # This is a simplified version - in practice, you'd need file path info
                    logger.warning(f"Cannot load ParsedAnimeInfo without file context: {key}")
                else:
                    logger.warning(f"Unknown key type for database loading: {key}")

                # Update metrics with results
                metrics.complete(
                    SyncOperationStatus.SUCCESS,
                    affected_records=affected_records,
                    additional_context={"key_type": key.split(":")[0], "found": result is not None},
                )

                return result

            except Exception as e:
                logger.error(f"Failed to load from database for key {key}: {e}")
                metrics.complete(
                    SyncOperationStatus.FAILED,
                    error_message=str(e),
                    additional_context={"key_type": key.split(":")[0]},
                )
                return None

    def _delete_from_database(self, key: str) -> None:
        """Delete a value from the database based on key type within a transaction.

        This method implements the write-through pattern by removing data
        from the database within a transactional context.

        Args:
            key: Cache key to delete from database
        """
        if not self.enable_db or not self.db_manager:
            logger.debug(f"Database not enabled, cannot delete key: {key}")
            return

        # Monitor the delete operation
        with sync_monitor.monitor_operation(
            SyncOperationType.DELETE, cache_hit=False, key=key
        ) as metrics:
            try:
                affected_records = 0

                if key.startswith("file:"):
                    # Extract file path from key
                    file_path = key.replace("file:", "")
                    logger.debug(f"Deleting parsed file from database: {file_path}")
                    self.db_manager.delete_parsed_file(file_path)
                    affected_records = 1
                    logger.debug(f"Successfully deleted parsed file: {key}")

                elif key.startswith("tmdb:"):
                    # Extract TMDB ID from key and delete metadata
                    tmdb_id_str = key.replace("tmdb:", "")
                    try:
                        tmdb_id = int(tmdb_id_str)
                        logger.debug(f"Deleting TMDB metadata from database: tmdb_id={tmdb_id}")
                        self.db_manager.delete_anime_metadata(tmdb_id)
                        affected_records = 1
                        logger.debug(f"Successfully deleted TMDB metadata: {key}")
                    except ValueError as e:
                        logger.warning(f"Invalid TMDB ID in key: {key}, error: {e}")
                else:
                    logger.warning(f"Unknown key type for deletion: {key}")

                # Update metrics with success information
                metrics.complete(
                    SyncOperationStatus.SUCCESS,
                    affected_records=affected_records,
                    additional_context={"key_type": key.split(":")[0]},
                )

            except Exception as e:
                logger.error(f"Failed to delete from database for key {key}: {e}")
                metrics.complete(
                    SyncOperationStatus.FAILED,
                    error_message=str(e),
                    additional_context={"key_type": key.split(":")[0]},
                )
                raise

    # Incremental Synchronization Methods

    def enable_incremental_sync(self) -> None:
        """Enable incremental synchronization mode."""
        self._incremental_sync_enabled = True
        logger.info("Incremental synchronization enabled")

    def disable_incremental_sync(self) -> None:
        """Disable incremental synchronization mode."""
        self._incremental_sync_enabled = False
        logger.info("Incremental synchronization disabled")

    def is_incremental_sync_enabled(self) -> bool:
        """Check if incremental synchronization is enabled.

        Returns:
            True if incremental sync is enabled, False otherwise
        """
        return self._incremental_sync_enabled

    def get_incremental_sync_manager(self) -> IncrementalSyncManager | None:
        """Get the incremental sync manager instance.

        Returns:
            IncrementalSyncManager instance or None if not available
        """
        return self._incremental_sync_manager

    @transactional
    def sync_tmdb_metadata_incremental(
        self, session: Session | None = None, force_full_sync: bool = False
    ) -> None:
        """Perform incremental synchronization of TMDB metadata.

        Args:
            session: Database session (automatically provided by decorator)
            force_full_sync: If True, perform full sync regardless of last sync state

        Returns:
            IncrementalSyncResult with sync operation details
        """
        if not self._incremental_sync_enabled:
            logger.warning("Incremental sync is disabled, skipping TMDB metadata sync")
            return None

        if not self._incremental_sync_manager:
            logger.error("Incremental sync manager not available")
            return None

        logger.info(f"Starting incremental TMDB metadata sync (force_full={force_full_sync})")
        return self._incremental_sync_manager.sync_tmdb_metadata_incremental(
            session, force_full_sync
        )

    @transactional
    def sync_parsed_files_incremental(
        self, session: Session | None = None, force_full_sync: bool = False
    ) -> None:
        """Perform incremental synchronization of parsed files.

        Args:
            session: Database session (automatically provided by decorator)
            force_full_sync: If True, perform full sync regardless of last sync state

        Returns:
            IncrementalSyncResult with sync operation details
        """
        if not self._incremental_sync_enabled:
            logger.warning("Incremental sync is disabled, skipping parsed files sync")
            return None

        if not self._incremental_sync_manager:
            logger.error("Incremental sync manager not available")
            return None

        logger.info(f"Starting incremental parsed files sync (force_full={force_full_sync})")
        return self._incremental_sync_manager.sync_parsed_files_incremental(
            session, force_full_sync
        )

    @transactional
    def sync_all_entities_incremental(
        self, session: Session | None = None, force_full_sync: bool = False
    ) -> None:
        """Perform incremental synchronization of all entity types.

        Args:
            session: Database session (automatically provided by decorator)
            force_full_sync: If True, perform full sync regardless of last sync state

        Returns:
            Dictionary mapping entity types to their sync results
        """
        if not self._incremental_sync_enabled:
            logger.warning("Incremental sync is disabled, skipping all entities sync")
            return {}

        if not self._incremental_sync_manager:
            logger.error("Incremental sync manager not available")
            return {}

        logger.info(f"Starting incremental sync for all entities (force_full={force_full_sync})")
        return self._incremental_sync_manager.sync_all_entities_incremental(
            session, force_full_sync
        )

    def get_sync_status(self) -> dict:
        """Get the current sync status for all entity types.

        Returns:
            Dictionary mapping entity types to their current sync states
        """
        if not self._incremental_sync_manager:
            return {}

        return self._incremental_sync_manager.get_sync_status()

    def _store_in_cache(self, key: str, value: ParsedAnimeInfo | TMDBAnime, ttl_seconds: int | None = None) -> None:
        """Store a value in the cache without database operations.

        Large objects are automatically compressed to reduce memory usage.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Per-entry TTL override (None to use global TTL)
        """
        # Calculate entry size
        entry_size = self._calculate_entry_size(key, value)

        # Remove existing entry if it exists (including from heap)
        if key in self._cache:
            self._remove_entry(key)

        # Check if we need to evict entries
        self._ensure_capacity(entry_size)

        # Apply compression for large objects
        compressed_value = self._apply_compression_if_needed(value)
        actual_entry_size = self._calculate_entry_size(key, compressed_value)

        # Determine effective TTL and expiration
        effective_ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        now = time.time()
        
        # Handle zero or negative TTL as immediate expiration
        if effective_ttl is not None and effective_ttl <= 0:
            expires_at = now  # Immediate expiration
        else:
            expires_at = (now + effective_ttl) if effective_ttl is not None else None

        # Create new entry
        entry = CacheEntry(
            key=key,
            value=compressed_value,
            created_at=now,
            last_accessed=now,
            size_bytes=actual_entry_size,
            ttl_seconds=effective_ttl,  # Store the effective TTL
            expires_at=expires_at,  # Store the calculated expiration timestamp
        )

        # Add to cache
        self._cache[key] = entry
        self._current_memory_bytes += actual_entry_size

        # Add to expiry heap for efficient cleanup (only if TTL is set)
        if expires_at is not None:
            with self._heap_lock:
                heapq.heappush(self._expiry_heap, (expires_at, key))

        # Update statistics
        self._stats.cache_size = len(self._cache)
        self._stats.memory_usage_bytes = self._current_memory_bytes

        # Log compression if applied
        if compressed_value != value:
            compression_saved = entry_size - actual_entry_size
            logger.debug(
                f"Applied compression to cache entry {key}: "
                f"{entry_size} -> {actual_entry_size} bytes "
                f"({compression_saved} bytes saved)"
            )

    def _apply_compression_if_needed(
        self, value: ParsedAnimeInfo | TMDBAnime
    ) -> ParsedAnimeInfo | TMDBAnime:
        """Apply compression to large metadata objects if beneficial.

        Args:
            value: Metadata object to potentially compress

        Returns:
            Original value or compressed version if compression is beneficial
        """
        # Check if this object has large raw_data that would benefit from compression
        if isinstance(value, TMDBAnime) and value.raw_data:
            # Estimate size of raw_data
            raw_data_size = len(str(value.raw_data).encode("utf-8"))

            if raw_data_size >= compression_manager.min_size_threshold:
                try:
                    # Compress the raw_data
                    compressed_raw_data = compression_manager.compress_for_storage(value.raw_data)

                    # Create new TMDBAnime with compressed raw_data
                    compressed_value = TMDBAnime(
                        tmdb_id=value.tmdb_id,
                        title=value.title,
                        original_title=value.original_title,
                        korean_title=value.korean_title,
                        overview=value.overview,
                        release_date=value.release_date,
                        poster_path=value.poster_path,
                        backdrop_path=value.backdrop_path,
                        first_air_date=value.first_air_date,
                        last_air_date=value.last_air_date,
                        status=value.status,
                        vote_average=value.vote_average,
                        vote_count=value.vote_count,
                        popularity=value.popularity,
                        genres=value.genres,
                        networks=value.networks,
                        production_companies=value.production_companies,
                        production_countries=value.production_countries,
                        spoken_languages=value.spoken_languages,
                        number_of_seasons=value.number_of_seasons,
                        number_of_episodes=value.number_of_episodes,
                        tagline=value.tagline,
                        homepage=value.homepage,
                        imdb_id=value.imdb_id,
                        external_ids=value.external_ids,
                        quality_score=value.quality_score,
                        search_strategy=value.search_strategy,
                        fallback_round=value.fallback_round,
                        raw_data=(
                            compressed_raw_data if isinstance(compressed_raw_data, dict) else {}
                        ),  # Store compressed data
                    )

                    logger.debug(
                        f"Compressed TMDBAnime raw_data: {raw_data_size} -> {len(compressed_raw_data)} bytes"
                    )
                    return compressed_value

                except Exception as e:
                    logger.warning(f"Failed to compress TMDBAnime raw_data: {e}")
                    return value

        elif isinstance(value, ParsedAnimeInfo) and value.raw_data:
            # Similar compression logic for ParsedAnimeInfo
            raw_data_size = len(str(value.raw_data).encode("utf-8"))

            if raw_data_size >= compression_manager.min_size_threshold:
                try:
                    compressed_raw_data = compression_manager.compress_for_storage(value.raw_data)

                    compressed_value = ParsedAnimeInfo(
                        title=value.title,
                        season=value.season,
                        episode=value.episode,
                        episode_title=value.episode_title,
                        resolution=value.resolution,
                        resolution_width=value.resolution_width,
                        resolution_height=value.resolution_height,
                        video_codec=value.video_codec,
                        audio_codec=value.audio_codec,
                        release_group=value.release_group,
                        file_extension=value.file_extension,
                        year=value.year,
                        source=value.source,
                        raw_data=(
                            compressed_raw_data if isinstance(compressed_raw_data, dict) else {}
                        ),  # Store compressed data
                    )

                    logger.debug(
                        f"Compressed ParsedAnimeInfo raw_data: {raw_data_size} -> {len(compressed_raw_data)} bytes"
                    )
                    return compressed_value

                except Exception as e:
                    logger.warning(f"Failed to compress ParsedAnimeInfo raw_data: {e}")
                    return value

        return value

    def _decompress_if_needed(
        self, value: ParsedAnimeInfo | TMDBAnime
    ) -> ParsedAnimeInfo | TMDBAnime:
        """Decompress metadata objects if they were compressed.

        Args:
            value: Potentially compressed metadata object

        Returns:
            Decompressed metadata object
        """
        if isinstance(value, TMDBAnime) and value.raw_data:
            try:
                # Try to decompress raw_data
                decompressed_raw_data = compression_manager.decompress_from_storage(
                    value.raw_data, expected_type="dict"
                )

                # If decompression succeeded, create new object with decompressed data
                if decompressed_raw_data != value.raw_data:
                    decompressed_value = TMDBAnime(
                        tmdb_id=value.tmdb_id,
                        title=value.title,
                        original_title=value.original_title,
                        korean_title=value.korean_title,
                        overview=value.overview,
                        release_date=value.release_date,
                        poster_path=value.poster_path,
                        backdrop_path=value.backdrop_path,
                        first_air_date=value.first_air_date,
                        last_air_date=value.last_air_date,
                        status=value.status,
                        vote_average=value.vote_average,
                        vote_count=value.vote_count,
                        popularity=value.popularity,
                        genres=value.genres,
                        networks=value.networks,
                        production_companies=value.production_companies,
                        production_countries=value.production_countries,
                        spoken_languages=value.spoken_languages,
                        number_of_seasons=value.number_of_seasons,
                        number_of_episodes=value.number_of_episodes,
                        tagline=value.tagline,
                        homepage=value.homepage,
                        imdb_id=value.imdb_id,
                        external_ids=value.external_ids,
                        quality_score=value.quality_score,
                        search_strategy=value.search_strategy,
                        fallback_round=value.fallback_round,
                        raw_data=(
                            decompressed_raw_data if isinstance(decompressed_raw_data, dict) else {}
                        ),  # Decompressed data
                    )

                    logger.debug("Decompressed TMDBAnime raw_data")
                    return decompressed_value

            except Exception as e:
                logger.debug(f"Raw data was not compressed or decompression failed: {e}")

        elif isinstance(value, ParsedAnimeInfo) and value.raw_data:
            try:
                decompressed_raw_data = compression_manager.decompress_from_storage(
                    value.raw_data, expected_type="dict"
                )

                if decompressed_raw_data != value.raw_data:
                    decompressed_value = ParsedAnimeInfo(
                        title=value.title,
                        season=value.season,
                        episode=value.episode,
                        episode_title=value.episode_title,
                        resolution=value.resolution,
                        resolution_width=value.resolution_width,
                        resolution_height=value.resolution_height,
                        video_codec=value.video_codec,
                        audio_codec=value.audio_codec,
                        release_group=value.release_group,
                        file_extension=value.file_extension,
                        year=value.year,
                        source=value.source,
                        raw_data=(
                            decompressed_raw_data if isinstance(decompressed_raw_data, dict) else {}
                        ),  # Decompressed data
                    )

                    logger.debug("Decompressed ParsedAnimeInfo raw_data")
                    return decompressed_value

            except Exception as e:
                logger.debug(f"Raw data was not compressed or decompression failed: {e}")

        return value


class MetadataCacheManager:
    """Manager for multiple metadata caches with different purposes.

    This class provides a unified interface for managing separate caches
    for different types of metadata (parsed info, TMDB data, etc.).
    """

    def __init__(self, db_manager: DatabaseManager | None = None, enable_db: bool = True) -> None:
        """Initialize the cache manager with optional database integration.

        Args:
            db_manager: Database manager for persistence (optional)
            enable_db: Whether to enable database persistence
        """
        self._caches: dict[str, MetadataCache] = {}
        self._lock = threading.RLock()
        self.db_manager = db_manager
        self.enable_db = enable_db and db_manager is not None

    def get_cache(self, name: str) -> MetadataCache:
        """Get or create a cache with the specified name.

        Args:
            name: Cache name

        Returns:
            MetadataCache instance
        """
        with self._lock:
            if name not in self._caches:
                self._caches[name] = MetadataCache(
                    db_manager=self.db_manager, enable_db=self.enable_db
                )
            return self._caches[name]

    def get_parsed_info_cache(self) -> MetadataCache:
        """Get the cache for ParsedAnimeInfo objects."""
        return self.get_cache("parsed_info")

    def get_tmdb_cache(self) -> MetadataCache:
        """Get the cache for TMDBAnime objects."""
        return self.get_cache("tmdb_anime")

    def get_combined_cache(self) -> MetadataCache:
        """Get the cache for combined metadata."""
        return self.get_cache("combined")

    def clear_all_caches(self) -> None:
        """Clear all caches."""
        with self._lock:
            for cache in self._caches.values():
                cache.clear()

    def get_all_stats(self) -> dict[str, CacheStats]:
        """Get statistics for all caches."""
        with self._lock:
            return {name: cache.get_stats() for name, cache in self._caches.items()}

    def get_total_memory_usage_mb(self) -> float:
        """Get total memory usage across all caches."""
        with self._lock:
            return sum(cache.get_memory_usage_mb() for cache in self._caches.values())


# Global cache manager instance
cache_manager = MetadataCacheManager()
