"""Update operations for SQLite cache.

This module provides update/delete operations for cache management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from anivault.services.sqlite_cache.operations.base import BaseOperation
from anivault.shared.constants import Cache

logger = logging.getLogger(__name__)


class UpdateOperations(BaseOperation):
    """Update/delete operations for cache management."""

    def delete(
        self,
        key: str,
        cache_type: str = Cache.TYPE_SEARCH,
    ) -> bool:
        """Delete cache entry by key.

        Args:
            key: Cache key identifier
            cache_type: Type of cache

        Returns:
            True if deleted, False if not found
        """
        self._validate_connection()

        # Generate key hash
        _, key_hash = self._generate_cache_key_hash(key)

        # Delete entry
        delete_sql = """
        DELETE FROM tmdb_cache
        WHERE key_hash = ? AND cache_type = ?
        """
        cursor = self.conn.execute(delete_sql, (key_hash, cache_type))

        deleted_count = cursor.rowcount
        deleted = deleted_count > 0

        if deleted:
            logger.debug(
                "Cache deleted: key=%s (hash=%s...), type=%s",
                key[:50],
                key_hash[:16],
                cache_type,
            )

        return deleted

    def purge_expired(self) -> int:
        """Purge expired cache entries.

        Returns:
            Number of purged entries
        """
        self._validate_connection()

        now = datetime.now(timezone.utc)

        purge_sql = """
        DELETE FROM tmdb_cache
        WHERE expires_at IS NOT NULL AND expires_at < ?
        """
        cursor = self.conn.execute(purge_sql, (now.isoformat(),))

        purged_count = cursor.rowcount

        if purged_count > 0:
            logger.info("Purged %d expired cache entries", purged_count)

        return purged_count

    def clear(self, cache_type: str | None = None) -> int:
        """Clear cache entries.

        Args:
            cache_type: Type of cache to clear (None for all types)

        Returns:
            Number of cleared entries
        """
        self._validate_connection()

        if cache_type:
            clear_sql = "DELETE FROM tmdb_cache WHERE cache_type = ?"
            cursor = self.conn.execute(clear_sql, (cache_type,))
            logger.info("Cleared cache for type: %s", cache_type)
        else:
            clear_sql = "DELETE FROM tmdb_cache"
            cursor = self.conn.execute(clear_sql)
            logger.info("Cleared all cache entries")

        cleared_count = cursor.rowcount

        return cleared_count
