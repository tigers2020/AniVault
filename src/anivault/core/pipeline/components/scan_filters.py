"""Scan filtering logic for DirectoryScanner.

This module provides pure filtering predicates used during directory scanning
to decide which files and directories to include or skip. Extracted from
scanner.py for Collector pattern separation (filter vs collect).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from anivault.core.filter import FilterEngine

logger = logging.getLogger(__name__)


def has_valid_extension(file_path: Path, extensions: set[str]) -> bool:
    """Check if file has a valid extension.

    Args:
        file_path: Path to the file to check.
        extensions: Set of allowed extensions (e.g., {'.mp4', '.mkv'}).

    Returns:
        True if file has a valid extension, False otherwise.
    """
    return file_path.suffix.lower() in extensions


def has_valid_extension_from_path(path_str: str, extensions: set[str]) -> bool:
    """Check if path string ends with a valid extension (for DirEntry.path).

    Args:
        path_str: Path string (e.g., from os.DirEntry.path).
        extensions: Set of allowed extensions (e.g., {'.mp4', '.mkv'}).

    Returns:
        True if path has a valid extension, False otherwise.
    """
    return path_str.lower().endswith(tuple(extensions))


def should_skip_directory(dir_name: str, filter_engine: FilterEngine | None) -> bool:
    """Check if directory should be skipped based on filtering criteria.

    Args:
        dir_name: Name of the directory to check.
        filter_engine: Optional FilterEngine instance for smart filtering.

    Returns:
        True if directory should be skipped, False otherwise.
    """
    if not filter_engine:
        return False
    return filter_engine.should_skip_directory(dir_name)


def should_include_file(
    file_path: Path,
    filter_engine: FilterEngine | None,
) -> bool:
    """Check if file should be included based on filtering criteria.

    Args:
        file_path: Path to the file to check.
        filter_engine: Optional FilterEngine instance for smart filtering.

    Returns:
        True if file should be included, False otherwise.
    """
    if not filter_engine:
        return True

    try:
        file_stat = file_path.stat()
        return not filter_engine.should_skip_file(file_path, file_stat)
    except PermissionError as e:
        logger.warning(
            "Skipping file due to permission error: %s",
            file_path,
            extra={"error": str(e), "operation": "should_include_file"},
        )
        return False
    except OSError as e:
        logger.warning(
            "Skipping file due to OS error: %s",
            file_path,
            extra={"error": str(e), "operation": "should_include_file"},
        )
        return False


def filter_directories_in_place(
    dirs: list[str],
    filter_engine: FilterEngine | None,
) -> None:
    """Filter directory list in-place (for os.walk dirs mutation).

    Args:
        dirs: List of subdirectory names to filter (mutated in-place).
        filter_engine: Optional FilterEngine instance for smart filtering.
    """
    if not filter_engine:
        return
    dirs[:] = [d for d in dirs if not filter_engine.should_skip_directory(d)]


def process_file_entry(
    entry: os.DirEntry[str],
    extensions: set[str],
    filter_engine: FilterEngine | None,
) -> Path | None:
    """Process a file entry during parallel scanning (os.scandir).

    Args:
        entry: Directory entry from os.scandir.
        extensions: Set of allowed extensions.
        filter_engine: Optional FilterEngine instance for smart filtering.

    Returns:
        Path object if file should be included, None otherwise.
    """
    if not has_valid_extension_from_path(entry.path, extensions):
        return None

    file_path = Path(entry.path).absolute()

    if not filter_engine:
        return file_path

    try:
        file_stat = entry.stat()
        if filter_engine.should_skip_file(file_path, file_stat):
            return None
    except PermissionError as e:
        logger.warning(
            "Skipping file entry due to permission error: %s",
            file_path,
            extra={"error": str(e), "operation": "process_file_entry"},
        )
        return None
    except OSError as e:
        logger.warning(
            "Skipping file entry due to OS error: %s",
            file_path,
            extra={"error": str(e), "operation": "process_file_entry"},
        )
        return None

    return file_path
