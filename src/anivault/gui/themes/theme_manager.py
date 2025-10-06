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

logger = logging.getLogger(__name__)


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
                      default path in resources/themes/
        """
        if themes_dir is None:
            # Get the package directory and construct themes path
            package_dir = Path(__file__).parent.parent.parent
            self.themes_dir = package_dir / "resources" / "themes"
        else:
            self.themes_dir = Path(themes_dir)

        self.current_theme: str | None = None
        self._ensure_themes_directory()

    def _ensure_themes_directory(self) -> None:
        """Ensure the themes directory exists."""
        try:
            self.themes_dir.mkdir(parents=True, exist_ok=True)
            logger.debug("Themes directory ensured: %s", self.themes_dir)
        except Exception as e:
            logger.exception("Failed to create themes directory: %s", e)
            raise ApplicationError(
                ErrorCode.FILE_OPERATION_ERROR,
                f"Failed to create themes directory: {e}",
                ErrorContext(file_path=str(self.themes_dir)),
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
        except Exception as e:
            logger.exception("Failed to get available themes: %s", e)
            return []

    def get_qss_path(self, theme_name: str) -> Path:
        """Get the path to a theme's QSS file.

        Args:
            theme_name: Name of the theme

        Returns:
            Path to the QSS file

        Raises:
            ApplicationError: If theme file doesn't exist
        """
        qss_path = self.themes_dir / f"{theme_name}.qss"

        if not qss_path.exists():
            logger.error("Theme file not found: %s", qss_path)
            raise ApplicationError(
                ErrorCode.FILE_NOT_FOUND,
                f"Theme file not found: {qss_path}",
                ErrorContext(file_path=str(qss_path)),
            )

        return qss_path

    def load_theme_content(self, theme_name: str) -> str:
        """Load QSS content from a theme file.

        Args:
            theme_name: Name of the theme to load

        Returns:
            QSS content as string

        Raises:
            ApplicationError: If theme file cannot be read
        """
        qss_path = None
        try:
            qss_path = self.get_qss_path(theme_name)

            with open(qss_path, encoding="utf-8") as f:
                content = f.read()

            logger.debug("Loaded theme content for: %s", theme_name)
            return content

        except Exception as e:
            logger.exception("Failed to load theme content for %s: %s", theme_name, e)
            raise ApplicationError(
                ErrorCode.FILE_READ_ERROR,
                f"Failed to load theme content for {theme_name}: {e}",
                ErrorContext(file_path=str(qss_path) if qss_path else f"{theme_name}.qss"),
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
            logger.exception("Failed to apply theme %s: %s", theme_name, e)
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

        Args:
            app: QApplication instance
            theme_name: Name of the theme to load and apply
        """
        try:
            # Load theme content
            qss_content = self.load_theme_content(theme_name)

            # Apply to application
            app.setStyleSheet(qss_content)
            self.current_theme = theme_name

            logger.info("Loaded and applied theme: %s", theme_name)

        except Exception as e:
            logger.exception("Failed to load and apply theme %s: %s", theme_name, e)
            # Fallback to default theme if available
            if theme_name != self.DEFAULT_THEME:
                logger.warning("Falling back to default theme: %s", self.DEFAULT_THEME)
                try:
                    self.load_and_apply_theme(app, self.DEFAULT_THEME)
                except Exception as fallback_error:
                    logger.exception("Failed to apply fallback theme: %s", fallback_error)
                    raise ApplicationError(
                        ErrorCode.APPLICATION_ERROR,
                        f"Failed to apply any theme: {e}",
                    ) from e
            else:
                raise ApplicationError(
                    ErrorCode.APPLICATION_ERROR,
                    f"Failed to apply theme {theme_name}: {e}",
                ) from e
