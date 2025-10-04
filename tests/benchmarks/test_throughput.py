"""Throughput benchmark tests for the file processing pipeline.

This module contains benchmark tests to measure and validate the
pipeline's file scanning and processing throughput.
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest

from anivault.core.pipeline.main import run_pipeline
from tests.test_helpers import cleanup_test_directory, create_large_test_directory

# Mark all tests in this module as benchmarks
pytestmark = pytest.mark.benchmark


class TestPipelineThroughput:
    """Benchmark tests for pipeline throughput performance."""

    @pytest.fixture
    def benchmark_data_dir(self, tmp_path: Path) -> Generator[Path, None, None]:
        """Create a directory for benchmark test data."""
        data_dir = tmp_path / "benchmark_data"
        data_dir.mkdir()
        yield data_dir
        # Cleanup is handled by tmp_path fixture

    @pytest.fixture
    def small_test_data(self, benchmark_data_dir: Path) -> list[Path]:
        """Create small test dataset for quick benchmarks."""
        return create_large_test_directory(
            benchmark_data_dir,
            num_files=100,
            extensions=[".mp4", ".mkv", ".avi"],
            create_subdirs=False,
        )

    @pytest.fixture
    def medium_test_data(self, benchmark_data_dir: Path) -> list[Path]:
        """Create medium test dataset for moderate benchmarks."""
        return create_large_test_directory(
            benchmark_data_dir,
            num_files=1_000,
            extensions=[".mp4", ".mkv", ".avi"],
            create_subdirs=True,
            subdir_count=5,
        )

    @pytest.fixture
    def large_test_data(self, benchmark_data_dir: Path) -> list[Path]:
        """Create large test dataset for comprehensive benchmarks."""
        return create_large_test_directory(
            benchmark_data_dir,
            num_files=10_000,
            extensions=[".mp4", ".mkv", ".avi", ".mov", ".wmv"],
            create_subdirs=True,
            subdir_count=10,
        )

    def test_scan_throughput_small_dataset(
        self,
        benchmark,
        small_test_data: list[Path],
        benchmark_data_dir: Path,
    ) -> None:
        """Benchmark scanner throughput with 100 files (quick test).

        This is a small-scale test to verify the benchmark setup works.
        """
        # Given
        extensions = [".mp4", ".mkv", ".avi"]

        def run_scan():
            """Function to benchmark - runs the full pipeline."""
            return run_pipeline(
                root_path=str(benchmark_data_dir),
                extensions=extensions,
                num_workers=2,
                max_queue_size=100,
            )

        # When - Run the benchmark
        results = benchmark(run_scan)

        # Then - Verify results
        assert results is not None
        assert len(small_test_data) == 100

    def test_scan_throughput_medium_dataset(
        self,
        benchmark,
        medium_test_data: list[Path],
        benchmark_data_dir: Path,
    ) -> None:
        """Benchmark scanner throughput with 1,000 files.

        This test measures performance with a moderate dataset.
        """
        # Given
        extensions = [".mp4", ".mkv", ".avi"]

        def run_scan():
            """Function to benchmark - runs the full pipeline."""
            return run_pipeline(
                root_path=str(benchmark_data_dir),
                extensions=extensions,
                num_workers=4,
                max_queue_size=1000,
            )

        # When - Run the benchmark
        results = benchmark(run_scan)

        # Then - Verify results
        assert results is not None
        assert len(medium_test_data) == 1_000

    @pytest.mark.slow
    def test_scan_throughput_large_dataset(
        self,
        benchmark,
        large_test_data: list[Path],
        benchmark_data_dir: Path,
    ) -> None:
        """Benchmark scanner throughput with 10,000 files.

        This is a comprehensive test that may take several minutes.
        """
        # Given
        extensions = [".mp4", ".mkv", ".avi", ".mov", ".wmv"]

        def run_scan():
            """Function to benchmark - runs the full pipeline."""
            return run_pipeline(
                root_path=str(benchmark_data_dir),
                extensions=extensions,
                num_workers=8,
                max_queue_size=5000,
            )

        # When - Run the benchmark
        results = benchmark(run_scan)

        # Then - Verify results
        assert results is not None
        assert len(large_test_data) == 10_000

    def test_scan_throughput_with_different_workers(
        self,
        small_test_data: list[Path],
        benchmark_data_dir: Path,
    ) -> None:
        """Benchmark scanner throughput with different worker counts."""
        # Given
        extensions = [".mp4", ".mkv", ".avi"]
        worker_counts = [1, 2, 4, 8]

        for num_workers in worker_counts:
            # When - Run the pipeline directly (no benchmark fixture)
            results = run_pipeline(
                root_path=str(benchmark_data_dir),
                extensions=extensions,
                num_workers=num_workers,
                max_queue_size=100,
            )

            # Then - Verify results
            assert results is not None

    def test_scan_throughput_with_different_extensions(
        self,
        benchmark,
        small_test_data: list[Path],
        benchmark_data_dir: Path,
    ) -> None:
        """Benchmark scanner throughput with different file extensions."""
        # Given
        extensions = [".mp4", ".mkv", ".avi", ".mov", ".wmv"]

        def run_scan():
            """Function to benchmark with multiple extensions."""
            return run_pipeline(
                root_path=str(benchmark_data_dir),
                extensions=extensions,
                num_workers=4,
                max_queue_size=100,
            )

        # When - Run the benchmark
        results = benchmark(run_scan)

        # Then - Verify results
        assert results is not None

    def test_memory_usage_during_scan(
        self,
        benchmark,
        medium_test_data: list[Path],
        benchmark_data_dir: Path,
    ) -> None:
        """Benchmark memory usage during file scanning."""
        import os

        import psutil

        # Given
        extensions = [".mp4", ".mkv", ".avi"]
        process = psutil.Process(os.getpid())

        def run_scan_with_memory_tracking():
            """Function to benchmark with memory tracking."""
            memory_before = process.memory_info().rss

            results = run_pipeline(
                root_path=str(benchmark_data_dir),
                extensions=extensions,
                num_workers=4,
                max_queue_size=1000,
            )

            memory_after = process.memory_info().rss
            memory_used = memory_after - memory_before

            return results, memory_used

        # When - Run the benchmark
        results, memory_used = benchmark(run_scan_with_memory_tracking)

        # Then - Verify results and memory usage
        assert results is not None
        assert memory_used > 0
        # Memory usage should be reasonable (less than 1GB for 1000 files)
        assert memory_used < 1024 * 1024 * 1024
