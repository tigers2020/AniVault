"""Performance tests for ThreadPoolExecutor implementation."""

import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

import pytest

from src.core.thread_executor_manager import get_thread_executor_manager
from src.core.models import ParsedAnimeInfo


class PerformanceTestHelper:
    """Helper class for performance testing utilities."""

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
            # Create files with anime-like names for realistic testing
            filename = f"Anime.Title.S01E{i+1:02d}.1080p.BluRay.x264.mkv"
            file_path = os.path.join(directory, filename)

            # Create empty file
            Path(file_path).touch()
            file_paths.append(file_path)

        return file_paths

    @staticmethod
    def mock_file_processing_task(file_path: str) -> ParsedAnimeInfo:
        """Mock file processing task that simulates actual work.

        Args:
            file_path: Path to the file to process

        Returns:
            ParsedAnimeInfo object with parsed data
        """
        # Simulate some processing time (file I/O, parsing, etc.)
        time.sleep(0.01)  # 10ms per file

        # Extract filename for parsing
        filename = os.path.basename(file_path)

        # Simple parsing logic (similar to actual implementation)
        parts = filename.split('.')
        if len(parts) >= 3:
            title = parts[0].replace(' ', ' ')
            episode = None
            resolution = None

            for part in parts:
                if part.startswith('E') and part[1:].isdigit():
                    episode = int(part[1:])
                elif part in ['720p', '1080p', '4K']:
                    resolution = part

            return ParsedAnimeInfo(
                title=title,
                episode=episode,
                resolution=resolution,
                resolution_width=1920 if resolution == '1080p' else 1280,
                resolution_height=1080 if resolution == '1080p' else 720,
                file_extension='.mkv'
            )
        else:
            # Fallback for simple filenames
            return ParsedAnimeInfo(
                title=filename,
                episode=None,
                resolution='1080p',
                resolution_width=1920,
                resolution_height=1080,
                file_extension='.mkv'
            )


