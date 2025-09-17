"""
File scanner module for AniVault application.

This module provides functionality to scan directories for animation files,
filter by supported extensions, and collect file metadata efficiently.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .models import AnimeFile


@dataclass
class ScanResult:
    """Result of a file scanning operation."""

    files: list[AnimeFile]
    scan_duration: float
    total_files_found: int
    supported_files: int
    errors: list[str]

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of file processing."""
        if self.total_files_found == 0:
            return 0.0
        return (self.supported_files / self.total_files_found) * 100


class FileScanner:
    """
    Scans directories for animation files and creates AnimeFile objects.

    This class provides efficient directory scanning with support for:
    - Recursive directory traversal
    - File extension filtering
    - Parallel processing for performance
    - Progress callbacks
    - Error handling and reporting
    """

    # Supported video file extensions
    SUPPORTED_EXTENSIONS: set[str] = {
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".3gp",
        ".ogv",
        ".ts",
        ".m2ts",
        ".mts",
    }

    def __init__(
        self, max_workers: int = 4, progress_callback: Callable[[int, str], None] | None = None
    ) -> None:
        """
        Initialize the file scanner.

        Args:
            max_workers: Maximum number of worker threads for parallel processing
            progress_callback: Optional callback for progress updates (progress, message)
        """
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self._cancelled = False

    def scan_directory(
        self, directory: Path, recursive: bool = True, follow_symlinks: bool = False
    ) -> ScanResult:
        """
        Scan a directory for animation files.

        Args:
            directory: Directory path to scan
            recursive: Whether to scan subdirectories recursively
            follow_symlinks: Whether to follow symbolic links

        Returns:
            ScanResult containing found files and metadata
        """
        start_time = time.time()
        files: list[AnimeFile] = []
        errors: list[str] = []

        try:
            # Validate directory
            if not directory.exists():
                raise FileNotFoundError(f"Directory does not exist: {directory}")

            if not directory.is_dir():
                raise NotADirectoryError(f"Path is not a directory: {directory}")

            # Get all files to process
            file_paths = self._collect_file_paths(directory, recursive, follow_symlinks)
            total_files = len(file_paths)

            if self.progress_callback:
                self.progress_callback(0, f"Found {total_files} files to process...")

            # Process files in parallel
            if total_files > 0:
                files, errors = self._process_files_parallel(file_paths, total_files)

            scan_duration = time.time() - start_time

            if self.progress_callback:
                self.progress_callback(100, f"Scan completed: {len(files)} files processed")

            return ScanResult(
                files=files,
                scan_duration=scan_duration,
                total_files_found=total_files,
                supported_files=len(files),
                errors=errors,
            )

        except Exception as e:
            error_msg = f"Error scanning directory {directory}: {str(e)}"
            errors.append(error_msg)

            if self.progress_callback:
                self.progress_callback(0, f"Error: {error_msg}")

            return ScanResult(
                files=[],
                scan_duration=time.time() - start_time,
                total_files_found=0,
                supported_files=0,
                errors=errors,
            )

    def _collect_file_paths(
        self, directory: Path, recursive: bool, follow_symlinks: bool
    ) -> list[Path]:
        """Collect all file paths that match supported extensions."""
        file_paths: list[Path] = []

        try:
            if recursive:
                # Use rglob for recursive search
                pattern = "**/*" if follow_symlinks else "**/*"
                for file_path in directory.rglob(pattern):
                    if file_path.is_file() and self._is_supported_file(file_path):
                        file_paths.append(file_path)
            else:
                # Scan only the immediate directory
                for file_path in directory.iterdir():
                    if file_path.is_file() and self._is_supported_file(file_path):
                        file_paths.append(file_path)

        except PermissionError as e:
            # Handle permission errors gracefully
            if self.progress_callback:
                self.progress_callback(0, f"Permission denied accessing {directory}: {e}")

        return file_paths

    def _is_supported_file(self, file_path: Path) -> bool:
        """Check if a file has a supported extension."""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def _process_files_parallel(
        self, file_paths: list[Path], total_files: int
    ) -> tuple[list[AnimeFile], list[str]]:
        """Process files in parallel using ThreadPoolExecutor."""
        files: list[AnimeFile] = []
        errors: list[str] = []
        processed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all file processing tasks
            future_to_path = {
                executor.submit(self._create_anime_file, file_path): file_path
                for file_path in file_paths
            }

            # Process completed tasks
            for future in as_completed(future_to_path):
                if self._cancelled:
                    break

                file_path = future_to_path[future]
                processed_count += 1

                try:
                    anime_file = future.result()
                    if anime_file:
                        files.append(anime_file)
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {str(e)}"
                    errors.append(error_msg)

                # Update progress
                if self.progress_callback:
                    progress = int((processed_count / total_files) * 100)
                    self.progress_callback(
                        progress, f"Processing files... {processed_count}/{total_files}"
                    )

        return files, errors

    def _create_anime_file(self, file_path: Path) -> AnimeFile | None:
        """
        Create an AnimeFile object from a file path.

        Args:
            file_path: Path to the file

        Returns:
            AnimeFile object or None if creation failed
        """
        try:
            # Get file statistics
            stat = file_path.stat()

            # Create AnimeFile object
            anime_file = AnimeFile(
                file_path=file_path,
                filename=file_path.name,
                file_size=stat.st_size,
                file_extension=file_path.suffix.lower(),
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
            )

            return anime_file

        except OSError as e:
            # File might be inaccessible or deleted
            raise Exception(f"Cannot access file {file_path}: {e}") from e
        except Exception as e:
            # Unexpected error
            raise Exception(f"Unexpected error processing {file_path}: {e}") from e

    def cancel_scan(self) -> None:
        """Cancel the current scanning operation."""
        self._cancelled = True

    def reset(self) -> None:
        """Reset the scanner state."""
        self._cancelled = False

    @classmethod
    def get_supported_extensions(cls) -> set[str]:
        """Get the set of supported file extensions."""
        return cls.SUPPORTED_EXTENSIONS.copy()

    @classmethod
    def add_supported_extension(cls, extension: str) -> None:
        """Add a new supported file extension."""
        cls.SUPPORTED_EXTENSIONS.add(extension.lower())

    @classmethod
    def remove_supported_extension(cls, extension: str) -> None:
        """Remove a supported file extension."""
        cls.SUPPORTED_EXTENSIONS.discard(extension.lower())


def scan_directory(
    directory: Path,
    recursive: bool = True,
    max_workers: int = 4,
    progress_callback: Callable[[int, str], None] | None = None,
) -> ScanResult:
    """
    Convenience function to scan a directory for animation files.

    Args:
        directory: Directory path to scan
        recursive: Whether to scan subdirectories recursively
        max_workers: Maximum number of worker threads
        progress_callback: Optional callback for progress updates

    Returns:
        ScanResult containing found files and metadata
    """
    scanner = FileScanner(max_workers=max_workers, progress_callback=progress_callback)
    return scanner.scan_directory(directory, recursive=recursive)
