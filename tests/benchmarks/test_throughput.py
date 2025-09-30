"""Throughput benchmark tests for the file processing pipeline.

This module contains benchmark tests to measure and validate the
pipeline's file scanning and processing throughput.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from tests.test_helpers import create_large_test_directory, cleanup_test_directory
from anivault.core.pipeline.main import run_pipeline


# Mark all tests in this module as benchmarks
pytestmark = pytest.mark.benchmark


class TestPipelineThroughput:
    """Benchmark tests for pipeline throughput performance."""

    @pytest.fixture
    def benchmark_data_dir(self, tmp_path: Path) -> Path:
        """Create a directory for benchmark test data."""
        return tmp_path / "benchmark_data"

    def test_scan_throughput_with_1k_files(
        self,
        benchmark,
        benchmark_data_dir: Path,
    ) -> None:
        """Benchmark scanner throughput with 1,000 files (quick test).

        This is a small-scale test to verify the benchmark setup works.
        """
        # Given
        num_files = 1_000
        extensions = [".mp4", ".mkv", ".avi"]

        def setup():
            """Setup function to create test files before benchmark."""
            create_large_test_directory(
                benchmark_data_dir,
                num_files,
                extensions=extensions,
            )

        def teardown():
            """Teardown function to clean up after benchmark."""
            cleanup_test_directory(benchmark_data_dir)

        def run_scan():
            """Function to benchmark - runs the full pipeline."""
            return run_pipeline(
                root_path=str(benchmark_data_dir),
                extensions=extensions,
                num_workers=4,
                max_queue_size=1000,
            )

        # Setup test data
        setup()

        try:
            # When - Run the benchmark
            results = benchmark(run_scan)

            # Then - Verify throughput
            files_scanned = len(results)
            assert files_scanned == num_files

            # Calculate throughput in paths/minute
            elapsed_seconds = benchmark.stats["mean"]
            throughput_per_min = (files_scanned / elapsed_seconds) * 60

            # Log the results
            print(f"\n{'='*60}")
            print(f"Throughput Benchmark Results (1k files):")
            print(f"  Files scanned: {files_scanned:,}")
            print(f"  Mean time: {elapsed_seconds:.3f}s")
            print(f"  Throughput: {throughput_per_min:,.0f} paths/min")
            print(f"{'='*60}\n")

        finally:
            teardown()

    def test_scan_throughput_with_10k_files(
        self,
        benchmark,
        benchmark_data_dir: Path,
    ) -> None:
        """Benchmark scanner throughput with 10,000 files (warm-up test).

        This is a smaller-scale test to verify the benchmark setup works
        and to get initial performance estimates.
        """
        # Given
        num_files = 10_000
        extensions = [".mp4", ".mkv", ".avi"]

        def setup():
            """Setup function to create test files before benchmark."""
            create_large_test_directory(
                benchmark_data_dir,
                num_files,
                extensions=extensions,
            )

        def teardown():
            """Teardown function to clean up after benchmark."""
            cleanup_test_directory(benchmark_data_dir)

        def run_scan():
            """Function to benchmark - runs the full pipeline."""
            return run_pipeline(
                root_path=str(benchmark_data_dir),
                extensions=extensions,
                num_workers=4,
                max_queue_size=1000,
            )

        # Setup test data
        setup()

        try:
            # When - Run the benchmark
            results = benchmark(run_scan)

            # Then - Verify throughput
            files_scanned = len(results)
            assert files_scanned == num_files

            # Calculate throughput in paths/minute
            elapsed_seconds = benchmark.stats["mean"]
            throughput_per_min = (files_scanned / elapsed_seconds) * 60

            # Log the results
            print(f"\n{'='*60}")
            print(f"Throughput Benchmark Results (10k files):")
            print(f"  Files scanned: {files_scanned:,}")
            print(f"  Mean time: {elapsed_seconds:.3f}s")
            print(f"  Throughput: {throughput_per_min:,.0f} paths/min")
            print(f"{'='*60}\n")

            # For 10k files, we expect reasonable performance
            # (not asserting a specific threshold for warm-up test)

        finally:
            teardown()

    def test_scan_throughput_with_120k_files(
        self,
        benchmark,
        benchmark_data_dir: Path,
    ) -> None:
        """Benchmark scanner throughput with 120,000 files (target test).

        This test validates that the pipeline meets the PRD requirement
        of processing at least 120,000 paths per minute.
        """
        # Given
        num_files = 120_000
        extensions = [".mp4", ".mkv", ".avi"]
        target_throughput = 120_000  # paths/min

        def setup():
            """Setup function to create test files before benchmark."""
            print(f"\nCreating {num_files:,} test files...")
            create_large_test_directory(
                benchmark_data_dir,
                num_files,
                extensions=extensions,
            )
            print("Test files created.")

        def teardown():
            """Teardown function to clean up after benchmark."""
            print("\nCleaning up test files...")
            cleanup_test_directory(benchmark_data_dir)
            print("Cleanup complete.")

        def run_scan():
            """Function to benchmark - runs the full pipeline."""
            return run_pipeline(
                root_path=str(benchmark_data_dir),
                extensions=extensions,
                num_workers=4,
                max_queue_size=1000,
            )

        # Setup test data
        setup()

        try:
            # When - Run the benchmark
            results = benchmark(run_scan)

            # Then - Verify throughput
            files_scanned = len(results)
            assert files_scanned == num_files

            # Calculate throughput in paths/minute
            elapsed_seconds = benchmark.stats["mean"]
            throughput_per_min = (files_scanned / elapsed_seconds) * 60

            # Log detailed results
            print(f"\n{'='*60}")
            print(f"THROUGHPUT BENCHMARK RESULTS (120k files):")
            print(f"{'='*60}")
            print(f"  Files scanned:      {files_scanned:,}")
            print(f"  Mean time:          {elapsed_seconds:.3f}s")
            print(f"  Min time:           {benchmark.stats['min']:.3f}s")
            print(f"  Max time:           {benchmark.stats['max']:.3f}s")
            print(f"  Std dev:            {benchmark.stats['stddev']:.3f}s")
            print(f"  Throughput:         {throughput_per_min:,.0f} paths/min")
            print(f"  Target:             {target_throughput:,} paths/min")
            print(
                f"  Status:             {'✅ PASS' if throughput_per_min >= target_throughput else '❌ FAIL'}"
            )
            print(f"{'='*60}\n")

            # Assert that throughput meets the target
            assert (
                throughput_per_min >= target_throughput
            ), f"Throughput {throughput_per_min:,.0f} paths/min is below target {target_throughput:,} paths/min"

        finally:
            teardown()

    def test_scan_throughput_with_varying_workers(
        self,
        benchmark,
        benchmark_data_dir: Path,
    ) -> None:
        """Benchmark scanner throughput with different worker counts.

        This test helps identify the optimal number of workers for
        maximum throughput.
        """
        # Given
        num_files = 50_000  # Smaller dataset for faster testing
        extensions = [".mp4", ".mkv", ".avi"]
        worker_counts = [2, 4, 8]

        def setup():
            """Setup function to create test files before benchmark."""
            create_large_test_directory(
                benchmark_data_dir,
                num_files,
                extensions=extensions,
            )

        def teardown():
            """Teardown function to clean up after benchmark."""
            cleanup_test_directory(benchmark_data_dir)

        # Setup test data once
        setup()

        try:
            results_by_workers = {}

            for num_workers in worker_counts:

                def run_scan():
                    """Function to benchmark with specific worker count."""
                    return run_pipeline(
                        root_path=str(benchmark_data_dir),
                        extensions=extensions,
                        num_workers=num_workers,
                        max_queue_size=1000,
                    )

                # Run benchmark for this worker count
                results = benchmark.pedantic(
                    run_scan,
                    rounds=3,
                    iterations=1,
                )

                # Calculate throughput
                elapsed_seconds = benchmark.stats["mean"]
                throughput_per_min = (num_files / elapsed_seconds) * 60
                results_by_workers[num_workers] = throughput_per_min

            # Display comparison
            print(f"\n{'='*60}")
            print("Worker Count Comparison (50k files):")
            print(f"{'='*60}")
            for workers, throughput in results_by_workers.items():
                print(f"  {workers} workers: {throughput:,.0f} paths/min")
            print(f"{'='*60}\n")

            # Verify all worker counts produce reasonable results
            assert all(t > 0 for t in results_by_workers.values())

        finally:
            teardown()
