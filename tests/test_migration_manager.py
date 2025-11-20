"""Unit tests for SQLite cache migration manager.

This module tests MigrationManager to ensure schema migration
works correctly with proper version tracking and rollback.
"""

from __future__ import annotations

import sqlite3

import pytest

from anivault.services.sqlite_cache.migration.manager import MigrationManager


@pytest.fixture
def temp_db() -> sqlite3.Connection:
    """Create a temporary SQLite database for testing."""
    return sqlite3.connect(":memory:")


@pytest.fixture
def migration_manager(temp_db: sqlite3.Connection) -> MigrationManager:
    """Create MigrationManager instance."""
    return MigrationManager(temp_db)


class TestMigrationManager:
    """Test MigrationManager."""

    def test_initial_version_is_zero(self, migration_manager: MigrationManager) -> None:
        """Test that new database starts at version 0."""
        assert migration_manager.get_current_version() == 0

    def test_create_tables_sets_version_to_one(
        self, migration_manager: MigrationManager
    ) -> None:
        """Test that create_tables() sets version to 1."""
        migration_manager.create_tables()

        assert migration_manager.get_current_version() == 1

    def test_create_tables_creates_required_tables(
        self, migration_manager: MigrationManager, temp_db: sqlite3.Connection
    ) -> None:
        """Test that create_tables() creates required tables."""
        migration_manager.create_tables()

        # Check if tables exist
        cursor = temp_db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "tmdb_cache" in tables
        assert "schema_version" in tables

    def test_create_tables_creates_indexes(
        self, migration_manager: MigrationManager, temp_db: sqlite3.Connection
    ) -> None:
        """Test that create_tables() creates required indexes."""
        migration_manager.create_tables()

        # Check if indexes exist
        cursor = temp_db.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        assert "idx_key_hash" in indexes
        assert "idx_cache_type" in indexes
        assert "idx_expires_at" in indexes
        assert "idx_last_accessed" in indexes

    def test_migrate_to_same_version_no_op(
        self, migration_manager: MigrationManager
    ) -> None:
        """Test that migrating to current version is a no-op."""
        migration_manager.create_tables()

        # Should not raise any exception
        migration_manager.migrate_to(1)

        assert migration_manager.get_current_version() == 1

    def test_migrate_to_invalid_version_raises_error(
        self, migration_manager: MigrationManager
    ) -> None:
        """Test that migrating to invalid version raises error."""
        with pytest.raises(ValueError, match="Invalid target version"):
            migration_manager.migrate_to(-1)

    def test_get_migration_history(self, migration_manager: MigrationManager) -> None:
        """Test getting migration history."""
        migration_manager.create_tables()

        history = migration_manager.get_migration_history()

        assert len(history) == 1
        assert history[0]["version"] == 1
        assert "applied_at" in history[0]

    def test_get_migration_history_empty_database(
        self, migration_manager: MigrationManager
    ) -> None:
        """Test getting migration history from empty database."""
        history = migration_manager.get_migration_history()

        assert history == []

    def test_validate_schema_valid(self, migration_manager: MigrationManager) -> None:
        """Test schema validation with valid schema."""
        migration_manager.create_tables()

        assert migration_manager.validate_schema() is True

    def test_validate_schema_invalid_missing_table(
        self, migration_manager: MigrationManager, temp_db: sqlite3.Connection
    ) -> None:
        """Test schema validation with missing table."""
        # Create only one table
        temp_db.execute(
            """
            CREATE TABLE tmdb_cache (
                id INTEGER PRIMARY KEY,
                cache_key TEXT
            )
        """
        )

        assert migration_manager.validate_schema() is False

    def test_migrate_to_higher_version_not_supported(
        self, migration_manager: MigrationManager
    ) -> None:
        """Test that migrating to unsupported version raises error."""
        migration_manager.create_tables()

        with pytest.raises(RuntimeError, match="Migration to version 2 failed"):
            migration_manager.migrate_to(2)

    def test_migrate_to_lower_version_not_supported(
        self, migration_manager: MigrationManager
    ) -> None:
        """Test that downgrading to version 0 raises error."""
        migration_manager.create_tables()

        with pytest.raises(RuntimeError, match="Migration from version 1 failed"):
            migration_manager.migrate_to(0)

    def test_schema_version_table_tracking(
        self, migration_manager: MigrationManager, temp_db: sqlite3.Connection
    ) -> None:
        """Test that schema_version table tracks versions correctly."""
        migration_manager.create_tables()

        # Check schema_version table
        cursor = temp_db.execute("SELECT version FROM schema_version")
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == 1

    def test_create_tables_is_idempotent(
        self, migration_manager: MigrationManager
    ) -> None:
        """Test that create_tables() can be called multiple times safely."""
        migration_manager.create_tables()
        version_after_first = migration_manager.get_current_version()

        migration_manager.create_tables()
        version_after_second = migration_manager.get_current_version()

        assert version_after_first == 1
        assert version_after_second == 1

    def test_validate_schema_checks_table_structure(
        self, migration_manager: MigrationManager, temp_db: sqlite3.Connection
    ) -> None:
        """Test that validate_schema() checks table structure."""
        migration_manager.create_tables()

        # Verify schema is valid
        assert migration_manager.validate_schema() is True

        # Drop a required table
        temp_db.execute("DROP TABLE schema_version")

        # Verify schema is now invalid
        assert migration_manager.validate_schema() is False

    def test_migration_history_ordering(
        self, migration_manager: MigrationManager
    ) -> None:
        """Test that migration history is ordered by version."""
        migration_manager.create_tables()

        history = migration_manager.get_migration_history()

        assert len(history) == 1
        assert history[0]["version"] == 1

    def test_get_current_version_after_create(
        self, migration_manager: MigrationManager
    ) -> None:
        """Test get_current_version() after create_tables()."""
        assert migration_manager.get_current_version() == 0

        migration_manager.create_tables()

        assert migration_manager.get_current_version() == 1

    def test_schema_version_table_has_timestamp(
        self, migration_manager: MigrationManager, temp_db: sqlite3.Connection
    ) -> None:
        """Test that schema_version table includes timestamp."""
        migration_manager.create_tables()

        cursor = temp_db.execute("SELECT applied_at FROM schema_version")
        row = cursor.fetchone()

        assert row is not None
        assert row[0] is not None

    def test_validate_schema_checks_version_validity(
        self, migration_manager: MigrationManager, temp_db: sqlite3.Connection
    ) -> None:
        """Test that validate_schema() checks version validity."""
        migration_manager.create_tables()

        # Corrupt version in database
        temp_db.execute("UPDATE schema_version SET version = -1")

        # Verify schema validation fails
        assert migration_manager.validate_schema() is False
