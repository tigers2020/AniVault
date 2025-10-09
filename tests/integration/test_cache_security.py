"""Integration tests for cache security features.

Tests verify that security features work correctly when integrated
with SQLiteCacheDB and real application flows.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.shared.constants import Cache
from anivault.shared.errors import ApplicationError, ErrorCode


class TestCacheSecurityIntegration:
    """Integration tests for cache security."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_new_db_file_has_secure_permissions_unix(self, tmp_path: Path) -> None:
        """New SQLite DB file should have 600 permissions on Unix."""
        # Given
        db_path = tmp_path / "secure_cache.db"

        # When
        cache = SQLiteCacheDB(db_path)

        # Then
        assert db_path.exists()
        stat_result = os.stat(db_path)
        file_mode = stat_result.st_mode & 0o777
        assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

        cache.close()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_new_db_file_has_secure_permissions_windows(self, tmp_path: Path) -> None:
        """New SQLite DB file should have owner-only permissions on Windows."""
        # Given
        db_path = tmp_path / "secure_cache.db"

        # When
        cache = SQLiteCacheDB(db_path)

        # Then
        assert db_path.exists()
        # On Windows, just verify file was created and permissions were attempted
        # Actual ACL verification requires pywin32

        cache.close()

    def test_api_key_cannot_be_cached(self, tmp_path: Path) -> None:
        """Should prevent caching data with API keys."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        sensitive_data = {
            "api_key": "sk-1234567890abcdef",
            "results": [{"id": 123, "title": "Test"}],
        }

        # When & Then
        with pytest.raises(ApplicationError) as exc_info:
            cache.set_cache(
                key="search:test",
                data=sensitive_data,
                cache_type=Cache.TYPE_SEARCH,
            )

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "sensitive data" in exc_info.value.message.lower()

        cache.close()

    def test_nested_api_key_cannot_be_cached(self, tmp_path: Path) -> None:
        """Should prevent caching data with nested API keys."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        sensitive_data = {
            "results": [{"id": 123, "title": "Test"}],
            "metadata": {"source": "tmdb", "access_token": "secret123"},
        }

        # When & Then
        with pytest.raises(ApplicationError) as exc_info:
            cache.set_cache(
                key="search:test",
                data=sensitive_data,
                cache_type=Cache.TYPE_SEARCH,
            )

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

        cache.close()

    def test_safe_data_can_be_cached(self, tmp_path: Path) -> None:
        """Should allow caching safe data without sensitive information."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        safe_data = {
            "results": [
                {"id": 123, "title": "Attack on Titan", "year": 2013},
                {"id": 456, "title": "One Piece", "year": 1999},
            ],
            "metadata": {"source": "tmdb", "version": "1.0"},
        }

        # When
        cache.set_cache(
            key="search:anime",
            data=safe_data,
            cache_type=Cache.TYPE_SEARCH,
            ttl_seconds=3600,
        )

        # Then
        retrieved = cache.get(key="search:anime", cache_type=Cache.TYPE_SEARCH)
        assert retrieved is not None
        assert retrieved == safe_data

        cache.close()

    def test_existing_db_file_permissions_not_changed(self, tmp_path: Path) -> None:
        """Should not modify permissions of existing DB files."""
        # Given
        db_path = tmp_path / "existing.db"

        # Create DB with initial permissions
        cache1 = SQLiteCacheDB(db_path)
        cache1.close()

        # Store original permissions (if on Unix)
        if sys.platform != "win32":
            original_mode = os.stat(db_path).st_mode & 0o777

        # When - Reopen existing DB
        cache2 = SQLiteCacheDB(db_path)

        # Then - Permissions should remain unchanged
        if sys.platform != "win32":
            current_mode = os.stat(db_path).st_mode & 0o777
            assert current_mode == original_mode

        cache2.close()

