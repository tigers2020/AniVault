"""Migration manager for SQLite cache.

This module provides database schema migration management.
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)


class MigrationManager:
    """Database schema migration manager."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Initialize migration manager.

        Args:
            conn: SQLite database connection
        """
        self.conn = conn
        self._current_version = self._get_current_version()

    def get_current_version(self) -> int:
        """Get current schema version.

        Returns:
            Current schema version number
        """
        return self._current_version

    def _get_current_version(self) -> int:
        """Get current schema version from database.

        Returns:
            Current schema version (0 if not set)
        """
        # Check if schema_version table exists
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        if cursor.fetchone() is None:
            return 0

        # Get version
        cursor = self.conn.execute("SELECT version FROM schema_version LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else 0

    def create_tables(self) -> None:
        """Create database schema (v1)."""
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

        -- Schema version tracking
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        );
        """

        self.conn.executescript(schema_sql)

        # Set version to 1
        self.conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (1)")
        self._current_version = 1

        logger.info("Created database schema (v1)")

    def migrate_to(self, target_version: int) -> None:
        """Migrate database to target version.

        Args:
            target_version: Target schema version

        Raises:
            ValueError: If target version is invalid
            RuntimeError: If migration fails
        """
        if target_version < 0:
            msg = f"Invalid target version: {target_version}"
            raise ValueError(msg)

        if target_version == self._current_version:
            logger.info("Already at target version %d", target_version)
            return

        if target_version > self._current_version:
            self._upgrade(target_version)
        else:
            self._downgrade(target_version)

    def _upgrade(self, target_version: int) -> None:
        """Upgrade database to target version.

        Args:
            target_version: Target schema version

        Raises:
            RuntimeError: If upgrade fails
        """
        logger.info(
            "Upgrading from version %d to %d", self._current_version, target_version
        )

        for version in range(self._current_version + 1, target_version + 1):
            try:
                self._apply_migration(version, direction="up")
            except Exception as e:
                logger.exception("Failed to apply migration to version %d", version)
                error_msg = f"Migration to version {version} failed: {e!s}"
                raise RuntimeError(error_msg) from e

        logger.info("Successfully upgraded to version %d", target_version)

    def _downgrade(self, target_version: int) -> None:
        """Downgrade database to target version.

        Args:
            target_version: Target schema version

        Raises:
            RuntimeError: If downgrade fails
        """
        logger.info(
            "Downgrading from version %d to %d", self._current_version, target_version
        )

        for version in range(self._current_version, target_version, -1):
            try:
                self._apply_migration(version, direction="down")
            except Exception as e:
                logger.exception("Failed to apply migration from version %d", version)
                error_msg = f"Migration from version {version} failed: {e!s}"
                raise RuntimeError(error_msg) from e

        logger.info("Successfully downgraded to version %d", target_version)

    def _apply_migration(self, version: int, direction: str) -> None:
        """Apply a single migration script.

        Args:
            version: Migration version
            direction: 'up' for upgrade, 'down' for downgrade

        Raises:
            FileNotFoundError: If migration script not found
            RuntimeError: If migration script execution fails
        """
        # For now, we only support v1 (initial schema)
        # Future migrations would be loaded from migration scripts directory
        if version == 1 and direction == "up":
            # Initial schema is already created by create_tables()
            self._current_version = 1
            logger.info("Applied migration v1 (initial schema)")
        else:
            msg = f"Migration script for version {version} ({direction}) not found"
            raise FileNotFoundError(msg)

    def get_migration_history(self) -> list[dict[str, int | str]]:
        """Get migration history.

        Returns:
            List of migration records with version and applied_at timestamp
        """
        try:
            cursor = self.conn.execute(
                "SELECT version, applied_at FROM schema_version ORDER BY version"
            )
            return [
                {"version": row[0], "applied_at": row[1]} for row in cursor.fetchall()
            ]
        except (sqlite3.Error, AttributeError):
            return []

    def validate_schema(self) -> bool:
        """Validate current schema integrity.

        Returns:
            True if schema is valid, False otherwise
        """
        try:
            # Check if required tables exist
            required_tables = ["tmdb_cache", "schema_version"]

            for table in required_tables:
                cursor = self.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                if cursor.fetchone() is None:
                    logger.error("Required table '%s' not found", table)
                    return False

            # Check schema version
            version = self._get_current_version()
            if version < 0:
                logger.error("Invalid schema version: %d", version)
                return False

            logger.info("Schema validation passed (version %d)", version)
            return True

        except Exception:
            logger.exception("Schema validation failed")
            return False
