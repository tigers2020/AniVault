#!/usr/bin/env python3
"""Apply Performance Indexes Script

This script applies the performance optimization indexes to the database.
It reads the SQL script and executes the index creation statements.

Usage:
    python scripts/apply_performance_indexes.py [--dry-run] [--verify-only]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from core.database import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class IndexManager:
    """Manages database index creation and verification."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.sql_script_path = Path(__file__).parent / "create_performance_indexes.sql"

    def read_sql_script(self) -> str:
        """Read the SQL script file."""
        try:
            with open(self.sql_script_path, encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"SQL script not found: {self.sql_script_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading SQL script: {e}")
            raise

    def split_sql_statements(self, sql_content: str) -> list[str]:
        """Split SQL content into individual statements."""
        # Remove comments and split by semicolon
        lines = sql_content.split("\n")
        clean_lines = []

        for line in lines:
            line = line.strip()
            # Skip empty lines and comment-only lines
            if line and not line.startswith("--"):
                clean_lines.append(line)

        # Join lines and split by semicolon
        sql_content_clean = "\n".join(clean_lines)
        statements = [stmt.strip() for stmt in sql_content_clean.split(";") if stmt.strip()]

        return statements

    def apply_indexes(self, dry_run: bool = False) -> dict[str, any]:
        """Apply the performance indexes to the database."""
        logger.info("Reading SQL script...")
        sql_content = self.read_sql_script()

        # Extract only the CREATE INDEX statements
        statements = self.split_sql_statements(sql_content)
        create_index_statements = [
            stmt for stmt in statements if stmt.upper().startswith("CREATE INDEX")
        ]

        logger.info(f"Found {len(create_index_statements)} CREATE INDEX statements")

        results = {
            "total_statements": len(create_index_statements),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "executed_statements": [],
        }

        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            for i, statement in enumerate(create_index_statements, 1):
                logger.info(f"Would execute statement {i}: {statement[:100]}...")
                results["executed_statements"].append(statement)
            results["successful"] = len(create_index_statements)
            return results

        with self.db_manager.get_session() as session:
            for i, statement in enumerate(create_index_statements, 1):
                try:
                    logger.info(f"Executing statement {i}/{len(create_index_statements)}...")
                    logger.debug(f"Statement: {statement}")

                    session.execute(text(statement))
                    session.commit()

                    results["successful"] += 1
                    results["executed_statements"].append(statement)
                    logger.info("✅ Successfully created index")

                except Exception as e:
                    logger.error(f"❌ Failed to execute statement {i}: {e}")
                    results["failed"] += 1
                    results["errors"].append({"statement": statement, "error": str(e)})
                    # Continue with next statement
                    continue

        logger.info(
            f"Index creation completed: {results['successful']} successful, {results['failed']} failed"
        )
        return results

    def verify_indexes(self) -> dict[str, any]:
        """Verify that the performance indexes exist."""
        logger.info("Verifying performance indexes...")

        verification_results = {
            "anime_metadata_indexes": [],
            "parsed_files_indexes": [],
            "missing_indexes": [],
            "expected_indexes": [
                "idx_anime_metadata_updated_at",
                "idx_parsed_files_db_updated_at",
                "idx_anime_metadata_updated_at_version",
                "idx_parsed_files_db_updated_at_version",
            ],
        }

        with self.db_manager.get_session() as session:
            # Check anime_metadata indexes
            anime_query = """
                SELECT name, sql
                FROM sqlite_master
                WHERE type = 'index'
                AND tbl_name = 'anime_metadata'
                AND name LIKE '%updated_at%'
                ORDER BY name
            """

            anime_results = session.execute(text(anime_query)).fetchall()
            verification_results["anime_metadata_indexes"] = [
                {"name": row[0], "definition": row[1]} for row in anime_results
            ]

            # Check parsed_files indexes
            files_query = """
                SELECT name, sql
                FROM sqlite_master
                WHERE type = 'index'
                AND tbl_name = 'parsed_files'
                AND name LIKE '%db_updated_at%'
                ORDER BY name
            """

            files_results = session.execute(text(files_query)).fetchall()
            verification_results["parsed_files_indexes"] = [
                {"name": row[0], "definition": row[1]} for row in files_results
            ]

            # Check for missing indexes
            existing_indexes = [
                idx["name"] for idx in verification_results["anime_metadata_indexes"]
            ]
            existing_indexes.extend(
                [idx["name"] for idx in verification_results["parsed_files_indexes"]]
            )

            for expected_index in verification_results["expected_indexes"]:
                if expected_index not in existing_indexes:
                    verification_results["missing_indexes"].append(expected_index)

        return verification_results

    def test_query_performance(self) -> dict[str, any]:
        """Test query performance with EXPLAIN QUERY PLAN."""
        logger.info("Testing query performance...")

        test_queries = {
            "anime_metadata_order_by_updated_at": """
                EXPLAIN QUERY PLAN
                SELECT * FROM anime_metadata
                ORDER BY updated_at
                LIMIT 10
            """,
            "parsed_files_order_by_db_updated_at": """
                EXPLAIN QUERY PLAN
                SELECT * FROM parsed_files
                ORDER BY db_updated_at
                LIMIT 10
            """,
            "anime_metadata_incremental_sync": """
                EXPLAIN QUERY PLAN
                SELECT * FROM anime_metadata
                ORDER BY updated_at, version
                LIMIT 50
            """,
            "parsed_files_incremental_sync": """
                EXPLAIN QUERY PLAN
                SELECT * FROM parsed_files
                ORDER BY db_updated_at, version
                LIMIT 50
            """,
        }

        performance_results = {}

        with self.db_manager.get_session() as session:
            for query_name, query_sql in test_queries.items():
                try:
                    result = session.execute(text(query_sql)).fetchall()
                    performance_results[query_name] = {
                        "query": query_sql.strip(),
                        "explain_result": [row[0] for row in result],
                        "uses_index": any("INDEX" in str(row[0]) for row in result),
                    }
                except Exception as e:
                    logger.warning(f"Failed to execute {query_name}: {e}")
                    performance_results[query_name] = {
                        "query": query_sql.strip(),
                        "error": str(e),
                        "uses_index": False,
                    }

        return performance_results


