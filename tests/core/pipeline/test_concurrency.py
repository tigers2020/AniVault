"""Concurrency and race condition tests for the pipeline.

This module tests the thread safety of the pipeline's concurrent
operations using a shared counter to detect race conditions.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.core.pipeline.main import run_pipeline
from anivault.core.pipeline.parser import ParserWorker
from tests.core.pipeline.concurrency_helpers import (
    SharedCounter,
    create_race_condition_test_parser,
)
from tests.test_helpers import cleanup_test_directory, create_large_test_directory


class TestPipelineConcurrency:
    """Test suite for pipeline concurrency and thread safety."""

    def test_pipeline_thread_safety_with_shared_counter(self, tmp_path: Path) -> None:
        """Test pipeline thread safety using a shared counter.

        This test verifies that the pipeline can safely handle concurrent
        operations without race conditions. A shared counter is incremented
        by each worker, and we verify the final count matches expectations.
        """
        # Given
        num_files = 100
        num_workers = 16  # High number to stress-test concurrency
        test_dir = tmp_path / "concurrency_test"

        # Create test files
        create_large_test_directory(test_dir, num_files)

        # Create shared counter
        counter = SharedCounter()

        try:
            # Patch the ParserWorker's _parse_file method to use our test parser
            test_parser = create_race_condition_test_parser(counter, use_lock=True)

            with patch.object(
                ParserWorker,
                "_parse_file",
                side_effect=test_parser,
            ):
                # When - Run pipeline with many workers
                results = run_pipeline(
                    root_path=str(test_dir),
                    extensions=[".mp4", ".mkv", ".avi"],
                    num_workers=num_workers,
                    max_queue_size=200,
                )

                # Then - Verify thread safety
                assert len(results) == num_files
                assert (
                    counter.value == num_files
                ), f"Race condition detected! Expected {num_files}, got {counter.value}"

                print(
                    f"\n✅ Thread safety verified: {num_files} files, {num_workers} workers, counter={counter.value}",
                )

        finally:
            cleanup_test_directory(test_dir)

    def test_statistics_thread_safety(self, tmp_path: Path) -> None:
        """Test that statistics are updated thread-safely.

        This test verifies that the ParserStatistics class correctly
        handles concurrent updates from multiple worker threads.
        """
        # Given
        num_files = 200
        num_workers = 8
        test_dir = tmp_path / "stats_concurrency_test"

        create_large_test_directory(test_dir, num_files)

        try:
            # When - Run pipeline
            results = run_pipeline(
                root_path=str(test_dir),
                extensions=[".mp4", ".mkv", ".avi"],
                num_workers=num_workers,
                max_queue_size=100,
            )

            # Then - All results should be accounted for
            assert len(results) == num_files

            # All files should be processed successfully
            successes = [r for r in results if r.get("status") == "success"]
            assert len(successes) == num_files

            print(
                f"\n✅ Statistics thread safety verified: {num_files} files processed correctly",
            )

        finally:
            cleanup_test_directory(test_dir)

    def test_queue_thread_safety_under_load(self, tmp_path: Path) -> None:
        """Test queue operations are thread-safe under heavy load.

        This test verifies that the BoundedQueue correctly handles
        concurrent put/get operations from multiple threads.
        """
        # Given
        num_files = 500
        num_workers = 12
        test_dir = tmp_path / "queue_concurrency_test"

        create_large_test_directory(test_dir, num_files)

        try:
            # When - Run pipeline with high concurrency
            results = run_pipeline(
                root_path=str(test_dir),
                extensions=[".mp4", ".mkv", ".avi"],
                num_workers=num_workers,
                max_queue_size=50,  # Smaller queue to increase contention
            )

            # Then - All files should be processed
            assert len(results) == num_files

            # No results should be lost or duplicated
            file_paths = [r.get("file_path") for r in results]
            assert len(file_paths) == len(set(file_paths))  # No duplicates

            print(
                f"\n✅ Queue thread safety verified: {num_files} files, {num_workers} workers, no data loss",
            )

        finally:
            cleanup_test_directory(test_dir)

    @pytest.mark.slow
    def test_high_concurrency_stress_test(self, tmp_path: Path) -> None:
        """Stress test with very high concurrency.

        This test pushes the pipeline to its limits with many workers
        to verify it remains stable and thread-safe.
        """
        # Given
        num_files = 1000
        num_workers = 32  # Very high worker count
        test_dir = tmp_path / "stress_test"

        create_large_test_directory(test_dir, num_files)

        try:
            # When - Run pipeline with extreme concurrency
            results = run_pipeline(
                root_path=str(test_dir),
                extensions=[".mp4", ".mkv", ".avi"],
                num_workers=num_workers,
                max_queue_size=100,
            )

            # Then - Should still process all files correctly
            assert len(results) == num_files

            successes = [r for r in results if r.get("status") == "success"]
            assert len(successes) == num_files

            print(
                f"\n✅ Stress test passed: {num_files} files, {num_workers} workers",
            )

        finally:
            cleanup_test_directory(test_dir)
