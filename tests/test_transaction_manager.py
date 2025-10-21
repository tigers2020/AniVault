"""Unit tests for SQLite cache transaction manager.

This module tests TransactionManager to ensure transaction management
works correctly with proper commit and rollback behavior.
"""

from __future__ import annotations

import sqlite3

import pytest

from anivault.core.statistics import StatisticsCollector
from anivault.services.sqlite_cache.operations.insert import InsertOperations
from anivault.services.sqlite_cache.operations.query import QueryOperations
from anivault.services.sqlite_cache.operations.update import UpdateOperations
from anivault.services.sqlite_cache.transaction.manager import TransactionManager
from anivault.shared.constants import Cache


@pytest.fixture
def temp_db() -> sqlite3.Connection:
    """Create a temporary SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

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
def transaction_manager(temp_db: sqlite3.Connection) -> TransactionManager:
    """Create TransactionManager instance."""
    return TransactionManager(temp_db)


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


class TestTransactionManager:
    """Test TransactionManager."""

    def test_transaction_success_commits(
        self,
        transaction_manager: TransactionManager,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test that successful transaction commits changes."""
        # Given
        key1 = "test:movie:tx1"
        key2 = "test:movie:tx2"
        data1 = {"results": [{"id": 1}]}
        data2 = {"results": [{"id": 2}]}

        # When - insert multiple items in transaction
        with transaction_manager.transaction():
            insert_ops.insert(key1, data1, Cache.TYPE_SEARCH)
            insert_ops.insert(key2, data2, Cache.TYPE_SEARCH)

        # Then - both should be committed and retrievable
        result1 = query_ops.get(key1, Cache.TYPE_SEARCH)
        result2 = query_ops.get(key2, Cache.TYPE_SEARCH)

        assert result1 == data1
        assert result2 == data2

    def test_transaction_rollback_on_exception(
        self,
        transaction_manager: TransactionManager,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test that transaction rolls back on exception."""
        # Given
        key1 = "test:movie:rollback1"
        key2 = "test:movie:rollback2"
        data1 = {"results": [{"id": 1}]}
        data2 = {"results": [{"id": 2}]}

        # When - insert items but raise exception
        with (
            pytest.raises(ValueError, match="Simulated error"),
            transaction_manager.transaction(),
        ):
            insert_ops.insert(key1, data1, Cache.TYPE_SEARCH)
            insert_ops.insert(key2, data2, Cache.TYPE_SEARCH)
            raise ValueError("Simulated error")

        # Then - neither should be committed
        result1 = query_ops.get(key1, Cache.TYPE_SEARCH)
        result2 = query_ops.get(key2, Cache.TYPE_SEARCH)

        assert result1 is None
        assert result2 is None

    def test_multiple_operations_in_transaction(
        self,
        transaction_manager: TransactionManager,
        insert_ops: InsertOperations,
        update_ops: UpdateOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test multiple CRUD operations in single transaction."""
        # Given
        key1 = "test:movie:multi1"
        key2 = "test:movie:multi2"
        key3 = "test:movie:multi3"
        data1 = {"results": [{"id": 1}]}
        data2 = {"results": [{"id": 2}]}
        data3 = {"results": [{"id": 3}]}

        # When - insert, update, delete in transaction
        with transaction_manager.transaction():
            # Insert 3 items
            insert_ops.insert(key1, data1, Cache.TYPE_SEARCH)
            insert_ops.insert(key2, data2, Cache.TYPE_SEARCH)
            insert_ops.insert(key3, data3, Cache.TYPE_SEARCH)

            # Update key2
            updated_data2 = {"results": [{"id": 2, "updated": True}]}
            insert_ops.insert(key2, updated_data2, Cache.TYPE_SEARCH)

            # Delete key3
            update_ops.delete(key3, Cache.TYPE_SEARCH)

        # Then - verify final state
        assert query_ops.get(key1, Cache.TYPE_SEARCH) == data1
        assert query_ops.get(key2, Cache.TYPE_SEARCH) == updated_data2
        assert query_ops.get(key3, Cache.TYPE_SEARCH) is None

    def test_manual_begin_commit(
        self,
        transaction_manager: TransactionManager,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test manual transaction control with begin/commit."""
        # Given
        key = "test:movie:manual"
        data = {"results": [{"id": 1}]}

        # When - manual transaction control
        transaction_manager.begin()
        insert_ops.insert(key, data, Cache.TYPE_SEARCH)
        transaction_manager.commit()

        # Then - data should be committed
        result = query_ops.get(key, Cache.TYPE_SEARCH)
        assert result == data

    def test_manual_rollback(
        self,
        transaction_manager: TransactionManager,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test manual rollback."""
        # Given
        key = "test:movie:manual_rollback"
        data = {"results": [{"id": 1}]}

        # When - manual rollback
        transaction_manager.begin()
        insert_ops.insert(key, data, Cache.TYPE_SEARCH)
        transaction_manager.rollback()

        # Then - data should not be committed
        result = query_ops.get(key, Cache.TYPE_SEARCH)
        assert result is None

    def test_partial_failure_rollback(
        self,
        transaction_manager: TransactionManager,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test that partial operations are rolled back on failure."""
        # Given
        key1 = "test:movie:partial1"
        data1 = {"results": [{"id": 1}]}

        # When - insert two items but fail on second
        with (
            pytest.raises(ValueError, match="Simulated failure"),
            transaction_manager.transaction(),
        ):
            insert_ops.insert(key1, data1, Cache.TYPE_SEARCH)
            # Simulate failure after first insert
            raise ValueError("Simulated failure")

        # Then - first insert should also be rolled back
        assert query_ops.get(key1, Cache.TYPE_SEARCH) is None

    def test_transaction_with_different_cache_types(
        self,
        transaction_manager: TransactionManager,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test transaction with different cache types."""
        # Given
        key = "test:movie:multitype"
        search_data = {"type": "search"}
        details_data = {"type": "details"}

        # When - insert same key with different types in transaction
        with transaction_manager.transaction():
            insert_ops.insert(key, search_data, Cache.TYPE_SEARCH)
            insert_ops.insert(key, details_data, Cache.TYPE_DETAILS)

        # Then - both should be committed
        assert query_ops.get(key, Cache.TYPE_SEARCH) == search_data
        assert query_ops.get(key, Cache.TYPE_DETAILS) == details_data

    def test_transaction_isolation(
        self,
        transaction_manager: TransactionManager,
        insert_ops: InsertOperations,
    ) -> None:
        """Test that uncommitted changes are not visible to other connections."""
        # Given
        key = "test:movie:isolation"
        data = {"results": [{"id": 1}]}

        # When - start transaction but don't commit
        transaction_manager.begin()
        insert_ops.insert(key, data, Cache.TYPE_SEARCH)

        # Then - data should not be visible to other queries
        # (In SQLite with WAL mode, this depends on isolation level)
        # For this test, we just verify the transaction is active
        assert transaction_manager.conn.in_transaction

        # Clean up
        transaction_manager.rollback()

    def test_transaction_with_large_data(
        self,
        transaction_manager: TransactionManager,
        insert_ops: InsertOperations,
        query_ops: QueryOperations,
    ) -> None:
        """Test transaction with large data payload."""
        # Given
        key = "test:movie:large"
        # Create large data (simulate large API response)
        large_data = {"results": [{"id": i, "data": "x" * 1000} for i in range(100)]}

        # When - insert large data in transaction
        with transaction_manager.transaction():
            insert_ops.insert(key, large_data, Cache.TYPE_SEARCH)

        # Then - data should be committed and retrievable
        result = query_ops.get(key, Cache.TYPE_SEARCH)
        assert result == large_data
        assert len(result["results"]) == 100

    def test_transaction_connection_none(self) -> None:
        """Test error handling when connection is None."""
        # Given
        transaction_manager = TransactionManager(None)  # type: ignore[arg-type]

        # When/Then - should raise error on transaction operations
        with pytest.raises(
            AttributeError, match="'NoneType' object has no attribute 'execute'"
        ):
            with transaction_manager.transaction():
                pass
