"""
Tests for the synchronization performance profiling system.

This module tests the SyncProfiler, PerformanceAnalyzer, and PerformanceBenchmark
components to ensure they correctly identify and analyze performance bottlenecks.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.core.sync_profiler import (
    SyncProfiler, ProfilerEvent, PerformanceMetrics,
    get_sync_profiler, profile_operation
)
from src.core.performance_analyzer import (
    PerformanceAnalyzer, OptimizationPriority, OptimizationCategory,
    OptimizationRecommendation, BottleneckAnalysis
)
from src.core.performance_benchmark import (
    PerformanceBenchmark, BenchmarkResult, BenchmarkConfig
)


class TestSyncProfiler:
    """Test the SyncProfiler class."""

    def test_profiler_initialization(self):
        """Test profiler initialization."""
        profiler = SyncProfiler()
        assert profiler.max_history == 10000
        assert len(profiler.metrics_history) == 0
        assert len(profiler.stats_by_event) == 0
        assert len(profiler.stats_by_operation) == 0

    def test_profile_operation_context_manager(self):
        """Test profiling operations with context manager."""
        profiler = SyncProfiler()

        # Test successful operation
        with profiler.profile_operation(
            ProfilerEvent.CACHE_GET,
            "test_operation",
            operation_size=100
        ):
            time.sleep(0.01)  # Simulate work

        assert len(profiler.metrics_history) == 1

        metrics = profiler.metrics_history[0]
        assert metrics.event_type == ProfilerEvent.CACHE_GET
        assert metrics.operation_name == "test_operation"
        assert metrics.operation_size == 100
        assert metrics.success is True
        assert metrics.duration_ms > 0

    def test_profile_operation_with_exception(self):
        """Test profiling operations that raise exceptions."""
        profiler = SyncProfiler()

        # Test operation that raises exception
        with pytest.raises(ValueError):
            with profiler.profile_operation(
                ProfilerEvent.CACHE_SET,
                "failing_operation"
            ):
                raise ValueError("Test exception")

        assert len(profiler.metrics_history) == 1

        metrics = profiler.metrics_history[0]
        assert metrics.success is False
        assert metrics.error_message == "Test exception"

    def test_record_metrics(self):
        """Test recording metrics manually."""
        profiler = SyncProfiler()

        metrics = PerformanceMetrics(
            event_type=ProfilerEvent.DB_BULK_INSERT,
            operation_name="test_bulk_insert",
            start_time=time.time(),
            end_time=time.time() + 0.1,
            duration_ms=100,
            cpu_percent=50.0,
            memory_mb=100.0,
            memory_peak_mb=120.0,
            thread_id=threading.get_ident(),
            operation_size=1000
        )

        profiler.record_metrics(metrics)

        assert len(profiler.metrics_history) == 1
        assert ProfilerEvent.DB_BULK_INSERT in profiler.stats_by_event
        assert "test_bulk_insert" in profiler.stats_by_operation

    def test_get_stats_by_event(self):
        """Test getting statistics by event type."""
        profiler = SyncProfiler()

        # Add some test metrics
        for i in range(10):
            metrics = PerformanceMetrics(
                event_type=ProfilerEvent.CACHE_GET,
                operation_name=f"test_operation_{i}",
                start_time=time.time(),
                end_time=time.time() + 0.01,
                duration_ms=10,
                cpu_percent=10.0,
                memory_mb=50.0,
                memory_peak_mb=60.0,
                thread_id=threading.get_ident(),
                success=True
            )
            profiler.record_metrics(metrics)

        stats = profiler.get_stats_by_event(ProfilerEvent.CACHE_GET)
        assert stats.total_operations == 10
        assert stats.avg_duration_ms == 10.0
        assert stats.success_rate == 100.0

    def test_get_stats_by_operation(self):
        """Test getting statistics by operation name."""
        profiler = SyncProfiler()

        # Add test metrics
        for i in range(5):
            metrics = PerformanceMetrics(
                event_type=ProfilerEvent.DB_BULK_INSERT,
                operation_name="bulk_insert_test",
                start_time=time.time(),
                end_time=time.time() + 0.1,
                duration_ms=100,
                cpu_percent=20.0,
                memory_mb=80.0,
                memory_peak_mb=90.0,
                thread_id=threading.get_ident(),
                operation_size=1000
            )
            profiler.record_metrics(metrics)

        stats = profiler.get_stats_by_operation("bulk_insert_test")
        assert stats.total_operations == 5
        assert stats.avg_duration_ms == 100.0
        assert stats.avg_throughput_per_sec == 10000.0  # 1000 records / 0.1 seconds

    def test_get_top_bottlenecks(self):
        """Test getting top bottlenecks."""
        profiler = SyncProfiler()

        # Add metrics with different durations
        durations = [100, 200, 50, 300, 150]
        for i, duration in enumerate(durations):
            metrics = PerformanceMetrics(
                event_type=ProfilerEvent.DB_QUERY,
                operation_name=f"query_{i}",
                start_time=time.time(),
                end_time=time.time() + duration / 1000,
                duration_ms=duration,
                cpu_percent=10.0,
                memory_mb=50.0,
                memory_peak_mb=60.0,
                thread_id=threading.get_ident()
            )
            profiler.record_metrics(metrics)

        bottlenecks = profiler.get_top_bottlenecks(3)
        assert len(bottlenecks) == 3

        # Should be sorted by average duration (descending)
        assert bottlenecks[0]["avg_duration_ms"] == 300
        assert bottlenecks[1]["avg_duration_ms"] == 200
        assert bottlenecks[2]["avg_duration_ms"] == 150

    def test_get_performance_summary(self):
        """Test getting performance summary."""
        profiler = SyncProfiler()

        # Add some test metrics
        for i in range(3):
            metrics = PerformanceMetrics(
                event_type=ProfilerEvent.CACHE_SET,
                operation_name="test_set",
                start_time=time.time(),
                end_time=time.time() + 0.01,
                duration_ms=10,
                cpu_percent=5.0,
                memory_mb=40.0,
                memory_peak_mb=50.0,
                thread_id=threading.get_ident(),
                success=True
            )
            profiler.record_metrics(metrics)

        summary = profiler.get_performance_summary()
        assert summary["total_operations"] == 3
        assert summary["overall_stats"]["avg_duration_ms"] == 10.0
        assert summary["overall_stats"]["success_rate"] == 100.0
        assert ProfilerEvent.CACHE_SET.value in summary["event_type_stats"]

    def test_memory_tracking(self):
        """Test memory tracking functionality."""
        profiler = SyncProfiler()

        # Start memory tracking
        profiler.start_memory_tracking()

        # Get memory stats
        memory_stats = profiler.get_memory_stats()
        assert "rss_mb" in memory_stats
        assert "vms_mb" in memory_stats
        assert "percent" in memory_stats

        # Stop memory tracking
        profiler.stop_memory_tracking()

    def test_cpu_stats(self):
        """Test CPU statistics functionality."""
        profiler = SyncProfiler()

        cpu_stats = profiler.get_cpu_stats()
        assert "cpu_percent" in cpu_stats
        assert "cpu_count" in cpu_stats
        assert cpu_stats["cpu_count"] > 0

    def test_clear_metrics(self):
        """Test clearing metrics."""
        profiler = SyncProfiler()

        # Add some metrics
        metrics = PerformanceMetrics(
            event_type=ProfilerEvent.SYNC_OPERATION,
            operation_name="test_sync",
            start_time=time.time(),
            end_time=time.time() + 0.1,
            duration_ms=100,
            cpu_percent=30.0,
            memory_mb=70.0,
            memory_peak_mb=80.0,
            thread_id=threading.get_ident()
        )
        profiler.record_metrics(metrics)

        assert len(profiler.metrics_history) == 1

        # Clear metrics
        profiler.clear_metrics()

        assert len(profiler.metrics_history) == 0
        assert len(profiler.stats_by_event) == 0
        assert len(profiler.stats_by_operation) == 0

    def test_global_profiler_instance(self):
        """Test global profiler instance."""
        profiler1 = get_sync_profiler()
        profiler2 = get_sync_profiler()

        assert profiler1 is profiler2  # Should be the same instance


class TestPerformanceAnalyzer:
    """Test the PerformanceAnalyzer class."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        profiler = SyncProfiler()
        analyzer = PerformanceAnalyzer(profiler)

        assert analyzer.profiler is profiler
        assert len(analyzer.performance_thresholds) > 0

    def test_analyze_bottlenecks_empty(self):
        """Test analyzing bottlenecks with no data."""
        profiler = SyncProfiler()
        analyzer = PerformanceAnalyzer(profiler)

        bottlenecks = analyzer.analyze_bottlenecks()
        assert len(bottlenecks) == 0

    def test_analyze_bottlenecks_with_data(self):
        """Test analyzing bottlenecks with test data."""
        profiler = SyncProfiler()

        # Add slow operations to create bottlenecks
        for i in range(10):
            metrics = PerformanceMetrics(
                event_type=ProfilerEvent.DB_BULK_INSERT,
                operation_name="slow_bulk_insert",
                start_time=time.time(),
                end_time=time.time() + 2.0,  # 2 seconds - very slow
                duration_ms=2000,
                cpu_percent=80.0,
                memory_mb=200.0,
                memory_peak_mb=250.0,
                thread_id=threading.get_ident(),
                operation_size=1000,
                success=True
            )
            profiler.record_metrics(metrics)

        analyzer = PerformanceAnalyzer(profiler)
        bottlenecks = analyzer.analyze_bottlenecks()

        assert len(bottlenecks) > 0

        # Check that we found the slow operation
        slow_bottleneck = next(
            (b for b in bottlenecks if b.operation_name == "slow_bulk_insert"),
            None
        )
        assert slow_bottleneck is not None
        assert slow_bottleneck.severity_score > 50  # Should be high severity
        assert len(slow_bottleneck.recommendations) > 0

    def test_calculate_severity_score(self):
        """Test severity score calculation."""
        profiler = SyncProfiler()
        analyzer = PerformanceAnalyzer(profiler)

        # Test high severity bottleneck
        bottleneck_data = {
            "operation_name": "slow_operation",
            "event_type": "db_bulk_insert",
            "avg_duration_ms": 2000,  # Very slow
            "max_duration_ms": 3000,
            "avg_throughput_per_sec": 100,  # Very low throughput
            "total_operations": 1000,  # High frequency
            "success_rate": 90.0  # Some failures
        }

        severity = analyzer._calculate_severity_score(
            bottleneck_data,
            ProfilerEvent.DB_BULK_INSERT
        )

        assert severity > 70  # Should be high severity

        # Test low severity bottleneck
        bottleneck_data_low = {
            "operation_name": "fast_operation",
            "event_type": "cache_get",
            "avg_duration_ms": 5,  # Fast
            "max_duration_ms": 10,
            "avg_throughput_per_sec": 2000,  # High throughput
            "total_operations": 10,  # Low frequency
            "success_rate": 100.0  # No failures
        }

        severity_low = analyzer._calculate_severity_score(
            bottleneck_data_low,
            ProfilerEvent.CACHE_GET
        )

        assert severity_low < 30  # Should be low severity

    def test_identify_root_causes(self):
        """Test root cause identification."""
        profiler = SyncProfiler()
        analyzer = PerformanceAnalyzer(profiler)

        # Test high variance bottleneck
        bottleneck_data = {
            "operation_name": "variable_operation",
            "avg_duration_ms": 100,
            "max_duration_ms": 500,  # High variance
            "avg_throughput_per_sec": 50,
            "success_rate": 85.0  # Some failures
        }

        root_causes = analyzer._identify_root_causes(
            bottleneck_data,
            ProfilerEvent.DB_BULK_INSERT
        )

        assert "High performance variance" in root_causes
        assert "High failure rate" in root_causes
        assert "Low bulk operation throughput" in root_causes

    def test_generate_recommendations(self):
        """Test recommendation generation."""
        profiler = SyncProfiler()
        analyzer = PerformanceAnalyzer(profiler)

        bottleneck_data = {
            "operation_name": "slow_bulk_insert",
            "avg_duration_ms": 1500,  # Slow
            "avg_throughput_per_sec": 400,  # Low throughput
            "success_rate": 95.0
        }

        recommendations = analyzer._generate_recommendations(
            "slow_bulk_insert",
            ProfilerEvent.DB_BULK_INSERT,
            bottleneck_data,
            ["Low bulk operation throughput"]
        )

        assert len(recommendations) > 0

        # Should have database optimization recommendations
        db_recommendations = [
            r for r in recommendations
            if r.category == OptimizationCategory.DATABASE
        ]
        assert len(db_recommendations) > 0

        # Check recommendation content
        rec = db_recommendations[0]
        assert rec.priority == OptimizationPriority.CRITICAL
        assert "bulk" in rec.title.lower()
        assert len(rec.specific_actions) > 0

    def test_generate_performance_report(self):
        """Test performance report generation."""
        profiler = SyncProfiler()

        # Add some test data
        for i in range(5):
            metrics = PerformanceMetrics(
                event_type=ProfilerEvent.CACHE_GET,
                operation_name="test_cache_get",
                start_time=time.time(),
                end_time=time.time() + 0.01,
                duration_ms=10,
                cpu_percent=5.0,
                memory_mb=40.0,
                memory_peak_mb=50.0,
                thread_id=threading.get_ident(),
                success=True
            )
            profiler.record_metrics(metrics)

        analyzer = PerformanceAnalyzer(profiler)
        report = analyzer.generate_performance_report()

        assert "analysis_timestamp" in report
        assert "overall_performance" in report
        assert "bottleneck_analysis" in report
        assert "optimization_recommendations" in report
        assert "performance_targets" in report

        # Check recommendation categories
        recommendations = report["optimization_recommendations"]
        assert "critical" in recommendations
        assert "high" in recommendations
        assert "medium" in recommendations
        assert "low" in recommendations


