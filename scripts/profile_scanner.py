#!/usr/bin/env python3
"""
Performance profiling script for AniVault file scanner.

This script measures the execution time and throughput of the core scanning
function against test directories to establish performance baselines.

Usage:
    python scripts/profile_scanner.py [--target TARGET_DIR] [--iterations N] [--warmup]
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from anivault.scanner.file_scanner import (
    get_media_files_count,
    scan_directory,
    scan_directory_with_stats,
)


class PerformanceProfiler:
    """Performance profiler for the file scanner."""

    def __init__(
        self, target_dir: str | Path, iterations: int = 3, warmup: bool = True
    ):
        """Initialize the profiler.

        Args:
            target_dir: Directory to profile against.
            iterations: Number of profiling iterations to run.
            warmup: Whether to run a warmup iteration before profiling.
        """
        self.target_dir = Path(target_dir)
        self.iterations = iterations
        self.warmup = warmup
        self.results: List[Dict[str, Any]] = []

    def validate_target(self) -> bool:
        """Validate that the target directory exists and is accessible.

        Returns:
            True if target is valid, False otherwise.
        """
        if not self.target_dir.exists():
            print(f"❌ Error: Target directory does not exist: {self.target_dir}")
            return False

        if not self.target_dir.is_dir():
            print(f"❌ Error: Target path is not a directory: {self.target_dir}")
            return False

        # Test basic access
        try:
            list(os.scandir(self.target_dir))
        except PermissionError:
            print(f"❌ Error: Permission denied accessing: {self.target_dir}")
            return False
        except OSError as e:
            print(f"❌ Error: Cannot access directory: {e}")
            return False

        return True

    def run_warmup(self) -> None:
        """Run a warmup iteration to prime the system."""
        if not self.warmup:
            return

        print("🔥 Running warmup iteration...")
        try:
            # Quick warmup scan
            count = get_media_files_count(self.target_dir)
            print(f"   Warmup completed: {count} files found")
        except Exception as e:
            print(f"   Warmup failed: {e}")

    def profile_scan_directory(self) -> Dict[str, Any]:
        """Profile the basic scan_directory function.

        Returns:
            Dictionary with performance metrics.
        """
        print("📁 Profiling scan_directory()...")

        start_time = time.perf_counter()
        files = list(scan_directory(self.target_dir))
        end_time = time.perf_counter()

        execution_time = end_time - start_time
        file_count = len(files)
        rate_files_per_sec = file_count / execution_time if execution_time > 0 else 0
        rate_paths_per_min = rate_files_per_sec * 60

        return {
            "function": "scan_directory",
            "files_found": file_count,
            "execution_time": execution_time,
            "rate_files_per_sec": rate_files_per_sec,
            "rate_paths_per_min": rate_paths_per_min,
            "memory_efficient": True,  # Generator-based
        }

    def profile_scan_with_stats(self) -> Dict[str, Any]:
        """Profile the scan_directory_with_stats function.

        Returns:
            Dictionary with performance metrics.
        """
        print("📊 Profiling scan_directory_with_stats()...")

        start_time = time.perf_counter()
        files, stats = scan_directory_with_stats(self.target_dir)
        file_list = list(files)
        end_time = time.perf_counter()

        execution_time = end_time - start_time
        file_count = len(file_list)
        rate_files_per_sec = file_count / execution_time if execution_time > 0 else 0
        rate_paths_per_min = rate_files_per_sec * 60

        return {
            "function": "scan_directory_with_stats",
            "files_found": file_count,
            "execution_time": execution_time,
            "rate_files_per_sec": rate_files_per_sec,
            "rate_paths_per_min": rate_paths_per_min,
            "directories_scanned": stats["directories_scanned"],
            "permission_errors": stats["permission_errors"],
            "other_errors": stats["other_errors"],
            "memory_efficient": True,  # Generator-based
        }

    def profile_count_only(self) -> Dict[str, Any]:
        """Profile the get_media_files_count function.

        Returns:
            Dictionary with performance metrics.
        """
        print("🔢 Profiling get_media_files_count()...")

        start_time = time.perf_counter()
        file_count = get_media_files_count(self.target_dir)
        end_time = time.perf_counter()

        execution_time = end_time - start_time
        rate_files_per_sec = file_count / execution_time if execution_time > 0 else 0
        rate_paths_per_min = rate_files_per_sec * 60

        return {
            "function": "get_media_files_count",
            "files_found": file_count,
            "execution_time": execution_time,
            "rate_files_per_sec": rate_files_per_sec,
            "rate_paths_per_min": rate_paths_per_min,
            "memory_efficient": True,  # Generator-based
        }

    def run_profiling_iteration(self, iteration: int) -> Dict[str, Any]:
        """Run a single profiling iteration.

        Args:
            iteration: Current iteration number.

        Returns:
            Dictionary with combined performance metrics.
        """
        print(f"\n🔄 Iteration {iteration + 1}/{self.iterations}")
        print("=" * 50)

        iteration_results = {}

        # Profile each function
        iteration_results["scan_directory"] = self.profile_scan_directory()
        iteration_results["scan_with_stats"] = self.profile_scan_with_stats()
        iteration_results["count_only"] = self.profile_count_only()

        # Calculate iteration summary
        total_time = sum(
            result["execution_time"] for result in iteration_results.values()
        )

        iteration_results["iteration"] = iteration + 1
        iteration_results["total_time"] = total_time

        return iteration_results

    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate statistical summary of all iterations.

        Returns:
            Dictionary with statistical analysis.
        """
        if not self.results:
            return {}

        # Extract metrics for each function
        functions = ["scan_directory", "scan_with_stats", "count_only"]
        stats = {}

        for func_name in functions:
            times = [result[func_name]["execution_time"] for result in self.results]
            rates = [result[func_name]["rate_files_per_sec"] for result in self.results]

            stats[func_name] = {
                "execution_time": {
                    "min": min(times),
                    "max": max(times),
                    "avg": sum(times) / len(times),
                    "std": self._calculate_std(times),
                },
                "rate_files_per_sec": {
                    "min": min(rates),
                    "max": max(rates),
                    "avg": sum(rates) / len(rates),
                    "std": self._calculate_std(rates),
                },
            }

        return stats

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation of values."""
        if len(values) <= 1:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance**0.5

    def print_results(self) -> None:
        """Print comprehensive performance results."""
        print("\n" + "=" * 80)
        print("📈 PERFORMANCE PROFILING RESULTS")
        print("=" * 80)

        # Target directory info
        print(f"🎯 Target Directory: {self.target_dir}")
        print(f"📁 Directory Size: {self._get_directory_size():.2f} MB")
        print(f"🔄 Iterations: {self.iterations}")
        print()

        # Individual iteration results
        for i, result in enumerate(self.results):
            print(f"📊 Iteration {i + 1} Results:")
            print("-" * 40)

            for func_name, metrics in result.items():
                if func_name in ["iteration", "total_time"]:
                    continue

                print(f"  {func_name}:")
                print(f"    Files: {metrics['files_found']:,}")
                print(f"    Time: {metrics['execution_time']:.4f}s")
                print(f"    Rate: {metrics['rate_files_per_sec']:.0f} files/sec")
                print(f"    Rate: {metrics['rate_paths_per_min']:.0f} paths/min")
                print()

        # Statistical summary
        stats = self.calculate_statistics()
        if stats:
            print("📈 Statistical Summary:")
            print("-" * 40)

            for func_name, func_stats in stats.items():
                print(f"  {func_name}:")
                time_stats = func_stats["execution_time"]
                rate_stats = func_stats["rate_files_per_sec"]

                print("    Execution Time:")
                print(f"      Min: {time_stats['min']:.4f}s")
                print(f"      Max: {time_stats['max']:.4f}s")
                print(f"      Avg: {time_stats['avg']:.4f}s")
                print(f"      Std: {time_stats['std']:.4f}s")

                print("    Rate (files/sec):")
                print(f"      Min: {rate_stats['min']:.0f}")
                print(f"      Max: {rate_stats['max']:.0f}")
                print(f"      Avg: {rate_stats['avg']:.0f}")
                print(f"      Std: {rate_stats['std']:.0f}")
                print()

        # Performance assessment
        self._print_performance_assessment()

    def _get_directory_size(self) -> float:
        """Calculate directory size in MB."""
        total_size = 0
        try:
            for file_path in self.target_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except (OSError, PermissionError):
            pass
        return total_size / (1024 * 1024)

    def _print_performance_assessment(self) -> None:
        """Print performance assessment and recommendations."""
        print("🎯 Performance Assessment:")
        print("-" * 40)

        if not self.results:
            print("  No results to assess.")
            return

        # Get average rates
        avg_rates = {}
        for func_name in ["scan_directory", "scan_with_stats", "count_only"]:
            rates = [result[func_name]["rate_files_per_sec"] for result in self.results]
            avg_rates[func_name] = sum(rates) / len(rates)

        # Performance targets from develop_plan.md
        target_rate = 120000  # paths/minute from the plan
        target_rate_per_sec = target_rate / 60  # Convert to per second

        print(
            f"  Target Rate: {target_rate:,} paths/minute ({target_rate_per_sec:.0f} files/sec)"
        )

        for func_name, avg_rate in avg_rates.items():
            percentage = (avg_rate / target_rate_per_sec) * 100
            status = (
                "✅ EXCELLENT"
                if percentage >= 100
                else "⚠️  NEEDS IMPROVEMENT"
                if percentage >= 50
                else "❌ POOR"
            )
            print(
                f"  {func_name}: {avg_rate:.0f} files/sec ({percentage:.1f}% of target) {status}"
            )

        print()
        print("💡 Recommendations:")
        if any(rate < target_rate_per_sec for rate in avg_rates.values()):
            print("  - Consider optimizing I/O operations")
            print("  - Check for unnecessary file system calls")
            print("  - Verify SSD vs HDD performance differences")
        else:
            print("  - Performance meets or exceeds targets! 🎉")
            print("  - Consider running on different hardware for comparison")

    def run(self) -> bool:
        """Run the complete profiling process.

        Returns:
            True if profiling completed successfully, False otherwise.
        """
        print("🚀 Starting AniVault Scanner Performance Profiling")
        print("=" * 60)

        # Validate target
        if not self.validate_target():
            return False

        # Run warmup
        self.run_warmup()

        # Run profiling iterations
        for i in range(self.iterations):
            result = self.run_profiling_iteration(i)
            self.results.append(result)

        # Print results
        self.print_results()

        return True


def main():
    """Main entry point for the profiling script."""
    parser = argparse.ArgumentParser(
        description="Profile AniVault file scanner performance",
    )
    parser.add_argument(
        "--target",
        type=str,
        default="./test_data_medium",
        help="Target directory to profile (default: ./test_data_medium)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of profiling iterations (default: 3)",
    )
    parser.add_argument(
        "--warmup",
        action="store_true",
        default=True,
        help="Run warmup iteration (default: True)",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip warmup iteration",
    )

    args = parser.parse_args()

    # Handle warmup flag
    warmup = args.warmup and not args.no_warmup

    # Create profiler
    profiler = PerformanceProfiler(
        target_dir=args.target,
        iterations=args.iterations,
        warmup=warmup,
    )

    # Run profiling
    success = profiler.run()

    if success:
        print("\n✅ Profiling completed successfully!")
        return 0
    print("\n❌ Profiling failed!")
    return 1


if __name__ == "__main__":
    sys.exit(main())