class TestThreadExecutorPerformance:
    """Test ThreadPoolExecutor performance improvements."""

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

    def test_sequential_vs_parallel_processing(self):
        """Test performance improvement of parallel processing over sequential."""
        # Create test files
        file_count = 100
        test_files = PerformanceTestHelper.create_test_files(self.test_dir, file_count)

        # Test sequential processing
        start_time = time.time()
        sequential_results = []
        for file_path in test_files:
            result = PerformanceTestHelper.mock_file_processing_task(file_path)
            sequential_results.append(result)
        sequential_time = time.time() - start_time

        # Test parallel processing with ThreadPoolExecutor
        start_time = time.time()
        parallel_results = []

        with self.executor_manager.get_general_executor() as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(PerformanceTestHelper.mock_file_processing_task, file_path): file_path
                for file_path in test_files
            }

            # Collect results as they complete
            for future in as_completed(future_to_file):
                result = future.result()
                parallel_results.append(result)

        parallel_time = time.time() - start_time

        # Verify results are equivalent
        assert len(sequential_results) == len(parallel_results) == file_count

        # Performance improvement should be significant for I/O-bound tasks
        speedup = sequential_time / parallel_time
        print(f"Sequential time: {sequential_time:.3f}s")
        print(f"Parallel time: {parallel_time:.3f}s")
        print(f"Speedup: {speedup:.2f}x")

        # For I/O-bound tasks with 100 files, we expect at least 2x speedup
        # This is a conservative estimate - actual speedup may be higher
        assert speedup >= 2.0, f"Expected at least 2x speedup, got {speedup:.2f}x"

    def test_executor_configuration_performance(self):
        """Test different executor configurations for optimal performance."""
        file_count = 50
        test_files = PerformanceTestHelper.create_test_files(self.test_dir, file_count)

        configs = [
            ("general", self.executor_manager.get_general_executor()),
            ("file_scan", self.executor_manager.get_file_scan_executor()),
        ]

        results = {}

        for config_name, executor in configs:
            start_time = time.time()

            with executor as exec:
                futures = [
                    exec.submit(PerformanceTestHelper.mock_file_processing_task, file_path)
                    for file_path in test_files
                ]

                # Wait for all to complete
                for future in as_completed(futures):
                    future.result()

            execution_time = time.time() - start_time
            results[config_name] = execution_time

            print(f"{config_name} executor time: {execution_time:.3f}s")

        # Both configurations should perform reasonably well
        # File scan executor might be slightly faster for file I/O operations
        for config_name, exec_time in results.items():
            assert exec_time < 2.0, f"{config_name} executor took too long: {exec_time:.3f}s"

    def test_large_dataset_performance(self):
        """Test performance with a larger dataset (1000+ files)."""
        file_count = 1000
        test_files = PerformanceTestHelper.create_test_files(self.test_dir, file_count)

        print(f"Testing with {file_count} files...")

        start_time = time.time()

        with self.executor_manager.get_general_executor() as executor:
            futures = [
                executor.submit(PerformanceTestHelper.mock_file_processing_task, file_path)
                for file_path in test_files
            ]

            completed_count = 0
            for future in as_completed(futures):
                future.result()
                completed_count += 1

                # Progress logging every 100 files
                if completed_count % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = completed_count / elapsed
                    print(f"Processed {completed_count}/{file_count} files ({rate:.1f} files/sec)")

        total_time = time.time() - start_time
        processing_rate = file_count / total_time

        print(f"Total time: {total_time:.3f}s")
        print(f"Processing rate: {processing_rate:.1f} files/sec")

        # Verify all files were processed
        assert completed_count == file_count

        # Should process at least 50 files per second
        assert processing_rate >= 50.0, f"Processing rate too low: {processing_rate:.1f} files/sec"

    def test_executor_shutdown_performance(self):
        """Test that executor shutdown is properly handled."""
        file_count = 20
        test_files = PerformanceTestHelper.create_test_files(self.test_dir, file_count)

        # Test that executor can be used multiple times
        for iteration in range(3):
            start_time = time.time()

            with self.executor_manager.get_general_executor() as executor:
                futures = [
                    executor.submit(PerformanceTestHelper.mock_file_processing_task, file_path)
                    for file_path in test_files
                ]

                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

            execution_time = time.time() - start_time
            print(f"Iteration {iteration + 1} time: {execution_time:.3f}s")

            assert len(results) == file_count
            assert execution_time < 1.0  # Should be fast with proper shutdown

        # Test explicit shutdown
        start_time = time.time()
        self.executor_manager.shutdown_all(wait=True)
        shutdown_time = time.time() - start_time

        print(f"Shutdown time: {shutdown_time:.3f}s")
        assert shutdown_time < 1.0, "Shutdown should be fast"

        # Verify executors are properly shut down
        config_info = self.executor_manager.get_configuration_info()
        assert not config_info['general_executor_active']

    def test_error_handling_performance(self):
        """Test performance with error scenarios."""
        file_count = 50
        test_files = PerformanceTestHelper.create_test_files(self.test_dir, file_count)

        def failing_task(file_path: str):
            """Task that fails for some files."""
            if 'E05' in file_path or 'E10' in file_path:
                raise ValueError(f"Simulated error for {file_path}")
            return PerformanceTestHelper.mock_file_processing_task(file_path)

        start_time = time.time()

        with self.executor_manager.get_general_executor() as executor:
            futures = [
                executor.submit(failing_task, file_path)
                for file_path in test_files
            ]

            successful_results = []
            failed_count = 0

            for future in as_completed(futures):
                try:
                    result = future.result()
                    successful_results.append(result)
                except Exception as e:
                    failed_count += 1
                    print(f"Expected error: {e}")

        total_time = time.time() - start_time

        print(f"Error handling test time: {total_time:.3f}s")
        print(f"Successful: {len(successful_results)}, Failed: {failed_count}")

        # Should still process successfully despite errors
        assert len(successful_results) == file_count - 2  # 2 files should fail
        assert failed_count == 2
        assert total_time < 1.0  # Should not be significantly slower due to errors


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
