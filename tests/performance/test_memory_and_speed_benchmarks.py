"""Memory usage and processing speed benchmarks for bulk update operations.

This module provides comprehensive benchmarks to measure memory efficiency
and processing speed improvements from batch operations.
"""

import gc
import logging
import statistics
import time
import tracemalloc
from typing import Any

import pytest

from src.core.database import DatabaseManager
from src.core.services.bulk_update_task import ConcreteBulkUpdateTask

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryProfiler:
    """Profiler for tracking memory usage during operations."""

    def __init__(self) -> None:
        """Initialize the memory profiler.

        Sets up tracking variables for memory usage monitoring.
        """
        self.start_memory = 0
        self.peak_memory = 0
        self.end_memory = 0
        self.memory_snapshots: list[float] = []

    def start_profiling(self) -> None:
        """Start memory profiling."""
        tracemalloc.start()
        gc.collect()  # Clean up before measuring
        self.start_memory = self._get_current_memory()
        self.peak_memory = self.start_memory

    def stop_profiling(self) -> None:
        """Stop memory profiling and calculate final metrics."""
        gc.collect()  # Clean up before final measurement
        self.end_memory = self._get_current_memory()

        # Get peak memory from tracemalloc
        _current, peak = tracemalloc.get_traced_memory()
        self.peak_memory = peak / 1024 / 1024  # Convert to MB
        tracemalloc.stop()

    def take_snapshot(self) -> None:
        """Take a memory snapshot during operation."""
        current_memory = self._get_current_memory()
        self.memory_snapshots.append(current_memory)
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory

    def _get_current_memory(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0

    def get_memory_metrics(self) -> dict[str, float]:
        """Get comprehensive memory metrics."""
        return {
            "start_memory_mb": self.start_memory,
            "end_memory_mb": self.end_memory,
            "peak_memory_mb": self.peak_memory,
            "memory_delta_mb": self.end_memory - self.start_memory,
            "peak_memory_delta_mb": self.peak_memory - self.start_memory,
            "memory_snapshots": self.memory_snapshots.copy(),
        }


class SpeedProfiler:
    """Profiler for tracking processing speed and throughput."""

    def __init__(self) -> None:
        """Initialize the speed profiler.

        Sets up tracking variables for processing speed monitoring.
        """
        self.start_time = 0
        self.end_time = 0
        self.checkpoints: list[tuple[str, float]] = []

    def start_profiling(self) -> None:
        """Start speed profiling."""
        self.start_time = time.perf_counter()
        self.checkpoints.clear()

    def stop_profiling(self) -> None:
        """Stop speed profiling."""
        self.end_time = time.perf_counter()

    def add_checkpoint(self, name: str) -> None:
        """Add a timing checkpoint."""
        current_time = time.perf_counter()
        self.checkpoints.append((name, current_time - self.start_time))

    def get_speed_metrics(self) -> dict[str, float]:
        """Get comprehensive speed metrics."""
        total_time = self.end_time - self.start_time

        return {
            "total_execution_time_s": total_time,
            "total_execution_time_ms": total_time * 1000,
            "checkpoints": self.checkpoints.copy(),
        }


class BenchmarkResult:
    """Container for benchmark test results."""

    def __init__(self, test_name: str) -> None:
        """Initialize benchmark result container.

        Args:
            test_name: Name of the benchmark test being executed.
        """
        self.test_name = test_name
        self.memory_profiler = MemoryProfiler()
        self.speed_profiler = SpeedProfiler()
        self.records_processed = 0
        self.records_per_second = 0
        self.memory_per_record = 0

    def calculate_metrics(self) -> None:
        """Calculate derived metrics."""
        speed_metrics = self.speed_profiler.get_speed_metrics()
        memory_metrics = self.memory_profiler.get_memory_metrics()

        if speed_metrics["total_execution_time_s"] > 0:
            self.records_per_second = (
                self.records_processed / speed_metrics["total_execution_time_s"]
            )

        if self.records_processed > 0:
            self.memory_per_record = memory_metrics["memory_delta_mb"] / self.records_processed

    def get_summary(self) -> dict[str, Any]:
        """Get comprehensive benchmark summary."""
        speed_metrics = self.speed_profiler.get_speed_metrics()
        memory_metrics = self.memory_profiler.get_memory_metrics()

        return {
            "test_name": self.test_name,
            "records_processed": self.records_processed,
            "execution_time_s": speed_metrics["total_execution_time_s"],
            "execution_time_ms": speed_metrics["total_execution_time_ms"],
            "records_per_second": self.records_per_second,
            "memory_metrics": memory_metrics,
            "memory_per_record_mb": self.memory_per_record,
            "checkpoints": speed_metrics["checkpoints"],
        }


class MemoryAndSpeedBenchmark:
    """Comprehensive benchmark suite for memory and speed testing."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize the memory and speed benchmark suite.

        Args:
            db_manager: Database manager instance for database operations.
        """
        self.db_manager = db_manager
        self.db_manager.initialize()  # Ensure database is initialized
        self.test_sizes = [100, 500, 1000, 2000, 5000]
        self.results: list[BenchmarkResult] = []

    def create_test_data(self, size: int) -> tuple[list[dict], list[dict]]:
        """Create test data for benchmarking.

        Args:
            size: Number of records to create

        Returns:
            Tuple of (anime_metadata_updates, parsed_file_updates)
        """
        anime_updates = []
        file_updates = []

        for i in range(size):
            anime_updates.append(
                {
                    "tmdb_id": 1000 + i,
                    "status": "processed",
                    "title": f"Benchmark Anime {i}",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            )

            file_updates.append(
                {
                    "file_path": f"/benchmark/path/anime_{i}.mkv",
                    "is_processed": True,
                    "processing_status": "completed",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            )

        return anime_updates, file_updates

    def benchmark_bulk_anime_metadata_update(self, updates: list[dict]) -> BenchmarkResult:
        """Benchmark bulk anime metadata update performance.

        Args:
            updates: List of update dictionaries

        Returns:
            Benchmark result
        """
        logger.info(f"Benchmarking bulk anime metadata update with {len(updates)} records...")

        result = BenchmarkResult("bulk_anime_metadata_update")
        result.records_processed = len(updates)

        # Start profiling
        result.memory_profiler.start_profiling()
        result.speed_profiler.start_profiling()

        try:
            # Execute bulk update with checkpoints
            result.speed_profiler.add_checkpoint("start")

            bulk_task = ConcreteBulkUpdateTask(
                update_type="anime_metadata", updates=updates, db_manager=self.db_manager
            )

            result.speed_profiler.add_checkpoint("task_created")
            result.memory_profiler.take_snapshot()

            updated_count = bulk_task.execute()

            result.speed_profiler.add_checkpoint("execution_complete")
            result.memory_profiler.take_snapshot()

            logger.info(f"  Updated {updated_count} records")

        finally:
            # Stop profiling
            result.speed_profiler.stop_profiling()
            result.memory_profiler.stop_profiling()
            result.calculate_metrics()

        return result

    def benchmark_bulk_parsed_files_update(self, updates: list[dict]) -> BenchmarkResult:
        """Benchmark bulk parsed files update performance.

        Args:
            updates: List of update dictionaries

        Returns:
            Benchmark result
        """
        logger.info(f"Benchmarking bulk parsed files update with {len(updates)} records...")

        result = BenchmarkResult("bulk_parsed_files_update")
        result.records_processed = len(updates)

        # Start profiling
        result.memory_profiler.start_profiling()
        result.speed_profiler.start_profiling()

        try:
            # Execute bulk update with checkpoints
            result.speed_profiler.add_checkpoint("start")

            bulk_task = ConcreteBulkUpdateTask(
                update_type="parsed_files", updates=updates, db_manager=self.db_manager
            )

            result.speed_profiler.add_checkpoint("task_created")
            result.memory_profiler.take_snapshot()

            updated_count = bulk_task.execute()

            result.speed_profiler.add_checkpoint("execution_complete")
            result.memory_profiler.take_snapshot()

            logger.info(f"  Updated {updated_count} records")

        finally:
            # Stop profiling
            result.speed_profiler.stop_profiling()
            result.memory_profiler.stop_profiling()
            result.calculate_metrics()

        return result

    def benchmark_mixed_updates(
        self, anime_updates: list[dict], file_updates: list[dict]
    ) -> BenchmarkResult:
        """Benchmark mixed update operations performance.

        Args:
            anime_updates: List of anime metadata updates
            file_updates: List of parsed file updates

        Returns:
            Benchmark result
        """
        logger.info(
            f"Benchmarking mixed updates with {len(anime_updates)} anime + {len(file_updates)} file records..."
        )

        result = BenchmarkResult("mixed_updates")
        result.records_processed = len(anime_updates) + len(file_updates)

        # Start profiling
        result.memory_profiler.start_profiling()
        result.speed_profiler.start_profiling()

        try:
            # Execute anime metadata updates
            result.speed_profiler.add_checkpoint("start")

            anime_task = ConcreteBulkUpdateTask(
                update_type="anime_metadata", updates=anime_updates, db_manager=self.db_manager
            )

            result.speed_profiler.add_checkpoint("anime_task_created")
            result.memory_profiler.take_snapshot()

            anime_updated = anime_task.execute()

            result.speed_profiler.add_checkpoint("anime_execution_complete")
            result.memory_profiler.take_snapshot()

            # Execute parsed files updates
            file_task = ConcreteBulkUpdateTask(
                update_type="parsed_files", updates=file_updates, db_manager=self.db_manager
            )

            result.speed_profiler.add_checkpoint("file_task_created")
            result.memory_profiler.take_snapshot()

            file_updated = file_task.execute()

            result.speed_profiler.add_checkpoint("file_execution_complete")
            result.memory_profiler.take_snapshot()

            logger.info(f"  Updated {anime_updated} anime + {file_updated} file records")

        finally:
            # Stop profiling
            result.speed_profiler.stop_profiling()
            result.memory_profiler.stop_profiling()
            result.calculate_metrics()

        return result

    def benchmark_memory_efficiency_scaling(self) -> list[BenchmarkResult]:
        """Benchmark memory efficiency across different batch sizes.

        Returns:
            List of benchmark results for different sizes
        """
        logger.info("Benchmarking memory efficiency scaling...")

        results = []

        for size in self.test_sizes:
            logger.info(f"\nTesting memory efficiency with {size} records...")

            # Create test data
            anime_updates, file_updates = self.create_test_data(size)

            # Benchmark anime metadata updates
            anime_result = self.benchmark_bulk_anime_metadata_update(anime_updates)
            anime_result.test_name = f"anime_metadata_{size}_records"
            results.append(anime_result)

            # Benchmark parsed files updates
            file_result = self.benchmark_bulk_parsed_files_update(file_updates)
            file_result.test_name = f"parsed_files_{size}_records"
            results.append(file_result)

            # Log results
            logger.info(
                f"  Anime metadata: {anime_result.records_per_second:.1f} records/sec, "
                f"{anime_result.memory_per_record:.4f} MB/record"
            )
            logger.info(
                f"  Parsed files: {file_result.records_per_second:.1f} records/sec, "
                f"{file_result.memory_per_record:.4f} MB/record"
            )

        return results

    def benchmark_throughput_scaling(self) -> list[BenchmarkResult]:
        """Benchmark throughput scaling across different batch sizes.

        Returns:
            List of benchmark results for different sizes
        """
        logger.info("Benchmarking throughput scaling...")

        results = []

        for size in self.test_sizes:
            logger.info(f"\nTesting throughput with {size} records...")

            # Create test data
            anime_updates, file_updates = self.create_test_data(size)

            # Benchmark mixed updates (most realistic scenario)
            mixed_result = self.benchmark_mixed_updates(anime_updates, file_updates)
            mixed_result.test_name = f"mixed_updates_{size}_records"
            results.append(mixed_result)

            # Log results
            logger.info(
                f"  Mixed updates: {mixed_result.records_per_second:.1f} records/sec, "
                f"{mixed_result.execution_time_s:.3f}s total"
            )

        return results

    def run_comprehensive_benchmarks(self) -> dict[str, Any]:
        """Run comprehensive memory and speed benchmarks.

        Returns:
            Complete benchmark results
        """
        logger.info("Starting comprehensive memory and speed benchmarks...")

        results = {
            "memory_efficiency_scaling": self.benchmark_memory_efficiency_scaling(),
            "throughput_scaling": self.benchmark_throughput_scaling(),
            "summary": {},
        }

        # Generate summary
        results["summary"] = self._generate_benchmark_summary(results)

        return results

    def _generate_benchmark_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary statistics from benchmark results.

        Args:
            results: Complete benchmark results

        Returns:
            Summary statistics
        """
        summary = {
            "memory_efficiency": {},
            "throughput_performance": {},
            "scaling_characteristics": {},
        }

        # Analyze memory efficiency scaling
        memory_results = results["memory_efficiency_scaling"]
        if memory_results:
            anime_memory_per_record = []
            file_memory_per_record = []
            anime_records_per_sec = []
            file_records_per_sec = []

            for result in memory_results:
                if "anime_metadata" in result.test_name:
                    anime_memory_per_record.append(result.memory_per_record)
                    anime_records_per_sec.append(result.records_per_second)
                elif "parsed_files" in result.test_name:
                    file_memory_per_record.append(result.memory_per_record)
                    file_records_per_sec.append(result.records_per_second)

            summary["memory_efficiency"] = {
                "anime_avg_memory_per_record_mb": (
                    statistics.mean(anime_memory_per_record) if anime_memory_per_record else 0
                ),
                "file_avg_memory_per_record_mb": (
                    statistics.mean(file_memory_per_record) if file_memory_per_record else 0
                ),
                "anime_avg_throughput_records_per_sec": (
                    statistics.mean(anime_records_per_sec) if anime_records_per_sec else 0
                ),
                "file_avg_throughput_records_per_sec": (
                    statistics.mean(file_records_per_sec) if file_records_per_sec else 0
                ),
            }

        # Analyze throughput scaling
        throughput_results = results["throughput_scaling"]
        if throughput_results:
            throughput_values = [result.records_per_second for result in throughput_results]
            execution_times = [result.execution_time_s for result in throughput_results]
            [result.records_processed for result in throughput_results]

            summary["throughput_performance"] = {
                "avg_throughput_records_per_sec": statistics.mean(throughput_values),
                "max_throughput_records_per_sec": (
                    max(throughput_values) if throughput_values else 0
                ),
                "min_execution_time_s": min(execution_times) if execution_times else 0,
                "max_execution_time_s": max(execution_times) if execution_times else 0,
            }

        # Analyze scaling characteristics
        if memory_results and throughput_results:
            # Calculate scaling ratios
            smallest_batch = min(result.records_processed for result in memory_results)
            largest_batch = max(result.records_processed for result in memory_results)

            smallest_time = min(
                result.execution_time_s
                for result in memory_results
                if result.records_processed == smallest_batch
            )
            largest_time = max(
                result.execution_time_s
                for result in memory_results
                if result.records_processed == largest_batch
            )

            time_scaling_ratio = largest_time / smallest_time if smallest_time > 0 else 1.0
            batch_scaling_ratio = largest_batch / smallest_batch if smallest_batch > 0 else 1.0

            summary["scaling_characteristics"] = {
                "batch_size_scaling_ratio": batch_scaling_ratio,
                "execution_time_scaling_ratio": time_scaling_ratio,
                "scaling_efficiency": (
                    batch_scaling_ratio / time_scaling_ratio if time_scaling_ratio > 0 else 1.0
                ),
                "is_linearly_scalable": time_scaling_ratio
                <= batch_scaling_ratio * 1.5,  # Allow 50% overhead
            }

        return summary


@pytest.mark.asyncio
async def test_memory_and_speed_benchmarks():
    """Main memory and speed benchmark test entry point."""
    # Initialize database manager
    db_manager = DatabaseManager("sqlite:///:memory:")  # Use in-memory database for testing

    try:
        # Create benchmark instance
        benchmark = MemoryAndSpeedBenchmark(db_manager)

        # Run comprehensive benchmarks
        results = benchmark.run_comprehensive_benchmarks()

        # Log final results
        logger.info("\n" + "=" * 60)
        logger.info("MEMORY AND SPEED BENCHMARK RESULTS")
        logger.info("=" * 60)

        summary = results["summary"]

        # Memory efficiency summary
        if "memory_efficiency" in summary:
            mem_eff = summary["memory_efficiency"]
            logger.info("Memory Efficiency:")
            logger.info(
                f"  Anime metadata - Avg memory/record: {mem_eff.get('anime_avg_memory_per_record_mb', 0):.4f} MB"
            )
            logger.info(
                f"  Parsed files - Avg memory/record: {mem_eff.get('file_avg_memory_per_record_mb', 0):.4f} MB"
            )
            logger.info(
                f"  Anime metadata - Avg throughput: {mem_eff.get('anime_avg_throughput_records_per_sec', 0):.1f} records/sec"
            )
            logger.info(
                f"  Parsed files - Avg throughput: {mem_eff.get('file_avg_throughput_records_per_sec', 0):.1f} records/sec"
            )

        # Throughput performance summary
        if "throughput_performance" in summary:
            throughput = summary["throughput_performance"]
            logger.info("\nThroughput Performance:")
            logger.info(
                f"  Average throughput: {throughput.get('avg_throughput_records_per_sec', 0):.1f} records/sec"
            )
            logger.info(
                f"  Maximum throughput: {throughput.get('max_throughput_records_per_sec', 0):.1f} records/sec"
            )
            logger.info(
                f"  Execution time range: {throughput.get('min_execution_time_s', 0):.3f}s - {throughput.get('max_execution_time_s', 0):.3f}s"
            )

        # Scaling characteristics summary
        if "scaling_characteristics" in summary:
            scaling = summary["scaling_characteristics"]
            logger.info("\nScaling Characteristics:")
            logger.info(
                f"  Batch size scaling ratio: {scaling.get('batch_size_scaling_ratio', 1):.2f}"
            )
            logger.info(
                f"  Execution time scaling ratio: {scaling.get('execution_time_scaling_ratio', 1):.2f}"
            )
            logger.info(f"  Scaling efficiency: {scaling.get('scaling_efficiency', 1):.2f}")
            logger.info(
                f"  Is linearly scalable: {'✅' if scaling.get('is_linearly_scalable', False) else '❌'}"
            )

        # Assert performance thresholds
        if "memory_efficiency" in summary:
            mem_eff = summary["memory_efficiency"]
            assert (
                mem_eff.get("anime_avg_memory_per_record_mb", 0) < 0.01
            ), "Anime memory per record should be < 0.01 MB"
            assert (
                mem_eff.get("file_avg_memory_per_record_mb", 0) < 0.01
            ), "File memory per record should be < 0.01 MB"

        if "throughput_performance" in summary:
            throughput = summary["throughput_performance"]
            assert (
                throughput.get("avg_throughput_records_per_sec", 0) > 1000
            ), "Average throughput should be > 1000 records/sec"

        if "scaling_characteristics" in summary:
            scaling = summary["scaling_characteristics"]
            assert scaling.get("is_linearly_scalable", False), "Operations should scale linearly"

        logger.info("\n✅ All memory and speed benchmarks passed!")

        return results

    finally:
        # Cleanup
        if hasattr(db_manager, "close"):
            db_manager.close()


if __name__ == "__main__":
    # Run benchmarks directly
    import asyncio

    asyncio.run(test_memory_and_speed_benchmarks())
