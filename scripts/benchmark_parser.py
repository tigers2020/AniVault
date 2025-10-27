"""Benchmark script for anime filename parser performance.

This script measures the parsing speed and memory usage of the
AnimeFilenameParser to ensure it meets performance requirements.

Usage:
    python scripts/benchmark_parser.py

Memory profiling:
    mprof run scripts/benchmark_parser.py
    mprof plot
"""

from __future__ import annotations

import time
from pathlib import Path

from anivault.core.parser.anime_parser import AnimeFilenameParser


def load_test_filenames(filepath: str, max_count: int = 10000) -> list[str]:
    """Load test filenames from file.

    Args:
        filepath: Path to filenames file.
        max_count: Maximum number of filenames to load.

    Returns:
        List of filenames.
    """
    filenames = []
    video_exts = {".avi", ".mp4", ".mkv", ".wmv", ".flv", ".webm", ".mov"}

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and any(line.lower().endswith(ext) for ext in video_exts):
                filenames.append(line)
                if len(filenames) >= max_count:
                    break

    return filenames


def benchmark_parsing_speed(filenames: list[str]) -> dict[str, float]:
    """Benchmark parsing speed.

    Args:
        filenames: List of filenames to parse.

    Returns:
        Dictionary with benchmark results.
    """
    parser = AnimeFilenameParser()

    print(f"🔬 Benchmarking parser with {len(filenames)} filenames...\n")

    # Warm-up (parse a few times to eliminate cold-start effects)
    for filename in filenames[:100]:
        parser.parse(filename)

    # Actual benchmark
    start_time = time.perf_counter()

    for filename in filenames:
        parser.parse(filename)

    end_time = time.perf_counter()

    # Calculate metrics
    duration = end_time - start_time
    filenames_per_second = len(filenames) / duration if duration > 0 else 0
    ms_per_filename = (duration * 1000) / len(filenames) if len(filenames) > 0 else 0

    return {
        "total_filenames": len(filenames),
        "duration_seconds": duration,
        "filenames_per_second": filenames_per_second,
        "ms_per_filename": ms_per_filename,
    }


def main():
    """Main benchmark function."""
    print("=" * 70)
    print("  AniVault Parser Performance Benchmark")
    print("=" * 70)
    print()

    # Try to load from filenames.txt
    filenames_path = Path("filenames.txt")

    if not filenames_path.exists():
        print("⚠️  filenames.txt not found, using test dataset...")
        # Fallback to test dataset
        import json

        fixture_path = Path("tests/fixtures/real_world_filenames.json")
        with open(fixture_path, encoding="utf-8") as f:
            data = json.load(f)

        filenames = [case["filename"] for case in data]
        # Duplicate to reach 10k
        filenames = filenames * (10000 // len(filenames) + 1)
        filenames = filenames[:10000]
    else:
        print(f"📁 Loading filenames from: {filenames_path}")
        filenames = load_test_filenames(str(filenames_path), max_count=10000)
        print(f"✅ Loaded {len(filenames)} filenames\n")

    # Run benchmark
    results = benchmark_parsing_speed(filenames)

    # Print results
    print("\n" + "=" * 70)
    print("  📊 Benchmark Results")
    print("=" * 70)
    print(f"  Total filenames:       {results['total_filenames']:,}")
    print(f"  Duration:              {results['duration_seconds']:.3f} seconds")
    print(f"  Throughput:            {results['filenames_per_second']:.2f} files/sec")
    print(f"  Avg time per file:     {results['ms_per_filename']:.3f} ms")
    print("=" * 70)

    # Check against targets
    print("\n🎯 Performance Targets:")
    target_fps = 1000  # Target: 1000 filenames/sec

    if results["filenames_per_second"] >= target_fps:
        print(
            f"  ✅ PASS: {results['filenames_per_second']:.0f} files/sec >= {target_fps} files/sec",
        )
    else:
        print(
            f"  ⚠️  WARN: {results['filenames_per_second']:.0f} files/sec < {target_fps} files/sec",
        )

    print("\n💡 Memory profiling:")
    print("  Run: mprof run scripts/benchmark_parser.py")
    print("  Plot: mprof plot")
    print()


if __name__ == "__main__":
    main()
