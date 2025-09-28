"""File scanner module for AniVault.

This module provides efficient directory scanning functionality using os.scandir()
for optimal performance when processing large directory structures.
"""

import os
from collections.abc import Iterator
from pathlib import Path

from anivault.core.config import APP_CONFIG
from anivault.core.logging import get_logger

logger = get_logger(__name__)


def scan_directory(root_path: str | Path) -> Iterator[os.DirEntry]:
    """Recursively scan a directory for media files using os.scandir().

    This function uses os.scandir() for optimal performance, avoiding the overhead
    of os.walk() or os.listdir(). It yields os.DirEntry objects that cache file
    type and stat information, making subsequent operations more efficient.

    Memory optimization features:
    - Uses os.scandir() for efficient directory traversal
    - Generator-based approach prevents loading all files into memory
    - Recursive scanning with yield from for memory efficiency
    - Early filtering to avoid unnecessary processing

    Args:
        root_path: Path to the directory to scan (string or Path object).

    Yields:
        os.DirEntry: Directory entries for media files found during the scan.

    Example:
        >>> for entry in scan_directory("/path/to/anime"):
        ...     print(f"Found: {entry.name} at {entry.path}")
    """
    root_path = Path(root_path)

    if not root_path.exists():
        logger.warning(f"Directory does not exist: {root_path}")
        return

    if not root_path.is_dir():
        logger.warning(f"Path is not a directory: {root_path}")
        return

    # Get media extensions from configuration (cached for efficiency)
    media_extensions = tuple(ext.lower() for ext in APP_CONFIG.media_extensions)

    try:
        # Use os.scandir() for memory-efficient directory traversal
        with os.scandir(root_path) as entries:
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    # Recursively scan subdirectories using yield from
                    # This maintains generator behavior and memory efficiency
                    yield from scan_directory(entry.path)
                elif entry.is_file() and _is_media_file(entry.name, media_extensions):
                    yield entry

    except PermissionError:
        logger.warning(f"Permission denied to access: {root_path}")
    except OSError as e:
        logger.error(f"Error scanning directory {root_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error scanning {root_path}: {e}")


def _is_media_file(filename: str, media_extensions: tuple[str, ...]) -> bool:
    """Check if a file has a media extension.

    Args:
        filename: Name of the file to check.
        media_extensions: Tuple of valid media extensions (lowercase).

    Returns:
        True if the file has a media extension, False otherwise.
    """
    return filename.lower().endswith(media_extensions)


def scan_directory_with_stats(
    root_path: str | Path,
) -> tuple[Iterator[os.DirEntry], dict[str, int]]:
    """Scan directory and return files with statistics.

    This is a convenience function that provides additional statistics
    about the scanning process, useful for performance monitoring.

    Args:
        root_path: Path to the directory to scan.

    Returns:
        Tuple of (file_iterator, stats_dict) where stats_dict contains:
        - 'files_found': Number of media files found
        - 'directories_scanned': Number of directories processed
        - 'permission_errors': Number of permission denied errors
        - 'other_errors': Number of other errors encountered
    """
    stats = {
        "files_found": 0,
        "directories_scanned": 0,
        "permission_errors": 0,
        "other_errors": 0,
    }

    def _scan_with_stats(path: str | Path) -> Iterator[os.DirEntry]:
        nonlocal stats
        root_path = Path(path)

        if not root_path.exists() or not root_path.is_dir():
            return

        media_extensions = tuple(ext.lower() for ext in APP_CONFIG.media_extensions)

        try:
            stats["directories_scanned"] += 1
            # Use context manager for proper resource cleanup
            with os.scandir(root_path) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        yield from _scan_with_stats(entry.path)
                    elif entry.is_file() and _is_media_file(
                        entry.name,
                        media_extensions,
                    ):
                        stats["files_found"] += 1
                        yield entry

        except PermissionError:
            stats["permission_errors"] += 1
            logger.warning(f"Permission denied to access: {root_path}")
        except OSError as e:
            stats["other_errors"] += 1
            logger.error(f"Error scanning directory {root_path}: {e}")
        except Exception as e:
            stats["other_errors"] += 1
            logger.error(f"Unexpected error scanning {root_path}: {e}")

    return _scan_with_stats(root_path), stats


def scan_directory_paths(root_path: str | Path) -> Iterator[str]:
    """Recursively scan a directory and yield file paths as strings.

    This function is specifically designed for integration with ScanParsePool.
    It yields file paths as strings rather than os.DirEntry objects, making
    it easier to work with in thread pool scenarios.

    Args:
        root_path: Path to the directory to scan (string or Path object).

    Yields:
        str: File paths found during the scan.

    Example:
        >>> for file_path in scan_directory_paths("/path/to/anime"):
        ...     print(f"Found: {file_path}")
    """
    for entry in scan_directory(root_path):
        yield entry.path


def get_media_files_count(root_path: str | Path) -> int:
    """Count the number of media files in a directory without yielding them.

    This function is useful for getting a quick count without the overhead
    of processing individual files.

    Args:
        root_path: Path to the directory to scan.

    Returns:
        Number of media files found in the directory tree.
    """
    count = 0
    for _ in scan_directory(root_path):
        count += 1
    return count
