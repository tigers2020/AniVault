"""Tests for cache adapter implementation."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from anivault.core.matching.services.cache_adapter import (
    CacheAdapterProtocol,
    SQLiteCacheAdapter,
)
from anivault.services.sqlite_cache_db import SQLiteCacheDB


class TestCacheAdapterProtocol:
    """Test suite for CacheAdapterProtocol interface."""

    def test_protocol_defines_get_method(self) -> None:
        """Protocol should define get method signature."""
        assert hasattr(CacheAdapterProtocol, "get")

    def test_protocol_defines_set_method(self) -> None:
        """Protocol should define set method signature."""
        assert hasattr(CacheAdapterProtocol, "set")


class TestSQLiteCacheAdapter:
    """Test suite for SQLiteCacheAdapter implementation."""

    @pytest.fixture
    def temp_db_path(self, tmp_path: Path) -> Path:
        """Create temporary database path."""
        return tmp_path / "test_cache.db"

    @pytest.fixture
    def cache_db(self, temp_db_path: Path) -> SQLiteCacheDB:
        """Create SQLiteCacheDB instance for testing."""
        db = SQLiteCacheDB(temp_db_path)
        yield db
        db.close()

    @pytest.fixture
    def adapter(self, cache_db: SQLiteCacheDB) -> SQLiteCacheAdapter:
        """Create SQLiteCacheAdapter instance for testing."""
        return SQLiteCacheAdapter(cache_db)

    def test_adapter_initialization(self, cache_db: SQLiteCacheDB) -> None:
        """Test adapter initialization with backend."""
        adapter = SQLiteCacheAdapter(cache_db)

        assert adapter.backend is cache_db
        assert adapter.MAX_KEY_LENGTH == 256

    def test_get_returns_none_for_missing_key(
        self, adapter: SQLiteCacheAdapter
    ) -> None:
        """Test get returns None for non-existent cache key."""
        result = adapter.get("nonexistent:key", "search")

        assert result is None

    def test_set_and_get_round_trip(self, adapter: SQLiteCacheAdapter) -> None:
        """Test setting and retrieving cache data."""
        test_key = "search:movie:test"
        test_data = {"results": [{"id": 1, "title": "Test Movie"}]}

        # Set data
        adapter.set(test_key, test_data, "search")

        # Get data
        result = adapter.get(test_key, "search")

        assert result is not None
        assert result == test_data
        assert result["results"][0]["title"] == "Test Movie"

    def test_set_with_ttl(self, adapter: SQLiteCacheAdapter) -> None:
        """Test setting cache data with TTL."""
        test_key = "search:movie:ttl_test"
        test_data = {"results": []}

        # Should not raise exception
        adapter.set(test_key, test_data, "search", ttl_seconds=3600)

        # Verify data is stored
        result = adapter.get(test_key, "search")
        assert result == test_data

    def test_validate_key_short_key_unchanged(
        self, adapter: SQLiteCacheAdapter
    ) -> None:
        """Test key validation with short key (within limit)."""
        short_key = "search:movie:short"

        validated = adapter._validate_key(short_key)

        assert validated == short_key

    def test_validate_key_long_key_hashed(self, adapter: SQLiteCacheAdapter) -> None:
        """Test key validation with overly long key (hashed)."""
        long_key = "a" * 300  # Exceeds MAX_KEY_LENGTH (256)

        validated = adapter._validate_key(long_key)

        # Should be SHA-256 hash (64 hex characters)
        assert len(validated) == 64
        assert validated != long_key
        assert all(c in "0123456789abcdef" for c in validated)

    def test_validate_key_exactly_max_length(self, adapter: SQLiteCacheAdapter) -> None:
        """Test key validation with key exactly at MAX_KEY_LENGTH."""
        exact_key = "a" * 256

        validated = adapter._validate_key(exact_key)

        # Should pass through unchanged (not exceeding limit)
        assert validated == exact_key

    def test_get_with_exception_returns_none(self, cache_db: SQLiteCacheDB) -> None:
        """Test graceful degradation when get operation raises exception."""
        adapter = SQLiteCacheAdapter(cache_db)

        # Mock backend.get to raise exception
        with patch.object(
            cache_db, "get", side_effect=sqlite3.OperationalError("DB error")
        ):
            result = adapter.get("test:key", "search")

        # Should return None instead of raising
        assert result is None

    def test_set_with_exception_does_not_raise(self, cache_db: SQLiteCacheDB) -> None:
        """Test graceful degradation when set operation raises exception."""
        adapter = SQLiteCacheAdapter(cache_db)

        # Mock backend.set_cache to raise exception
        with patch.object(
            cache_db, "set_cache", side_effect=sqlite3.OperationalError("DB error")
        ):
            # Should not raise exception
            adapter.set("test:key", {"data": "test"}, "search")

        # If we reach here, test passed (no exception raised)

    def test_get_different_cache_types(self, adapter: SQLiteCacheAdapter) -> None:
        """Test get/set with different cache types."""
        search_data = {"results": [{"id": 1}]}
        details_data = {"title": "Test", "year": 2024}

        # Set data with different cache types
        adapter.set("key1", search_data, "search")
        adapter.set("key2", details_data, "details")

        # Get data with correct cache types
        search_result = adapter.get("key1", "search")
        details_result = adapter.get("key2", "details")

        assert search_result == search_data
        assert details_result == details_data

        # Wrong cache type should return None
        wrong_type_result = adapter.get("key1", "details")
        assert wrong_type_result is None

    def test_delete_removes_cached_data(self, adapter: SQLiteCacheAdapter) -> None:
        """Test delete removes cached data."""
        test_key = "search:movie:delete_test"
        test_data = {"results": [{"id": 1}]}

        # Set data first
        adapter.set(test_key, test_data, "search")

        # Verify it exists
        assert adapter.get(test_key, "search") is not None

        # Delete
        adapter.delete(test_key, "search")

        # Verify it's gone
        assert adapter.get(test_key, "search") is None

    def test_delete_with_exception_does_not_raise(
        self, cache_db: SQLiteCacheDB
    ) -> None:
        """Test graceful degradation when delete operation raises exception."""
        adapter = SQLiteCacheAdapter(cache_db)

        # Mock backend.delete to raise exception
        with patch.object(
            cache_db, "delete", side_effect=sqlite3.OperationalError("DB error")
        ):
            # Should not raise exception
            adapter.delete("test:key", "search")

        # If we reach here, test passed (no exception raised)

    def test_adapter_conforms_to_protocol(self, adapter: SQLiteCacheAdapter) -> None:
        """Test that SQLiteCacheAdapter conforms to CacheAdapterProtocol."""
        # Static type checking should verify this, but we can check method existence
        assert hasattr(adapter, "get")
        assert hasattr(adapter, "set")
        assert hasattr(adapter, "delete")
        assert callable(adapter.get)
        assert callable(adapter.set)
        assert callable(adapter.delete)

    def test_get_returns_dict_copy_not_reference(
        self, adapter: SQLiteCacheAdapter
    ) -> None:
        """Test that get returns a copy of cached data, not a reference."""
        test_key = "search:movie:copy_test"
        test_data = {"results": [{"id": 1, "mutable": "original"}]}

        # Set data
        adapter.set(test_key, test_data, "search")

        # Get data twice
        result1 = adapter.get(test_key, "search")
        result2 = adapter.get(test_key, "search")

        # Modify first result
        if result1:
            result1["results"][0]["mutable"] = "modified"

        # Second result should be unaffected (not a reference)
        assert result2 is not None
        assert result2["results"][0]["mutable"] == "original"
