"""
Folder Path Validation Module

This module provides utilities for validating folder paths and permissions
for the AniVault application.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FolderValidator:
    """Validates folder paths and permissions."""

    @staticmethod
    def validate_folder_path(path: str | Path) -> tuple[bool, str]:
        """Validate a folder path.

        Args:
            path: Folder path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not path:
            return False, "Path is empty"

        try:
            folder_path = Path(path).resolve()
        except (OSError, ValueError) as e:
            return False, f"Invalid path format: {e}"

        # Check if path exists
        if not folder_path.exists():
            return False, f"Path does not exist: {folder_path}"

        # Check if it's a directory
        if not folder_path.is_dir():
            return False, f"Path is not a directory: {folder_path}"

        # Check read permission
        if not os.access(folder_path, os.R_OK):
            return False, f"No read permission for: {folder_path}"

        return True, ""

    @staticmethod
    def validate_target_folder(path: str | Path) -> tuple[bool, str]:
        """Validate a target folder path (requires write permission).

        Args:
            path: Target folder path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not path:
            return False, "Path is empty"

        try:
            folder_path = Path(path).resolve()
        except (OSError, ValueError) as e:
            return False, f"Invalid path format: {e}"

        # Check if path exists
        if not folder_path.exists():
            # Try to create the directory
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                logger.info("Created target directory: %s", folder_path)
            except (OSError, PermissionError) as e:
                return False, f"Cannot create directory: {e}"

        # Check if it's a directory
        if not folder_path.is_dir():
            return False, f"Path is not a directory: {folder_path}"

        # Check write permission
        if not os.access(folder_path, os.W_OK):
            return False, f"No write permission for: {folder_path}"

        return True, ""

    @staticmethod
    def validate_folder_pair(source: str | Path, target: str | Path) -> tuple[bool, str]:
        """Validate source and target folder pair.

        Args:
            source: Source folder path
            target: Target folder path

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate source folder
        is_valid, error = FolderValidator.validate_folder_path(source)
        if not is_valid:
            return False, f"Source folder error: {error}"

        # Validate target folder
        is_valid, error = FolderValidator.validate_target_folder(target)
        if not is_valid:
            return False, f"Target folder error: {error}"

        # Check if target is inside source (prevent infinite loops)
        try:
            source_path = Path(source).resolve()
            target_path = Path(target).resolve()

            if target_path.is_relative_to(source_path):
                return False, "Target folder cannot be inside source folder"
        except (OSError, ValueError):
            # If we can't resolve paths, skip this check
            pass

        return True, ""

    @staticmethod
    def get_folder_info(path: str | Path) -> dict[str, Any]:
        """Get information about a folder.

        Args:
            path: Folder path

        Returns:
            Dictionary with folder information
        """
        info = {
            "path": str(path),
            "exists": False,
            "is_directory": False,
            "readable": False,
            "writable": False,
            "absolute_path": "",
            "error": "",
        }

        if not path:
            info["error"] = "Path is empty"
            return info

        try:
            folder_path = Path(path).resolve()
            info["absolute_path"] = str(folder_path)
            info["exists"] = folder_path.exists()

            if info["exists"]:
                info["is_directory"] = folder_path.is_dir()
                info["readable"] = os.access(folder_path, os.R_OK)
                info["writable"] = os.access(folder_path, os.W_OK)

        except (OSError, ValueError) as e:
            info["error"] = str(e)

        return info

    @staticmethod
    def sanitize_path(path: str) -> str:
        """Sanitize a path string for logging.

        Args:
            path: Path to sanitize

        Returns:
            Sanitized path safe for logging
        """
        if not path:
            return ""

        try:
            # Convert to Path and resolve
            resolved_path = Path(path).resolve()

            # Mask home directory
            home = Path.home()
            if str(resolved_path).startswith(str(home)):
                return str(Path("~") / resolved_path.relative_to(home))

            return str(resolved_path)
        except (OSError, ValueError):
            # If sanitization fails, return a safe placeholder
            return "<invalid_path>"
