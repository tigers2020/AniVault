#!/usr/bin/env python3
"""Database Query Performance Analysis Script

This script analyzes the current performance baseline for queries involving
the target columns: tmdb_id, file_path, updated_at, and db_updated_at.

Usage:
    python scripts/analyze_query_performance.py [--database-url DATABASE_URL]
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from core.database import AnimeMetadata, DatabaseManager, ParsedFile

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class QueryPerformanceAnalyzer:
    """Analyzes database query performance for indexing optimization."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.results: dict[str, Any] = {}

    def analyze_tmdb_id_queries(self) -> dict[str, Any]:
        """Analyze performance of queries involving tmdb_id."""
        logger.info("Analyzing tmdb_id query performance...")

        results = {"single_lookup": {}, "bulk_lookup": {}, "bulk_in_operation": {}}

        with self.db_manager.get_session() as session:
            # Get sample tmdb_ids for testing
            sample_tmdb_ids = session.query(AnimeMetadata.tmdb_id).limit(100).all()
            if not sample_tmdb_ids:
                logger.warning("No anime metadata found for testing")
                return results

            tmdb_id_list = [row[0] for row in sample_tmdb_ids]

            # Test 1: Single tmdb_id lookup
            start_time = time.time()
            for tmdb_id in tmdb_id_list[:10]:  # Test first 10
                session.query(AnimeMetadata).filter_by(tmdb_id=tmdb_id).first()
            end_time = time.time()

            results["single_lookup"] = {
                "queries_executed": 10,
                "total_time_ms": (end_time - start_time) * 1000,
                "avg_time_per_query_ms": (end_time - start_time) * 100,
                "sample_tmdb_ids": tmdb_id_list[:5],
            }

            # Test 2: Bulk lookup with individual queries (N+1 pattern)
            start_time = time.time()
            for tmdb_id in tmdb_id_list[:20]:
                session.query(AnimeMetadata).filter_by(tmdb_id=tmdb_id).first()
            end_time = time.time()

            results["bulk_lookup"] = {
                "queries_executed": 20,
                "total_time_ms": (end_time - start_time) * 1000,
                "avg_time_per_query_ms": (end_time - start_time) * 50,
                "sample_tmdb_ids": tmdb_id_list[:5],
            }

            # Test 3: Bulk IN operation
            start_time = time.time()
            session.query(AnimeMetadata).filter(AnimeMetadata.tmdb_id.in_(tmdb_id_list[:50])).all()
            end_time = time.time()

            results["bulk_in_operation"] = {
                "queries_executed": 1,
                "records_queried": 50,
                "total_time_ms": (end_time - start_time) * 1000,
                "avg_time_per_record_ms": (end_time - start_time) * 20,
                "sample_tmdb_ids": tmdb_id_list[:5],
            }

        return results

    def analyze_file_path_queries(self) -> dict[str, Any]:
        """Analyze performance of queries involving file_path."""
        logger.info("Analyzing file_path query performance...")

        results = {"single_lookup": {}, "bulk_lookup": {}, "bulk_in_operation": {}}

        with self.db_manager.get_session() as session:
            # Get sample file paths for testing
            sample_file_paths = session.query(ParsedFile.file_path).limit(100).all()
            if not sample_file_paths:
                logger.warning("No parsed files found for testing")
                return results

            file_path_list = [row[0] for row in sample_file_paths]

            # Test 1: Single file_path lookup
            start_time = time.time()
            for file_path in file_path_list[:10]:  # Test first 10
                session.query(ParsedFile).filter_by(file_path=file_path).first()
            end_time = time.time()

            results["single_lookup"] = {
                "queries_executed": 10,
                "total_time_ms": (end_time - start_time) * 1000,
                "avg_time_per_query_ms": (end_time - start_time) * 100,
                "sample_file_paths": file_path_list[:3],  # Show first 3 for brevity
            }

            # Test 2: Bulk lookup with individual queries (N+1 pattern)
            start_time = time.time()
            for file_path in file_path_list[:20]:
                session.query(ParsedFile).filter_by(file_path=file_path).first()
            end_time = time.time()

            results["bulk_lookup"] = {
                "queries_executed": 20,
                "total_time_ms": (end_time - start_time) * 1000,
                "avg_time_per_query_ms": (end_time - start_time) * 50,
                "sample_file_paths": file_path_list[:3],
            }

            # Test 3: Bulk IN operation
            start_time = time.time()
            session.query(ParsedFile).filter(ParsedFile.file_path.in_(file_path_list[:50])).all()
            end_time = time.time()

            results["bulk_in_operation"] = {
                "queries_executed": 1,
                "records_queried": 50,
                "total_time_ms": (end_time - start_time) * 1000,
                "avg_time_per_record_ms": (end_time - start_time) * 20,
                "sample_file_paths": file_path_list[:3],
            }

        return results

    def analyze_updated_at_queries(self) -> dict[str, Any]:
        """Analyze performance of queries involving updated_at (AnimeMetadata)."""
        logger.info("Analyzing updated_at query performance...")

        results = {
            "order_by_updated_at": {},
            "filter_by_updated_at": {},
            "incremental_sync_pattern": {},
        }

        with self.db_manager.get_session() as session:
            # Test 1: ORDER BY updated_at
            start_time = time.time()
            session.query(AnimeMetadata).order_by(AnimeMetadata.updated_at).limit(100).all()
            end_time = time.time()

            results["order_by_updated_at"] = {
                "queries_executed": 1,
                "records_queried": 100,
                "total_time_ms": (end_time - start_time) * 1000,
                "avg_time_per_record_ms": (end_time - start_time) * 10,
            }

            # Test 2: Filter by updated_at (simulating incremental sync)
            # Get a recent timestamp for filtering
            recent_timestamp = (
                session.query(AnimeMetadata.updated_at)
                .order_by(AnimeMetadata.updated_at.desc())
                .first()
            )

            if recent_timestamp:
                start_time = time.time()
                session.query(AnimeMetadata).filter(
                    AnimeMetadata.updated_at >= recent_timestamp[0]
                ).all()
                end_time = time.time()

                results["filter_by_updated_at"] = {
                    "queries_executed": 1,
                    "filter_timestamp": recent_timestamp[0].isoformat(),
                    "total_time_ms": (end_time - start_time) * 1000,
                }

            # Test 3: Incremental sync pattern (ORDER BY + LIMIT)
            start_time = time.time()
            session.query(AnimeMetadata).order_by(
                AnimeMetadata.updated_at, AnimeMetadata.version
            ).limit(50).all()
            end_time = time.time()

            results["incremental_sync_pattern"] = {
                "queries_executed": 1,
                "records_queried": 50,
                "total_time_ms": (end_time - start_time) * 1000,
                "avg_time_per_record_ms": (end_time - start_time) * 20,
            }

        return results

    def analyze_db_updated_at_queries(self) -> dict[str, Any]:
        """Analyze performance of queries involving db_updated_at (ParsedFile)."""
        logger.info("Analyzing db_updated_at query performance...")

        results = {
            "order_by_db_updated_at": {},
            "filter_by_db_updated_at": {},
            "incremental_sync_pattern": {},
        }

        with self.db_manager.get_session() as session:
            # Test 1: ORDER BY db_updated_at
            start_time = time.time()
            session.query(ParsedFile).order_by(ParsedFile.db_updated_at).limit(100).all()
            end_time = time.time()

            results["order_by_db_updated_at"] = {
                "queries_executed": 1,
                "records_queried": 100,
                "total_time_ms": (end_time - start_time) * 1000,
                "avg_time_per_record_ms": (end_time - start_time) * 10,
            }

            # Test 2: Filter by db_updated_at (simulating incremental sync)
            # Get a recent timestamp for filtering
            recent_timestamp = (
                session.query(ParsedFile.db_updated_at)
                .order_by(ParsedFile.db_updated_at.desc())
                .first()
            )

            if recent_timestamp:
                start_time = time.time()
                session.query(ParsedFile).filter(
                    ParsedFile.db_updated_at >= recent_timestamp[0]
                ).all()
                end_time = time.time()

                results["filter_by_db_updated_at"] = {
                    "queries_executed": 1,
                    "filter_timestamp": recent_timestamp[0].isoformat(),
                    "total_time_ms": (end_time - start_time) * 1000,
                }

            # Test 3: Incremental sync pattern (ORDER BY + LIMIT)
            start_time = time.time()
            session.query(ParsedFile).order_by(ParsedFile.db_updated_at, ParsedFile.version).limit(
                50
            ).all()
            end_time = time.time()

            results["incremental_sync_pattern"] = {
                "queries_executed": 1,
                "records_queried": 50,
                "total_time_ms": (end_time - start_time) * 1000,
                "avg_time_per_record_ms": (end_time - start_time) * 20,
            }

        return results

    def get_explain_analyze_results(self) -> dict[str, Any]:
        """Get EXPLAIN ANALYZE results for key queries."""
        logger.info("Getting EXPLAIN ANALYZE results...")

        results = {}

        with self.db_manager.get_session() as session:
            # Test queries with EXPLAIN ANALYZE
            queries = {
                "tmdb_id_lookup": """
                    EXPLAIN QUERY PLAN
                    SELECT * FROM anime_metadata
                    WHERE tmdb_id = 1
                """,
                "file_path_lookup": """
                    EXPLAIN QUERY PLAN
                    SELECT * FROM parsed_files
                    WHERE file_path = 'test_path.mkv'
                """,
                "updated_at_order": """
                    EXPLAIN QUERY PLAN
                    SELECT * FROM anime_metadata
                    ORDER BY updated_at
                    LIMIT 10
                """,
                "db_updated_at_order": """
                    EXPLAIN QUERY PLAN
                    SELECT * FROM parsed_files
                    ORDER BY db_updated_at
                    LIMIT 10
                """,
            }

            for query_name, query_sql in queries.items():
                try:
                    result = session.execute(text(query_sql)).fetchall()
                    results[query_name] = {
                        "query": query_sql.strip(),
                        "explain_result": [row[0] for row in result],
                    }
                except Exception as e:
                    logger.warning(f"Failed to execute {query_name}: {e}")
                    results[query_name] = {"query": query_sql.strip(), "error": str(e)}

        return results

    def get_database_stats(self) -> dict[str, Any]:
        """Get database statistics for context."""
        logger.info("Getting database statistics...")

        with self.db_manager.get_session() as session:
            stats = {}

            # Get table row counts
            anime_count = session.query(AnimeMetadata).count()
            file_count = session.query(ParsedFile).count()

            stats["table_stats"] = {
                "anime_metadata_count": anime_count,
                "parsed_files_count": file_count,
            }

            # Get index information (SQLite specific)
            try:
                index_query = """
                    SELECT
                        name,
                        tbl_name,
                        sql
                    FROM sqlite_master
                    WHERE type = 'index'
                    AND tbl_name IN ('anime_metadata', 'parsed_files')
                    ORDER BY tbl_name, name
                """
                index_results = session.execute(text(index_query)).fetchall()
                stats["current_indexes"] = [
                    {"table": row[1], "index": row[0], "definition": row[2]}
                    for row in index_results
                ]
            except Exception as e:
                logger.warning(f"Could not get index information: {e}")
                stats["current_indexes"] = []

        return stats

    def run_full_analysis(self) -> dict[str, Any]:
        """Run complete performance analysis."""
        logger.info("Starting full query performance analysis...")

        start_time = time.time()

        analysis_results = {
            "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "database_stats": self.get_database_stats(),
            "tmdb_id_queries": self.analyze_tmdb_id_queries(),
            "file_path_queries": self.analyze_file_path_queries(),
            "updated_at_queries": self.analyze_updated_at_queries(),
            "db_updated_at_queries": self.analyze_db_updated_at_queries(),
            "explain_analyze_results": self.get_explain_analyze_results(),
        }

        end_time = time.time()
        analysis_results["analysis_duration_seconds"] = end_time - start_time

        logger.info(f"Analysis completed in {end_time - start_time:.2f} seconds")

        return analysis_results


