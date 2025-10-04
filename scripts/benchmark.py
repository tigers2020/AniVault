#!/usr/bin/env python3
"""Benchmark script for AniVault directory scanning performance.

This script measures the performance of the DirectoryScanner class
and provides detailed metrics for optimization analysis.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil
from memory_profiler import profile

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import AniVault modules after path setup
from anivault.config import FilterConfig  # noqa: E402
from anivault.core.filter import FilterEngine  # noqa: E402
from anivault.core.pipeline.parallel_scanner import (  # noqa: E402
    ParallelDirectoryScanner,
)
from anivault.core.pipeline.scanner import DirectoryScanner  # noqa: E402
from anivault.core.pipeline.utils import BoundedQueue, ScanStatistics  # noqa: E402


def get_memory_usage() -> float:
    """Get current memory usage in MB.

    Returns:
        Memory usage in megabytes.
    """
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def calculate_advanced_metrics(metrics: dict) -> dict:
    """Calculate advanced performance metrics.

    Args:
        metrics: Basic metrics dictionary.

    Returns:
        Enhanced metrics dictionary with additional calculations.
    """
    enhanced_metrics = metrics.copy()

    # Add efficiency metrics
    if metrics["files_found"] > 0:
        enhanced_metrics["memory_per_file_kb"] = (
            metrics["memory_increase_mb"] * 1024
        ) / metrics["files_found"]
        enhanced_metrics["time_per_file_ms"] = (
            metrics["scan_duration"] * 1000
        ) / metrics["files_found"]

    # Add throughput efficiency
    total_paths = metrics["files_found"] + metrics["directories_scanned"]
    if total_paths > 0:
        enhanced_metrics["memory_per_path_kb"] = (
            metrics["memory_increase_mb"] * 1024
        ) / total_paths
        enhanced_metrics["time_per_path_ms"] = (
            metrics["scan_duration"] * 1000
        ) / total_paths

    # Add performance rating
    paths_per_minute = metrics["paths_per_minute"]
    if paths_per_minute >= 150000:
        enhanced_metrics["performance_rating"] = "excellent"
    elif paths_per_minute >= 100000:
        enhanced_metrics["performance_rating"] = "good"
    elif paths_per_minute >= 50000:
        enhanced_metrics["performance_rating"] = "fair"
    else:
        enhanced_metrics["performance_rating"] = "poor"

    # Add memory efficiency rating
    memory_per_file_kb = enhanced_metrics.get("memory_per_file_kb", 0)
    if memory_per_file_kb <= 1:
        enhanced_metrics["memory_rating"] = "excellent"
    elif memory_per_file_kb <= 5:
        enhanced_metrics["memory_rating"] = "good"
    elif memory_per_file_kb <= 10:
        enhanced_metrics["memory_rating"] = "fair"
    else:
        enhanced_metrics["memory_rating"] = "poor"

    return enhanced_metrics


def create_benchmark_report(metrics: dict, found_files: list[Path], args) -> dict:
    """Create a comprehensive benchmark report.

    Args:
        metrics: Performance metrics.
        found_files: List of found files.
        args: Command line arguments.

    Returns:
        Complete benchmark report dictionary.
    """
    enhanced_metrics = calculate_advanced_metrics(metrics)

    report = {
        "benchmark_info": {
            "timestamp": datetime.now().isoformat(),
            "script_version": "1.0.0",
            "command_line": " ".join(sys.argv),
            "python_version": sys.version,
        },
        "scan_config": {
            "root_path": str(args.path),
            "extensions": metrics["extensions"],
            "verbose_output": args.verbose,
        },
        "performance_metrics": enhanced_metrics,
        "summary": {
            "total_files_found": metrics["files_found"],
            "total_directories_scanned": metrics["directories_scanned"],
            "scan_duration_seconds": round(metrics["scan_duration"], 3),
            "paths_per_minute": round(metrics["paths_per_minute"], 0),
            "peak_memory_mb": round(metrics["peak_memory_mb"], 2),
            "performance_rating": enhanced_metrics.get("performance_rating", "unknown"),
            "memory_rating": enhanced_metrics.get("memory_rating", "unknown"),
        },
        "file_details": [str(f) for f in found_files] if args.verbose else None,
    }

    return report


def conditional_profile(func):
    """Conditional profile decorator that only applies @profile when needed."""

    def wrapper(*args, **kwargs):
        # Check if memory profiling is enabled via command line or environment
        enable_profile = kwargs.pop("enable_memory_profile", False)
        if enable_profile:
            return profile(func)(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper


@conditional_profile
def run_parallel_scan(
    root_path: Path,
    extensions: list[str],
    max_workers: int | None = None,
    enable_memory_profile: bool = False,
) -> tuple[list[Path], dict]:
    """Run a parallel directory scan and collect performance metrics.

    Args:
        root_path: Directory to scan.
        extensions: List of file extensions to include.
        max_workers: Maximum number of worker threads.
        enable_memory_profile: Whether to enable memory profiling.

    Returns:
        Tuple of (list of found files, performance metrics).
    """
    # Initialize pipeline components
    input_queue = BoundedQueue(maxsize=10000)  # Large queue for benchmarking
    stats = ScanStatistics()

    # Create parallel scanner instance
    scanner = ParallelDirectoryScanner(
        root_path=root_path,
        extensions=extensions,
        input_queue=input_queue,
        stats=stats,
        max_workers=max_workers,
    )

    # Measure memory usage before scan
    initial_memory = get_memory_usage()

    # Measure scan time
    start_time = time.perf_counter()

    # Start the scanner thread
    scanner.start()

    # Collect results from the queue
    found_files = []
    while True:
        try:
            file_path = input_queue.get(timeout=1.0)
            if file_path is None:  # Sentinel value
                break
            found_files.append(file_path)
        except:
            break

    # Wait for scanner to complete
    scanner.join(timeout=5.0)

    end_time = time.perf_counter()
    scan_duration = end_time - start_time

    # Measure memory usage after scan
    final_memory = get_memory_usage()
    peak_memory = max(initial_memory, final_memory)

    # Calculate metrics
    metrics = {
        "scan_duration": scan_duration,
        "files_found": len(found_files),
        "directories_scanned": stats.directories_scanned,
        "files_per_second": (
            len(found_files) / scan_duration if scan_duration > 0 else 0
        ),
        "paths_per_minute": (
            (len(found_files) + stats.directories_scanned) * 60 / scan_duration
            if scan_duration > 0
            else 0
        ),
        "initial_memory_mb": initial_memory,
        "final_memory_mb": final_memory,
        "peak_memory_mb": peak_memory,
        "memory_increase_mb": final_memory - initial_memory,
        "root_path": str(root_path),
        "extensions": extensions,
        "max_workers": max_workers,
        "scanner_type": "parallel",
    }

    return found_files, metrics


@conditional_profile
def run_scan(
    root_path: Path,
    extensions: list[str],
    parallel: bool = False,
    max_workers: int | None = None,
    quiet: bool = False,
    enable_memory_profile: bool = False,
    enable_filtering: bool = False,
) -> tuple[list[Path], dict]:
    """Run a directory scan and collect performance metrics.

    Args:
        root_path: Directory to scan.
        extensions: List of file extensions to include.
        parallel: Whether to use parallel scanning.
        max_workers: Maximum number of worker threads for parallel scanning.
        quiet: Whether to suppress adaptive threshold messages.
        enable_memory_profile: Whether to enable memory profiling.
        enable_filtering: Whether to enable smart filtering engine.

    Returns:
        Tuple of (list of found files, performance metrics).
    """
    # Initialize pipeline components
    input_queue = BoundedQueue(maxsize=10000)  # Large queue for benchmarking
    stats = ScanStatistics()

    # Create FilterEngine if filtering is enabled
    filter_engine = None
    if enable_filtering:
        filter_config = FilterConfig()
        filter_engine = FilterEngine(filter_config)

    # Create scanner instance
    scanner = DirectoryScanner(
        root_path=root_path,
        extensions=extensions,
        input_queue=input_queue,
        stats=stats,
        parallel=parallel,
        max_workers=max_workers,
        quiet=quiet,
        filter_engine=filter_engine,
    )

    # Measure memory usage before scan
    initial_memory = get_memory_usage()

    # Measure scan time
    start_time = time.perf_counter()

    # Start the scanner thread
    scanner.start()

    # Collect results from the queue
    found_files = []
    while True:
        try:
            file_path = input_queue.get(timeout=1.0)
            if file_path is None:  # Sentinel value
                break
            found_files.append(file_path)
        except:
            break

    # Wait for scanner to complete
    scanner.join(timeout=5.0)

    end_time = time.perf_counter()
    scan_duration = end_time - start_time

    # Measure memory usage after scan
    final_memory = get_memory_usage()
    peak_memory = max(initial_memory, final_memory)

    # Calculate metrics
    metrics = {
        "scan_duration": scan_duration,
        "files_found": len(found_files),
        "directories_scanned": stats.directories_scanned,
        "files_per_second": (
            len(found_files) / scan_duration if scan_duration > 0 else 0
        ),
        "paths_per_minute": (
            (len(found_files) + stats.directories_scanned) * 60 / scan_duration
            if scan_duration > 0
            else 0
        ),
        "initial_memory_mb": initial_memory,
        "final_memory_mb": final_memory,
        "peak_memory_mb": peak_memory,
        "memory_increase_mb": final_memory - initial_memory,
        "root_path": str(root_path),
        "extensions": extensions,
        "scanner_type": "parallel" if parallel else "sequential",
        "max_workers": max_workers if parallel else None,
        "filtering_enabled": enable_filtering,
    }

    return found_files, metrics


def main():
    """Main function to parse arguments and run benchmarks."""
    parser = argparse.ArgumentParser(
        description="Benchmark AniVault directory scanning performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --path ./test_data --extensions .mp4,.mkv
  %(prog)s --path ./large_test_data --extensions .mp4,.mkv,.avi --output results.json
        """,
    )

    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Directory path to scan for benchmarking",
    )

    parser.add_argument(
        "--extensions",
        type=str,
        default=".mp4,.mkv,.avi,.mov,.m4v,.wmv,.flv,.webm",
        help="Comma-separated list of file extensions to include (default: common video formats)",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output file to save benchmark results (JSON format)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output including file list",
    )

    parser.add_argument(
        "--memory-profile",
        action="store_true",
        help="Enable detailed memory profiling (shows line-by-line memory usage)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output except for final results",
    )

    parser.add_argument(
        "--filter",
        action="store_true",
        help="Enable smart filtering engine to skip unwanted files and directories",
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Use parallel directory scanner with ThreadPoolExecutor",
    )

    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of worker threads for parallel scanning (default: CPU count * 2)",
    )

    args = parser.parse_args()

    # Convert path to Path object
    root_path = Path(args.path)

    # Validate path
    if not root_path.exists():
        print(f"Error: Path does not exist: {root_path}")
        return 1

    if not root_path.is_dir():
        print(f"Error: Path is not a directory: {root_path}")
        return 1

    # Parse extensions
    extensions = [ext.strip() for ext in args.extensions.split(",") if ext.strip()]
    if not extensions:
        print("Error: No valid extensions provided")
        return 1

    if not args.quiet:
        print(f"Starting benchmark scan of: {root_path}")
        print(f"Looking for extensions: {extensions}")
        if args.memory_profile:
            print("Memory profiling enabled - detailed memory usage will be shown")
        print("-" * 50)

    try:
        # Run the scan
        if args.parallel and not args.quiet:
            print(
                f"Using parallel scanner with {args.max_workers or 'auto'} workers",
            )

        if args.filter:
            if not args.quiet:
                print(
                    "Smart filtering engine enabled - skipping unwanted files and directories",
                )

        found_files, metrics = run_scan(
            root_path,
            extensions,
            args.parallel,
            args.max_workers,
            args.quiet,
            args.memory_profile,
            args.filter,
        )

        # Create comprehensive report
        report = create_benchmark_report(metrics, found_files, args)

        # Print results
        if not args.quiet:
            print(f"Scan completed in {metrics['scan_duration']:.3f} seconds")
            print(f"Files found: {metrics['files_found']}")
            print(f"Directories scanned: {metrics['directories_scanned']}")
            print(f"Files per second: {metrics['files_per_second']:.2f}")
            print(f"Paths per minute: {metrics['paths_per_minute']:.0f}")
            print(f"Initial memory: {metrics['initial_memory_mb']:.2f} MB")
            print(f"Final memory: {metrics['final_memory_mb']:.2f} MB")
            print(f"Peak memory: {metrics['peak_memory_mb']:.2f} MB")
            print(f"Memory increase: {metrics['memory_increase_mb']:.2f} MB")

            # Print advanced metrics
            enhanced_metrics = report["performance_metrics"]
            if "memory_per_file_kb" in enhanced_metrics:
                print(
                    f"Memory per file: {enhanced_metrics['memory_per_file_kb']:.2f} KB",
                )
                print(f"Time per file: {enhanced_metrics['time_per_file_ms']:.2f} ms")
            print(
                f"Performance rating: {enhanced_metrics.get('performance_rating', 'unknown')}",
            )
            print(f"Memory rating: {enhanced_metrics.get('memory_rating', 'unknown')}")
        else:
            # Quiet mode - only show essential results
            enhanced_metrics = report["performance_metrics"]
            print(
                f"Scan: {metrics['files_found']} files in {metrics['scan_duration']:.3f}s "
                f"({metrics['paths_per_minute']:.0f} paths/min, "
                f"{enhanced_metrics.get('performance_rating', 'unknown')} performance)",
            )

        if args.verbose:
            print("\nFound files:")
            for file_path in found_files[:20]:  # Show first 20 files
                print(f"  {file_path}")
            if len(found_files) > 20:
                print(f"  ... and {len(found_files) - 20} more files")

        # Save results if output file specified
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            if not args.quiet:
                print(f"\nComprehensive results saved to: {output_path}")

        return 0

    except Exception as e:
        print(f"Error during benchmark: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
