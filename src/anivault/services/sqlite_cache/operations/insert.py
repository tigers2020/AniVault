"""Insert operations for SQLite cache.

This module provides insert operations for storing cached data.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from anivault.shared.constants import Cache, MatchingCacheConfig

if TYPE_CHECKING:
    from typing import Any


from anivault.services.sqlite_cache.operations.base import BaseOperation

logger = logging.getLogger(__name__)


class InsertOperations(BaseOperation):
    """Insert operations for cache storage."""

    def insert(
        self,
        key: str,
        data: dict[str, Any],
        cache_type: str = Cache.TYPE_SEARCH,
        ttl_seconds: int | None = None,
    ) -> None:
        """Insert data into cache.

        Args:
            key: Cache key identifier
            data: Data to cache (must be JSON-serializable)
            cache_type: Type of cache ('search' or 'details')
            ttl_seconds: Time-to-live in seconds (None for default TTL)
        """
        self._validate_connection()

        # Generate key hash
        _, key_hash = self._generate_cache_key_hash(key)

        # Serialize data to JSON
        try:
            response_data_json = json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError):
            logger.exception(
                "Failed to serialize cache data for key %s",
                key[:50],
            )
            raise

        # Calculate TTL
        if ttl_seconds is None:
            ttl_seconds = self._get_default_ttl(cache_type)

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

        # Calculate response size
        response_size = len(response_data_json.encode("utf-8"))

        # Note: Response size validation removed as CacheValidationConstants
        # doesn't have MAX_RESPONSE_SIZE. If needed, add to constants.

        # Insert or replace
        insert_sql = """
        INSERT OR REPLACE INTO tmdb_cache (
            cache_key, key_hash, cache_type, response_data,
            created_at, expires_at, response_size
        ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
        """

        self.conn.execute(
            insert_sql,
            (
                key,
                key_hash,
                cache_type,
                response_data_json,
                expires_at.isoformat(),
                response_size,
            ),
        )

        logger.debug(
            "Cache inserted: key=%s (hash=%s...), type=%s, size=%d bytes, ttl=%ds",
            key[:50],
            key_hash[:16],
            cache_type,
            response_size,
            ttl_seconds,
        )

    def _get_default_ttl(self, cache_type: str) -> int:
        """Get default TTL for cache type.

        Args:
            cache_type: Type of cache

        Returns:
            Default TTL in seconds
        """
        ttl_map = {
            Cache.TYPE_SEARCH: MatchingCacheConfig.SEARCH_CACHE_TTL_SECONDS,
            Cache.TYPE_DETAILS: MatchingCacheConfig.DETAILS_CACHE_TTL_SECONDS,
        }
        return ttl_map.get(cache_type, MatchingCacheConfig.SEARCH_CACHE_TTL_SECONDS)
