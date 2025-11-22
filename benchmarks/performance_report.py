"""Performance benchmark report generator.

This module runs benchmark scenarios and collects performance metrics
by executing the main application with --benchmark flag and parsing JSON output.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, NamedTuple

from benchmarks.benchmark_scenarios import generate_all_scenarios
from benchmarks.subtitle_scenarios import generate_all_subtitle_scenarios


class BenchmarkResult(NamedTuple):
    """Result of a single benchmark run."""

    scenario_name: str
    success: bool
    timers: dict[str, float]
    total_time: float
    total_files: int
    files_per_second: float
    error_message: str | None = None


def run_benchmark_scenario(
    scenario_dir: Path,
    scenario_name: str,
    anivault_command: str = "anivault",
) -> BenchmarkResult:
    """Run benchmark for a single scenario.

    Args:
        scenario_dir: Directory containing test data
        scenario_name: Name of the scenario
        anivault_command: Command to run anivault (default: "anivault")

    Returns:
        BenchmarkResult with performance metrics

    Example:
        >>> result = run_benchmark_scenario(
        ...     Path("benchmarks/test_data/100_files_10_subs"),
        ...     "100_files_10_subs"
        ... )
        >>> result.success
        True
    """
    try:
        # Run anivault with --benchmark and --json flags
        # Split command into list if it contains spaces (e.g., "python -m anivault")
        if " " in anivault_command:
            cmd_base = anivault_command.split()
        else:
            cmd_base = [anivault_command]

        cmd = [
            *cmd_base,
            "--benchmark",  # Global option, must come before command
            "run",
            str(scenario_dir),
            "--json",
            "--yes",  # Skip confirmation prompts
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit
            timeout=3600,  # 1 hour timeout
        )

        if result.returncode != 0:
            return BenchmarkResult(
                scenario_name=scenario_name,
                success=False,
                timers={},
                total_time=0.0,
                total_files=0,
                files_per_second=0.0,
                error_message=f"Command failed with exit code {result.returncode}: {result.stderr}",
            )

        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return BenchmarkResult(
                scenario_name=scenario_name,
                success=False,
                timers={},
                total_time=0.0,
                total_files=0,
                files_per_second=0.0,
                error_message=f"Failed to parse JSON output: {e!s}",
            )

        # Extract benchmark data
        if not output_data.get("success", False):
            errors = output_data.get("errors", [])
            error_msg = "; ".join(errors) if errors else "Unknown error"
            return BenchmarkResult(
                scenario_name=scenario_name,
                success=False,
                timers={},
                total_time=0.0,
                total_files=0,
                files_per_second=0.0,
                error_message=error_msg,
            )

        data = output_data.get("data", {})
        benchmark_data = data.get("benchmark", {})

        if not benchmark_data:
            return BenchmarkResult(
                scenario_name=scenario_name,
                success=False,
                timers={},
                total_time=0.0,
                total_files=0,
                files_per_second=0.0,
                error_message="No benchmark data in output",
            )

        return BenchmarkResult(
            scenario_name=scenario_name,
            success=True,
            timers=benchmark_data.get("timers", {}),
            total_time=benchmark_data.get("total_time", 0.0),
            total_files=benchmark_data.get("total_files", 0),
            files_per_second=benchmark_data.get("files_per_second", 0.0),
        )

    except subprocess.TimeoutExpired:
        return BenchmarkResult(
            scenario_name=scenario_name,
            success=False,
            timers={},
            total_time=0.0,
            total_files=0,
            files_per_second=0.0,
            error_message="Benchmark execution timed out",
        )
    except Exception as e:
        return BenchmarkResult(
            scenario_name=scenario_name,
            success=False,
            timers={},
            total_time=0.0,
            total_files=0,
            files_per_second=0.0,
            error_message=f"Unexpected error: {e!s}",
        )


def save_benchmark_results(
    results: list[BenchmarkResult],
    output_path: Path,
    format: str = "auto",
) -> None:
    """Save benchmark results to file.

    Args:
        results: List of benchmark results
        output_path: Path to output file
        format: Output format ("json", "csv", "markdown", or "auto" based on extension)

    Example:
        >>> results = [BenchmarkResult(...)]
        >>> save_benchmark_results(results, Path("results.json"))
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine format from extension if auto
    if format == "auto":
        ext = output_path.suffix.lower()
        if ext == ".csv":
            format = "csv"
        elif ext in (".md", ".markdown"):
            format = "markdown"
        else:
            format = "json"

    if format == "json":
        output_data = {
            "summary": {
                "total_scenarios": len(results),
                "successful": len([r for r in results if r.success]),
                "failed": len([r for r in results if not r.success]),
            },
            "results": [
                {
                    "scenario_name": r.scenario_name,
                    "success": r.success,
                    "timers": r.timers,
                    "total_time": r.total_time,
                    "total_files": r.total_files,
                    "files_per_second": r.files_per_second,
                    "error_message": r.error_message,
                }
                for r in results
            ],
        }

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)

    elif format == "csv":
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Scenario",
                "Success",
                "Total Files",
                "Total Time (s)",
                "Throughput (files/s)",
                "Scan Time (s)",
                "Match Time (s)",
                "Organize Time (s)",
                "Error Message",
            ])

            for r in results:
                writer.writerow([
                    r.scenario_name,
                    "Yes" if r.success else "No",
                    r.total_files,
                    f"{r.total_time:.3f}",
                    f"{r.files_per_second:.2f}",
                    f"{r.timers.get('scan', 0.0):.3f}",
                    f"{r.timers.get('match', 0.0):.3f}",
                    f"{r.timers.get('organize', 0.0):.3f}",
                    r.error_message or "",
                ])

    elif format == "markdown":
        with output_path.open("w", encoding="utf-8") as f:
            f.write("# Benchmark Performance Report\n\n")

            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]

            f.write(f"## Summary\n\n")
            f.write(f"- **Total Scenarios**: {len(results)}\n")
            f.write(f"- **Successful**: {len(successful)}\n")
            f.write(f"- **Failed**: {len(failed)}\n\n")

            if successful:
                f.write("## Performance Results\n\n")
                f.write("| Scenario | Files | Total Time (s) | Throughput (files/s) | Scan (s) | Match (s) | Organize (s) |\n")
                f.write("|----------|-------|----------------|---------------------|----------|-----------|--------------|\n")

                for r in successful:
                    f.write(
                        f"| {r.scenario_name} | {r.total_files} | {r.total_time:.3f} | "
                        f"{r.files_per_second:.2f} | {r.timers.get('scan', 0.0):.3f} | "
                        f"{r.timers.get('match', 0.0):.3f} | {r.timers.get('organize', 0.0):.3f} |\n"
                    )

            if failed:
                f.write("\n## Failed Scenarios\n\n")
                for r in failed:
                    f.write(f"- **{r.scenario_name}**: {r.error_message}\n")

    print(f"\n[OK] Results saved to: {output_path} ({format.upper()} format)")


