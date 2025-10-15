"""Unit tests for BackupManager.

Tests follow the Failure-First pattern:
1. Test failure cases first
2. Test edge cases
3. Test happy path
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anivault.services.sqlite_cache import SQLiteCacheDB
from anivault.services.sqlite_cache.backup import BackupManager
from anivault.shared.constants import Cache


class TestBackupManagerCreateBackup:
    """Test BackupManager.create_backup() method."""

    def test_create_backup_success(self, tmp_path: Path) -> None:
        """Create backup should successfully copy database file."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("test:key", {"data": "test"}, cache_type=Cache.TYPE_SEARCH)

        backup_manager = BackupManager(db_path)

        # When
        backup_path = backup_manager.create_backup()

        # Then
        assert backup_path.exists()
        assert backup_path.suffix == ".db"
        assert "cache_" in backup_path.stem

        # Verify backup is valid
        cache2 = SQLiteCacheDB(backup_path)
        result = cache2.get("test:key", cache_type=Cache.TYPE_SEARCH)
        assert result is not None
        assert result == {"data": "test"}

        cache.close()
        cache2.close()

    def test_create_backup_with_suffix(self, tmp_path: Path) -> None:
        """Create backup should include suffix in filename."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("test:key", {"data": "test"}, cache_type=Cache.TYPE_SEARCH)

        backup_manager = BackupManager(db_path)

        # When
        backup_path = backup_manager.create_backup(suffix="manual")

        # Then
        assert backup_path.exists()
        assert "manual" in backup_path.stem

        cache.close()

    def test_create_backup_nonexistent_db_raises_error(self, tmp_path: Path) -> None:
        """Create backup should raise FileNotFoundError for non-existent database."""
        # Given
        db_path = tmp_path / "nonexistent.db"
        backup_manager = BackupManager(db_path)

        # When & Then
        with pytest.raises(FileNotFoundError):
            backup_manager.create_backup()

    def test_create_backup_cleanup_old_backups(self, tmp_path: Path) -> None:
        """Create backup should clean up old backups."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("test:key", {"data": "test"}, cache_type=Cache.TYPE_SEARCH)

        backup_manager = BackupManager(db_path)

        # When - Create more backups than max_backups
        for i in range(12):  # max_backups is 10
            cache.set_cache(
                f"test:key{i}", {"data": f"test{i}"}, cache_type=Cache.TYPE_SEARCH
            )
            backup_manager.create_backup()

        # Then - Only 10 backups should exist
        backups = backup_manager.list_backups()
        assert len(backups) == 10

        cache.close()


