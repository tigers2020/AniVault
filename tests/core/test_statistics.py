"""
Tests for the statistics collection module.
"""

import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from anivault.core.statistics import (
    BenchmarkResult,
    PerformanceMetrics,
    StatisticsCollector,
    get_statistics_collector,
    reset_statistics,
)


class TestPerformanceMetrics:
    """Test the PerformanceMetrics dataclass."""

    def test_initialization(self):
        """Test that PerformanceMetrics initializes with default values."""
        metrics = PerformanceMetrics()

        assert metrics.total_time == 0.0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.cache_hit_ratio == 0.0
        assert metrics.total_files == 0
        assert metrics.successful_matches == 0
        assert metrics.failed_matches == 0
        assert metrics.match_success_rate == 0.0

    def test_cache_hit_ratio_calculation(self):
        """Test that cache hit ratio is calculated correctly."""
        metrics = PerformanceMetrics()
        metrics.cache_hits = 8
        metrics.cache_misses = 2

        # Trigger __post_init__ by creating a new instance
        metrics = PerformanceMetrics(cache_hits=8, cache_misses=2)
        assert metrics.cache_hit_ratio == 0.8

    def test_cache_hit_ratio_zero_operations(self):
        """Test that cache hit ratio is 0 when no operations."""
        metrics = PerformanceMetrics()
        assert metrics.cache_hit_ratio == 0.0

    def test_match_success_rate_calculation(self):
        """Test that match success rate is calculated correctly."""
        metrics = PerformanceMetrics(total_files=10, successful_matches=7)
        assert metrics.match_success_rate == 0.7

    def test_match_success_rate_zero_files(self):
        """Test that match success rate is 0 when no files."""
        metrics = PerformanceMetrics()
        assert metrics.match_success_rate == 0.0


class TestBenchmarkResult:
    """Test the BenchmarkResult dataclass."""

    def test_initialization(self):
        """Test that BenchmarkResult initializes correctly."""
        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc)
        metrics = PerformanceMetrics()

        result = BenchmarkResult(
            test_name="test_benchmark",
            start_time=start_time,
            end_time=end_time,
            duration=1.5,
            metrics=metrics,
            success=True,
        )

        assert result.test_name == "test_benchmark"
        assert result.start_time == start_time
        assert result.end_time == end_time
        assert result.duration == 1.5
        assert result.success is True
        assert result.error_message is None

    def test_duration_calculation(self):
        """Test that duration is calculated if not provided."""
        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc)
        metrics = PerformanceMetrics()

        result = BenchmarkResult(
            test_name="test_benchmark",
            start_time=start_time,
            end_time=end_time,
            duration=0.0,  # Will be calculated
            metrics=metrics,
            success=True,
        )

        assert result.duration > 0.0


