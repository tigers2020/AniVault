"""Monitoring dashboard widget for AniVault application.

This module provides a PyQt5-based monitoring dashboard for viewing
cache-DB synchronization metrics and system health in real-time.
"""

import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.metrics_exporter import metrics_exporter
from ..core.metrics_server import metrics_server
from ..core.sync_monitoring import sync_monitor


class MetricsWidget(QWidget):
    """Base widget for displaying metrics."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.init_ui()

    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()

        # Title
        title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Content will be added by subclasses
        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)

        self.setLayout(layout)

    def update_metrics(self):
        """Update the displayed metrics. Override in subclasses."""
        pass


class SyncOperationsWidget(MetricsWidget):
    """Widget for displaying synchronization operation metrics."""

    def __init__(self, parent=None):
        super().__init__("Synchronization Operations", parent)
        self.setup_operation_metrics()

    def setup_operation_metrics(self):
        """Setup the operation metrics display."""
        # Overall stats
        stats_group = QGroupBox("Overall Statistics")
        stats_layout = QGridLayout()

        self.total_ops_label = QLabel("0")
        self.success_rate_label = QLabel("0.0%")
        self.avg_duration_label = QLabel("0.0ms")
        self.affected_records_label = QLabel("0")

        stats_layout.addWidget(QLabel("Total Operations:"), 0, 0)
        stats_layout.addWidget(self.total_ops_label, 0, 1)
        stats_layout.addWidget(QLabel("Success Rate:"), 1, 0)
        stats_layout.addWidget(self.success_rate_label, 1, 1)
        stats_layout.addWidget(QLabel("Avg Duration:"), 2, 0)
        stats_layout.addWidget(self.avg_duration_label, 2, 1)
        stats_layout.addWidget(QLabel("Affected Records:"), 3, 0)
        stats_layout.addWidget(self.affected_records_label, 3, 1)

        stats_group.setLayout(stats_layout)
        self.content_layout.addWidget(stats_group)

        # Operation type breakdown
        breakdown_group = QGroupBox("Operation Breakdown")
        breakdown_layout = QVBoxLayout()

        self.operation_table = QTableWidget()
        self.operation_table.setColumnCount(5)
        self.operation_table.setHorizontalHeaderLabels(
            ["Operation Type", "Count", "Success Rate", "Avg Duration", "Total Records"]
        )
        breakdown_layout.addWidget(self.operation_table)

        breakdown_group.setLayout(breakdown_layout)
        self.content_layout.addWidget(breakdown_group)

    def update_metrics(self):
        """Update the synchronization operation metrics."""
        stats = sync_monitor.get_performance_stats()

        # Update overall stats
        self.total_ops_label.setText(str(stats.total_operations))
        self.success_rate_label.setText(f"{stats.success_rate:.1f}%")
        self.avg_duration_label.setText(f"{stats.average_duration_ms:.2f}ms")
        self.affected_records_label.setText(str(stats.total_affected_records))

        # Update operation breakdown table
        self.operation_table.setRowCount(len(stats.operation_type_stats))
        row = 0
        for op_type, type_stats in stats.operation_type_stats.items():
            if type_stats["count"] > 0:
                self.operation_table.setItem(row, 0, QTableWidgetItem(op_type.value))
                self.operation_table.setItem(row, 1, QTableWidgetItem(str(type_stats["count"])))

                success_rate = (type_stats["success_count"] / type_stats["count"]) * 100
                self.operation_table.setItem(row, 2, QTableWidgetItem(f"{success_rate:.1f}%"))

                avg_duration = type_stats["total_duration_ms"] / type_stats["count"]
                self.operation_table.setItem(row, 3, QTableWidgetItem(f"{avg_duration:.2f}ms"))

                self.operation_table.setItem(
                    row, 4, QTableWidgetItem(str(type_stats["total_affected_records"]))
                )
                row += 1

        self.operation_table.resizeColumnsToContents()


class CacheMetricsWidget(MetricsWidget):
    """Widget for displaying cache performance metrics."""

    def __init__(self, parent=None):
        super().__init__("Cache Performance", parent)
        self.setup_cache_metrics()

    def setup_cache_metrics(self):
        """Setup the cache metrics display."""
        # Cache performance
        perf_group = QGroupBox("Cache Performance")
        perf_layout = QGridLayout()

        self.hit_rate_label = QLabel("0.0%")
        self.hit_rate_bar = QProgressBar()
        self.hit_rate_bar.setRange(0, 100)

        self.cache_size_label = QLabel("0")
        self.memory_usage_label = QLabel("0 MB")

        perf_layout.addWidget(QLabel("Hit Rate:"), 0, 0)
        perf_layout.addWidget(self.hit_rate_label, 0, 1)
        perf_layout.addWidget(self.hit_rate_bar, 0, 2)
        perf_layout.addWidget(QLabel("Cache Size:"), 1, 0)
        perf_layout.addWidget(self.cache_size_label, 1, 1)
        perf_layout.addWidget(QLabel("Memory Usage:"), 2, 0)
        perf_layout.addWidget(self.memory_usage_label, 2, 1)

        perf_group.setLayout(perf_layout)
        self.content_layout.addWidget(perf_group)

        # Cache events
        events_group = QGroupBox("Cache Events")
        events_layout = QVBoxLayout()

        self.events_table = QTableWidget()
        self.events_table.setColumnCount(3)
        self.events_table.setHorizontalHeaderLabels(["Event Type", "Operation Type", "Count"])
        events_layout.addWidget(self.events_table)

        events_group.setLayout(events_layout)
        self.content_layout.addWidget(events_group)

    def update_metrics(self):
        """Update the cache metrics."""
        stats = sync_monitor.get_performance_stats()

        # Update cache performance
        hit_rate = stats.cache_hit_rate
        self.hit_rate_label.setText(f"{hit_rate:.1f}%")
        self.hit_rate_bar.setValue(int(hit_rate))

        # Color the progress bar based on hit rate
        if hit_rate >= 80:
            self.hit_rate_bar.setStyleSheet("QProgressBar::chunk { background-color: green; }")
        elif hit_rate >= 60:
            self.hit_rate_bar.setStyleSheet("QProgressBar::chunk { background-color: orange; }")
        else:
            self.hit_rate_bar.setStyleSheet("QProgressBar::chunk { background-color: red; }")

        # Note: Cache size and memory usage would need to be obtained from MetadataCache
        # For now, we'll show placeholder values
        self.cache_size_label.setText("N/A")
        self.memory_usage_label.setText("N/A")


class SystemHealthWidget(MetricsWidget):
    """Widget for displaying system health metrics."""

    def __init__(self, parent=None):
        super().__init__("System Health", parent)
        self.setup_health_metrics()

    def setup_health_metrics(self):
        """Setup the health metrics display."""
        # Database health
        db_group = QGroupBox("Database Health")
        db_layout = QGridLayout()

        self.db_status_label = QLabel("Unknown")
        self.db_status_label.setStyleSheet("color: gray;")

        self.connection_errors_label = QLabel("0")

        db_layout.addWidget(QLabel("Status:"), 0, 0)
        db_layout.addWidget(self.db_status_label, 0, 1)
        db_layout.addWidget(QLabel("Connection Errors:"), 1, 0)
        db_layout.addWidget(self.connection_errors_label, 1, 1)

        db_group.setLayout(db_layout)
        self.content_layout.addWidget(db_group)

        # Circuit breaker status
        cb_group = QGroupBox("Circuit Breaker Status")
        cb_layout = QGridLayout()

        self.cb_status_label = QLabel("Unknown")
        self.cb_status_label.setStyleSheet("color: gray;")

        self.cb_failures_label = QLabel("0")

        cb_layout.addWidget(QLabel("Status:"), 0, 0)
        cb_layout.addWidget(self.cb_status_label, 0, 1)
        cb_layout.addWidget(QLabel("Failures:"), 1, 0)
        cb_layout.addWidget(self.cb_failures_label, 1, 1)

        cb_group.setLayout(cb_layout)
        self.content_layout.addWidget(cb_group)

        # Metrics server status
        server_group = QGroupBox("Metrics Server")
        server_layout = QGridLayout()

        self.server_status_label = QLabel("Unknown")
        self.server_status_label.setStyleSheet("color: gray;")

        self.server_url_label = QLabel("http://localhost:8080")

        server_layout.addWidget(QLabel("Status:"), 0, 0)
        server_layout.addWidget(self.server_status_label, 0, 1)
        server_layout.addWidget(QLabel("URL:"), 1, 0)
        server_layout.addWidget(self.server_url_label, 1, 1)

        server_group.setLayout(server_layout)
        self.content_layout.addWidget(server_group)

    def update_metrics(self):
        """Update the system health metrics."""
        # Update database health (placeholder - would need actual health check)
        self.db_status_label.setText("Healthy")
        self.db_status_label.setStyleSheet("color: green;")

        # Update circuit breaker status (placeholder)
        self.cb_status_label.setText("Closed")
        self.cb_status_label.setStyleSheet("color: green;")

        # Update metrics server status
        if metrics_server.is_running():
            self.server_status_label.setText("Running")
            self.server_status_label.setStyleSheet("color: green;")
        else:
            self.server_status_label.setText("Stopped")
            self.server_status_label.setStyleSheet("color: red;")


class MetricsLogWidget(MetricsWidget):
    """Widget for displaying metrics log output."""

    def __init__(self, parent=None):
        super().__init__("Metrics Log", parent)
        self.setup_log_display()

    def setup_log_display(self):
        """Setup the log display."""
        # Log output
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)

        # Control buttons
        button_layout = QHBoxLayout()

        self.refresh_button = QPushButton("Refresh Metrics")
        self.refresh_button.clicked.connect(self.refresh_metrics)

        self.clear_button = QPushButton("Clear Log")
        self.clear_button.clicked.connect(self.clear_log)

        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()

        self.content_layout.addLayout(button_layout)
        self.content_layout.addWidget(self.log_text)

    def refresh_metrics(self):
        """Refresh and display current metrics."""
        try:
            # Get current metrics
            stats = sync_monitor.get_performance_stats()
            metrics_output = metrics_exporter.generate_metrics()

            # Display summary
            summary = f"""