def main():
    """Main function to run the query performance analysis."""
    parser = argparse.ArgumentParser(description="Analyze database query performance")
    parser.add_argument("--database-url", help="Database URL (optional, uses default from config)")
    parser.add_argument(
        "--output-file", help="Output file for results (default: query_performance_baseline.json)"
    )

    args = parser.parse_args()

    try:
        # Initialize database manager
        db_manager = DatabaseManager()

        # Run analysis
        analyzer = QueryPerformanceAnalyzer(db_manager)
        results = analyzer.run_full_analysis()

        # Save results
        output_file = args.output_file or "query_performance_baseline.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Results saved to {output_file}")

        # Print summary
        print("\n" + "=" * 80)
        print("QUERY PERFORMANCE ANALYSIS SUMMARY")
        print("=" * 80)

        db_stats = results["database_stats"]["table_stats"]
        print(
            f"Database Size: {db_stats['anime_metadata_count']} anime records, {db_stats['parsed_files_count']} file records"
        )

        # Highlight slow queries
        slow_queries = []
        for query_type, query_results in results.items():
            if isinstance(query_results, dict) and "total_time_ms" in query_results:
                if query_results["total_time_ms"] > 100:  # > 100ms
                    slow_queries.append((query_type, query_results["total_time_ms"]))

        if slow_queries:
            print("\nSlow Queries (>100ms):")
            for query_type, time_ms in slow_queries:
                print(f"  - {query_type}: {time_ms:.2f}ms")
        else:
            print("\nNo queries exceeded 100ms threshold")

        print(f"\nFull results available in: {output_file}")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
