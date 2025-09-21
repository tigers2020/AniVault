"""Core cache functionality for AniVault application.

This module provides the fundamental cache operations including LRU eviction,
statistics tracking, and thread-safe operations.
"""

from __future__ import annotations

import heapq
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from .cache_key_generator import get_cache_key_generator
from .cache_metrics_exporter import update_cache_metrics, update_cache_size, update_memory_usage
from .cache_tracker import CacheMetrics, get_cache_tracker
from .compression import compression_manager
from .smart_cache_matcher import smart_cache_matcher
from .models import ParsedAnimeInfo, TMDBAnime

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


class CacheEntry:
    """Represents a single cache entry with metadata."""

    def __init__(self, value: ParsedAnimeInfo | TMDBAnime, ttl_seconds: int | None = None):
        """Initialize cache entry.

        Args:
            value: The cached data
            ttl_seconds: Time to live in seconds (None for no expiration)
        """
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0
        self.ttl_seconds = ttl_seconds

    def update_access(self) -> None:
        """Update access time and count."""
        self.last_accessed = time.time()
        self.access_count += 1

    def is_expired(self) -> bool:
        """Check if entry has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_at > self.ttl_seconds

    def get_remaining_ttl(self) -> int:
        """Get remaining TTL in seconds."""
        if self.ttl_seconds is None:
            return -1
        elapsed = time.time() - self.created_at
        return max(0, int(self.ttl_seconds - elapsed))


class CacheCore:
    """Core cache functionality with LRU eviction and statistics tracking."""

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl_seconds: int | None = None,
        enable_compression: bool = True,
        cache_name: str = "default",
    ):
        """Initialize the cache.

        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl_seconds: Default TTL for entries
            enable_compression: Whether to enable compression
            cache_name: Name of the cache for metrics
        """
        self.max_size = max_size
        self.max_memory_mb = max_memory_mb
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl_seconds = default_ttl_seconds
        self.enable_compression = enable_compression
        self.cache_name = cache_name

        # Core cache data structures
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()

        # Cache key generator
        self._key_generator = get_cache_key_generator()
        self._cache_tracker = get_cache_tracker(cache_name)

        # Background cleanup
        self._cleanup_thread: threading.Thread | None = None
        self._cleanup_stop_event = threading.Event()
        self._cleanup_interval = 60  # seconds

        # Cache state
        self._enabled = True
        self._cache_only_mode = False
        self._cache_only_reason = ""

        logger.info(f"Initialized cache '{cache_name}' with max_size={max_size}, max_memory={max_memory_mb}MB")

    def get(self, key: str, session: Session | None = None) -> ParsedAnimeInfo | TMDBAnime | None:
        """Get value from cache.

        Args:
            key: Cache key
            session: Database session (for fallback loading)

        Returns:
            Cached value or None if not found
        """
        if not self._enabled:
            return None

        with self._lock:
            self._stats.total_requests += 1

            if key not in self._cache:
                self._stats.misses += 1
                return None

            entry = self._cache[key]

            # Check TTL expiration
            if entry.is_expired():
                self._stats.ttl_misses += 1
                self._stats.ttl_expirations += 1
                del self._cache[key]
                self._stats.cache_size = len(self._cache)
                return None

            # Update access info
            entry.update_access()
            self._cache.move_to_end(key)  # Move to end (most recently used)

            self._stats.hits += 1
            self._stats.ttl_hits += 1

            # Update metrics
            update_cache_metrics(self.cache_name, "hit")
            self._cache_tracker.track_hit()

            return entry.value

    def get_smart(
        self,
        query: str,
        session: Session | None = None,
        similarity_threshold: float = 0.8,
        max_results: int = 10,
    ) -> list[tuple[ParsedAnimeInfo | TMDBAnime, float]]:
        """Get values using smart matching.

        Args:
            query: Search query
            session: Database session
            similarity_threshold: Minimum similarity score
            max_results: Maximum number of results

        Returns:
            List of tuples (value, similarity_score)
        """
        if not self._enabled:
            return []

        with self._lock:
            results = []
            current_time = time.time()

            for key, entry in self._cache.items():
                if entry.is_expired():
                    continue

                # Use smart matcher to calculate similarity
                similarity = smart_cache_matcher.calculate_similarity(query, key)
                if similarity >= similarity_threshold:
                    entry.update_access()
                    results.append((entry.value, similarity))

            # Sort by similarity (descending) and limit results
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:max_results]

    def put(
        self,
        key: str,
        value: ParsedAnimeInfo | TMDBAnime,
        ttl_seconds: int | None = None,
        session: Session | None = None,
    ) -> None:
        """Store value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: TTL override (uses default if None)
            session: Database session (for persistence)
        """
        if not self._enabled:
            return

        with self._lock:
            # Use provided TTL or default
            effective_ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds

            # Create new entry
            entry = CacheEntry(value, effective_ttl)

            # Calculate entry size
            entry_size = self._calculate_entry_size(key, value)

            # Ensure capacity
            self._ensure_capacity(entry_size)

            # Store in cache
            self._store_in_cache(key, value, effective_ttl)

            # Update statistics
            self._stats.cache_size = len(self._cache)
            self._stats.memory_usage_bytes += entry_size

            # Update metrics
            update_cache_size(self.cache_name, self._stats.cache_size)
            update_memory_usage(self.cache_name, self._stats.memory_usage_bytes)

    def delete(self, key: str, session: Session | None = None) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key
            session: Database session (for persistence)

        Returns:
            True if key was found and deleted
        """
        if not self._enabled:
            return False

        with self._lock:
            if key not in self._cache:
                return False

            # Calculate size of entry being removed
            entry = self._cache[key]
            entry_size = self._calculate_entry_size(key, entry.value)

            # Remove from cache
            del self._cache[key]

            # Update statistics
            self._stats.cache_size = len(self._cache)
            self._stats.memory_usage_bytes = max(0, self._stats.memory_usage_bytes - entry_size)

            # Update metrics
            update_cache_size(self.cache_name, self._stats.cache_size)
            update_memory_usage(self.cache_name, self._stats.memory_usage_bytes)

            return True

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats.cache_size = 0
            self._stats.memory_usage_bytes = 0

            # Update metrics
            update_cache_size(self.cache_name, 0)
            update_memory_usage(self.cache_name, 0)

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate entries matching a pattern.

        Args:
            pattern: Pattern to match against keys

        Returns:
            Number of entries invalidated
        """
        if not self._enabled:
            return 0

        with self._lock:
            keys_to_remove = []
            for key in self._cache.keys():
                if pattern in key:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del self._cache[key]

            # Update statistics
            self._stats.cache_size = len(self._cache)

            # Update metrics
            update_cache_size(self.cache_name, self._stats.cache_size)

            return len(keys_to_remove)

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Current cache statistics
        """
        with self._lock:
            # Update current stats
            self._stats.cache_size = len(self._cache)
            self._stats.memory_usage_bytes = self._calculate_total_memory_usage()

            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                total_requests=self._stats.total_requests,
                cache_size=self._stats.cache_size,
                memory_usage_bytes=self._stats.memory_usage_bytes,
                expirations=self._stats.expirations,
                ttl_expirations=self._stats.ttl_expirations,
                ttl_hits=self._stats.ttl_hits,
                ttl_misses=self._stats.ttl_misses,
            )

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self._stats.reset()

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        with self._lock:
            return self._stats.memory_usage_bytes / (1024 * 1024)

    def is_enabled(self) -> bool:
        """Check if cache is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable cache."""
        self._enabled = True

    def disable(self) -> None:
        """Disable cache."""
        self._enabled = False

    def set_max_size(self, max_size: int) -> None:
        """Set maximum cache size."""
        with self._lock:
            self.max_size = max_size
            # Trigger cleanup if needed
            self._ensure_capacity(0)

    def set_max_memory_mb(self, max_memory_mb: int) -> None:
        """Set maximum memory usage in MB."""
        with self._lock:
            self.max_memory_mb = max_memory_mb
            self.max_memory_bytes = max_memory_mb * 1024 * 1024
            # Trigger cleanup if needed
            self._ensure_capacity(0)

    def enable_cache_only_mode(self, reason: str = "Database unavailable") -> None:
        """Enable cache-only mode.

        Args:
            reason: Reason for enabling cache-only mode
        """
        with self._lock:
            self._cache_only_mode = True
            self._cache_only_reason = reason
            logger.warning(f"Cache '{self.cache_name}' switched to cache-only mode: {reason}")

    def disable_cache_only_mode(self) -> None:
        """Disable cache-only mode."""
        with self._lock:
            self._cache_only_mode = False
            self._cache_only_reason = ""
            logger.info(f"Cache '{self.cache_name}' disabled cache-only mode")

    def is_cache_only_mode(self) -> bool:
        """Check if cache is in cache-only mode."""
        return self._cache_only_mode

    def get_cache_only_reason(self) -> str:
        """Get reason for cache-only mode."""
        return self._cache_only_reason

    def get_entries_info(self) -> list[dict[str, Any]]:
        """Get information about all cache entries.

        Returns:
            List of dictionaries with entry information
        """
        with self._lock:
            entries_info = []
            current_time = time.time()

            for key, entry in self._cache.items():
                info = {
                    "key": key,
                    "created_at": entry.created_at,
                    "last_accessed": entry.last_accessed,
                    "access_count": entry.access_count,
                    "ttl_seconds": entry.ttl_seconds,
                    "is_expired": entry.is_expired(),
                    "remaining_ttl": entry.get_remaining_ttl(),
                    "value_type": type(entry.value).__name__,
                }
                entries_info.append(info)

            return entries_info

    def get_ttl_info(self) -> dict[str, Any]:
        """Get TTL-related information.

        Returns:
            Dictionary with TTL statistics
        """
        with self._lock:
            current_time = time.time()
            total_entries = len(self._cache)
            expired_entries = 0
            ttl_entries = 0
            no_ttl_entries = 0

            for entry in self._cache.values():
                if entry.is_expired():
                    expired_entries += 1
                if entry.ttl_seconds is not None:
                    ttl_entries += 1
                else:
                    no_ttl_entries += 1

            return {
                "total_entries": total_entries,
                "expired_entries": expired_entries,
                "ttl_entries": ttl_entries,
                "no_ttl_entries": no_ttl_entries,
                "default_ttl_seconds": self.default_ttl_seconds,
            }

    def set_ttl(self, key: str, ttl_seconds: int | None) -> bool:
        """Set TTL for a specific cache entry.

        Args:
            key: Cache key
            ttl_seconds: TTL in seconds (None to remove TTL)

        Returns:
            True if key was found and TTL was set
        """
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            entry.ttl_seconds = ttl_seconds
            return True

    def get_remaining_ttl(self, key: str) -> int | None:
        """Get remaining TTL for a cache entry.

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds, or None if not found or no TTL
        """
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            return entry.get_remaining_ttl()

    def cleanup_expired_entries_manual(self) -> int:
        """Manually clean up expired entries.

        Returns:
            Number of entries cleaned up
        """
        with self._lock:
            return self._cleanup_expired_entries()

    def _remove_entry(self, key: str) -> None:
        """Remove entry from cache and update statistics.

        Args:
            key: Cache key to remove
        """
        if key in self._cache:
            entry = self._cache[key]
            entry_size = self._calculate_entry_size(key, entry.value)

            del self._cache[key]

            # Update statistics
            self._stats.cache_size = len(self._cache)
            self._stats.memory_usage_bytes = max(0, self._stats.memory_usage_bytes - entry_size)

            # Update metrics
            update_cache_size(self.cache_name, self._stats.cache_size)
            update_memory_usage(self.cache_name, self._stats.memory_usage_bytes)

    def _calculate_entry_size(self, key: str, value: ParsedAnimeInfo | TMDBAnime) -> int:
        """Calculate memory size of a cache entry.

        Args:
            key: Cache key
            value: Cached value

        Returns:
            Estimated size in bytes
        """
        # Base size for key and entry metadata
        base_size = len(key.encode('utf-8')) + 100  # Rough estimate for entry metadata

        if isinstance(value, ParsedAnimeInfo):
            return base_size + self._calculate_parsed_info_size(value)
        elif isinstance(value, TMDBAnime):
            return base_size + self._calculate_tmdb_anime_size(value)
        else:
            return base_size + 1000  # Default estimate

    def _calculate_parsed_info_size(self, info: ParsedAnimeInfo) -> int:
        """Calculate memory size of ParsedAnimeInfo.

        Args:
            info: ParsedAnimeInfo instance

        Returns:
            Estimated size in bytes
        """
        size = 0
        for field_name in ['title', 'season', 'episode', 'year', 'quality', 'group', 'file_path']:
            value = getattr(info, field_name, None)
            if value is not None:
                size += len(str(value).encode('utf-8'))
        return size

    def _calculate_tmdb_anime_size(self, anime: TMDBAnime) -> int:
        """Calculate memory size of TMDBAnime.

        Args:
            anime: TMDBAnime instance

        Returns:
            Estimated size in bytes
        """
        size = 0
        for field_name in ['title', 'original_title', 'overview', 'poster_path', 'backdrop_path']:
            value = getattr(anime, field_name, None)
            if value is not None:
                size += len(str(value).encode('utf-8'))
        return size

    def _calculate_total_memory_usage(self) -> int:
        """Calculate total memory usage of all cache entries.

        Returns:
            Total memory usage in bytes
        """
        total_size = 0
        for key, entry in self._cache.items():
            total_size += self._calculate_entry_size(key, entry.value)
        return total_size

    def _ensure_capacity(self, new_entry_size: int) -> None:
        """Ensure cache has capacity for new entry.

        Args:
            new_entry_size: Size of new entry to be added
        """
        # Check size limit
        while len(self._cache) >= self.max_size:
            self._evict_lru()

        # Check memory limit
        current_memory = self._calculate_total_memory_usage()
        while current_memory + new_entry_size > self.max_memory_bytes and self._cache:
            self._evict_lru()
            current_memory = self._calculate_total_memory_usage()

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return

        # Remove oldest entry (first in OrderedDict)
        key, entry = self._cache.popitem(last=False)
        entry_size = self._calculate_entry_size(key, entry.value)

        # Update statistics
        self._stats.evictions += 1
        self._stats.memory_usage_bytes = max(0, self._stats.memory_usage_bytes - entry_size)

        # Update metrics
        update_cache_metrics(self.cache_name, "eviction")
        self._cache_tracker.track_eviction()

    def _should_cleanup(self) -> bool:
        """Check if cleanup should be performed."""
        return len(self._cache) > 0

    def _cleanup_expired_entries(self) -> int:
        """Clean up expired entries.

        Returns:
            Number of entries cleaned up
        """
        if not self._should_cleanup():
            return 0

        current_time = time.time()
        expired_keys = []

        # Find expired entries
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        # Remove expired entries
        for key in expired_keys:
            self._remove_entry(key)

        # Update statistics
        self._stats.expirations += len(expired_keys)
        self._stats.ttl_expirations += len(expired_keys)

        # Update metrics
        update_cache_metrics(self.cache_name, "expiration", len(expired_keys))

        return len(expired_keys)

    def _store_in_cache(self, key: str, value: ParsedAnimeInfo | TMDBAnime, ttl_seconds: int | None = None) -> None:
        """Store value in cache with compression if enabled.

        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: TTL for the entry
        """
        # Apply compression if enabled
        if self.enable_compression:
            compressed_value = self._apply_compression_if_needed(value)
            if compressed_value is not None:
                value = compressed_value

        # Create and store entry
        entry = CacheEntry(value, ttl_seconds)
        self._cache[key] = entry

        # Update access info
        entry.update_access()

    def _apply_compression_if_needed(self, value: ParsedAnimeInfo | TMDBAnime) -> ParsedAnimeInfo | TMDBAnime | None:
        """Apply compression to value if beneficial.

        Args:
            value: Value to potentially compress

        Returns:
            Compressed value or None if compression not beneficial
        """
        if not self.enable_compression:
            return None

        try:
            # Check if compression would be beneficial
            original_size = self._calculate_entry_size("", value)
            if original_size < 1024:  # Don't compress small values
                return None

            # Apply compression
            compressed_data = compression_manager.compress(value)
            if compressed_data is None:
                return None

            # Check if compression actually saved space
            compressed_size = len(compressed_data)
            if compressed_size >= original_size * 0.8:  # Less than 20% savings
                return None

            # Create a wrapper object to hold compressed data
            class CompressedValue:
                def __init__(self, data: bytes, original_type: type):
                    self.compressed_data = data
                    self.original_type = original_type

            return CompressedValue(compressed_data, type(value))

        except Exception as e:
            logger.warning(f"Compression failed for value: {e}")
            return None

    def _decompress_if_needed(self, value: Any) -> ParsedAnimeInfo | TMDBAnime:
        """Decompress value if it's compressed.

        Args:
            value: Potentially compressed value

        Returns:
            Decompressed value
        """
        if not self.enable_compression:
            return value

        try:
            # Check if value is compressed
            if hasattr(value, 'compressed_data') and hasattr(value, 'original_type'):
                # Decompress
                decompressed = compression_manager.decompress(value.compressed_data, value.original_type)
                if decompressed is not None:
                    return decompressed

        except Exception as e:
            logger.warning(f"Decompression failed: {e}")

        return value

    def start_background_cleanup(self) -> None:
        """Start background cleanup thread."""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return

        self._cleanup_stop_event.clear()
        self._cleanup_thread = threading.Thread(
            target=self._background_cleanup_worker,
            name=f"CacheCleanup-{self.cache_name}",
            daemon=True
        )
        self._cleanup_thread.start()
        logger.info(f"Started background cleanup for cache '{self.cache_name}'")

    def stop_background_cleanup(self) -> None:
        """Stop background cleanup thread."""
        if self._cleanup_thread is None:
            return

        self._cleanup_stop_event.set()
        if self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5.0)
        self._cleanup_thread = None
        logger.info(f"Stopped background cleanup for cache '{self.cache_name}'")

    def _background_cleanup_worker(self) -> None:
        """Background worker for cleaning up expired entries."""
        while not self._cleanup_stop_event.is_set():
            try:
                # Perform cleanup
                cleaned = self._cleanup_expired_entries()
                if cleaned > 0:
                    logger.debug(f"Cleaned up {cleaned} expired entries from cache '{self.cache_name}'")

                # Wait for next cleanup cycle
                self._cleanup_stop_event.wait(self._cleanup_interval)

            except Exception as e:
                logger.error(f"Error in background cleanup for cache '{self.cache_name}': {e}")
                self._cleanup_stop_event.wait(10)  # Wait 10 seconds before retrying

    def __del__(self) -> None:
        """Cleanup when cache is destroyed."""
        try:
            if hasattr(self, '_cleanup_thread'):
                self.stop_background_cleanup()
        except Exception:
            # Ignore errors during cleanup
            pass
