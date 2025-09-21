"""Prometheus metrics exporter for cache performance monitoring.

This module provides Prometheus metrics for cache hit/miss tracking,
enabling real-time monitoring and alerting for cache performance.
"""

import logging
from typing import Any

from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest
from prometheus_client.core import GaugeMetricFamily

from .cache_tracker import CacheMetrics, get_all_cache_metrics

logger = logging.getLogger(__name__)


# Prometheus metrics - use try/except to handle duplicate registration
def _safe_create_counter(name, description, labelnames):
    """Safely create counter, handling duplicate registration."""
    try:
        return Counter(name, description, labelnames)
    except ValueError as e:
        if "Duplicated timeseries" in str(e):
            # Return a dummy counter if already registered

            class DummyCounter:
                def __init__(self, name, description, labelnames):
                    self._name = name
                    self._description = description
                    self._labelnames = labelnames

                def labels(self, **kwargs):
                    return self

                def inc(self, amount=1):
                    pass

            return DummyCounter(name, description, labelnames)
        else:
            raise


CACHE_HITS_TOTAL = _safe_create_counter(
    "cache_hits_total", "Total number of cache hits", ["cache_name"]
)

CACHE_MISSES_TOTAL = _safe_create_counter(
    "cache_misses_total", "Total number of cache misses", ["cache_name"]
)

CACHE_REQUESTS_TOTAL = _safe_create_counter(
    "cache_requests_total", "Total number of cache requests", ["cache_name"]
)

CACHE_EVICTIONS_TOTAL = _safe_create_counter(
    "cache_evictions_total", "Total number of cache evictions", ["cache_name"]
)


def _safe_create_gauge(name, description, labelnames):
    """Safely create gauge, handling duplicate registration."""
    try:
        return Gauge(name, description, labelnames)
    except ValueError as e:
        if "Duplicated timeseries" in str(e):
            # Return a dummy gauge if already registered
            class DummyGauge:
                def __init__(self, name, description, labelnames):
                    self._name = name
                    self._description = description
                    self._labelnames = labelnames

                def labels(self, **kwargs):
                    return self

                def set(self, value):
                    pass

                def inc(self, amount=1):
                    pass

                def dec(self, amount=1):
                    pass

            return DummyGauge(name, description, labelnames)
        else:
            raise


CACHE_SIZE = _safe_create_gauge("cache_size", "Current number of items in cache", ["cache_name"])

CACHE_MEMORY_USAGE_BYTES = _safe_create_gauge(
    "cache_memory_usage_bytes", "Current memory usage of cache in bytes", ["cache_name"]
)

CACHE_HIT_RATE = _safe_create_gauge(
    "cache_hit_rate_percent", "Cache hit rate as a percentage", ["cache_name"]
)

CACHE_MISS_RATE = _safe_create_gauge(
    "cache_miss_rate_percent", "Cache miss rate as a percentage", ["cache_name"]
)


class CacheMetricsCollector:
    """Custom Prometheus collector for cache metrics from Redis."""

    def __init__(self, cache_trackers: dict[str, Any] = None):
        """Initialize the cache metrics collector.

        Args:
            cache_trackers: Dictionary of cache tracker instances
        """
        self.cache_trackers = cache_trackers or {}

    def collect(self):
        """Collect metrics from all cache trackers."""
        try:
            # Get metrics from all caches
            all_metrics = get_all_cache_metrics()

            for cache_name, metrics in all_metrics.items():
                # Create gauge metrics for current values
                yield GaugeMetricFamily(
                    "cache_hits_total",
                    "Total number of cache hits",
                    value=metrics.hits,
                    labels=[cache_name],
                )

                yield GaugeMetricFamily(
                    "cache_misses_total",
                    "Total number of cache misses",
                    value=metrics.misses,
                    labels=[cache_name],
                )

                yield GaugeMetricFamily(
                    "cache_requests_total",
                    "Total number of cache requests",
                    value=metrics.total_requests,
                    labels=[cache_name],
                )

                yield GaugeMetricFamily(
                    "cache_evictions_total",
                    "Total number of cache evictions",
                    value=metrics.evictions,
                    labels=[cache_name],
                )

                yield GaugeMetricFamily(
                    "cache_hit_rate_percent",
                    "Cache hit rate as a percentage",
                    value=metrics.hit_rate,
                    labels=[cache_name],
                )

                yield GaugeMetricFamily(
                    "cache_miss_rate_percent",
                    "Cache miss rate as a percentage",
                    value=metrics.miss_rate,
                    labels=[cache_name],
                )

        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")


