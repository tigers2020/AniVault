"""Example script demonstrating performance profiling and analysis for AniVault.

This script shows how to use the SyncProfiler, PerformanceAnalyzer, and
PerformanceBenchmark modules to identify and analyze performance bottlenecks.
"""

import logging
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.metadata_cache import MetadataCache
from core.performance_analyzer import PerformanceAnalyzer
from core.performance_benchmark import PerformanceBenchmark
from core.sync_profiler import (
    ProfilerEvent,
    SyncProfiler,
    get_sync_profiler,
    profile_sync_operation,
)


def setup_logging():
    """Set up logging for the example."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def simulate_cache_operations(profiler: SyncProfiler, operation_count: int = 1000):
    """Simulate cache operations with profiling."""
    print(f"\n=== Simulating {operation_count} cache operations ===")

    metadata_cache = MetadataCache()

    with profiler.profile_operation(
        ProfilerEvent.CACHE_SET, "bulk_cache_setup", operation_size=operation_count
    ):
        # Simulate cache set operations
        for i in range(operation_count):
            key = f"anime_{i}"
            # Create a TMDBAnime object for testing
            from core.models import TMDBAnime

            data = TMDBAnime(tmdb_id=i, title=f"Anime Title {i}")
            data.original_title = f"Original Anime Title {i}"
            data.overview = f"This is a test anime with ID {i}"
            data.release_date = f"2020-{(i % 12) + 1:02d}-01"
            data.vote_average = 8.5 + (i % 10) * 0.1
            data.vote_count = 100 + i
            data.popularity = 50.0 + i
            data.genres = ["Action", "Adventure", "Drama"]
            data.backdrop_path = f"/backdrop_{i}.jpg"
            data.poster_path = f"/poster_{i}.jpg"
            metadata_cache.put(key, data)

    # Simulate cache get operations
    with profiler.profile_operation(
        ProfilerEvent.CACHE_GET, "bulk_cache_retrieval", operation_size=operation_count
    ):
        for i in range(operation_count):
            key = f"anime_{i}"
            data = metadata_cache.get(key)

    print(f"Completed {operation_count} cache operations")


def simulate_database_operations(profiler: SyncProfiler, operation_count: int = 100):
    """Simulate database operations with profiling."""
    print(f"\n=== Simulating {operation_count} database operations ===")

    # Simulate bulk insert
    with profiler.profile_operation(
        ProfilerEvent.DB_BULK_INSERT, "bulk_insert_simulation", operation_size=operation_count
    ):
        # Simulate database bulk insert
        time.sleep(0.01 * operation_count / 100)  # Simulate database latency

    # Simulate bulk update
    with profiler.profile_operation(
        ProfilerEvent.DB_BULK_UPDATE, "bulk_update_simulation", operation_size=operation_count
    ):
        # Simulate database bulk update
        time.sleep(0.015 * operation_count / 100)  # Simulate database latency

    print(f"Completed {operation_count} database operations")


def simulate_sync_operations(profiler: SyncProfiler, operation_count: int = 50):
    """Simulate synchronization operations with profiling."""
    print(f"\n=== Simulating {operation_count} sync operations ===")

    # Simulate incremental sync
    with profiler.profile_operation(
        ProfilerEvent.INCREMENTAL_SYNC,
        "incremental_sync_simulation",
        operation_size=operation_count,
    ):
        # Simulate incremental synchronization
        time.sleep(0.1 * operation_count / 10)  # Simulate sync latency

    # Simulate consistency check
    with profiler.profile_operation(
        ProfilerEvent.CONSISTENCY_CHECK,
        "consistency_check_simulation",
        operation_size=operation_count,
    ):
        # Simulate consistency checking
        time.sleep(0.2 * operation_count / 10)  # Simulate consistency check latency

    print(f"Completed {operation_count} sync operations")


@profile_sync_operation(ProfilerEvent.SYNC_OPERATION, "example_decorated_function")
def example_decorated_function(data_size: int = 100):
    """Example function using the profiling decorator."""
    print(f"Running decorated function with data size: {data_size}")

    # Simulate some work
    result = []
    for i in range(data_size):
        result.append(f"processed_item_{i}")
        time.sleep(0.001)  # Simulate processing time

    return result


def run_performance_analysis():
    """Run comprehensive performance analysis."""
    print("\n" + "=" * 60)
    print("PERFORMANCE PROFILING AND ANALYSIS EXAMPLE")
    print("=" * 60)

    # Get profiler instance
    profiler = get_sync_profiler()

    # Start memory tracking for detailed analysis
    profiler.start_memory_tracking()

    print("\n1. Running simulated operations with profiling...")

    # Run various operations with profiling
    simulate_cache_operations(profiler, 5000)
    simulate_database_operations(profiler, 200)
    simulate_sync_operations(profiler, 25)

    # Test decorated function
    print("\n=== Testing decorated function ===")
    result = example_decorated_function(100)
    print(f"Decorated function returned {len(result)} items")

    # Stop memory tracking
    profiler.stop_memory_tracking()

    print("\n2. Analyzing performance data...")

    # Get performance summary
    summary = profiler.get_performance_summary()
    print(f"Total operations profiled: {summary['total_operations']}")
    print(f"Overall average duration: {summary['overall_stats']['avg_duration_ms']:.2f}ms")
    print(f"Overall success rate: {summary['overall_stats']['success_rate']:.2f}%")

    # Get top bottlenecks
    bottlenecks = profiler.get_top_bottlenecks(5)
    print("\nTop 5 performance bottlenecks:")
    for i, bottleneck in enumerate(bottlenecks, 1):
        print(f"{i}. {bottleneck['operation_name']}: {bottleneck['avg_duration_ms']:.2f}ms avg")

    print("\n3. Running performance analysis...")

    # Create performance analyzer
    analyzer = PerformanceAnalyzer(profiler)

    # Analyze bottlenecks
    bottleneck_analyses = analyzer.analyze_bottlenecks()
    print(f"Found {len(bottleneck_analyses)} significant bottlenecks")

    # Show top recommendations
    if bottleneck_analyses:
        top_bottleneck = bottleneck_analyses[0]
        print(f"\nTop bottleneck: {top_bottleneck.operation_name}")
        print(f"Severity score: {top_bottleneck.severity_score:.1f}/100")
        print(f"Root causes: {', '.join(top_bottleneck.root_causes)}")

        if top_bottleneck.recommendations:
            print("Recommendations:")
            for i, rec in enumerate(top_bottleneck.recommendations[:3], 1):
                print(f"  {i}. {rec.title} ({rec.priority.value} priority)")
                print(f"     Impact: {rec.impact_estimate}")
                print(f"     Effort: {rec.effort_estimate}")

    print("\n4. Running performance benchmarks...")

    # Create and run benchmarks
    benchmark = PerformanceBenchmark()
    benchmark_results = benchmark.run_all_benchmarks()

    print(f"Completed {len(benchmark_results)} benchmarks:")
    for benchmark_name, result in benchmark_results.items():
        print(
            f"  {benchmark_name}: {result.throughput_per_sec:.2f} ops/sec, "
            f"{result.avg_duration_ms:.2f}ms avg, {result.success_rate:.1f}% success"
        )

    print("\n5. Generating comprehensive report...")

    # Generate performance report
    performance_report = analyzer.generate_performance_report()

    # Export metrics
    export_file = "performance_metrics_export.json"
    profiler.export_metrics(export_file)
    print(f"Exported metrics to {export_file}")

    # Show system stats
    system_stats = profiler.get_memory_stats()
    print(f"\nSystem memory usage: {system_stats['rss_mb']:.2f}MB")

    cpu_stats = profiler.get_cpu_stats()
    print(f"System CPU usage: {cpu_stats['cpu_percent']:.2f}%")

    print("\n6. Performance targets validation...")

    # Check against performance targets
    targets_met = 0
    total_targets = 0

    for benchmark_name, result in benchmark_results.items():
        if benchmark_name in performance_report["performance_targets"]:
            target = performance_report["performance_targets"][benchmark_name]
            total_targets += 1

            # Check single operations target
            if "max_duration_ms" in target:
                if result.avg_duration_ms <= target["max_duration_ms"]:
                    targets_met += 1
                    print(
                        f"✅ {benchmark_name}: Duration target met ({result.avg_duration_ms:.2f}ms <= {target['max_duration_ms']}ms)"
                    )
                else:
                    print(
                        f"❌ {benchmark_name}: Duration target missed ({result.avg_duration_ms:.2f}ms > {target['max_duration_ms']}ms)"
                    )

            # Check bulk operations target
            if "min_throughput_per_sec" in target:
                if result.throughput_per_sec >= target["min_throughput_per_sec"]:
                    targets_met += 1
                    print(
                        f"✅ {benchmark_name}: Throughput target met ({result.throughput_per_sec:.2f}/sec >= {target['min_throughput_per_sec']}/sec)"
                    )
                else:
                    print(
                        f"❌ {benchmark_name}: Throughput target missed ({result.throughput_per_sec:.2f}/sec < {target['min_throughput_per_sec']}/sec)"
                    )

    if total_targets > 0:
        target_percentage = (targets_met / total_targets) * 100
        print(
            f"\nPerformance targets met: {targets_met}/{total_targets} ({target_percentage:.1f}%)"
        )

    print("\n" + "=" * 60)
    print("PERFORMANCE ANALYSIS COMPLETE")
    print("=" * 60)

    return {
        "summary": summary,
        "bottlenecks": bottlenecks,
        "benchmark_results": benchmark_results,
        "performance_report": performance_report,
    }


if __name__ == "__main__":
    setup_logging()

    try:
        results = run_performance_analysis()
        print("\nPerformance analysis completed successfully!")

        # Show quick summary
        print("\nQuick Summary:")
        print(f"- Total operations: {results['summary']['total_operations']}")
        print(
            f"- Top bottleneck: {results['bottlenecks'][0]['operation_name'] if results['bottlenecks'] else 'None'}"
        )
        print(f"- Benchmarks completed: {len(results['benchmark_results'])}")

    except Exception as e:
        print(f"Performance analysis failed: {e}")
        import traceback

        traceback.print_exc()
