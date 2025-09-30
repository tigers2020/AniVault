"""
Tests for Statistics base class implementation.
"""

import pytest
import time
import threading
from typing import List
from src.anivault.core.statistics import (
    Statistics,
    MetricType,
    MetricValue,
    HistogramData,
)


class MockStatistics(Statistics):
    """Test implementation of Statistics abstract class."""

    def _record_metric(self, name: str, metric_type: MetricType, value, tags=None):
        """Implementation of abstract method for testing."""
        # Simple implementation that just stores the metric
        self._metrics[name].append(
            MetricValue(value=value, timestamp=time.time(), tags=tags or {})
        )


class TestStatisticsClass:
    """Test cases for Statistics base class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.stats = MockStatistics("test_stats", max_history=100)

    def teardown_method(self) -> None:
        """Clean up after tests."""
        if hasattr(self, "stats"):
            self.stats.reset()

    def test_initialization(self) -> None:
        """Test statistics initialization."""
        assert self.stats.name == "test_stats"
        assert self.stats.max_history == 100
        assert self.stats.get_uptime() >= 0

    def test_counter_operations(self) -> None:
        """Test counter metric operations."""
        # Test increment
        self.stats.increment_counter("test_counter")
        assert self.stats.get_counter("test_counter") == 1

        # Test increment by value
        self.stats.increment_counter("test_counter", 5)
        assert self.stats.get_counter("test_counter") == 6

        # Test multiple counters
        self.stats.increment_counter("other_counter", 3)
        assert self.stats.get_counter("other_counter") == 3
        assert self.stats.get_counter("test_counter") == 6

    def test_gauge_operations(self) -> None:
        """Test gauge metric operations."""
        # Test set gauge
        self.stats.set_gauge("test_gauge", 42.5)
        assert self.stats.get_gauge("test_gauge") == 42.5

        # Test update gauge
        self.stats.set_gauge("test_gauge", 100.0)
        assert self.stats.get_gauge("test_gauge") == 100.0

        # Test non-existent gauge
        assert self.stats.get_gauge("non_existent") is None

    def test_histogram_operations(self) -> None:
        """Test histogram metric operations."""
        # Record histogram values
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            self.stats.record_histogram("test_histogram", value)

        # Get histogram data
        hist_data = self.stats.get_histogram_data("test_histogram")
        assert hist_data is not None
        assert hist_data.count == 5
        assert hist_data.sum == 15.0
        assert hist_data.min == 1.0
        assert hist_data.max == 5.0
        assert hist_data.mean == 3.0

    def test_timer_operations(self) -> None:
        """Test timer metric operations."""
        # Record timer durations
        durations = [0.1, 0.2, 0.3, 0.4, 0.5]
        for duration in durations:
            self.stats.record_timer("test_timer", duration)

        # Get timer data
        timer_data = self.stats.get_timer_data("test_timer")
        assert timer_data is not None
        assert timer_data.count == 5
        assert timer_data.sum == 1.5
        assert timer_data.min == 0.1
        assert timer_data.max == 0.5
        assert timer_data.mean == 0.3

    def test_rate_operations(self) -> None:
        """Test rate metric operations."""
        # Record rate values over time
        current_time = time.time()
        for i in range(10):
            self.stats.record_rate("test_rate", i * 10, {"iteration": str(i)})
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Get rate
        rate = self.stats.get_rate("test_rate", window_seconds=1)
        assert rate is not None
        assert rate > 0

    def test_time_function(self) -> None:
        """Test timing function execution."""

        def test_function(delay: float) -> str:
            time.sleep(delay)
            return "completed"

        # Time a function
        result = self.stats.time_function("function_timer", test_function, 0.1)
        assert result == "completed"

        # Check timer data was recorded
        timer_data = self.stats.get_timer_data("function_timer")
        assert timer_data is not None
        assert timer_data.count == 1
        assert timer_data.mean >= 0.1

    def test_percentile_calculation(self) -> None:
        """Test percentile calculation."""
        # Record values for percentile calculation
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for value in values:
            self.stats.record_histogram("percentile_test", float(value))

        hist_data = self.stats.get_histogram_data("percentile_test")
        assert hist_data is not None
        assert 50.0 in hist_data.percentiles
        assert 90.0 in hist_data.percentiles
        assert 95.0 in hist_data.percentiles
        assert 99.0 in hist_data.percentiles

        # Check percentile values are reasonable
        assert hist_data.percentiles[50.0] <= hist_data.percentiles[90.0]
        assert hist_data.percentiles[90.0] <= hist_data.percentiles[95.0]
        assert hist_data.percentiles[95.0] <= hist_data.percentiles[99.0]

    def test_get_all_metrics(self) -> None:
        """Test getting all metrics."""
        # Add various metrics
        self.stats.increment_counter("counter1", 5)
        self.stats.set_gauge("gauge1", 42.0)
        self.stats.record_histogram("hist1", 1.0)
        self.stats.record_timer("timer1", 0.5)
        self.stats.record_rate("rate1", 10.0)

        all_metrics = self.stats.get_all_metrics()

        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "histograms" in all_metrics
        assert "timers" in all_metrics
        assert "rates" in all_metrics

        assert all_metrics["counters"]["counter1"] == 5
        assert all_metrics["gauges"]["gauge1"] == 42.0

    def test_reset_operation(self) -> None:
        """Test resetting all metrics."""
        # Add some metrics
        self.stats.increment_counter("test_counter", 10)
        self.stats.set_gauge("test_gauge", 100.0)
        self.stats.record_histogram("test_histogram", 5.0)

        # Verify metrics exist
        assert self.stats.get_counter("test_counter") == 10
        assert self.stats.get_gauge("test_gauge") == 100.0
        assert self.stats.get_histogram_data("test_histogram") is not None

        # Reset
        self.stats.reset()

        # Verify metrics are cleared
        assert self.stats.get_counter("test_counter") == 0
        assert self.stats.get_gauge("test_gauge") is None
        assert self.stats.get_histogram_data("test_histogram") is None

    def test_export_metrics(self) -> None:
        """Test exporting metrics."""
        # Add some metrics
        self.stats.increment_counter("export_test", 5)
        self.stats.set_gauge("export_gauge", 25.0)

        export_data = self.stats.export_metrics()

        assert "name" in export_data
        assert "uptime" in export_data
        assert "timestamp" in export_data
        assert "metrics" in export_data

        assert export_data["name"] == "test_stats"
        assert export_data["uptime"] >= 0
        assert export_data["timestamp"] > 0

    def test_max_history_limit(self) -> None:
        """Test max history limit."""
        # Create stats with small history limit
        limited_stats = MockStatistics("limited", max_history=5)

        try:
            # Add more items than history limit
            for i in range(10):
                limited_stats.record_histogram("test", float(i))

            # Should only keep recent 5 items
            hist_data = limited_stats.get_histogram_data("test")
            assert hist_data is not None
            assert hist_data.count == 5  # Should be limited to 5

        finally:
            limited_stats.reset()

    def test_thread_safety(self) -> None:
        """Test thread safety with concurrent access."""
        results: list[Exception] = []

        def worker(thread_id: int):
            """Worker thread."""
            try:
                for i in range(100):
                    self.stats.increment_counter(f"thread_{thread_id}_counter")
                    self.stats.set_gauge(f"thread_{thread_id}_gauge", float(i))
                    self.stats.record_histogram(f"thread_{thread_id}_hist", float(i))
                    time.sleep(0.001)
            except Exception as e:
                results.append(e)

        # Start multiple threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Check for errors
        assert len(results) == 0, f"Thread safety errors: {results}"

        # Verify counters were incremented
        for i in range(5):
            assert self.stats.get_counter(f"thread_{i}_counter") == 100

    def test_empty_histogram_data(self) -> None:
        """Test getting histogram data from empty histogram."""
        hist_data = self.stats.get_histogram_data("non_existent")
        assert hist_data is None

    def test_empty_timer_data(self) -> None:
        """Test getting timer data from empty timer."""
        timer_data = self.stats.get_timer_data("non_existent")
        assert timer_data is None

    def test_empty_rate_data(self) -> None:
        """Test getting rate data from empty rate."""
        rate = self.stats.get_rate("non_existent")
        assert rate is None

    def test_rate_calculation_with_insufficient_data(self) -> None:
        """Test rate calculation with insufficient data."""
        # Record rate with very old timestamp
        old_time = time.time() - 1000  # 1000 seconds ago
        self.stats._rates["old_rate"].append((old_time, 10.0))

        # Try to get rate with short window
        rate = self.stats.get_rate("old_rate", window_seconds=1)
        assert rate is None

    def test_string_representation(self) -> None:
        """Test string representation."""
        repr_str = repr(self.stats)
        assert "Statistics" in repr_str
        assert "test_stats" in repr_str
        assert "uptime" in repr_str

    def test_tags_support(self) -> None:
        """Test tags support in metrics."""
        # Test with tags
        self.stats.increment_counter(
            "tagged_counter", 1, {"env": "test", "service": "api"}
        )
        self.stats.set_gauge("tagged_gauge", 42.0, {"env": "test"})
        self.stats.record_histogram("tagged_hist", 1.0, {"env": "test"})
        self.stats.record_timer("tagged_timer", 0.1, {"env": "test"})
        self.stats.record_rate("tagged_rate", 5.0, {"env": "test"})

        # Verify metrics were recorded
        assert self.stats.get_counter("tagged_counter") == 1
        assert self.stats.get_gauge("tagged_gauge") == 42.0
        assert self.stats.get_histogram_data("tagged_hist") is not None
        assert self.stats.get_timer_data("tagged_timer") is not None
        assert self.stats.get_rate("tagged_rate") is not None

    def test_concurrent_metric_access(self) -> None:
        """Test concurrent access to the same metric."""

        def increment_counter():
            for _ in range(50):
                self.stats.increment_counter("concurrent_counter")

        # Start multiple threads incrementing the same counter
        threads = [threading.Thread(target=increment_counter) for _ in range(4)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify final counter value
        assert self.stats.get_counter("concurrent_counter") == 200