class CacheMetricsExporter:
    """High-performance cache metrics exporter for Prometheus."""

    def __init__(self, registry: CollectorRegistry = None):
        """Initialize the cache metrics exporter.

        Args:
            registry: Prometheus registry to use (defaults to default registry)
        """
        self.registry = registry or CollectorRegistry()
        self.collector = CacheMetricsCollector()

        # Register the custom collector
        self.registry.register(self.collector)

        # Register standard metrics
        self.registry.register(CACHE_HITS_TOTAL)
        self.registry.register(CACHE_MISSES_TOTAL)
        self.registry.register(CACHE_REQUESTS_TOTAL)
        self.registry.register(CACHE_EVICTIONS_TOTAL)
        self.registry.register(CACHE_SIZE)
        self.registry.register(CACHE_MEMORY_USAGE_BYTES)
        self.registry.register(CACHE_HIT_RATE)
        self.registry.register(CACHE_MISS_RATE)

    def update_metrics(self, cache_name: str, metrics: CacheMetrics) -> None:
        """Update Prometheus metrics for a specific cache.

        Args:
            cache_name: Name of the cache
            metrics: Cache metrics to update
        """
        try:
            # Update counter metrics (these are cumulative)
            CACHE_HITS_TOTAL.labels(cache_name=cache_name)._value._value = metrics.hits
            CACHE_MISSES_TOTAL.labels(cache_name=cache_name)._value._value = metrics.misses
            CACHE_REQUESTS_TOTAL.labels(cache_name=cache_name)._value._value = (
                metrics.total_requests
            )
            CACHE_EVICTIONS_TOTAL.labels(cache_name=cache_name)._value._value = metrics.evictions

            # Update gauge metrics (these are current values)
            CACHE_HIT_RATE.labels(cache_name=cache_name).set(metrics.hit_rate)
            CACHE_MISS_RATE.labels(cache_name=cache_name).set(metrics.miss_rate)

        except Exception as e:
            logger.warning(f"Failed to update metrics for {cache_name}: {e}")

    def update_cache_size(self, cache_name: str, size: int) -> None:
        """Update cache size metric.

        Args:
            cache_name: Name of the cache
            size: Current cache size
        """
        try:
            CACHE_SIZE.labels(cache_name=cache_name).set(size)
        except Exception as e:
            logger.warning(f"Failed to update cache size for {cache_name}: {e}")

    def update_memory_usage(self, cache_name: str, memory_bytes: int) -> None:
        """Update memory usage metric.

        Args:
            cache_name: Name of the cache
            memory_bytes: Current memory usage in bytes
        """
        try:
            CACHE_MEMORY_USAGE_BYTES.labels(cache_name=cache_name).set(memory_bytes)
        except Exception as e:
            logger.warning(f"Failed to update memory usage for {cache_name}: {e}")

    def generate_metrics(self) -> str:
        """Generate Prometheus metrics in text format.

        Returns:
            Prometheus metrics in text format
        """
        try:
            metrics_bytes = generate_latest(self.registry)
            return (
                metrics_bytes.decode("utf-8") if isinstance(metrics_bytes, bytes) else metrics_bytes
            )
        except Exception as e:
            logger.error(f"Failed to generate metrics: {e}")
            return ""

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get a summary of current cache metrics.

        Returns:
            Dictionary containing metrics summary
        """
        try:
            all_metrics = get_all_cache_metrics()
            summary = {}

            for cache_name, metrics in all_metrics.items():
                summary[cache_name] = {
                    "hits": metrics.hits,
                    "misses": metrics.misses,
                    "total_requests": metrics.total_requests,
                    "evictions": metrics.evictions,
                    "hit_rate": metrics.hit_rate,
                    "miss_rate": metrics.miss_rate,
                    "last_updated": metrics.last_updated,
                }

            return summary
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}


# Global metrics exporter instance
_metrics_exporter: CacheMetricsExporter = None


def get_metrics_exporter() -> CacheMetricsExporter:
    """Get the global cache metrics exporter instance.

    Returns:
        CacheMetricsExporter instance
    """
    global _metrics_exporter
    if _metrics_exporter is None:
        _metrics_exporter = CacheMetricsExporter()
    return _metrics_exporter


def update_cache_metrics(cache_name: str, metrics: CacheMetrics) -> None:
    """Update metrics for a specific cache.

    Args:
        cache_name: Name of the cache
        metrics: Cache metrics to update
    """
    exporter = get_metrics_exporter()
    exporter.update_metrics(cache_name, metrics)


def update_cache_size(cache_name: str, size: int) -> None:
    """Update cache size metric.

    Args:
        cache_name: Name of the cache
        size: Current cache size
    """
    exporter = get_metrics_exporter()
    exporter.update_cache_size(cache_name, size)


def update_memory_usage(cache_name: str, memory_bytes: int) -> None:
    """Update memory usage metric.

    Args:
        cache_name: Name of the cache
        memory_bytes: Current memory usage in bytes
    """
    exporter = get_metrics_exporter()
    exporter.update_memory_usage(cache_name, memory_bytes)


def generate_metrics() -> str:
    """Generate Prometheus metrics in text format.

    Returns:
        Prometheus metrics in text format
    """
    exporter = get_metrics_exporter()
    return exporter.generate_metrics()


def get_metrics_summary() -> dict[str, Any]:
    """Get a summary of current cache metrics.

    Returns:
        Dictionary containing metrics summary
    """
    exporter = get_metrics_exporter()
    return exporter.get_metrics_summary()