class TestStatisticsCollector:
    """Test the StatisticsCollector class."""

    def test_initialization(self):
        """Test that StatisticsCollector initializes correctly."""
        collector = StatisticsCollector()

        assert isinstance(collector.metrics, PerformanceMetrics)
        assert len(collector.benchmark_results) == 0
        assert isinstance(collector.session_start, datetime)
        assert len(collector.timing_stack) == 0
        assert len(collector.file_metrics) == 0
        assert len(collector.api_call_times) == 0
        assert len(collector.cache_operations) == 0

    def test_timing_operations(self):
        """Test timing start and end operations."""
        collector = StatisticsCollector()

        # Start timing
        collector.start_timing("test_operation")
        assert len(collector.timing_stack) == 1

        # End timing
        time.sleep(0.01)  # Small delay to ensure non-zero duration
        duration = collector.end_timing("test_operation")

        assert len(collector.timing_stack) == 0
        assert duration > 0.0

    def test_end_timing_without_start(self):
        """Test ending timing without starting."""
        collector = StatisticsCollector()

        duration = collector.end_timing("test_operation")
        assert duration == 0.0

    def test_record_matching_operation_success(self):
        """Test recording a successful matching operation."""
        collector = StatisticsCollector()

        collector.record_matching_operation(
            file_path="/test/file.mkv",
            success=True,
            confidence=0.85,
            duration=1.5,
            used_fallback=False,
        )

        assert collector.metrics.total_files == 1
        assert collector.metrics.successful_matches == 1
        assert collector.metrics.failed_matches == 0
        assert collector.metrics.high_confidence_matches == 1
        assert collector.metrics.medium_confidence_matches == 0
        assert collector.metrics.low_confidence_matches == 0

        # Check file metrics
        assert "/test/file.mkv" in collector.file_metrics
        file_metrics = collector.file_metrics["/test/file.mkv"]
        assert file_metrics["success"] is True
        assert file_metrics["confidence"] == 0.85
        assert file_metrics["duration"] == 1.5
        assert file_metrics["used_fallback"] is False

    def test_record_matching_operation_failure(self):
        """Test recording a failed matching operation."""
        collector = StatisticsCollector()

        collector.record_matching_operation(
            file_path="/test/file.mkv",
            success=False,
            confidence=None,
            duration=2.0,
            used_fallback=True,
        )

        assert collector.metrics.total_files == 1
        assert collector.metrics.successful_matches == 0
        assert collector.metrics.failed_matches == 1
        assert collector.metrics.high_confidence_matches == 0
        assert collector.metrics.medium_confidence_matches == 0
        assert collector.metrics.low_confidence_matches == 0

    def test_record_matching_operation_confidence_levels(self):
        """Test recording matching operations with different confidence levels."""
        collector = StatisticsCollector()

        # High confidence
        collector.record_matching_operation("/test1.mkv", True, 0.9)
        assert collector.metrics.high_confidence_matches == 1

        # Medium confidence
        collector.record_matching_operation("/test2.mkv", True, 0.7)
        assert collector.metrics.medium_confidence_matches == 1

        # Low confidence
        collector.record_matching_operation("/test3.mkv", True, 0.5)
        assert collector.metrics.low_confidence_matches == 1

        assert collector.metrics.total_files == 3
        assert collector.metrics.successful_matches == 3

    def test_record_cache_operation(self):
        """Test recording cache operations."""
        collector = StatisticsCollector()

        # Cache hit
        collector.record_cache_operation("get", True, 0.1, "test_key")
        assert collector.metrics.cache_hits == 1
        assert collector.metrics.cache_misses == 0

        # Cache miss
        collector.record_cache_operation("get", False, 0.2, "test_key2")
        assert collector.metrics.cache_hits == 1
        assert collector.metrics.cache_misses == 1

        # Check cache operations list
        assert len(collector.cache_operations) == 2
        assert collector.cache_operations[0]["operation"] == "get"
        assert collector.cache_operations[0]["hit"] is True
        assert collector.cache_operations[1]["hit"] is False

    def test_record_api_call(self):
        """Test recording API calls."""
        collector = StatisticsCollector()

        # Successful API call
        collector.record_api_call("search", True, 0.5)
        assert collector.metrics.api_calls == 1
        assert collector.metrics.api_errors == 0
        assert collector.metrics.api_time == 0.5

        # Failed API call
        collector.record_api_call("search", False, 0.3, "Rate limit exceeded")
        assert collector.metrics.api_calls == 2
        assert collector.metrics.api_errors == 1
        assert collector.metrics.api_time == 0.8

    def test_record_rate_limit_hit(self):
        """Test recording rate limit hits."""
        collector = StatisticsCollector()

        collector.record_rate_limit_hit()
        assert collector.metrics.rate_limit_hits == 1

        collector.record_rate_limit_hit()
        assert collector.metrics.rate_limit_hits == 2

    def test_record_memory_usage(self):
        """Test recording memory usage."""
        collector = StatisticsCollector()

        collector.record_memory_usage(100.0)
        assert collector.metrics.peak_memory_mb == 100.0
        assert collector.metrics.average_memory_mb == 100.0

        collector.record_memory_usage(150.0)
        assert collector.metrics.peak_memory_mb == 150.0
        assert collector.metrics.average_memory_mb == 125.0

        collector.record_memory_usage(120.0)
        assert collector.metrics.peak_memory_mb == 150.0
        assert abs(collector.metrics.average_memory_mb - 123.33) < 0.01

    def test_benchmark_operations(self):
        """Test benchmark start and end operations."""
        collector = StatisticsCollector()

        # Start benchmark
        collector.start_benchmark("test_benchmark")
        assert len(collector.timing_stack) == 1

        # End benchmark
        time.sleep(0.01)
        result = collector.end_benchmark("test_benchmark", success=True)

        assert len(collector.timing_stack) == 0
        assert len(collector.benchmark_results) == 1
        assert result.test_name == "test_benchmark"
        assert result.success is True
        assert result.duration > 0.0

    def test_benchmark_with_error(self):
        """Test benchmark with error."""
        collector = StatisticsCollector()

        collector.start_benchmark("test_benchmark")
        result = collector.end_benchmark(
            "test_benchmark",
            success=False,
            error_message="Test error",
        )

        assert result.success is False
        assert result.error_message == "Test error"

    def test_get_summary(self):
        """Test getting summary statistics."""
        collector = StatisticsCollector()

        # Add some test data
        collector.record_matching_operation("/test1.mkv", True, 0.9)
        collector.record_matching_operation("/test2.mkv", False)
        collector.record_cache_operation("get", True, 0.1)
        collector.record_cache_operation("get", False, 0.2)
        collector.record_api_call("search", True, 0.5)
        collector.record_memory_usage(100.0)

        summary = collector.get_summary()

        assert "session_info" in summary
        assert "performance_metrics" in summary
        assert "detailed_metrics" in summary

        metrics = summary["performance_metrics"]
        assert metrics["total_files"] == 2
        assert metrics["successful_matches"] == 1
        assert metrics["failed_matches"] == 1
        assert metrics["cache_hits"] == 1
        assert metrics["cache_misses"] == 1
        assert metrics["api_calls"] == 1
        assert metrics["peak_memory_mb"] == 100.0

    def test_export_to_json(self):
        """Test exporting statistics to JSON format."""
        collector = StatisticsCollector()

        # Add some test data
        collector.record_matching_operation("/test.mkv", True, 0.8)
        collector.record_cache_operation("get", True, 0.1)
        collector.record_api_call("search", True, 0.5)

        json_data = collector.export_to_json()

        assert "summary" in json_data
        assert "file_metrics" in json_data
        assert "cache_operations" in json_data
        assert "api_call_times" in json_data
        assert "benchmark_results" in json_data

        # Check that all data is JSON-serializable
        import json

        json.dumps(json_data)  # Should not raise an exception

    def test_reset(self):
        """Test resetting the collector."""
        collector = StatisticsCollector()

        # Add some data
        collector.record_matching_operation("/test.mkv", True, 0.8)
        collector.record_cache_operation("get", True, 0.1)
        collector.start_benchmark("test")
        collector.end_benchmark("test")

        # Reset
        collector.reset()

        assert collector.metrics.total_files == 0
        assert len(collector.benchmark_results) == 0
        assert len(collector.timing_stack) == 0
        assert len(collector.file_metrics) == 0
        assert len(collector.api_call_times) == 0
        assert len(collector.cache_operations) == 0


class TestGlobalFunctions:
    """Test global functions."""

    def test_get_statistics_collector(self):
        """Test getting the global statistics collector."""
        collector1 = get_statistics_collector()
        collector2 = get_statistics_collector()

        assert collector1 is collector2  # Should be the same instance

    def test_reset_statistics(self):
        """Test resetting global statistics."""
        collector = get_statistics_collector()
        collector.record_matching_operation("/test.mkv", True, 0.8)

        assert collector.metrics.total_files == 1

        reset_statistics()

        assert collector.metrics.total_files == 0