class TestBackupManagerRestoreBackup:
    """Test BackupManager.restore_backup() method."""

    def test_restore_backup_success(self, tmp_path: Path) -> None:
        """Restore backup should successfully restore database."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("test:key", {"data": "original"}, cache_type=Cache.TYPE_SEARCH)

        backup_manager = BackupManager(db_path)
        backup_path = backup_manager.create_backup()

        # Modify database
        cache.set_cache("test:key", {"data": "modified"}, cache_type=Cache.TYPE_SEARCH)
        cache.close()

        # When
        backup_manager.restore_backup(backup_path)

        # Then - Database should be restored
        cache2 = SQLiteCacheDB(db_path)
        result = cache2.get("test:key", cache_type=Cache.TYPE_SEARCH)
        assert result is not None
        assert result == {"data": "original"}

        cache2.close()

    def test_restore_backup_with_pre_backup(self, tmp_path: Path) -> None:
        """Restore backup should create backup of current database."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("test:key", {"data": "original"}, cache_type=Cache.TYPE_SEARCH)

        backup_manager = BackupManager(db_path)
        backup_path = backup_manager.create_backup()

        # Modify database
        cache.set_cache("test:key", {"data": "modified"}, cache_type=Cache.TYPE_SEARCH)
        cache.close()

        # When
        backup_manager.restore_backup(backup_path, create_backup=True)

        # Then - Pre-restore backup should exist
        backups = backup_manager.list_backups()
        pre_restore_backups = [b for b in backups if "pre_restore" in b.stem]
        assert len(pre_restore_backups) == 1

    def test_restore_backup_nonexistent_file_raises_error(self, tmp_path: Path) -> None:
        """Restore backup should raise FileNotFoundError for non-existent backup."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        backup_manager = BackupManager(db_path)
        nonexistent_backup = tmp_path / "nonexistent.db"

        # When & Then
        with pytest.raises(FileNotFoundError):
            backup_manager.restore_backup(nonexistent_backup)

        cache.close()


class TestBackupManagerListBackups:
    """Test BackupManager.list_backups() method."""

    def test_list_backups_returns_sorted_list(self, tmp_path: Path) -> None:
        """List backups should return backups sorted by modification time."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        backup_manager = BackupManager(db_path)

        # Create multiple backups
        for i in range(3):
            cache.set_cache(
                f"test:key{i}", {"data": f"test{i}"}, cache_type=Cache.TYPE_SEARCH
            )
            backup_manager.create_backup()

        # When
        backups = backup_manager.list_backups()

        # Then
        assert len(backups) == 3
        # Verify sorted by modification time (newest first)
        for i in range(len(backups) - 1):
            assert backups[i].stat().st_mtime >= backups[i + 1].stat().st_mtime

        cache.close()

    def test_list_backups_empty_returns_empty_list(self, tmp_path: Path) -> None:
        """List backups should return empty list when no backups exist."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        backup_manager = BackupManager(db_path)

        # When
        backups = backup_manager.list_backups()

        # Then
        assert len(backups) == 0

        cache.close()


class TestBackupManagerGetLatestBackup:
    """Test BackupManager.get_latest_backup() method."""

    def test_get_latest_backup_returns_newest(self, tmp_path: Path) -> None:
        """Get latest backup should return most recent backup."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        backup_manager = BackupManager(db_path)

        # Create multiple backups
        for i in range(3):
            cache.set_cache(
                f"test:key{i}", {"data": f"test{i}"}, cache_type=Cache.TYPE_SEARCH
            )
            backup_manager.create_backup()

        # When
        latest = backup_manager.get_latest_backup()

        # Then
        assert latest is not None
        assert latest.exists()
        # Verify it's the newest
        backups = backup_manager.list_backups()
        assert latest == backups[0]

        cache.close()

    def test_get_latest_backup_returns_none_when_no_backups(
        self, tmp_path: Path
    ) -> None:
        """Get latest backup should return None when no backups exist."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        backup_manager = BackupManager(db_path)

        # When
        latest = backup_manager.get_latest_backup()

        # Then
        assert latest is None

        cache.close()


class TestBackupManagerDeleteBackup:
    """Test BackupManager.delete_backup() method."""

    def test_delete_backup_success(self, tmp_path: Path) -> None:
        """Delete backup should successfully remove backup file."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        backup_manager = BackupManager(db_path)

        backup_path = backup_manager.create_backup()
        assert backup_path.exists()

        # When
        backup_manager.delete_backup(backup_path)

        # Then
        assert not backup_path.exists()

        cache.close()

    def test_delete_backup_nonexistent_file_raises_error(self, tmp_path: Path) -> None:
        """Delete backup should raise FileNotFoundError for non-existent backup."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        backup_manager = BackupManager(db_path)
        nonexistent_backup = tmp_path / "nonexistent.db"

        # When & Then
        with pytest.raises(FileNotFoundError):
            backup_manager.delete_backup(nonexistent_backup)

        cache.close()


class TestBackupManagerGetBackupInfo:
    """Test BackupManager.get_backup_info() method."""

    def test_get_backup_info_returns_correct_info(self, tmp_path: Path) -> None:
        """Get backup info should return correct information."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        backup_manager = BackupManager(db_path)

        backup_path = backup_manager.create_backup()

        # When
        info = backup_manager.get_backup_info(backup_path)

        # Then
        assert info["path"] == str(backup_path)
        assert info["size"] > 0
        assert "created" in info
        assert "modified" in info

        cache.close()

    def test_get_backup_info_nonexistent_file_raises_error(
        self, tmp_path: Path
    ) -> None:
        """Get backup info should raise FileNotFoundError for non-existent backup."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        backup_manager = BackupManager(db_path)
        nonexistent_backup = tmp_path / "nonexistent.db"

        # When & Then
        with pytest.raises(FileNotFoundError):
            backup_manager.get_backup_info(nonexistent_backup)

        cache.close()


class TestSQLiteCacheDBBackupIntegration:
    """Integration tests for SQLiteCacheDB backup functionality."""

    def test_cache_create_backup(self, tmp_path: Path) -> None:
        """SQLiteCacheDB should support backup creation."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("test:key", {"data": "test"}, cache_type=Cache.TYPE_SEARCH)

        # When
        backup_path = cache.create_backup()

        # Then
        assert backup_path.exists()
        assert backup_path.suffix == ".db"

        cache.close()

    def test_cache_restore_backup(self, tmp_path: Path) -> None:
        """SQLiteCacheDB should support backup restoration."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("test:key", {"data": "original"}, cache_type=Cache.TYPE_SEARCH)
        cache.close()

        backup_path = cache.create_backup()

        # Modify database
        cache2 = SQLiteCacheDB(db_path)
        cache2.set_cache("test:key", {"data": "modified"}, cache_type=Cache.TYPE_SEARCH)
        cache2.close()

        # When - Restore backup
        backup_manager = BackupManager(db_path)
        backup_manager.restore_backup(backup_path, create_backup=False)

        # Then - Open new connection to verify restore
        cache3 = SQLiteCacheDB(db_path)
        result = cache3.get("test:key", cache_type=Cache.TYPE_SEARCH)
        assert result is not None
        assert result == {"data": "original"}

        cache3.close()

    def test_cache_list_backups(self, tmp_path: Path) -> None:
        """SQLiteCacheDB should support listing backups."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)

        # Create multiple backups
        for i in range(3):
            cache.set_cache(
                f"test:key{i}", {"data": f"test{i}"}, cache_type=Cache.TYPE_SEARCH
            )
            cache.create_backup()

        # When
        backups = cache.list_backups()

        # Then
        assert len(backups) == 3

        cache.close()

    def test_cache_get_latest_backup(self, tmp_path: Path) -> None:
        """SQLiteCacheDB should support getting latest backup."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("test:key", {"data": "test"}, cache_type=Cache.TYPE_SEARCH)

        cache.create_backup()

        # When
        latest = cache.get_latest_backup()

        # Then
        assert latest is not None
        assert latest.exists()

        cache.close()

    def test_cache_delete_backup(self, tmp_path: Path) -> None:
        """SQLiteCacheDB should support deleting backups."""
        # Given
        db_path = tmp_path / "cache.db"
        cache = SQLiteCacheDB(db_path)
        cache.set_cache("test:key", {"data": "test"}, cache_type=Cache.TYPE_SEARCH)

        backup_path = cache.create_backup()
        assert backup_path.exists()

        # When
        cache.delete_backup(backup_path)

        # Then
        assert not backup_path.exists()

        cache.close()
