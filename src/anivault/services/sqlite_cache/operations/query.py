"""Query operations for SQLite cache.

This module provides query operations for retrieving cached data.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from anivault.services.cache_models import (
    CacheEntry,
    CacheValidationConstants,
)
from anivault.shared.constants import Cache

if TYPE_CHECKING:
    from typing import Any


from anivault.services.sqlite_cache.operations.base import BaseOperation

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

    from datetime import timezone as tz

    dt = datetime.fromisoformat(timestamp_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.utc)
    return dt


def _deserialize_response_data(
    response_data_str: str, key_hash: str
) -> dict[str, Any] | None:
    """Deserialize JSON response data.

    Args:
        response_data_str: JSON string to deserialize
        key_hash: Cache key hash for logging

    Returns:
        Deserialized data or None if deserialization fails
    """
    try:
        return json.loads(response_data_str)  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        logger.warning(
            "Failed to deserialize cache data for key hash %s...: %s",
            key_hash[: CacheValidationConstants.HASH_PREFIX_LOG_LENGTH],
            str(e),
        )
        return None


def _build_cache_entry_from_row(
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
        return CacheEntry(
            cache_key=cache_key,
            key_hash=key_hash,
            cache_type=cache_type,  # type: ignore[arg-type]
            response_data=response_data,
            created_at=_parse_timestamp_with_tz(created_at_str),  # type: ignore[arg-type]
            expires_at=_parse_timestamp_with_tz(expires_at_str),
            hit_count=hit_count or 0,
            last_accessed_at=_parse_timestamp_with_tz(last_accessed_at_str),
            response_size=response_size or 0,
        )
    except (ValueError, TypeError) as e:
        logger.warning(
            "Failed to reconstruct CacheEntry for key hash %s...: %s",
            key_hash[: CacheValidationConstants.HASH_PREFIX_LOG_LENGTH],
            str(e),
        )
        return None


class QueryOperations(BaseOperation):
    """Query operations for cache retrieval."""

    def get(
        self,
        key: str,
        cache_type: str = Cache.TYPE_SEARCH,
    ) -> dict[str, Any] | None:
        """Retrieve data from cache.

        Args:
            key: Cache key identifier
            cache_type: Type of cache ('search' or 'details')

        Returns:
            Cached data if found and not expired, None otherwise
        """
        self._validate_connection()

        # Generate key hash
        _, key_hash = self._generate_cache_key_hash(key)

        # Query cache - fetch all fields to reconstruct CacheEntry
        sql = """
        SELECT cache_key, key_hash, cache_type, response_data,
               created_at, expires_at, hit_count, last_accessed_at, response_size
        FROM tmdb_cache
        WHERE key_hash = ? AND cache_type = ?
        """

        cursor = self.conn.execute(sql, (key_hash, cache_type))
        row = cursor.fetchone()

        if row is None:
            # Cache miss
            self.statistics.record_cache_miss(cache_type)
            return None

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

        # Deserialize response data
        response_data = _deserialize_response_data(response_data_str, key_hash)
        if response_data is None:
            self.statistics.record_cache_miss(cache_type)
            return None

        # Build CacheEntry from row data
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

        # Check expiration
        if cache_entry.is_expired():
            logger.debug("Cache entry expired for key: %s", key[:50])
            self.statistics.record_cache_miss(cache_type)
            return None

        # Update hit count and last accessed time
        self._update_access_stats(key_hash, cache_type)

        # Record cache hit
        self.statistics.record_cache_hit(cache_type)

        logger.debug(
            "Cache hit: key=%s (hash=%s...), type=%s",
            key[:50],
            key_hash[:16],
            cache_type,
        )

        # Return only the response data (backward compatibility)
        return response_data

    def _update_access_stats(self, key_hash: str, cache_type: str) -> None:
        """Update access statistics for cache entry.

        Args:
            key_hash: Cache key hash
            cache_type: Type of cache
        """
        update_sql = """
        UPDATE tmdb_cache
        SET hit_count = hit_count + 1,
            last_accessed_at = CURRENT_TIMESTAMP
        WHERE key_hash = ? AND cache_type = ?
        """
        self.conn.execute(update_sql, (key_hash, cache_type))
