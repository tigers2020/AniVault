"""
End-to-end integration tests for the AniVault monitoring system.

This module tests the complete monitoring pipeline from metrics collection
through dashboard display and alerting.
"""

import pytest
import time
import threading
import requests
from unittest.mock import Mock, patch
from http.server import HTTPServer
from threading import Thread

from src.core.sync_monitoring import sync_monitor, SyncOperationType, SyncOperationStatus
from src.core.metrics_exporter import metrics_exporter
from src.core.metrics_server import MetricsServer, MetricsHTTPRequestHandler
from src.gui.monitoring_dashboard import MonitoringDashboard
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import sys


class TestMonitoringIntegration:
    """End-to-end integration tests for the monitoring system."""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment for each test."""
        # Reset monitoring state
        sync_monitor.reset_stats()

        # Create QApplication if it doesn't exist
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()

    def test_metrics_collection_pipeline(self):
        """Test the complete metrics collection pipeline."""
        # Perform various operations to generate metrics
        with sync_monitor.monitor_operation(
            SyncOperationType.READ_THROUGH,
            cache_hit=False,
            key="test_key"
        ) as metrics:
            time.sleep(0.01)
            metrics.complete(SyncOperationStatus.SUCCESS, affected_records=1)

        # Test cache events
        sync_monitor.log_cache_hit("test_key", SyncOperationType.READ_THROUGH)
        sync_monitor.log_cache_miss("test_key", SyncOperationType.WRITE_THROUGH)

        # Test bulk operations
        sync_monitor.log_bulk_operation_start(
            SyncOperationType.BULK_INSERT,
            record_count=100,
            operation_subtype="test"
        )
        sync_monitor.log_bulk_operation_complete(
            SyncOperationType.BULK_INSERT,
            record_count=100,
            duration_ms=50.0,
            success_count=95,
            operation_subtype="test"
        )

        # Verify metrics were collected
        stats = sync_monitor.get_performance_stats()
        assert stats.total_operations >= 1
        assert stats.cache_hits >= 1
        assert stats.cache_misses >= 1

        # Verify Prometheus metrics were recorded
        metrics_output = metrics_exporter.generate_metrics()
        assert "anivault_sync_operations_total" in metrics_output
        assert "anivault_cache_events_total" in metrics_output

    def test_metrics_server_endpoints(self):
        """Test the metrics server HTTP endpoints."""
        server = MetricsServer(host='localhost', port=8084)

        try:
            # Start server
            assert server.start()
            time.sleep(0.5)  # Give server time to start

            # Test /metrics endpoint
            response = requests.get('http://localhost:8084/metrics', timeout=5)
            assert response.status_code == 200
            assert 'anivault_sync_operations_total' in response.text
            assert 'anivault_application_info' in response.text

            # Test /health endpoint
            response = requests.get('http://localhost:8084/health', timeout=5)
            assert response.status_code == 200
            assert 'healthy' in response.text

            # Test 404 endpoint
            response = requests.get('http://localhost:8084/nonexistent', timeout=5)
            assert response.status_code == 404

        finally:
            server.stop()

    def test_metrics_server_with_operations(self):
        """Test metrics server with actual operations."""
        server = MetricsServer(host='localhost', port=8085)

        try:
            # Start server
            assert server.start()
            time.sleep(0.5)

            # Perform operations to generate metrics
            with sync_monitor.monitor_operation(
                SyncOperationType.WRITE_THROUGH,
                cache_hit=True,
                key="integration_test"
            ) as metrics:
                time.sleep(0.01)
                metrics.complete(SyncOperationStatus.SUCCESS, affected_records=2)

            # Get metrics from server
            response = requests.get('http://localhost:8085/metrics', timeout=5)
            assert response.status_code == 200

            metrics_text = response.text
            assert 'write_through' in metrics_text
            assert 'success' in metrics_text

        finally:
            server.stop()

    def test_dashboard_widget_creation(self):
        """Test creation and basic functionality of dashboard widgets."""
        dashboard = MonitoringDashboard()

        # Test that all widgets are created
        assert dashboard.tab_widget.count() == 4

        # Test tab names
        tab_names = []
        for i in range(dashboard.tab_widget.count()):
            tab_names.append(dashboard.tab_widget.tabText(i))

        expected_tabs = ["Sync Operations", "Cache Metrics", "System Health", "Metrics Log"]
        for tab_name in expected_tabs:
            assert tab_name in tab_names

        # Test timer setup
        assert dashboard.update_timer.isActive()

        # Clean up
        dashboard.stop_monitoring()

    def test_dashboard_metrics_update(self):
        """Test dashboard metrics update functionality."""
        dashboard = MonitoringDashboard()

        try:
            # Generate some test metrics
            with sync_monitor.monitor_operation(
                SyncOperationType.READ_THROUGH,
                cache_hit=False,
                key="dashboard_test"
            ) as metrics:
                time.sleep(0.01)
                metrics.complete(SyncOperationStatus.SUCCESS, affected_records=1)

            # Manually trigger update
            dashboard.update_all_metrics()

            # Verify status label is updated
            assert "Last Updated:" in dashboard.status_label.text()
            assert dashboard.status_label.styleSheet() == "color: green; font-weight: bold;"

        finally:
            dashboard.stop_monitoring()

    def test_dashboard_error_handling(self):
        """Test dashboard error handling."""
        dashboard = MonitoringDashboard()

        try:
            # Mock an error in metrics collection
            with patch.object(sync_monitor, 'get_performance_stats', side_effect=Exception("Test error")):
                dashboard.update_all_metrics()

                # Verify error is handled gracefully
                assert "Monitoring Error:" in dashboard.status_label.text()
                assert dashboard.status_label.styleSheet() == "color: red; font-weight: bold;"

        finally:
            dashboard.stop_monitoring()

    def test_metrics_exporter_integration(self):
        """Test integration between sync monitor and metrics exporter."""
        # Reset stats
        sync_monitor.reset_stats()

        # Perform operations
        with sync_monitor.monitor_operation(
            SyncOperationType.BULK_UPDATE,
            cache_hit=False,
            record_count=50
        ) as metrics:
            time.sleep(0.01)
            metrics.complete(SyncOperationStatus.SUCCESS, affected_records=50)

        # Check that metrics were recorded in both systems
        stats = sync_monitor.get_performance_stats()
        assert stats.total_operations == 1
        assert stats.successful_operations == 1

        # Check Prometheus metrics
        metrics_output = metrics_exporter.generate_metrics()
        assert "bulk_update" in metrics_output
        assert "success" in metrics_output

    def test_cache_metrics_integration(self):
        """Test cache metrics integration."""
        # Update cache metrics
        sync_monitor.update_cache_metrics(
            hit_rate=85.0,
            size=1000,
            memory_bytes=512 * 1024
        )

        # Verify metrics are available in Prometheus format
        metrics_output = metrics_exporter.generate_metrics()
        assert "anivault_cache_hit_rate" in metrics_output
        assert "anivault_cache_size" in metrics_output
        assert "anivault_cache_memory_usage_bytes" in metrics_output

    def test_consistency_check_metrics(self):
        """Test consistency check metrics recording."""
        # Record consistency check
        sync_monitor.record_consistency_check(
            check_type="data_integrity",
            duration_seconds=1.5,
            inconsistencies_found=3,
            severity="medium"
        )

        # Verify metrics are recorded
        metrics_output = metrics_exporter.generate_metrics()
        assert "anivault_consistency_check_duration_seconds" in metrics_output
        assert "anivault_consistency_inconsistencies_total" in metrics_output

    def test_reconciliation_metrics(self):
        """Test reconciliation metrics recording."""
        # Record reconciliation
        sync_monitor.record_reconciliation(
            strategy="database_wins",
            status="success",
            duration_seconds=2.0,
            records_affected=25
        )

        # Verify metrics are recorded
        metrics_output = metrics_exporter.generate_metrics()
        assert "anivault_reconciliation_operations_total" in metrics_output
        assert "anivault_reconciliation_duration_seconds" in metrics_output

    def test_database_health_metrics(self):
        """Test database health metrics."""
        # Update database health
        sync_monitor.update_database_health(True)
        sync_monitor.record_database_error("connection_timeout")

        # Verify metrics are recorded
        metrics_output = metrics_exporter.generate_metrics()
        assert "anivault_database_health_status" in metrics_output
        assert "anivault_database_connection_errors_total" in metrics_output

    def test_circuit_breaker_metrics(self):
        """Test circuit breaker metrics."""
        # Update circuit breaker state
        sync_monitor.update_circuit_breaker_state("database", "open")
        sync_monitor.record_circuit_breaker_failure("database")

        # Verify metrics are recorded
        metrics_output = metrics_exporter.generate_metrics()
        assert "anivault_circuit_breaker_state" in metrics_output
        assert "anivault_circuit_breaker_failures_total" in metrics_output

    def test_performance_under_load(self):
        """Test monitoring performance under load."""
        # Perform many operations quickly
        start_time = time.time()

        for i in range(100):
            with sync_monitor.monitor_operation(
                SyncOperationType.READ_THROUGH,
                cache_hit=(i % 2 == 0),
                key=f"load_test_{i}"
            ) as metrics:
                time.sleep(0.001)  # Very short delay
                metrics.complete(SyncOperationStatus.SUCCESS, affected_records=1)

        end_time = time.time()
        duration = end_time - start_time

        # Verify operations were recorded
        stats = sync_monitor.get_performance_stats()
        assert stats.total_operations == 100
        assert stats.cache_hits == 50
        assert stats.cache_misses == 50

        # Verify performance is reasonable (should complete in < 1 second)
        assert duration < 1.0

        # Verify metrics are still accessible
        metrics_output = metrics_exporter.generate_metrics()
        assert "anivault_sync_operations_total" in metrics_output

    def test_concurrent_operations(self):
        """Test monitoring with concurrent operations."""
        def perform_operations(thread_id: int, count: int):
            """Perform operations in a separate thread."""
            for i in range(count):
                with sync_monitor.monitor_operation(
                    SyncOperationType.WRITE_THROUGH,
                    cache_hit=False,
                    key=f"thread_{thread_id}_op_{i}"
                ) as metrics:
                    time.sleep(0.001)
                    metrics.complete(SyncOperationStatus.SUCCESS, affected_records=1)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=perform_operations, args=(i, 20))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations were recorded
        stats = sync_monitor.get_performance_stats()
        assert stats.total_operations == 100  # 5 threads * 20 operations

        # Verify metrics are consistent
        metrics_output = metrics_exporter.generate_metrics()
        assert "write_through" in metrics_output
        assert "success" in metrics_output

    def test_metrics_server_restart(self):
        """Test metrics server restart functionality."""
        server = MetricsServer(host='localhost', port=8086)

        try:
            # Start server
            assert server.start()
            assert server.is_running()
            time.sleep(0.5)

            # Stop server
            server.stop()
            assert not server.is_running()
            time.sleep(0.5)

            # Restart server
            assert server.start()
            assert server.is_running()
            time.sleep(0.5)

            # Verify server is still functional
            response = requests.get('http://localhost:8086/health', timeout=5)
            assert response.status_code == 200

        finally:
            server.stop()

    def test_application_info_metrics(self):
        """Test application info metrics."""
        metrics_output = metrics_exporter.generate_metrics()

        # Check that application info is present
        assert "anivault_application_info" in metrics_output
        assert "name" in metrics_output
        assert "AniVault" in metrics_output
        assert "version" in metrics_output
        assert "component" in metrics_output


class TestMonitoringDocumentation:
    """Test documentation and configuration files."""

    def test_prometheus_config_validity(self):
        """Test that Prometheus configuration is valid."""
        import yaml

        with open('monitoring/prometheus.yml', 'r') as f:
            config = yaml.safe_load(f)

        # Check required sections
        assert 'global' in config
        assert 'scrape_configs' in config

        # Check AniVault job configuration
        anivault_job = None
        for job in config['scrape_configs']:
            if job['job_name'] == 'anivault':
                anivault_job = job
                break

        assert anivault_job is not None
        assert 'localhost:8080' in anivault_job['static_configs'][0]['targets']
        assert anivault_job['metrics_path'] == '/metrics'

    def test_alerting_rules_validity(self):
        """Test that alerting rules are valid."""
        import yaml

        with open('monitoring/anivault_rules.yml', 'r') as f:
            rules = yaml.safe_load(f)

        # Check structure
        assert 'groups' in rules
        assert len(rules['groups']) > 0

        # Check that we have the expected alert groups
        group_names = [group['name'] for group in rules['groups']]
        expected_groups = [
            'anivault_sync_alerts',
            'anivault_health_alerts',
            'anivault_consistency_alerts',
            'anivault_resource_alerts'
        ]

        for expected_group in expected_groups:
            assert expected_group in group_names

    def test_grafana_dashboard_validity(self):
        """Test that Grafana dashboard configuration is valid."""
        import json

        with open('monitoring/grafana/dashboards/anivault-dashboard.json', 'r') as f:
            dashboard = json.load(f)

        # Check structure
        assert 'dashboard' in dashboard
        dashboard_config = dashboard['dashboard']

        assert 'title' in dashboard_config
        assert 'panels' in dashboard_config
        assert len(dashboard_config['panels']) > 0

        # Check that we have expected panels
        panel_titles = [panel['title'] for panel in dashboard_config['panels']]
        expected_panels = [
            'Sync Operations Overview',
            'Success Rate',
            'Cache Hit Rate',
            'Average Operation Duration'
        ]

        for expected_panel in expected_panels:
            assert expected_panel in panel_titles


if __name__ == "__main__":
    pytest.main([__file__])
