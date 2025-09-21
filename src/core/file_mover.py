"""Transactional file movement system with robust error handling.

This module provides functionality to safely move and rename files with
transactional guarantees, including rollback capabilities and comprehensive
error handling.
"""

import os
import re
import shutil
import tempfile
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ..utils.logger import get_logger
from .exceptions import (
    MoveConflictError,
    MoveDiskSpaceError,
    MovePermissionError,
    MoveRollbackError,
    MoveValidationError,
)
from .file_classifier import FileClassifier
from .file_namer import FileNamer
from .logging_utils import log_operation_error
from .models import AnimeFile, FileGroup


class MoveOperation(Enum):
    """Types of file movement operations."""

    MOVE = "move"
    COPY = "copy"
    RENAME = "rename"
    DELETE = "delete"


@dataclass
class MoveTransaction:
    """Represents a file movement transaction."""

    transaction_id: str
    operations: list[dict[str, Any]]
    created_at: float
    status: str = "pending"  # pending, committed, rolled_back, failed
    rollback_operations: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.rollback_operations is None:
            self.rollback_operations = []


@dataclass
class MoveResult:
    """Result of a file movement operation."""

    success: bool
    source_path: Path
    target_path: Path
    operation: MoveOperation
    transaction_id: str | None = None
    error_message: str | None = None
    rollback_required: bool = False
    file_size: int = 0
    duration: float = 0.0


