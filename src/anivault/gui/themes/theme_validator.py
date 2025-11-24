"""
Theme Validator for AniVault GUI

This module provides input validation for theme names and QSS import paths,
ensuring security and preventing directory traversal attacks.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

logger = logging.getLogger(__name__)

# Maximum theme name length (security limit)
MAX_THEME_NAME_LENGTH = 50


class ThemeValidator:
    """Validates theme names and import paths for security.

    This class is responsible for input validation to prevent:
    - Path traversal attacks (../, ../../etc/passwd, etc.)
    - Invalid theme names (special characters, excessive length)
    - Access to files outside allowed directories

    Security:
        - base_theme_dir is REQUIRED for path traversal prevention
        - validate_import_path checks if resolved path is within
          EITHER themes_dir OR base_theme_dir
        - Both directories are allowed to support PyInstaller bundle mode
    """

    def __init__(self, themes_dir: Path, base_theme_dir: Path) -> None:
        """Initialize validator with theme directories.

        Args:
            themes_dir: User theme directory (e.g., ~/.anivault/themes)
            base_theme_dir: Base theme directory (bundle or development)
                           CRITICAL: Used to prevent path traversal in imports
                           while allowing bundle theme access
        """
        self.themes_dir = themes_dir
        self.base_theme_dir = base_theme_dir

    def validate_theme_name(self, theme_name: str) -> str:
        """Validate and sanitize theme name input.

        Args:
            theme_name: Raw theme name from user input

        Returns:
            str: Validated theme name (unchanged if valid)

        Raises:
            ApplicationError with ErrorCode.VALIDATION_ERROR if:
                - theme_name is empty or None
                - length > 50 characters
                - contains invalid characters (only alphanumeric, hyphen, underscore allowed)
                - contains path separators (/, \\, ..)
        """
        if not theme_name:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "Theme name cannot be empty",
                ErrorContext(operation="validate_theme_name"),
            )

        if len(theme_name) > MAX_THEME_NAME_LENGTH:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Theme name too long (max {MAX_THEME_NAME_LENGTH} characters): {len(theme_name)}",
                ErrorContext(
                    operation="validate_theme_name",
                    additional_data={"theme_name": theme_name[:50]},
                ),
            )

        # Security: Prevent path traversal attacks
        if any(char in theme_name for char in ["/", "\\", ".."]):
            logger.error("Invalid theme name (path traversal attempt): %s", theme_name)
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid theme name (contains path separators): {theme_name}",
                ErrorContext(
                    operation="validate_theme_name",
                    additional_data={"theme_name": theme_name},
                ),
            )

        # Only allow alphanumeric, hyphen, and underscore
        if not re.match(r"^[a-zA-Z0-9_-]+$", theme_name):
            logger.error("Invalid theme name (invalid characters): %s", theme_name)
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid theme name (only alphanumeric, hyphen, underscore allowed): {theme_name}",
                ErrorContext(
                    operation="validate_theme_name",
                    additional_data={"theme_name": theme_name},
                ),
            )

        return theme_name

    def validate_import_path(self, qss_path: Path) -> Path:
        """Validate QSS import path for security.

        Ensures the path is within EITHER themes_dir OR base_theme_dir
        to prevent directory traversal attacks while allowing bundle theme imports.

        This implements the bug fix from theme_manager.py:381-383 where
        the original code only validated themes_dir, preventing bundle themes
        from importing common.qss and other shared resources.

        Security:
            - themes_dir: User-writable directory
            - base_theme_dir: Bundle themes (read-only in PyInstaller mode)
            - Both directories are allowed for imports
            - Paths outside both directories are rejected

        Args:
            qss_path: Path to validate

        Returns:
            Resolved absolute path

        Raises:
            ApplicationError: If path is outside allowed directories
        """
        # Resolve to absolute path
        resolved_path = qss_path.resolve()
        themes_dir_resolved = self.themes_dir.resolve()
        base_dir_resolved = self.base_theme_dir.resolve()

        # Check if path is within EITHER themes_dir OR base_theme_dir
        # CRITICAL: OR condition allows bundle theme imports (bug fix)
        try:
            if resolved_path.is_relative_to(themes_dir_resolved) or resolved_path.is_relative_to(base_dir_resolved):
                logger.debug("Import path validated: %s", resolved_path)
                return resolved_path
        except (ValueError, AttributeError):
            # is_relative_to not available or comparison failed
            pass

        # Path is outside allowed directories
        logger.error(
            "Import path outside allowed directories: %s (allowed: %s, %s)",
            resolved_path,
            themes_dir_resolved,
            base_dir_resolved,
        )
        raise ApplicationError(
            ErrorCode.VALIDATION_ERROR,
            f"QSS import path outside allowed directories: {qss_path}",
            ErrorContext(
                operation="validate_import_path",
                additional_data={
                    "requested_path": str(qss_path),
                    "resolved_path": str(resolved_path),
                    "themes_dir": str(themes_dir_resolved),
                    "base_theme_dir": str(base_dir_resolved),
                },
            ),
        )
