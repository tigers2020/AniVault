"""Performance profiling system for cache-database synchronization operations.

This module provides comprehensive profiling capabilities to identify bottlenecks,
measure performance metrics, and analyze synchronization operations in the AniVault system.
"""

import json
import statistics
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import psutil

from .logging_utils import logger


class ProfilerEvent(Enum):
    """Types of profiler events."""

    CACHE_GET = "cache_get"
    CACHE_SET = "cache_set"
    CACHE_DELETE = "cache_delete"
    DB_QUERY = "db_query"
    DB_BULK_INSERT = "db_bulk_insert"
    DB_BULK_UPDATE = "db_bulk_update"
    DB_BULK_UPSERT = "db_bulk_upsert"
    SYNC_OPERATION = "sync_operation"
    TRANSACTION = "transaction"
    INCREMENTAL_SYNC = "incremental_sync"
    CONSISTENCY_CHECK = "consistency_check"
    RECONCILIATION = "reconciliation"


@dataclass
class PerformanceMetrics:
    """Performance metrics for a single operation."""

    event_type: ProfilerEvent
    operation_name: str
    start_time: float
    end_time: float
    duration_ms: float
    cpu_percent: float
    memory_mb: float
    memory_peak_mb: float
    thread_id: int
    operation_size: int | None = None  # Number of records, bytes, etc.
    success: bool = True
    error_message: str | None = None
    additional_context: dict[str, Any] = field(default_factory=dict)

    @property
    def throughput_per_sec(self) -> float:
        """Calculate throughput per second if operation size is known."""
        if self.operation_size and self.duration_ms > 0:
            return (self.operation_size * 1000) / self.duration_ms
        return 0.0


@dataclass
class ProfilerStats:
    """Aggregated statistics for profiling data."""

    total_operations: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0
    p50_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    success_rate: float = 0.0
    total_throughput_per_sec: float = 0.0
    avg_throughput_per_sec: float = 0.0
    total_cpu_percent: float = 0.0
    avg_cpu_percent: float = 0.0
    total_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    memory_peak_mb: float = 0.0

    def update(self, metrics: PerformanceMetrics) -> None:
        """Update statistics with a new metric."""
        self.total_operations += 1
        self.total_duration_ms += metrics.duration_ms

        if metrics.duration_ms < self.min_duration_ms:
            self.min_duration_ms = metrics.duration_ms
        if metrics.duration_ms > self.max_duration_ms:
            self.max_duration_ms = metrics.duration_ms

        self.total_throughput_per_sec += metrics.throughput_per_sec
        self.total_cpu_percent += metrics.cpu_percent
        self.total_memory_mb += metrics.memory_mb

        if metrics.memory_peak_mb > self.memory_peak_mb:
            self.memory_peak_mb = metrics.memory_peak_mb

    def finalize(self, durations: list[float], success_count: int) -> None:
        """Finalize statistics with percentile calculations."""
        if durations:
            self.avg_duration_ms = self.total_duration_ms / self.total_operations
            self.p50_duration_ms = statistics.median(durations)
            self.p95_duration_ms = (
                statistics.quantiles(durations, n=20)[18] if len(durations) > 1 else durations[0]
            )
            self.p99_duration_ms = (
                statistics.quantiles(durations, n=100)[98] if len(durations) > 1 else durations[0]
            )

        if self.total_operations > 0:
            self.success_rate = (success_count / self.total_operations) * 100
            self.avg_throughput_per_sec = self.total_throughput_per_sec / self.total_operations
            self.avg_cpu_percent = self.total_cpu_percent / self.total_operations
            self.avg_memory_mb = self.total_memory_mb / self.total_operations


