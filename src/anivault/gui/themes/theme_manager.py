"""
Theme Manager for AniVault GUI

This module provides centralized theme management using PySide6 QSS files
to ensure consistent styling across the application.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

from .path_resolver import ThemePathResolver
from .qss_loader import QSSLoader
from .theme_cache import ThemeCache
from .theme_validator import ThemeValidator

logger = logging.getLogger(__name__)


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

        # Initialize QSS loader with all dependencies
        self._qss_loader = QSSLoader(
            validator=self._validator,
            path_resolver=self._path_resolver,
            cache=self._cache,
            logger=logger,
        )

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

    def load_theme_content(self, theme_name: str) -> str:
        """Load QSS content from a theme file with @import resolution.

        Delegates to QSSLoader for actual loading.

        Args:
            theme_name: Name of the theme to load

        Returns:
            QSS content as string with all imports resolved,
            or empty string if theme not found (safe fallback)

        Raises:
            ApplicationError: If theme file read fails (not file-not-found)
        """
        return self._qss_loader.load(theme_name)

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
