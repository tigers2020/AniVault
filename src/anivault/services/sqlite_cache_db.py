"""SQLite-based TMDB cache database implementation.

This module provides a SQLite-based cache system for TMDB API responses,
using a Generic Key-Value Store pattern that's compatible with all TMDB
API endpoints. Implements Write-Ahead Logging (WAL) for concurrency.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from anivault.core.statistics import StatisticsCollector
from anivault.security.permissions import (
    set_secure_file_permissions,
    validate_api_key_not_in_data,
)
from anivault.shared.constants import Cache
from anivault.shared.constants.core import CacheConfig
from anivault.shared.errors import (
    ApplicationError,
    DomainError,
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
                    logger.info("Secure permissions (600) set for new DB: %s", self.db_path)
                except Exception as e:  # noqa: BLE001
                    # Log warning but continue - permissions are not critical for functionality
                    logger.warning(
                        "Failed to set secure permissions for DB file %s: %s",
                        self.db_path,
                        e,
                    )

            # Enable WAL mode (Write-Ahead Logging)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")  # Performance boost

            # Create schema
            self._create_tables()

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
                code=ErrorCode.DATABASE_CONNECTION_ERROR,
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

    def _create_tables(self) -> None:
        """Create cache table schema with Generic Key-Value Store pattern."""
        if self.conn is None:
            msg = "Database connection not initialized"
            raise InfrastructureError(
                code=ErrorCode.DATABASE_CONNECTION_ERROR,
                message=msg,
                context=ErrorContext(operation="create_tables"),
            )

        schema_sql = """
        CREATE TABLE IF NOT EXISTS tmdb_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Cache key information
            cache_key TEXT NOT NULL UNIQUE,
            key_hash TEXT NOT NULL UNIQUE,

            -- Cache type (extensible)
            cache_type TEXT NOT NULL,
            endpoint_category TEXT,

            -- Response data (JSON BLOB)
            response_data TEXT NOT NULL,

            -- TTL and metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            expires_at TIMESTAMP,

            -- Statistics (optional)
            hit_count INTEGER DEFAULT 0,
            last_accessed_at TIMESTAMP,
            response_size INTEGER,

            -- Constraints
            CHECK (length(cache_key) > 0),
            CHECK (length(key_hash) = 64)
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_key_hash ON tmdb_cache(key_hash);
        CREATE INDEX IF NOT EXISTS idx_cache_type ON tmdb_cache(cache_type);
        CREATE INDEX IF NOT EXISTS idx_expires_at ON tmdb_cache(expires_at);
        CREATE INDEX IF NOT EXISTS idx_last_accessed ON tmdb_cache(last_accessed_at);
        """

        self.conn.executescript(schema_sql)

    def _generate_cache_key_hash(self, key: str) -> tuple[str, str]:
        """Generate cache key and SHA-256 hash with security masking.

        Args:
            key: Original cache key

        Returns:
            Tuple of (normalized_key, key_hash)

        Security:
            - Normalizes key (lowercase, strip)
            - Generates SHA-256 hash for secure lookup
            - Never logs original key in production
        """
        # Normalize key
        normalized_key = key.lower().strip()

        # Generate SHA-256 hash (64 characters)
        key_hash = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()

        # Log only hash prefix, never full key
        logger.debug("Generated cache key hash: %s...", key_hash[:16])

        return normalized_key, key_hash

    def set_cache(
        self,
        key: str,
        data: dict[str, Any],
        cache_type: str = Cache.TYPE_SEARCH,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store data in cache (JSONCacheV2 compatible signature).

        Args:
            key: Cache key identifier
            data: Dictionary containing the data to cache
            cache_type: Type of cache ('search' or 'details')
            ttl_seconds: Time-to-live in seconds (None for default TTL)

        Raises:
            InfrastructureError: If database operation fails
            DomainError: If data validation fails
        """
        context = ErrorContext(
            operation="cache_set",
            additional_data={
                "key": key[:50],  # Truncate for logging
                "cache_type": cache_type,
                "ttl_seconds": ttl_seconds,
            },
        )

        if self.conn is None:
            msg = "Database connection not initialized"
            raise InfrastructureError(
                code=ErrorCode.DATABASE_CONNECTION_ERROR,
                message=msg,
                context=context,
            )

        # Validate that data doesn't contain sensitive information
        try:
            validate_api_key_not_in_data(data)
        except ApplicationError as e:
            logger.exception("Security validation failed: %s", e.message)
            raise

        try:
            # Generate cache key and hash
            cache_key, key_hash = self._generate_cache_key_hash(key)

            # Calculate expiration timestamp
            now = datetime.now(timezone.utc)
            if ttl_seconds is not None and ttl_seconds >= 0:
                expires_at = now + timedelta(seconds=ttl_seconds)
            else:
                # Use default TTL
                expires_at = now + timedelta(seconds=CacheConfig.DEFAULT_TTL)

            # Serialize data to JSON
            try:
                response_data = json.dumps(data, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                error = DomainError(
                    code=ErrorCode.CACHE_SERIALIZATION_ERROR,
                    message=f"Failed to serialize cache data: {e!s}",
                    context=context,
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    error=error,
                    operation="cache_set",
                    additional_context=context.additional_data,
                )
                raise error from e

            response_size = len(response_data)

            # Insert or replace cache entry
            sql = """
            INSERT OR REPLACE INTO tmdb_cache (
                cache_key, key_hash, cache_type, response_data,
                created_at, expires_at, response_size, hit_count, last_accessed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """

            self.conn.execute(
                sql,
                (
                    cache_key,
                    key_hash,
                    cache_type,
                    response_data,
                    now.isoformat(),
                    expires_at.isoformat(),
                    response_size,
                    now.isoformat(),
                ),
            )

            # Record cache operation
            self.statistics.record_cache_operation("set", hit=False, key=key_hash)

            log_operation_success(
                logger=logger,
                operation="cache_set",
                duration_ms=0,
                context=context.additional_data,
            )

        except sqlite3.Error as e:
            error = InfrastructureError(
                code=ErrorCode.DATABASE_OPERATION_ERROR,
                message=f"Failed to set cache: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="cache_set",
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
        context = ErrorContext(
            operation="cache_get",
            additional_data={"key": key[:50], "cache_type": cache_type},
        )

        if self.conn is None:
            msg = "Database connection not initialized"
            raise InfrastructureError(
                code=ErrorCode.DATABASE_CONNECTION_ERROR,
                message=msg,
                context=context,
            )

        try:
            # Generate key hash
            _, key_hash = self._generate_cache_key_hash(key)

            # Query cache
            sql = """
            SELECT response_data, expires_at
            FROM tmdb_cache
            WHERE key_hash = ? AND cache_type = ?
            """

            cursor = self.conn.execute(sql, (key_hash, cache_type))
            row = cursor.fetchone()

            if row is None:
                # Cache miss
                self.statistics.record_cache_miss(cache_type)
                return None

            response_data_str, expires_at_str = row

            # Check expiration
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now(timezone.utc) > expires_at:
                    # Expired
                    logger.debug("Cache entry expired for key hash: %s...", key_hash[:16])
                    self.statistics.record_cache_miss(cache_type)
                    return None

            # Deserialize JSON
            try:
                data = json.loads(response_data_str)
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to deserialize cache data for key hash %s...: %s",
                    key_hash[:16],
                    str(e),
                )
                self.statistics.record_cache_miss(cache_type)
                return None

            # Update hit count and last accessed
            update_sql = """
            UPDATE tmdb_cache
            SET hit_count = hit_count + 1,
                last_accessed_at = ?
            WHERE key_hash = ?
            """
            self.conn.execute(update_sql, (datetime.now(timezone.utc).isoformat(), key_hash))

            # Cache hit
            self.statistics.record_cache_hit(cache_type)
            logger.debug("Cache hit for key hash: %s...", key_hash[:16])

            return data

        except sqlite3.Error as e:
            error = InfrastructureError(
                code=ErrorCode.DATABASE_OPERATION_ERROR,
                message=f"Failed to get cache: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="cache_get",
                additional_context=context.additional_data,
            )
            return None  # Don't raise on read errors, just return None

    def delete(self, key: str, cache_type: str = Cache.TYPE_SEARCH) -> bool:
        """Delete specific cache entry.

        Args:
            key: Cache key identifier
            cache_type: Type of cache ('search' or 'details')

        Returns:
            True if entry was deleted, False if it didn't exist

        Raises:
            InfrastructureError: If database operation fails
        """
        context = ErrorContext(
            operation="cache_delete",
            additional_data={"key": key[:50], "cache_type": cache_type},
        )

        if self.conn is None:
            msg = "Database connection not initialized"
            raise InfrastructureError(
                code=ErrorCode.DATABASE_CONNECTION_ERROR,
                message=msg,
                context=context,
            )

        try:
            # Generate key hash
            _, key_hash = self._generate_cache_key_hash(key)

            # Delete entry
            sql = "DELETE FROM tmdb_cache WHERE key_hash = ? AND cache_type = ?"
            cursor = self.conn.execute(sql, (key_hash, cache_type))

            deleted = cursor.rowcount > 0

            if deleted:
                logger.debug("Deleted cache entry for key hash: %s...", key_hash[:16])

            return deleted

        except sqlite3.Error as e:
            error = InfrastructureError(
                code=ErrorCode.DATABASE_OPERATION_ERROR,
                message=f"Failed to delete cache: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="cache_delete",
                additional_context=context.additional_data,
            )
            return False

    def purge_expired(self, cache_type: str | None = None) -> int:
        """Remove expired cache entries.

        Args:
            cache_type: Optional cache type filter

        Returns:
            Number of entries removed

        Raises:
            InfrastructureError: If database operation fails
        """
        context = ErrorContext(
            operation="purge_expired",
            additional_data={"cache_type": cache_type},
        )

        if self.conn is None:
            msg = "Database connection not initialized"
            raise InfrastructureError(
                code=ErrorCode.DATABASE_CONNECTION_ERROR,
                message=msg,
                context=context,
            )

        try:
            now = datetime.now(timezone.utc).isoformat()

            if cache_type:
                sql = """
                DELETE FROM tmdb_cache
                WHERE expires_at IS NOT NULL
                  AND expires_at < ?
                  AND cache_type = ?
                """
                cursor = self.conn.execute(sql, (now, cache_type))
            else:
                sql = """
                DELETE FROM tmdb_cache
                WHERE expires_at IS NOT NULL
                  AND expires_at < ?
                """
                cursor = self.conn.execute(sql, (now,))

            purged_count = cursor.rowcount

            if purged_count > 0:
                logger.info(
                    "Purged %d expired cache entries (%s)",
                    purged_count,
                    cache_type or "all",
                )

            return purged_count

        except sqlite3.Error as e:
            error = InfrastructureError(
                code=ErrorCode.DATABASE_OPERATION_ERROR,
                message=f"Failed to purge expired cache: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="purge_expired",
                additional_context=context.additional_data,
            )
            raise error from e

    def clear(self, cache_type: str | None = None) -> int:
        """Clear cache entries (JSONCacheV2 compatible).

        Args:
            cache_type: Optional cache type filter

        Returns:
            Number of entries deleted

        Raises:
            InfrastructureError: If database operation fails
        """
        context = ErrorContext(
            operation="cache_clear",
            additional_data={"cache_type": cache_type},
        )

        if self.conn is None:
            msg = "Database connection not initialized"
            raise InfrastructureError(
                code=ErrorCode.DATABASE_CONNECTION_ERROR,
                message=msg,
                context=context,
            )

        try:
            if cache_type:
                sql = "DELETE FROM tmdb_cache WHERE cache_type = ?"
                cursor = self.conn.execute(sql, (cache_type,))
            else:
                sql = "DELETE FROM tmdb_cache"
                cursor = self.conn.execute(sql)

            deleted_count = cursor.rowcount

            logger.info(
                "Cleared %d cache entries (%s)",
                deleted_count,
                cache_type or "all",
            )

            return deleted_count

        except sqlite3.Error as e:
            error = InfrastructureError(
                code=ErrorCode.DATABASE_OPERATION_ERROR,
                message=f"Failed to clear cache: {e!s}",
                context=context,
                original_error=e,
            )
            log_operation_error(
                logger=logger,
                error=error,
                operation="cache_clear",
                additional_context=context.additional_data,
            )
            raise error from e

    def get_cache_info(self, cache_type: str | None = None) -> dict[str, Any]:
        """Get cache statistics (JSONCacheV2 compatible).

        Args:
            cache_type: Optional cache type filter

        Returns:
            Dictionary with cache statistics:
            - total_files: Total number of cache entries
            - valid_entries: Non-expired entries
            - expired_entries: Expired but not yet purged
            - total_size_bytes: Total cache size
            - cache_directory: Database file path
            - cache_type: Type filter used
        """
        if self.conn is None:
            return {
                "total_files": 0,
                "valid_entries": 0,
                "expired_entries": 0,
                "total_size_bytes": 0,
                "cache_directory": str(self.db_path),
                "cache_type": cache_type or "all",
            }

        try:
            now = datetime.now(timezone.utc).isoformat()

            # Count total entries
            if cache_type:
                count_sql = "SELECT COUNT(*), SUM(response_size) FROM tmdb_cache WHERE cache_type = ?"
                cursor = self.conn.execute(count_sql, (cache_type,))
            else:
                count_sql = "SELECT COUNT(*), SUM(response_size) FROM tmdb_cache"
                cursor = self.conn.execute(count_sql)

            row = cursor.fetchone()
            total_count = row[0] if row else 0
            total_size = row[1] if row and row[1] else 0

            # Count expired entries
            if cache_type:
                expired_sql = """
                SELECT COUNT(*) FROM tmdb_cache
                WHERE expires_at IS NOT NULL AND expires_at < ? AND cache_type = ?
                """
                cursor = self.conn.execute(expired_sql, (now, cache_type))
            else:
                expired_sql = """
                SELECT COUNT(*) FROM tmdb_cache
                WHERE expires_at IS NOT NULL AND expires_at < ?
                """
                cursor = self.conn.execute(expired_sql, (now,))

            expired_count = cursor.fetchone()[0]
            valid_count = total_count - expired_count

            return {
                "total_files": total_count,
                "valid_entries": valid_count,
                "expired_entries": expired_count,
                "total_size_bytes": total_size,
                "cache_directory": str(self.db_path),
                "cache_type": cache_type or "all",
            }

        except sqlite3.Error as e:
            logger.warning("Failed to get cache info: %s", str(e))
            return {
                "total_files": 0,
                "valid_entries": 0,
                "expired_entries": 0,
                "total_size_bytes": 0,
                "cache_directory": str(self.db_path),
                "cache_type": cache_type or "all",
            }

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            try:
                self.conn.close()
                logger.debug("Closed SQLite cache database connection")
            except sqlite3.Error as e:
                logger.warning("Failed to close database connection: %s", str(e))
            finally:
                self.conn = None

