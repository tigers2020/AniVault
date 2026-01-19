"""Style Manager for GUI v2."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


class StyleManager:
    """Manages QSS styles for GUI v2."""

    DARK_THEME = "dark"
    LIGHT_THEME = "light"
    DEFAULT_THEME = DARK_THEME

    def __init__(self, theme: str = DARK_THEME) -> None:
        """Initialize style manager.

        Args:
            theme: Theme name ('dark' or 'light'), defaults to 'dark'
        """
        self._theme = theme
        self._styles_dir = Path(__file__).parent

    def apply_styles(self, app: QApplication) -> None:
        """Apply styles to the application.

        Args:
            app: QApplication instance
        """
        styles = self._load_theme(self._theme)
        if styles:
            app.setStyleSheet(styles)
        else:
            # Fallback to default styles
            app.setStyleSheet(self._get_default_styles())

    def _load_theme(self, theme: str) -> str | None:
        """Load theme from file.

        Args:
            theme: Theme name

        Returns:
            Stylesheet content or None if file not found
        """
        if theme == self.DARK_THEME:
            theme_file = self._styles_dir / "dark.qss"
        elif theme == self.LIGHT_THEME:
            theme_file = self._styles_dir / "styles.qss"
        else:
            theme_file = self._styles_dir / "styles.qss"

        if theme_file.exists():
            with open(theme_file, encoding="utf-8") as f:
                return f.read()
        return None

    def set_theme(self, theme: str, app: QApplication) -> None:
        """Change theme and apply to application.

        Args:
            theme: Theme name ('dark' or 'light')
            app: QApplication instance
        """
        self._theme = theme
        self.apply_styles(app)

    def _get_default_styles(self) -> str:
        """Get default inline styles as fallback."""
        return """
        /* Default minimal styles - will be replaced by theme file */
        QMainWindow {
            background-color: #0f172a;
            color: #f8fafc;
        }
        """