def main():
    """Main function to apply performance indexes."""
    parser = argparse.ArgumentParser(description="Apply performance indexes to database")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be executed without making changes"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify existing indexes without creating new ones",
    )
    parser.add_argument(
        "--test-performance",
        action="store_true",
        help="Test query performance after applying indexes",
    )

    args = parser.parse_args()

    try:
        # Initialize database manager and index manager
        db_manager = DatabaseManager()
        index_manager = IndexManager(db_manager)

        if args.verify_only:
            # Only verify existing indexes
            verification_results = index_manager.verify_indexes()

            print("\n" + "=" * 80)
            print("INDEX VERIFICATION RESULTS")
            print("=" * 80)

            print("\nAnime Metadata Indexes:")
            for idx in verification_results["anime_metadata_indexes"]:
                print(f"  ✅ {idx['name']}")

            print("\nParsed Files Indexes:")
            for idx in verification_results["parsed_files_indexes"]:
                print(f"  ✅ {idx['name']}")

            if verification_results["missing_indexes"]:
                print("\nMissing Indexes:")
                for idx in verification_results["missing_indexes"]:
                    print(f"  ❌ {idx}")
            else:
                print("\n✅ All expected indexes are present!")

        else:
            # Apply indexes
            results = index_manager.apply_indexes(dry_run=args.dry_run)

            print("\n" + "=" * 80)
            print("INDEX CREATION RESULTS")
            print("=" * 80)

            if args.dry_run:
                print(f"DRY RUN - Would create {results['successful']} indexes")
                for i, statement in enumerate(results["executed_statements"], 1):
                    print(f"  {i}. {statement[:80]}...")
            else:
                print(f"Successfully created: {results['successful']} indexes")
                print(f"Failed: {results['failed']} indexes")

                if results["errors"]:
                    print("\nErrors:")
                    for error in results["errors"]:
                        print(f"  ❌ {error['error']}")

            # Verify indexes after creation
            if not args.dry_run and results["successful"] > 0:
                verification_results = index_manager.verify_indexes()

                print("\nVerification:")
                if verification_results["missing_indexes"]:
                    print(f"  ⚠️  Still missing: {verification_results['missing_indexes']}")
                else:
                    print("  ✅ All indexes verified successfully!")

            # Test performance if requested
            if args.test_performance and not args.dry_run:
                performance_results = index_manager.test_query_performance()

                print("\nPerformance Test Results:")
                for query_name, result in performance_results.items():
                    status = "✅ Uses Index" if result.get("uses_index") else "❌ No Index"
                    print(f"  {query_name}: {status}")

        print("=" * 80)

    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
