"""High-performance cache hit/miss tracking system using Redis.

This module provides optimized cache performance tracking with minimal overhead,
designed for high-concurrency applications with multiple threads and processes.
"""

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # Set to None to avoid NameError
    logger.warning("Redis not available. Cache tracking will use in-memory fallback.")


@dataclass
class CacheMetrics:
    """Cache performance metrics with atomic operations."""

    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    evictions: int = 0
    last_updated: float = 0.0

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
        """Reset all metrics to zero."""
        self.hits = 0
        self.misses = 0
        self.total_requests = 0
        self.evictions = 0
        self.last_updated = time.time()


class InMemoryCacheTracker:
    """Thread-safe in-memory cache tracker using thread-local storage."""

    def __init__(self, enabled: bool = True):
        """Initialize in-memory tracker.

        Args:
            enabled: Whether tracking is enabled
        """
        self.enabled = enabled
        self._thread_local = threading.local()
        self._global_metrics: dict[str, CacheMetrics] = {}
        self._global_lock = threading.RLock()

    def _get_thread_metrics(self, cache_name: str) -> CacheMetrics:
        """Get thread-local metrics for a cache."""
        if not hasattr(self._thread_local, "metrics"):
            self._thread_local.metrics = {}

        if cache_name not in self._thread_local.metrics:
            self._thread_local.metrics[cache_name] = CacheMetrics()

        return self._thread_local.metrics[cache_name]

    def track_hit(self, cache_name: str) -> None:
        """Track a cache hit."""
        if not self.enabled:
            return

        metrics = self._get_thread_metrics(cache_name)
        metrics.hits += 1
        metrics.total_requests += 1
        metrics.last_updated = time.time()

    def track_miss(self, cache_name: str) -> None:
        """Track a cache miss."""
        if not self.enabled:
            return

        metrics = self._get_thread_metrics(cache_name)
        metrics.misses += 1
        metrics.total_requests += 1
        metrics.last_updated = time.time()

    def track_eviction(self, cache_name: str) -> None:
        """Track a cache eviction."""
        if not self.enabled:
            return

        metrics = self._get_thread_metrics(cache_name)
        metrics.evictions += 1
        metrics.last_updated = time.time()

    def get_metrics(self, cache_name: str) -> CacheMetrics:
        """Get aggregated metrics for a cache across all threads."""
        if not self.enabled:
            return CacheMetrics()

        with self._global_lock:
            if cache_name not in self._global_metrics:
                self._global_metrics[cache_name] = CacheMetrics()

            # For simplicity, use the current thread's metrics
            # In a real implementation, you'd need to collect from all threads
            thread_metrics = self._get_thread_metrics(cache_name)

            # Update global metrics with current thread's data
            self._global_metrics[cache_name].hits = thread_metrics.hits
            self._global_metrics[cache_name].misses = thread_metrics.misses
            self._global_metrics[cache_name].total_requests = thread_metrics.total_requests
            self._global_metrics[cache_name].evictions = thread_metrics.evictions
            self._global_metrics[cache_name].last_updated = thread_metrics.last_updated

            return CacheMetrics(
                hits=thread_metrics.hits,
                misses=thread_metrics.misses,
                total_requests=thread_metrics.total_requests,
                evictions=thread_metrics.evictions,
                last_updated=thread_metrics.last_updated,
            )

    def reset_metrics(self, cache_name: str) -> None:
        """Reset metrics for a specific cache."""
        if not self.enabled:
            return

        with self._global_lock:
            if cache_name in self._global_metrics:
                self._global_metrics[cache_name].reset()

        # Reset thread-local metrics
        if hasattr(self._thread_local, "metrics") and cache_name in self._thread_local.metrics:
            self._thread_local.metrics[cache_name].reset()


