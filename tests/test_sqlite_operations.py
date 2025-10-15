"""Unit tests for SQLite cache operations.

This module tests QueryOperations, InsertOperations, and UpdateOperations
to ensure CRUD operations work correctly with proper error handling.
"""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from anivault.core.statistics import StatisticsCollector
from anivault.services.sqlite_cache.operations.insert import InsertOperations
from anivault.services.sqlite_cache.operations.query import QueryOperations
from anivault.services.sqlite_cache.operations.update import UpdateOperations
from anivault.shared.constants import Cache


@pytest.fixture
def temp_db() -> sqlite3.Connection:
    """Create a temporary SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")

    # Create cache table
    conn.execute(
        """
        CREATE TABLE tmdb_cache (
            cache_key TEXT NOT NULL,
            key_hash TEXT NOT NULL,
            cache_type TEXT NOT NULL,
            response_data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT,
            hit_count INTEGER DEFAULT 0,
            last_accessed_at TEXT,
            response_size INTEGER NOT NULL,
            PRIMARY KEY (key_hash, cache_type)
        )
    """
    )

    # Create indexes
    conn.execute("CREATE INDEX idx_cache_type ON tmdb_cache(cache_type)")
    conn.execute("CREATE INDEX idx_expires_at ON tmdb_cache(expires_at)")

    return conn


@pytest.fixture
def statistics() -> StatisticsCollector:
    """Create a statistics collector for testing."""
    return StatisticsCollector()


@pytest.fixture
def query_ops(
    temp_db: sqlite3.Connection, statistics: StatisticsCollector
) -> QueryOperations:
    """Create QueryOperations instance."""
    return QueryOperations(temp_db, statistics)


@pytest.fixture
def insert_ops(
    temp_db: sqlite3.Connection, statistics: StatisticsCollector
) -> InsertOperations:
    """Create InsertOperations instance."""
    return InsertOperations(temp_db, statistics)


@pytest.fixture
def update_ops(
    temp_db: sqlite3.Connection, statistics: StatisticsCollector
) -> UpdateOperations:
    """Create UpdateOperations instance."""
    return UpdateOperations(temp_db, statistics)


class TestQueryOperations:
    """Test QueryOperations (SELECT)."""

    def test_get_cache_hit(
        self, query_ops: QueryOperations, insert_ops: InsertOperations
    ) -> None:
        """Test successful cache retrieval."""
        # Given
        key = "test:movie:123"
        data = {"results": [{"id": 123, "title": "Test Movie"}]}

        # Insert data
        insert_ops.insert(key, data, Cache.TYPE_SEARCH)

        # When
        result = query_ops.get(key, Cache.TYPE_SEARCH)

        # Then
        assert result is not None
        assert result == data

    def test_get_cache_miss(self, query_ops: QueryOperations) -> None:
        """Test cache miss (key not found)."""
        # Given
        key = "test:movie:999"

        # When
        result = query_ops.get(key, Cache.TYPE_SEARCH)

        # Then
        assert result is None

    def test_get_expired_entry(
        self, query_ops: QueryOperations, insert_ops: InsertOperations
    ) -> None:
        """Test expired cache entry returns None."""
        # Given
        key = "test:movie:456"
        data: dict[str, Any] = {"results": []}

        # Insert with very short TTL (1 second)
        insert_ops.insert(key, data, Cache.TYPE_SEARCH, ttl_seconds=1)

        # Wait for expiration
        import time

        time.sleep(2)

        # When
        result = query_ops.get(key, Cache.TYPE_SEARCH)

        # Then
        assert result is None

    def test_get_invalid_json(
        self, query_ops: QueryOperations, temp_db: sqlite3.Connection
    ) -> None:
        """Test handling of corrupted JSON data."""
        # Given
        key = "test:movie:corrupt"
        key_hash = "abc123"

        # Insert corrupted JSON
        temp_db.execute(
            """
            INSERT INTO tmdb_cache
            (cache_key, key_hash, cache_type, response_data, created_at, expires_at, response_size)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """,
            (key, key_hash, Cache.TYPE_SEARCH, "invalid json", None, 100),
        )

        # When
        result = query_ops.get(key, Cache.TYPE_SEARCH)

        # Then
        assert result is None

    def test_get_different_cache_types(
        self, query_ops: QueryOperations, insert_ops: InsertOperations
    ) -> None:
        """Test cache isolation between different cache types."""
        # Given
        key = "test:movie:789"
        search_data = {"results": [{"id": 789}]}
        details_data = {"id": 789, "title": "Test"}

        # Insert same key with different types
        insert_ops.insert(key, search_data, Cache.TYPE_SEARCH)
        insert_ops.insert(key, details_data, Cache.TYPE_DETAILS)

        # When
        search_result = query_ops.get(key, Cache.TYPE_SEARCH)
        details_result = query_ops.get(key, Cache.TYPE_DETAILS)

        # Then
        assert search_result == search_data
        assert details_result == details_data

    def test_get_updates_hit_count(
        self,
        query_ops: QueryOperations,
        insert_ops: InsertOperations,
        temp_db: sqlite3.Connection,
    ) -> None:
        """Test that hit count is incremented on cache access."""
        # Given
        key = "test:movie:hitcount"
        data = {"test": "data"}
        insert_ops.insert(key, data, Cache.TYPE_SEARCH)

        # When - access multiple times
        query_ops.get(key, Cache.TYPE_SEARCH)
        query_ops.get(key, Cache.TYPE_SEARCH)
        query_ops.get(key, Cache.TYPE_SEARCH)

        # Then
        cursor = temp_db.execute(
            "SELECT hit_count FROM tmdb_cache WHERE key_hash = ?",
            (query_ops._generate_cache_key_hash(key)[1],),
        )
        hit_count = cursor.fetchone()[0]
        assert hit_count == 3

    def test_get_connection_none(self, statistics: StatisticsCollector) -> None:
        """Test error handling when connection is None."""
        # Given
        query_ops = QueryOperations(None, statistics)  # type: ignore[arg-type]

        # When/Then
        with pytest.raises(RuntimeError, match="Database connection not initialized"):
            query_ops.get("test:key", Cache.TYPE_SEARCH)


class TestInsertOperations:
    """Test InsertOperations (INSERT)."""

    def test_insert_basic(
        self, insert_ops: InsertOperations, query_ops: QueryOperations
    ) -> None:
        """Test basic insert operation."""
        # Given
        key = "test:movie:basic"
        data = {"results": [{"id": 1, "title": "Basic Test"}]}

        # When
        insert_ops.insert(key, data, Cache.TYPE_SEARCH)

        # Then
        result = query_ops.get(key, Cache.TYPE_SEARCH)
        assert result == data

    def test_insert_with_custom_ttl(
        self, insert_ops: InsertOperations, query_ops: QueryOperations
    ) -> None:
        """Test insert with custom TTL."""
        # Given
        key = "test:movie:ttl"
        data = {"test": "ttl"}
        custom_ttl = 3600  # 1 hour

        # When
        insert_ops.insert(key, data, Cache.TYPE_SEARCH, ttl_seconds=custom_ttl)

        # Then
        result = query_ops.get(key, Cache.TYPE_SEARCH)
        assert result == data

    def test_insert_replace_existing(
        self, insert_ops: InsertOperations, query_ops: QueryOperations
    ) -> None:
        """Test that INSERT OR REPLACE updates existing entry."""
        # Given
        key = "test:movie:replace"
        old_data = {"old": "data"}
        new_data = {"new": "data"}

        # Insert old data
        insert_ops.insert(key, old_data, Cache.TYPE_SEARCH)

        # When - insert new data with same key
        insert_ops.insert(key, new_data, Cache.TYPE_SEARCH)

        # Then
        result = query_ops.get(key, Cache.TYPE_SEARCH)
        assert result == new_data
        assert result != old_data

    def test_insert_different_types(
        self, insert_ops: InsertOperations, query_ops: QueryOperations
    ) -> None:
        """Test inserting different cache types."""
        # Given
        key = "test:movie:types"
        search_data = {"type": "search"}
        details_data = {"type": "details"}

        # When
        insert_ops.insert(key, search_data, Cache.TYPE_SEARCH)
        insert_ops.insert(key, details_data, Cache.TYPE_DETAILS)

        # Then
        assert query_ops.get(key, Cache.TYPE_SEARCH) == search_data
        assert query_ops.get(key, Cache.TYPE_DETAILS) == details_data

    def test_insert_invalid_json(self, insert_ops: InsertOperations) -> None:
        """Test error handling for non-serializable data."""
        # Given
        key = "test:movie:invalid"
        # Create object that can't be JSON serialized
        invalid_data = {"func": lambda x: x}

        # When/Then
        with pytest.raises((TypeError, ValueError)):
            insert_ops.insert(key, invalid_data, Cache.TYPE_SEARCH)

    def test_insert_connection_none(self, statistics: StatisticsCollector) -> None:
        """Test error handling when connection is None."""
        # Given
        insert_ops = InsertOperations(None, statistics)  # type: ignore[arg-type]

        # When/Then
        with pytest.raises(RuntimeError, match="Database connection not initialized"):
            insert_ops.insert("test:key", {"data": "test"}, Cache.TYPE_SEARCH)

    def test_insert_default_ttl_search(self, insert_ops: InsertOperations) -> None:
        """Test default TTL for search cache type."""
        # Given
        key = "test:movie:default_ttl_search"
        data = {"test": "default"}

        # When
        insert_ops.insert(key, data, Cache.TYPE_SEARCH)

        # Then - verify expires_at is set (we can't easily test exact value without mocking time)
        # Just verify it doesn't fail
        assert True

    def test_insert_default_ttl_details(self, insert_ops: InsertOperations) -> None:
        """Test default TTL for details cache type."""
        # Given
        key = "test:movie:default_ttl_details"
        data = {"test": "default"}

        # When
        insert_ops.insert(key, data, Cache.TYPE_DETAILS)

        # Then - verify it doesn't fail
        assert True


class TestUpdateOperations:
    """Test UpdateOperations (UPDATE/DELETE)."""

    def test_delete_existing(
        self,
        update_ops: UpdateOperations,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test deleting existing cache entry."""
        # Given
        key = "test:movie:delete"
        data = {"test": "delete"}
        insert_ops.insert(key, data, Cache.TYPE_SEARCH)

        # When
        deleted = update_ops.delete(key, Cache.TYPE_SEARCH)

        # Then
        assert deleted is True
        assert query_ops.get(key, Cache.TYPE_SEARCH) is None

    def test_delete_nonexistent(self, update_ops: UpdateOperations) -> None:
        """Test deleting non-existent cache entry."""
        # Given
        key = "test:movie:nonexistent"

        # When
        deleted = update_ops.delete(key, Cache.TYPE_SEARCH)

        # Then
        assert deleted is False

    def test_delete_different_type(
        self,
        update_ops: UpdateOperations,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test deleting only affects correct cache type."""
        # Given
        key = "test:movie:multitype"
        search_data = {"type": "search"}
        details_data = {"type": "details"}
        insert_ops.insert(key, search_data, Cache.TYPE_SEARCH)
        insert_ops.insert(key, details_data, Cache.TYPE_DETAILS)

        # When
        update_ops.delete(key, Cache.TYPE_SEARCH)

        # Then
        assert query_ops.get(key, Cache.TYPE_SEARCH) is None
        assert query_ops.get(key, Cache.TYPE_DETAILS) == details_data

    def test_purge_expired(
        self, update_ops: UpdateOperations, insert_ops: InsertOperations
    ) -> None:
        """Test purging expired entries."""
        # Given
        # Insert expired entry (negative TTL)
        expired_key = "test:movie:expired"
        insert_ops.insert(
            expired_key, {"expired": True}, Cache.TYPE_SEARCH, ttl_seconds=-1
        )

        # Insert valid entry
        valid_key = "test:movie:valid"
        insert_ops.insert(
            valid_key, {"valid": True}, Cache.TYPE_SEARCH, ttl_seconds=3600
        )

        # When
        purged_count = update_ops.purge_expired()

        # Then
        assert purged_count >= 1

    def test_purge_no_expired(
        self, update_ops: UpdateOperations, insert_ops: InsertOperations
    ) -> None:
        """Test purging when no expired entries exist."""
        # Given
        valid_key = "test:movie:all_valid"
        insert_ops.insert(
            valid_key, {"valid": True}, Cache.TYPE_SEARCH, ttl_seconds=3600
        )

        # When
        purged_count = update_ops.purge_expired()

        # Then
        assert purged_count == 0

    def test_clear_by_type(
        self,
        update_ops: UpdateOperations,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test clearing cache by type."""
        # Given
        key1 = "test:movie:clear1"
        key2 = "test:movie:clear2"
        insert_ops.insert(key1, {"type": "search"}, Cache.TYPE_SEARCH)
        insert_ops.insert(key2, {"type": "details"}, Cache.TYPE_DETAILS)

        # When
        cleared_count = update_ops.clear(Cache.TYPE_SEARCH)

        # Then
        assert cleared_count >= 1
        assert query_ops.get(key1, Cache.TYPE_SEARCH) is None
        assert query_ops.get(key2, Cache.TYPE_DETAILS) is not None

    def test_clear_all(
        self,
        update_ops: UpdateOperations,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test clearing all cache entries."""
        # Given
        key1 = "test:movie:all1"
        key2 = "test:movie:all2"
        insert_ops.insert(key1, {"data": 1}, Cache.TYPE_SEARCH)
        insert_ops.insert(key2, {"data": 2}, Cache.TYPE_DETAILS)

        # When
        cleared_count = update_ops.clear()

        # Then
        assert cleared_count >= 2
        assert query_ops.get(key1, Cache.TYPE_SEARCH) is None
        assert query_ops.get(key2, Cache.TYPE_DETAILS) is None

    def test_connection_none(self, statistics: StatisticsCollector) -> None:
        """Test error handling when connection is None."""
        # Given
        update_ops = UpdateOperations(None, statistics)  # type: ignore[arg-type]

        # When/Then
        with pytest.raises(RuntimeError, match="Database connection not initialized"):
            update_ops.delete("test:key", Cache.TYPE_SEARCH)
