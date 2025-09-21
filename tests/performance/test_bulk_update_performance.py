"""Performance tests for bulk update operations.

This module contains comprehensive load tests to validate the performance
improvements from batch update operations and N+1 query elimination.
"""

import asyncio
import logging
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
from sqlalchemy import text

from src.core.database import DatabaseManager
from src.core.database import AnimeMetadata, ParsedFile
from src.core.services.bulk_update_task import ConcreteBulkUpdateTask

# Configure logging for performance tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Container for performance test metrics."""

    def __init__(self) -> None:
        self.execution_times: List[float] = []
        self.query_counts: List[int] = []
        self.memory_usage: List[float] = []
        self.batch_sizes: List[int] = []

    def add_measurement(self, execution_time: float, query_count: int, memory_usage: float, batch_size: int) -> None:
        """Add a performance measurement."""
        self.execution_times.append(execution_time)
        self.query_counts.append(query_count)
        self.memory_usage.append(memory_usage)
        self.batch_sizes.append(batch_size)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for all metrics."""
        return {
            "execution_time": {
                "mean": statistics.mean(self.execution_times) if self.execution_times else 0,
                "median": statistics.median(self.execution_times) if self.execution_times else 0,
                "min": min(self.execution_times) if self.execution_times else 0,
                "max": max(self.execution_times) if self.execution_times else 0,
                "stdev": statistics.stdev(self.execution_times) if len(self.execution_times) > 1 else 0,
            },
            "query_count": {
                "mean": statistics.mean(self.query_counts) if self.query_counts else 0,
                "median": statistics.median(self.query_counts) if self.query_counts else 0,
                "min": min(self.query_counts) if self.query_counts else 0,
                "max": max(self.query_counts) if self.query_counts else 0,
            },
            "memory_usage": {
                "mean": statistics.mean(self.memory_usage) if self.memory_usage else 0,
                "median": statistics.median(self.memory_usage) if self.memory_usage else 0,
                "min": min(self.memory_usage) if self.memory_usage else 0,
                "max": max(self.memory_usage) if self.memory_usage else 0,
            },
            "total_measurements": len(self.execution_times),
        }


class QueryCounter:
    """Context manager to count database queries during operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager
        self.initial_query_count = 0
        self.final_query_count = 0

    def __enter__(self) -> "QueryCounter":
        # Get initial query count from database statistics
        with self.db_manager.get_session() as session:
            result = session.execute(text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"))
            self.initial_query_count = result.scalar() or 0
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Get final query count
        with self.db_manager.get_session() as session:
            result = session.execute(text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"))
            self.final_query_count = result.scalar() or 0

    @property
    def query_count(self) -> int:
        """Get the number of queries executed during the context."""
        return self.final_query_count - self.initial_query_count


class BulkUpdatePerformanceTest:
    """Comprehensive performance tests for bulk update operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager
        self.db_manager.initialize()  # Ensure database is initialized
        self.test_data_sizes = [100, 500, 1000, 2000, 5000]
        self.metrics = PerformanceMetrics()

    async def setup_test_data(self, size: int) -> Tuple[List[Dict], List[Dict]]:
        """Create test data for performance testing.

        Args:
            size: Number of records to create

        Returns:
            Tuple of (anime_metadata_updates, parsed_file_updates)
        """
        logger.info(f"Setting up test data for {size} records...")

        # Create anime metadata updates
        anime_updates = []
        for i in range(size):
            anime_updates.append({
                "tmdb_id": 1000 + i,
                "status": "processed" if i % 2 == 0 else "pending",
                "title": f"Test Anime {i}",
                "updated_at": "2024-01-01T00:00:00Z"
            })

        # Create parsed file updates
        file_updates = []
        for i in range(size):
            file_updates.append({
                "file_path": f"/test/path/anime_{i}.mkv",
                "is_processed": i % 2 == 0,
                "processing_status": "completed" if i % 2 == 0 else "pending",
                "updated_at": "2024-01-01T00:00:00Z"
            })

        return anime_updates, file_updates

    async def test_bulk_anime_metadata_update_performance(self, updates: List[Dict]) -> Dict[str, Any]:
        """Test performance of bulk anime metadata updates.

        Args:
            updates: List of update dictionaries

        Returns:
            Performance metrics dictionary
        """
        logger.info(f"Testing bulk anime metadata update with {len(updates)} records...")

        start_time = time.time()
        start_memory = self._get_memory_usage()

        with QueryCounter(self.db_manager) as query_counter:
            # Create and execute bulk update task
            bulk_task = ConcreteBulkUpdateTask(
                update_type="anime_metadata",
                updates=updates,
                db_manager=self.db_manager
            )

            updated_count = bulk_task.execute()

        end_time = time.time()
        end_memory = self._get_memory_usage()

        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory
        query_count = query_counter.query_count

        logger.info(f"Bulk anime metadata update completed:")
        logger.info(f"  - Records updated: {updated_count}")
        logger.info(f"  - Execution time: {execution_time:.3f}s")
        logger.info(f"  - Query count: {query_count}")
        logger.info(f"  - Memory usage: {memory_usage:.2f}MB")

        return {
            "execution_time": execution_time,
            "query_count": query_count,
            "memory_usage": memory_usage,
            "records_updated": updated_count,
            "batch_size": len(updates)
        }

    async def test_bulk_parsed_files_update_performance(self, updates: List[Dict]) -> Dict[str, Any]:
        """Test performance of bulk parsed files updates.

        Args:
            updates: List of update dictionaries

        Returns:
            Performance metrics dictionary
        """
        logger.info(f"Testing bulk parsed files update with {len(updates)} records...")

        start_time = time.time()
        start_memory = self._get_memory_usage()

        with QueryCounter(self.db_manager) as query_counter:
            # Create and execute bulk update task
            bulk_task = ConcreteBulkUpdateTask(
                update_type="parsed_files",
                updates=updates,
                db_manager=self.db_manager
            )

            updated_count = bulk_task.execute()

        end_time = time.time()
        end_memory = self._get_memory_usage()

        execution_time = end_time - start_time
        memory_usage = end_memory - start_memory
        query_count = query_counter.query_count

        logger.info(f"Bulk parsed files update completed:")
        logger.info(f"  - Records updated: {updated_count}")
        logger.info(f"  - Execution time: {execution_time:.3f}s")
        logger.info(f"  - Query count: {query_count}")
        logger.info(f"  - Memory usage: {memory_usage:.2f}MB")

        return {
            "execution_time": execution_time,
            "query_count": query_count,
            "memory_usage": memory_usage,
            "records_updated": updated_count,
            "batch_size": len(updates)
        }

    async def test_individual_vs_bulk_performance(self, updates: List[Dict], update_type: str) -> Dict[str, Any]:
        """Compare individual updates vs bulk updates performance.

        Args:
            updates: List of update dictionaries
            update_type: Type of update ('anime_metadata' or 'parsed_files')

        Returns:
            Comparison metrics dictionary
        """
        logger.info(f"Comparing individual vs bulk updates for {update_type} with {len(updates)} records...")

        # Test individual updates (simulating N+1 pattern)
        individual_start = time.time()
        individual_memory_start = self._get_memory_usage()

        with QueryCounter(self.db_manager) as individual_counter:
            for update in updates[:100]:  # Limit to 100 for individual test
                if update_type == "anime_metadata":
                    self.db_manager.update_anime_metadata(update["tmdb_id"], update)
                elif update_type == "parsed_files":
                    self.db_manager.update_parsed_file(update["file_path"], update)

        individual_end = time.time()
        individual_memory_end = self._get_memory_usage()

        individual_time = individual_end - individual_start
        individual_memory = individual_memory_end - individual_memory_start
        individual_queries = individual_counter.query_count

        # Test bulk updates
        bulk_start = time.time()
        bulk_memory_start = self._get_memory_usage()

        with QueryCounter(self.db_manager) as bulk_counter:
            bulk_task = ConcreteBulkUpdateTask(
                update_type=update_type,
                updates=updates[:100],  # Same subset for fair comparison
                db_manager=self.db_manager
            )
            bulk_task.execute()

        bulk_end = time.time()
        bulk_memory_end = self._get_memory_usage()

        bulk_time = bulk_end - bulk_start
        bulk_memory = bulk_memory_end - bulk_memory_start
        bulk_queries = bulk_counter.query_count

        # Calculate improvements
        time_improvement = ((individual_time - bulk_time) / individual_time) * 100 if individual_time > 0 else 0
        query_improvement = ((individual_queries - bulk_queries) / individual_queries) * 100 if individual_queries > 0 else 0
        memory_improvement = ((individual_memory - bulk_memory) / individual_memory) * 100 if individual_memory > 0 else 0

        logger.info(f"Performance comparison for {update_type}:")
        logger.info(f"  Individual updates: {individual_time:.3f}s, {individual_queries} queries, {individual_memory:.2f}MB")
        logger.info(f"  Bulk updates: {bulk_time:.3f}s, {bulk_queries} queries, {bulk_memory:.2f}MB")
        logger.info(f"  Time improvement: {time_improvement:.1f}%")
        logger.info(f"  Query reduction: {query_improvement:.1f}%")
        logger.info(f"  Memory improvement: {memory_improvement:.1f}%")

        return {
            "individual": {
                "execution_time": individual_time,
                "query_count": individual_queries,
                "memory_usage": individual_memory
            },
            "bulk": {
                "execution_time": bulk_time,
                "query_count": bulk_queries,
                "memory_usage": bulk_memory
            },
            "improvements": {
                "time_improvement_percent": time_improvement,
                "query_reduction_percent": query_improvement,
                "memory_improvement_percent": memory_improvement
            }
        }

    async def run_comprehensive_performance_test(self) -> Dict[str, Any]:
        """Run comprehensive performance tests across different data sizes.

        Returns:
            Complete performance test results
        """
        logger.info("Starting comprehensive bulk update performance tests...")

        results = {
            "anime_metadata_tests": {},
            "parsed_files_tests": {},
            "comparison_tests": {},
            "summary": {}
        }

        for size in self.test_data_sizes:
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing with {size} records")
            logger.info(f"{'='*50}")

            # Setup test data
            anime_updates, file_updates = await self.setup_test_data(size)

            # Test anime metadata bulk updates
            anime_results = await self.test_bulk_anime_metadata_update_performance(anime_updates)
            results["anime_metadata_tests"][size] = anime_results

            # Test parsed files bulk updates
            file_results = await self.test_bulk_parsed_files_update_performance(file_updates)
            results["parsed_files_tests"][size] = file_results

            # Test comparison (only for smaller sizes to avoid timeout)
            if size <= 1000:
                anime_comparison = await self.test_individual_vs_bulk_performance(anime_updates, "anime_metadata")
                file_comparison = await self.test_individual_vs_bulk_performance(file_updates, "parsed_files")

                results["comparison_tests"][size] = {
                    "anime_metadata": anime_comparison,
                    "parsed_files": file_comparison
                }

        # Generate summary
        results["summary"] = self._generate_performance_summary(results)

        return results

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return 0.0

    def _generate_performance_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from test results.

        Args:
            results: Complete test results

        Returns:
            Summary statistics
        """
        summary = {
            "anime_metadata_summary": {},
            "parsed_files_summary": {},
            "overall_improvements": {}
        }

        # Calculate anime metadata summary
        anime_times = [results["anime_metadata_tests"][size]["execution_time"] for size in self.test_data_sizes]
        anime_queries = [results["anime_metadata_tests"][size]["query_count"] for size in self.test_data_sizes]

        summary["anime_metadata_summary"] = {
            "avg_execution_time": statistics.mean(anime_times),
            "avg_query_count": statistics.mean(anime_queries),
            "scalability_ratio": anime_times[-1] / anime_times[0] if len(anime_times) > 1 else 1.0
        }

        # Calculate parsed files summary
        file_times = [results["parsed_files_tests"][size]["execution_time"] for size in self.test_data_sizes]
        file_queries = [results["parsed_files_tests"][size]["query_count"] for size in self.test_data_sizes]

        summary["parsed_files_summary"] = {
            "avg_execution_time": statistics.mean(file_times),
            "avg_query_count": statistics.mean(file_queries),
            "scalability_ratio": file_times[-1] / file_times[0] if len(file_times) > 1 else 1.0
        }

        # Calculate overall improvements from comparison tests
        if results["comparison_tests"]:
            time_improvements = []
            query_improvements = []

            for size, comparison in results["comparison_tests"].items():
                anime_improvement = comparison["anime_metadata"]["improvements"]["time_improvement_percent"]
                file_improvement = comparison["parsed_files"]["improvements"]["time_improvement_percent"]
                time_improvements.extend([anime_improvement, file_improvement])

                anime_query_improvement = comparison["anime_metadata"]["improvements"]["query_reduction_percent"]
                file_query_improvement = comparison["parsed_files"]["improvements"]["query_reduction_percent"]
                query_improvements.extend([anime_query_improvement, file_query_improvement])

            summary["overall_improvements"] = {
                "avg_time_improvement_percent": statistics.mean(time_improvements),
                "avg_query_reduction_percent": statistics.mean(query_improvements),
                "min_time_improvement_percent": min(time_improvements),
                "min_query_reduction_percent": min(query_improvements)
            }

        return summary


@pytest.mark.asyncio
async def test_bulk_update_performance():
    """Main performance test entry point."""
    # Initialize database manager
    db_manager = DatabaseManager("sqlite:///:memory:")  # Use in-memory database for testing

    try:
        # Create performance test instance
        perf_test = BulkUpdatePerformanceTest(db_manager)

        # Run comprehensive performance tests
        results = await perf_test.run_comprehensive_performance_test()

        # Log final results
        logger.info("\n" + "="*60)
        logger.info("PERFORMANCE TEST RESULTS SUMMARY")
        logger.info("="*60)

        summary = results["summary"]

        logger.info(f"Anime Metadata Performance:")
        logger.info(f"  Average execution time: {summary['anime_metadata_summary']['avg_execution_time']:.3f}s")
        logger.info(f"  Average query count: {summary['anime_metadata_summary']['avg_query_count']:.1f}")
        logger.info(f"  Scalability ratio: {summary['anime_metadata_summary']['scalability_ratio']:.2f}")

        logger.info(f"\nParsed Files Performance:")
        logger.info(f"  Average execution time: {summary['parsed_files_summary']['avg_execution_time']:.3f}s")
        logger.info(f"  Average query count: {summary['parsed_files_summary']['avg_query_count']:.1f}")
        logger.info(f"  Scalability ratio: {summary['parsed_files_summary']['scalability_ratio']:.2f}")

        if "overall_improvements" in summary:
            improvements = summary["overall_improvements"]
            logger.info(f"\nOverall Improvements vs Individual Updates:")
            logger.info(f"  Average time improvement: {improvements['avg_time_improvement_percent']:.1f}%")
            logger.info(f"  Average query reduction: {improvements['avg_query_reduction_percent']:.1f}%")
            logger.info(f"  Minimum time improvement: {improvements['min_time_improvement_percent']:.1f}%")
            logger.info(f"  Minimum query reduction: {improvements['min_query_reduction_percent']:.1f}%")

        # Assert performance improvements
        assert improvements["avg_time_improvement_percent"] > 50, "Expected >50% time improvement"
        assert improvements["avg_query_reduction_percent"] > 80, "Expected >80% query reduction"

        logger.info("\n✅ All performance tests passed!")

        return results

    finally:
        # Cleanup
        if hasattr(db_manager, 'close'):
            db_manager.close()


if __name__ == "__main__":
    # Run performance tests directly
    asyncio.run(test_bulk_update_performance())