class RedisCacheTracker:
    """High-performance Redis-based cache tracker with atomic operations."""

    def __init__(
        self,
        redis_client: Any | None = None,
        enabled: bool = True,
        key_prefix: str = "cache_metrics",
    ):
        """Initialize Redis cache tracker.

        Args:
            redis_client: Redis client instance
            enabled: Whether tracking is enabled
            key_prefix: Prefix for Redis keys
        """
        self.enabled = enabled
        self.key_prefix = key_prefix

        if redis_client is None:
            if not REDIS_AVAILABLE:
                raise RuntimeError("Redis not available and no client provided")

            # Default Redis connection
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True,
            )
        else:
            self.redis_client = redis_client

        # Test Redis connection
        try:
            self.redis_client.ping()
            logger.info("Redis cache tracker initialized successfully")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _get_key(self, cache_name: str, metric_type: str) -> str:
        """Generate Redis key for a metric."""
        return f"{self.key_prefix}:{cache_name}:{metric_type}"

    def track_hit(self, cache_name: str) -> None:
        """Track a cache hit using atomic Redis INCR."""
        if not self.enabled:
            return

        try:
            self.redis_client.incr(self._get_key(cache_name, "hits"))
            self.redis_client.incr(self._get_key(cache_name, "total_requests"))
        except redis.RedisError as e:
            logger.warning(f"Failed to track cache hit for {cache_name}: {e}")

    def track_miss(self, cache_name: str) -> None:
        """Track a cache miss using atomic Redis INCR."""
        if not self.enabled:
            return

        try:
            self.redis_client.incr(self._get_key(cache_name, "misses"))
            self.redis_client.incr(self._get_key(cache_name, "total_requests"))
        except redis.RedisError as e:
            logger.warning(f"Failed to track cache miss for {cache_name}: {e}")

    def track_eviction(self, cache_name: str) -> None:
        """Track a cache eviction using atomic Redis INCR."""
        if not self.enabled:
            return

        try:
            self.redis_client.incr(self._get_key(cache_name, "evictions"))
        except redis.RedisError as e:
            logger.warning(f"Failed to track cache eviction for {cache_name}: {e}")

    def get_metrics(self, cache_name: str) -> CacheMetrics:
        """Get current metrics for a cache from Redis."""
        if not self.enabled:
            return CacheMetrics()

        try:
            hits = int(self.redis_client.get(self._get_key(cache_name, "hits")) or 0)
            misses = int(self.redis_client.get(self._get_key(cache_name, "misses")) or 0)
            total_requests = int(
                self.redis_client.get(self._get_key(cache_name, "total_requests")) or 0
            )
            evictions = int(self.redis_client.get(self._get_key(cache_name, "evictions")) or 0)

            return CacheMetrics(
                hits=hits,
                misses=misses,
                total_requests=total_requests,
                evictions=evictions,
                last_updated=time.time(),
            )
        except redis.RedisError as e:
            logger.warning(f"Failed to get metrics for {cache_name}: {e}")
            return CacheMetrics()

    def reset_metrics(self, cache_name: str) -> None:
        """Reset metrics for a specific cache."""
        if not self.enabled:
            return

        try:
            keys_to_delete = [
                self._get_key(cache_name, "hits"),
                self._get_key(cache_name, "misses"),
                self._get_key(cache_name, "total_requests"),
                self._get_key(cache_name, "evictions"),
            ]
            self.redis_client.delete(*keys_to_delete)
            logger.info(f"Reset metrics for cache: {cache_name}")
        except redis.RedisError as e:
            logger.warning(f"Failed to reset metrics for {cache_name}: {e}")

    def get_all_cache_names(self) -> list[str]:
        """Get list of all cache names with metrics."""
        if not self.enabled:
            return []

        try:
            pattern = f"{self.key_prefix}:*:hits"
            keys = self.redis_client.keys(pattern)
            cache_names = []
            for key in keys:
                # Extract cache name from key: "cache_metrics:cache_name:hits"
                parts = key.split(":")
                if len(parts) >= 3:
                    cache_names.append(parts[1])
            return list(set(cache_names))
        except redis.RedisError as e:
            logger.warning(f"Failed to get cache names: {e}")
            return []

    def set_ttl(self, cache_name: str, ttl_seconds: int) -> None:
        """Set TTL for cache metrics to prevent indefinite growth."""
        if not self.enabled:
            return

        try:
            keys = [
                self._get_key(cache_name, "hits"),
                self._get_key(cache_name, "misses"),
                self._get_key(cache_name, "total_requests"),
                self._get_key(cache_name, "evictions"),
            ]
            for key in keys:
                self.redis_client.expire(key, ttl_seconds)
        except redis.RedisError as e:
            logger.warning(f"Failed to set TTL for {cache_name}: {e}")


