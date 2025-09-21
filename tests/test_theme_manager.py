"""Tests for theme manager functionality."""


import pytest
from PyQt5.QtWidgets import QApplication

from src.themes.dark_theme import DarkTheme
from src.themes.theme_manager import (
    ThemeManager,
    get_color,
    get_log_level_color,
    get_status_color,
    get_theme_manager,
)


class TestThemeManagerSingleton:
    """Test singleton pattern implementation."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Ensure QApplication exists
        if QApplication.instance() is None:
            QApplication([])
        
        # Reset ThemeManager singleton state
        ThemeManager._instance = None
        ThemeManager._initialized = False

    def test_singleton_instance(self) -> None:
        """Test that only one instance is created."""
        manager1 = ThemeManager()
        manager2 = ThemeManager()
        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    def test_global_access_functions(self) -> None:
        """Test global access functions."""
        manager = get_theme_manager()
        assert isinstance(manager, ThemeManager)

        # Test color access
        color = get_color("primary")
        assert color == "#3b82f6"

        # Test log level color
        log_color = get_log_level_color("INFO")
        assert log_color == "#94a3b8"

        # Test status color
        status_color = get_status_color("success")
        assert status_color == "#22c55e"


class TestThemeManagerColors:
    """Test color management functionality."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Ensure QApplication exists
        if QApplication.instance() is None:
            QApplication([])
        
        # Reset ThemeManager singleton state
        ThemeManager._instance = None
        ThemeManager._initialized = False

    def test_get_color(self) -> None:
        """Test getting colors from theme."""
        manager = ThemeManager()

        # Test existing colors
        assert manager.get_color("primary") == "#3b82f6"
        assert manager.get_color("log_info") == "#94a3b8"
        assert manager.get_color("status_success") == "#22c55e"

        # Test non-existing color (should return default)
        assert manager.get_color("non_existing") == "#000000"

    def test_is_theme_available(self) -> None:
        """Test checking if color is available."""
        manager = ThemeManager()

        assert manager.is_theme_available("primary") is True
        assert manager.is_theme_available("log_info") is True
        assert manager.is_theme_available("non_existing") is False

    def test_get_theme_colors(self) -> None:
        """Test getting all theme colors."""
        manager = ThemeManager()
        colors = manager.get_theme_colors()

        assert isinstance(colors, dict)
        assert "primary" in colors
        assert "log_info" in colors
        assert "status_success" in colors
        assert colors["primary"] == "#3b82f6"


class TestThemeManagerCallbacks:
    """Test theme change callback system."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Ensure QApplication exists
        if QApplication.instance() is None:
            QApplication([])
        
        # Reset ThemeManager singleton state
        ThemeManager._instance = None
        ThemeManager._initialized = False

    def test_register_callback(self) -> None:
        """Test registering theme change callbacks."""
        manager = ThemeManager()
        callback_called: list[DarkTheme] = []

        def test_callback(theme: DarkTheme) -> None:
            callback_called.append(theme)

        # Register callback
        manager.register_theme_change_callback(test_callback)
        assert len(manager._theme_change_callbacks) == 1

        # Test callback is called
        manager.switch_theme(DarkTheme)
        assert len(callback_called) == 1
        assert isinstance(callback_called[0], DarkTheme)

    def test_unregister_callback(self) -> None:
        """Test unregistering theme change callbacks."""
        manager = ThemeManager()
        callback_called: list[DarkTheme] = []

        def test_callback(theme: DarkTheme) -> None:
            callback_called.append(theme)

        # Register and then unregister
        manager.register_theme_change_callback(test_callback)
        manager.unregister_theme_change_callback(test_callback)

        # Test callback is not called
        manager.switch_theme(DarkTheme)
        assert len(callback_called) == 0

    def test_multiple_callbacks(self) -> None:
        """Test multiple callbacks are called."""
        manager = ThemeManager()
        callbacks_called: list[str] = []

        def callback1(theme: DarkTheme) -> None:
            callbacks_called.append("callback1")

        def callback2(theme: DarkTheme) -> None:
            callbacks_called.append("callback2")

        # Register multiple callbacks
        manager.register_theme_change_callback(callback1)
        manager.register_theme_change_callback(callback2)

        # Test both callbacks are called
        manager.switch_theme(DarkTheme)
        assert len(callbacks_called) == 2
        assert "callback1" in callbacks_called
        assert "callback2" in callbacks_called


class TestDarkThemeNewColors:
    """Test new color functionality in DarkTheme."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Ensure QApplication exists
        if QApplication.instance() is None:
            QApplication([])
        
        # Reset ThemeManager singleton state
        ThemeManager._instance = None
        ThemeManager._initialized = False

    def test_log_level_colors(self) -> None:
        """Test log level color methods."""
        # Test individual log level colors
        assert DarkTheme.get_log_level_color("INFO") == "#94a3b8"
        assert DarkTheme.get_log_level_color("WARNING") == "#fbbf24"
        assert DarkTheme.get_log_level_color("ERROR") == "#ef4444"
        assert DarkTheme.get_log_level_color("SUCCESS") == "#22c55e"

        # Test case insensitive
        assert DarkTheme.get_log_level_color("info") == "#94a3b8"
        assert DarkTheme.get_log_level_color("error") == "#ef4444"

        # Test unknown level (should return default)
        assert DarkTheme.get_log_level_color("UNKNOWN") == "#94a3b8"

    def test_status_colors(self) -> None:
        """Test status color methods."""
        # Test individual status colors
        assert DarkTheme.get_status_color("success") == "#22c55e"
        assert DarkTheme.get_status_color("warning") == "#eab308"
        assert DarkTheme.get_status_color("error") == "#dc2626"
        assert DarkTheme.get_status_color("completed") == "#22c55e"
        assert DarkTheme.get_status_color("pending") == "#eab308"
        assert DarkTheme.get_status_color("failed") == "#dc2626"

        # Test case insensitive
        assert DarkTheme.get_status_color("SUCCESS") == "#22c55e"
        assert DarkTheme.get_status_color("ERROR") == "#dc2626"

        # Test unknown status (should return default)
        assert DarkTheme.get_status_color("unknown") == "#94a3b8"

    def test_label_text_style(self) -> None:
        """Test label text style generation."""
        style = DarkTheme.get_label_text_style()
        assert "color: #94a3b8" in style
        assert "QLabel" in style


class TestThemeManagerIntegration:
    """Test integration between ThemeManager and DarkTheme."""

    def setup_method(self) -> None:
        """Set up test environment."""
        # Ensure QApplication exists
        if QApplication.instance() is None:
            QApplication([])
        
        # Reset ThemeManager singleton state
        ThemeManager._instance = None
        ThemeManager._initialized = False

    def test_theme_switching(self) -> None:
        """Test theme switching functionality."""
        manager = ThemeManager()
        original_theme = manager.get_current_theme()

        # Switch theme (should create new instance)
        manager.switch_theme(DarkTheme)
        new_theme = manager.get_current_theme()

        # Should be different instances but same class
        assert original_theme is not new_theme
        assert isinstance(new_theme, DarkTheme)
        assert isinstance(original_theme, DarkTheme)

    def test_theme_history(self) -> None:
        """Test theme history tracking."""
        manager = ThemeManager()
        initial_history_length = len(manager._theme_history)

        # Switch theme
        manager.switch_theme(DarkTheme)
        assert len(manager._theme_history) == initial_history_length + 1

        # Switch again
        manager.switch_theme(DarkTheme)
        assert len(manager._theme_history) == initial_history_length + 2


if __name__ == "__main__":
    pytest.main([__file__])
