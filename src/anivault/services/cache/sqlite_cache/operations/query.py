"""Query operations for SQLite cache.

This module provides query operations for retrieving cached data.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal, cast

from anivault.services.cache.sqlite_cache.operations.base import BaseOperation
from anivault.services.cache_models import CacheEntry
from anivault.shared.constants import Cache

logger = logging.getLogger(__name__)


def _parse_timestamp_with_tz(timestamp_str: str | None) -> datetime | None:
    """Parse ISO timestamp string and ensure timezone-aware.

    Args:
        timestamp_str: ISO format timestamp string or None

    Returns:
        Timezone-aware datetime or None if input is None
    """
    if not timestamp_str:
        return None
    dt = datetime.fromisoformat(timestamp_str)  # pylint: disable=import-outside-toplevel
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _deserialize_response_data(response_data_str: str | None, key_hash: str) -> dict[str, Any] | None:
    """Deserialize JSON response data.

    Args:
        response_data_str: JSON string to deserialize (may be None)
        key_hash: Cache key hash for logging

    Returns:
        Deserialized data or None if deserialization fails
    """
    if response_data_str is None:
        logger.warning("response_data is None for key hash %s...", key_hash[:8])
        return None
    try:
        result = json.loads(response_data_str)
        return cast("dict[str, Any]", result)
    except json.JSONDecodeError as e:
        logger.warning("Failed to deserialize cache data for key hash %s...: %s", key_hash[:8], str(e))
        return None
    except TypeError as e:
        logger.warning("Invalid type for response_data for key hash %s...: %s", key_hash[:8], str(e))
        return None


def _build_cache_entry_from_row(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    cache_key: str,
    key_hash: str,
    cache_type: str,
    response_data: dict[str, Any],
    created_at_str: str,
    expires_at_str: str | None,
    hit_count: int | None,
    last_accessed_at_str: str | None,
    response_size: int | None,
) -> CacheEntry | None:
    """Build CacheEntry from database row data.

    Args:
        cache_key: Cache key
        key_hash: Cache key hash
        cache_type: Cache type
        response_data: Deserialized response data
        created_at_str: Created timestamp string
        expires_at_str: Expiration timestamp string
        hit_count: Hit count
        last_accessed_at_str: Last accessed timestamp string
        response_size: Response size in bytes

    Returns:
        CacheEntry instance or None if construction fails
    """
    try:
        # Validate cache_type - support "parser" type for backward compatibility
        # CacheEntry model only accepts "search" or "details", but we need to handle "parser"
        # For "parser" type, we'll skip CacheEntry construction and return None
        # This allows the query to continue but treats parser cache as miss
        if cache_type not in ("search", "details"):
            logger.debug("Cache type '%s' not supported for CacheEntry, treating as cache miss", cache_type)
            return None
        cache_type_literal: Literal["search", "details"] = cast('Literal["search", "details"]', cache_type)

        # Validate created_at is not None
        created_at = _parse_timestamp_with_tz(created_at_str)
        if created_at is None:
            logger.warning("created_at is None for key hash %s...", key_hash[:8])
            return None

        return CacheEntry(
            cache_key=cache_key,
            key_hash=key_hash,
            cache_type=cache_type_literal,
            response_data=response_data,
            created_at=created_at,
            expires_at=_parse_timestamp_with_tz(expires_at_str),
            hit_count=hit_count or 0,
            last_accessed_at=_parse_timestamp_with_tz(last_accessed_at_str),
            response_size=response_size or 0,
        )
    except (ValueError, TypeError) as e:
        logger.warning("Failed to reconstruct CacheEntry for key hash %s...: %s", key_hash[:8], str(e))
        return None


class QueryOperations(BaseOperation):
    """Query operations for cache retrieval."""

    def get(self, key: str, cache_type: str = Cache.TYPE_SEARCH) -> dict[str, Any] | None:
        """Retrieve data from cache.

        Args:
            key: Cache key identifier
            cache_type: Type of cache ('search' or 'details')

        Returns:
            Cached data if found and not expired, None otherwise
        """
        # #region agent log
        with open(r"f:\Python_Projects\AniVault\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "query.py:114", "message": "QueryOperations.get entry", "data": {"key": key[:64] if len(key) > 64 else key, "key_length": len(key), "cache_type": cache_type}, "timestamp": __import__("time").time() * 1000}) + "\n")
        # #endregion

        self._validate_connection()
        _, key_hash = self._generate_cache_key_hash(key)

        # #region agent log
        with open(r"f:\Python_Projects\AniVault\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "query.py:127", "message": "before SQL execute", "data": {"key_hash": key_hash[:16], "cache_type": cache_type}, "timestamp": __import__("time").time() * 1000}) + "\n")
        # #endregion

        sql = "\n        SELECT cache_key, key_hash, cache_type, response_data,\n               created_at, expires_at, hit_count, last_accessed_at, response_size\n        FROM tmdb_cache\n        WHERE key_hash = ? AND cache_type = ?\n        "
        try:
            cursor = self.conn.execute(sql, (key_hash, cache_type))
            row = cursor.fetchone()
            # Explicitly close cursor to prevent "another row available" errors
            cursor.close()
        except Exception as sql_err:  # pylint: disable=broad-exception-caught
            # #region agent log
            with open(r"f:\Python_Projects\AniVault\.cursor\debug.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "E", "location": "query.py:131", "message": "SQL execute failed", "data": {"error": str(sql_err), "error_type": type(sql_err).__name__}, "timestamp": __import__("time").time() * 1000}) + "\n")
            # #endregion
            raise

        # #region agent log
        with open(r"f:\Python_Projects\AniVault\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "F", "location": "query.py:137", "message": "fetchone result", "data": {"row_is_none": row is None, "row_type": type(row).__name__, "row_length": len(row) if row else 0}, "timestamp": __import__("time").time() * 1000}) + "\n")
        # #endregion

        if row is None:
            self.statistics.record_cache_miss(cache_type)
            return None

        # #region agent log
        with open(r"f:\Python_Projects\AniVault\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": "debug-session", "runId": "run1", "hypothesisId": "F", "location": "query.py:143", "message": "before unpack row", "data": {"row_length": len(row) if row else 0}, "timestamp": __import__("time").time() * 1000}) + "\n")
        # #endregion

        (
            cache_key_db,
            key_hash_db,
            cache_type_db,
            response_data_str,
            created_at_str,
            expires_at_str,
            hit_count_db,
            last_accessed_at_str,
            response_size_db,
        ) = row
        response_data = _deserialize_response_data(response_data_str, key_hash)
        if response_data is None:
            self.statistics.record_cache_miss(cache_type)
            return None
        cache_entry = _build_cache_entry_from_row(
            cache_key=cache_key_db,
            key_hash=key_hash_db,
            cache_type=cache_type_db,
            response_data=response_data,
            created_at_str=created_at_str,
            expires_at_str=expires_at_str,
            hit_count=hit_count_db,
            last_accessed_at_str=last_accessed_at_str,
            response_size=response_size_db,
        )
        if cache_entry is None:
            self.statistics.record_cache_miss(cache_type)
            return None
        if cache_entry.is_expired():
            logger.debug("Cache entry expired for key: %s", key[:50])
            self.statistics.record_cache_miss(cache_type)
            return None
        self._update_access_stats(key_hash, cache_type)
        self.statistics.record_cache_hit(cache_type)
        logger.debug("Cache hit: key=%s (hash=%s...), type=%s", key[:50], key_hash[:8], cache_type)
        return response_data

    def _update_access_stats(self, key_hash: str, cache_type: str) -> None:
        """Update access statistics for cache entry.

        Args:
            key_hash: Cache key hash
            cache_type: Type of cache
        """
        update_sql = "\n        UPDATE tmdb_cache\n        SET hit_count = hit_count + 1,\n            last_accessed_at = CURRENT_TIMESTAMP\n        WHERE key_hash = ? AND cache_type = ?\n        "
        cursor = self.conn.execute(update_sql, (key_hash, cache_type))
        cursor.close()
