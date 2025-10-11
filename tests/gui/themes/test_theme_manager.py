"""
Tests for ThemeManager

This module contains tests for the ThemeManager class to ensure
proper theme loading and application functionality.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from anivault.gui.themes import ThemeManager
from anivault.shared.errors import ApplicationError, ErrorCode


class TestThemeManager:
    """Test cases for ThemeManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_themes_dir = Path("test_themes")
        self.theme_manager = ThemeManager(self.test_themes_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up test directory if it exists
        if self.test_themes_dir.exists():
            import shutil

            shutil.rmtree(self.test_themes_dir)

    def test_init_default_themes_dir(self):
        """Test ThemeManager initialization with default themes directory."""
        theme_manager = ThemeManager()
        assert theme_manager.themes_dir is not None
        assert theme_manager.current_theme is None

    def test_init_custom_themes_dir(self):
        """Test ThemeManager initialization with custom themes directory."""
        custom_dir = Path("custom_themes")
        theme_manager = ThemeManager(custom_dir)
        assert theme_manager.themes_dir == custom_dir
        assert theme_manager.current_theme is None

    def test_ensure_themes_directory_creation(self):
        """Test that themes directory is created if it doesn't exist."""
        # Directory should be created during initialization
        assert self.test_themes_dir.exists()

    def test_get_available_themes_empty(self):
        """Test getting available themes when directory is empty."""
        themes = self.theme_manager.get_available_themes()
        assert themes == []

    def test_get_available_themes_with_files(self):
        """Test getting available themes when QSS files exist."""
        # Create test QSS files
        (self.test_themes_dir / "light.qss").write_text("/* Light theme */")
        (self.test_themes_dir / "dark.qss").write_text("/* Dark theme */")
        (self.test_themes_dir / "not_a_theme.txt").write_text("Not a theme")

        themes = self.theme_manager.get_available_themes()
        assert "light" in themes
        assert "dark" in themes
        assert len(themes) == 2

    def test_get_qss_path_existing(self):
        """Test getting QSS path for existing theme."""
        # Create test QSS file
        (self.test_themes_dir / "light.qss").write_text("/* Light theme */")

        qss_path = self.theme_manager.get_qss_path("light")
        assert qss_path == self.test_themes_dir / "light.qss"
        assert qss_path.exists()

    def test_get_qss_path_nonexistent(self):
        """Test getting QSS path for non-existent theme raises error."""
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.get_qss_path("nonexistent")

        assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND
        assert "Theme file not found" in str(exc_info.value)

    def test_load_theme_content_success(self):
        """Test loading theme content successfully."""
        # Create test QSS file
        test_content = "/* Test theme content */\nQMainWindow { background: white; }"
        (self.test_themes_dir / "light.qss").write_text(test_content)

        content = self.theme_manager.load_theme_content("light")
        assert content == test_content

    def test_load_theme_content_file_not_found(self):
        """Test loading theme content for non-existent file raises error."""
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.load_theme_content("nonexistent")

        assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND

    def test_load_theme_content_read_error(self):
        """Test loading theme content with read error."""
        # Create a file that will cause read error
        qss_path = self.test_themes_dir / "light.qss"
        qss_path.write_text("test")

        # Mock _read_file_with_imports to simulate IOError
        with patch.object(
            self.theme_manager,
            "_read_file_with_imports",
            side_effect=IOError("Read error"),
        ):
            with pytest.raises(ApplicationError) as exc_info:
                self.theme_manager.load_theme_content("light")

            assert exc_info.value.code == ErrorCode.FILE_READ_ERROR

    @patch("PySide6.QtWidgets.QApplication.instance")
    def test_apply_theme_success(self, mock_app_instance):
        """Test applying theme successfully."""
        # Setup mock
        mock_app = Mock()
        mock_app.topLevelWidgets.return_value = []  # Return empty list for iteration
        mock_app_instance.return_value = mock_app

        # Create test QSS file
        test_content = "QMainWindow { background: white; }"
        (self.test_themes_dir / "light.qss").write_text(test_content)

        # Apply theme
        self.theme_manager.apply_theme("light")

        # Verify (setStyleSheet may be called multiple times for widget repolishing)
        mock_app.setStyleSheet.assert_called_with(test_content)
        assert self.theme_manager.current_theme == "light"

    @patch("PySide6.QtWidgets.QApplication.instance")
    def test_apply_theme_no_app(self, mock_app_instance):
        """Test applying theme when no QApplication instance exists."""
        mock_app_instance.return_value = None

        # Create test QSS file first
        (self.test_themes_dir / "light.qss").write_text(
            "QMainWindow { background: white; }"
        )

        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.apply_theme("light")

        assert exc_info.value.code == ErrorCode.APPLICATION_ERROR
        assert "No QApplication instance found" in str(exc_info.value)

    @patch("PySide6.QtWidgets.QApplication.instance")
    def test_apply_theme_file_error(self, mock_app_instance):
        """Test applying theme when file cannot be loaded."""
        mock_app = Mock()
        mock_app_instance.return_value = mock_app

        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.apply_theme("nonexistent")

        assert exc_info.value.code == ErrorCode.APPLICATION_ERROR

    def test_get_current_theme(self):
        """Test getting current theme."""
        # Initially no theme
        assert self.theme_manager.get_current_theme() is None

        # Set current theme
        self.theme_manager.current_theme = "light"
        assert self.theme_manager.get_current_theme() == "light"

    @patch("PySide6.QtWidgets.QApplication.instance")
    def test_load_and_apply_theme_success(self, mock_app_instance):
        """Test load and apply theme successfully (deprecated method)."""
        # Setup mock
        mock_app = Mock()
        mock_style = Mock()
        mock_style.standardPalette.return_value = Mock()
        mock_app.style.return_value = mock_style
        mock_app.topLevelWidgets.return_value = []
        mock_app_instance.return_value = mock_app

        # Create test QSS file
        test_content = "QMainWindow { background: white; }"
        (self.test_themes_dir / "light.qss").write_text(test_content)

        # Load and apply theme (deprecated method delegates to apply_theme)
        self.theme_manager.load_and_apply_theme(mock_app, "light")

        # Verify theme was applied via apply_theme
        assert self.theme_manager.current_theme == "light"
        assert mock_app.setStyleSheet.call_count >= 2  # Reset + Apply

    @patch("PySide6.QtWidgets.QApplication.instance")
    def test_load_and_apply_theme_fallback(self, mock_app_instance):
        """Test load and apply theme with fallback to default (deprecated method)."""
        # Setup mock
        mock_app = Mock()
        mock_style = Mock()
        mock_style.standardPalette.return_value = Mock()
        mock_app.style.return_value = mock_style
        mock_app.topLevelWidgets.return_value = []
        mock_app_instance.return_value = mock_app

        # Create default theme file
        default_content = "QMainWindow { background: white; }"
        (self.test_themes_dir / "light.qss").write_text(default_content)

        # Try to load non-existent theme, should fallback to default via apply_theme
        self.theme_manager.load_and_apply_theme(mock_app, "nonexistent")

        # Should have applied default theme
        assert self.theme_manager.current_theme == "light"

    @patch("PySide6.QtWidgets.QApplication.instance")
    def test_load_and_apply_theme_no_fallback(self, mock_app_instance):
        """Test load and apply theme when fallback also fails (deprecated method)."""
        # Setup mock
        mock_app = Mock()
        mock_style = Mock()
        mock_style.standardPalette.return_value = Mock()
        mock_app.style.return_value = mock_style
        mock_app.topLevelWidgets.return_value = []
        mock_app_instance.return_value = mock_app

        # Try to load non-existent theme with no fallback available
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.load_and_apply_theme(mock_app, "nonexistent")

        assert exc_info.value.code == ErrorCode.APPLICATION_ERROR
        assert "Failed to apply any theme" in str(exc_info.value)

    def test_theme_constants(self):
        """Test theme constants are properly defined."""
        assert ThemeManager.LIGHT_THEME == "light"
        assert ThemeManager.DARK_THEME == "dark"
        assert ThemeManager.DEFAULT_THEME == "light"


class TestThemeManagerPyInstallerBundle:
    """Test cases for ThemeManager in PyInstaller bundle environment."""

    def test_bundle_mode_detection(self, tmp_path):
        """Test bundle mode detection via sys._MEIPASS."""
        # Setup: Simulate PyInstaller bundle
        bundle_dir = tmp_path / "bundle"
        bundle_dir.mkdir()

        # Patch sys._MEIPASS
        with patch.object(sys, "_MEIPASS", str(bundle_dir), create=True):
            # Verify _is_bundle() detects bundle mode
            theme_manager = ThemeManager()
            assert theme_manager._is_bundle()

    def test_bundle_mode_paths(self, tmp_path):
        """Test path resolution in PyInstaller bundle mode."""
        # Setup: Simulate bundle environment
        bundle_dir = tmp_path / "bundle"
        bundle_dir.mkdir()
        (bundle_dir / "anivault" / "resources" / "themes").mkdir(parents=True)

        # Patch sys._MEIPASS
        with patch.object(sys, "_MEIPASS", str(bundle_dir), create=True):
            # Create theme manager
            theme_manager = ThemeManager()

            # Verify paths
            assert "AniVault" in str(theme_manager.user_theme_dir)
            assert str(bundle_dir) in str(theme_manager.base_theme_dir)

    def test_readonly_bundle_directory(self, tmp_path):
        """Test that bundle directory is not written to in bundle mode."""
        # Setup: Simulate read-only bundle
        bundle_dir = tmp_path / "bundle"
        bundle_dir.mkdir()
        (bundle_dir / "anivault" / "resources" / "themes").mkdir(parents=True)
        bundle_dir.chmod(0o444)  # Read-only

        # Patch sys._MEIPASS
        with patch.object(sys, "_MEIPASS", str(bundle_dir), create=True):
            # Should create user_theme_dir without error
            theme_manager = ThemeManager()

            # Verify user directory exists (not bundle directory)
            assert theme_manager.user_theme_dir.exists()

    @pytest.mark.parametrize(
        "platform,expected_substring",
        [
            ("win32", "AppData"),
            ("darwin", "Library"),
            ("linux", ".local"),
        ],
    )
    def test_user_theme_dir_by_platform(
        self, monkeypatch, platform, expected_substring
    ):
        """Test OS-specific user theme directory resolution."""
        # Setup: Mock platform
        monkeypatch.setattr(sys, "platform", platform)

        if platform == "win32":
            monkeypatch.setenv("APPDATA", "C:\\Users\\Test\\AppData\\Roaming")

        # Create theme manager
        theme_manager = ThemeManager()

        # Verify OS-specific path
        user_dir_str = str(theme_manager._get_user_theme_dir())
        assert expected_substring in user_dir_str
        assert "AniVault" in user_dir_str
        assert "themes" in user_dir_str


class TestThemeManagerSecurity:
    """Test cases for ThemeManager security features."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_themes_dir = Path("test_themes_security")
        self.theme_manager = ThemeManager(self.test_themes_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_themes_dir.exists():
            import shutil

            shutil.rmtree(self.test_themes_dir)

    @pytest.mark.parametrize(
        "malicious_theme_name",
        [
            "../etc/passwd",
            "..\\Windows\\System32\\config\\SAM",
            "../../sensitive_data",
            "theme/../../../etc/shadow",
            "theme/../../Windows/System32",
        ],
    )
    def test_path_traversal_prevention(self, malicious_theme_name):
        """Test path traversal attack prevention."""
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.get_qss_path(malicious_theme_name)

        assert exc_info.value.code == ErrorCode.SECURITY_VIOLATION
        assert "Invalid theme name" in str(exc_info.value)

    @pytest.mark.parametrize(
        "invalid_theme_name",
        [
            "theme/subdir",
            "theme\\subdir",
            "theme/../other",
        ],
    )
    def test_directory_separator_rejection(self, invalid_theme_name):
        """Test rejection of theme names with directory separators."""
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.get_qss_path(invalid_theme_name)

        assert exc_info.value.code == ErrorCode.SECURITY_VIOLATION


class TestThemeManagerUserThemePriority:
    """Test cases for user theme prioritization over bundled themes."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_themes_dir = Path("test_themes_priority")
        self.test_themes_dir.mkdir(exist_ok=True)
        self.user_themes_dir = Path("test_user_themes")
        self.user_themes_dir.mkdir(exist_ok=True)

        # Create theme manager with explicit paths for testing
        self.theme_manager = ThemeManager(self.test_themes_dir)
        # Manually override user_theme_dir for testing
        self.theme_manager.user_theme_dir = self.user_themes_dir

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.test_themes_dir.exists():
            shutil.rmtree(self.test_themes_dir)
        if self.user_themes_dir.exists():
            shutil.rmtree(self.user_themes_dir)

    def test_user_theme_priority_over_bundled(self):
        """Test that user themes take priority over bundled themes."""
        # Create bundled theme
        bundled_theme = self.test_themes_dir / "light.qss"
        bundled_theme.write_text("/* Bundled theme */")

        # Create user theme with same name
        user_theme = self.user_themes_dir / "light.qss"
        user_theme.write_text("/* User custom theme */")

        # Get QSS path
        qss_path = self.theme_manager.get_qss_path("light")

        # Should return user theme
        assert qss_path == user_theme
        assert "User custom theme" in qss_path.read_text()

    def test_fallback_to_bundled_theme(self):
        """Test fallback to bundled theme when user theme doesn't exist."""
        # Create only bundled theme
        bundled_theme = self.test_themes_dir / "dark.qss"
        bundled_theme.write_text("/* Bundled dark theme */")

        # Get QSS path
        qss_path = self.theme_manager.get_qss_path("dark")

        # Should return bundled theme
        assert qss_path == bundled_theme
        assert "Bundled dark theme" in qss_path.read_text()

    def test_theme_not_found_in_either_location(self):
        """Test error when theme not found in both locations."""
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.get_qss_path("nonexistent")

        assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND
        assert "Theme file not found" in str(exc_info.value)


class TestThemeManagerDirectoryCreation:
    """Test cases for theme directory creation logic."""

    def test_directory_creation_failure(self, monkeypatch, tmp_path):
        """Test directory creation failure handling."""

        # Setup: Mock mkdir to fail
        def mock_mkdir_failure(*args, **kwargs):
            raise OSError("Permission denied")

        # Create theme manager with invalid path
        invalid_path = tmp_path / "invalid"

        # Patch Path.mkdir to fail
        with patch("pathlib.Path.mkdir", side_effect=mock_mkdir_failure):
            with pytest.raises(ApplicationError) as exc_info:
                ThemeManager(invalid_path)

            assert exc_info.value.code == ErrorCode.DIRECTORY_CREATION_FAILED
            assert "Failed to create themes directory" in str(exc_info.value)
