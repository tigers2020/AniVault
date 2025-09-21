"""Refactored metadata caching system for AniVault application.

This module provides a refactored cache system with separated concerns:
- CacheCore: Basic cache functionality
- CacheDatabaseIntegration: Database integration
- CacheBulkOperations: Bulk operations
- CacheIncrementalSync: Incremental synchronization
- CacheCompression: Compression handling
- CacheSimilarityKeys: Similarity key management
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from .cache_bulk_operations import CacheBulkOperations
from .cache_compression import CacheCompression
from .cache_core import CacheCore, CacheStats
from .cache_database_integration import CacheDatabaseIntegration
from .cache_incremental_sync import CacheIncrementalSync
from .cache_similarity_keys import CacheSimilarityKeys
from .database import DatabaseManager
from .incremental_sync import IncrementalSyncManager
from .models import ParsedAnimeInfo, TMDBAnime

# Configure logging
logger = logging.getLogger(__name__)


class MetadataCache:
    """Refactored metadata cache with separated concerns."""

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl_seconds: int | None = None,
        enable_compression: bool = True,
        cache_name: str = "default",
        db_manager: DatabaseManager | None = None,
        enable_db: bool = True,
        incremental_sync_manager: IncrementalSyncManager | None = None,
    ) -> None:
        """Initialize the refactored metadata cache.

        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl_seconds: Default TTL for entries
            enable_compression: Whether to enable compression
            cache_name: Name of the cache for metrics
            db_manager: Database manager instance
            enable_db: Whether to enable database integration
            incremental_sync_manager: Incremental sync manager
        """
        # Initialize core cache
        self.cache_core = CacheCore(
            max_size=max_size,
            max_memory_mb=max_memory_mb,
            default_ttl_seconds=default_ttl_seconds,
            enable_compression=enable_compression,
            cache_name=cache_name,
        )

        # Initialize database integration
        self.db_integration = CacheDatabaseIntegration(
            cache_core=self.cache_core, db_manager=db_manager if enable_db else None
        )

        # Initialize bulk operations
        self.bulk_operations = CacheBulkOperations(
            cache_core=self.cache_core, db_integration=self.db_integration
        )

        # Initialize incremental sync
        self.incremental_sync = CacheIncrementalSync(
            cache_core=self.cache_core,
            db_integration=self.db_integration,
            incremental_sync_manager=incremental_sync_manager,
        )

        # Initialize compression
        self.compression = CacheCompression(
            enable_compression=enable_compression, compression_threshold=1024
        )

        # Initialize similarity keys
        self.similarity_keys = CacheSimilarityKeys()

        # Store configuration
        self.cache_name = cache_name
        self.enable_db = enable_db

        logger.info(f"Initialized refactored metadata cache '{cache_name}'")

    # Core cache operations (delegated to CacheCore)
    def get(self, key: str, session: Session | None = None) -> ParsedAnimeInfo | TMDBAnime | None:
        """Get value from cache."""
        value = self.cache_core.get(key, session)
        if value is not None:
            # Decompress if needed
            value = self.compression.decompress_if_needed(value)
        return value

    def get_smart(
        self,
        query: str,
        session: Session | None = None,
        similarity_threshold: float = 0.8,
        max_results: int = 10,
    ) -> list[tuple[ParsedAnimeInfo | TMDBAnime, float]]:
        """Get values using smart matching."""
        results = self.cache_core.get_smart(query, session, similarity_threshold, max_results)

        # Decompress results
        decompressed_results = []
        for value, similarity in results:
            decompressed_value = self.compression.decompress_if_needed(value)
            decompressed_results.append((decompressed_value, similarity))

        return decompressed_results

    def put(
        self,
        key: str,
        value: ParsedAnimeInfo | TMDBAnime,
        ttl_seconds: int | None = None,
        session: Session | None = None,
    ) -> None:
        """Store value in cache."""
        # Apply compression if needed
        compressed_value = self.compression.apply_compression_if_needed(value)
        if compressed_value is not None:
            value = compressed_value

        # Store in cache
        self.cache_core.put(key, value, ttl_seconds, session)

        # Store similarity keys
        self.similarity_keys.store_similarity_keys(key, value)

        # Store in database if enabled
        if self.enable_db and not self.cache_core.is_cache_only_mode():
            self.db_integration._store_in_database(key, value)

    def delete(self, key: str, session: Session | None = None) -> bool:
        """Delete value from cache."""
        # Remove similarity keys
        self.similarity_keys.remove_similarity_keys(key)

        # Delete from cache
        result = self.cache_core.delete(key, session)

        # Delete from database if enabled
        if self.enable_db and not self.cache_core.is_cache_only_mode():
            self.db_integration._delete_from_database(key)

        return result

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache_core.clear()
        self.similarity_keys.clear_all_similarity_keys()

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate entries matching a pattern."""
        # Find matching keys using similarity keys
        matching_keys = self.similarity_keys.get_keys_by_similarity_pattern(pattern)

        # Also use core cache pattern matching
        core_invalidated = self.cache_core.invalidate_pattern(pattern)

        # Remove similarity keys for invalidated entries
        for key in matching_keys:
            self.similarity_keys.remove_similarity_keys(key)

        return core_invalidated + len(matching_keys)

    # Statistics and monitoring (delegated to CacheCore)
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.cache_core.get_stats()

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self.cache_core.reset_stats()

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        return self.cache_core.get_memory_usage_mb()

    # Cache state management (delegated to CacheCore)
    def is_enabled(self) -> bool:
        """Check if cache is enabled."""
        return self.cache_core.is_enabled()

    def enable(self) -> None:
        """Enable cache."""
        self.cache_core.enable()

    def disable(self) -> None:
        """Disable cache."""
        self.cache_core.disable()

    def set_max_size(self, max_size: int) -> None:
        """Set maximum cache size."""
        self.cache_core.set_max_size(max_size)

    def set_max_memory_mb(self, max_memory_mb: int) -> None:
        """Set maximum memory usage in MB."""
        self.cache_core.set_max_memory_mb(max_memory_mb)

    def enable_cache_only_mode(self, reason: str = "Database unavailable") -> None:
        """Enable cache-only mode."""
        self.cache_core.enable_cache_only_mode(reason)

    def disable_cache_only_mode(self) -> None:
        """Disable cache-only mode."""
        self.cache_core.disable_cache_only_mode()

    def is_cache_only_mode(self) -> bool:
        """Check if cache is in cache-only mode."""
        return self.cache_core.is_cache_only_mode()

    def get_cache_only_reason(self) -> str:
        """Get reason for cache-only mode."""
        return self.cache_core.get_cache_only_reason()

    def enable_auto_cache_only_mode(self) -> None:
        """Enable automatic cache-only mode based on database health."""
        self.db_integration.enable_auto_cache_only_mode()

    def check_database_health_and_adapt(self) -> None:
        """Check database health and adapt cache behavior accordingly."""
        self.db_integration.check_database_health_and_adapt()

    # TTL management (delegated to CacheCore)
    def get_entries_info(self) -> list[dict[str, Any]]:
        """Get information about all cache entries."""
        return self.cache_core.get_entries_info()

    def get_ttl_info(self) -> dict[str, Any]:
        """Get TTL-related information."""
        return self.cache_core.get_ttl_info()

    def set_ttl(self, key: str, ttl_seconds: int | None) -> bool:
        """Set TTL for a specific cache entry."""
        return self.cache_core.set_ttl(key, ttl_seconds)

    def get_remaining_ttl(self, key: str) -> int | None:
        """Get remaining TTL for a cache entry."""
        return self.cache_core.get_remaining_ttl(key)

    def cleanup_expired_entries_manual(self) -> int:
        """Manually clean up expired entries."""
        return self.cache_core.cleanup_expired_entries_manual()

    # Background cleanup (delegated to CacheCore)
    def start_background_cleanup(self) -> None:
        """Start background cleanup thread."""
        self.cache_core.start_background_cleanup()

    def stop_background_cleanup(self) -> None:
        """Stop background cleanup thread."""
        self.cache_core.stop_background_cleanup()

    # Bulk operations (delegated to CacheBulkOperations)
    def bulk_store_tmdb_metadata(self, session: Session, anime_list: list[TMDBAnime]) -> int:
        """Bulk store TMDB metadata."""
        return self.bulk_operations.bulk_store_tmdb_metadata(session, anime_list)

    def bulk_store_parsed_files(
        self, session: Session, parsed_files: list[ParsedAnimeInfo], batch_size: int = 100
    ) -> int:
        """Bulk store parsed files."""
        return self.bulk_operations.bulk_store_parsed_files(session, parsed_files, batch_size)

    def bulk_update_tmdb_metadata(self, session: Session, updates: list[dict]) -> int:
        """Bulk update TMDB metadata."""
        return self.bulk_operations.bulk_update_tmdb_metadata(session, updates)

    def bulk_update_parsed_files(self, session: Session, updates: list[dict]) -> int:
        """Bulk update parsed files."""
        return self.bulk_operations.bulk_update_parsed_files(session, updates)

    def bulk_update_tmdb_metadata_by_ids(
        self, session: Session, tmdb_ids: list[int], update_fields: dict[str, Any]
    ) -> int:
        """Bulk update TMDB metadata by IDs."""
        return self.bulk_operations.bulk_update_tmdb_metadata_by_ids(
            session, tmdb_ids, update_fields
        )

    def bulk_update_parsed_files_by_paths(
        self, session: Session, file_paths: list[str], update_fields: dict[str, Any]
    ) -> int:
        """Bulk update parsed files by file paths."""
        return self.bulk_operations.bulk_update_parsed_files_by_paths(
            session, file_paths, update_fields
        )

    # Incremental sync (delegated to CacheIncrementalSync)
    def enable_incremental_sync(self) -> None:
        """Enable incremental synchronization."""
        self.incremental_sync.enable_incremental_sync()

    def disable_incremental_sync(self) -> None:
        """Disable incremental synchronization."""
        self.incremental_sync.disable_incremental_sync()

    def is_incremental_sync_enabled(self) -> bool:
        """Check if incremental sync is enabled."""
        return self.incremental_sync.is_incremental_sync_enabled()

    def get_incremental_sync_manager(self) -> IncrementalSyncManager | None:
        """Get incremental sync manager."""
        return self.incremental_sync.get_incremental_sync_manager()

    def sync_tmdb_metadata_incremental(
        self, session: Session, last_sync_timestamp: float | None = None, batch_size: int = 100
    ) -> dict[str, Any]:
        """Incremental sync for TMDB metadata."""
        return self.incremental_sync.sync_tmdb_metadata_incremental(
            session, last_sync_timestamp, batch_size
        )

    def sync_parsed_files_incremental(
        self, session: Session, last_sync_timestamp: float | None = None, batch_size: int = 100
    ) -> dict[str, Any]:
        """Incremental sync for parsed files."""
        return self.incremental_sync.sync_parsed_files_incremental(
            session, last_sync_timestamp, batch_size
        )

    def sync_all_entities_incremental(
        self, session: Session, last_sync_timestamp: float | None = None, batch_size: int = 100
    ) -> dict[str, Any]:
        """Incremental sync for all entities."""
        return self.incremental_sync.sync_all_entities_incremental(
            session, last_sync_timestamp, batch_size
        )

    def get_sync_status(self) -> dict:
        """Get current sync status."""
        return self.incremental_sync.get_sync_status()

    # Similarity key management (delegated to CacheSimilarityKeys)
    def find_similar_keys(self, query: str, threshold: float = 0.8) -> list[tuple[str, float]]:
        """Find cache keys similar to a query."""
        return self.similarity_keys.find_similar_keys(query, threshold)

    def get_similarity_stats(self) -> dict[str, Any]:
        """Get similarity key statistics."""
        return self.similarity_keys.get_similarity_stats()

    def get_similarity_key_coverage(self) -> dict[str, float]:
        """Get similarity key coverage statistics."""
        return self.similarity_keys.get_similarity_key_coverage()

    # Compression management (delegated to CacheCompression)
    def get_compression_stats(self) -> dict[str, Any]:
        """Get compression statistics."""
        return self.compression.get_compression_stats()

    # Database integration (delegated to CacheDatabaseIntegration)
    def store_with_database(
        self, key: str, value: ParsedAnimeInfo | TMDBAnime, ttl_seconds: int | None = None
    ) -> None:
        """Store value in both cache and database."""
        self.db_integration.store_with_database(key, value, ttl_seconds)

    def load_with_database(self, key: str) -> ParsedAnimeInfo | TMDBAnime | None:
        """Load value from cache, fallback to database."""
        return self.db_integration.load_with_database(key)

    def delete_with_database(self, key: str) -> bool:
        """Delete value from both cache and database."""
        return self.db_integration.delete_with_database(key)

    def sync_with_database(self) -> dict[str, Any]:
        """Sync cache with database."""
        return self.db_integration.sync_with_database()

    def __del__(self) -> None:
        """Cleanup when cache is destroyed."""
        try:
            if hasattr(self, "cache_core"):
                self.cache_core.stop_background_cleanup()
        except Exception:
            # Ignore errors during cleanup
            pass
