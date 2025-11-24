"""Generate performance comparison report between baseline and optimized results.

This script compares baseline performance data with optimized results and generates
a markdown report showing improvement multipliers and PRD success criteria fulfillment.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# PRD Success Criteria (from task requirements)
PRD_CRITERIA = {
    "subtitle_matching": {
        "target": 10.0,  # 10x improvement
        "description": "Subtitle matching performance improvement",
    },
    "title_matcher": {
        "target": 5.0,  # 5x improvement
        "description": "Title Matcher performance improvement",
    },
}


def load_benchmark_results(file_path: Path) -> dict[str, Any]:
    """Load benchmark results from JSON file.

    Args:
        file_path: Path to benchmark results JSON file

    Returns:
        Dictionary containing benchmark results data
    """
    with file_path.open(encoding="utf-8") as f:
        return json.load(f)


def calculate_improvement(
    baseline_time: float,
    optimized_time: float,
) -> float | None:
    """Calculate improvement multiplier.

    Args:
        baseline_time: Baseline execution time
        optimized_time: Optimized execution time

    Returns:
        Improvement multiplier (e.g., 2.5 means 2.5x faster), or None if invalid
    """
    if baseline_time <= 0 or optimized_time <= 0:
        return None
    return baseline_time / optimized_time


def generate_comparison_report(
    baseline_path: Path | None,
    optimized_path: Path,
    output_path: Path,
) -> None:
    """Generate markdown comparison report.

    Args:
        baseline_path: Path to baseline benchmark results (optional)
        optimized_path: Path to optimized benchmark results
        output_path: Path to output markdown report
    """
    # Load optimized results
    optimized_data = load_benchmark_results(optimized_path)
    optimized_results = {
        r["scenario_name"]: r
        for r in optimized_data.get("results", [])
        if r.get("success", False)
    }

    # Load baseline results if provided
    baseline_results: dict[str, Any] = {}
    if baseline_path and baseline_path.exists():
        baseline_data = load_benchmark_results(baseline_path)
        baseline_results = {
            r["scenario_name"]: r
            for r in baseline_data.get("results", [])
            if r.get("success", False)
        }

    # Generate report
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        f.write("# Performance Optimization Report\n\n")
        f.write("## Summary\n\n")

        if baseline_results:
            f.write(
                f"- **Baseline Results**: {len(baseline_results)} successful scenarios\n"
            )
        f.write(
            f"- **Optimized Results**: {len(optimized_results)} successful scenarios\n"
        )

        if not optimized_results:
            f.write("\n⚠️ **Warning**: No successful benchmark results found.\n")
            f.write("Please ensure benchmarks completed successfully before generating report.\n")
            return

        if baseline_results:
            f.write("\n## Performance Comparison\n\n")
            f.write(
                "| Scenario | Files | Baseline Time (s) | Optimized Time (s) | "
                "Improvement | Status |\n"
            )
            f.write(
                "|----------|-------|-------------------|-------------------|"
                "-------------|--------|\n"
            )

            for scenario_name in sorted(optimized_results.keys()):
                opt_result = optimized_results[scenario_name]
                baseline_result = baseline_results.get(scenario_name)

                if not baseline_result:
                    f.write(
                        f"| {scenario_name} | {opt_result['total_files']} | "
                        f"N/A | {opt_result['total_time']:.3f} | N/A | ⚠️ No baseline |\n"
                    )
                    continue

                improvement = calculate_improvement(
                    baseline_result["total_time"],
                    opt_result["total_time"],
                )

                if improvement:
                    status = "✅" if improvement >= 1.0 else "❌"
                    f.write(
                        f"| {scenario_name} | {opt_result['total_files']} | "
                        f"{baseline_result['total_time']:.3f} | "
                        f"{opt_result['total_time']:.3f} | "
                        f"{improvement:.2f}x | {status} |\n"
                    )
                else:
                    f.write(
                        f"| {scenario_name} | {opt_result['total_files']} | "
                        f"{baseline_result['total_time']:.3f} | "
                        f"{opt_result['total_time']:.3f} | N/A | ⚠️ Invalid |\n"
                    )

        # Detailed results table
        f.write("\n## Detailed Optimized Results\n\n")
        f.write(
            "| Scenario | Files | Total Time (s) | Throughput (files/s) | "
            "Scan (s) | Match (s) | Organize (s) |\n"
        )
        f.write(
            "|----------|-------|----------------|---------------------|"
            "----------|-----------|--------------|\n"
        )

        for scenario_name in sorted(optimized_results.keys()):
            result = optimized_results[scenario_name]
            timers = result.get("timers", {})
            f.write(
                f"| {scenario_name} | {result['total_files']} | "
                f"{result['total_time']:.3f} | "
                f"{result.get('files_per_second', 0.0):.2f} | "
                f"{timers.get('scan', 0.0):.3f} | "
                f"{timers.get('match', 0.0):.3f} | "
                f"{timers.get('organize', 0.0):.3f} |\n"
            )

        # PRD Success Criteria Check
        if baseline_results:
            f.write("\n## PRD Success Criteria\n\n")

            # Calculate subtitle matching improvement (if subtitle scenarios exist)
            subtitle_scenarios = [
                name for name in optimized_results.keys() if "subs" in name.lower()
            ]
            if subtitle_scenarios:
                subtitle_improvements = []
                for scenario_name in subtitle_scenarios:
                    if scenario_name in baseline_results:
                        improvement = calculate_improvement(
                            baseline_results[scenario_name]["total_time"],
                            optimized_results[scenario_name]["total_time"],
                        )
                        if improvement:
                            subtitle_improvements.append(improvement)

                if subtitle_improvements:
                    avg_subtitle_improvement = sum(subtitle_improvements) / len(
                        subtitle_improvements
                    )
                    target = PRD_CRITERIA["subtitle_matching"]["target"]
                    met = avg_subtitle_improvement >= target
                    status = "✅ PASS" if met else "❌ FAIL"
                    f.write(
                        f"- **Subtitle Matching**: {avg_subtitle_improvement:.2f}x "
                        f"(Target: {target}x) {status}\n"
                    )

            # Calculate title matcher improvement
            title_scenarios = [
                name
                for name in optimized_results.keys()
                if any(x in name for x in ["100", "1000", "10000"])
            ]
            if title_scenarios:
                title_improvements = []
                for scenario_name in title_scenarios:
                    if scenario_name in baseline_results:
                        improvement = calculate_improvement(
                            baseline_results[scenario_name]["total_time"],
                            optimized_results[scenario_name]["total_time"],
                        )
                        if improvement:
                            title_improvements.append(improvement)

                if title_improvements:
                    avg_title_improvement = sum(title_improvements) / len(
                        title_improvements
                    )
                    target = PRD_CRITERIA["title_matcher"]["target"]
                    met = avg_title_improvement >= target
                    status = "✅ PASS" if met else "❌ FAIL"
                    f.write(
                        f"- **Title Matcher**: {avg_title_improvement:.2f}x "
                        f"(Target: {target}x) {status}\n"
                    )

        f.write("\n## Notes\n\n")
        f.write(
            "- Improvement multiplier: Higher is better (e.g., 2.5x means 2.5 times faster)\n"
        )
        if not baseline_results:
            f.write(
                "- Baseline data not provided. Run benchmarks with baseline data to see comparisons.\n"
            )
        f.write(
            "- All times are in seconds\n"
            "- Throughput is calculated as files processed per second\n"
        )

    print(f"\n[OK] Comparison report saved to: {output_path}")


if __name__ == "__main__":
    """Generate comparison report from command line."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate performance comparison report"
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Path to baseline benchmark results JSON file",
    )
    parser.add_argument(
        "--optimized",
        type=Path,
        default=Path("benchmarks/final_performance_results.json"),
        help="Path to optimized benchmark results JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/performance_comparison_report.md"),
        help="Path to output markdown report",
    )

    args = parser.parse_args()

    generate_comparison_report(
        baseline_path=args.baseline,
        optimized_path=args.optimized,
        output_path=args.output,
    )
