"""
Theme Manager for AniVault GUI

This module provides centralized theme management using PySide6 QSS files
to ensure consistent styling across the application.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

from anivault.shared.errors import (
    AniVaultError,
    ApplicationError,
    ErrorCode,
    ErrorContextModel,
)

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

    def __init__(
        self,
        themes_dir: Path | None = None,
        validator: ThemeValidator | None = None,
        path_resolver: ThemePathResolver | None = None,
    ) -> None:
        """Initialize ThemeManager with modular components.

        This constructor supports dependency injection for testing and
        uses a factory-like pattern to resolve the circular dependency
        between ThemeValidator and ThemePathResolver.

        Args:
            themes_dir: Optional themes directory (defaults to bundle/dev mode)
            validator: Optional ThemeValidator (for testing/DI)
            path_resolver: Optional ThemePathResolver (for testing/DI)
        """
        # Factory pattern: Create components in dependency order
        # Step 1: Create PathResolver (determines all directories)
        if path_resolver is None:
            # Create minimal validator for PathResolver initialization
            # (PathResolver only needs validator for get_qss_path validation)
            temp_dir = Path.home() / ".anivault" / "themes"
            temp_validator = ThemeValidator(themes_dir=temp_dir, base_theme_dir=temp_dir)
            self._path_resolver = ThemePathResolver(themes_dir, temp_validator)
        else:
            self._path_resolver = path_resolver

        # Step 2: Create proper validator with resolved paths
        if validator is None:
            self._validator = ThemeValidator(
                themes_dir=self._path_resolver.themes_dir,
                base_theme_dir=self._path_resolver.base_theme_dir,
            )
        else:
            self._validator = validator

        # Step 3: Update PathResolver's validator reference
        # Use public setter method to avoid protected member access
        self._path_resolver.set_validator(self._validator)

        # Step 4: Initialize remaining components with dependencies
        self._cache = ThemeCache(self._validator)
        self._qss_loader = QSSLoader(
            validator=self._validator,
            path_resolver=self._path_resolver,
            cache=self._cache,
            logger=logger,
        )

        # Expose paths for backward compatibility
        self.themes_dir = self._path_resolver.themes_dir
        self.base_theme_dir = self._path_resolver.base_theme_dir
        self.user_theme_dir = self._path_resolver.user_theme_dir
        self._is_bundled = self._path_resolver.is_bundled
        self.current_theme: str | None = None

        # Initialize bundle themes if needed
        if self._path_resolver.is_bundled:
            self._path_resolver.ensure_bundle_themes()

    def get_available_themes(self) -> list[str]:
        """Get list of available theme names."""
        return self._path_resolver.get_available_themes()

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
        """Apply theme with 3-level fallback: requested → default → safe mode.

        Args:
            theme_name: Theme to apply
            app: QApplication (None = auto-detect)
            _fallback_attempted: Internal recursion guard

        Raises:
            ApplicationError: If all fallbacks fail
        """
        theme_name = self._validator.validate_theme_name(theme_name)

        # Get QApplication instance
        if app is None:
            instance = QApplication.instance()
            if instance is None:
                raise ApplicationError(
                    ErrorCode.APPLICATION_ERROR,
                    "No QApplication instance found",
                    ErrorContextModel(operation="apply_theme"),
                )
            app = instance

        # Level 1: Try requested theme
        try:
            logger.info("Applying theme: %s", theme_name)
            qss_content = self.load_theme_content(theme_name)
            # app is guaranteed to be QApplication at this point (not None)
            app.setStyleSheet("")
            app.setStyleSheet(qss_content)
            self.current_theme = theme_name
            self._repolish_all_top_levels(app)
            logger.info("Successfully applied theme: %s", theme_name)
            return

        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            original_error = e
            logger.warning("Failed to apply theme %s: %s", theme_name, original_error, exc_info=True)

            # Level 2: Fallback to default
            if not _fallback_attempted and theme_name != self.DEFAULT_THEME:
                logger.warning("Falling back to default theme: %s", self.DEFAULT_THEME)
                try:
                    # pylint: disable-next=redefined-outer-name
                    self.apply_theme(self.DEFAULT_THEME, app, _fallback_attempted=True)
                    return
                except ApplicationError:
                    # ApplicationError from apply_theme already handled
                    logger.exception("Failed to apply fallback theme %s", self.DEFAULT_THEME)
                # pylint: disable-next=broad-exception-caught

                # pylint: disable-next=broad-exception-caught

                except Exception as fallback_error:  # pylint: disable=broad-exception-caught
                    # Unexpected errors during fallback theme application

                    context = ErrorContextModel(
                        operation="apply_fallback_theme",
                        additional_data={"theme": self.DEFAULT_THEME},
                    )
                    error = AniVaultError(
                        ErrorCode.APPLICATION_ERROR,
                        f"Unexpected error applying fallback theme: {fallback_error}",
                        context,
                        original_error=fallback_error,
                    )
                    logger.exception(
                        "Failed to apply fallback theme %s: %s",
                        self.DEFAULT_THEME,
                        error.message,
                    )

            # Level 3: Safe mode
            logger.error("All theme loading failed. Entering safe mode.")
            try:
                if app:
                    app.setStyleSheet("")
                    app.setPalette(app.style().standardPalette())
                    self._repolish_all_top_levels(app)
                self.current_theme = None
                logger.warning("Safe mode activated: using default system styles")
                return
            except Exception as safe_mode_error:  # pylint: disable=broad-exception-caught
                logger.critical("Safe mode failed: %s", safe_mode_error, exc_info=True)

            raise ApplicationError(
                ErrorCode.APPLICATION_ERROR,
                f"Failed to apply theme and all fallbacks: {original_error}",
                ErrorContextModel(
                    operation="apply_theme",
                    additional_data={
                        "requested_theme": theme_name,
                        "fallback_theme": self.DEFAULT_THEME,
                        "safe_mode": True,
                    },
                ),
            ) from original_error

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
