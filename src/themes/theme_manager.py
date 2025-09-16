"""Theme manager for handling theme switching and application."""

from typing import Optional, Callable, List
from PyQt5.QtCore import QObject, pyqtSignal

from .dark_theme import DarkTheme


class ThemeManager(QObject):
    """Manages theme application and switching with singleton pattern."""
    
    # Signal emitted when theme changes
    theme_changed = pyqtSignal(object)
    
    _instance = None
    _initialized = False

    def __new__(cls) -> 'ThemeManager':
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize theme manager (only once)."""
        if not self._initialized:
            super().__init__()
            self.current_theme = DarkTheme()
            self._theme_history = []
            self._theme_change_callbacks: List[Callable] = []
            self._initialized = True

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
        
        # Notify all registered callbacks
        self._notify_theme_change()
        
        # Emit signal for Qt-based components
        self.theme_changed.emit(self.current_theme)

    def get_current_theme(self) -> DarkTheme:
        """Get the current theme."""
        return self.current_theme

    def get_color(self, color_name: str) -> str:
        """Get a color from the current theme."""
        return self.current_theme.get_color(color_name)
    
    def register_theme_change_callback(self, callback: Callable) -> None:
        """Register a callback to be called when theme changes."""
        if callback not in self._theme_change_callbacks:
            self._theme_change_callbacks.append(callback)
    
    def unregister_theme_change_callback(self, callback: Callable) -> None:
        """Unregister a theme change callback."""
        if callback in self._theme_change_callbacks:
            self._theme_change_callbacks.remove(callback)
    
    def _notify_theme_change(self) -> None:
        """Notify all registered callbacks about theme change."""
        for callback in self._theme_change_callbacks:
            try:
                callback(self.current_theme)
            except Exception as e:
                print(f"Error in theme change callback: {e}")
    
    def get_theme_colors(self) -> dict:
        """Get all available colors from current theme."""
        return self.current_theme.COLORS
    
    def is_theme_available(self, color_name: str) -> bool:
        """Check if a color is available in current theme."""
        return color_name in self.current_theme.COLORS


# Global instance access
def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    return ThemeManager()


def get_color(color_name: str) -> str:
    """Get a color from the global theme manager."""
    return get_theme_manager().get_color(color_name)


def get_log_level_color(level: str) -> str:
    """Get log level color from the global theme manager."""
    return get_theme_manager().current_theme.get_log_level_color(level)


def get_status_color(status: str) -> str:
    """Get status color from the global theme manager."""
    return get_theme_manager().current_theme.get_status_color(status)