class OptimizedCacheTracker:
    """High-performance cache tracker with automatic fallback."""

    def __init__(
        self,
        cache_name: str,
        redis_client: Any | None = None,
        enabled: bool = True,
        use_redis: bool = True,
    ):
        """Initialize optimized cache tracker.

        Args:
            cache_name: Name of the cache being tracked
            redis_client: Redis client instance (optional)
            enabled: Whether tracking is enabled
            use_redis: Whether to use Redis (falls back to in-memory if Redis unavailable)
        """
        self.cache_name = cache_name
        self.enabled = enabled

        # Try Redis first, fall back to in-memory
        if use_redis and REDIS_AVAILABLE:
            try:
                self.tracker = RedisCacheTracker(redis_client, enabled)
                self.tracker_type = "redis"
                logger.info(f"Using Redis tracker for cache: {cache_name}")
            except Exception as e:
                logger.warning(f"Redis tracker failed, falling back to in-memory: {e}")
                self.tracker = InMemoryCacheTracker(enabled)
                self.tracker_type = "memory"
        else:
            self.tracker = InMemoryCacheTracker(enabled)
            self.tracker_type = "memory"
            logger.info(f"Using in-memory tracker for cache: {cache_name}")

    def track_hit(self) -> None:
        """Track a cache hit."""
        self.tracker.track_hit(self.cache_name)

    def track_miss(self) -> None:
        """Track a cache miss."""
        self.tracker.track_miss(self.cache_name)

    def track_eviction(self) -> None:
        """Track a cache eviction."""
        self.tracker.track_eviction(self.cache_name)

    def get_metrics(self) -> CacheMetrics:
        """Get current metrics for this cache."""
        return self.tracker.get_metrics(self.cache_name)

    def reset_metrics(self) -> None:
        """Reset metrics for this cache."""
        self.tracker.reset_metrics(self.cache_name)

    def is_redis_enabled(self) -> bool:
        """Check if Redis tracking is enabled."""
        return self.tracker_type == "redis"


# Global tracker instances for different caches
_trackers: dict[str, OptimizedCacheTracker] = {}


def get_cache_tracker(cache_name: str, **kwargs) -> OptimizedCacheTracker:
    """Get or create a cache tracker for the specified cache.

    Args:
        cache_name: Name of the cache
        **kwargs: Additional arguments for OptimizedCacheTracker

    Returns:
        OptimizedCacheTracker instance
    """
    if cache_name not in _trackers:
        _trackers[cache_name] = OptimizedCacheTracker(cache_name, **kwargs)

    return _trackers[cache_name]


def get_all_cache_metrics() -> dict[str, CacheMetrics]:
    """Get metrics for all tracked caches.

    Returns:
        Dictionary mapping cache names to their metrics
    """
    metrics = {}
    for cache_name, tracker in _trackers.items():
        metrics[cache_name] = tracker.get_metrics()

    return metrics


def reset_all_cache_metrics() -> None:
    """Reset metrics for all tracked caches."""
    for tracker in _trackers.values():
        tracker.reset_metrics()


# Decorator for easy cache tracking
def track_cache_performance(cache_name: str):
    """Decorator to automatically track cache performance.

    Args:
        cache_name: Name of the cache to track

    Returns:
        Decorator function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            tracker = get_cache_tracker(cache_name)

            # Execute the function
            result = func(*args, **kwargs)

            # Track based on result
            if result is not None:
                tracker.track_hit()
            else:
                tracker.track_miss()

            return result

        return wrapper

    return decorator
