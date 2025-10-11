"""
Theme Manager for AniVault GUI

This module provides centralized theme management using PySide6 QSS files
to ensure consistent styling across the application.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext
from anivault.utils.resource_path import get_resource_path

logger = logging.getLogger(__name__)

# Regular expression to detect @import directives in QSS files
# Matches: @import url("path/to/file.qss"); or @import url('path/to/file.qss');
# Captures the path in a named group
QSS_IMPORT_PATTERN = re.compile(
    r'^\s*@import\s+url\(["\']?(?P<path>[^"\']+)["\']?\)\s*;\s*$',
    re.MULTILINE,
)


class ThemeManager:
    """Manages application themes using QSS files."""

    # Available themes
    LIGHT_THEME = "light"
    DARK_THEME = "dark"
    DEFAULT_THEME = LIGHT_THEME

    def __init__(self, themes_dir: Path | None = None) -> None:
        """Initialize the ThemeManager.

        Args:
            themes_dir: Optional path to themes directory. If None, uses
                      default paths (bundle and user directories)
        """
        if themes_dir is not None:
            # Explicit path provided (development/testing)
            self.base_theme_dir = Path(themes_dir)
            self.user_theme_dir = self.base_theme_dir
        else:
            # Use bundle-aware default paths
            self.base_theme_dir = get_resource_path("anivault/resources/themes")
            self.user_theme_dir = self._get_user_theme_dir()

        # Active theme root: prefer user themes, fallback to bundled
        self.themes_dir = (
            self.user_theme_dir if self.user_theme_dir.exists() else self.base_theme_dir
        )

        self.current_theme: str | None = None
        self._ensure_themes_directory()

    @staticmethod
    def _is_bundle() -> bool:
        """Check if running in PyInstaller bundle.

        Returns:
            True if running as PyInstaller bundle, False otherwise
        """
        return hasattr(sys, "_MEIPASS")

    @staticmethod
    def _get_user_theme_dir() -> Path:
        """Get OS-specific user theme directory.

        Returns:
            Path to user's theme directory based on OS conventions

        Examples:
            Windows: %APPDATA%/AniVault/themes
            macOS: ~/Library/Application Support/AniVault/themes
            Linux: ~/.local/share/AniVault/themes
        """
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
            return base / "AniVault" / "themes"
        if sys.platform == "darwin":
            return Path.home() / "Library/Application Support/AniVault/themes"
        # Linux and other Unix-like
        return Path.home() / ".local/share/AniVault/themes"

    def _ensure_themes_directory(self) -> None:
        """Ensure the themes directory exists.

        In bundle mode, only creates user theme directory (bundle is read-only).
        In development mode, ensures the specified themes_dir exists.

        Raises:
            ApplicationError: If directory creation fails
        """
        try:
            if self._is_bundle():
                # Bundle mode: only create user theme directory
                self.user_theme_dir.mkdir(parents=True, exist_ok=True)
                logger.debug("User themes directory ensured: %s", self.user_theme_dir)
            else:
                # Development mode: ensure active themes_dir exists
                self.themes_dir.mkdir(parents=True, exist_ok=True)
                logger.debug("Themes directory ensured: %s", self.themes_dir)
        except Exception as e:
            logger.exception("Failed to create themes directory")
            directory_path = (
                self.user_theme_dir if self._is_bundle() else self.themes_dir
            )
            raise ApplicationError(
                ErrorCode.DIRECTORY_CREATION_FAILED,
                f"Failed to create themes directory: {e}",
                ErrorContext(
                    operation="_ensure_themes_directory",
                    additional_data={"directory": str(directory_path)},
                ),
            ) from e

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names.

        Returns:
            List of available theme names
        """
        themes = []
        try:
            for qss_file in self.themes_dir.glob("*.qss"):
                theme_name = qss_file.stem
                themes.append(theme_name)
            logger.debug("Available themes: %s", themes)
            return themes
        except Exception:
            logger.exception("Failed to get available themes")
            return []

    def _validate_import_path(self, qss_path: Path) -> Path:
        """Validate QSS import path for security.

        Ensures the path is within allowed theme directories (base or user)
        to prevent directory traversal attacks.

        Args:
            qss_path: Path to validate

        Returns:
            Resolved absolute path

        Raises:
            ApplicationError: If path is outside allowed directories
        """
        # Resolve to absolute path
        resolved_path = qss_path.resolve()

        # Check if path is within allowed directories
        try:
            base_resolved = self.base_theme_dir.resolve()
            if resolved_path.is_relative_to(base_resolved):
                logger.debug("Import path validated (base): %s", resolved_path)
                return resolved_path
        except (ValueError, AttributeError):
            pass

        try:
            user_resolved = self.user_theme_dir.resolve()
            if resolved_path.is_relative_to(user_resolved):
                logger.debug("Import path validated (user): %s", resolved_path)
                return resolved_path
        except (ValueError, AttributeError):
            pass

        # Path is outside allowed directories
        logger.error("Import path outside allowed directories: %s", resolved_path)
        raise ApplicationError(
            ErrorCode.INVALID_PATH,
            f"QSS import path outside allowed directories: {qss_path}",
            ErrorContext(
                operation="_validate_import_path",
                additional_data={
                    "requested_path": str(qss_path),
                    "resolved_path": str(resolved_path),
                    "allowed_base": str(base_resolved),
                    "allowed_user": str(user_resolved),
                },
            ),
        )

    def get_qss_path(self, theme_name: str) -> Path:
        """Get the path to a theme's QSS file.

        Searches user theme directory first, then falls back to bundled themes.
        Includes path traversal protection.

        Args:
            theme_name: Name of the theme

        Returns:
            Path to the QSS file

        Raises:
            ApplicationError: If theme file doesn't exist or invalid theme name
        """
        # Security: Prevent path traversal attacks
        if ".." in theme_name or "/" in theme_name or "\\" in theme_name:
            logger.error("Invalid theme name (path traversal attempt): %s", theme_name)
            raise ApplicationError(
                ErrorCode.SECURITY_VIOLATION,
                f"Invalid theme name: {theme_name}",
                ErrorContext(
                    operation="get_qss_path",
                    additional_data={"theme_name": theme_name},
                ),
            )

        # Priority 1: User theme directory
        user_path = self.user_theme_dir / f"{theme_name}.qss"
        if user_path.exists():
            logger.debug("Using user theme: %s", user_path)
            return user_path

        # Priority 2: Bundled theme directory
        base_path = self.base_theme_dir / f"{theme_name}.qss"
        if base_path.exists():
            logger.debug("Using bundled theme: %s", base_path)
            return base_path

        # Not found in either location
        logger.error("Theme file not found: %s", theme_name)
        raise ApplicationError(
            ErrorCode.FILE_NOT_FOUND,
            f"Theme file not found: {theme_name}",
            ErrorContext(
                operation="get_qss_path",
                additional_data={
                    "theme_name": theme_name,
                    "searched_user_path": str(user_path),
                    "searched_bundled_path": str(base_path),
                },
            ),
        )

    def _read_file_with_imports(
        self, qss_path: Path, visited: set[Path] | None = None
    ) -> str:
        """Read QSS file and resolve @import directives recursively.

        Supports @import url("path/to/file.qss"); syntax.
        Includes circular import detection and path security validation.

        Args:
            qss_path: Path to QSS file to read
            visited: Set of already visited paths (for circular detection)

        Returns:
            QSS content with all imports resolved

        Raises:
            ApplicationError: If circular import detected or invalid path
        """
        # Initialize visited set
        if visited is None:
            visited = set()

        # Validate and resolve path
        resolved_path = self._validate_import_path(qss_path)

        # Check for circular imports
        if resolved_path in visited:
            logger.error("Circular QSS import detected: %s", resolved_path)
            # Convert visited paths to comma-separated string for ErrorContext
            visited_str = ", ".join(str(p) for p in visited)
            raise ApplicationError(
                ErrorCode.CONFIG_ERROR,
                f"Circular QSS import detected: {resolved_path}",
                ErrorContext(
                    operation="_read_file_with_imports",
                    additional_data={
                        "circular_path": str(resolved_path),
                        "visited_paths": visited_str,
                    },
                ),
            )

        # Mark as visited
        visited.add(resolved_path)

        try:
            # Read file content
            content = resolved_path.read_text(encoding="utf-8")
            lines = []

            # Process each line
            for line in content.splitlines():
                # Check for @import directive
                match = QSS_IMPORT_PATTERN.match(line)
                if match:
                    # Extract import path
                    import_path = match.group("path")
                    # Resolve relative to current file's directory
                    nested_path = resolved_path.parent / import_path

                    logger.debug(
                        "Processing QSS import: %s -> %s", import_path, nested_path
                    )

                    # Recursively read imported file
                    imported_content = self._read_file_with_imports(
                        nested_path, visited
                    )
                    lines.append(imported_content)
                else:
                    # Regular line, keep as-is
                    lines.append(line)

            return "\n".join(lines)

        except FileNotFoundError as e:
            logger.exception("QSS import file not found: %s", resolved_path)
            raise ApplicationError(
                ErrorCode.FILE_NOT_FOUND,
                f"QSS import file not found: {resolved_path}",
                ErrorContext(
                    operation="_read_file_with_imports",
                    file_path=str(resolved_path),
                ),
            ) from e
        except Exception as e:
            logger.exception("Failed to read QSS file with imports: %s", resolved_path)
            raise ApplicationError(
                ErrorCode.FILE_READ_ERROR,
                f"Failed to read QSS file with imports: {resolved_path}: {e}",
                ErrorContext(
                    operation="_read_file_with_imports",
                    file_path=str(resolved_path),
                ),
            ) from e

    def load_theme_content(self, theme_name: str) -> str:
        """Load QSS content from a theme file with @import resolution.

        Resolves @import directives recursively and includes circular
        import detection and path security validation.

        Args:
            theme_name: Name of the theme to load

        Returns:
            QSS content as string with all imports resolved

        Raises:
            ApplicationError: If theme file cannot be read or imports fail
        """
        try:
            qss_path = self.get_qss_path(theme_name)

            # Read with @import resolution
            content = self._read_file_with_imports(qss_path)

            logger.debug(
                "Loaded theme content for: %s (with imports resolved)", theme_name
            )
            return content

        except ApplicationError:
            # Re-raise ApplicationError as-is
            raise
        except Exception as e:
            logger.exception("Failed to load theme content for %s", theme_name)
            raise ApplicationError(
                ErrorCode.FILE_READ_ERROR,
                f"Failed to load theme content for {theme_name}: {e}",
                ErrorContext(
                    operation="load_theme_content",
                    additional_data={"theme_name": theme_name},
                ),
            ) from e

    def apply_theme(self, theme_name: str) -> None:
        """Apply a theme to the application.

        Args:
            theme_name: Name of the theme to apply

        Raises:
            ApplicationError: If theme cannot be applied
        """
        try:
            # Load theme content
            qss_content = self.load_theme_content(theme_name)

            # Apply to application
            app = QApplication.instance()
            if app is None:
                logger.error("No QApplication instance found")
                raise ApplicationError(
                    ErrorCode.APPLICATION_ERROR,
                    "No QApplication instance found",
                )

            # 1) 이전 스타일 제거 + 플랫폼 기본 팔레트로 리셋
            app.setStyleSheet("")
            app.setPalette(app.style().standardPalette())

            # 2) 새 스타일 적용
            app.setStyleSheet(qss_content)
            self.current_theme = theme_name

            # 3) 위젯 리폴리시 (툴바/메뉴/상태바까지 강제 반영)
            self._repolish_all_top_levels(app)

            logger.info("Applied theme: %s", theme_name)

        except Exception as e:
            logger.exception("Failed to apply theme %s", theme_name)
            raise ApplicationError(
                ErrorCode.APPLICATION_ERROR,
                f"Failed to apply theme {theme_name}: {e}",
            ) from e

    def _repolish_all_top_levels(self, app: QApplication) -> None:
        """Repolish all top-level widgets to ensure theme changes are applied."""
        for widget in app.topLevelWidgets():
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def get_current_theme(self) -> str | None:
        """Get the currently applied theme.

        Returns:
            Name of current theme, or None if no theme applied
        """
        return self.current_theme

    def load_and_apply_theme(self, app: QApplication, theme_name: str) -> None:
        """Load and apply a theme to the application.

        DEPRECATED: Use apply_theme() instead. This method is kept for backward
        compatibility and delegates to apply_theme().

        Args:
            app: QApplication instance (unused, kept for compatibility)
            theme_name: Name of the theme to load and apply
        """
        logger.warning(
            "load_and_apply_theme() is deprecated, use apply_theme() instead"
        )
        try:
            self.apply_theme(theme_name)
        except ApplicationError:
            # Fallback to default theme if available
            if theme_name != self.DEFAULT_THEME:
                logger.warning("Falling back to default theme: %s", self.DEFAULT_THEME)
                try:
                    self.apply_theme(self.DEFAULT_THEME)
                except Exception as fallback_error:
                    logger.exception("Failed to apply fallback theme")
                    raise ApplicationError(
                        ErrorCode.APPLICATION_ERROR,
                        f"Failed to apply any theme: {fallback_error}",
                    ) from fallback_error
            else:
                raise
