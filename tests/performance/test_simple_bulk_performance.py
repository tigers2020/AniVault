"""Simple bulk update performance test without async dependencies."""

import logging
import time
from typing import Any, Dict, List

import pytest

from src.core.database import DatabaseManager
from src.core.services.bulk_update_task import ConcreteBulkUpdateTask

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimplePerformanceTest:
    """Simple performance test for bulk update operations."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def create_test_data(self, size: int, base_id: int = 10000) -> List[Dict]:
        """Create test data for performance testing."""
        test_updates = []
        for i in range(size):
            test_updates.append({
                "tmdb_id": base_id + i,
                "status": "processed",
                "title": f"Test Anime {i}"
            })
        return test_updates

    def setup_test_data(self, updates: List[Dict]) -> None:
        """Setup test data in database before testing."""
        logger.info(f"Setting up {len(updates)} test records...")

        # Create test records first
        for update in updates:
            # Insert new record
            session = self.db_manager.get_session()
            try:
                from src.core.database import AnimeMetadata
                from datetime import datetime, timezone

                anime_record = AnimeMetadata(
                    tmdb_id=update["tmdb_id"],
                    title=update["title"],
                    status="pending",  # Initial status
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(anime_record)
                session.commit()
            finally:
                session.close()

    def test_bulk_update_performance(self, updates: List[Dict]) -> Dict[str, Any]:
        """Test bulk update performance."""
        logger.info(f"Testing bulk update with {len(updates)} records...")

        # Setup test data first
        self.setup_test_data(updates)

        start_time = time.time()

        bulk_task = ConcreteBulkUpdateTask(
            update_type="anime_metadata",
            updates=updates,
            db_manager=self.db_manager
        )

        updated_count = bulk_task.execute()

        end_time = time.time()
        execution_time = end_time - start_time

        logger.info(f"Updated {updated_count} records in {execution_time:.3f}s")

        return {
            "records_updated": updated_count,
            "execution_time_s": execution_time,
            "records_per_second": len(updates) / execution_time if execution_time > 0 else 0
        }


def test_simple_bulk_update_performance():
    """Test bulk update performance with simple synchronous test."""
    # Initialize database manager
    db_manager = DatabaseManager("sqlite:///:memory:")

    try:
        # Create performance test instance
        perf_test = SimplePerformanceTest(db_manager)

        # Test different sizes
        test_sizes = [100, 500, 1000]
        results = {}

        for i, size in enumerate(test_sizes):
            logger.info(f"\nTesting with {size} records...")

            # Create test data with unique base ID for each test
            test_updates = perf_test.create_test_data(size, base_id=10000 + i * 10000)

            # Run performance test
            result = perf_test.test_bulk_update_performance(test_updates)
            results[size] = result

            # Log results
            logger.info(f"Results for {size} records:")
            logger.info(f"  Execution time: {result['execution_time_s']:.3f}s")
            logger.info(f"  Records per second: {result['records_per_second']:.1f}")

        # Assert performance thresholds
        for size, result in results.items():
            assert result['records_per_second'] > 100, f"Expected >100 records/sec for {size} records, got {result['records_per_second']:.1f}"

        logger.info("\n✅ Simple bulk update performance test passed!")

        return results

    finally:
        # Cleanup
        if hasattr(db_manager, 'close'):
            db_manager.close()


if __name__ == "__main__":
    # Run test directly
    test_simple_bulk_update_performance()
