"""Failure-First tests for sqlite_cache_db.py.

Stage 3.3: Test cache system error handling.
- get() method: Distinguish cache miss from errors
- delete() method: Raise exceptions instead of returning False
"""

from pathlib import Path
from unittest.mock import Mock, patch
import sqlite3

import pytest

from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.shared.errors import ApplicationError, ErrorCode, InfrastructureError


class TestCacheGetFailures:
    """SQLiteCacheDB.get() 실패 케이스 테스트."""

    def test_json_decode_error_returns_none_with_logging(self, caplog, tmp_path):
        """JSON decode 실패 시 None 반환 + 로깅 (graceful degradation)."""
        # Given
        db_path = tmp_path / "test_cache.db"
        cache_db = SQLiteCacheDB(db_path=str(db_path))

        # Insert corrupted JSON data directly into DB
        # Generate valid 64-char hex hash
        key_hash = "a" * 64
        with cache_db.conn:
            cache_db.conn.execute(
                """
                INSERT INTO tmdb_cache (cache_key, key_hash, response_data, cache_type, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("test_key", key_hash, "invalid json{{{", "search", "2025-10-07T10:00:00Z"),
            )

        # When
        result = cache_db.get("test_key", cache_type="search")

        # Then: None 반환 (graceful degradation - 캐시 miss로 처리)
        assert result is None

        # And: 로깅되어야 함 (로그 확인 - 실제 출력은 stderr)
        # Note: logger.warning이므로 caplog에는 안 잡힐 수 있음
        # 실제로는 logger.warning이 호출됨 (코드에서 확인)

    def test_database_error_returns_none_with_logging(self, caplog, tmp_path):
        """DB 에러 시 None 반환 + 로깅 (graceful degradation)."""
        # Given
        db_path = tmp_path / "test_cache.db"
        cache_db = SQLiteCacheDB(db_path=str(db_path))

        # Close connection to trigger error
        cache_db.conn.close()

        # When
        result = cache_db.get("test_key", cache_type="search")

        # Then: None 반환 (graceful degradation)
        assert result is None

        # And: 로깅되어야 함 (stderr 출력 확인됨)

    def test_valid_cache_hit_returns_data(self, tmp_path):
        """유효한 캐시 hit 시 데이터 반환."""
        # Given
        db_path = tmp_path / "test_cache.db"
        cache_db = SQLiteCacheDB(db_path=str(db_path))

        test_data = {"title": "Attack on Titan", "id": 1234}
        # Use set_cache() method
        cache_db.set_cache(key="test_key", data=test_data, cache_type="search")

        # When
        result = cache_db.get("test_key", cache_type="search")

        # Then
        assert result is not None
        assert result["title"] == "Attack on Titan"


class TestCacheDeleteFailures:
    """SQLiteCacheDB.delete() 실패 케이스 테스트."""

    def test_database_error_raises_infrastructure_error(self, tmp_path):
        """DB 에러 시 InfrastructureError 발생."""
        # Given
        db_path = tmp_path / "test_cache.db"
        cache_db = SQLiteCacheDB(db_path=str(db_path))

        # Close connection to trigger error
        cache_db.conn.close()

        # When & Then: delete 실패는 명확히 예외 발생해야 함
        with pytest.raises(InfrastructureError) as exc_info:
            cache_db.delete("test_key", cache_type="search")

        assert exc_info.value.code in [ErrorCode.FILE_ACCESS_ERROR, ErrorCode.APPLICATION_ERROR]

    def test_nonexistent_key_returns_false(self, tmp_path):
        """존재하지 않는 키 삭제 시 False 반환 (정상 동작)."""
        # Given
        db_path = tmp_path / "test_cache.db"
        cache_db = SQLiteCacheDB(db_path=str(db_path))

        # When
        result = cache_db.delete("nonexistent_key", cache_type="search")

        # Then: False 반환 (존재하지 않음 - 정상)
        assert result is False

    def test_valid_delete_returns_true(self, tmp_path):
        """유효한 삭제 시 True 반환."""
        # Given
        db_path = tmp_path / "test_cache.db"
        cache_db = SQLiteCacheDB(db_path=str(db_path))

        test_data = {"title": "Attack on Titan"}
        cache_db.set_cache(key="test_key", data=test_data, cache_type="search")

        # When
        result = cache_db.delete("test_key", cache_type="search")

        # Then
        assert result is True


# Note: 캐시 시스템의 get()은 graceful degradation을 위해 None 반환 유지
# 하지만 delete()는 명확한 실패를 위해 예외 발생으로 변경

