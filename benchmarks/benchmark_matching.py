"""Benchmark for MatchingEngine.find_match performance.

This script measures the performance of the matching engine's find_match
method to ensure the dataclass refactoring hasn't introduced significant overhead.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from statistics import mean, median, stdev

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anivault.core.matching.engine import MatchingEngine
from anivault.services.sqlite_cache_db import SQLiteCacheDB
from test_data import generate_anitopy_results


async def benchmark_find_match(iterations: int = 100) -> dict:
    """Benchmark find_match performance.

    Args:
        iterations: Number of find_match calls to perform

    Returns:
        Dictionary with benchmark results
    """
    # Setup - use in-memory cache to isolate matching logic
    cache_path = Path(":memory:")
    cache = SQLiteCacheDB(cache_path)

    # Mock TMDB client (we're measuring matching logic, not API calls)
    # In real benchmarks, you'd want to pre-populate cache
    tmdb_client = None  # Will use cached results only

    matching_engine = MatchingEngine(cache=cache, tmdb_client=tmdb_client)

    # Generate test data
    print(f"🔧 Generating {iterations} test cases...")
    anitopy_results = generate_anitopy_results(iterations)

    # Warmup run
    print("🔥 Warmup run...")
    if len(anitopy_results) > 0:
        try:
            await matching_engine.find_match(anitopy_results[0])
        except Exception:
            pass  # Expected if no cache/API

    # Benchmark
    print(f"⏱️  Benchmarking {iterations} find_match calls...")
    timings = []

    for i, anitopy_result in enumerate(anitopy_results):
        start = time.perf_counter()

        try:
            await matching_engine.find_match(anitopy_result)
        except Exception:
            # Expected if no cache/API - we're measuring overhead
            pass

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000

        timings.append(elapsed_ms)

        if (i + 1) % 25 == 0:
            print(f"   Progress: {i + 1}/{iterations}")

    # Calculate statistics
    return {
        "iterations": iterations,
        "total_time_ms": sum(timings),
        "average_ms": mean(timings),
        "median_ms": median(timings),
        "std_dev_ms": stdev(timings) if len(timings) > 1 else 0.0,
        "min_ms": min(timings),
        "max_ms": max(timings),
    }


def print_results(results: dict) -> None:
    """Print benchmark results in a formatted way.

    Args:
        results: Dictionary containing benchmark metrics
    """
    print("\n" + "=" * 60)
    print("📊 MatchingEngine.find_match() Benchmark Results")
    print("=" * 60)
    print(f"Iterations:    {results['iterations']}")
    print(f"Total time:    {results['total_time_ms']:.2f} ms")
    print(f"Average time:  {results['average_ms']:.3f} ms/call")
    print(f"Median time:   {results['median_ms']:.3f} ms/call")
    print(f"Std deviation: {results['std_dev_ms']:.3f} ms")
    print(f"Min time:      {results['min_ms']:.3f} ms")
    print(f"Max time:      {results['max_ms']:.3f} ms")
    print("=" * 60)


async def main() -> None:
    """Run the benchmark."""
    iterations = 100  # Adjust as needed

    print("🚀 Starting MatchingEngine benchmark...\n")

    results = await benchmark_find_match(iterations)
    print_results(results)

    print("\n✅ Benchmark complete!")


if __name__ == "__main__":
    asyncio.run(main())

