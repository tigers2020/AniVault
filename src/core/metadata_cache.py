"""
Metadata caching system for AniVault application.

This module provides an in-memory cache system for storing and retrieving
anime metadata (ParsedAnimeInfo and TMDBAnime) with LRU eviction policy,
statistics tracking, and thread-safe operations.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from .models import ParsedAnimeInfo, TMDBAnime


@dataclass
class CacheStats:
    """Statistics for cache performance monitoring."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0
    cache_size: int = 0
    memory_usage_bytes: int = 0

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

    def reset(self) -> None:
        """Reset all statistics to zero."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_requests = 0
        self.cache_size = 0
        self.memory_usage_bytes = 0


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata."""

    key: str
    value: ParsedAnimeInfo | TMDBAnime
    created_at: float
    last_accessed: float
    access_count: int = 0
    size_bytes: int = 0

    def update_access(self) -> None:
        """Update access statistics."""
        self.last_accessed = time.time()
        self.access_count += 1


class MetadataCache:
    """
    Thread-safe in-memory cache for anime metadata with LRU eviction policy.

    This cache provides fast access to frequently used metadata while
    managing memory usage through configurable size limits and LRU eviction.
    """

    def __init__(
        self, max_size: int = 1000, max_memory_mb: int = 100, ttl_seconds: int | None = None
    ) -> None:
        """
        Initialize the metadata cache.

        Args:
            max_size: Maximum number of entries in the cache
            max_memory_mb: Maximum memory usage in megabytes
            ttl_seconds: Time-to-live for cache entries (None for no expiration)
        """
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.ttl_seconds = ttl_seconds

        # Thread-safe cache storage using OrderedDict for LRU behavior
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # Statistics tracking
        self._stats = CacheStats()

        # Memory usage tracking
        self._current_memory_bytes = 0

        # Cache configuration
        self._enabled = True
        self._auto_cleanup = True
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

    def get(
        self, key: str, default: ParsedAnimeInfo | TMDBAnime | None = None
    ) -> ParsedAnimeInfo | TMDBAnime | None:
        """
        Retrieve a value from the cache.

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

            if key not in self._cache:
                self._stats.misses += 1
                return default

            entry = self._cache[key]

            # Check TTL expiration
            if self.ttl_seconds and (time.time() - entry.created_at) > self.ttl_seconds:
                self._remove_entry(key)
                self._stats.misses += 1
                return default

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.update_access()

            self._stats.hits += 1
            self._stats.cache_size = len(self._cache)

            return entry.value

    def put(self, key: str, value: ParsedAnimeInfo | TMDBAnime) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        if not self._enabled:
            return

        with self._lock:
            # Calculate entry size
            entry_size = self._calculate_entry_size(key, value)

            # Remove existing entry if it exists
            if key in self._cache:
                self._remove_entry(key)

            # Check if we need to evict entries
            self._ensure_capacity(entry_size)

            # Create new entry
            now = time.time()
            entry = CacheEntry(
                key=key, value=value, created_at=now, last_accessed=now, size_bytes=entry_size
            )

            # Add to cache
            self._cache[key] = entry
            self._current_memory_bytes += entry_size

            # Update statistics
            self._stats.cache_size = len(self._cache)
            self._stats.memory_usage_bytes = self._current_memory_bytes

            # Perform cleanup if needed
            if self._auto_cleanup and self._should_cleanup():
                self._cleanup_expired_entries()

    def delete(self, key: str) -> bool:
        """
        Remove a value from the cache.

        Args:
            key: Cache key to remove

        Returns:
            True if key was found and removed, False otherwise
        """
        with self._lock:
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
        """
        Remove all entries matching a pattern.

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
            # Update current stats
            self._stats.cache_size = len(self._cache)
            self._stats.memory_usage_bytes = self._current_memory_bytes
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                total_requests=self._stats.total_requests,
                cache_size=self._stats.cache_size,
                memory_usage_bytes=self._stats.memory_usage_bytes,
            )

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self._stats.reset()

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

    def get_entries_info(self) -> list[dict[str, Any]]:
        """
        Get information about all cache entries.

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

    def _remove_entry(self, key: str) -> None:
        """Remove an entry from the cache."""
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
        elif isinstance(value, TMDBAnime):
            value_size = self._calculate_tmdb_anime_size(value)
        else:
            value_size = 200  # Default estimate

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
            key, entry = self._cache.popitem(last=False)
            self._current_memory_bytes -= entry.size_bytes
            self._stats.evictions += 1

    def _should_cleanup(self) -> bool:
        """Check if cleanup should be performed."""
        return (time.time() - self._last_cleanup) > self._cleanup_interval

    def _cleanup_expired_entries(self) -> None:
        """Remove expired entries from the cache."""
        if not self.ttl_seconds:
            return

        current_time = time.time()
        expired_keys = []

        for key, entry in self._cache.items():
            if (current_time - entry.created_at) > self.ttl_seconds:
                expired_keys.append(key)

        for key in expired_keys:
            self._remove_entry(key)

        self._last_cleanup = current_time


class MetadataCacheManager:
    """
    Manager for multiple metadata caches with different purposes.

    This class provides a unified interface for managing separate caches
    for different types of metadata (parsed info, TMDB data, etc.).
    """

    def __init__(self) -> None:
        """Initialize the cache manager."""
        self._caches: dict[str, MetadataCache] = {}
        self._lock = threading.RLock()

    def get_cache(self, name: str) -> MetadataCache:
        """
        Get or create a cache with the specified name.

        Args:
            name: Cache name

        Returns:
            MetadataCache instance
        """
        with self._lock:
            if name not in self._caches:
                self._caches[name] = MetadataCache()
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