class FileMover:
    """Handles transactional file movement operations.

    This class provides methods to:
    - Move files with transactional guarantees
    - Handle conflicts and naming issues
    - Provide rollback capabilities
    - Validate file operations
    - Log all operations for audit
    """

    def __init__(self, temp_dir: Path | None = None) -> None:
        """Initialize the file mover.

        Args:
            temp_dir: Directory for temporary files (uses system temp if None)
        """
        self.temp_dir = temp_dir or Path(tempfile.gettempdir()) / "anivault_moves"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.classifier = FileClassifier()
        self.namer = FileNamer()
        self.logger = get_logger(__name__)

        # Active transactions
        self._transactions: dict[str, MoveTransaction] = {}
        self._transaction_lock = False

    def move_file(
        self,
        source_path: Path,
        target_path: Path,
        create_dirs: bool = True,
        overwrite: bool = False,
        transaction_id: str | None = None,
    ) -> MoveResult:
        """Move a file from source to target with transactional safety.

        Args:
            source_path: Source file path
            target_path: Target file path
            create_dirs: Create target directories if they don't exist
            overwrite: Allow overwriting existing files
            transaction_id: Optional transaction ID for grouping operations

        Returns:
            MoveResult with operation details

        Raises:
            MovePermissionError: If insufficient permissions
            MoveDiskSpaceError: If insufficient disk space
            MoveConflictError: If target exists and overwrite is False
        """
        start_time = time.time()
        transaction_id = transaction_id or str(uuid.uuid4())

        try:
            # Validate source file
            self._validate_source_file(source_path)

            # Prepare target path
            target_path = self._prepare_target_path(target_path, create_dirs)

            # Handle conflicts
            if target_path.exists() and not overwrite:
                target_path = self._resolve_conflict(source_path, target_path)

            # Check disk space
            self._check_disk_space(source_path, target_path)

            # Store file size before moving
            file_size = source_path.stat().st_size if source_path.exists() else 0

            # Perform the move operation
            if self._is_same_filesystem(source_path, target_path):
                result = self._move_direct(source_path, target_path, transaction_id)
            else:
                result = self._move_cross_filesystem(source_path, target_path, transaction_id)

            # Set final result
            result.duration = time.time() - start_time
            result.file_size = file_size

            self.logger.info(
                f"File moved successfully: {source_path} -> {target_path} "
                f"(size: {result.file_size} bytes, duration: {result.duration:.2f}s)"
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"File move failed: {source_path} -> {target_path}: {e}")

            return MoveResult(
                success=False,
                source_path=source_path,
                target_path=target_path,
                operation=MoveOperation.MOVE,
                transaction_id=transaction_id,
                error_message=str(e),
                rollback_required=True,
                duration=duration,
            )

    def move_files_batch(
        self,
        file_operations: list[tuple[Path, Path]],
        create_dirs: bool = True,
        overwrite: bool = False,
    ) -> list[MoveResult]:
        """Move multiple files in a batch operation.

        Args:
            file_operations: List of (source_path, target_path) tuples
            create_dirs: Create target directories if they don't exist
            overwrite: Allow overwriting existing files

        Returns:
            List of MoveResult objects
        """
        transaction_id = str(uuid.uuid4())
        results = []

        self.logger.info(f"Starting batch move operation with {len(file_operations)} files")

        for source_path, target_path in file_operations:
            try:
                result = self.move_file(
                    source_path, target_path, create_dirs, overwrite, transaction_id
                )
                results.append(result)

                # If any operation fails and rollback is required, stop the batch
                if not result.success and result.rollback_required:
                    self.logger.error(
                        f"Batch operation stopped due to failure: {result.error_message}"
                    )
                    break

            except Exception as e:
                log_operation_error("batch operation", e)
                results.append(
                    MoveResult(
                        success=False,
                        source_path=source_path,
                        target_path=target_path,
                        operation=MoveOperation.MOVE,
                        transaction_id=transaction_id,
                        error_message=str(e),
                        rollback_required=True,
                    )
                )
                break

        success_count = sum(1 for r in results if r.success)
        self.logger.info(
            f"Batch operation completed: {success_count}/{len(file_operations)} successful"
        )

        return results

    def move_anime_files(
        self,
        files: list[AnimeFile],
        target_directory: Path,
        organize_by_series: bool = True,
        keep_best_quality: bool = False,  # Changed default to False to move all files
    ) -> list[MoveResult]:
        """Move anime files with intelligent organization.

        Args:
            files: List of AnimeFile objects to move
            target_directory: Target directory for files
            organize_by_series: Create subdirectories by series name
            keep_best_quality: Only move the best quality file from each group

        Returns:
            List of MoveResult objects
        """
        results = []

        if organize_by_series:
            # Group files by series
            series_groups = self.classifier.group_by_series(files)

            for series_title, series_files in series_groups.items():
                # Use TMDB Korean title if available, otherwise use original title
                folder_name = self._get_series_folder_name(series_files, series_title)

                # Create series directory
                series_dir = target_directory / self._sanitize_directory_name(folder_name)
                series_dir.mkdir(parents=True, exist_ok=True)

                # Select files to move (all files by default, including subtitles)
                if keep_best_quality:
                    best_file = self.classifier.find_best_file(series_files)
                    files_to_move = [best_file] if best_file is not None else []
                else:
                    files_to_move = series_files

                # Move files
                for file in files_to_move:
                    target_path = series_dir / file.filename
                    result = self.move_file(Path(file.file_path), target_path)
                    results.append(result)
        else:
            # Move all files to target directory
            for file in files:
                target_path = target_directory / file.filename
                result = self.move_file(Path(file.file_path), target_path)
                results.append(result)

        return results

    def move_file_groups(
        self,
        groups: list[FileGroup],
        target_directory: Path,
        organize_by_series: bool = True,
        keep_best_quality: bool = False,
    ) -> list[MoveResult]:
        """Move file groups using TMDB metadata for folder names.

        Args:
            groups: List of FileGroup objects to move
            target_directory: Target directory for files
            organize_by_series: Create subdirectories by series name
            keep_best_quality: Only move the best quality file from each group

        Returns:
            List of MoveResult objects
        """
        results = []

        for group in groups:
            if not group.files:
                continue

            if organize_by_series:
                # Use TMDB Korean title if available, otherwise use group name
                folder_name = self._get_group_folder_name(group)

                # Create series directory
                series_dir = target_directory / self._sanitize_directory_name(folder_name)
                series_dir.mkdir(parents=True, exist_ok=True)

                # Select files to move (all files by default, including subtitles)
                if keep_best_quality:
                    best_file = self.classifier.find_best_file(group.files)
                    files_to_move = [best_file] if best_file is not None else []
                else:
                    files_to_move = group.files

                # Move files
                for file in files_to_move:
                    target_path = series_dir / file.filename
                    result = self.move_file(Path(file.file_path), target_path)
                    results.append(result)
            else:
                # Move all files to target directory
                for file in group.files:
                    target_path = target_directory / file.filename
                    result = self.move_file(Path(file.file_path), target_path)
                    results.append(result)

        return results

    def cleanup_empty_directories(self, root_directory: Path) -> list[Path]:
        """Remove empty directories under the root directory.

        Args:
            root_directory: Root directory to clean up (this directory itself is not removed)

        Returns:
            List of removed directory paths
        """
        removed_dirs = []

        try:
            # Walk through all subdirectories
            for dir_path in sorted(
                root_directory.rglob("*"), key=lambda p: len(p.parts), reverse=True
            ):
                if dir_path.is_dir() and dir_path != root_directory:
                    try:
                        # Check if directory is empty
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                            removed_dirs.append(dir_path)
                            self.logger.info(f"Removed empty directory: {dir_path}")
                    except OSError as e:
                        self.logger.warning(f"Could not remove directory {dir_path}: {e}")

        except Exception as e:
            log_operation_error("directory cleanup", e)

        self.logger.info(f"Cleanup completed: {len(removed_dirs)} empty directories removed")
        return removed_dirs

    def rollback_transaction(self, transaction_id: str) -> bool:
        """Rollback a transaction by undoing all operations.

        Args:
            transaction_id: ID of the transaction to rollback

        Returns:
            True if rollback was successful, False otherwise

        Raises:
            MoveRollbackError: If rollback fails
        """
        if transaction_id not in self._transactions:
            raise MoveRollbackError(
                f"Transaction {transaction_id} not found",
                "",
                "",
                0,
                f"Transaction {transaction_id} does not exist",
            )

        transaction = self._transactions[transaction_id]

        if transaction.status == "rolled_back":
            self.logger.warning(f"Transaction {transaction_id} already rolled back")
            return True

        self.logger.info(f"Starting rollback for transaction {transaction_id}")

        try:
            # Execute rollback operations in reverse order
            if transaction.rollback_operations:
                for operation in reversed(transaction.rollback_operations):
                    self._execute_rollback_operation(operation)

            transaction.status = "rolled_back"
            self.logger.info(f"Transaction {transaction_id} rolled back successfully")
            return True

        except Exception as e:
            transaction.status = "failed"
            self.logger.error(f"Rollback failed for transaction {transaction_id}: {e}")
            raise MoveRollbackError(
                f"Failed to rollback transaction {transaction_id}: {e!s}",
                "",
                "",
                len(transaction.rollback_operations or []),
                str(e),
            ) from e

    def _validate_source_file(self, source_path: Path) -> None:
        """Validate that the source file exists and is accessible."""
        if not source_path.exists():
            raise MoveValidationError(
                f"Source file does not exist: {source_path}", "file_existence", str(source_path)
            )

        if not source_path.is_file():
            raise MoveValidationError(
                f"Source path is not a file: {source_path}", "file_type", str(source_path)
            )

        if not os.access(source_path, os.R_OK):
            raise MovePermissionError(
                f"No read permission for source file: {source_path}", str(source_path), "read"
            )

    def _prepare_target_path(self, target_path: Path, create_dirs: bool) -> Path:
        """Prepare the target path and create directories if needed."""
        if create_dirs:
            target_path.parent.mkdir(parents=True, exist_ok=True)

        if not target_path.parent.exists():
            raise MoveValidationError(
                f"Target directory does not exist: {target_path.parent}",
                "directory_existence",
                str(target_path.parent),
            )

        if not os.access(target_path.parent, os.W_OK):
            raise MovePermissionError(
                f"No write permission for target directory: {target_path.parent}",
                str(target_path.parent),
                "write",
            )

        return target_path

    def _resolve_conflict(self, source_path: Path, target_path: Path) -> Path:
        """Resolve filename conflicts by generating a unique name."""
        try:
            available_path = self.namer.get_available_filename(target_path)
            return available_path
        except Exception as e:
            raise MoveConflictError(
                f"Failed to resolve filename conflict: {e}",
                str(source_path),
                str(target_path),
                str(target_path),
                str(e),
            ) from e

    def _check_disk_space(self, source_path: Path, target_path: Path) -> None:
        """Check if there's enough disk space for the operation."""
        try:
            source_size = source_path.stat().st_size
            target_free_space = shutil.disk_usage(target_path.parent).free

            if source_size > target_free_space:
                raise MoveDiskSpaceError(
                    f"Insufficient disk space: need {source_size} bytes, "
                    f"have {target_free_space} bytes",
                    source_size,
                    target_free_space,
                    str(target_path.parent),
                )
        except OSError as e:
            raise MoveDiskSpaceError(
                f"Failed to check disk space: {e}", 0, 0, str(target_path.parent), str(e)
            ) from e

    def _is_same_filesystem(self, source_path: Path, target_path: Path) -> bool:
        """Check if source and target are on the same filesystem."""
        try:
            source_stat = source_path.stat()
            target_stat = target_path.parent.stat()
            return source_stat.st_dev == target_stat.st_dev
        except OSError:
            return False

    def _move_direct(self, source_path: Path, target_path: Path, transaction_id: str) -> MoveResult:
        """Move file directly (same filesystem)."""
        try:
            # Create rollback operation
            rollback_op = {
                "operation": "move",
                "source": str(target_path),
                "target": str(source_path),
                "timestamp": time.time(),
            }

            # Perform move
            shutil.move(str(source_path), str(target_path))

            # Store rollback operation
            if transaction_id in self._transactions:
                transaction = self._transactions[transaction_id]
                if transaction.rollback_operations is not None:
                    transaction.rollback_operations.append(rollback_op)

            return MoveResult(
                success=True,
                source_path=source_path,
                target_path=target_path,
                operation=MoveOperation.MOVE,
                transaction_id=transaction_id,
            )

        except Exception as e:
            raise MoveValidationError(
                f"Direct move failed: {e}", "move_operation", str(source_path), str(e)
            ) from e

    def _move_cross_filesystem(
        self, source_path: Path, target_path: Path, transaction_id: str
    ) -> MoveResult:
        """Move file across filesystems (copy + delete)."""
        temp_path = None

        try:
            # Create temporary file
            temp_path = self.temp_dir / f"move_{uuid.uuid4()}_{source_path.name}"

            # Copy to temporary location
            shutil.copy2(str(source_path), str(temp_path))

            # Verify copy
            if not self._verify_file_integrity(source_path, temp_path):
                raise MoveValidationError(
                    "File integrity check failed after copy", "integrity_check", str(source_path)
                )

            # Move from temp to target
            shutil.move(str(temp_path), str(target_path))
            temp_path = None  # Prevent cleanup

            # Create rollback operation
            rollback_op = {
                "operation": "move",
                "source": str(target_path),
                "target": str(source_path),
                "timestamp": time.time(),
            }

            # Store rollback operation
            if transaction_id in self._transactions:
                transaction = self._transactions[transaction_id]
                if transaction.rollback_operations is not None:
                    transaction.rollback_operations.append(rollback_op)

            # Delete original file
            source_path.unlink()

            return MoveResult(
                success=True,
                source_path=source_path,
                target_path=target_path,
                operation=MoveOperation.MOVE,
                transaction_id=transaction_id,
            )

        except Exception as e:
            # Cleanup temporary file
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

            raise MoveValidationError(
                f"Cross-filesystem move failed: {e}", "move_operation", str(source_path), str(e)
            ) from e

    def _verify_file_integrity(self, source_path: Path, target_path: Path) -> bool:
        """Verify that the copied file is identical to the source."""
        try:
            source_size = source_path.stat().st_size
            target_size = target_path.stat().st_size

            if source_size != target_size:
                return False

            # Simple hash comparison (could be enhanced with actual hash)
            with open(source_path, "rb") as f1, open(target_path, "rb") as f2:
                while True:
                    chunk1 = f1.read(8192)
                    chunk2 = f2.read(8192)
                    if chunk1 != chunk2:
                        return False
                    if not chunk1:
                        break

            return True

        except Exception:
            return False

    def _execute_rollback_operation(self, operation: dict[str, Any]) -> None:
        """Execute a rollback operation."""
        op_type = operation.get("operation")
        source = operation.get("source")
        target = operation.get("target")

        if op_type == "move" and source and target:
            try:
                shutil.move(source, target)
                self.logger.info(f"Rollback: moved {source} -> {target}")
            except Exception as e:
                log_operation_error("rollback", e)
                raise

    def _get_group_folder_name(self, group: FileGroup) -> str:
        """Get the best folder name for a FileGroup using TMDB title (Korean).

        Args:
            group: FileGroup object with TMDB metadata

        Returns:
            Best folder name to use
        """
        # Check if group has TMDB info
        if group.tmdb_info:
            tmdb_info = group.tmdb_info
            # Use title (which is Korean when language is set to Korean)
            if tmdb_info.title:
                return tmdb_info.title
            elif tmdb_info.original_title:
                return tmdb_info.original_title

        # Fallback to group name or series title
        if group.group_name:
            return group.group_name
        elif group.series_title:
            return group.series_title
        else:
            return "Unknown"

    def _get_series_folder_name(self, series_files: list[AnimeFile], fallback_title: str) -> str:
        """Get the best folder name for a series, preferring TMDB Korean title.

        Args:
            series_files: List of files in the series
            fallback_title: Fallback title if no TMDB info available

        Returns:
            Best folder name to use
        """
        # Look for TMDB info in any of the files
        for file in series_files:
            if hasattr(file, "file_group") and file.file_group and file.file_group.tmdb_info:
                tmdb_info = file.file_group.tmdb_info
                # Prefer Korean title, then original title, then fallback
                if tmdb_info.korean_title:
                    return f"{tmdb_info.korean_title} ({tmdb_info.original_title})"
                elif tmdb_info.original_title:
                    return tmdb_info.original_title
                elif tmdb_info.title:
                    return tmdb_info.title

        # If no TMDB info found, use fallback title
        return fallback_title

    def _sanitize_directory_name(self, name: str) -> str:
        """Sanitize a directory name for safe filesystem use."""
        # Remove invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
        # Remove multiple underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores and dots
        sanitized = sanitized.strip("_.")
        # Ensure it's not empty
        if not sanitized:
            sanitized = "unnamed"
        return sanitized

    @contextmanager
    def transaction(
        self, transaction_id: str | None = None
    ) -> Generator[MoveTransaction, None, None]:
        """Context manager for transactional file operations."""
        tid = transaction_id or str(uuid.uuid4())
        transaction = MoveTransaction(transaction_id=tid, operations=[], created_at=time.time())

        self._transactions[tid] = transaction

        try:
            yield transaction
            transaction.status = "committed"
        except Exception:
            transaction.status = "failed"
            # Attempt rollback
            try:
                self.rollback_transaction(tid)
            except Exception as rollback_error:
                log_operation_error("rollback", rollback_error)
            raise
        finally:
            # Clean up transaction after some time
            pass
