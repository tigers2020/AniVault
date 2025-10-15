"""Backup manager for SQLite cache database.

This module provides backup and restore functionality for SQLite cache databases.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backup and restore operations for SQLite cache database."""

    def __init__(
        self,
        db_path: Path,
        backup_dir: Path | None = None,
    ) -> None:
        """Initialize backup manager.

        Args:
            db_path: Path to SQLite database file
            backup_dir: Directory for backup files (default: db_path.parent / "backups")
        """
        self.db_path = Path(db_path)
        self.backup_dir = backup_dir or self.db_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        suffix: str | None = None,
        max_backups: int = 10,
    ) -> Path:
        """Create a backup of the database file.

        Args:
            suffix: Optional suffix for backup filename
            max_backups: Maximum number of backups to keep (oldest deleted)

        Returns:
            Path to created backup file

        Raises:
            FileNotFoundError: If database file doesn't exist
            OSError: If backup operation fails
        """
        if not self.db_path.exists():
            msg = f"Database file not found: {self.db_path}"
            raise FileNotFoundError(msg)

        # Generate backup filename with timestamp (include microseconds for uniqueness)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        if suffix:
            backup_filename = f"{self.db_path.stem}_{timestamp}_{suffix}.db"
        else:
            backup_filename = f"{self.db_path.stem}_{timestamp}.db"

        backup_path = self.backup_dir / backup_filename

        try:
            # Copy database file
            shutil.copy2(self.db_path, backup_path)

            # Copy WAL file if exists
            wal_path = self.db_path.with_suffix(".db-wal")
            if wal_path.exists():
                backup_wal_path = backup_path.with_suffix(".db-wal")
                shutil.copy2(wal_path, backup_wal_path)

            # Copy SHM file if exists
            shm_path = self.db_path.with_suffix(".db-shm")
            if shm_path.exists():
                backup_shm_path = backup_path.with_suffix(".db-shm")
                shutil.copy2(shm_path, backup_shm_path)

            logger.info(
                "Backup created: %s (size: %s bytes)",
                backup_path,
                backup_path.stat().st_size,
            )

            # Clean up old backups
            self._cleanup_old_backups(max_backups)

            return backup_path

        except Exception:
            logger.exception("Failed to create backup")
            raise

    def restore_backup(
        self,
        backup_path: Path,
        create_backup: bool = True,
    ) -> None:
        """Restore database from backup file.

        Args:
            backup_path: Path to backup file
            create_backup: If True, create backup of current database before restore

        Raises:
            FileNotFoundError: If backup file doesn't exist
            OSError: If restore operation fails
        """
        if not backup_path.exists():
            msg = f"Backup file not found: {backup_path}"
            raise FileNotFoundError(msg)

        try:
            # Create backup of current database if it exists
            if self.db_path.exists() and create_backup:
                logger.info("Creating backup of current database before restore")
                self.create_backup(suffix="pre_restore")

            # Restore database file
            shutil.copy2(backup_path, self.db_path)

            # Restore WAL file if exists
            backup_wal_path = backup_path.with_suffix(".db-wal")
            if backup_wal_path.exists():
                wal_path = self.db_path.with_suffix(".db-wal")
                shutil.copy2(backup_wal_path, wal_path)

            # Restore SHM file if exists (may fail on Windows if DB is open)
            backup_shm_path = backup_path.with_suffix(".db-shm")
            if backup_shm_path.exists():
                shm_path = self.db_path.with_suffix(".db-shm")
                try:
                    shutil.copy2(backup_shm_path, shm_path)
                except OSError as e:
                    logger.warning(
                        "Failed to restore SHM file (may be in use): %s",
                        e,
                    )

            logger.info("Database restored from: %s", backup_path)

        except Exception:
            logger.exception("Failed to restore backup")
            raise

    def list_backups(self) -> list[Path]:
        """List all available backup files.

        Returns:
            List of backup file paths, sorted by modification time (newest first)
        """
        backups = sorted(
            self.backup_dir.glob(f"{self.db_path.stem}_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return backups

    def get_latest_backup(self) -> Path | None:
        """Get the most recent backup file.

        Returns:
            Path to latest backup, or None if no backups exist
        """
        backups = self.list_backups()
        return backups[0] if backups else None

    def delete_backup(self, backup_path: Path) -> None:
        """Delete a backup file.

        Args:
            backup_path: Path to backup file to delete

        Raises:
            FileNotFoundError: If backup file doesn't exist
        """
        if not backup_path.exists():
            msg = f"Backup file not found: {backup_path}"
            raise FileNotFoundError(msg)

        try:
            # Delete database file
            backup_path.unlink()

            # Delete WAL file if exists
            wal_path = backup_path.with_suffix(".db-wal")
            if wal_path.exists():
                wal_path.unlink()

            # Delete SHM file if exists
            shm_path = backup_path.with_suffix(".db-shm")
            if shm_path.exists():
                shm_path.unlink()

            logger.info("Backup deleted: %s", backup_path)

        except Exception:
            logger.exception("Failed to delete backup")
            raise

    def _cleanup_old_backups(self, max_backups: int) -> None:
        """Delete old backup files, keeping only the most recent ones.

        Args:
            max_backups: Maximum number of backups to keep
        """
        backups = self.list_backups()
        if len(backups) <= max_backups:
            return

        # Delete oldest backups
        for backup in backups[max_backups:]:
            try:
                self.delete_backup(backup)
            except (FileNotFoundError, OSError, PermissionError) as e:
                logger.warning("Failed to delete old backup %s: %s", backup, e)

    def get_backup_info(self, backup_path: Path) -> dict[str, str | int]:
        """Get information about a backup file.

        Args:
            backup_path: Path to backup file

        Returns:
            Dictionary with backup information

        Raises:
            FileNotFoundError: If backup file doesn't exist
        """
        if not backup_path.exists():
            msg = f"Backup file not found: {backup_path}"
            raise FileNotFoundError(msg)

        stat = backup_path.stat()

        return {
            "path": str(backup_path),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(
                stat.st_ctime, tz=timezone.utc
            ).isoformat(),
            "modified": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
        }
