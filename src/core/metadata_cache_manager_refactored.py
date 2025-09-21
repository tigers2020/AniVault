"""Refactored metadata cache manager for AniVault application.

This module provides a manager for multiple cache instances with separated concerns.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .cache_core import CacheStats
from .database import DatabaseManager
from .incremental_sync import IncrementalSyncManager
from .metadata_cache_refactored import MetadataCache

# Configure logging
logger = logging.getLogger(__name__)


class MetadataCacheManager:
    """Manager for multiple metadata cache instances."""

    def __init__(self, db_manager: DatabaseManager | None = None, enable_db: bool = True) -> None:
        """Initialize the cache manager.

        Args:
            db_manager: Database manager instance
            enable_db: Whether to enable database integration
        """
        self.db_manager = db_manager
        self.enable_db = enable_db
        self._caches: dict[str, MetadataCache] = {}
        self._incremental_sync_manager = IncrementalSyncManager() if enable_db else None

        # Create default caches
        self._create_default_caches()

        logger.info("Initialized refactored metadata cache manager")

    def _create_default_caches(self) -> None:
        """Create default cache instances."""
        # Parsed info cache
        self._caches["parsed_info"] = MetadataCache(
            max_size=1000,
            max_memory_mb=100,
            default_ttl_seconds=3600,  # 1 hour
            enable_compression=True,
            cache_name="parsed_info",
            db_manager=self.db_manager,
            enable_db=self.enable_db,
            incremental_sync_manager=self._incremental_sync_manager,
        )

        # TMDB cache
        self._caches["tmdb"] = MetadataCache(
            max_size=500,
            max_memory_mb=50,
            default_ttl_seconds=7200,  # 2 hours
            enable_compression=True,
            cache_name="tmdb",
            db_manager=self.db_manager,
            enable_db=self.enable_db,
            incremental_sync_manager=self._incremental_sync_manager,
        )

        # Combined cache (for backward compatibility)
        self._caches["combined"] = MetadataCache(
            max_size=1500,
            max_memory_mb=150,
            default_ttl_seconds=3600,  # 1 hour
            enable_compression=True,
            cache_name="combined",
            db_manager=self.db_manager,
            enable_db=self.enable_db,
            incremental_sync_manager=self._incremental_sync_manager,
        )

    def get_cache(self, name: str) -> MetadataCache:
        """Get a cache instance by name.

        Args:
            name: Cache name

        Returns:
            Cache instance

        Raises:
            KeyError: If cache name not found
        """
        if name not in self._caches:
            raise KeyError(
                f"Cache '{name}' not found. Available caches: {list(self._caches.keys())}"
            )

        return self._caches[name]

    def create_cache(
        self,
        name: str,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        default_ttl_seconds: int | None = None,
        enable_compression: bool = True,
    ) -> MetadataCache:
        """Create a new cache instance.

        Args:
            name: Cache name
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl_seconds: Default TTL for entries
            enable_compression: Whether to enable compression

        Returns:
            New cache instance

        Raises:
            ValueError: If cache name already exists
        """
        if name in self._caches:
            raise ValueError(f"Cache '{name}' already exists")

        cache = MetadataCache(
            max_size=max_size,
            max_memory_mb=max_memory_mb,
            default_ttl_seconds=default_ttl_seconds,
            enable_compression=enable_compression,
            cache_name=name,
            db_manager=self.db_manager,
            enable_db=self.enable_db,
            incremental_sync_manager=self._incremental_sync_manager,
        )

        self._caches[name] = cache
        logger.info(f"Created new cache instance: {name}")
        return cache

    def remove_cache(self, name: str) -> bool:
        """Remove a cache instance.

        Args:
            name: Cache name

        Returns:
            True if cache was removed, False if not found
        """
        if name not in self._caches:
            return False

        # Stop background cleanup
        self._caches[name].stop_background_cleanup()

        # Remove from manager
        del self._caches[name]
        logger.info(f"Removed cache instance: {name}")
        return True

    def get_parsed_info_cache(self) -> MetadataCache:
        """Get the parsed info cache instance."""
        return self.get_cache("parsed_info")

    def get_tmdb_cache(self) -> MetadataCache:
        """Get the TMDB cache instance."""
        return self.get_cache("tmdb")

    def get_combined_cache(self) -> MetadataCache:
        """Get the combined cache instance."""
        return self.get_cache("combined")

    def clear_all_caches(self) -> None:
        """Clear all cache instances."""
        for cache in self._caches.values():
            cache.clear()
        logger.info("Cleared all cache instances")

    def get_all_stats(self) -> dict[str, CacheStats]:
        """Get statistics for all cache instances.

        Returns:
            Dictionary mapping cache names to their statistics
        """
        stats = {}
        for name, cache in self._caches.items():
            stats[name] = cache.get_stats()
        return stats

    def get_total_memory_usage_mb(self) -> float:
        """Get total memory usage across all caches in MB.

        Returns:
            Total memory usage in MB
        """
        total_memory = 0.0
        for cache in self._caches.values():
            total_memory += cache.get_memory_usage_mb()
        return total_memory

    def get_cache_names(self) -> list[str]:
        """Get list of all cache names.

        Returns:
            List of cache names
        """
        return list(self._caches.keys())

    def get_cache_count(self) -> int:
        """Get number of cache instances.

        Returns:
            Number of cache instances
        """
        return len(self._caches)

    def enable_all_caches(self) -> None:
        """Enable all cache instances."""
        for cache in self._caches.values():
            cache.enable()
        logger.info("Enabled all cache instances")

    def disable_all_caches(self) -> None:
        """Disable all cache instances."""
        for cache in self._caches.values():
            cache.disable()
        logger.info("Disabled all cache instances")

    def start_all_background_cleanup(self) -> None:
        """Start background cleanup for all cache instances."""
        for cache in self._caches.values():
            cache.start_background_cleanup()
        logger.info("Started background cleanup for all cache instances")

    def stop_all_background_cleanup(self) -> None:
        """Stop background cleanup for all cache instances."""
        for cache in self._caches.values():
            cache.stop_background_cleanup()
        logger.info("Stopped background cleanup for all cache instances")

    def get_combined_stats(self) -> dict[str, Any]:
        """Get combined statistics across all caches.

        Returns:
            Combined statistics
        """
        all_stats = self.get_all_stats()

        total_hits = sum(stats.hits for stats in all_stats.values())
        total_misses = sum(stats.misses for stats in all_stats.values())
        total_evictions = sum(stats.evictions for stats in all_stats.values())
        total_requests = sum(stats.total_requests for stats in all_stats.values())
        total_cache_size = sum(stats.cache_size for stats in all_stats.values())
        total_memory_usage = sum(stats.memory_usage_bytes for stats in all_stats.values())

        return {
            "total_caches": len(all_stats),
            "total_hits": total_hits,
            "total_misses": total_misses,
            "total_evictions": total_evictions,
            "total_requests": total_requests,
            "total_cache_size": total_cache_size,
            "total_memory_usage_bytes": total_memory_usage,
            "total_memory_usage_mb": total_memory_usage / (1024 * 1024),
            "overall_hit_rate": (total_hits / total_requests * 100) if total_requests > 0 else 0.0,
            "overall_miss_rate": (
                (total_misses / total_requests * 100) if total_requests > 0 else 0.0
            ),
            "cache_details": {
                name: {
                    "hits": stats.hits,
                    "misses": stats.misses,
                    "evictions": stats.evictions,
                    "cache_size": stats.cache_size,
                    "memory_usage_mb": stats.memory_usage_bytes / (1024 * 1024),
                    "hit_rate": stats.hit_rate,
                    "miss_rate": stats.miss_rate,
                }
                for name, stats in all_stats.items()
            },
        }

    def get_health_status(self) -> dict[str, Any]:
        """Get health status of all caches.

        Returns:
            Health status information
        """
        health_status = {
            "overall_status": "healthy",
            "cache_count": len(self._caches),
            "total_memory_usage_mb": self.get_total_memory_usage_mb(),
            "caches": {},
        }

        for name, cache in self._caches.items():
            cache_health = {
                "enabled": cache.is_enabled(),
                "cache_only_mode": cache.is_cache_only_mode(),
                "cache_only_reason": cache.get_cache_only_reason(),
                "memory_usage_mb": cache.get_memory_usage_mb(),
                "stats": cache.get_stats(),
            }

            # Determine cache health
            if not cache.is_enabled():
                cache_health["status"] = "disabled"
            elif cache.is_cache_only_mode():
                cache_health["status"] = "cache_only"
            else:
                cache_health["status"] = "healthy"

            health_status["caches"][name] = cache_health

        # Determine overall health
        if any(not cache.is_enabled() for cache in self._caches.values()):
            health_status["overall_status"] = "degraded"
        elif any(cache.is_cache_only_mode() for cache in self._caches.values()):
            health_status["overall_status"] = "cache_only"

        return health_status

    def __del__(self) -> None:
        """Cleanup when manager is destroyed."""
        self.stop_all_background_cleanup()
