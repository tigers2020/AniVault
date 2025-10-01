"""Directory-level caching for incremental scans.

This module provides a caching mechanism that stores directory modification times
and their contents, allowing the scanner to skip unchanged directories on subsequent runs.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


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
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._loaded = False

    def load_cache(self) -> None:
        """
        Load the cache from the JSON file.

        If the file doesn't exist, initializes an empty cache.
        Handles JSON parsing errors gracefully.
        """
        with self._lock:
            if self._loaded:
                return

            try:
                if self.cache_file.exists():
                    with open(self.cache_file, encoding="utf-8") as f:
                        self._cache = json.load(f)
                else:
                    self._cache = {}
            except (OSError, json.JSONDecodeError):
                # If cache is corrupted or unreadable, start fresh
                self._cache = {}

            self._loaded = True

    def save_cache(self) -> None:
        """
        Save the current cache to the JSON file.

        Creates the file if it doesn't exist. Handles write errors gracefully.
        """
        with self._lock:
            try:
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f, indent=2, ensure_ascii=False)
            except OSError:
                # Silently fail if we can't write the cache
                pass

    def get_directory_data(self, dir_path: str | Path) -> dict[str, Any] | None:
        """
        Retrieve cached data for a directory.

        Args:
            dir_path: Path to the directory.

        Returns:
            Dictionary containing:
                - 'mtime': float - Last modification time
                - 'files': list[str] - List of file names in the directory
                - 'subdirs': list[str] - List of subdirectory names
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
            self._cache[key] = {"mtime": mtime, "files": files, "subdirs": subdirs}

    def clear_cache(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._cache = {}

    def remove_directory(self, dir_path: str | Path) -> None:
        """
        Remove a specific directory from the cache.

        Args:
            dir_path: Path to the directory to remove.
        """
        with self._lock:
            key = str(Path(dir_path).resolve())
            self._cache.pop(key, None)

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
        cached_mtime = cached_data.get("mtime", 0.0)
        return abs(cached_mtime - current_mtime) < 0.001