class TestPerformanceBenchmark:
    """Test the PerformanceBenchmark class."""

    def test_benchmark_initialization(self):
        """Test benchmark initialization."""
        benchmark = PerformanceBenchmark()

        assert benchmark.metadata_cache is not None
        assert benchmark.profiler is not None
        assert benchmark.incremental_sync_manager is not None
        assert benchmark.consistency_scheduler is not None
        assert len(benchmark.benchmark_results) == 0

    def test_benchmark_config(self):
        """Test benchmark configuration."""
        config = BenchmarkConfig(
            name="test_benchmark",
            operation_count=100,
            batch_size=10,
            concurrent_threads=2
        )

        assert config.name == "test_benchmark"
        assert config.operation_count == 100
        assert config.batch_size == 10
        assert config.concurrent_threads == 2

    def test_run_operations_batch(self):
        """Test running a batch of operations."""
        benchmark = PerformanceBenchmark()

        def mock_operation(batch_size):
            time.sleep(0.001)  # Simulate work
            return 1.0, True, {"test_metric": batch_size}

        durations, successes, errors, metrics = benchmark._run_operations_batch(
            mock_operation, 10, 2
        )

        assert len(durations) == 5  # 10 operations / 2 batch size
        assert len(successes) == 5
        assert all(successes)  # All should succeed
        assert len(errors) == 0
        assert "test_metric" in metrics

    def test_get_test_data(self):
        """Test test data generation."""
        benchmark = PerformanceBenchmark()

        # Test anime metadata generation
        anime_data = benchmark._get_test_data("anime_metadata", 5)
        assert len(anime_data) == 5
        assert all("id" in item for item in anime_data)
        assert all("title" in item for item in anime_data)

        # Test caching
        anime_data_cached = benchmark._get_test_data("anime_metadata", 5)
        assert anime_data is anime_data_cached  # Should be same object

        # Test TMDB anime generation
        tmdb_data = benchmark._get_test_data("tmdb_anime", 3)
        assert len(tmdb_data) == 3
        assert all(hasattr(item, 'tmdb_id') for item in tmdb_data)

    def test_execute_cache_operations(self):
        """Test cache operations benchmark."""
        benchmark = PerformanceBenchmark()

        duration, success, metrics = benchmark._execute_cache_operations(10)

        assert duration > 0
        assert success is True
        assert "operations" in metrics
        assert metrics["operations"] == 10

    def test_execute_database_operations(self):
        """Test database operations benchmark."""
        benchmark = PerformanceBenchmark()

        # Test bulk insert
        duration, success, metrics = benchmark._execute_bulk_insert_operations(5)
        assert duration > 0
        assert success is True
        assert "records_inserted" in metrics

        # Test bulk update
        duration, success, metrics = benchmark._execute_bulk_update_operations(5)
        assert duration > 0
        assert success is True
        assert "records_updated" in metrics

        # Test bulk upsert
        duration, success, metrics = benchmark._execute_bulk_upsert_operations(5)
        assert duration > 0
        assert success is True
        assert "records_upserted" in metrics

    def test_execute_concurrent_operations(self):
        """Test concurrent operations benchmark."""
        benchmark = PerformanceBenchmark()

        duration, success, metrics = benchmark._execute_concurrent_operations(20)

        assert duration > 0
        assert success is True
        assert "concurrent_operations" in metrics

    def test_execute_memory_intensive_operations(self):
        """Test memory-intensive operations benchmark."""
        benchmark = PerformanceBenchmark()

        duration, success, metrics = benchmark._execute_memory_intensive_operations(5)

        assert duration > 0
        assert success is True
        assert "large_objects" in metrics

    def test_run_all_benchmarks(self):
        """Test running all benchmarks."""
        benchmark = PerformanceBenchmark()

        # Mock the database operations to avoid actual database calls
        with patch.object(benchmark.metadata_cache, 'bulk_store_tmdb_metadata'):
            results = benchmark.run_all_benchmarks()

        assert len(results) > 0

        # Check that we have results for key benchmarks
        expected_benchmarks = [
            "cache_operations",
            "database_bulk_insert",
            "database_bulk_update",
            "database_bulk_upsert",
            "concurrent_operations",
            "memory_intensive_operations"
        ]

        for expected in expected_benchmarks:
            assert expected in results

            result = results[expected]
            assert isinstance(result, BenchmarkResult)
            assert result.benchmark_name == expected
            assert result.operation_count > 0
            assert result.avg_duration_ms >= 0

    def test_generate_benchmark_report(self):
        """Test benchmark report generation."""
        benchmark = PerformanceBenchmark()

        # Mock benchmarks to avoid actual execution
        mock_result = BenchmarkResult(
            benchmark_name="test_benchmark",
            operation_count=100,
            total_duration_ms=1000,
            avg_duration_ms=10,
            min_duration_ms=5,
            max_duration_ms=20,
            throughput_per_sec=100,
            success_rate=95,
            memory_peak_mb=50,
            cpu_avg_percent=10,
            errors=[],
            additional_metrics={}
        )

        benchmark.benchmark_results["test_benchmark"] = mock_result

        report = benchmark.generate_benchmark_report()

        assert "benchmark_timestamp" in report
        assert "system_info" in report
        assert "benchmark_results" in report
        assert "performance_summary" in report
        assert "performance_targets" in report
        assert "recommendations" in report

        assert "test_benchmark" in report["benchmark_results"]
        assert report["benchmark_results"]["test_benchmark"]["operation_count"] == 100


