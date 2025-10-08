"""
Smart Filtering Engine for AniVault

This module provides the FilterEngine class that intelligently prunes file lists
during directory scanning to minimize I/O and improve performance.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any

from anivault.config.settings import FilterConfig


class FilterEngine:
    """
    Smart filtering engine that prunes file and directory lists during scanning.

    This engine applies multiple filtering strategies to exclude unwanted files
    and directories early in the scanning process, reducing I/O operations
    and improving overall performance.
    """

    def __init__(self, config: FilterConfig) -> None:
        """
        Initialize the FilterEngine with configuration.

        Args:
            config: Filter configuration containing all filtering rules
        """
        self.config = config

        # Pre-compile patterns for better performance
        self._compiled_filename_patterns = [
            pattern.lower() for pattern in config.excluded_filename_patterns
        ]
        self._compiled_dir_patterns = [
            pattern.lower() for pattern in config.excluded_dir_patterns
        ]

        # Pre-compile extensions for faster lookup
        self._allowed_extensions_set = {
            ext.lower() for ext in config.allowed_extensions
        }

    def should_skip_directory(self, dir_name: str) -> bool:
        """
        Check if a directory should be skipped based on exclusion patterns.

        Args:
            dir_name: Name of the directory to check

        Returns:
            True if the directory should be skipped, False otherwise
        """
        dir_name_lower = dir_name.lower()

        # Check if directory matches any exclusion pattern
        for pattern in self._compiled_dir_patterns:
            if fnmatch.fnmatch(dir_name_lower, pattern):
                return True

        # Check if directory matches filename exclusion patterns (for patterns like *sample*, *trailer*, etc.)
        for pattern in self._compiled_filename_patterns:
            if fnmatch.fnmatch(dir_name_lower, pattern):
                return True

        # Check for hidden directories if enabled
        if self.config.skip_hidden_files and dir_name.startswith("."):
            return True

        # Check for system directories if enabled
        if self.config.skip_system_files:
            system_dirs = {
                "system volume information",
                "recycler",
                "recycled",
                "lost+found",
                "found.000",
                "found.001",
            }
            if dir_name_lower in system_dirs:
                return True

        return False

    def should_skip_file(
        self,
        file_path: str | Path,
        file_stat: os.stat_result,
    ) -> bool:
        """
        Check if a file should be skipped based on filtering rules.

        This method applies filters in order of efficiency:
        1. Extension filtering (fastest)
        2. Filename pattern filtering
        3. File size filtering (most expensive)

        Args:
            file_path: Path to the file to check
            file_stat: os.stat_result object containing file information

        Returns:
            True if the file should be skipped, False otherwise
        """
        file_path = Path(file_path)
        file_name = file_path.name.lower()

        # 1. Extension filtering (fastest check)
        file_ext = file_path.suffix.lower()
        if file_ext not in self._allowed_extensions_set:
            return True

        # 2. Filename pattern filtering
        for pattern in self._compiled_filename_patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return True

        # 3. Hidden file filtering
        if self.config.skip_hidden_files and file_name.startswith("."):
            return True

        # 4. System file filtering
        if self.config.skip_system_files:
            system_files = {"thumbs.db", "desktop.ini", ".ds_store", "folder.jpg"}
            if file_name in system_files:
                return True

        # 5. File size filtering (most expensive - done last)
        if self.config.min_file_size_mb > 0:
            file_size_mb = file_stat.st_size / (1024 * 1024)
            if file_size_mb < self.config.min_file_size_mb:
                return True

        return False

    def filter_extensions(self, extensions: list[str]) -> list[str]:
        """
        Filter a list of extensions to only include allowed ones.

        Args:
            extensions: List of file extensions to filter

        Returns:
            List of extensions that are allowed by the configuration
        """
        allowed_extensions = []
        for ext in extensions:
            if ext.lower() in self._allowed_extensions_set:
                allowed_extensions.append(ext)

        return allowed_extensions

    def get_allowed_extensions(self) -> list[str]:
        """
        Get the list of allowed file extensions.

        Returns:
            List of allowed file extensions
        """
        return self.config.allowed_extensions.copy()

    def get_min_file_size_mb(self) -> int:
        """
        Get the minimum file size threshold in MB.

        Returns:
            Minimum file size in MB
        """
        return self.config.min_file_size_mb

    def is_extension_allowed(self, extension: str) -> bool:
        """
        Check if a specific extension is allowed.

        Args:
            extension: File extension to check (with or without dot)

        Returns:
            True if the extension is allowed, False otherwise
        """
        # Ensure extension starts with a dot
        if not extension.startswith("."):
            extension = f".{extension}"

        return extension.lower() in self._allowed_extensions_set

    def get_excluded_patterns_summary(self) -> dict[str, Any]:
        """
        Get a summary of all exclusion patterns for debugging/logging.

        Returns:
            Dictionary containing excluded patterns by category
        """
        return {
            "filename_patterns": self.config.excluded_filename_patterns,
            "directory_patterns": self.config.excluded_dir_patterns,
            "allowed_extensions": self.config.allowed_extensions,
            "min_file_size_mb": self.config.min_file_size_mb,
            "skip_hidden_files": self.config.skip_hidden_files,
            "skip_system_files": self.config.skip_system_files,
        }

    def __repr__(self) -> str:
        """Return a string representation of the FilterEngine."""
        return (
            f"FilterEngine("
            f"extensions={len(self.config.allowed_extensions)}, "
            f"min_size={self.config.min_file_size_mb}MB, "
            f"filename_patterns={len(self.config.excluded_filename_patterns)}, "
            f"dir_patterns={len(self.config.excluded_dir_patterns)}"
            f")"
        )
