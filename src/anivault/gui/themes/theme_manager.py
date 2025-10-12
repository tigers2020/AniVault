"""
Theme Manager for AniVault GUI

This module provides centralized theme management using PySide6 QSS files
to ensure consistent styling across the application.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from PySide6.QtWidgets import QApplication

from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

from .path_resolver import ThemePathResolver
from .theme_cache import ThemeCache
from .theme_validator import ThemeValidator

logger = logging.getLogger(__name__)

# Regular expression to detect @import directives in QSS files
# Matches: @import url("path/to/file.qss"); or @import url('path/to/file.qss');
# Captures the path in a named group
QSS_IMPORT_PATTERN = re.compile(
    r'^\s*@import\s+url\(["\']?(?P<path>[^"\']+)["\']?\)\s*;\s*$',
    re.MULTILINE,
)

# Maximum recursion depth for @import resolution (security limit)
MAX_IMPORT_DEPTH = 10


class ThemeManager:
    """Manages application themes using QSS files."""

    # Available themes
    LIGHT_THEME = "light"
    DARK_THEME = "dark"
    DEFAULT_THEME = LIGHT_THEME

    def __init__(self, themes_dir: Path | None = None) -> None:
        """Initialize the ThemeManager.

        Detects PyInstaller bundle environment and sets up appropriate
        theme directories (bundled + user-writable).

        Args:
            themes_dir: Optional path to themes directory. If None, uses
                      default path based on environment (bundle/development)
        """
        # Initialize path resolver (handles all path-related logic)
        # Note: ThemeValidator is created inside ThemePathResolver for validation
        # We create a temporary validator first for the path resolver
        temp_validator = ThemeValidator(
            themes_dir=Path.home() / ".anivault" / "themes",  # temporary
            base_theme_dir=Path.home() / ".anivault" / "themes",  # temporary
        )
        self._path_resolver = ThemePathResolver(themes_dir, temp_validator)

        # Now create the proper validator with actual paths from resolver
        self._validator = ThemeValidator(
            themes_dir=self._path_resolver.themes_dir,
            base_theme_dir=self._path_resolver.base_theme_dir,
        )

        # Update path resolver's validator reference
        self._path_resolver._validator = self._validator

        # Initialize theme cache with validator
        self._cache = ThemeCache(self._validator)

        # Expose commonly used path properties for backward compatibility
        self.themes_dir = self._path_resolver.themes_dir
        self.base_theme_dir = self._path_resolver.base_theme_dir
        self.user_theme_dir = self._path_resolver.user_theme_dir
        self._is_bundled = self._path_resolver.is_bundled

        self.current_theme: str | None = None

        # Initialize bundle themes if running as PyInstaller bundle
        if self._path_resolver.is_bundled:
            self._path_resolver.ensure_bundle_themes()

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

    def _mask_home_path(self, path: Path) -> str:
        """Mask home directory in path for secure logging.

        Delegates to ThemePathResolver for path masking.

        Args:
            path: Path to mask

        Returns:
            String path with home directory masked
        """
        return self._path_resolver.mask_home_path(path)

    def get_qss_path(self, theme_name: str) -> Path | None:
        """Get the path to a theme's QSS file with fallback priority.

        Delegates to ThemePathResolver for path resolution.

        Args:
            theme_name: Name of the theme

        Returns:
            Path to the QSS file, or None if not found after all fallbacks

        Raises:
            ApplicationError: If theme name is invalid (security)
        """
        return self._path_resolver.get_qss_path(theme_name)

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
            ApplicationError: If circular import detected, invalid path,
                            or max depth exceeded
        """
        # Initialize visited set
        if visited is None:
            visited = set()

        # Check depth limit (security: prevent DoS)
        if len(visited) >= MAX_IMPORT_DEPTH:
            logger.error("Max import depth exceeded: %d", len(visited))
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                f"Max QSS import depth exceeded ({MAX_IMPORT_DEPTH})",
                ErrorContext(
                    operation="_read_file_with_imports",
                    additional_data={"depth": len(visited)},
                ),
            )

        # Validate and resolve path
        resolved_path = self._validator.validate_import_path(qss_path)

        # Check for circular imports
        if resolved_path in visited:
            logger.error("Circular QSS import detected: %s", resolved_path)
            visited_str = ", ".join(str(p) for p in visited)
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
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

        Performance monitoring: Logs DEBUG timing for all loads,
        WARNING if loading exceeds 50ms (potential performance issue).

        If theme file cannot be found after all fallback attempts,
        returns empty string to allow application to continue with
        minimal styling.

        Args:
            theme_name: Name of the theme to load

        Returns:
            QSS content as string with all imports resolved,
            or empty string if theme not found (safe fallback)

        Raises:
            ApplicationError: If theme file read fails (not file-not-found)
        """
        import time

        start_time = time.perf_counter()
        qss_path = None

        try:
            qss_path = self.get_qss_path(theme_name)

            # Handle None return (all fallbacks exhausted)
            if qss_path is None:
                logger.warning(
                    "No theme file found for %s after all fallbacks, using empty stylesheet",
                    theme_name,
                    extra=ErrorContext(
                        file_path=f"{theme_name}.qss",
                        additional_data={
                            "stage": "final-fallback",
                            "theme_name": theme_name,
                            "fallback_result": "empty-stylesheet",
                        },
                    ).model_dump(),
                )
                return ""  # Safe fallback: empty stylesheet

            # Use cached @import-aware reader (mtime-based)
            content = self._cache.get_or_load(qss_path, self._read_file_with_imports)

            # Performance monitoring
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # Log performance metrics
            if elapsed_ms > 50:
                logger.warning(
                    "Theme loading exceeded 50ms threshold: %s (%.2fms)",
                    theme_name,
                    elapsed_ms,
                )
            else:
                logger.debug(
                    "Loaded theme content for: %s (%.2fms, with imports)",
                    theme_name,
                    elapsed_ms,
                )

            return content

        except ApplicationError as e:
            # Re-raise ApplicationError (not file-not-found, but read errors)
            if e.code == ErrorCode.FILE_NOT_FOUND:
                logger.warning(
                    "Theme file not found: %s, using empty stylesheet",
                    theme_name,
                    extra=ErrorContext(
                        file_path=str(qss_path) if qss_path else f"{theme_name}.qss",
                        additional_data={
                            "stage": "load-error",
                            "theme_name": theme_name,
                            "error_code": e.code.value,
                        },
                    ).model_dump(),
                )
                return ""  # Safe fallback for file-not-found
            raise  # Re-raise other ApplicationErrors
        except Exception as e:
            logger.exception("Failed to load theme content for %s", theme_name)
            raise ApplicationError(
                ErrorCode.FILE_READ_ERROR,
                f"Failed to load theme content for {theme_name}: {e}",
                ErrorContext(
                    file_path=str(qss_path) if qss_path else f"{theme_name}.qss",
                ),
            ) from e

    def apply_theme(
        self,
        theme_name: str,
        app: QApplication | None = None,
        _fallback_attempted: bool = False,
    ) -> None:
        """Apply a theme with automatic fallback and recursion prevention.

        Implements 3-level fallback strategy:
        - Level 1: Try requested theme
        - Level 2: On failure, try DEFAULT_THEME (light) if different
        - Level 3: On failure, apply empty stylesheet (safe mode)

        Args:
            theme_name: Name of the theme to apply
            app: QApplication instance (None = auto-detect)
            _fallback_attempted: Internal flag to prevent infinite recursion
                                (DO NOT SET MANUALLY)

        Raises:
            ApplicationError: If theme cannot be applied and all fallbacks fail
        """
        # Validate theme name (security)
        theme_name = self._validator.validate_theme_name(theme_name)

        # Get QApplication instance
        if app is None:
            # QApplication.instance() returns QCoreApplication | None
            # We need to cast it to QApplication for type checker
            instance = QApplication.instance()
            if instance is None:
                logger.error("No QApplication instance found")
                raise ApplicationError(
                    ErrorCode.APPLICATION_ERROR,
                    "No QApplication instance found",
                    ErrorContext(operation="apply_theme"),
                )
            # Type assertion: instance is guaranteed to be QApplication here
            # because QCoreApplication.instance() returns the QApplication if one exists
            app = instance  # type: ignore[assignment]

        # Level 1: Try requested theme
        try:
            logger.info("Applying theme: %s", theme_name)

            # Load theme content
            qss_content = self.load_theme_content(theme_name)

            # Apply to application
            # 1) 이전 스타일 제거
            app.setStyleSheet("")

            # 2) 새 스타일 적용
            app.setStyleSheet(qss_content)
            self.current_theme = theme_name

            # 3) 위젯 리폴리시 (툴바/메뉴/상태바까지 강제 반영)
            self._repolish_all_top_levels(app)

            logger.info("Successfully applied theme: %s", theme_name)
            return  # Success!

        except Exception as e:
            logger.warning(
                "Failed to apply theme %s: %s",
                theme_name,
                e,
                exc_info=True,
            )

            # Level 2: Fallback to default theme (if not already trying default)
            if not _fallback_attempted and theme_name != self.DEFAULT_THEME:
                logger.warning(
                    "Falling back to default theme: %s",
                    self.DEFAULT_THEME,
                )
                try:
                    # Recursive call with fallback flag
                    self.apply_theme(
                        self.DEFAULT_THEME,
                        app=app,
                        _fallback_attempted=True,
                    )
                    return  # Fallback success!
                except Exception:
                    logger.exception(
                        "Failed to apply fallback theme %s",
                        self.DEFAULT_THEME,
                    )

            # Level 3: Safe mode - apply empty stylesheet
            logger.error(  # noqa: TRY400
                "All theme loading failed. Entering safe mode (empty stylesheet)."
            )
            try:
                app.setStyleSheet("")
                app.setPalette(app.style().standardPalette())
                self._repolish_all_top_levels(app)
                self.current_theme = None  # No theme applied
                logger.warning("Safe mode activated: using default system styles")
                # Don't raise error in safe mode - allow app to continue
                return
            except Exception as safe_mode_error:  # noqa: BLE001
                # Safe mode also failed - this is critical (broad catch necessary for safety)
                logger.critical(
                    "Safe mode failed: %s",
                    safe_mode_error,
                    exc_info=True,
                )
            raise ApplicationError(
                ErrorCode.APPLICATION_ERROR,
                f"Failed to apply theme and all fallbacks: {e}",
                ErrorContext(
                    operation="apply_theme",
                    additional_data={
                        "requested_theme": theme_name,
                        "fallback_theme": self.DEFAULT_THEME,
                        "safe_mode": True,
                    },
                ),
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

    def refresh_theme_cache(self, theme_name: str | None = None) -> None:
        """Invalidate and refresh theme cache.

        Delegates to ThemeCache for cache management.

        Args:
            theme_name: Specific theme to refresh, or None for all themes
        """
        self._cache.refresh(theme_name)

    def load_and_apply_theme(self, app: QApplication, theme_name: str) -> None:
        """Load and apply a theme to the application.

        .. deprecated:: 0.1.0
            Use :meth:`apply_theme` instead. This method is a compatibility
            wrapper that delegates to the new unified apply_theme method.

        Args:
            app: QApplication instance
            theme_name: Name of the theme to load and apply
        """
        import warnings

        warnings.warn(
            "load_and_apply_theme is deprecated, use apply_theme instead",
            DeprecationWarning,
            stacklevel=2,
        )
        # Delegate to new unified method
        self.apply_theme(theme_name, app=app)
