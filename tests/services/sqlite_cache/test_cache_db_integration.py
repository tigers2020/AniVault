"""Integration tests for SQLiteCacheDB Facade.

Tests verify that the Facade correctly delegates to operations.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anivault.services.sqlite_cache import SQLiteCacheDB
from anivault.shared.constants import Cache


class TestSQLiteCacheDBFacadeIntegration:
    """Integration tests for SQLiteCacheDB Facade."""

    def test_facade_delegates_to_query_operations(self, tmp_path: Path) -> None:
        """Facade should delegate get() to QueryOperations."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When
        cache.set_cache(
            "test:key", {"results": [{"id": 123}]}, cache_type=Cache.TYPE_SEARCH
        )
        result = cache.get("test:key", cache_type=Cache.TYPE_SEARCH)

        # Then
        assert result is not None
        assert result == {"results": [{"id": 123}]}

        cache.close()

    def test_facade_delegates_to_insert_operations(self, tmp_path: Path) -> None:
        """Facade should delegate set_cache() to InsertOperations."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When
        cache.set_cache(
            "test:key",
            {"results": [{"id": 456}]},
            cache_type=Cache.TYPE_SEARCH,
            ttl_seconds=3600,
        )

        # Then - Verify data inserted
        result = cache.get("test:key", cache_type=Cache.TYPE_SEARCH)
        assert result is not None
        assert result == {"results": [{"id": 456}]}

        cache.close()

    def test_facade_delegates_to_update_operations(self, tmp_path: Path) -> None:
        """Facade should delegate delete() to UpdateOperations."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When
        cache.set_cache(
            "test:key", {"results": [{"id": 789}]}, cache_type=Cache.TYPE_SEARCH
        )
        deleted = cache.delete("test:key", cache_type=Cache.TYPE_SEARCH)

        # Then
        assert deleted is True

        result = cache.get("test:key", cache_type=Cache.TYPE_SEARCH)
        assert result is None

        cache.close()

    def test_facade_delegates_to_purge_operations(self, tmp_path: Path) -> None:
        """Facade should delegate purge_expired() to UpdateOperations."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When - Add expired entries
        cache.set_cache("expired:key", {"data": "old"}, ttl_seconds=0)
        import time

        time.sleep(0.1)
        purged_count = cache.purge_expired()

        # Then
        assert purged_count == 1

        result = cache.get("expired:key", cache_type=Cache.TYPE_SEARCH)
        assert result is None

        cache.close()

    def test_facade_delegates_to_clear_operations(self, tmp_path: Path) -> None:
        """Facade should delegate clear() to UpdateOperations."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When
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

    def test_facade_get_cache_info(self, tmp_path: Path) -> None:
        """Facade should provide cache info."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When
        cache.set_cache("key1", {"data": "1"}, cache_type=Cache.TYPE_SEARCH)
        cache.set_cache("key2", {"data": "2"}, cache_type=Cache.TYPE_DETAILS)

        info = cache.get_cache_info()

        # Then
        assert info["total_files"] == 2
        assert info["valid_entries"] == 2
        assert info["expired_entries"] == 0

        cache.close()

    def test_facade_close(self, tmp_path: Path) -> None:
        """Facade should close connection properly."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When
        cache.close()

        # Then - Should not raise exception
        assert True

    def test_facade_manual_close(self, tmp_path: Path) -> None:
        """Facade should support manual close."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When
        cache.set_cache("test:key", {"data": "test"}, cache_type=Cache.TYPE_SEARCH)
        result = cache.get("test:key", cache_type=Cache.TYPE_SEARCH)
        cache.close()

        # Then
        assert result is not None
        assert result == {"data": "test"}
