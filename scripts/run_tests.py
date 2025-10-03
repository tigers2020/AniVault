#!/usr/bin/env python3
"""
Test runner script for AniVault project.

This script provides convenient commands for running different types of tests
with appropriate configurations and options.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], description: str) -> int:
    """Run a command and return its exit code."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def run_unit_tests(verbose: bool = False, coverage: bool = False) -> int:
    """Run unit tests only."""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "unit"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(
            ["--cov=src/anivault", "--cov-report=html", "--cov-report=term-missing"]
        )

    return run_command(cmd, "Unit Tests")


def run_integration_tests(verbose: bool = False) -> int:
    """Run integration tests only."""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "integration"]

    if verbose:
        cmd.append("-v")

    return run_command(cmd, "Integration Tests")


def run_benchmark_tests(verbose: bool = False) -> int:
    """Run benchmark tests only."""
    cmd = ["python", "-m", "pytest", "tests/benchmarks/", "-m", "benchmark"]

    if verbose:
        cmd.append("-v")

    return run_command(cmd, "Benchmark Tests")


def run_all_tests(
    verbose: bool = False, coverage: bool = False, exclude_slow: bool = False
) -> int:
    """Run all tests."""
    cmd = ["python", "-m", "pytest", "tests/"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(
            ["--cov=src/anivault", "--cov-report=html", "--cov-report=term-missing"]
        )

    if exclude_slow:
        cmd.extend(["-m", "not slow"])

    return run_command(cmd, "All Tests")


def run_specific_test(test_path: str, verbose: bool = False) -> int:
    """Run a specific test file or test function."""
    cmd = ["python", "-m", "pytest", test_path]

    if verbose:
        cmd.append("-v")

    return run_command(cmd, f"Specific Test: {test_path}")


def run_fast_tests(verbose: bool = False) -> int:
    """Run fast tests only (exclude slow and benchmark tests)."""
    cmd = ["python", "-m", "pytest", "tests/", "-m", "not slow and not benchmark"]

    if verbose:
        cmd.append("-v")

    return run_command(cmd, "Fast Tests Only")


def run_with_parallel(workers: int = 4, verbose: bool = False) -> int:
    """Run tests in parallel using pytest-xdist."""
    cmd = ["python", "-m", "pytest", "tests/", f"-n={workers}"]

    if verbose:
        cmd.append("-v")

    return run_command(cmd, f"Parallel Tests ({workers} workers)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AniVault Test Runner")
    parser.add_argument(
        "test_type",
        choices=[
            "unit",
            "integration",
            "benchmark",
            "all",
            "fast",
            "parallel",
            "specific",
        ],
        help="Type of tests to run",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--coverage", "-c", action="store_true", help="Generate coverage report"
    )
    parser.add_argument(
        "--exclude-slow",
        action="store_true",
        help="Exclude slow tests when running all tests",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=4,
        help="Number of parallel workers (for parallel mode)",
    )
    parser.add_argument(
        "--test-path", help="Specific test file or function to run (for specific mode)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.test_type == "specific" and not args.test_path:
        print("Error: --test-path is required for 'specific' test type")
        return 1

    # Run appropriate test suite
    if args.test_type == "unit":
        return run_unit_tests(args.verbose, args.coverage)
    elif args.test_type == "integration":
        return run_integration_tests(args.verbose)
    elif args.test_type == "benchmark":
        return run_benchmark_tests(args.verbose)
    elif args.test_type == "all":
        return run_all_tests(args.verbose, args.coverage, args.exclude_slow)
    elif args.test_type == "fast":
        return run_fast_tests(args.verbose)
    elif args.test_type == "parallel":
        return run_with_parallel(args.workers, args.verbose)
    elif args.test_type == "specific":
        return run_specific_test(args.test_path, args.verbose)
    else:
        print(f"Unknown test type: {args.test_type}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