class SyncProfiler:
    """Comprehensive profiler for synchronization operations."""

    def __init__(self, max_history: int = 10000):
        """Initialize the sync profiler.

        Args:
            max_history: Maximum number of metrics to keep in memory
        """
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.stats_by_event: dict[ProfilerEvent, ProfilerStats] = defaultdict(ProfilerStats)
        self.stats_by_operation: dict[str, ProfilerStats] = defaultdict(ProfilerStats)

        # Thread safety
        self._lock = threading.RLock()

        # Memory profiling
        self._memory_tracking_enabled = False
        self._memory_snapshots: list[tuple[float, float]] = []

        # CPU profiling
        self._process = psutil.Process()
        self._cpu_baseline = self._process.cpu_percent()

        # Performance targets
        self.performance_targets = {
            ProfilerEvent.CACHE_GET: {"max_duration_ms": 10, "min_throughput_per_sec": 1000},
            ProfilerEvent.CACHE_SET: {"max_duration_ms": 20, "min_throughput_per_sec": 500},
            ProfilerEvent.DB_BULK_INSERT: {"max_duration_ms": 1000, "min_throughput_per_sec": 1000},
            ProfilerEvent.DB_BULK_UPDATE: {"max_duration_ms": 1000, "min_throughput_per_sec": 1000},
            ProfilerEvent.DB_BULK_UPSERT: {"max_duration_ms": 1500, "min_throughput_per_sec": 800},
            ProfilerEvent.SYNC_OPERATION: {"max_duration_ms": 5000, "min_throughput_per_sec": 100},
            ProfilerEvent.INCREMENTAL_SYNC: {
                "max_duration_ms": 30000,
                "min_throughput_per_sec": 50,
            },
            ProfilerEvent.CONSISTENCY_CHECK: {
                "max_duration_ms": 10000,
                "min_throughput_per_sec": 10,
            },
        }

    def start_memory_tracking(self) -> None:
        """Start memory tracking for detailed analysis."""
        self._memory_tracking_enabled = True
        tracemalloc.start()
        logger.info("Memory tracking started")

    def stop_memory_tracking(self) -> None:
        """Stop memory tracking and get memory statistics."""
        if self._memory_tracking_enabled:
            tracemalloc.stop()
            self._memory_tracking_enabled = False
            logger.info("Memory tracking stopped")

    def get_memory_stats(self) -> dict[str, Any]:
        """Get current memory statistics."""
        memory_info = self._process.memory_info()
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": self._process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
        }

    def get_cpu_stats(self) -> dict[str, Any]:
        """Get current CPU statistics."""
        return {
            "cpu_percent": self._process.cpu_percent(),
            "cpu_count": psutil.cpu_count(),
            "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
        }

    @contextmanager
    def profile_operation(
        self,
        event_type: ProfilerEvent,
        operation_name: str,
        operation_size: int | None = None,
        additional_context: dict[str, Any] | None = None,
    ):
        """Context manager for profiling operations.

        Args:
            event_type: Type of operation being profiled
            operation_name: Name of the specific operation
            operation_size: Size of the operation (records, bytes, etc.)
            additional_context: Additional context information
        """
        start_time = time.time()
        start_cpu = self._process.cpu_percent()
        start_memory = self.get_memory_stats()

        # Get memory snapshot if tracking is enabled
        memory_snapshot = None
        if self._memory_tracking_enabled:
            memory_snapshot = tracemalloc.take_snapshot()

        success = True
        error_message = None
        additional_context = additional_context or {}

        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            end_time = time.time()
            end_cpu = self._process.cpu_percent()
            end_memory = self.get_memory_stats()

            duration_ms = (end_time - start_time) * 1000

            # Calculate memory peak if tracking is enabled
            memory_peak_mb = start_memory["rss_mb"]
            if memory_snapshot:
                memory_peak_mb = max(memory_peak_mb, end_memory["rss_mb"])

            # Create metrics
            metrics = PerformanceMetrics(
                event_type=event_type,
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                cpu_percent=(start_cpu + end_cpu) / 2,  # Average CPU usage
                memory_mb=end_memory["rss_mb"],
                memory_peak_mb=memory_peak_mb,
                thread_id=threading.get_ident(),
                operation_size=operation_size,
                success=success,
                error_message=error_message,
                additional_context=additional_context,
            )

            # Record metrics
            self.record_metrics(metrics)

    def record_metrics(self, metrics: PerformanceMetrics) -> None:
        """Record performance metrics.

        Args:
            metrics: Performance metrics to record
        """
        with self._lock:
            # Add to history
            self.metrics_history.append(metrics)

            # Update statistics
            self.stats_by_event[metrics.event_type].update(metrics)
            self.stats_by_operation[metrics.operation_name].update(metrics)

            # Log performance warnings
            self._check_performance_targets(metrics)

    def _check_performance_targets(self, metrics: PerformanceMetrics) -> None:
        """Check if metrics meet performance targets."""
        if metrics.event_type in self.performance_targets:
            targets = self.performance_targets[metrics.event_type]

            # Check duration target
            if metrics.duration_ms > targets.get("max_duration_ms", float("inf")):
                logger.warning(
                    f"Performance target exceeded for {metrics.event_type.value}: "
                    f"{metrics.duration_ms:.2f}ms > {targets['max_duration_ms']}ms "
                    f"(operation: {metrics.operation_name})"
                )

            # Check throughput target
            min_throughput = targets.get("min_throughput_per_sec", 0)
            if metrics.throughput_per_sec > 0 and metrics.throughput_per_sec < min_throughput:
                logger.warning(
                    f"Throughput target not met for {metrics.event_type.value}: "
                    f"{metrics.throughput_per_sec:.2f}/sec < {min_throughput}/sec "
                    f"(operation: {metrics.operation_name})"
                )

    def get_stats_by_event(self, event_type: ProfilerEvent) -> ProfilerStats:
        """Get statistics for a specific event type.

        Args:
            event_type: Event type to get statistics for

        Returns:
            Aggregated statistics for the event type
        """
        with self._lock:
            stats = self.stats_by_event[event_type]
            if stats.total_operations > 0:
                # Get durations for percentile calculations
                durations = [
                    m.duration_ms for m in self.metrics_history if m.event_type == event_type
                ]
                success_count = sum(
                    1 for m in self.metrics_history if m.event_type == event_type and m.success
                )
                stats.finalize(durations, success_count)
            return stats

    def get_stats_by_operation(self, operation_name: str) -> ProfilerStats:
        """Get statistics for a specific operation.

        Args:
            operation_name: Operation name to get statistics for

        Returns:
            Aggregated statistics for the operation
        """
        with self._lock:
            stats = self.stats_by_operation[operation_name]
            if stats.total_operations > 0:
                # Get durations for percentile calculations
                durations = [
                    m.duration_ms
                    for m in self.metrics_history
                    if m.operation_name == operation_name
                ]
                success_count = sum(
                    1
                    for m in self.metrics_history
                    if m.operation_name == operation_name and m.success
                )
                stats.finalize(durations, success_count)
            return stats

    def get_top_bottlenecks(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the top performance bottlenecks.

        Args:
            limit: Maximum number of bottlenecks to return

        Returns:
            List of bottlenecks sorted by duration
        """
        with self._lock:
            bottlenecks = []

            # Group by operation name and calculate averages
            operation_stats = defaultdict(list)
            for metrics in self.metrics_history:
                operation_stats[metrics.operation_name].append(metrics)

            for operation_name, metrics_list in operation_stats.items():
                if not metrics_list:
                    continue

                avg_duration = statistics.mean(m.duration_ms for m in metrics_list)
                max_duration = max(m.duration_ms for m in metrics_list)
                total_operations = len(metrics_list)
                success_rate = (sum(1 for m in metrics_list if m.success) / total_operations) * 100

                bottlenecks.append(
                    {
                        "operation_name": operation_name,
                        "event_type": metrics_list[0].event_type.value,
                        "avg_duration_ms": avg_duration,
                        "max_duration_ms": max_duration,
                        "total_operations": total_operations,
                        "success_rate": success_rate,
                        "avg_throughput_per_sec": (
                            statistics.mean(
                                m.throughput_per_sec
                                for m in metrics_list
                                if m.throughput_per_sec > 0
                            )
                            if any(m.throughput_per_sec > 0 for m in metrics_list)
                            else 0.0
                        ),
                    }
                )

            # Sort by average duration (descending)
            bottlenecks.sort(key=lambda x: x["avg_duration_ms"], reverse=True)
            return bottlenecks[:limit]

    def get_performance_summary(self) -> dict[str, Any]:
        """Get a comprehensive performance summary.

        Returns:
            Dictionary containing performance summary
        """
        with self._lock:
            summary = {
                "total_operations": len(self.metrics_history),
                "time_range": {
                    "start": (
                        min(m.start_time for m in self.metrics_history)
                        if self.metrics_history
                        else None
                    ),
                    "end": (
                        max(m.end_time for m in self.metrics_history)
                        if self.metrics_history
                        else None
                    ),
                },
                "overall_stats": {
                    "avg_duration_ms": (
                        statistics.mean(m.duration_ms for m in self.metrics_history)
                        if self.metrics_history
                        else 0
                    ),
                    "max_duration_ms": (
                        max(m.duration_ms for m in self.metrics_history)
                        if self.metrics_history
                        else 0
                    ),
                    "success_rate": (
                        (
                            sum(1 for m in self.metrics_history if m.success)
                            / len(self.metrics_history)
                            * 100
                        )
                        if self.metrics_history
                        else 0
                    ),
                },
                "event_type_stats": {},
                "operation_stats": {},
                "bottlenecks": self.get_top_bottlenecks(5),
                "system_stats": {
                    "memory": self.get_memory_stats(),
                    "cpu": self.get_cpu_stats(),
                },
            }

            # Add event type statistics
            for event_type in ProfilerEvent:
                stats = self.get_stats_by_event(event_type)
                if stats.total_operations > 0:
                    summary["event_type_stats"][event_type.value] = {
                        "total_operations": stats.total_operations,
                        "avg_duration_ms": stats.avg_duration_ms,
                        "max_duration_ms": stats.max_duration_ms,
                        "p95_duration_ms": stats.p95_duration_ms,
                        "success_rate": stats.success_rate,
                        "avg_throughput_per_sec": stats.avg_throughput_per_sec,
                    }

            # Add operation statistics (top 10)
            operation_stats = sorted(
                [
                    (name, self.get_stats_by_operation(name))
                    for name in self.stats_by_operation.keys()
                ],
                key=lambda x: x[1].total_operations,
                reverse=True,
            )[:10]

            for operation_name, stats in operation_stats:
                if stats.total_operations > 0:
                    summary["operation_stats"][operation_name] = {
                        "total_operations": stats.total_operations,
                        "avg_duration_ms": stats.avg_duration_ms,
                        "max_duration_ms": stats.max_duration_ms,
                        "p95_duration_ms": stats.p95_duration_ms,
                        "success_rate": stats.success_rate,
                        "avg_throughput_per_sec": stats.avg_throughput_per_sec,
                    }

            return summary

    def export_metrics(self, filepath: str) -> None:
        """Export metrics to a JSON file.

        Args:
            filepath: Path to export the metrics to
        """
        with self._lock:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "summary": self.get_performance_summary(),
                "raw_metrics": [
                    {
                        "event_type": m.event_type.value,
                        "operation_name": m.operation_name,
                        "start_time": m.start_time,
                        "end_time": m.end_time,
                        "duration_ms": m.duration_ms,
                        "cpu_percent": m.cpu_percent,
                        "memory_mb": m.memory_mb,
                        "memory_peak_mb": m.memory_peak_mb,
                        "thread_id": m.thread_id,
                        "operation_size": m.operation_size,
                        "success": m.success,
                        "error_message": m.error_message,
                        "additional_context": m.additional_context,
                    }
                    for m in self.metrics_history
                ],
            }

            with open(filepath, "w") as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Exported {len(self.metrics_history)} metrics to {filepath}")

    def clear_metrics(self) -> None:
        """Clear all recorded metrics."""
        with self._lock:
            self.metrics_history.clear()
            self.stats_by_event.clear()
            self.stats_by_operation.clear()
            logger.info("Cleared all performance metrics")


# Global profiler instance
_sync_profiler: SyncProfiler | None = None


def get_sync_profiler() -> SyncProfiler:
    """Get the global sync profiler instance.

    Returns:
        Global SyncProfiler instance
    """
    global _sync_profiler
    if _sync_profiler is None:
        _sync_profiler = SyncProfiler()
    return _sync_profiler


def profile_sync_operation(
    event_type: ProfilerEvent,
    operation_name: str,
    operation_size: int | None = None,
    additional_context: dict[str, Any] | None = None,
):
    """Decorator for profiling synchronization operations.

    Args:
        event_type: Type of operation being profiled
        operation_name: Name of the specific operation
        operation_size: Size of the operation (records, bytes, etc.)
        additional_context: Additional context information
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            profiler = get_sync_profiler()
            with profiler.profile_operation(
                event_type=event_type,
                operation_name=operation_name,
                operation_size=operation_size,
                additional_context=additional_context,
            ):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def profile_operation(
    event_type: ProfilerEvent,
    operation_name: str,
    operation_size: int | None = None,
    additional_context: dict[str, Any] | None = None,
):
    """Context manager for profiling operations.

    Args:
        event_type: Type of operation being profiled
        operation_name: Name of the specific operation
        operation_size: Size of the operation (records, bytes, etc.)
        additional_context: Additional context information
    """
    profiler = get_sync_profiler()
    return profiler.profile_operation(
        event_type=event_type,
        operation_name=operation_name,
        operation_size=operation_size,
        additional_context=additional_context,
    )
