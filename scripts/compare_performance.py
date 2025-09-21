#!/usr/bin/env python3
"""Performance Comparison Script

This script compares the performance before and after index creation.
"""

import json
import sys


def load_performance_data(filepath: str) -> dict:
    """Load performance data from JSON file."""
    try:
        with open(filepath) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)


def compare_performance(before_data: dict, after_data: dict):
    """Compare performance before and after index creation."""
    print("=" * 80)
    print("PERFORMANCE COMPARISON: BEFORE vs AFTER INDEX CREATION")
    print("=" * 80)

    # Compare updated_at queries
    print("\n📊 ANIME METADATA (updated_at) QUERIES:")
    print("-" * 50)

    before_updated = before_data["updated_at_queries"]
    after_updated = after_data["updated_at_queries"]

    # ORDER BY updated_at
    before_order = before_updated["order_by_updated_at"]["avg_time_per_record_ms"]
    after_order = after_updated["order_by_updated_at"]["avg_time_per_record_ms"]
    improvement_order = (
        ((before_order - after_order) / before_order) * 100 if before_order > 0 else 0
    )

    print("ORDER BY updated_at:")
    print(f"  Before: {before_order:.6f}ms per record")
    print(f"  After:  {after_order:.6f}ms per record")
    print(
        f"  Improvement: {improvement_order:.1f}% {'faster' if improvement_order > 0 else 'slower'}"
    )

    # Filter by updated_at
    before_filter = before_updated["filter_by_updated_at"]["total_time_ms"]
    after_filter = after_updated["filter_by_updated_at"]["total_time_ms"]
    improvement_filter = (
        ((before_filter - after_filter) / before_filter) * 100 if before_filter > 0 else 0
    )

    print("\nFilter by updated_at:")
    print(f"  Before: {before_filter:.6f}ms total")
    print(f"  After:  {after_filter:.6f}ms total")
    print(
        f"  Improvement: {improvement_filter:.1f}% {'faster' if improvement_filter > 0 else 'slower'}"
    )

    # Incremental sync pattern
    before_sync = before_updated["incremental_sync_pattern"]["avg_time_per_record_ms"]
    after_sync = after_updated["incremental_sync_pattern"]["avg_time_per_record_ms"]
    improvement_sync = ((before_sync - after_sync) / before_sync) * 100 if before_sync > 0 else 0

    print("\nIncremental sync pattern:")
    print(f"  Before: {before_sync:.6f}ms per record")
    print(f"  After:  {after_sync:.6f}ms per record")
    print(
        f"  Improvement: {improvement_sync:.1f}% {'faster' if improvement_sync > 0 else 'slower'}"
    )

    # Compare db_updated_at queries
    print("\n📊 PARSED FILES (db_updated_at) QUERIES:")
    print("-" * 50)

    before_db_updated = before_data["db_updated_at_queries"]
    after_db_updated = after_data["db_updated_at_queries"]

    # ORDER BY db_updated_at
    before_order = before_db_updated["order_by_db_updated_at"]["avg_time_per_record_ms"]
    after_order = after_db_updated["order_by_db_updated_at"]["avg_time_per_record_ms"]
    improvement_order = (
        ((before_order - after_order) / before_order) * 100 if before_order > 0 else 0
    )

    print("ORDER BY db_updated_at:")
    print(f"  Before: {before_order:.6f}ms per record")
    print(f"  After:  {after_order:.6f}ms per record")
    print(
        f"  Improvement: {improvement_order:.1f}% {'faster' if improvement_order > 0 else 'slower'}"
    )

    # Filter by db_updated_at
    before_filter = before_db_updated["filter_by_db_updated_at"]["total_time_ms"]
    after_filter = after_db_updated["filter_by_db_updated_at"]["total_time_ms"]
    improvement_filter = (
        ((before_filter - after_filter) / before_filter) * 100 if before_filter > 0 else 0
    )

    print("\nFilter by db_updated_at:")
    print(f"  Before: {before_filter:.6f}ms total")
    print(f"  After:  {after_filter:.6f}ms total")
    print(
        f"  Improvement: {improvement_filter:.1f}% {'faster' if improvement_filter > 0 else 'slower'}"
    )

    # Incremental sync pattern
    before_sync = before_db_updated["incremental_sync_pattern"]["avg_time_per_record_ms"]
    after_sync = after_db_updated["incremental_sync_pattern"]["avg_time_per_record_ms"]
    improvement_sync = ((before_sync - after_sync) / before_sync) * 100 if before_sync > 0 else 0

    print("\nIncremental sync pattern:")
    print(f"  Before: {before_sync:.6f}ms per record")
    print(f"  After:  {after_sync:.6f}ms per record")
    print(
        f"  Improvement: {improvement_sync:.1f}% {'faster' if improvement_sync > 0 else 'slower'}"
    )

    # Overall summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)

    improvements = [
        improvement_order,  # updated_at ORDER BY
        improvement_filter,  # updated_at filter
        improvement_sync,  # updated_at sync
    ]

    avg_improvement = sum(improvements) / len(improvements)

    print(f"Average Performance Improvement: {avg_improvement:.1f}%")

    if avg_improvement > 0:
        print("✅ Index creation was successful and improved performance!")
    elif avg_improvement > -5:
        print("⚠️  Performance remained roughly the same (small dataset effect)")
    else:
        print("❌ Performance degraded - investigate index usage")

    # Database size context
    before_count = before_data["database_stats"]["table_stats"]["anime_metadata_count"]
    after_count = after_data["database_stats"]["table_stats"]["anime_metadata_count"]

    print("\nDatabase Context:")
    print(
        f"  Test Dataset: {after_count} anime records, {after_data['database_stats']['table_stats']['parsed_files_count']} file records"
    )
    print("  Note: Performance improvements become more significant with larger datasets")

    print("=" * 80)


def main():
    """Main function to compare performance."""
    if len(sys.argv) != 3:
        print("Usage: python scripts/compare_performance.py <before_file> <after_file>")
        print(
            "Example: python scripts/compare_performance.py query_performance_baseline.json query_performance_after_indexes.json"
        )
        sys.exit(1)

    before_file = sys.argv[1]
    after_file = sys.argv[2]

    print("Loading performance data...")
    print(f"  Before: {before_file}")
    print(f"  After:  {after_file}")

    before_data = load_performance_data(before_file)
    after_data = load_performance_data(after_file)

    compare_performance(before_data, after_data)


if __name__ == "__main__":
    main()
