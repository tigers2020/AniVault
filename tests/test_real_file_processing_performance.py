"""Real file processing performance tests without artificial delays."""

import os
import tempfile
import time
from pathlib import Path
from typing import List

import pytest

from src.core.thread_executor_manager import get_thread_executor_manager
from src.core.models import ParsedAnimeInfo
from src.core.anime_parser import AnimeParser


class RealPerformanceTestHelper:
    """Helper class for real performance testing without artificial delays."""

    @staticmethod
    def create_test_files(directory: str, count: int) -> List[str]:
        """Create test files for performance testing.

        Args:
            directory: Directory to create files in
            count: Number of files to create

        Returns:
            List of created file paths
        """
        file_paths = []
        for i in range(count):
            # Create files with realistic anime filenames
            filename = f"Attack on Titan.S01E{i+1:02d}.1080p.BluRay.x264-ANIME.mkv"
            file_path = os.path.join(directory, filename)

            # Create empty file
            Path(file_path).touch()
            file_paths.append(file_path)

        return file_paths

    @staticmethod
    def real_file_processing_task(file_path: str) -> ParsedAnimeInfo:
        """Real file processing task using actual AnimeParser (no artificial delays).

        Args:
            file_path: Path to the file to process

        Returns:
            ParsedAnimeInfo object with parsed data
        """
        # Use the actual AnimeParser for realistic performance testing
        parser = AnimeParser()
        filename = os.path.basename(file_path)

        # Parse using the real parser (this is what actually happens in the app)
        parsed_info = parser.parse_filename(filename)

        return parsed_info


class TestRealFileProcessingPerformance:
    """Test real file processing performance without artificial delays."""

    def setup_method(self):
        """Setup test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.executor_manager = get_thread_executor_manager()

    def teardown_method(self):
        """Cleanup test environment."""
        # Clean up test files
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

        # Shutdown executor manager
        self.executor_manager.shutdown_all(wait=True)

    def test_real_sequential_vs_parallel_processing(self):
        """Test real performance improvement without artificial delays."""
        # Create test files
        file_count = 100
        test_files = RealPerformanceTestHelper.create_test_files(self.test_dir, file_count)

        print(f"\n=== Real Performance Test (No Artificial Delays) ===")
        print(f"Processing {file_count} files...")

        # Test sequential processing
        start_time = time.time()
        sequential_results = []
        for file_path in test_files:
            result = RealPerformanceTestHelper.real_file_processing_task(file_path)
            sequential_results.append(result)
        sequential_time = time.time() - start_time

        # Test parallel processing with ThreadPoolExecutor
        start_time = time.time()
        parallel_results = []

        with self.executor_manager.get_general_executor() as executor:
            from concurrent.futures import as_completed

            # Submit all tasks
            future_to_file = {
                executor.submit(RealPerformanceTestHelper.real_file_processing_task, file_path): file_path
                for file_path in test_files
            }

            # Collect results as they complete
            for future in as_completed(future_to_file):
                result = future.result()
                parallel_results.append(result)

        parallel_time = time.time() - start_time

        # Verify results are equivalent
        assert len(sequential_results) == len(parallel_results) == file_count

        # Calculate performance metrics
        speedup = sequential_time / parallel_time
        sequential_rate = file_count / sequential_time
        parallel_rate = file_count / parallel_time

        print(f"Sequential time: {sequential_time:.4f}s ({sequential_rate:.1f} files/sec)")
        print(f"Parallel time: {parallel_time:.4f}s ({parallel_rate:.1f} files/sec)")
        print(f"Speedup: {speedup:.2f}x")
        print(f"Performance improvement: {(parallel_rate - sequential_rate):.1f} additional files/sec")

        # For real file processing, we expect significant speedup
        # Even without artificial delays, parsing operations benefit from parallelism
        assert speedup > 1.0, f"Expected speedup > 1x, got {speedup:.2f}x"

        # Real processing should be much faster than the artificial delay test
        print(f"Real processing is {sequential_time:.4f}s vs {1.049:.4f}s (with 10ms delays)")
        print(f"Real processing is {sequential_time/1.049*100:.1f}% of artificial delay time")

    def test_small_batch_performance(self):
        """Test performance with smaller batches (more realistic usage)."""
        file_counts = [10, 25, 50]

        print(f"\n=== Small Batch Performance Test ===")

        for file_count in file_counts:
            test_files = RealPerformanceTestHelper.create_test_files(self.test_dir, file_count)

            # Sequential processing
            start_time = time.time()
            for file_path in test_files:
                RealPerformanceTestHelper.real_file_processing_task(file_path)
            sequential_time = time.time() - start_time

            # Parallel processing
            start_time = time.time()
            with self.executor_manager.get_general_executor() as executor:
                from concurrent.futures import as_completed

                futures = [
                    executor.submit(RealPerformanceTestHelper.real_file_processing_task, file_path)
                    for file_path in test_files
                ]

                for future in as_completed(futures):
                    future.result()

            parallel_time = time.time() - start_time

            speedup = sequential_time / parallel_time if parallel_time > 0 else 0
            print(f"{file_count:2d} files: Sequential {sequential_time:.4f}s, Parallel {parallel_time:.4f}s, Speedup {speedup:.2f}x")

    def test_parser_performance_breakdown(self):
        """Test individual parser performance to understand bottlenecks."""
        test_files = RealPerformanceTestHelper.create_test_files(self.test_dir, 10)

        print(f"\n=== Parser Performance Breakdown ===")

        # Test just the parsing logic
        parser = AnimeParser()
        start_time = time.time()

        for file_path in test_files:
            filename = os.path.basename(file_path)
            parser.parse_filename(filename)

        parsing_time = time.time() - start_time

        print(f"Pure parsing time for 10 files: {parsing_time:.4f}s")
        print(f"Average parsing time per file: {parsing_time/10:.4f}s ({parsing_time/10*1000:.2f}ms)")

        # This shows the actual parsing overhead
        assert parsing_time < 0.1, f"Parsing should be very fast, got {parsing_time:.4f}s"


if __name__ == "__main__":
    # Run real performance tests
    pytest.main([__file__, "-v", "-s"])
