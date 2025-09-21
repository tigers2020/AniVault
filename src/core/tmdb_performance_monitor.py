"""Performance monitoring utilities for TMDB client optimization.

This module provides tools to monitor and analyze the performance improvements
achieved through TMDB client optimization in parallel processing scenarios.
"""

import logging
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import psutil

from .tmdb_client import TMDBClient
from .tmdb_client_pool import ThreadLocalTMDBClient, TMDBClientPool

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for TMDB client operations."""

    # Timing metrics
    total_time: float = 0.0
    client_creation_time: float = 0.0
    api_call_time: float = 0.0

    # Memory metrics
    peak_memory_usage: int = 0
    memory_before: int = 0
    memory_after: int = 0

    # Client usage metrics
    clients_created: int = 0
    clients_reused: int = 0
    api_calls_made: int = 0

    # Thread metrics
    threads_used: int = 0
    concurrent_operations: int = 0

    # Error metrics
    errors_occurred: int = 0
    retry_attempts: int = 0

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def record_thread_usage(self, thread_count: int) -> None:
        """Record thread usage."""
        self.threads_used = max(self.threads_used, thread_count)

    def record_concurrent_operations(self, count: int) -> None:
        """Record concurrent operations."""
        self.concurrent_operations = max(self.concurrent_operations, count)


class TMDBPerformanceMonitor:
    """Monitor for tracking TMDB client performance metrics."""

    def __init__(self) -> None:
        """Initialize the performance monitor."""
        self._metrics_history: list[PerformanceMetrics] = []
        self._current_metrics: PerformanceMetrics | None = None
        self._start_time: float | None = None
        self._start_memory: int | None = None

    @contextmanager
    def monitor_operation(
        self, operation_name: str = "tmdb_operation"
    ) -> Generator[Any, None, None]:
        """Context manager for monitoring TMDB operations.

        Args:
            operation_name: Name of the operation being monitored

        Yields:
            PerformanceMetrics: Metrics object for the current operation
        """
        self._start_time = time.time()
        self._start_memory = psutil.Process().memory_info().rss

        self._current_metrics = PerformanceMetrics()
        self._current_metrics.memory_before = self._start_memory

        try:
            yield self._current_metrics
        finally:
            if self._current_metrics:
                self._current_metrics.total_time = time.time() - self._start_time
                self._current_metrics.memory_after = psutil.Process().memory_info().rss
                self._current_metrics.metadata["operation_name"] = operation_name

                self._metrics_history.append(self._current_metrics)

                logger.debug(
                    f"Operation '{operation_name}' completed in {self._current_metrics.total_time:.3f}s"
                )

    def record_client_creation(self, creation_time: float) -> None:
        """Record client creation time.

        Args:
            creation_time: Time taken to create a client
        """
        if self._current_metrics:
            self._current_metrics.client_creation_time += creation_time
            self._current_metrics.clients_created += 1

    def record_client_reuse(self) -> None:
        """Record client reuse."""
        if self._current_metrics:
            self._current_metrics.clients_reused += 1

    def record_api_call(self, call_time: float) -> None:
        """Record API call time.

        Args:
            call_time: Time taken for an API call
        """
        if self._current_metrics:
            self._current_metrics.api_call_time += call_time
            self._current_metrics.api_calls_made += 1

    def record_thread_usage(self, thread_count: int) -> None:
        """Record thread usage.

        Args:
            thread_count: Number of threads used
        """
        if self._current_metrics:
            self._current_metrics.threads_used = max(
                self._current_metrics.threads_used, thread_count
            )

    def record_concurrent_operations(self, count: int) -> None:
        """Record concurrent operations.

        Args:
            count: Number of concurrent operations
        """
        if self._current_metrics:
            self._current_metrics.concurrent_operations = max(
                self._current_metrics.concurrent_operations, count
            )

    def record_error(self) -> None:
        """Record an error occurrence."""
        if self._current_metrics:
            self._current_metrics.errors_occurred += 1

    def record_retry(self) -> None:
        """Record a retry attempt."""
        if self._current_metrics:
            self._current_metrics.retry_attempts += 1

    def get_latest_metrics(self) -> PerformanceMetrics | None:
        """Get the latest performance metrics.

        Returns:
            Latest PerformanceMetrics or None if no metrics available
        """
        return self._metrics_history[-1] if self._metrics_history else None

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get a summary of all performance metrics.

        Returns:
            Dictionary containing summary statistics
        """
        if not self._metrics_history:
            return {"message": "No metrics available"}

        total_operations = len(self._metrics_history)
        total_time = sum(m.total_time for m in self._metrics_history)
        avg_time = total_time / total_operations

        total_clients_created = sum(m.clients_created for m in self._metrics_history)
        total_clients_reused = sum(m.clients_reused for m in self._metrics_history)
        total_api_calls = sum(m.api_calls_made for m in self._metrics_history)

        memory_usage = [m.memory_after - m.memory_before for m in self._metrics_history]
        avg_memory_usage = sum(memory_usage) / len(memory_usage) if memory_usage else 0

        return {
            "total_operations": total_operations,
            "total_time": total_time,
            "average_time": avg_time,
            "total_clients_created": total_clients_created,
            "total_clients_reused": total_clients_reused,
            "total_api_calls": total_api_calls,
            "average_memory_usage": avg_memory_usage,
            "client_reuse_rate": (
                total_clients_reused / (total_clients_created + total_clients_reused)
                if (total_clients_created + total_clients_reused) > 0
                else 0.0
            ),
            "operations_per_second": total_operations / total_time if total_time > 0 else 0.0,
        }

    def clear_metrics(self) -> None:
        """Clear all stored metrics."""
        self._metrics_history.clear()
        self._current_metrics = None


