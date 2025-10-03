"""Simple memory profiling script using psutil for real-time monitoring.

This script monitors memory usage during pipeline execution.

Usage:
    python scripts/profile_memory.py [num_files]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

import psutil
from anivault.core.pipeline.main import run_pipeline

from tests.test_helpers import cleanup_test_directory, create_large_test_directory


def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


# Memory target constant (MB)
MEMORY_TARGET_MB = 500


def profile_pipeline_memory(num_files: int = 50_000) -> dict:
    """Profile pipeline memory usage.

    Args:
        num_files: Number of test files to process.

    Returns:
        Dictionary containing profiling results.
    """
    print(f"\n{'='*60}")
    print("PIPELINE MEMORY PROFILING")
    print(f"{'='*60}")
    print("Target: < 500MB memory usage")
    print(f"Files to process: {num_files:,}")
    print(f"{'='*60}\n")

    # Get initial memory
    initial_memory = get_memory_usage_mb()
    print(f"Initial memory: {initial_memory:.2f} MB")

    # Create test directory
    test_dir = Path("test_memory_profile_data")
    peak_memory = initial_memory
    results = None

    try:
        # Create test files
        print(f"\nCreating {num_files:,} test files...")
        create_large_test_directory(test_dir, num_files)
        after_creation_memory = get_memory_usage_mb()
        peak_memory = max(peak_memory, after_creation_memory)
        print("✅ Test files created")
        print(f"Memory after file creation: {after_creation_memory:.2f} MB\n")

        # Run pipeline with memory monitoring
        print("Starting pipeline...")
        start_time = time.time()

        results = run_pipeline(
            root_path=str(test_dir),
            extensions=[".mp4", ".mkv", ".avi"],
            num_workers=4,
            max_queue_size=1000,
        )

        elapsed = time.time() - start_time

        # Get peak memory after pipeline
        after_pipeline_memory = get_memory_usage_mb()
        peak_memory = max(peak_memory, after_pipeline_memory)

        print(f"\n✅ Pipeline completed in {elapsed:.2f}s")
        print(f"Files processed: {len(results):,}")
        print(f"Memory after pipeline: {after_pipeline_memory:.2f} MB")

    finally:
        # Cleanup
        print("\nCleaning up test files...")
        cleanup_test_directory(test_dir)
        after_cleanup_memory = get_memory_usage_mb()
        print("✅ Cleanup complete")
        print(f"Memory after cleanup: {after_cleanup_memory:.2f} MB")

    # Print summary
    print(f"\n{'='*60}")
    print("MEMORY PROFILING RESULTS")
    print(f"{'='*60}")
    print(f"Initial memory:        {initial_memory:.2f} MB")
    print(f"Peak memory:           {peak_memory:.2f} MB")
    print(f"Memory increase:       {peak_memory - initial_memory:.2f} MB")
    print(f"Final memory:          {after_cleanup_memory:.2f} MB")
    print(f"Target limit:          {MEMORY_TARGET_MB:.2f} MB")
    print(
        f"Status:                {'✅ PASS' if peak_memory < MEMORY_TARGET_MB else '❌ FAIL'}",
    )
    print(f"{'='*60}\n")

    return {
        "initial_memory_mb": initial_memory,
        "peak_memory_mb": peak_memory,
        "final_memory_mb": after_cleanup_memory,
        "memory_increase_mb": peak_memory - initial_memory,
        "target_mb": MEMORY_TARGET_MB,
        "passed": peak_memory < MEMORY_TARGET_MB,
        "files_processed": len(results) if results else 0,
    }


if __name__ == "__main__":
    # Determine number of files from command line or use default
    num_files = 50_000
    if len(sys.argv) > 1:
        try:
            num_files = int(sys.argv[1])
        except ValueError:
            print(f"Invalid number: {sys.argv[1]}, using default: {num_files:,}")

    result = profile_pipeline_memory(num_files)

    # Exit with error code if failed
    if not result["passed"]:
        print(f"❌ Memory usage {result['peak_memory_mb']:.2f} MB exceeds target!")
        sys.exit(1)
    else:
        print(f"✅ Memory usage {result['peak_memory_mb']:.2f} MB is within target!")
        sys.exit(0)