class TestIntegration:
    """Integration tests for the profiling system."""

    def test_full_profiling_workflow(self):
        """Test the complete profiling workflow."""
        # Initialize profiler
        profiler = get_sync_profiler()
        profiler.clear_metrics()  # Start fresh

        # Run some operations
        with profiler.profile_operation(
            ProfilerEvent.CACHE_GET,
            "integration_test",
            operation_size=100
        ):
            time.sleep(0.01)

        # Analyze performance
        analyzer = PerformanceAnalyzer(profiler)
        bottlenecks = analyzer.analyze_bottlenecks()

        # Run benchmarks
        benchmark = PerformanceBenchmark()
        with patch.object(benchmark.metadata_cache, 'bulk_store_tmdb_metadata'):
            benchmark_results = benchmark.run_all_benchmarks()

        # Generate reports
        performance_report = analyzer.generate_performance_report()
        benchmark_report = benchmark.generate_benchmark_report()

        # Verify results
        assert len(profiler.metrics_history) > 0
        assert len(benchmark_results) > 0
        assert "overall_performance" in performance_report
        assert "benchmark_results" in benchmark_report

    def test_decorator_functionality(self):
        """Test the profiling decorator."""
        profiler = get_sync_profiler()
        profiler.clear_metrics()

        @profile_sync_operation(
            ProfilerEvent.SYNC_OPERATION,
            "decorator_test",
            operation_size=50
        )
        def test_function():
            time.sleep(0.01)
            return "test_result"

        # Call decorated function
        result = test_function()
        assert result == "test_result"

        # Check that metrics were recorded
        assert len(profiler.metrics_history) == 1

        metrics = profiler.metrics_history[0]
        assert metrics.event_type == ProfilerEvent.SYNC_OPERATION
        assert metrics.operation_name == "decorator_test"
        assert metrics.operation_size == 50
        assert metrics.success is True
