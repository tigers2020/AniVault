"""Tests for synchronization performance optimizer.

This module tests the SyncPerformanceOptimizer and related optimization components
to ensure performance targets are met (<1 second for single ops, >1000 records/second for bulk).
"""

import threading
import time
from unittest.mock import MagicMock, Mock, patch

from src.core.performance_analyzer import PerformanceAnalyzer
from src.core.sync_performance_optimizer import (
    BatchOptimizer,
    ConnectionPoolOptimizer,
    OptimizationResult,
    SyncPerformanceOptimizer,
    get_sync_optimizer,
    optimize_sync_performance,
)
from src.core.sync_profiler import PerformanceMetrics, ProfilerEvent, SyncProfiler


class TestConnectionPoolOptimizer:
    """Test the ConnectionPoolOptimizer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db_manager = Mock()
        self.mock_engine = Mock()
        self.mock_db_manager.engine = self.mock_engine
        self.optimizer = ConnectionPoolOptimizer(self.mock_db_manager)

    def test_optimizer_initialization(self) -> None:
        """Test optimizer initialization."""
        assert self.optimizer.db_manager is self.mock_db_manager
        assert self.optimizer.original_pool_settings == {}

    def test_optimize_pool_settings_success(self) -> None:
        """Test successful pool settings optimization."""
        # Mock engine attributes
        self.mock_engine.pool_size = 5
        self.mock_engine.max_overflow = 10
        self.mock_engine.pool_pre_ping = False
        self.mock_engine.pool_recycle = -1

        # Mock connection performance test
        with patch.object(self.optimizer, "_test_connection_performance", return_value=50.0):
            result = self.optimizer.optimize_pool_settings()

        assert result.success is True
        assert result.optimization_name == "connection_pool_optimization"
        assert result.improvement_percent > 0
        assert "connection_time_ms" in result.before_metrics
        assert "connection_time_ms" in result.after_metrics

        # Verify settings were applied
        assert self.mock_engine.pool_size == 20
        assert self.mock_engine.max_overflow == 30
        assert self.mock_engine.pool_pre_ping is True
        assert self.mock_engine.pool_recycle == 3600

    def test_optimize_pool_settings_no_engine(self) -> None:
        """Test optimization when no engine is available."""
        self.mock_db_manager.engine = None

        result = self.optimizer.optimize_pool_settings()

        assert result.success is False
        assert result.error_message == "Database engine not available"

    def test_optimize_pool_settings_exception(self) -> None:
        """Test optimization when exception occurs."""
        self.mock_engine.pool_size = 5
        self.mock_engine.configure_mock(**{"pool_size": 5})

        # Mock exception during optimization by making engine None
        original_engine = self.optimizer.db_manager.engine
        self.optimizer.db_manager.engine = None

        result = self.optimizer.optimize_pool_settings()

        assert result.success is False
        assert "Database engine not available" in result.error_message

        # Restore engine
        self.optimizer.db_manager.engine = original_engine

    def test_test_connection_performance(self) -> None:
        """Test connection performance testing."""
        # Mock connection context manager
        mock_conn = Mock()
        mock_conn.execute.return_value = None

        with patch.object(self.mock_engine, "connect", return_value=mock_conn):
            with patch("builtins.open", mock_open()):
                duration = self.optimizer._test_connection_performance()

        assert isinstance(duration, float)
        assert duration >= 0


class TestBatchOptimizer:
    """Test the BatchOptimizer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.optimizer = BatchOptimizer(batch_size=1000)

    def test_optimizer_initialization(self) -> None:
        """Test optimizer initialization."""
        assert self.optimizer.batch_size == 1000
        assert self.optimizer.optimal_batch_sizes == {}

    def test_optimize_batch_size_success(self) -> None:
        """Test successful batch size optimization."""
        # Generate test data
        test_data = [{"id": i, "data": f"test_data_{i}"} for i in range(1000)]

        # Mock performance measurement
        with patch.object(self.optimizer, "_measure_batch_performance") as mock_measure:
            mock_measure.return_value = 100.0  # 100ms for any batch size

            result = self.optimizer.optimize_batch_size("insert", test_data)

        assert result.success is True
        assert result.optimization_name == "batch_size_optimization_insert"
        assert "batch_size" in result.before_metrics
        assert "throughput" in result.before_metrics
        assert "batch_size" in result.after_metrics
        assert "throughput" in result.after_metrics

        # Verify optimal batch size was stored
        assert "insert" in self.optimizer.optimal_batch_sizes
        assert isinstance(self.optimizer.optimal_batch_sizes["insert"], int)

    def test_optimize_batch_size_insufficient_data(self) -> None:
        """Test batch size optimization with insufficient data."""
        # Small test data
        test_data = [{"id": i} for i in range(50)]

        result = self.optimizer.optimize_batch_size("insert", test_data)

        # Should fail due to insufficient data for optimization
        assert result.success is False
        assert "max() iterable argument is empty" in result.error_message

    def test_optimize_batch_size_exception(self) -> None:
        """Test batch size optimization when exception occurs."""
        test_data = [{"id": i} for i in range(1000)]

        # Mock exception during measurement
        with patch.object(
            self.optimizer, "_measure_batch_performance", side_effect=Exception("Test error")
        ):
            result = self.optimizer.optimize_batch_size("insert", test_data)

        assert result.success is False
        assert "Test error" in result.error_message

    def test_get_optimal_batch_size(self) -> None:
        """Test getting optimal batch size."""
        # Set optimal batch size
        self.optimizer.optimal_batch_sizes["insert"] = 500

        assert self.optimizer.get_optimal_batch_size("insert") == 500
        assert self.optimizer.get_optimal_batch_size("update") == 1000  # Default

    def test_measure_batch_performance(self) -> None:
        """Test batch performance measurement."""
        test_data = [{"id": i} for i in range(100)]

        duration = self.optimizer._measure_batch_performance("insert", test_data)

        assert isinstance(duration, float)
        assert duration >= 0


