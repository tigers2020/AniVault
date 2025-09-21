"""Comprehensive monitoring and logging for cache-DB synchronization operations.

This module provides detailed logging, performance metrics collection, and monitoring
capabilities for all cache-DB synchronization operations in the AniVault system.
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .logging_utils import logger
from .sync_enums import SyncOperationStatus, SyncOperationType


@dataclass
class SyncOperationMetrics:
    """Metrics for a single synchronization operation."""

    operation_id: str
    operation_type: SyncOperationType
    status: SyncOperationStatus
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float | None = None
    affected_records: int = 0
    cache_hit: bool = False
    error_message: str | None = None
    additional_context: dict[str, Any] = field(default_factory=dict)

    def complete(
        self,
        status: SyncOperationStatus,
        affected_records: int = 0,
        error_message: str | None = None,
        **context,
    ):
        """Mark the operation as complete with results."""
        self.status = status
        self.end_time = datetime.now()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.affected_records = affected_records
        self.error_message = error_message
        self.additional_context.update(context)


@dataclass
class SyncPerformanceStats:
    """Aggregated performance statistics for synchronization operations."""

    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_duration_ms: float = 0.0
    average_duration_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    total_affected_records: int = 0
    operation_type_stats: dict[SyncOperationType, dict[str, Any]] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total_cache_operations = self.cache_hits + self.cache_misses
        if total_cache_operations == 0:
            return 0.0
        return (self.cache_hits / total_cache_operations) * 100


class SyncMonitor:
    """Comprehensive monitoring system for cache-DB synchronization operations.

    Provides detailed logging, performance metrics collection, and operational
    visibility for all synchronization activities.
    """

    def __init__(self, enable_detailed_logging: bool = True):
        """Initialize the synchronization monitor.

        Args:
            enable_detailed_logging: Whether to enable detailed debug logging
        """
        self.enable_detailed_logging = enable_detailed_logging
        self._metrics_lock = threading.RLock()
        self._operation_metrics: list[SyncOperationMetrics] = []
        self._performance_stats = SyncPerformanceStats()
        self._operation_counter = 0

        # Configure logging
        self.logger = logger

    def _generate_operation_id(self, operation_type: SyncOperationType) -> str:
        """Generate a unique operation ID."""
        with self._metrics_lock:
            self._operation_counter += 1
            return f"{operation_type.value}_{self._operation_counter}_{int(time.time())}"

    @contextmanager
    def monitor_operation(
        self, operation_type: SyncOperationType, cache_hit: bool = False, **context
    ):
        """Context manager for monitoring synchronization operations.

        Args:
            operation_type: Type of synchronization operation
            cache_hit: Whether this operation resulted in a cache hit
            **context: Additional context information

        Yields:
            SyncOperationMetrics: Metrics object for the operation
        """
        operation_id = self._generate_operation_id(operation_type)
        metrics = SyncOperationMetrics(
            operation_id=operation_id,
            operation_type=operation_type,
            status=SyncOperationStatus.STARTED,
            start_time=datetime.now(),
            cache_hit=cache_hit,
            additional_context=context,
        )

        # Log operation start
        self._log_operation_start(metrics)

        try:
            yield metrics
            # Mark as successful if no exception occurred
            metrics.complete(SyncOperationStatus.SUCCESS)
            self._log_operation_success(metrics)
        except Exception as e:
            # Mark as failed and capture error
            metrics.complete(SyncOperationStatus.FAILED, error_message=str(e))
            self._log_operation_failure(metrics)
            raise
        finally:
            # Update aggregated statistics
            self._update_performance_stats(metrics)

    def _log_operation_start(self, metrics: SyncOperationMetrics) -> None:
        """Log the start of a synchronization operation."""
        if self.enable_detailed_logging:
            self.logger.debug(
                f"Sync operation started: {metrics.operation_id} "
                f"type={metrics.operation_type.value} "
                f"cache_hit={metrics.cache_hit} "
                f"context={metrics.additional_context}"
            )
        else:
            self.logger.info(
                f"Sync operation started: {metrics.operation_type.value} "
                f"(ID: {metrics.operation_id})"
            )

    def _log_operation_success(self, metrics: SyncOperationMetrics) -> None:
        """Log successful completion of a synchronization operation."""
        duration_str = f"{metrics.duration_ms:.2f}ms" if metrics.duration_ms else "unknown"
        records_str = (
            f"{metrics.affected_records} records" if metrics.affected_records > 0 else "no records"
        )

        if self.enable_detailed_logging:
            self.logger.debug(
                f"Sync operation completed: {metrics.operation_id} "
                f"duration={duration_str} "
                f"affected={records_str} "
                f"context={metrics.additional_context}"
            )
        else:
            self.logger.info(
                f"Sync operation completed: {metrics.operation_type.value} "
                f"duration={duration_str} affected={records_str}"
            )

    def _log_operation_failure(self, metrics: SyncOperationMetrics) -> None:
        """Log failure of a synchronization operation."""
        duration_str = f"{metrics.duration_ms:.2f}ms" if metrics.duration_ms else "unknown"

        self.logger.error(
            f"Sync operation failed: {metrics.operation_id} "
            f"type={metrics.operation_type.value} "
            f"duration={duration_str} "
            f"error={metrics.error_message} "
            f"context={metrics.additional_context}"
        )

    def _update_performance_stats(self, metrics: SyncOperationMetrics) -> None:
        """Update aggregated performance statistics."""
        with self._metrics_lock:
            self._operation_metrics.append(metrics)

            # Update overall stats
            self._performance_stats.total_operations += 1
            if metrics.status == SyncOperationStatus.SUCCESS:
                self._performance_stats.successful_operations += 1
            elif metrics.status == SyncOperationStatus.FAILED:
                self._performance_stats.failed_operations += 1

            if metrics.duration_ms is not None:
                self._performance_stats.total_duration_ms += metrics.duration_ms
                self._performance_stats.average_duration_ms = (
                    self._performance_stats.total_duration_ms
                    / self._performance_stats.total_operations
                )

            if metrics.cache_hit:
                self._performance_stats.cache_hits += 1
            else:
                self._performance_stats.cache_misses += 1

            self._performance_stats.total_affected_records += metrics.affected_records

            # Update operation type specific stats
            op_type = metrics.operation_type
            if op_type not in self._performance_stats.operation_type_stats:
                self._performance_stats.operation_type_stats[op_type] = {
                    "count": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "total_duration_ms": 0.0,
                    "total_affected_records": 0,
                }

            type_stats = self._performance_stats.operation_type_stats[op_type]
            type_stats["count"] += 1
            if metrics.status == SyncOperationStatus.SUCCESS:
                type_stats["success_count"] += 1
            elif metrics.status == SyncOperationStatus.FAILED:
                type_stats["failed_count"] += 1

            if metrics.duration_ms is not None:
                type_stats["total_duration_ms"] += metrics.duration_ms
            type_stats["total_affected_records"] += metrics.affected_records

            # Record metrics in Prometheus exporter (lazy import to avoid circular dependency)
            try:
                from .metrics_exporter import metrics_exporter

                duration_seconds = (metrics.duration_ms / 1000.0) if metrics.duration_ms else 0.0
                metrics_exporter.record_sync_operation(
                    operation_type=metrics.operation_type,
                    status=metrics.status,
                    duration_seconds=duration_seconds,
                    affected_records=metrics.affected_records,
                )
            except ImportError:
                pass  # Metrics exporter not available

    def log_cache_miss(self, key: str, operation_type: SyncOperationType) -> None:
        """Log a cache miss event."""
        self.logger.debug(f"Cache miss: key={key} operation_type={operation_type.value}")
        # Record cache miss metric (lazy import to avoid circular dependency)
        try:
            from .metrics_exporter import metrics_exporter

            metrics_exporter.record_cache_event("miss", operation_type)
        except ImportError:
            pass  # Metrics exporter not available

    def log_cache_hit(self, key: str, operation_type: SyncOperationType) -> None:
        """Log a cache hit event."""
        self.logger.debug(f"Cache hit: key={key} operation_type={operation_type.value}")
        # Record cache hit metric (lazy import to avoid circular dependency)
        try:
            from .metrics_exporter import metrics_exporter

            metrics_exporter.record_cache_event("hit", operation_type)
        except ImportError:
            pass  # Metrics exporter not available

    def log_bulk_operation_start(
        self, operation_type: SyncOperationType, record_count: int, **context
    ) -> None:
        """Log the start of a bulk operation."""
        self.logger.info(
            f"Bulk {operation_type.value} operation started: "
            f"{record_count} records context={context}"
        )

    def log_bulk_operation_complete(
        self,
        operation_type: SyncOperationType,
        record_count: int,
        duration_ms: float,
        success_count: int,
        **context,
    ) -> None:
        """Log completion of a bulk operation."""
        self.logger.info(
            f"Bulk {operation_type.value} operation completed: "
            f"{success_count}/{record_count} records in {duration_ms:.2f}ms "
            f"context={context}"
        )

    def log_consistency_check(
        self, check_type: str, records_checked: int, inconsistencies_found: int, duration_ms: float
    ) -> None:
        """Log consistency check results."""
        if inconsistencies_found > 0:
            self.logger.warning(
                f"Consistency check {check_type}: {inconsistencies_found} "
                f"inconsistencies found in {records_checked} records "
                f"(duration: {duration_ms:.2f}ms)"
            )
        else:
            self.logger.info(
                f"Consistency check {check_type}: No inconsistencies found "
                f"in {records_checked} records (duration: {duration_ms:.2f}ms)"
            )

    def log_reconciliation_event(
        self, event_type: str, records_affected: int, strategy: str, duration_ms: float
    ) -> None:
        """Log reconciliation events."""
        self.logger.info(
            f"Reconciliation event {event_type}: {records_affected} records "
            f"using strategy '{strategy}' (duration: {duration_ms:.2f}ms)"
        )

    def get_performance_stats(self) -> SyncPerformanceStats:
        """Get current performance statistics."""
        with self._metrics_lock:
            return self._performance_stats

    def get_recent_operations(self, limit: int = 100) -> list[SyncOperationMetrics]:
        """Get recent synchronization operations."""
        with self._metrics_lock:
            return self._operation_metrics[-limit:]

    def get_operation_type_stats(self, operation_type: SyncOperationType) -> dict[str, Any]:
        """Get statistics for a specific operation type."""
        with self._metrics_lock:
            return self._performance_stats.operation_type_stats.get(operation_type, {})

    def reset_stats(self) -> None:
        """Reset all performance statistics."""
        with self._metrics_lock:
            self._operation_metrics.clear()
            self._performance_stats = SyncPerformanceStats()
            self._operation_counter = 0
            self.logger.info("Sync monitoring statistics reset")

    def log_performance_summary(self) -> None:
        """Log a summary of current performance statistics."""
        stats = self.get_performance_stats()

        self.logger.info(
            f"Sync Performance Summary: "
            f"Total operations: {stats.total_operations}, "
            f"Success rate: {stats.success_rate:.1f}%, "
            f"Cache hit rate: {stats.cache_hit_rate:.1f}%, "
            f"Average duration: {stats.average_duration_ms:.2f}ms, "
            f"Total affected records: {stats.total_affected_records}"
        )

        # Log per-operation-type stats
        for op_type, type_stats in stats.operation_type_stats.items():
            if type_stats["count"] > 0:
                avg_duration = type_stats["total_duration_ms"] / type_stats["count"]
                success_rate = (type_stats["success_count"] / type_stats["count"]) * 100

                self.logger.info(
                    f"  {op_type.value}: {type_stats['count']} operations, "
                    f"{success_rate:.1f}% success rate, "
                    f"{avg_duration:.2f}ms avg duration"
                )

    def update_cache_metrics(self, hit_rate: float, size: int, memory_bytes: int) -> None:
        """Update cache performance metrics in Prometheus.

        Args:
            hit_rate: Current cache hit rate percentage
            size: Current number of entries in cache
            memory_bytes: Current memory usage in bytes
        """
        # Update cache metrics (lazy import to avoid circular dependency)
        try:
            from .metrics_exporter import metrics_exporter

            metrics_exporter.update_cache_metrics(hit_rate, size, memory_bytes)
        except ImportError:
            pass  # Metrics exporter not available

    def update_database_health(self, is_healthy: bool) -> None:
        """Update database health status in Prometheus.

        Args:
            is_healthy: Whether the database is currently healthy
        """
        # Update database health (lazy import to avoid circular dependency)
        try:
            from .metrics_exporter import metrics_exporter

            metrics_exporter.update_database_health(is_healthy)
        except ImportError:
            pass  # Metrics exporter not available

    def record_database_error(self, error_type: str) -> None:
        """Record a database connection error in Prometheus.

        Args:
            error_type: Type of database error
        """
        # Record database error (lazy import to avoid circular dependency)
        try:
            from .metrics_exporter import metrics_exporter

            metrics_exporter.record_database_error(error_type)
        except ImportError:
            pass  # Metrics exporter not available

    def record_consistency_check(
        self,
        check_type: str,
        duration_seconds: float,
        inconsistencies_found: int,
        severity: str = "medium",
    ) -> None:
        """Record a consistency check operation in Prometheus.

        Args:
            check_type: Type of consistency check
            duration_seconds: Duration of the check in seconds
            inconsistencies_found: Number of inconsistencies found
            severity: Severity of inconsistencies (low, medium, high)
        """
        # Record consistency check (lazy import to avoid circular dependency)
        try:
            from .metrics_exporter import metrics_exporter

            metrics_exporter.record_consistency_check(
                check_type, duration_seconds, inconsistencies_found, severity
            )
        except ImportError:
            pass  # Metrics exporter not available

    def record_reconciliation(
        self, strategy: str, status: str, duration_seconds: float, records_affected: int = 0
    ) -> None:
        """Record a reconciliation operation in Prometheus.

        Args:
            strategy: Reconciliation strategy used
            status: Status of the reconciliation (success, failed, partial)
            duration_seconds: Duration of the reconciliation in seconds
            records_affected: Number of records affected
        """
        # Record reconciliation (lazy import to avoid circular dependency)
        try:
            from .metrics_exporter import metrics_exporter

            metrics_exporter.record_reconciliation(
                strategy, status, duration_seconds, records_affected
            )
        except ImportError:
            pass  # Metrics exporter not available


# Global sync monitor instance
sync_monitor = SyncMonitor()
