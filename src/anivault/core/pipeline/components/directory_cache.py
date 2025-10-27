"""Directory-level caching for incremental scans.

This module provides a caching mechanism that stores directory modification times
and their contents, allowing the scanner to skip unchanged directories on subsequent runs.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from anivault.core.data_structures.linked_hash_table import LinkedHashTable
from anivault.shared.errors import ErrorCode, ErrorContext, InfrastructureError

logger = logging.getLogger(__name__)


@dataclass
class DirectoryInfo:
    """Directory cache information."""

    mtime: float
    files: list[str]
    subdirs: list[str]


class DirectoryCacheManager:
    """
    Manages directory-level cache for incremental scans.

    This cache stores modification times (mtime) of directories along with
    their file and subdirectory lists, enabling fast incremental scans by
    skipping unchanged directories.
    """

    def __init__(self, cache_file: Path | str = ".anivault_scan_cache.json") -> None:
        """
        Initialize the directory cache manager.

        Args:
            cache_file: Path to the JSON cache file. Defaults to '.anivault_scan_cache.json'
                       in the current directory.
        """
        self.cache_file = Path(cache_file)
        self._cache: LinkedHashTable[str, DirectoryInfo] = LinkedHashTable()
        self._lock = threading.Lock()
        self._loaded = False

    def load_cache(self) -> None:
        """
        Load the cache from the JSON file.

        If the file doesn't exist, initializes an empty cache.
        Handles JSON parsing errors gracefully.

        Raises:
            InfrastructureError: If cache file cannot be read due to permission issues.
        """
        with self._lock:
            if self._loaded:
                return

            context = ErrorContext(
                operation="load_cache",
                file_path=str(self.cache_file),
            )

            try:
                if self.cache_file.exists():
                    with open(self.cache_file, encoding="utf-8") as f:
                        cache_data = json.load(f)
                        # Convert dict to LinkedHashTable with DirectoryInfo
                        self._cache = LinkedHashTable()
                        for key, value in cache_data.items():
                            if isinstance(value, dict):
                                dir_info = DirectoryInfo(
                                    mtime=value["mtime"],
                                    files=value["files"],
                                    subdirs=value["subdirs"],
                                )
                                self._cache.put(key, dir_info)
                else:
                    self._cache = LinkedHashTable()
            except PermissionError as e:
                error = InfrastructureError(
                    code=ErrorCode.FILE_ACCESS_DENIED,
                    message=f"Permission denied reading cache file: {self.cache_file}",
                    context=context,
                    original_error=e,
                )
                logger.exception(
                    "Failed to load cache due to permission error: %s",
                    self.cache_file,
                )
                raise error from e
            except OSError as e:
                # Handle other file system errors (disk full, network issues, etc.)
                error = InfrastructureError(
                    code=ErrorCode.FILE_READ_ERROR,
                    message=f"File system error reading cache file: {self.cache_file}",
                    context=context,
                    original_error=e,
                )
                logger.warning(
                    "File system error loading cache, starting with empty cache: %s",
                    self.cache_file,
                    exc_info=True,
                )
                # For OSError, start with empty cache rather than failing completely
                self._cache = LinkedHashTable()
            except json.JSONDecodeError:
                # Handle corrupted JSON gracefully
                logger.warning(
                    "Corrupted cache file detected, starting with empty cache: %s",
                    self.cache_file,
                    exc_info=True,
                )
                self._cache = LinkedHashTable()

            self._loaded = True

    def save_cache(self) -> None:
        """
        Save the current cache to the JSON file.

        Creates the file if it doesn't exist. Handles write errors gracefully.

        Raises:
            InfrastructureError: If cache file cannot be written due to critical errors.
        """
        with self._lock:
            context = ErrorContext(
                operation="save_cache",
                file_path=str(self.cache_file),
            )

            try:
                # Convert LinkedHashTable to dict for JSON serialization
                cache_dict = {}
                for key, dir_info in self._cache:
                    cache_dict[key] = {
                        "mtime": dir_info.mtime,
                        "files": dir_info.files,
                        "subdirs": dir_info.subdirs,
                    }

                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache_dict, f, indent=2, ensure_ascii=False)
                logger.debug("Successfully saved cache to: %s", self.cache_file)
            except PermissionError as e:
                error = InfrastructureError(
                    code=ErrorCode.FILE_ACCESS_DENIED,
                    message=f"Permission denied writing cache file: {self.cache_file}",
                    context=context,
                    original_error=e,
                )
                logger.exception(
                    "Failed to save cache due to permission error: %s",
                    self.cache_file,
                )
                raise error from e
            except OSError as e:
                # Handle other file system errors (disk full, network issues, etc.)
                error = InfrastructureError(
                    code=ErrorCode.FILE_WRITE_ERROR,
                    message=f"File system error writing cache file: {self.cache_file}",
                    context=context,
                    original_error=e,
                )
                logger.warning(
                    "File system error saving cache (continuing without cache): %s",
                    self.cache_file,
                    exc_info=True,
                )
                # For OSError, log but don't fail the operation completely
                # This allows the application to continue functioning without cache

    def get_directory_data(self, dir_path: str | Path) -> DirectoryInfo | None:
        """
        Retrieve cached data for a directory.

        Args:
            dir_path: Path to the directory.

        Returns:
            DirectoryInfo object containing:
                - mtime: float - Last modification time
                - files: list[str] - List of file names in the directory
                - subdirs: list[str] - List of subdirectory names
            Returns None if the directory is not in the cache.
        """
        with self._lock:
            key = str(Path(dir_path).resolve())
            return self._cache.get(key)

    def update_directory_data(
        self,
        dir_path: str | Path,
        mtime: float,
        files: list[str],
        subdirs: list[str],
    ) -> None:
        """
        Update or add cached data for a directory.

        Args:
            dir_path: Path to the directory.
            mtime: Current modification time of the directory.
            files: List of file names in the directory.
            subdirs: List of subdirectory names in the directory.
        """
        with self._lock:
            key = str(Path(dir_path).resolve())
            dir_info = DirectoryInfo(mtime=mtime, files=files, subdirs=subdirs)
            self._cache.put(key, dir_info)

    def clear_cache(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache = LinkedHashTable()

    def remove_directory(self, dir_path: str | Path) -> None:
        """
        Remove a specific directory from the cache.

        Args:
            dir_path: Path to the directory to remove.
        """
        with self._lock:
            key = str(Path(dir_path).resolve())
            self._cache.remove(key)

    def get_cache_size(self) -> int:
        """
        Get the number of directories in the cache.

        Returns:
            Number of cached directories.
        """
        with self._lock:
            return len(self._cache)

    def is_directory_cached(self, dir_path: str | Path, current_mtime: float) -> bool:
        """
        Check if a directory is cached and unchanged.

        Args:
            dir_path: Path to the directory.
            current_mtime: Current modification time of the directory.

        Returns:
            True if the directory is cached and its mtime matches, False otherwise.
        """
        cached_data = self.get_directory_data(dir_path)
        if cached_data is None:
            return False

        # Compare modification times (with small epsilon for float comparison)
        cached_mtime = cached_data.mtime
        return abs(cached_mtime - current_mtime) < 0.001