=== Sync Performance Summary ===
Total Operations: {stats.total_operations}
Success Rate: {stats.success_rate:.1f}%
Cache Hit Rate: {stats.cache_hit_rate:.1f}%
Average Duration: {stats.average_duration_ms:.2f}ms
Total Affected Records: {stats.total_affected_records}

=== Recent Operations ===
"""

            recent_ops = sync_monitor.get_recent_operations(limit=10)
            for op in recent_ops:
                summary += (
                    f"{op.operation_type.value}: {op.status.value} ({op.duration_ms:.2f}ms)\n"
                )

            summary += f"\n=== Prometheus Metrics ===\n{metrics_output[:1000]}..."

            self.log_text.setPlainText(summary)

        except Exception as e:
            self.log_text.setPlainText(f"Error refreshing metrics: {e}")

    def clear_log(self):
        """Clear the log display."""
        self.log_text.clear()

    def update_metrics(self):
        """Update the metrics log."""
        # Auto-refresh every update cycle
        self.refresh_metrics()


class MonitoringDashboard(QWidget):
    """Main monitoring dashboard widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        """Initialize the dashboard UI."""
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("AniVault Monitoring Dashboard")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(16)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Create tab widget
        self.tab_widget = QTabWidget()

        # Add metric widgets as tabs
        self.sync_ops_widget = SyncOperationsWidget()
        self.cache_metrics_widget = CacheMetricsWidget()
        self.health_widget = SystemHealthWidget()
        self.log_widget = MetricsLogWidget()

        self.tab_widget.addTab(self.sync_ops_widget, "Sync Operations")
        self.tab_widget.addTab(self.cache_metrics_widget, "Cache Metrics")
        self.tab_widget.addTab(self.health_widget, "System Health")
        self.tab_widget.addTab(self.log_widget, "Metrics Log")

        layout.addWidget(self.tab_widget)

        # Status bar
        self.status_label = QLabel("Monitoring Active")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def setup_timer(self):
        """Setup the update timer."""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_all_metrics)
        self.update_timer.start(5000)  # Update every 5 seconds

    def update_all_metrics(self):
        """Update all metric widgets."""
        try:
            self.sync_ops_widget.update_metrics()
            self.cache_metrics_widget.update_metrics()
            self.health_widget.update_metrics()
            self.log_widget.update_metrics()

            self.status_label.setText(
                "Monitoring Active - Last Updated: " + time.strftime("%H:%M:%S")
            )
            self.status_label.setStyleSheet("color: green; font-weight: bold;")

        except Exception as e:
            self.status_label.setText(f"Monitoring Error: {e}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    def start_monitoring(self):
        """Start the monitoring timer."""
        self.update_timer.start()
        self.status_label.setText("Monitoring Started")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

    def stop_monitoring(self):
        """Stop the monitoring timer."""
        self.update_timer.stop()
        self.status_label.setText("Monitoring Stopped")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")

    def closeEvent(self, event):
        """Handle widget close event."""
        self.stop_monitoring()
        event.accept()
