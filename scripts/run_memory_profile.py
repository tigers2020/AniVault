"""Memory profiling script for AniVault pipeline.

This script profiles the pipeline's memory usage during large-scale
file processing to ensure it stays within the 500MB limit.

Usage:
    python -m memory_profiler scripts/run_memory_profile.py

Or with mprof:
    mprof run scripts/run_memory_profile.py
    mprof plot
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import modules after path setup
from anivault.core.pipeline.main import run_pipeline  # noqa: E402

from tests.test_helpers import (  # noqa: E402
    cleanup_test_directory,
    create_large_test_directory,
)


# Note: @profile decorator is added by memory_profiler when running with:
# python -m memory_profiler scripts/run_memory_profile.py
def run_pipeline_with_profiling(num_files: int = 50_000) -> None:
    """Run the pipeline with memory profiling enabled.

    Args:
        num_files: Number of test files to process.
    """
    print(f"\n{'='*60}")
    print("MEMORY PROFILING TEST")
    print(f"{'='*60}")
    print("Target: < 500MB memory usage")
    print(f"Files to process: {num_files:,}")
    print(f"{'='*60}\n")

    # Create test directory
    test_dir = Path("test_memory_profile_data")

    try:
        # Create test files
        print(f"Creating {num_files:,} test files...")
        create_large_test_directory(test_dir, num_files)
        print("✅ Test files created\n")

        # Run pipeline
        print("Starting pipeline with memory profiling...")
        results = run_pipeline(
            root_path=str(test_dir),
            extensions=[".mp4", ".mkv", ".avi"],
            num_workers=4,
            max_queue_size=1000,
        )

        print("\n✅ Pipeline completed")
        print(f"Files processed: {len(results):,}")

    finally:
        # Cleanup
        print("\nCleaning up test files...")
        cleanup_test_directory(test_dir)
        print("✅ Cleanup complete\n")


if __name__ == "__main__":
    # Determine number of files from command line or use default
    num_files = 50_000
    if len(sys.argv) > 1:
        try:
            num_files = int(sys.argv[1])
        except ValueError:
            print(f"Invalid number: {sys.argv[1]}, using default: {num_files:,}")

    run_pipeline_with_profiling(num_files)
