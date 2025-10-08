"""Benchmark for SQLiteCacheDB serialization/deserialization performance.

This script measures the performance of cache set/get operations to ensure
Pydantic model validation hasn't introduced significant overhead.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from statistics import mean, median, stdev

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anivault.services.sqlite_cache_db import SQLiteCacheDB
from test_data import generate_cache_test_data


def benchmark_cache_operations(iterations: int = 1000) -> dict:
    """Benchmark cache set/get performance.

    Args:
        iterations: Number of cache operations to perform

    Returns:
        Dictionary with benchmark results for both set and get operations
    """
    # Setup - use in-memory DB for speed
    cache_path = Path(":memory:")
    cache = SQLiteCacheDB(cache_path)

    # Generate test data
    print(f"🔧 Generating {iterations} cache entries...")
    cache_data = generate_cache_test_data(iterations)

    # Benchmark SET operations
    print(f"⏱️  Benchmarking {iterations} cache.set() calls...")
    set_timings = []

    for i, entry in enumerate(cache_data):
        start = time.perf_counter()

        try:
            cache.set_cache(
                key=entry["key"],
                data=entry["data"],
                cache_type=entry["cache_type"],
                ttl_seconds=entry["ttl_seconds"],
            )
        except Exception as e:
            print(f"⚠️  Error at iteration {i}: {e}")
            continue

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        set_timings.append(elapsed_ms)

        if (i + 1) % 250 == 0:
            print(f"   Progress: {i + 1}/{iterations}")

    # Benchmark GET operations
    print(f"⏱️  Benchmarking {iterations} cache.get() calls...")
    get_timings = []

    for i, entry in enumerate(cache_data):
        start = time.perf_counter()

        try:
            cache.get(entry["key"])
        except Exception as e:
            print(f"⚠️  Error at iteration {i}: {e}")
            continue

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        get_timings.append(elapsed_ms)

        if (i + 1) % 250 == 0:
            print(f"   Progress: {i + 1}/{iterations}")

    # Calculate statistics
    return {
        "iterations": iterations,
        "set": {
            "total_time_ms": sum(set_timings),
            "average_ms": mean(set_timings),
            "median_ms": median(set_timings),
            "std_dev_ms": stdev(set_timings) if len(set_timings) > 1 else 0.0,
            "min_ms": min(set_timings),
            "max_ms": max(set_timings),
        },
        "get": {
            "total_time_ms": sum(get_timings),
            "average_ms": mean(get_timings),
            "median_ms": median(get_timings),
            "std_dev_ms": stdev(get_timings) if len(get_timings) > 1 else 0.0,
            "min_ms": min(get_timings),
            "max_ms": max(get_timings),
        },
    }


def print_results(results: dict) -> None:
    """Print benchmark results in a formatted way.

    Args:
        results: Dictionary containing benchmark metrics
    """
    print("\n" + "=" * 60)
    print("📊 SQLiteCacheDB Benchmark Results")
    print("=" * 60)
    print(f"Iterations: {results['iterations']}\n")

    print("🔹 SET Operations (Serialization + Write):")
    print(f"   Total time:    {results['set']['total_time_ms']:.2f} ms")
    print(f"   Average time:  {results['set']['average_ms']:.3f} ms/call")
    print(f"   Median time:   {results['set']['median_ms']:.3f} ms/call")
    print(f"   Std deviation: {results['set']['std_dev_ms']:.3f} ms")
    print(f"   Min time:      {results['set']['min_ms']:.3f} ms")
    print(f"   Max time:      {results['set']['max_ms']:.3f} ms\n")

    print("🔹 GET Operations (Read + Deserialization):")
    print(f"   Total time:    {results['get']['total_time_ms']:.2f} ms")
    print(f"   Average time:  {results['get']['average_ms']:.3f} ms/call")
    print(f"   Median time:   {results['get']['median_ms']:.3f} ms/call")
    print(f"   Std deviation: {results['get']['std_dev_ms']:.3f} ms")
    print(f"   Min time:      {results['get']['min_ms']:.3f} ms")
    print(f"   Max time:      {results['get']['max_ms']:.3f} ms")
    print("=" * 60)


def main() -> None:
    """Run the benchmark."""
    iterations = 1000  # Adjust as needed

    print("🚀 Starting SQLiteCacheDB benchmark...\n")

    results = benchmark_cache_operations(iterations)
    print_results(results)

    print("\n✅ Benchmark complete!")


if __name__ == "__main__":
    main()

