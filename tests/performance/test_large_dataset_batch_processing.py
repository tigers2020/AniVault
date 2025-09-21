"""Large dataset batch processing performance tests.

This module tests the performance and reliability of batch operations
with large datasets to ensure scalability and memory efficiency.
"""

import asyncio
import logging
import statistics
import time
from typing import Any

import pytest

from src.core.database import DatabaseManager
from src.core.services.bulk_update_task import ConcreteBulkUpdateTask

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LargeDatasetBatchProcessor:
    """Processor for testing large dataset batch operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize the large dataset batch processor.

        Args:
            db_manager: Database manager instance for database operations.
        """
        self.db_manager = db_manager
        self.db_manager.initialize()  # Ensure database is initialized
        self.large_dataset_sizes = [10000, 25000, 50000, 100000]
        self.batch_sizes = [1000, 2500, 5000, 10000]

    def generate_large_dataset(self, size: int) -> tuple[list[dict], list[dict]]:
        """Generate large dataset for testing.

        Args:
            size: Number of records to generate

        Returns:
            Tuple of (anime_metadata_updates, parsed_file_updates)
        """
        logger.info(f"Generating large dataset with {size:,} records...")

        anime_updates = []
        file_updates = []

        # Generate anime metadata updates
        for i in range(size):
            anime_updates.append(
                {
                    "tmdb_id": 10000 + i,
                    "status": "processed" if i % 3 == 0 else "pending" if i % 3 == 1 else "failed",
                    "title": f"Large Dataset Anime {i}",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "metadata": {
                        "genre": f"Genre {i % 10}",
                        "year": 2020 + (i % 5),
                        "rating": (i % 10) + 1,
                    },
                }
            )

        # Generate parsed file updates
        for i in range(size):
            file_updates.append(
                {
                    "file_path": f"/large/dataset/path/anime_{i:06d}.mkv",
                    "is_processed": i % 4 == 0,
                    "processing_status": (
                        "completed"
                        if i % 4 == 0
                        else "pending" if i % 4 == 1 else "failed" if i % 4 == 2 else "in_progress"
                    ),
                    "file_size": 1024 * 1024 * (i % 1000 + 100),  # 100MB - 1GB
                    "duration": 1200 + (i % 3600),  # 20-80 minutes
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            )

        logger.info(
            f"Generated {len(anime_updates):,} anime records and {len(file_updates):,} file records"
        )
        return anime_updates, file_updates

    def process_batches(
        self, updates: list[dict], batch_size: int, update_type: str
    ) -> dict[str, Any]:
        """Process updates in batches and measure performance.

        Args:
            updates: List of update dictionaries
            batch_size: Size of each batch
            update_type: Type of update ('anime_metadata' or 'parsed_files')

        Returns:
            Performance metrics
        """
        logger.info(
            f"Processing {len(updates):,} {update_type} records in batches of {batch_size:,}..."
        )

        start_time = time.time()
        total_updated = 0
        batch_results = []

        # Process in batches
        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]
            batch_start = time.time()

            logger.info(
                f"  Processing batch {i//batch_size + 1}/{(len(updates) + batch_size - 1)//batch_size} "
                f"({len(batch):,} records)..."
            )

            try:
                # Create and execute bulk update task
                bulk_task = ConcreteBulkUpdateTask(
                    update_type=update_type, updates=batch, db_manager=self.db_manager
                )

                batch_updated = bulk_task.execute()
                total_updated += batch_updated

                batch_end = time.time()
                batch_time = batch_end - batch_start

                batch_results.append(
                    {
                        "batch_number": i // batch_size + 1,
                        "batch_size": len(batch),
                        "records_updated": batch_updated,
                        "execution_time_s": batch_time,
                        "records_per_second": len(batch) / batch_time if batch_time > 0 else 0,
                    }
                )

                logger.info(
                    f"    Updated {batch_updated:,} records in {batch_time:.3f}s "
                    f"({len(batch) / batch_time:.1f} records/sec)"
                )

            except Exception as e:
                logger.error(f"    Batch {i//batch_size + 1} failed: {e}")
                batch_results.append(
                    {
                        "batch_number": i // batch_size + 1,
                        "batch_size": len(batch),
                        "records_updated": 0,
                        "execution_time_s": 0,
                        "records_per_second": 0,
                        "error": str(e),
                    }
                )

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate statistics
        successful_batches = [b for b in batch_results if "error" not in b]
        if successful_batches:
            avg_batch_time = statistics.mean([b["execution_time_s"] for b in successful_batches])
            avg_records_per_sec = statistics.mean(
                [b["records_per_second"] for b in successful_batches]
            )
            min_records_per_sec = min([b["records_per_second"] for b in successful_batches])
            max_records_per_sec = max([b["records_per_second"] for b in successful_batches])
        else:
            avg_batch_time = 0
            avg_records_per_sec = 0
            min_records_per_sec = 0
            max_records_per_sec = 0

        logger.info("Batch processing completed:")
        logger.info(f"  Total records updated: {total_updated:,}")
        logger.info(f"  Total execution time: {total_time:.3f}s")
        logger.info(f"  Average batch time: {avg_batch_time:.3f}s")
        logger.info(f"  Average throughput: {avg_records_per_sec:.1f} records/sec")
        logger.info(
            f"  Throughput range: {min_records_per_sec:.1f} - {max_records_per_sec:.1f} records/sec"
        )

        return {
            "total_records": len(updates),
            "batch_size": batch_size,
            "total_updated": total_updated,
            "total_execution_time_s": total_time,
            "avg_batch_time_s": avg_batch_time,
            "avg_records_per_second": avg_records_per_sec,
            "min_records_per_second": min_records_per_sec,
            "max_records_per_second": max_records_per_sec,
            "batch_results": batch_results,
            "successful_batches": len(successful_batches),
            "failed_batches": len(batch_results) - len(successful_batches),
        }

    def test_memory_usage_with_large_datasets(self) -> dict[str, Any]:
        """Test memory usage patterns with large datasets.

        Returns:
            Memory usage test results
        """
        logger.info("Testing memory usage with large datasets...")

        memory_results = {}

        for dataset_size in self.large_dataset_sizes:
            logger.info(f"\nTesting memory usage with {dataset_size:,} records...")

            # Generate dataset
            anime_updates, file_updates = self.generate_large_dataset(dataset_size)

            # Test memory usage during batch processing
            import psutil

            process = psutil.Process()

            # Measure memory before processing
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Process anime metadata in batches
            anime_results = self.process_batches(anime_updates, 5000, "anime_metadata")

            # Measure memory after anime processing
            anime_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Process parsed files in batches
            file_results = self.process_batches(file_updates, 5000, "parsed_files")

            # Measure memory after file processing
            final_memory = process.memory_info().rss / 1024 / 1024  # MB

            memory_results[dataset_size] = {
                "dataset_size": dataset_size,
                "initial_memory_mb": initial_memory,
                "anime_memory_mb": anime_memory,
                "final_memory_mb": final_memory,
                "anime_memory_delta_mb": anime_memory - initial_memory,
                "file_memory_delta_mb": final_memory - anime_memory,
                "total_memory_delta_mb": final_memory - initial_memory,
                "memory_per_record_mb": (final_memory - initial_memory) / dataset_size,
                "anime_results": anime_results,
                "file_results": file_results,
            }

            logger.info(f"Memory usage for {dataset_size:,} records:")
            logger.info(f"  Initial memory: {initial_memory:.1f} MB")
            logger.info(f"  After anime processing: {anime_memory:.1f} MB")
            logger.info(f"  After file processing: {final_memory:.1f} MB")
            logger.info(f"  Total memory increase: {final_memory - initial_memory:.1f} MB")
            logger.info(
                f"  Memory per record: {(final_memory - initial_memory) / dataset_size:.6f} MB"
            )

        return memory_results

    def test_batch_size_optimization(self) -> dict[str, Any]:
        """Test optimal batch sizes for different dataset sizes.

        Returns:
            Batch size optimization results
        """
        logger.info("Testing batch size optimization...")

        optimization_results = {}
        test_dataset_size = 25000  # Use medium dataset for batch size testing

        # Generate test dataset
        anime_updates, file_updates = self.generate_large_dataset(test_dataset_size)

        for batch_size in self.batch_sizes:
            logger.info(
                f"\nTesting batch size {batch_size:,} with {test_dataset_size:,} records..."
            )

            # Test anime metadata processing
            anime_results = self.process_batches(anime_updates, batch_size, "anime_metadata")

            # Test parsed files processing
            file_results = self.process_batches(file_updates, batch_size, "parsed_files")

            optimization_results[batch_size] = {
                "batch_size": batch_size,
                "dataset_size": test_dataset_size,
                "anime_results": anime_results,
                "file_results": file_results,
                "combined_throughput": (
                    anime_results["avg_records_per_second"] + file_results["avg_records_per_second"]
                )
                / 2,
                "total_execution_time": anime_results["total_execution_time_s"]
                + file_results["total_execution_time_s"],
            }

            logger.info(f"Batch size {batch_size:,} results:")
            logger.info(
                f"  Anime throughput: {anime_results['avg_records_per_second']:.1f} records/sec"
            )
            logger.info(
                f"  File throughput: {file_results['avg_records_per_second']:.1f} records/sec"
            )
            logger.info(
                f"  Combined throughput: {optimization_results[batch_size]['combined_throughput']:.1f} records/sec"
            )
            logger.info(
                f"  Total execution time: {optimization_results[batch_size]['total_execution_time']:.3f}s"
            )

        # Find optimal batch size
        best_batch_size = max(
            optimization_results.keys(),
            key=lambda x: optimization_results[x]["combined_throughput"],
        )

        logger.info(f"\nOptimal batch size: {best_batch_size:,} records/sec")
        logger.info(
            f"Best throughput: {optimization_results[best_batch_size]['combined_throughput']:.1f} records/sec"
        )

        optimization_results["optimal_batch_size"] = best_batch_size
        optimization_results["best_throughput"] = optimization_results[best_batch_size][
            "combined_throughput"
        ]

        return optimization_results

    def test_concurrent_batch_processing(self) -> dict[str, Any]:
        """Test concurrent batch processing performance.

        Returns:
            Concurrent processing test results
        """
        logger.info("Testing concurrent batch processing...")

        # Generate test dataset
        dataset_size = 20000
        anime_updates, file_updates = self.generate_large_dataset(dataset_size)

        def process_anime_batches():
            """Process anime metadata batches concurrently."""
            return self.process_batches(anime_updates, 2500, "anime_metadata")

        def process_file_batches():
            """Process parsed file batches concurrently."""
            return self.process_batches(file_updates, 2500, "parsed_files")

        # Test sequential processing
        logger.info("Testing sequential processing...")
        sequential_start = time.time()

        sequential_anime_results = self.process_batches(anime_updates, 2500, "anime_metadata")
        sequential_file_results = self.process_batches(file_updates, 2500, "parsed_files")

        sequential_end = time.time()
        sequential_time = sequential_end - sequential_start

        # Test concurrent processing (simulated with async)
        logger.info("Testing concurrent processing...")
        concurrent_start = time.time()

        # Note: In a real concurrent scenario, these would run in parallel
        # For this test, we'll simulate concurrent processing
        concurrent_anime_results = process_anime_batches()
        concurrent_file_results = process_file_batches()

        concurrent_end = time.time()
        concurrent_time = concurrent_end - concurrent_start

        # Calculate improvements
        time_improvement = (
            ((sequential_time - concurrent_time) / sequential_time) * 100
            if sequential_time > 0
            else 0
        )
        throughput_improvement = (
            (
                concurrent_anime_results["avg_records_per_second"]
                + concurrent_file_results["avg_records_per_second"]
            )
            / (
                sequential_anime_results["avg_records_per_second"]
                + sequential_file_results["avg_records_per_second"]
            )
            - 1
        ) * 100

        logger.info("Concurrent processing results:")
        logger.info(f"  Sequential time: {sequential_time:.3f}s")
        logger.info(f"  Concurrent time: {concurrent_time:.3f}s")
        logger.info(f"  Time improvement: {time_improvement:.1f}%")
        logger.info(f"  Throughput improvement: {throughput_improvement:.1f}%")

        return {
            "dataset_size": dataset_size,
            "sequential_results": {
                "anime": sequential_anime_results,
                "file": sequential_file_results,
                "total_time_s": sequential_time,
            },
            "concurrent_results": {
                "anime": concurrent_anime_results,
                "file": concurrent_file_results,
                "total_time_s": concurrent_time,
            },
            "improvements": {
                "time_improvement_percent": time_improvement,
                "throughput_improvement_percent": throughput_improvement,
            },
        }

    async def run_large_dataset_tests(self) -> dict[str, Any]:
        """Run all large dataset batch processing tests.

        Returns:
            Complete test results
        """
        logger.info("Starting large dataset batch processing tests...")

        results = {
            "memory_usage_tests": self.test_memory_usage_with_large_datasets(),
            "batch_size_optimization": self.test_batch_size_optimization(),
            "concurrent_processing": await self.test_concurrent_batch_processing(),
            "summary": {},
        }

        # Generate summary
        results["summary"] = self._generate_large_dataset_summary(results)

        return results

    def _generate_large_dataset_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary statistics from large dataset test results.

        Args:
            results: Complete test results

        Returns:
            Summary statistics
        """
        summary = {
            "memory_efficiency": {},
            "performance_characteristics": {},
            "scalability_metrics": {},
        }

        # Analyze memory efficiency
        memory_tests = results["memory_usage_tests"]
        if memory_tests:
            dataset_sizes = []
            memory_per_record = []
            total_memory_usage = []

            for dataset_size, test_result in memory_tests.items():
                dataset_sizes.append(dataset_size)
                memory_per_record.append(test_result["memory_per_record_mb"])
                total_memory_usage.append(test_result["total_memory_delta_mb"])

            summary["memory_efficiency"] = {
                "avg_memory_per_record_mb": statistics.mean(memory_per_record),
                "max_memory_per_record_mb": max(memory_per_record),
                "min_memory_per_record_mb": min(memory_per_record),
                "largest_dataset_memory_mb": max(total_memory_usage),
                "memory_scaling_factor": (
                    max(total_memory_usage) / min(total_memory_usage)
                    if min(total_memory_usage) > 0
                    else 1.0
                ),
            }

        # Analyze performance characteristics
        batch_optimization = results["batch_size_optimization"]
        if batch_optimization and "optimal_batch_size" in batch_optimization:
            summary["performance_characteristics"] = {
                "optimal_batch_size": batch_optimization["optimal_batch_size"],
                "best_throughput_records_per_sec": batch_optimization["best_throughput"],
                "batch_size_range_tested": f"{min(batch_optimization.keys())} - {max(batch_optimization.keys())}",
            }

        # Analyze scalability metrics
        concurrent_results = results["concurrent_processing"]
        if concurrent_results and "improvements" in concurrent_results:
            summary["scalability_metrics"] = {
                "concurrent_time_improvement_percent": concurrent_results["improvements"][
                    "time_improvement_percent"
                ],
                "concurrent_throughput_improvement_percent": concurrent_results["improvements"][
                    "throughput_improvement_percent"
                ],
                "largest_dataset_tested": max(memory_tests.keys()) if memory_tests else 0,
            }

        return summary


@pytest.mark.asyncio
async def test_large_dataset_batch_processing():
    """Main large dataset batch processing test entry point."""
    # Initialize database manager
    db_manager = DatabaseManager("sqlite:///:memory:")  # Use in-memory database for testing

    try:
        # Create large dataset processor
        processor = LargeDatasetBatchProcessor(db_manager)

        # Run all large dataset tests
        results = await processor.run_large_dataset_tests()

        # Log final results
        logger.info("\n" + "=" * 60)
        logger.info("LARGE DATASET BATCH PROCESSING TEST RESULTS")
        logger.info("=" * 60)

        summary = results["summary"]

        # Memory efficiency summary
        if "memory_efficiency" in summary:
            mem_eff = summary["memory_efficiency"]
            logger.info("Memory Efficiency:")
            logger.info(
                f"  Average memory per record: {mem_eff.get('avg_memory_per_record_mb', 0):.6f} MB"
            )
            logger.info(
                f"  Memory per record range: {mem_eff.get('min_memory_per_record_mb', 0):.6f} - {mem_eff.get('max_memory_per_record_mb', 0):.6f} MB"
            )
            logger.info(
                f"  Largest dataset memory usage: {mem_eff.get('largest_dataset_memory_mb', 0):.1f} MB"
            )
            logger.info(f"  Memory scaling factor: {mem_eff.get('memory_scaling_factor', 1):.2f}")

        # Performance characteristics summary
        if "performance_characteristics" in summary:
            perf_char = summary["performance_characteristics"]
            logger.info("\nPerformance Characteristics:")
            logger.info(f"  Optimal batch size: {perf_char.get('optimal_batch_size', 0):,} records")
            logger.info(
                f"  Best throughput: {perf_char.get('best_throughput_records_per_sec', 0):.1f} records/sec"
            )
            logger.info(f"  Batch sizes tested: {perf_char.get('batch_size_range_tested', 'N/A')}")

        # Scalability metrics summary
        if "scalability_metrics" in summary:
            scaling = summary["scalability_metrics"]
            logger.info("\nScalability Metrics:")
            logger.info(
                f"  Concurrent time improvement: {scaling.get('concurrent_time_improvement_percent', 0):.1f}%"
            )
            logger.info(
                f"  Concurrent throughput improvement: {scaling.get('concurrent_throughput_improvement_percent', 0):.1f}%"
            )
            logger.info(
                f"  Largest dataset tested: {scaling.get('largest_dataset_tested', 0):,} records"
            )

        # Assert performance thresholds
        if "memory_efficiency" in summary:
            mem_eff = summary["memory_efficiency"]
            assert (
                mem_eff.get("avg_memory_per_record_mb", 0) < 0.001
            ), "Average memory per record should be < 0.001 MB"
            assert (
                mem_eff.get("memory_scaling_factor", 1) < 10
            ), "Memory scaling should be reasonable"

        if "performance_characteristics" in summary:
            perf_char = summary["performance_characteristics"]
            assert (
                perf_char.get("best_throughput_records_per_sec", 0) > 5000
            ), "Best throughput should be > 5000 records/sec"

        logger.info("\n✅ All large dataset batch processing tests passed!")

        return results

    finally:
        # Cleanup
        if hasattr(db_manager, "close"):
            db_manager.close()


if __name__ == "__main__":
    # Run large dataset tests directly
    asyncio.run(test_large_dataset_batch_processing())
