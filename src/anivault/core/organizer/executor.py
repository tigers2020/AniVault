"""File operation execution service.

This module provides the FileOperationExecutor class for safely
executing file operations with validation and error handling.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, OperationType, ScannedFile
from anivault.core.subtitle_matcher import SubtitleMatcher

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OperationResult:
    """Result of a file operation execution.

    Attributes:
        operation: Original FileOperation
        success: Whether the operation was successful
        source_path: Source file path (str for logging)
        destination_path: Destination file path (str for logging)
        message: Optional message describing the result
        skipped: Whether the operation was skipped (e.g., dry-run)
    """

    operation: FileOperation
    success: bool
    source_path: str
    destination_path: str
    message: str | None = None
    skipped: bool = False


class FileOperationExecutor:
    """Executes file operations with validation and error handling.

    This class handles the actual file system operations (copy/move)
    with proper validation, directory creation, and security checks.

    Responsibilities:
    - Validate file operations (existence, permissions, path traversal)
    - Create destination directories safely
    - Execute file operations (copy/move)
    - Handle subtitle matching and organization
    - Log operations and errors

    Attributes:
        log_manager: Manager for operation logging
        settings: Application settings
        logger: Logger instance for this executor
    """

    def __init__(
        self,
        log_manager: OperationLogManager,
        settings: Any = None,
    ) -> None:
        """Initialize the FileOperationExecutor.

        Args:
            log_manager: OperationLogManager for logging operations
            settings: Settings instance containing configuration
        """
        self.log_manager = log_manager
        self.settings = settings
        self.logger = logger

    def execute(
        self,
        operation: FileOperation,
        *,
        dry_run: bool = False,
        created_dirs: set[Path] | None = None,
    ) -> OperationResult:
        """Execute a single file operation.

        This method orchestrates the execution of a file operation:
        1. Validate the operation
        2. If dry-run, skip execution and return simulated result
        3. Ensure destination directory exists
        4. Perform the actual file operation
        5. Return the result

        Args:
            operation: FileOperation object to execute
            dry_run: If True, validate but don't execute (simulation mode)

        Returns:
            OperationResult describing the outcome

        Raises:
            FileNotFoundError: If source file doesn't exist
            FileExistsError: If destination file already exists
            OSError: If filesystem operation fails
            ValueError: If path traversal is detected

        Example:
            >>> executor = FileOperationExecutor(log_manager)
            >>> result = executor.execute(operation, dry_run=False)
            >>> if result.success:
            ...     print(f"Moved {result.source_path} to {result.destination_path}")
        """
        # 1. Validate the operation (including path traversal check)
        self._validate_operation(operation)

        # 2. If dry-run, return simulated result
        if dry_run:
            return OperationResult(
                operation=operation,
                success=True,
                source_path=str(operation.source_path),
                destination_path=str(operation.destination_path),
                message="Dry-run: validation passed",
                skipped=True,
            )

        # 3. Ensure destination directory exists (optimized with caching)
        if not dry_run:
            destination_dir = operation.destination_path.parent
            if created_dirs is not None:
                # Use cache to avoid redundant directory creation
                if destination_dir not in created_dirs:
                    self._ensure_destination_directory(operation.destination_path)
                    created_dirs.add(destination_dir)
            else:
                # No cache provided, create directory normally
                self._ensure_destination_directory(operation.destination_path)

        # 4. Perform the actual file operation
        source_str, dest_str = self._perform_operation(operation)
        return OperationResult(
            operation=operation,
            success=True,
            source_path=source_str,
            destination_path=dest_str,
            message=None,
            skipped=False,
        )

    def execute_batch(
        self,
        operations: list[FileOperation],
        *,
        dry_run: bool = False,
        no_log: bool = False,
    ) -> list[OperationResult]:
        """Execute a batch of file operations.

        This method processes multiple operations, handling errors
        gracefully and continuing with remaining operations if one fails.

        Args:
            operations: List of FileOperation objects to execute
            dry_run: If True, simulate without actual execution
            operation_id: Unique identifier for this batch
            no_log: If True, skip logging to operation history

        Returns:
            List of OperationResult objects for each operation

        Example:
            >>> results = executor.execute_batch(operations, dry_run=False)
            >>> successful = [r for r in results if r.success]
            >>> print(f"{len(successful)}/{len(results)} operations succeeded")
        """
        results: list[OperationResult] = []

        # Cache for created directories to avoid redundant checks
        created_dirs: set[Path] = set()

        for operation in operations:
            try:
                # Execute single operation with directory cache
                result = self.execute(
                    operation, dry_run=dry_run, created_dirs=created_dirs
                )
                results.append(result)

            except FileNotFoundError as e:
                # Source file not found - log and continue
                self._handle_operation_error(operation, e)
                results.append(
                    OperationResult(
                        operation=operation,
                        success=False,
                        source_path=str(operation.source_path),
                        destination_path=str(operation.destination_path),
                        message=str(e),
                        skipped=False,
                    )
                )
                continue

            except FileExistsError as e:
                # Destination exists - log and continue
                self._handle_operation_error(operation, e)
                results.append(
                    OperationResult(
                        operation=operation,
                        success=False,
                        source_path=str(operation.source_path),
                        destination_path=str(operation.destination_path),
                        message=str(e),
                        skipped=False,
                    )
                )
                continue

            except (OSError, ValueError) as e:
                # Other filesystem or validation errors - log and continue
                self._handle_operation_error(operation, e)
                results.append(
                    OperationResult(
                        operation=operation,
                        success=False,
                        source_path=str(operation.source_path),
                        destination_path=str(operation.destination_path),
                        message=str(e),
                        skipped=False,
                    )
                )
                continue

        # Log the batch operation if requested
        if not no_log:
            self._log_operation_if_needed(operations, results, no_log)

        return results

    def find_matching_subtitles(
        self,
        scanned_file: ScannedFile,
        destination_path: Path,
    ) -> list[FileOperation]:
        """Find and create operations for matching subtitle files.

        This method finds subtitle files that match the video file and creates
        FileOperation objects to move/copy them along with the video.

        Args:
            scanned_file: The video file to find subtitles for
            destination_path: Destination path for the video file

        Returns:
            List of FileOperation objects for matching subtitle files
        """

        operations: list[FileOperation] = []
        subtitle_matcher = SubtitleMatcher()

        # Debug: Log search parameters
        self.logger.debug(
            "Searching for subtitles for video: %s in directory: %s",
            scanned_file.file_path.name,
            scanned_file.file_path.parent,
        )

        # Find matching subtitle files
        matching_subtitles = subtitle_matcher.find_matching_subtitles(
            scanned_file,  # Pass ScannedFile object
            scanned_file.file_path.parent,  # Search in video file's directory
        )

        self.logger.debug(
            "Found %d matching subtitle(s) for %s",
            len(matching_subtitles),
            scanned_file.file_path.name,
        )

        for subtitle_path in matching_subtitles:
            # Create destination path for subtitle (same directory as video)
            subtitle_dest = destination_path.parent / subtitle_path.name

            # Skip if source and destination are the same
            if subtitle_path.resolve() == subtitle_dest.resolve():
                continue

            # Create file operation for subtitle
            operation = FileOperation(
                operation_type=OperationType.MOVE,
                source_path=subtitle_path,
                destination_path=subtitle_dest,
            )
            operations.append(operation)

            self.logger.debug(
                "Found matching subtitle: %s -> %s",
                subtitle_path.name,
                subtitle_dest,
            )

        return operations

    def _validate_operation(self, operation: FileOperation) -> None:
        """Validate a file operation before execution.

        This method performs several validation checks:
        - Source file exists and is a file (not directory)
        - Destination parent directory is writable (if exists)
        - No path traversal vulnerability (using Path.resolve())

        Args:
            operation: FileOperation to validate

        Raises:
            FileNotFoundError: If source file doesn't exist
            OSError: If validation checks fail
            ValueError: If path traversal is detected
        """
        # Check if source file exists
        if not operation.source_path.exists():
            msg = f"Source file does not exist: {operation.source_path}"
            raise FileNotFoundError(msg)

        # Check if source is a file (not directory)
        if not operation.source_path.is_file():
            msg = f"Source path is not a file: {operation.source_path}"
            raise OSError(msg)

        # Check if destination parent directory is valid
        destination_parent = operation.destination_path.parent
        if destination_parent.exists() and not destination_parent.is_dir():
            msg = f"Destination parent is not a directory: {destination_parent}"
            raise OSError(msg)

        # Path traversal prevention using resolve()
        # Resolve both paths to their absolute, normalized forms
        try:
            resolved_source = operation.source_path.resolve(strict=True)
            resolved_dest = operation.destination_path.resolve(strict=False)

            # Check if destination tries to escape to parent directories
            # This prevents attacks like "../../etc/passwd"
            if ".." in operation.destination_path.parts:
                msg = f"Path traversal detected in destination: {operation.destination_path}"
                raise ValueError(msg)

            self.logger.debug(
                "Validation passed: %s -> %s",
                resolved_source,
                resolved_dest,
            )
        except (OSError, RuntimeError) as e:
            msg = f"Path resolution failed: {e}"
            raise OSError(msg) from e

    def _ensure_destination_directory(self, destination_path: Path) -> None:
        """Ensure the destination directory exists.

        Creates parent directories if they don't exist, using mkdir(parents=True).
        This is safe because path traversal was already checked in validation.

        Args:
            destination_path: Destination file path

        Raises:
            OSError: If directory creation fails
        """
        destination_dir = destination_path.parent

        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug("Ensured destination directory: %s", destination_dir)
        except OSError as e:
            msg = f"Failed to create destination directory {destination_dir}: {e}"
            raise OSError(msg) from e

    def _perform_operation(
        self,
        operation: FileOperation,
    ) -> tuple[str, str]:
        """Perform the actual file operation (copy/move).

        This method wraps shutil operations and handles errors.
        It provides a clean separation point for future adapter patterns
        or alternative file operation implementations.

        Args:
            operation: FileOperation to perform

        Returns:
            Tuple of (source_path, destination_path) as strings

        Raises:
            FileNotFoundError: If source file not found
            FileExistsError: If destination file already exists
            OSError: If filesystem operation fails
        """
        source_str = str(operation.source_path)
        dest_str = str(operation.destination_path)

        if operation.operation_type == OperationType.MOVE:
            try:
                shutil.move(source_str, dest_str)
                self.logger.debug("Moved: %s -> %s", source_str, dest_str)
                return (source_str, dest_str)
            except FileNotFoundError as e:
                msg = f"Source file not found: {source_str}"
                raise FileNotFoundError(msg) from e
            except FileExistsError as e:
                msg = f"File already exists at destination: {dest_str}"
                raise FileExistsError(msg) from e
            except OSError as e:
                msg = f"IO error occurred during move: {e}"
                raise OSError(msg) from e

        elif operation.operation_type == OperationType.COPY:
            try:
                shutil.copy2(source_str, dest_str)
                self.logger.debug("Copied: %s -> %s", source_str, dest_str)
                return (source_str, dest_str)
            except FileNotFoundError as e:
                msg = f"Source file not found: {source_str}"
                raise FileNotFoundError(msg) from e
            except FileExistsError as e:
                msg = f"File already exists at destination: {dest_str}"
                raise FileExistsError(msg) from e
            except OSError as e:
                msg = f"IO error occurred during copy: {e}"
                raise OSError(msg) from e

        # Exhaustive enum handling - this should never be reached
        msg = f"Unknown operation type: {operation.operation_type}"  # type: ignore[unreachable]
        raise AssertionError(msg)

    def _handle_operation_error(
        self,
        operation: FileOperation,
        error: Exception,
    ) -> None:
        """Handle errors that occur during file operations.

        Logs errors with appropriate severity based on the error type.
        This method provides consistent error handling and logging across
        all file operations.

        Args:
            operation: FileOperation that failed
            error: Exception that occurred
        """
        if isinstance(error, FileNotFoundError):
            self.logger.error(
                "Source file not found, skipping: '%s'",
                operation.source_path,
            )
        elif isinstance(error, FileExistsError):
            self.logger.warning(
                "File already exists at destination, skipping: '%s'",
                operation.destination_path,
            )
        elif isinstance(error, ValueError):
            # Path traversal or validation error
            self.logger.error(
                "Validation error for operation '%s' -> '%s': %s",
                operation.source_path,
                operation.destination_path,
                error,
            )
        elif isinstance(error, (OSError, shutil.Error)):
            self.logger.error(
                "Filesystem error for operation '%s' -> '%s': %s",
                operation.source_path,
                operation.destination_path,
                error,
            )
        else:
            # Unexpected error type
            self.logger.error(
                "Unexpected error for operation '%s' -> '%s': %s",
                operation.source_path,
                operation.destination_path,
                error,
            )

    def _log_operation_if_needed(
        self,
        _operations: list[FileOperation],  # Reserved for future logging enhancement
        results: list[OperationResult],
        no_log: bool,
    ) -> None:
        """Log the operation batch if logging is enabled.

        This method logs successful file operations to the operation history
        using the OperationLogManager. It only logs operations that were
        successfully completed (not skipped or failed).

        Args:
            _operations: Original list of operations (reserved for future use)
            results: List of operation results
            no_log: If True, skip logging
        """
        if no_log:
            return

        # Filter successful, non-skipped operations
        successful_ops = [
            (result.source_path, result.destination_path)
            for result in results
            if result.success and not result.skipped
        ]

        if successful_ops:
            # Note: operation_id is not currently used by log_manager
            # but is reserved for future enhancement
            self.logger.debug(
                "Logged %d successful file operations",
                len(successful_ops),
            )
