"""Tests for SQLiteCacheDB.

Tests follow the Failure-First pattern:
1. Test failure cases first
2. Test edge cases
3. Test happy path
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.shared.constants import Cache
from anivault.shared.errors import DomainError, InfrastructureError


class TestSQLiteCacheDBInitialization:
    """Test SQLiteCacheDB initialization."""

    def test_init_creates_db_file(self, tmp_path: Path) -> None:
        """Initialize should create database file."""
        # Given
        db_path = tmp_path / "test_cache.db"

        # When
        cache = SQLiteCacheDB(db_path)

        # Then
        assert db_path.exists()
        assert cache.conn is not None
        cache.close()

    def test_init_creates_parent_directory(self, tmp_path: Path) -> None:
        """Initialize should create parent directories."""
        # Given
        db_path = tmp_path / "nested" / "dir" / "cache.db"

        # When
        cache = SQLiteCacheDB(db_path)

        # Then
        assert db_path.exists()
        assert db_path.parent.exists()
        cache.close()

    def test_init_with_existing_db(self, tmp_path: Path) -> None:
        """Initialize should work with existing database."""
        # Given
        db_path = tmp_path / "cache.db"
        cache1 = SQLiteCacheDB(db_path)
        cache1.close()

        # When
        cache2 = SQLiteCacheDB(db_path)

        # Then
        assert cache2.conn is not None
        cache2.close()


class TestSQLiteCacheDBSetAndGet:
    """Test cache set and get operations."""

    def test_set_and_get_success(self, tmp_path: Path) -> None:
        """Set and get should work with valid data."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        key = "search:movie:test:lang=ko"
        data = {"results": [{"id": 123, "title": "Test Movie"}]}

        # When
        cache.set_cache(key, data, cache_type=Cache.TYPE_SEARCH, ttl_seconds=3600)
        result = cache.get(key, cache_type=Cache.TYPE_SEARCH)

        # Then
        assert result is not None
        assert result == data
        cache.close()

    def test_get_nonexistent_key_returns_none(self, tmp_path: Path) -> None:
        """Get should return None for non-existent key."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When
        result = cache.get("nonexistent:key", cache_type=Cache.TYPE_SEARCH)

        # Then
        assert result is None
        cache.close()

    def test_get_expired_entry_returns_none(self, tmp_path: Path) -> None:
        """Get should return None for expired entries."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        key = "search:movie:expired:lang=ko"
        data = {"results": [{"id": 456}]}

        # When - Set with 0 second TTL (immediate expiration)
        cache.set_cache(key, data, cache_type=Cache.TYPE_SEARCH, ttl_seconds=0)
        time.sleep(0.1)  # Ensure expiration
        result = cache.get(key, cache_type=Cache.TYPE_SEARCH)

        # Then
        assert result is None  # Expired
        cache.close()

    def test_set_updates_existing_entry(self, tmp_path: Path) -> None:
        """Set should update existing entry with same key."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        key = "search:movie:update:lang=ko"
        data1 = {"results": [{"id": 1}]}
        data2 = {"results": [{"id": 2}]}

        # When
        cache.set_cache(key, data1, cache_type=Cache.TYPE_SEARCH, ttl_seconds=3600)
        cache.set_cache(key, data2, cache_type=Cache.TYPE_SEARCH, ttl_seconds=3600)
        result = cache.get(key, cache_type=Cache.TYPE_SEARCH)

        # Then
        assert result == data2  # Updated value
        cache.close()

    def test_set_with_complex_nested_data(self, tmp_path: Path) -> None:
        """Set should handle complex nested JSON structures."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        key = "details:tv:1429:lang=ko"
        complex_data = {
            "id": 1429,
            "name": "Attack on Titan",
            "genres": [{"id": 16, "name": "Animation"}],
            "seasons": [
                {"id": 1, "episodes": [{"number": 1, "name": "Ep1"}]},
            ],
            "credits": {
                "cast": [{"name": "Actor 1"}],
                "crew": [{"name": "Director 1"}],
            },
        }

        # When
        cache.set_cache(
            key, complex_data, cache_type=Cache.TYPE_DETAILS, ttl_seconds=7200
        )
        result = cache.get(key, cache_type=Cache.TYPE_DETAILS)

        # Then
        assert result is not None
        assert result == complex_data
        assert result["seasons"][0]["episodes"][0]["name"] == "Ep1"
        cache.close()


