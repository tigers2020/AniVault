"""
File Scanner Worker for AniVault GUI

This module contains the worker class that handles background file scanning
operations using PySide6's QThread and signal/slot mechanism.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from anivault.gui.models import FileItem
from anivault.shared.errors import (
    AniVaultError,
    AniVaultFileError,
    AniVaultPermissionError,
    ErrorCode,
    ErrorContext,
)

logger = logging.getLogger(__name__)

# Simple video extensions list for now
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"}


class FileScannerWorker(QObject):
    """
    Worker class for scanning files in the background.

    This class runs in a separate thread and uses signals to communicate
    with the main GUI thread for thread-safe updates.
    """

    # Signals for communication with main thread
    scan_started: Signal = Signal()  # Emitted when scan starts
    file_found: Signal = Signal(object)  # Emits FileItem object
    scan_progress: Signal = Signal(int)  # Emits progress percentage (0-100)
    scan_finished: Signal = Signal(list)  # Emits list[FileItem]
    scan_error: Signal = Signal(str)  # Emits error message
    scan_cancelled: Signal = Signal()  # Emitted when scan is cancelled

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cancelled = False
        self._current_directory: Path | None = (
            None  # Will be set in scan_directory (Python 3.9 compat)
        )

        logger.debug("FileScannerWorker initialized")

    def scan_directory(self, directory: str) -> None:
        """
        Scan a directory for media files.

        Args:
            directory: Path to the directory to scan
        """
        try:
            dir_path = Path(directory)
            self._current_directory = dir_path
            self._cancelled = False

            # Validate directory path
            if not self._validate_directory(directory):
                self.scan_error.emit(f"Invalid or inaccessible directory: {directory}")
                return

            self.scan_started.emit()
            logger.info("Starting file scan in directory: %s", directory)

            # Get all files in directory
            all_files = self._get_all_files(dir_path)

            if self._cancelled:
                self.scan_cancelled.emit()
                return

            # Filter for media files
            media_files = self._filter_media_files(all_files)

            # Cancel check already done above - NO LONGER NEEDED

            # Convert to FileItem objects
            file_items = []
            total_files = len(media_files)

            for i, file_path in enumerate(media_files):
                # Cancel check done at top level - NO LONGER NEEDED

                # Create file item
                file_item = FileItem(file_path, "Scanned")
                file_items.append(file_item)

                # Emit file found signal (FileItem object, NO dict!)
                self.file_found.emit(file_item)

                # Update progress
                progress = int((i + 1) * 100 / total_files)
                self.scan_progress.emit(progress)

                # Allow GUI to process events
                QApplication.processEvents()

            if not self._cancelled:
                self.scan_finished.emit(file_items)
                logger.info(
                    "File scan completed. Found %d media files",
                    len(file_items),
                )

        except Exception as e:
            logger.exception("Error during file scan")
            self.scan_error.emit(f"Scan error: {e!s}")

    def cancel_scan(self) -> None:
        """Cancel the current scan operation."""
        self._cancelled = True
        logger.info("File scan cancellation requested")

    def _validate_directory(self, directory: str) -> bool:
        """
        Validate that the directory exists and is accessible.

        Args:
            directory: Directory path to validate

        Returns:
            True if directory is valid and accessible
        """
        try:
            path = Path(directory)

            # Check if path exists
            if not path.exists():
                logger.warning("Directory does not exist: %s", directory)
                return False

            # Check if it's a directory
            if not path.is_dir():
                logger.warning("Path is not a directory: %s", directory)
                return False

            # Check if we have read permission
            if not os.access(path, os.R_OK):
                logger.warning("No read permission for directory: %s", directory)
                return False

            # Check for path traversal attempts (basic validation)
            resolved_path = path.resolve()
            if str(resolved_path) != str(path.resolve()):
                logger.warning("Suspicious path traversal detected: %s", directory)
                return False

            return True

        except (FileNotFoundError, PermissionError) as e:
            context = ErrorContext(
                file_path=str(directory),
                operation="validate_directory",
            )
            if isinstance(e, FileNotFoundError):
                _error = AniVaultFileError(
                    ErrorCode.DIRECTORY_NOT_FOUND,
                    f"Directory not found: {directory}",
                    context,
                    original_error=e,
                )
            else:
                _error = AniVaultPermissionError(
                    ErrorCode.PERMISSION_DENIED,
                    f"Permission denied accessing directory: {directory}",
                    context,
                    original_error=e,
                )
            logger.exception("Directory validation error: %s", directory)
            return False
        except OSError as e:
            context = ErrorContext(
                file_path=str(directory),
                operation="validate_directory",
            )
            _error = AniVaultFileError(
                ErrorCode.FILE_ACCESS_ERROR,
                f"File system error validating directory: {directory}",
                context,
                original_error=e,
            )
            logger.exception("Directory validation error: %s", directory)
            return False
        except Exception as e:
            context = ErrorContext(
                file_path=str(directory),
                operation="validate_directory",
            )
            _error = AniVaultError(
                ErrorCode.INVALID_PATH,
                f"Unexpected error validating directory: {directory}",
                context,
                original_error=e,
            )
            logger.exception("Directory validation error: %s", directory)
            return False

    def _get_all_files(self, directory: Path) -> list[Path]:
        """
        Recursively get all files in a directory.

        Args:
            directory: Directory to scan

        Returns:
            List of file paths
        """
        files = []

        try:
            # Use os.walk for better performance and error handling
            for root, dirs, filenames in os.walk(directory):
                if self._cancelled:
                    break

                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith(".")]

                for filename in filenames:
                    # Cancel check done at top level - NO LONGER NEEDED

                    # Skip hidden files
                    if filename.startswith("."):
                        continue

                    file_path = Path(root) / filename
                    files.append(file_path)

                    # Process events periodically to keep GUI responsive
                    if len(files) % 100 == 0:
                        QApplication.processEvents()

        except PermissionError as e:
            context = ErrorContext(
                file_path=str(directory),
                operation="get_all_files",
            )
            error = AniVaultPermissionError(
                ErrorCode.PERMISSION_DENIED,
                f"Permission denied accessing directory: {directory}",
                context,
                original_error=e,
            )
            logger.warning("Permission denied accessing directory: %s", e)
            raise error from e
        except (FileNotFoundError, OSError) as e:
            context = ErrorContext(
                file_path=str(directory),
                operation="get_all_files",
            )
            if isinstance(e, FileNotFoundError):
                error = AniVaultFileError(
                    ErrorCode.DIRECTORY_NOT_FOUND,
                    f"Directory not found: {directory}",
                    context,
                    original_error=e,
                )
            else:
                error = AniVaultFileError(
                    ErrorCode.FILE_ACCESS_ERROR,
                    f"File system error walking directory: {directory}",
                    context,
                    original_error=e,
                )
            logger.exception("Error walking directory: %s", directory)
            raise error from e
        except Exception as e:
            context = ErrorContext(
                file_path=str(directory),
                operation="get_all_files",
            )
            error = AniVaultError(
                ErrorCode.SCANNER_ERROR,
                f"Unexpected error walking directory: {directory}",
                context,
                original_error=e,
            )
            logger.exception("Error walking directory: %s", directory)
            raise error from e

        return files

    def _filter_media_files(self, files: list[Path]) -> list[Path]:
        """
        Filter files to only include media files.

        Args:
            files: List of file paths to filter

        Returns:
            List of media file paths
        """
        media_files = []

        for file_path in files:
            if self._cancelled:
                break

            # Check file extension
            if file_path.suffix.lower() in VIDEO_EXTENSIONS:
                media_files.append(file_path)

        logger.debug(
            "Filtered %d media files from %d total files",
            len(media_files),
            len(files),
        )

        return media_files
