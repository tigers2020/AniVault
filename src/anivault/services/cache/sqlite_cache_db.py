"""SQLite cache database facade.

This module provides a refactored SQLite cache implementation using
modular operations for better maintainability and testability.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anivault.core.statistics import StatisticsCollector
from anivault.security.permissions import set_secure_file_permissions
from anivault.services.cache.sqlite_cache.migration.manager import MigrationManager
from anivault.services.cache.sqlite_cache.operations.insert import InsertOperations
from anivault.services.cache.sqlite_cache.operations.query import QueryOperations
from anivault.services.cache.sqlite_cache.operations.update import UpdateOperations
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
        # Store path as Path object (don't resolve here - let SQLite handle it)
        self.db_path = Path(db_path)
        self.statistics = statistics or StatisticsCollector()
        self.conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()  # Thread-safe access to SQLite connection
        self._initialize_db()

    def _cleanup_old_db_files(self) -> None:
        """Clean up old timestamped DB files from previous failed attempts.

        This method removes old timestamped DB files (e.g., tmdb_cache_1234567890.db)
        that were created when the main DB file was locked. Only keeps the most recent one.
        """
        try:
            cache_dir = self.db_path.parent
            if not cache_dir.exists():
                return

            # Find all timestamped DB files matching pattern: tmdb_cache_*.db
            # e.g., "tmdb_cache" from "tmdb_cache_1234567890"  # pylint: disable=line-too-long
            base_name = self.db_path.stem.split("_")[0]
            pattern = f"{base_name}_*.db"

            timestamped_files = []
            for file_path in cache_dir.glob(pattern):
                # Check if it's a timestamped file (has underscore and numeric suffix)
                name_parts = file_path.stem.split("_")
                if len(name_parts) >= 2:
                    try:
                        # Try to parse timestamp from filename
                        timestamp = int(name_parts[-1])
                        timestamped_files.append((timestamp, file_path))
                    except ValueError:
                        # Not a timestamped file, skip
                        continue

            if not timestamped_files:
                return

            # Sort by timestamp (newest first)
            timestamped_files.sort(key=lambda x: x[0], reverse=True)

            # Keep only the most recent file, delete the rest
            kept_count = 0
            deleted_count = 0
            for _, file_path in timestamped_files:
                try:
                    # Try to delete the file
                    if file_path.exists():
                        file_path.unlink()
                        # Also try to delete associated WAL/SHM files
                        wal_file = file_path.with_suffix(file_path.suffix + "-wal")
                        shm_file = file_path.with_suffix(file_path.suffix + "-shm")
                        if wal_file.exists():
                            wal_file.unlink()
                        if shm_file.exists():
                            shm_file.unlink()
                        deleted_count += 1
                        logger.debug("Cleaned up old timestamped DB file: %s", file_path)
                except (PermissionError, OSError) as e:
                    # File might be locked, skip it
                    logger.debug(
                        "Could not delete old DB file %s (may be locked): %s",
                        file_path,
                        e,
                    )
                    if kept_count == 0:
                        # Keep the first one we couldn't delete (might be in use)
                        kept_count += 1

            if deleted_count > 0:
                logger.info(
                    "Cleaned up %d old timestamped DB file(s), kept %d",
                    deleted_count,
                    kept_count,
                )

        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            # Don't fail initialization if cleanup fails
            logger.warning("Failed to cleanup old DB files: %s", e)

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
            # Clean up old timestamped DB files on startup
            self._cleanup_old_db_files()

            # Use path as-is (don't resolve - SQLite handles paths correctly)
            # Resolving can cause issues on Windows with certain path formats
            db_path_absolute = self.db_path
            db_path_str = str(self.db_path)

            # Check path length (Windows MAX_PATH = 260, extended = 32767)
            if len(db_path_str) > 260:
                logger.warning(
                    "Database path exceeds 260 characters: %d chars. This may cause issues on Windows.",
                    len(db_path_str),
                )

            # Create parent directory with error handling
            try:
                db_path_absolute.parent.mkdir(parents=True, exist_ok=True)
                logger.debug(
                    "Cache directory created/verified: %s",
                    db_path_absolute.parent,
                )
            except PermissionError as e:
                error = InfrastructureError(
                    code=ErrorCode.PERMISSION_DENIED,
                    message=(f"Cannot create cache directory: {db_path_absolute.parent}. Permission denied. Check directory permissions."),
                    context=context,
                    original_error=e,
                )
                logger.exception(
                    "Permission denied creating cache directory: %s",
                    db_path_absolute.parent,
                )
                raise error from e
            except OSError as e:
                error = InfrastructureError(
                    code=ErrorCode.FILE_ACCESS_ERROR,
                    message=(f"Cannot create cache directory: {db_path_absolute.parent}. OS error: {e!s}"),
                    context=context,
                    original_error=e,
                )
                logger.exception(
                    "Failed to create cache directory: %s",
                    db_path_absolute.parent,
                )
                raise error from e

            # Verify parent directory is writable
            if not db_path_absolute.parent.exists():
                error = InfrastructureError(
                    code=ErrorCode.FILE_ACCESS_ERROR,
                    message=(f"Cache directory does not exist after creation: {db_path_absolute.parent}"),
                    context=context,
                )
                logger.error("Cache directory missing: %s", db_path_absolute.parent)
                raise error

            # Test write permissions by creating a temporary file
            try:
                test_file = db_path_absolute.parent / ".anivault_write_test"
                test_file.touch()
                test_file.unlink()
                logger.debug(
                    "Write permission test passed for: %s",
                    db_path_absolute.parent,
                )
            except PermissionError as e:
                error = InfrastructureError(
                    code=ErrorCode.PERMISSION_DENIED,
                    message=(f"Cache directory is not writable: {db_path_absolute.parent}. Check directory permissions."),
                    context=context,
                    original_error=e,
                )
                logger.exception(
                    "Cache directory not writable: %s",
                    db_path_absolute.parent,
                )
                raise error from e
            # pylint: disable-next=broad-exception-caught

            # pylint: disable-next=broad-exception-caught

            except Exception as e:  # pylint: disable=broad-exception-caught  # noqa: BLE001
                # Log unexpected errors during write test but continue
                logger.warning(
                    "Unexpected error during write test (continuing): %s",
                    e,
                )

            # Verify directory is actually a directory (not a file)
            if not db_path_absolute.parent.is_dir():
                error = InfrastructureError(
                    code=ErrorCode.FILE_ACCESS_ERROR,
                    message=(f"Cache path exists but is not a directory: {db_path_absolute.parent}"),
                    context=context,
                )
                logger.error("Cache path is not a directory: %s", db_path_absolute.parent)
                raise error

            # Check if existing DB file is accessible
            # If it exists but is corrupted/locked, remove it and create a new one
            db_is_new = not db_path_absolute.exists()

            if not db_is_new:
                # Try to open existing file to check if it's accessible
                wal_file = db_path_absolute.with_suffix(db_path_absolute.suffix + "-wal")
                # pylint: disable-next=unused-variable
                shm_file = db_path_absolute.with_suffix(db_path_absolute.suffix + "-shm")

                try:
                    # Quick test connection
                    test_conn = sqlite3.connect(
                        str(db_path_absolute),
                        check_same_thread=False,
                        isolation_level=None,
                    )
                    test_conn.close()
                    logger.debug("Existing DB file is accessible: %s", db_path_absolute)
                except sqlite3.OperationalError as test_error:
                    # DB is locked or corrupted - try to remove it and all related files
                    logger.warning(
                        "Existing database file is inaccessible (locked or corrupted): %s. Attempting to remove and recreate. Error: %s",
                        db_path_absolute,
                        test_error,
                    )
                    try:
                        # Try to remove lock files first (they might be easier to remove)
                        if wal_file.exists():
                            wal_file.unlink()
                            logger.info("Removed stale WAL file: %s", wal_file)
                        if shm_file.exists():
                            shm_file.unlink()
                            logger.info("Removed stale SHM file: %s", shm_file)

                        # Try to remove main DB file
                        if db_path_absolute.exists():
                            db_path_absolute.unlink()
                            logger.info("Removed corrupted DB file: %s", db_path_absolute)
                            db_is_new = True  # Mark as new so we create fresh DB
                    except PermissionError:
                        # File is locked by another process - try waiting a bit and retry
                        logger.debug(
                            "Cannot remove locked database file (may be in use): %s. "  # pylint: disable=line-too-long
                            "Waiting briefly and retrying...",
                            db_path_absolute,
                        )
                        time.sleep(0.5)  # Wait 500ms for lock to be released

                        try:
                            # Retry deletion
                            if db_path_absolute.exists():
                                db_path_absolute.unlink()
                                logger.info(
                                    "Successfully removed locked DB file after retry: %s",  # pylint: disable=line-too-long
                                    db_path_absolute,
                                )
                                db_is_new = True
                        except (PermissionError, OSError):
                            # Still locked - use alternative filename as last resort
                            logger.warning(
                                "Database file still locked after retry: %s. Using alternative filename.",
                                db_path_absolute,
                            )
                            # Generate alternative filename with timestamp
                            timestamp = int(time.time())
                            alt_name = (
                                db_path_absolute.stem + f"_{timestamp}" + db_path_absolute.suffix  # pylint: disable=line-too-long
                            )
                            self.db_path = db_path_absolute.parent / alt_name
                            db_path_absolute = self.db_path
                            db_is_new = True
                            logger.info("Using alternative DB filename: %s", self.db_path)
                    except Exception:  # pylint: disable=broad-exception-caught
                        logger.exception(
                            "Failed to remove corrupted DB files (will use alternative filename): %s",
                            db_path_absolute,
                        )
                        # Use alternative filename as fallback
                        timestamp = int(time.time())
                        alt_name = db_path_absolute.stem + f"_{timestamp}" + db_path_absolute.suffix
                        self.db_path = db_path_absolute.parent / alt_name
                        db_path_absolute = self.db_path
                        db_is_new = True
                        logger.info(
                            "Using alternative DB filename due to cleanup failure: %s",
                            self.db_path,
                        )

            logger.debug(
                "Attempting to create/open SQLite database at: %s (new: %s)",  # pylint: disable=line-too-long
                db_path_absolute,
                db_is_new,
            )

            # Connect with WAL mode for concurrency
            # Match the working implementation in sqlite_cache/cache_db.py exactly  # pylint: disable=line-too-long
            try:
                # Use simple path string - match the working implementation exactly
                # Don't use resolve() - it can cause issues on Windows
                db_path_str = str(self.db_path)

                logger.debug("Connecting to SQLite with path: %s", db_path_str)
                # Match the exact parameters from the working implementation
                # Don't use timeout parameter - it may cause issues on Windows
                self.conn = sqlite3.connect(
                    db_path_str,
                    check_same_thread=False,  # Safe with WAL mode  # pylint: disable=line-too-long
                    isolation_level=None,  # Auto-commit mode
                )
                logger.debug("SQLite connection established successfully")
            except sqlite3.OperationalError as e:
                # Provide more detailed error message
                error_msg = str(e)
                if "unable to open database file" in error_msg.lower():
                    detailed_msg = (
                        f"Cannot open SQLite database: {db_path_absolute}\n"
                        f"Absolute path: {db_path_absolute.resolve()}\n"
                        f"Parent directory exists: {db_path_absolute.parent.exists()}\n"
                        f"Parent directory is writable: {os.access(db_path_absolute.parent, os.W_OK) if db_path_absolute.parent.exists() else False}\n"
                        f"Possible causes:\n"
                        f"  1. Directory permissions: {db_path_absolute.parent}\n"
                        f"  2. Path too long (Windows limit: 260 chars, "
                        f"current: {len(db_path_str)})\n"
                        f"  3. Disk full or filesystem error\n"
                        f"  4. Antivirus blocking file access\n"
                        f"  5. File already locked by another process\n"
                        f"Try:\n"
                        f"  - Check directory permissions\n"
                        f"  - Verify disk space\n"
                        f"  - Check antivirus settings\n"
                        f"  - Close any other applications using the database\n"
                        f"  - Use shorter path if possible"
                    )
                else:
                    detailed_msg = f"Cannot open SQLite database: {db_path_absolute}\nError: {error_msg}"

                error = InfrastructureError(
                    code=ErrorCode.FILE_ACCESS_ERROR,
                    message=detailed_msg,
                    context=context,
                    original_error=e,
                )
                logger.exception(
                    "Failed to open SQLite database: %s\n%s",
                    db_path_absolute,
                    detailed_msg,
                )
                raise error from e

            # Set secure permissions for newly created DB files
            if db_is_new:
                try:
                    set_secure_file_permissions(self.db_path)
                    logger.info(
                        "Secure permissions (600) set for new DB: %s",
                        self.db_path,
                    )
                # pylint: disable-next=broad-exception-caught

                # pylint: disable-next=broad-exception-caught

                except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
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
            # pylint: disable-next=broad-exception-caught

            # pylint: disable-next=broad-exception-caught

            except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
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
        with self._lock:
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
        with self._lock:
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
        cursor.close()

        # Get valid (non-expired) entries
        now = datetime.now(timezone.utc)
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM tmdb_cache WHERE expires_at IS NULL OR expires_at > ?",
            (now.isoformat(),),
        )
        valid_entries = cursor.fetchone()[0]
        cursor.close()

        # Calculate total size
        cursor = self.conn.execute("SELECT SUM(response_size) FROM tmdb_cache")
        total_size_bytes = cursor.fetchone()[0] or 0
        cursor.close()

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