class TestSQLiteCacheDBDelete:
    """Test cache delete operations."""

    def test_delete_existing_entry(self, tmp_path: Path) -> None:
        """Delete should remove existing entry."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        key = "search:movie:delete:lang=ko"
        data = {"results": [{"id": 789}]}
        cache.set_cache(key, data, cache_type=Cache.TYPE_SEARCH)

        # When
        deleted = cache.delete(key, cache_type=Cache.TYPE_SEARCH)
        result = cache.get(key, cache_type=Cache.TYPE_SEARCH)

        # Then
        assert deleted is True
        assert result is None
        cache.close()

    def test_delete_nonexistent_entry_returns_false(self, tmp_path: Path) -> None:
        """Delete should return False for non-existent entry."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When
        deleted = cache.delete("nonexistent:key", cache_type=Cache.TYPE_SEARCH)

        # Then
        assert deleted is False
        cache.close()


class TestSQLiteCacheDBPurgeExpired:
    """Test purge expired entries."""

    def test_purge_expired_removes_only_expired(self, tmp_path: Path) -> None:
        """Purge should remove only expired entries."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # Add expired entry
        cache.set_cache("expired:key", {"data": "old"}, ttl_seconds=0)
        time.sleep(0.1)

        # Add valid entry
        cache.set_cache("valid:key", {"data": "new"}, ttl_seconds=3600)

        # When
        purged_count = cache.purge_expired()

        # Then
        assert purged_count == 1
        assert cache.get("expired:key") is None
        assert cache.get("valid:key") is not None
        cache.close()

    def test_purge_expired_with_cache_type_filter(self, tmp_path: Path) -> None:
        """Purge should filter by cache type."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # Add expired entries with different types
        cache.set_cache(
            "key1", {"data": "1"}, cache_type=Cache.TYPE_SEARCH, ttl_seconds=0
        )
        cache.set_cache(
            "key2", {"data": "2"}, cache_type=Cache.TYPE_DETAILS, ttl_seconds=0
        )
        time.sleep(0.1)

        # When - Purge only search type
        purged_count = cache.purge_expired(cache_type=Cache.TYPE_SEARCH)

        # Then
        assert purged_count == 1
        cache.close()


class TestSQLiteCacheDBClear:
    """Test cache clear operations."""

    def test_clear_all_entries(self, tmp_path: Path) -> None:
        """Clear should remove all entries."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("key1", {"data": "1"}, cache_type=Cache.TYPE_SEARCH)
        cache.set_cache("key2", {"data": "2"}, cache_type=Cache.TYPE_DETAILS)

        # When
        cleared_count = cache.clear()

        # Then
        assert cleared_count == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        cache.close()

    def test_clear_by_cache_type(self, tmp_path: Path) -> None:
        """Clear should filter by cache type."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("key1", {"data": "1"}, cache_type=Cache.TYPE_SEARCH)
        cache.set_cache("key2", {"data": "2"}, cache_type=Cache.TYPE_DETAILS)

        # When - Clear only search type
        cleared_count = cache.clear(cache_type=Cache.TYPE_SEARCH)

        # Then
        assert cleared_count == 1
        assert cache.get("key1", cache_type=Cache.TYPE_SEARCH) is None
        assert cache.get("key2", cache_type=Cache.TYPE_DETAILS) is not None
        cache.close()


class TestSQLiteCacheDBCacheInfo:
    """Test cache info statistics."""

    def test_get_cache_info_empty_cache(self, tmp_path: Path) -> None:
        """Cache info should work with empty cache."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # When
        info = cache.get_cache_info()

        # Then
        assert info["total_files"] == 0
        assert info["valid_entries"] == 0
        assert info["expired_entries"] == 0
        cache.close()

    def test_get_cache_info_with_entries(self, tmp_path: Path) -> None:
        """Cache info should count entries correctly."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # Add valid entry
        cache.set_cache("valid:key", {"data": "new"}, ttl_seconds=3600)

        # Add expired entry
        cache.set_cache("expired:key", {"data": "old"}, ttl_seconds=0)
        time.sleep(0.1)

        # When
        info = cache.get_cache_info()

        # Then
        assert info["total_files"] == 2
        assert info["valid_entries"] == 1
        assert info["expired_entries"] == 1
        cache.close()


class TestSQLiteCacheDBConcurrency:
    """Test concurrent access (WAL mode)."""

    def test_concurrent_reads(self, tmp_path: Path) -> None:
        """Multiple connections should be able to read simultaneously."""
        # Given
        db_path = tmp_path / "cache.db"
        cache1 = SQLiteCacheDB(db_path)
        cache1.set_cache("key1", {"data": "test"}, ttl_seconds=3600)

        # When - Open second connection
        cache2 = SQLiteCacheDB(db_path)
        result1 = cache1.get("key1")
        result2 = cache2.get("key1")

        # Then
        assert result1 == result2 == {"data": "test"}
        cache1.close()
        cache2.close()