def run_all_benchmarks(
    base_dir: Path | None = None,
    anivault_command: str = "anivault",
    regenerate_data: bool = False,
) -> list[BenchmarkResult]:
    """Run all benchmark scenarios and collect results.

    Args:
        base_dir: Base directory for test data. Defaults to benchmarks/test_data
        anivault_command: Command to run anivault (default: "anivault")
        regenerate_data: Whether to regenerate test data before running

    Returns:
        List of BenchmarkResult objects

    Example:
        >>> results = run_all_benchmarks()
        >>> len(results) > 0
        True
    """
    if base_dir is None:
        base_dir = Path(__file__).parent / "test_data"

    # Generate test data if needed
    if regenerate_data or not base_dir.exists():
        print("Generating test data scenarios...")
        generate_all_scenarios(base_dir)
        generate_all_subtitle_scenarios(base_dir)
        print()

    # Collect all scenario directories
    scenarios: dict[str, Path] = {}

    # Add file+subtitle scenarios
    file_scenarios = generate_all_scenarios(base_dir)
    scenarios.update(file_scenarios)

    # Add subtitle-only scenarios
    sub_scenarios = generate_all_subtitle_scenarios(base_dir)
    scenarios.update(sub_scenarios)

    # Run benchmarks
    results: list[BenchmarkResult] = []

    print(f"Running {len(scenarios)} benchmark scenarios...\n")

    for scenario_name, scenario_dir in scenarios.items():
        print(f"Running benchmark: {scenario_name}...")
        result = run_benchmark_scenario(scenario_dir, scenario_name, anivault_command)

        if result.success:
            print(f"  [OK] Success: {result.total_files} files in {result.total_time:.3f}s ({result.files_per_second:.2f} files/s)")
        else:
            print(f"  [FAIL] Failed: {result.error_message}")

        results.append(result)
        print()

    return results


if __name__ == "__main__":
    """Run all benchmarks when executed directly."""
    import argparse

    parser = argparse.ArgumentParser(description="Run performance benchmarks")
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate test data before running benchmarks",
    )
    parser.add_argument(
        "--command",
        default="anivault",
        help="Command to run anivault (default: anivault)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for results (JSON format)",
    )

    args = parser.parse_args()

    # Run benchmarks
    results = run_all_benchmarks(
        regenerate_data=args.regenerate,
        anivault_command=args.command,
    )

    # Print summary
    print("\n" + "=" * 80)
    print("Benchmark Summary")
    print("=" * 80)

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"\nSuccessful: {len(successful)}/{len(results)}")
    if failed:
        print(f"Failed: {len(failed)}")
        for result in failed:
            print(f"  - {result.scenario_name}: {result.error_message}")

    if successful:
        print("\nPerformance Results:")
        print("-" * 80)
        print(f"{'Scenario':<30} {'Files':<10} {'Time (s)':<12} {'Throughput (files/s)':<20}")
        print("-" * 80)

        for result in successful:
            print(
                f"{result.scenario_name:<30} "
                f"{result.total_files:<10} "
                f"{result.total_time:<12.3f} "
                f"{result.files_per_second:<20.2f}"
            )

    # Save results if output specified
    if args.output:
        save_benchmark_results(results, args.output)

