"""SQLite cache database facade.

This module provides a refactored SQLite cache implementation using
modular operations for better maintainability and testability.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from anivault.core.statistics import StatisticsCollector
from anivault.security.permissions import set_secure_file_permissions
from anivault.services.sqlite_cache.migration.manager import MigrationManager
from anivault.services.sqlite_cache.operations.insert import InsertOperations
from anivault.services.sqlite_cache.operations.query import QueryOperations
from anivault.services.sqlite_cache.operations.update import UpdateOperations
from anivault.shared.constants import Cache
from anivault.shared.errors import (
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error, log_operation_success

logger = logging.getLogger(__name__)


class SQLiteCacheDB:
    """SQLite-based TMDB API cache with Generic Key-Value Store pattern.

    This cache system stores TMDB API responses as JSON blobs in SQLite,
    compatible with all TMDB API endpoints. Uses WAL mode for concurrency
    and includes TTL-based expiration.

    Attributes:
        db_path: Path to SQLite database file
        statistics: Statistics collector for performance tracking
        conn: SQLite database connection

    Example:
        >>> cache = SQLiteCacheDB(Path("cache.db"))
        >>> cache.set_cache("search:movie:test", {"results": [...]}, "search", 3600)
        >>> data = cache.get("search:movie:test", "search")
        >>> cache.close()
    """

    def __init__(
        self,
        db_path: Path | str,
        statistics: StatisticsCollector | None = None,
    ) -> None:
        """Initialize SQLite cache database.

        Args:
            db_path: Path to SQLite database file
            statistics: Optional statistics collector for performance tracking

        Raises:
            InfrastructureError: If database initialization fails
        """
        self.db_path = Path(db_path)
        self.statistics = statistics or StatisticsCollector()
        self.conn: sqlite3.Connection | None = None
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initialize database with WAL mode and schema.

        Raises:
            InfrastructureError: If database connection or schema creation fails
        """
        context = ErrorContext(
            operation="initialize_db",
            additional_data={"db_path": str(self.db_path)},
        )

        try:
            # Create parent directory
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if DB file is newly created
            db_is_new = not self.db_path.exists()

            # Connect with WAL mode for concurrency
            self.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,  # Safe with WAL mode
                isolation_level=None,  # Auto-commit mode
            )

            # Set secure permissions for newly created DB files
            if db_is_new:
                try:
                    set_secure_file_permissions(self.db_path)
                    logger.info(
                        "Secure permissions (600) set for new DB: %s",
                        self.db_path,
                    )
                except Exception as e:  # noqa: BLE001
                    # Log warning but continue - permissions are not critical
                    logger.warning(
                        "Failed to set secure permissions for DB file %s: %s",
                        self.db_path,
                        e,
                    )

            # Enable WAL mode (Write-Ahead Logging)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")

            # Initialize migration manager and create schema
            migration_manager = MigrationManager(self.conn)
            migration_manager.create_tables()

            # Initialize operations
            self._query_ops = QueryOperations(self.conn, self.statistics)
            self._insert_ops = InsertOperations(self.conn, self.statistics)
            self._update_ops = UpdateOperations(self.conn, self.statistics)

            # Cleanup expired on startup
            try:
                purged_count = self.purge_expired()
                if purged_count > 0:
                    logger.info(
                        "Purged %d expired cache entries on startup",
                        purged_count,
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to purge expired entries on startup: %s", str(e))

            log_operation_success(
                logger=logger,
                operation="initialize_db",
                duration_ms=0,
                context=context.additional_data,
            )

        except sqlite3.Error as e:
            error = InfrastructureError(
                code=ErrorCode.FILE_ACCESS_ERROR,
                message=f"Failed to initialize SQLite cache: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="initialize_db",
                additional_context=context.additional_data,
            )
            raise error from e

    def get(
        self,
        key: str,
        cache_type: str = Cache.TYPE_SEARCH,
    ) -> dict[str, Any] | None:
        """Retrieve data from cache (JSONCacheV2 compatible signature).

        Args:
            key: Cache key identifier
            cache_type: Type of cache ('search' or 'details')

        Returns:
            Cached data if found and not expired, None otherwise

        Raises:
            InfrastructureError: If database operation fails
        """
        return self._query_ops.get(key, cache_type)

    def set_cache(
        self,
        key: str,
        data: dict[str, Any],
        cache_type: str = Cache.TYPE_SEARCH,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store data in cache.

        Args:
            key: Cache key identifier
            data: Data to cache (must be JSON-serializable)
            cache_type: Type of cache ('search' or 'details')
            ttl_seconds: Time-to-live in seconds (None for default TTL)

        Raises:
            InfrastructureError: If database operation fails
        """
        self._insert_ops.insert(key, data, cache_type, ttl_seconds)

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

        Raises:
            InfrastructureError: If database operation fails
        """
        return self._update_ops.delete(key, cache_type)

    def purge_expired(self) -> int:
        """Purge expired cache entries.

        Returns:
            Number of purged entries

        Raises:
            InfrastructureError: If database operation fails
        """
        return self._update_ops.purge_expired()

    def clear(self, cache_type: str | None = None) -> int:
        """Clear cache entries.

        Args:
            cache_type: Type of cache to clear (None for all types)

        Returns:
            Number of cleared entries

        Raises:
            InfrastructureError: If database operation fails
        """
        return self._update_ops.clear(cache_type)

    def get_cache_info(self) -> dict[str, Any]:
        """Get cache statistics and metadata.

        Returns:
            Dictionary with cache information:
            - cache_directory: Path to cache directory
            - total_files: Total number of cache entries
            - valid_entries: Number of non-expired entries
            - expired_entries: Number of expired entries
            - total_size_bytes: Total size of cache data

        Raises:
            InfrastructureError: If database operation fails
        """
        if self.conn is None:
            msg = "Database connection not initialized"
            raise InfrastructureError(
                code=ErrorCode.FILE_ACCESS_ERROR,
                message=msg,
                context=ErrorContext(operation="get_cache_info"),
            )

        # Get total entries
        cursor = self.conn.execute("SELECT COUNT(*) FROM tmdb_cache")
        total_files = cursor.fetchone()[0]

        # Get valid (non-expired) entries
        now = sqlite3.datetime.datetime.now(sqlite3.datetime.timezone.utc)
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM tmdb_cache WHERE expires_at IS NULL OR expires_at > ?",
            (now.isoformat(),),
        )
        valid_entries = cursor.fetchone()[0]

        # Calculate total size
        cursor = self.conn.execute("SELECT SUM(response_size) FROM tmdb_cache")
        total_size_bytes = cursor.fetchone()[0] or 0

        return {
            "cache_directory": str(self.db_path.parent),
            "total_files": total_files,
            "valid_entries": valid_entries,
            "expired_entries": total_files - valid_entries,
            "total_size_bytes": total_size_bytes,
        }

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Closed SQLite cache connection: %s", self.db_path)
