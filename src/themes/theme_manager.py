"""Theme manager for handling theme switching and application."""

from typing import Optional

from .dark_theme import DarkTheme


class ThemeManager:
    """Manages theme application and switching."""

    def __init__(self) -> None:
        """Initialize theme manager."""
        self.current_theme = DarkTheme()
        self._theme_history = []

    def apply_theme(self, widget, theme: Optional[DarkTheme] = None) -> None:
        """Apply theme to a widget and its children."""
        if theme is None:
            theme = self.current_theme

        # Apply main window theme
        if hasattr(widget, 'setStyleSheet'):
            widget.setStyleSheet(theme.get_complete_style())

        # Recursively apply to children
        for child in widget.findChildren(object):
            if hasattr(child, 'setStyleSheet'):
                self._apply_widget_theme(child, theme)

    def _apply_widget_theme(self, widget, theme: DarkTheme) -> None:
        """Apply specific theme to a widget based on its type."""
        widget_name = widget.__class__.__name__
        
        if widget_name == "QGroupBox":
            widget.setStyleSheet(theme.get_group_box_style())
        elif widget_name == "QLineEdit":
            widget.setStyleSheet(theme.get_line_edit_style())
        elif widget_name == "QTableWidget":
            widget.setStyleSheet(theme.get_table_style())
        elif widget_name == "QTextEdit":
            widget.setStyleSheet(theme.get_text_edit_style())
        elif widget_name == "QScrollArea":
            widget.setStyleSheet(theme.get_scroll_area_style())
        elif widget_name == "QPushButton":
            # Try to determine button type from object name or properties
            button_type = getattr(widget, 'button_type', 'default')
            widget.setStyleSheet(theme.get_button_style(button_type))
        elif widget_name == "QFrame":
            frame_type = getattr(widget, 'frame_type', 'default')
            widget.setStyleSheet(theme.get_frame_style(frame_type))
        elif widget_name == "QLabel":
            label_type = getattr(widget, 'label_type', 'default')
            widget.setStyleSheet(theme.get_label_style(label_type))

    def switch_theme(self, theme_class) -> None:
        """Switch to a different theme."""
        self._theme_history.append(self.current_theme)
        self.current_theme = theme_class()

    def get_current_theme(self) -> DarkTheme:
        """Get the current theme."""
        return self.current_theme

    def get_color(self, color_name: str) -> str:
        """Get a color from the current theme."""
        return self.current_theme.get_color(color_name)
