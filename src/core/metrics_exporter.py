"""
Prometheus metrics exporter for AniVault cache-DB synchronization operations.

This module provides Prometheus-compatible metrics for monitoring synchronization
performance, cache behavior, and system health.
"""

import time
from typing import Dict, Any
from prometheus_client import (
    Counter, Histogram, Gauge, Info, CollectorRegistry,
    generate_latest, CONTENT_TYPE_LATEST, REGISTRY
)

from .sync_enums import SyncOperationType, SyncOperationStatus


class SyncMetricsExporter:
    """
    Prometheus metrics exporter for cache-DB synchronization operations.
    
    Provides standardized metrics for monitoring synchronization performance,
    cache behavior, and system health indicators.
    """
    
    def __init__(self, registry: CollectorRegistry = None):
        """Initialize the metrics exporter.
        
        Args:
            registry: Prometheus registry to use (defaults to global registry)
        """
        self.registry = registry or REGISTRY
        
        # Initialize all metrics
        self._initialize_metrics()
    
    def _initialize_metrics(self) -> None:
        """Initialize all Prometheus metrics."""
        
        # Sync operation counters
        self.sync_operations_total = Counter(
            'anivault_sync_operations_total',
            'Total number of synchronization operations',
            ['operation_type', 'status'],
            registry=self.registry
        )
        
        # Sync operation duration histogram
        self.sync_operation_duration_seconds = Histogram(
            'anivault_sync_operation_duration_seconds',
            'Duration of synchronization operations in seconds',
            ['operation_type'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
            registry=self.registry
        )
        
        # Affected records counter
        self.sync_affected_records_total = Counter(
            'anivault_sync_affected_records_total',
            'Total number of records affected by synchronization operations',
            ['operation_type'],
            registry=self.registry
        )
        
        # Cache events counter
        self.cache_events_total = Counter(
            'anivault_cache_events_total',
            'Total number of cache events',
            ['event_type', 'operation_type'],
            registry=self.registry
        )
        
        # Cache performance gauges
        self.cache_hit_rate = Gauge(
            'anivault_cache_hit_rate',
            'Current cache hit rate percentage',
            registry=self.registry
        )
        
        self.cache_size = Gauge(
            'anivault_cache_size',
            'Current number of entries in cache',
            registry=self.registry
        )
        
        self.cache_memory_usage_bytes = Gauge(
            'anivault_cache_memory_usage_bytes',
            'Current memory usage of cache in bytes',
            registry=self.registry
        )
        
        # Database health metrics
        self.database_health_status = Gauge(
            'anivault_database_health_status',
            'Database health status (1=healthy, 0=unhealthy)',
            registry=self.registry
        )
        
        self.database_connection_errors_total = Counter(
            'anivault_database_connection_errors_total',
            'Total number of database connection errors',
            ['error_type'],
            registry=self.registry
        )
        
        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            'anivault_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half_open)',
            ['breaker_name'],
            registry=self.registry
        )
        
        self.circuit_breaker_failures_total = Counter(
            'anivault_circuit_breaker_failures_total',
            'Total number of circuit breaker failures',
            ['breaker_name'],
            registry=self.registry
        )
        
        # Consistency check metrics
        self.consistency_check_duration_seconds = Histogram(
            'anivault_consistency_check_duration_seconds',
            'Duration of consistency checks in seconds',
            ['check_type'],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        self.consistency_inconsistencies_total = Counter(
            'anivault_consistency_inconsistencies_total',
            'Total number of data inconsistencies found',
            ['check_type', 'severity'],
            registry=self.registry
        )
        
        # Reconciliation metrics
        self.reconciliation_operations_total = Counter(
            'anivault_reconciliation_operations_total',
            'Total number of reconciliation operations',
            ['strategy', 'status'],
            registry=self.registry
        )
        
        self.reconciliation_duration_seconds = Histogram(
            'anivault_reconciliation_duration_seconds',
            'Duration of reconciliation operations in seconds',
            ['strategy'],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        # Application info
        self.application_info = Info(
            'anivault_application_info',
            'Information about the AniVault application',
            registry=self.registry
        )
        
        # Set application info
        self.application_info.info({
            'name': 'AniVault',
            'version': '1.0.0',
            'component': 'cache-db-sync'
        })
    
    def record_sync_operation(self, operation_type: SyncOperationType, 
                            status: SyncOperationStatus, duration_seconds: float,
                            affected_records: int = 0) -> None:
        """Record a synchronization operation.
        
        Args:
            operation_type: Type of synchronization operation
            status: Status of the operation
            duration_seconds: Duration of the operation in seconds
            affected_records: Number of records affected by the operation
        """
        # Increment operation counter
        self.sync_operations_total.labels(
            operation_type=operation_type.value,
            status=status.value
        ).inc()
        
        # Record operation duration
        self.sync_operation_duration_seconds.labels(
            operation_type=operation_type.value
        ).observe(duration_seconds)
        
        # Record affected records
        if affected_records > 0:
            self.sync_affected_records_total.labels(
                operation_type=operation_type.value
            ).inc(affected_records)
    
    def record_cache_event(self, event_type: str, operation_type: SyncOperationType) -> None:
        """Record a cache event (hit, miss, etc.).
        
        Args:
            event_type: Type of cache event (hit, miss, eviction, etc.)
            operation_type: Type of operation that triggered the event
        """
        self.cache_events_total.labels(
            event_type=event_type,
            operation_type=operation_type.value
        ).inc()
    
    def update_cache_metrics(self, hit_rate: float, size: int, memory_bytes: int) -> None:
        """Update cache performance metrics.
        
        Args:
            hit_rate: Current cache hit rate percentage
            size: Current number of entries in cache
            memory_bytes: Current memory usage in bytes
        """
        self.cache_hit_rate.set(hit_rate)
        self.cache_size.set(size)
        self.cache_memory_usage_bytes.set(memory_bytes)
    
    def update_database_health(self, is_healthy: bool) -> None:
        """Update database health status.
        
        Args:
            is_healthy: Whether the database is currently healthy
        """
        self.database_health_status.set(1 if is_healthy else 0)
    
    def record_database_error(self, error_type: str) -> None:
        """Record a database connection error.
        
        Args:
            error_type: Type of database error
        """
        self.database_connection_errors_total.labels(error_type=error_type).inc()
    
    def update_circuit_breaker_state(self, breaker_name: str, state: str) -> None:
        """Update circuit breaker state.
        
        Args:
            breaker_name: Name of the circuit breaker
            state: Current state (closed, open, half_open)
        """
        state_value = {'closed': 0, 'open': 1, 'half_open': 2}.get(state, 0)
        self.circuit_breaker_state.labels(breaker_name=breaker_name).set(state_value)
    
    def record_circuit_breaker_failure(self, breaker_name: str) -> None:
        """Record a circuit breaker failure.
        
        Args:
            breaker_name: Name of the circuit breaker
        """
        self.circuit_breaker_failures_total.labels(breaker_name=breaker_name).inc()
    
    def record_consistency_check(self, check_type: str, duration_seconds: float,
                               inconsistencies_found: int, severity: str = 'medium') -> None:
        """Record a consistency check operation.
        
        Args:
            check_type: Type of consistency check
            duration_seconds: Duration of the check in seconds
            inconsistencies_found: Number of inconsistencies found
            severity: Severity of inconsistencies (low, medium, high)
        """
        # Record duration
        self.consistency_check_duration_seconds.labels(
            check_type=check_type
        ).observe(duration_seconds)
        
        # Record inconsistencies if any found
        if inconsistencies_found > 0:
            self.consistency_inconsistencies_total.labels(
                check_type=check_type,
                severity=severity
            ).inc(inconsistencies_found)
    
    def record_reconciliation(self, strategy: str, status: str, duration_seconds: float,
                            records_affected: int = 0) -> None:
        """Record a reconciliation operation.
        
        Args:
            strategy: Reconciliation strategy used
            status: Status of the reconciliation (success, failed, partial)
            duration_seconds: Duration of the reconciliation in seconds
            records_affected: Number of records affected
        """
        # Record operation
        self.reconciliation_operations_total.labels(
            strategy=strategy,
            status=status
        ).inc()
        
        # Record duration
        self.reconciliation_duration_seconds.labels(
            strategy=strategy
        ).observe(duration_seconds)
        
        # Record affected records if any
        if records_affected > 0:
            self.sync_affected_records_total.labels(
                operation_type=SyncOperationType.RECONCILIATION.value
            ).inc(records_affected)
    
    def generate_metrics(self) -> str:
        """Generate Prometheus metrics in text format.
        
        Returns:
            Prometheus metrics in text format
        """
        return generate_latest(self.registry).decode('utf-8')
    
    def get_content_type(self) -> str:
        """Get the content type for metrics response.
        
        Returns:
            Content type string for Prometheus metrics
        """
        return CONTENT_TYPE_LATEST


# Global metrics exporter instance
metrics_exporter = SyncMetricsExporter()