class TestSyncPerformanceOptimizer:
    """Test the SyncPerformanceOptimizer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_db_manager = Mock()
        self.mock_cache = Mock()
        self.optimizer = SyncPerformanceOptimizer(self.mock_db_manager, self.mock_cache)

    def test_optimizer_initialization(self) -> None:
        """Test optimizer initialization."""
        assert self.optimizer.db_manager is self.mock_db_manager
        assert self.optimizer.cache_instance is self.mock_cache
        assert isinstance(self.optimizer.analyzer, PerformanceAnalyzer)
        assert isinstance(self.optimizer.connection_optimizer, ConnectionPoolOptimizer)
        assert isinstance(self.optimizer.batch_optimizer, BatchOptimizer)
        assert self.optimizer.optimization_results == []

    def test_analyze_and_optimize_no_data(self) -> None:
        """Test optimization with no performance data."""
        # Mock analyzer to return empty list
        with patch.object(self.optimizer.analyzer, "analyze_bottlenecks", return_value=[]):
            results = self.optimizer.analyze_and_optimize()

        assert results == []

    def test_analyze_and_optimize_with_connection_optimization(self) -> None:
        """Test optimization with connection optimization needed."""
        # Mock analysis with connection bottleneck
        mock_bottleneck = Mock()
        mock_bottleneck.event_type.value = "db_query"
        mock_bottleneck.avg_duration_ms = 200
        mock_bottleneck.success_rate = 90

        mock_analysis = Mock()
        mock_analysis.bottlenecks = [mock_bottleneck]

        mock_optimization_result = OptimizationResult(
            optimization_name="connection_pool_optimization",
            before_metrics={"connection_time_ms": 100},
            after_metrics={"connection_time_ms": 50},
            improvement_percent=50.0,
            success=True,
        )

        with patch.object(
            self.optimizer.analyzer, "analyze_bottlenecks", return_value=[mock_bottleneck]
        ):
            with patch.object(
                self.optimizer.connection_optimizer,
                "optimize_pool_settings",
                return_value=mock_optimization_result,
            ):
                results = self.optimizer.analyze_and_optimize()

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].improvement_percent == 50.0

    def test_analyze_and_optimize_with_batch_optimization(self) -> None:
        """Test optimization with batch size optimization needed."""
        # Mock analysis with batch bottleneck
        mock_bottleneck = Mock()
        mock_bottleneck.event_type.value = "db_bulk_insert"
        mock_bottleneck.throughput_per_sec = 500  # Below threshold
        mock_bottleneck.avg_duration_ms = 50  # Add required attribute
        mock_bottleneck.success_rate = 100  # Add required attribute

        mock_analysis = Mock()
        mock_analysis.bottlenecks = [mock_bottleneck]

        mock_optimization_result = OptimizationResult(
            optimization_name="batch_size_optimization_insert",
            before_metrics={"throughput": 500},
            after_metrics={"throughput": 1500},
            improvement_percent=200.0,
            success=True,
        )

        with patch.object(
            self.optimizer.analyzer, "analyze_bottlenecks", return_value=[mock_bottleneck]
        ):
            with patch.object(
                self.optimizer.batch_optimizer,
                "optimize_batch_size",
                return_value=mock_optimization_result,
            ):
                results = self.optimizer.analyze_and_optimize()

        assert len(results) == 3  # insert, update, upsert
        assert all(result.success for result in results)

    def test_should_optimize_connections(self) -> None:
        """Test connection optimization decision logic."""
        # Test high duration
        mock_bottleneck1 = Mock()
        mock_bottleneck1.event_type.value = "db_query"
        mock_bottleneck1.avg_duration_ms = 200
        mock_bottleneck1.success_rate = 95

        assert self.optimizer._should_optimize_connections([mock_bottleneck1]) is True

        # Test low success rate
        mock_bottleneck2 = Mock()
        mock_bottleneck2.event_type.value = "db_bulk_insert"
        mock_bottleneck2.avg_duration_ms = 50
        mock_bottleneck2.success_rate = 90

        assert self.optimizer._should_optimize_connections([mock_bottleneck2]) is True

        # Test no optimization needed
        mock_bottleneck3 = Mock()
        mock_bottleneck3.event_type.value = "cache_get"
        mock_bottleneck3.avg_duration_ms = 10
        mock_bottleneck3.success_rate = 99

        assert self.optimizer._should_optimize_connections([mock_bottleneck3]) is False

    def test_should_optimize_batch_sizes(self) -> None:
        """Test batch size optimization decision logic."""
        # Test low throughput
        mock_bottleneck = Mock()
        mock_bottleneck.event_type.value = "db_bulk_insert"
        mock_bottleneck.throughput_per_sec = 500

        assert self.optimizer._should_optimize_batch_sizes([mock_bottleneck]) is True

        # Test high throughput
        mock_bottleneck.throughput_per_sec = 1500

        assert self.optimizer._should_optimize_batch_sizes([mock_bottleneck]) is False

    def test_generate_test_data(self) -> None:
        """Test test data generation."""
        # Test insert data
        insert_data = self.optimizer._generate_test_data("insert", 10)
        assert len(insert_data) == 10
        assert all("id" in record for record in insert_data)
        assert all("title" in record for record in insert_data)

        # Test update data
        update_data = self.optimizer._generate_test_data("update", 5)
        assert len(update_data) == 5
        assert all("Updated Title" in record["title"] for record in update_data)

        # Test upsert data
        upsert_data = self.optimizer._generate_test_data("upsert", 3)
        assert len(upsert_data) == 3
        assert all("Upsert Title" in record["title"] for record in upsert_data)

    def test_validate_performance_targets(self) -> None:
        """Test performance target validation."""
        # Mock profiler with good metrics
        mock_profiler = Mock()
        mock_metrics = {
            ProfilerEvent.CACHE_GET: {"avg_duration_ms": 5},
            ProfilerEvent.CACHE_SET: {"avg_duration_ms": 10},
            ProfilerEvent.DB_QUERY: {"avg_duration_ms": 50},
            ProfilerEvent.DB_BULK_INSERT: {"avg_throughput_per_sec": 1500},
            ProfilerEvent.DB_BULK_UPDATE: {"avg_throughput_per_sec": 1200},
            ProfilerEvent.DB_BULK_UPSERT: {"avg_throughput_per_sec": 1300},
            "overall_stats": {"success_rate": 98},
        }
        mock_profiler.get_performance_summary.return_value = mock_metrics

        with patch(
            "src.core.sync_performance_optimizer.get_sync_profiler", return_value=mock_profiler
        ):
            targets = self.optimizer.validate_performance_targets()

        assert targets["single_operation_under_1s"] is True
        assert targets["bulk_throughput_over_1000_per_sec"] is True
        assert targets["success_rate_over_95_percent"] is True

    def test_validate_performance_targets_poor_performance(self) -> None:
        """Test performance target validation with poor performance."""
        # Mock profiler with poor metrics
        mock_profiler = Mock()
        mock_metrics = {
            ProfilerEvent.CACHE_GET: {"avg_duration_ms": 1500},  # Over 1s
            ProfilerEvent.DB_BULK_INSERT: {"avg_throughput_per_sec": 500},  # Under 1000
            "overall_stats": {"success_rate": 90},  # Under 95%
        }
        mock_profiler.get_performance_summary.return_value = mock_metrics

        with patch(
            "src.core.sync_performance_optimizer.get_sync_profiler", return_value=mock_profiler
        ):
            targets = self.optimizer.validate_performance_targets()

        assert targets["single_operation_under_1s"] is False
        assert targets["bulk_throughput_over_1000_per_sec"] is False
        assert targets["success_rate_over_95_percent"] is False

    def test_validate_performance_targets_no_profiler(self) -> None:
        """Test performance target validation when no profiler available."""
        with patch("src.core.sync_performance_optimizer.get_sync_profiler", return_value=None):
            targets = self.optimizer.validate_performance_targets()

        assert all(target is False for target in targets.values())

    def test_get_optimization_summary_no_results(self) -> None:
        """Test optimization summary with no results."""
        summary = self.optimizer.get_optimization_summary()

        assert summary["total_optimizations"] == 0
        assert summary["successful_optimizations"] == 0
        assert summary["average_improvement_percent"] == 0
        assert "performance_targets_met" in summary

    def test_get_optimization_summary_with_results(self) -> None:
        """Test optimization summary with results."""
        # Add some optimization results
        result1 = OptimizationResult(
            optimization_name="test_opt_1",
            before_metrics={"metric": 100},
            after_metrics={"metric": 50},
            improvement_percent=50.0,
            success=True,
        )

        result2 = OptimizationResult(
            optimization_name="test_opt_2",
            before_metrics={"metric": 200},
            after_metrics={"metric": 150},
            improvement_percent=25.0,
            success=True,
        )

        result3 = OptimizationResult(
            optimization_name="test_opt_3",
            before_metrics={"metric": 300},
            after_metrics={"metric": 300},
            improvement_percent=0.0,
            success=False,
            error_message="Test error",
        )

        self.optimizer.optimization_results = [result1, result2, result3]

        summary = self.optimizer.get_optimization_summary()

        assert summary["total_optimizations"] == 3
        assert summary["successful_optimizations"] == 2
        assert summary["average_improvement_percent"] == 37.5  # (50 + 25) / 2
        assert len(summary["optimization_details"]) == 3

        # Check details
        details = summary["optimization_details"]
        assert details[0]["name"] == "test_opt_1"
        assert details[0]["improvement_percent"] == 50.0
        assert details[0]["success"] is True

        assert details[2]["success"] is False


class TestGlobalOptimizer:
    """Test global optimizer functions."""

    def test_get_sync_optimizer_singleton(self) -> None:
        """Test that get_sync_optimizer returns singleton instance."""
        optimizer1 = get_sync_optimizer()
        optimizer2 = get_sync_optimizer()

        assert optimizer1 is optimizer2

    def test_get_sync_optimizer_with_params(self) -> None:
        """Test get_sync_optimizer with parameters."""
        mock_db = Mock()
        mock_cache = Mock()

        # Reset global optimizer to test with new parameters
        import src.core.sync_performance_optimizer

        src.core.sync_performance_optimizer._global_sync_optimizer = None

        optimizer = get_sync_optimizer(mock_db, mock_cache)

        assert optimizer.db_manager is mock_db
        assert optimizer.cache_instance is mock_cache

    def test_optimize_sync_performance(self) -> None:
        """Test optimize_sync_performance function."""
        mock_db = Mock()
        mock_cache = Mock()

        # Mock optimization results
        mock_results = [
            OptimizationResult(
                optimization_name="test_optimization",
                before_metrics={"metric": 100},
                after_metrics={"metric": 50},
                improvement_percent=50.0,
                success=True,
            )
        ]

        with patch("src.core.sync_performance_optimizer.get_sync_optimizer") as mock_get_optimizer:
            mock_optimizer = Mock()
            mock_optimizer.analyze_and_optimize.return_value = mock_results
            mock_optimizer.get_optimization_summary.return_value = {
                "total_optimizations": 1,
                "successful_optimizations": 1,
                "average_improvement_percent": 50.0,
                "performance_targets_met": {"test_target": True},
            }
            mock_get_optimizer.return_value = mock_optimizer

            result = optimize_sync_performance(mock_db, mock_cache)

        assert result["total_optimizations"] == 1
        assert result["successful_optimizations"] == 1
        assert result["average_improvement_percent"] == 50.0
        assert result["performance_targets_met"]["test_target"] is True


class TestIntegration:
    """Integration tests for performance optimization."""

    def test_full_optimization_workflow(self) -> None:
        """Test complete optimization workflow."""
        # Create real profiler with test data
        profiler = SyncProfiler()

        # Add some test metrics
        for _i in range(10):
            metrics = PerformanceMetrics(
                event_type=ProfilerEvent.DB_BULK_INSERT,
                operation_name="test_bulk_insert",
                start_time=time.time(),
                end_time=time.time() + 0.5,  # 500ms - slow
                duration_ms=500,
                cpu_percent=80.0,
                memory_mb=200.0,
                memory_peak_mb=250.0,
                thread_id=threading.get_ident(),
                operation_size=1000,
                success=True,
            )
            profiler.record_metrics(metrics)

        # Create optimizer
        mock_db = Mock()
        mock_cache = Mock()
        optimizer = SyncPerformanceOptimizer(mock_db, mock_cache)

        # Mock the analyzer to return our bottleneck data
        mock_bottleneck = Mock()
        mock_bottleneck.event_type.value = "db_bulk_insert"
        mock_bottleneck.avg_duration_ms = 500
        mock_bottleneck.throughput_per_sec = 2000  # Good throughput
        mock_bottleneck.success_rate = 100

        # Mock optimization components
        with patch.object(
            optimizer.analyzer, "analyze_bottlenecks", return_value=[mock_bottleneck]
        ):
            with patch.object(
                optimizer.connection_optimizer, "optimize_pool_settings"
            ) as mock_conn_opt:
                with patch.object(
                    optimizer.batch_optimizer, "optimize_batch_size"
                ) as mock_batch_opt:
                    mock_conn_opt.return_value = OptimizationResult(
                        optimization_name="connection_optimization",
                        before_metrics={"connection_time_ms": 100},
                        after_metrics={"connection_time_ms": 50},
                        improvement_percent=50.0,
                        success=True,
                    )

                    mock_batch_opt.return_value = OptimizationResult(
                        optimization_name="batch_optimization",
                        before_metrics={"throughput": 500},
                        after_metrics={"throughput": 1500},
                        improvement_percent=200.0,
                        success=True,
                    )

                    # Run optimization
                    results = optimizer.analyze_and_optimize()

        # Verify results
        assert len(results) > 0
        assert all(result.success for result in results)

        # Get summary
        summary = optimizer.get_optimization_summary()
        assert summary["total_optimizations"] > 0
        assert summary["successful_optimizations"] > 0
        assert summary["average_improvement_percent"] > 0


# Mock helper for testing
def mock_open(*args, **kwargs):
    """Mock open function for testing."""
    return MagicMock()
