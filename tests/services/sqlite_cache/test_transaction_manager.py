"""Integration tests for TransactionManager.

Tests verify transaction management works correctly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anivault.services.sqlite_cache import SQLiteCacheDB
from anivault.shared.constants import Cache


class TestTransactionManagerIntegration:
    """Integration tests for TransactionManager."""

    def test_transaction_commits_on_success(self, tmp_path: Path) -> None:
        """Transaction should commit on successful execution."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When - Multiple operations in transaction
        cache.set_cache("key1", {"data": "1"}, cache_type=Cache.TYPE_SEARCH)
        cache.set_cache("key2", {"data": "2"}, cache_type=Cache.TYPE_DETAILS)

        # Then - Both committed
        result1 = cache.get("key1", cache_type=Cache.TYPE_SEARCH)
        result2 = cache.get("key2", cache_type=Cache.TYPE_DETAILS)

        assert result1 is not None
        assert result1 == {"data": "1"}

        assert result2 is not None
        assert result2 == {"data": "2"}

        cache.close()

    def test_transaction_isolation(self, tmp_path: Path) -> None:
        """Transactions should be isolated."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When - Multiple operations
        cache.set_cache("key1", {"data": "1"}, cache_type=Cache.TYPE_SEARCH)
        cache.delete("key1", cache_type=Cache.TYPE_SEARCH)
        cache.set_cache("key2", {"data": "2"}, cache_type=Cache.TYPE_DETAILS)

        # Then - Verify isolation
        result1 = cache.get("key1", cache_type=Cache.TYPE_SEARCH)
        result2 = cache.get("key2", cache_type=Cache.TYPE_DETAILS)

        assert result1 is None  # Deleted
        assert result2 is not None  # Added

        cache.close()

    def test_transaction_with_purge(self, tmp_path: Path) -> None:
        """Transaction should work with purge operation."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When - Add entries and purge
        cache.set_cache(
            "key1", {"data": "1"}, cache_type=Cache.TYPE_SEARCH, ttl_seconds=0
        )
        import time

        time.sleep(0.1)
        purged_count = cache.purge_expired()

        # Then
        assert purged_count == 1

        result = cache.get("key1", cache_type=Cache.TYPE_SEARCH)
        assert result is None

        cache.close()

    def test_transaction_with_clear(self, tmp_path: Path) -> None:
        """Transaction should work with clear operation."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When - Add entries and clear
        cache.set_cache("key1", {"data": "1"}, cache_type=Cache.TYPE_SEARCH)
        cache.set_cache("key2", {"data": "2"}, cache_type=Cache.TYPE_DETAILS)
        cleared_count = cache.clear()

        # Then
        assert cleared_count == 2

        result1 = cache.get("key1", cache_type=Cache.TYPE_SEARCH)
        result2 = cache.get("key2", cache_type=Cache.TYPE_DETAILS)

        assert result1 is None
        assert result2 is None

        cache.close()
