"""
Tests for synchronization monitoring and metrics collection.
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.core.sync_monitoring import (
    SyncMonitor, SyncOperationType, SyncOperationStatus,
    SyncOperationMetrics, sync_monitor
)
from src.core.metrics_exporter import SyncMetricsExporter, metrics_exporter
from src.core.metrics_server import MetricsServer, metrics_server


class TestSyncOperationMetrics:
    """Test SyncOperationMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating sync operation metrics."""
        metrics = SyncOperationMetrics(
            operation_id="test_1",
            operation_type=SyncOperationType.READ_THROUGH,
            status=SyncOperationStatus.STARTED,
            start_time=time.time()
        )

        assert metrics.operation_id == "test_1"
        assert metrics.operation_type == SyncOperationType.READ_THROUGH
        assert metrics.status == SyncOperationStatus.STARTED
        assert metrics.affected_records == 0
        assert metrics.cache_hit is False

    def test_metrics_completion(self):
        """Test completing sync operation metrics."""
        metrics = SyncOperationMetrics(
            operation_id="test_2",
            operation_type=SyncOperationType.WRITE_THROUGH,
            status=SyncOperationStatus.STARTED,
            start_time=time.time()
        )

        time.sleep(0.01)  # Small delay to ensure duration > 0
        metrics.complete(
            status=SyncOperationStatus.SUCCESS,
            affected_records=5,
            additional_context={'key_type': 'tmdb'}
        )

        assert metrics.status == SyncOperationStatus.SUCCESS
        assert metrics.affected_records == 5
        assert metrics.duration_ms is not None
        assert metrics.duration_ms > 0
        assert metrics.additional_context['key_type'] == 'tmdb'


class TestSyncMonitor:
    """Test SyncMonitor class."""

    def test_monitor_operation_success(self):
        """Test monitoring a successful operation."""
        monitor = SyncMonitor(enable_detailed_logging=False)

        with monitor.monitor_operation(
            SyncOperationType.READ_THROUGH,
            cache_hit=False,
            key="test_key"
        ) as metrics:
            time.sleep(0.01)  # Simulate work
            metrics.complete(SyncOperationStatus.SUCCESS, affected_records=1)

        # Check that metrics were recorded
        stats = monitor.get_performance_stats()
        assert stats.total_operations == 1
        assert stats.successful_operations == 1
        assert stats.failed_operations == 0
        assert stats.cache_misses == 1
        assert stats.total_affected_records == 1

    def test_monitor_operation_failure(self):
        """Test monitoring a failed operation."""
        monitor = SyncMonitor(enable_detailed_logging=False)

        with pytest.raises(ValueError):
            with monitor.monitor_operation(
                SyncOperationType.WRITE_THROUGH,
                cache_hit=True
            ) as metrics:
                raise ValueError("Test error")

        # Check that metrics were recorded
        stats = monitor.get_performance_stats()
        assert stats.total_operations == 1
        assert stats.successful_operations == 0
        assert stats.failed_operations == 1
        assert stats.cache_hits == 1

    def test_cache_event_logging(self):
        """Test cache event logging."""
        monitor = SyncMonitor(enable_detailed_logging=False)

        # Test cache hit logging
        monitor.log_cache_hit("test_key", SyncOperationType.READ_THROUGH)

        # Test cache miss logging
        monitor.log_cache_miss("test_key", SyncOperationType.READ_THROUGH)

        # No exceptions should be raised
        assert True

    def test_bulk_operation_logging(self):
        """Test bulk operation logging."""
        monitor = SyncMonitor(enable_detailed_logging=False)

        # Test bulk operation start
        monitor.log_bulk_operation_start(
            SyncOperationType.BULK_INSERT,
            record_count=100,
            operation_subtype="test"
        )

        # Test bulk operation complete
        monitor.log_bulk_operation_complete(
            SyncOperationType.BULK_INSERT,
            record_count=100,
            duration_ms=50.0,
            success_count=95,
            operation_subtype="test"
        )

        # No exceptions should be raised
        assert True

    def test_consistency_check_logging(self):
        """Test consistency check logging."""
        monitor = SyncMonitor(enable_detailed_logging=False)

        # Test with inconsistencies found
        monitor.log_consistency_check(
            check_type="test_check",
            records_checked=1000,
            inconsistencies_found=5,
            duration_ms=100.0
        )

        # Test with no inconsistencies
        monitor.log_consistency_check(
            check_type="test_check",
            records_checked=500,
            inconsistencies_found=0,
            duration_ms=50.0
        )

        # No exceptions should be raised
        assert True

    def test_reconciliation_event_logging(self):
        """Test reconciliation event logging."""
        monitor = SyncMonitor(enable_detailed_logging=False)

        monitor.log_reconciliation_event(
            event_type="test_reconciliation",
            records_affected=10,
            strategy="database_wins",
            duration_ms=25.0
        )

        # No exceptions should be raised
        assert True

    def test_performance_summary(self):
        """Test performance summary logging."""
        monitor = SyncMonitor(enable_detailed_logging=False)

        # Add some test data
        with monitor.monitor_operation(SyncOperationType.READ_THROUGH) as metrics:
            metrics.complete(SyncOperationStatus.SUCCESS, affected_records=1)

        # Test summary logging
        monitor.log_performance_summary()

        # No exceptions should be raised
        assert True

    def test_stats_reset(self):
        """Test statistics reset functionality."""
        monitor = SyncMonitor(enable_detailed_logging=False)

        # Add some test data
        with monitor.monitor_operation(SyncOperationType.READ_THROUGH) as metrics:
            metrics.complete(SyncOperationStatus.SUCCESS, affected_records=1)

        # Verify data exists
        stats = monitor.get_performance_stats()
        assert stats.total_operations == 1

        # Reset stats
        monitor.reset_stats()

        # Verify data is cleared
        stats = monitor.get_performance_stats()
        assert stats.total_operations == 0


class TestSyncMetricsExporter:
    """Test SyncMetricsExporter class."""

    def test_exporter_initialization(self):
        """Test metrics exporter initialization."""
        exporter = SyncMetricsExporter()

        # Check that metrics are initialized
        assert exporter.sync_operations_total is not None
        assert exporter.sync_operation_duration_seconds is not None
        assert exporter.sync_affected_records_total is not None
        assert exporter.cache_events_total is not None
        assert exporter.cache_hit_rate is not None
        assert exporter.cache_size is not None
        assert exporter.cache_memory_usage_bytes is not None
        assert exporter.database_health_status is not None
        assert exporter.circuit_breaker_state is not None
        assert exporter.application_info is not None

    def test_record_sync_operation(self):
        """Test recording sync operations."""
        exporter = SyncMetricsExporter()

        # Record a successful operation
        exporter.record_sync_operation(
            SyncOperationType.READ_THROUGH,
            SyncOperationStatus.SUCCESS,
            duration_seconds=0.1,
            affected_records=5
        )

        # Record a failed operation
        exporter.record_sync_operation(
            SyncOperationType.WRITE_THROUGH,
            SyncOperationStatus.FAILED,
            duration_seconds=0.05,
            affected_records=0
        )

        # No exceptions should be raised
        assert True

    def test_record_cache_event(self):
        """Test recording cache events."""
        exporter = SyncMetricsExporter()

        # Record cache hit
        exporter.record_cache_event("hit", SyncOperationType.READ_THROUGH)

        # Record cache miss
        exporter.record_cache_event("miss", SyncOperationType.READ_THROUGH)

        # No exceptions should be raised
        assert True

    def test_update_cache_metrics(self):
        """Test updating cache metrics."""
        exporter = SyncMetricsExporter()

        exporter.update_cache_metrics(
            hit_rate=85.5,
            size=1000,
            memory_bytes=1024 * 1024
        )

        # No exceptions should be raised
        assert True

    def test_update_database_health(self):
        """Test updating database health."""
        exporter = SyncMetricsExporter()

        exporter.update_database_health(True)
        exporter.update_database_health(False)

        # No exceptions should be raised
        assert True

    def test_record_database_error(self):
        """Test recording database errors."""
        exporter = SyncMetricsExporter()

        exporter.record_database_error("connection_timeout")
        exporter.record_database_error("query_failed")

        # No exceptions should be raised
        assert True

    def test_update_circuit_breaker_state(self):
        """Test updating circuit breaker state."""
        exporter = SyncMetricsExporter()

        exporter.update_circuit_breaker_state("database", "closed")
        exporter.update_circuit_breaker_state("database", "open")
        exporter.update_circuit_breaker_state("database", "half_open")

        # No exceptions should be raised
        assert True

    def test_record_consistency_check(self):
        """Test recording consistency checks."""
        exporter = SyncMetricsExporter()

        # Record check with inconsistencies
        exporter.record_consistency_check(
            "data_integrity",
            duration_seconds=1.5,
            inconsistencies_found=3,
            severity="medium"
        )

        # Record check with no inconsistencies
        exporter.record_consistency_check(
            "data_integrity",
            duration_seconds=0.8,
            inconsistencies_found=0,
            severity="low"
        )

        # No exceptions should be raised
        assert True

    def test_record_reconciliation(self):
        """Test recording reconciliation operations."""
        exporter = SyncMetricsExporter()

        exporter.record_reconciliation(
            "database_wins",
            "success",
            duration_seconds=2.0,
            records_affected=50
        )

        exporter.record_reconciliation(
            "last_modified_wins",
            "partial",
            duration_seconds=1.2,
            records_affected=25
        )

        # No exceptions should be raised
        assert True

    def test_generate_metrics(self):
        """Test generating metrics output."""
        exporter = SyncMetricsExporter()

        # Add some test data
        exporter.record_sync_operation(
            SyncOperationType.READ_THROUGH,
            SyncOperationStatus.SUCCESS,
            duration_seconds=0.1,
            affected_records=1
        )

        # Generate metrics
        metrics_output = exporter.generate_metrics()

        # Check that output is a string and contains expected metrics
        assert isinstance(metrics_output, str)
        assert "anivault_sync_operations_total" in metrics_output
        assert "anivault_sync_operation_duration_seconds" in metrics_output
        assert "anivault_application_info" in metrics_output


class TestMetricsServer:
    """Test MetricsServer class."""

    def test_server_initialization(self):
        """Test metrics server initialization."""
        server = MetricsServer(host='localhost', port=8081)

        assert server.host == 'localhost'
        assert server.port == 8081
        assert not server.running
        assert server.server is None
        assert server.server_thread is None

    def test_server_start_stop(self):
        """Test starting and stopping the metrics server."""
        server = MetricsServer(host='localhost', port=8082)

        # Start server
        success = server.start()
        assert success
        assert server.running

        # Give server time to start
        time.sleep(0.1)

        # Stop server
        server.stop()
        assert not server.running

    def test_server_already_running(self):
        """Test starting server when already running."""
        server = MetricsServer(host='localhost', port=8083)

        # Start server twice
        success1 = server.start()
        success2 = server.start()

        assert success1
        assert success2  # Should return True if already running

        # Clean up
        server.stop()

    def test_server_invalid_port(self):
        """Test server with invalid port."""
        # This should fail gracefully
        server = MetricsServer(host='localhost', port=99999)

        success = server.start()
        # May succeed or fail depending on system, but shouldn't crash
        assert isinstance(success, bool)

        if success:
            server.stop()


class TestIntegration:
    """Integration tests for monitoring system."""

    def test_monitor_with_metrics_integration(self):
        """Test integration between SyncMonitor and metrics exporter."""
        # Use the global instances
        monitor = sync_monitor

        # Reset stats first
        monitor.reset_stats()

        # Perform some operations
        with monitor.monitor_operation(
            SyncOperationType.READ_THROUGH,
            cache_hit=False,
            key="integration_test"
        ) as metrics:
            time.sleep(0.01)
            metrics.complete(SyncOperationStatus.SUCCESS, affected_records=2)

        # Check that both monitor and metrics were updated
        stats = monitor.get_performance_stats()
        assert stats.total_operations == 1
        assert stats.successful_operations == 1

        # Check metrics output contains our operation
        metrics_output = metrics_exporter.generate_metrics()
        assert "anivault_sync_operations_total" in metrics_output
        assert "read_through" in metrics_output
        assert "success" in metrics_output

    def test_cache_metrics_integration(self):
        """Test cache metrics integration."""
        # Update cache metrics
        sync_monitor.update_cache_metrics(
            hit_rate=75.0,
            size=500,
            memory_bytes=512 * 1024
        )

        # Check metrics output
        metrics_output = metrics_exporter.generate_metrics()
        assert "anivault_cache_hit_rate" in metrics_output
        assert "anivault_cache_size" in metrics_output
        assert "anivault_cache_memory_usage_bytes" in metrics_output


if __name__ == "__main__":
    pytest.main([__file__])