class TMDBClientPoolMonitor:
    """Monitor for TMDB client pool performance."""

    def __init__(self, pool: TMDBClientPool) -> None:
        """Initialize the pool monitor.

        Args:
            pool: TMDBClientPool instance to monitor
        """
        self.pool = pool
        self._initial_stats = pool.get_pool_stats()
        self._monitoring_active = False

    def start_monitoring(self) -> None:
        """Start monitoring the pool."""
        self._monitoring_active = True
        logger.info("Started monitoring TMDB client pool")

    def stop_monitoring(self) -> None:
        """Stop monitoring the pool."""
        self._monitoring_active = False
        logger.info("Stopped monitoring TMDB client pool")

    def get_performance_report(self) -> dict[str, Any]:
        """Get a comprehensive performance report.

        Returns:
            Dictionary containing performance report
        """
        if not self._monitoring_active:
            return {"error": "Monitoring not active"}

        current_stats = self.pool.get_pool_stats()
        health_check = self.pool.health_check()

        # Calculate performance improvements
        pool_hit_rate = current_stats.get("pool_hit_rate", 0.0)
        utilization_rate = current_stats.get("utilization_rate", 0.0)

        return {
            "pool_performance": {
                "pool_hit_rate": pool_hit_rate,
                "utilization_rate": utilization_rate,
                "total_requests": current_stats.get("total_requests", 0),
                "pool_hits": current_stats.get("pool_hits", 0),
                "pool_misses": current_stats.get("pool_misses", 0),
                "clients_created": current_stats.get("clients_created", 0),
            },
            "pool_health": health_check,
            "efficiency_metrics": {
                "pool_efficiency": pool_hit_rate,
                "resource_utilization": utilization_rate,
                "client_reuse_effectiveness": (
                    current_stats.get("pool_hits", 0) / current_stats.get("total_requests", 1)
                ),
            },
            "recommendations": self._generate_recommendations(current_stats, health_check),
        }

    def _generate_recommendations(self, stats: dict[str, Any], health: dict[str, Any]) -> list[str]:
        """Generate performance recommendations based on stats and health.

        Args:
            stats: Pool statistics
            health: Pool health check results

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Check pool hit rate
        pool_hit_rate = stats.get("pool_hit_rate", 0.0)
        if pool_hit_rate < 0.7:
            recommendations.append(
                "Low pool hit rate detected. Consider increasing pool size or "
                "checking for client release issues."
            )

        # Check utilization rate
        utilization_rate = stats.get("utilization_rate", 0.0)
        if utilization_rate > 0.9:
            recommendations.append("High pool utilization detected. Consider increasing pool size.")
        elif utilization_rate < 0.3:
            recommendations.append("Low pool utilization detected. Consider reducing pool size.")

        # Check health issues
        if not health.get("healthy", True):
            issues = health.get("issues", [])
            recommendations.extend([f"Health issue: {issue}" for issue in issues])

        return recommendations


def benchmark_tmdb_approaches(
    config: Any, num_operations: int = 100, num_threads: int = 4, mock_api_calls: bool = True
) -> dict[str, Any]:
    """Benchmark different TMDB client approaches.

    Args:
        config: TMDBConfig instance
        num_operations: Number of operations to perform
        num_threads: Number of threads to use
        mock_api_calls: Whether to mock API calls for testing

    Returns:
        Dictionary containing benchmark results
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}

    def traditional_approach() -> dict[str, Any]:
        """Traditional approach: create new client for each operation."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss

        clients_created = 0

        def worker() -> None:
            nonlocal clients_created
            for _ in range(num_operations // num_threads):
                if mock_api_calls:
                    with patch.object(TMDBClient, "__init__", return_value=None):
                        TMDBClient(config)
                        clients_created += 1
                        time.sleep(0.001)  # Simulate API call
                else:
                    TMDBClient(config)
                    clients_created += 1
                    time.sleep(0.001)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss

        return {
            "time": end_time - start_time,
            "memory_usage": end_memory - start_memory,
            "clients_created": clients_created,
            "approach": "traditional",
        }

    def optimized_approach() -> dict[str, Any]:
        """Optimized approach: use thread-local client."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss

        thread_local_manager = ThreadLocalTMDBClient(config)

        def worker() -> None:
            for _ in range(num_operations // num_threads):
                if mock_api_calls:
                    with patch.object(TMDBClient, "__init__", return_value=None):
                        thread_local_manager.get_client()
                        time.sleep(0.001)  # Simulate API call
                else:
                    thread_local_manager.get_client()
                    time.sleep(0.001)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        stats = thread_local_manager.get_stats()

        return {
            "time": end_time - start_time,
            "memory_usage": end_memory - start_memory,
            "clients_created": stats["clients_created"],
            "approach": "optimized",
        }

    # Run benchmarks
    results["traditional"] = traditional_approach()
    results["optimized"] = optimized_approach()

    # Calculate improvements
    traditional = results["traditional"]
    optimized = results["optimized"]

    time_improvement = (traditional["time"] - optimized["time"]) / traditional["time"] * 100
    memory_improvement = (
        (traditional["memory_usage"] - optimized["memory_usage"])
        / traditional["memory_usage"]
        * 100
    )

    results["improvements"] = {
        "time_improvement_percent": time_improvement,
        "memory_improvement_percent": memory_improvement,
        "client_creation_reduction": traditional["clients_created"] - optimized["clients_created"],
    }

    return results


# Global performance monitor instance
_performance_monitor: TMDBPerformanceMonitor | None = None


def get_performance_monitor() -> TMDBPerformanceMonitor:
    """Get the global performance monitor instance.

    Returns:
        TMDBPerformanceMonitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = TMDBPerformanceMonitor()
    return _performance_monitor


def reset_performance_monitor() -> None:
    """Reset the global performance monitor."""
    global _performance_monitor
    if _performance_monitor is not None:
        _performance_monitor.clear_metrics()
        _performance_monitor = None


# Context manager for easy monitoring
@contextmanager
def monitor_tmdb_operation(operation_name: str = "tmdb_operation") -> Generator[Any, None, None]:
    """Context manager for monitoring TMDB operations.

    Args:
        operation_name: Name of the operation

    Yields:
        PerformanceMetrics: Metrics object for the operation
    """
    monitor = get_performance_monitor()
    with monitor.monitor_operation(operation_name) as metrics:
        yield metrics
