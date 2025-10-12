"""
Tests for ThemeManager

This module contains tests for the ThemeManager class to ensure
proper theme loading and application functionality.
"""

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

        assert exc_info.value.code == ErrorCode.FILE_READ_ERROR

    def test_load_theme_content_read_error(self):
        """Test loading theme content with read error."""
        # Create a file that will cause read error
        qss_path = self.test_themes_dir / "light.qss"
        qss_path.write_text("test")

        with patch("builtins.open", side_effect=IOError("Read error")):
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

    def test_theme_constants(self):
        """Test theme constants are properly defined."""
        assert ThemeManager.LIGHT_THEME == "light"
        assert ThemeManager.DARK_THEME == "dark"
        assert ThemeManager.DEFAULT_THEME == "light"


class TestThemeManagerQSSImport:
    """Test cases for QSS @import functionality (Task 2.5)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_themes_dir = Path("test_themes_import")
        self.theme_manager = ThemeManager(self.test_themes_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_themes_dir.exists():
            import shutil

            shutil.rmtree(self.test_themes_dir)

    def test_import_directive_normal(self):
        """Test normal @import resolution."""
        # Create common.qss
        common_content = """/* Common styles */
QWidget { font-family: Arial; }"""
        (self.test_themes_dir / "common.qss").write_text(common_content)

        # Create light.qss with @import
        light_content = """/* Light theme */
@import url("common.qss");
QMainWindow { background: white; }"""
        (self.test_themes_dir / "light.qss").write_text(light_content)

        # Load theme
        content = self.theme_manager.load_theme_content("light")

        # Verify @import was resolved
        assert "font-family: Arial" in content
        assert "background: white" in content
        assert "@import" not in content  # Import directive should be replaced

    def test_import_circular_detection(self):
        """Test circular import detection."""
        # Create a.qss importing b.qss
        (self.test_themes_dir / "a.qss").write_text(
            '@import url("b.qss");\nQWidget { color: red; }'
        )

        # Create b.qss importing a.qss (circular!)
        (self.test_themes_dir / "b.qss").write_text(
            '@import url("a.qss");\nQWidget { color: blue; }'
        )

        # Should raise error
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.load_theme_content("a")

        # Error is wrapped in FILE_READ_ERROR, check message
        assert "Circular" in str(exc_info.value)

    def test_import_path_traversal(self):
        """Test path traversal attack prevention."""
        # Create malicious theme trying to import outside themes dir
        malicious_content = """/* Malicious theme */
@import url("../../etc/passwd");
QWidget { color: red; }"""
        (self.test_themes_dir / "malicious.qss").write_text(malicious_content)

        # Should raise security error
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.load_theme_content("malicious")

        # Error is wrapped in FILE_READ_ERROR, check message
        assert "outside" in str(exc_info.value).lower()

    def test_import_max_depth(self):
        """Test maximum import depth limit."""
        # Create chain of imports exceeding MAX_IMPORT_DEPTH
        for i in range(15):
            if i == 14:
                content = "QWidget { color: red; }"
            else:
                content = f'@import url("level{i + 1}.qss");\nQWidget {{ color: red; }}'
            (self.test_themes_dir / f"level{i}.qss").write_text(content)

        # Should raise error (MAX_IMPORT_DEPTH = 10)
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.load_theme_content("level0")

        # Error is wrapped in FILE_READ_ERROR, check message
        assert "depth" in str(exc_info.value).lower()

    def test_import_file_not_found(self):
        """Test missing import file."""
        # Create theme with non-existent import
        (self.test_themes_dir / "broken.qss").write_text(
            '@import url("nonexistent.qss");'
        )

        # Should raise error
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.load_theme_content("broken")

        # Error is wrapped in FILE_READ_ERROR, check message
        assert "not found" in str(exc_info.value).lower()


class TestThemeManagerInputValidation:
    """Test cases for theme name input validation (Task 2.6)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_themes_dir = Path("test_themes_validation")
        self.theme_manager = ThemeManager(self.test_themes_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_themes_dir.exists():
            import shutil

            shutil.rmtree(self.test_themes_dir)

    def test_validate_theme_name_valid(self):
        """Test valid theme names."""
        valid_names = ["light", "dark", "custom", "my-theme", "my_theme", "theme123"]

        for name in valid_names:
            # Should not raise
            validated = self.theme_manager._validate_theme_name(name)
            assert validated == name, f"Failed for name: {name}"

    def test_validate_theme_name_empty(self):
        """Test empty theme name."""
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager._validate_theme_name("")

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "empty" in str(exc_info.value).lower()

    def test_validate_theme_name_too_long(self):
        """Test theme name exceeding length limit."""
        long_name = "a" * 51  # MAX = 50

        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager._validate_theme_name(long_name)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "too long" in str(exc_info.value).lower()

    def test_validate_theme_name_path_separators(self):
        """Test theme name with path separators."""
        invalid_names = ["../theme", "theme/name", "theme\\name", ".."]

        for name in invalid_names:
            with pytest.raises(ApplicationError, match="VALIDATION_ERROR") as exc_info:
                self.theme_manager._validate_theme_name(name)

            assert (
                exc_info.value.code == ErrorCode.VALIDATION_ERROR
            ), f"Failed for name: {name}"
            assert (
                "path" in str(exc_info.value).lower()
                or "separator" in str(exc_info.value).lower()
            ), f"Failed for name: {name}"

    def test_validate_theme_name_special_characters(self):
        """Test theme name with invalid special characters."""
        invalid_names = [
            "theme!",
            "theme@home",
            "theme#1",
            "theme$",
            "theme%",
            "theme&",
        ]

        for name in invalid_names:
            with pytest.raises(ApplicationError, match="VALIDATION_ERROR") as exc_info:
                self.theme_manager._validate_theme_name(name)

            assert (
                exc_info.value.code == ErrorCode.VALIDATION_ERROR
            ), f"Failed for name: {name}"

    def test_get_qss_path_with_invalid_name(self):
        """Test get_qss_path with invalid theme name."""
        # Path traversal attempt
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.get_qss_path("../../../etc/passwd")

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


class TestThemeManagerFallback:
    """Test cases for theme fallback logic (Task 4.2)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_themes_dir = Path("test_themes_fallback")
        self.theme_manager = ThemeManager(self.test_themes_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_themes_dir.exists():
            import shutil

            shutil.rmtree(self.test_themes_dir)

    @patch("anivault.gui.themes.theme_manager.QApplication.instance")
    def test_fallback_to_default_theme(self, mock_app_instance):
        """Test fallback to default theme on failure."""
        # Create light.qss (default) but not dark.qss
        (self.test_themes_dir / "light.qss").write_text("QWidget { color: white; }")

        # Setup mock app
        mock_app = Mock()
        mock_app_instance.return_value = mock_app
        mock_app.topLevelWidgets.return_value = []

        # Try to apply non-existent dark theme
        # Should fallback to light
        self.theme_manager.apply_theme("dark")

        # Verify fallback to light theme
        assert self.theme_manager.current_theme == "light"

    @patch("anivault.gui.themes.theme_manager.QApplication.instance")
    def test_safe_mode_when_all_fail(self, mock_app_instance):
        """Test safe mode when all themes fail."""
        # No theme files exist
        mock_app = Mock()
        mock_app_instance.return_value = mock_app
        mock_app.topLevelWidgets.return_value = []

        # Try to apply theme - should enter safe mode
        self.theme_manager.apply_theme("dark")

        # Verify safe mode (empty stylesheet, no theme)
        assert self.theme_manager.current_theme is None
        mock_app.setStyleSheet.assert_called_with("")

    @patch("anivault.gui.themes.theme_manager.QApplication.instance")
    def test_no_recursion_when_default_fails(self, mock_app_instance):
        """Test no infinite recursion when default theme fails."""
        # No theme files exist
        mock_app = Mock()
        mock_app_instance.return_value = mock_app
        mock_app.topLevelWidgets.return_value = []

        # Try to apply default theme directly - should go to safe mode
        self.theme_manager.apply_theme("light")

        # Should not raise error, enter safe mode
        assert self.theme_manager.current_theme is None

    @patch("anivault.gui.themes.theme_manager.QApplication.instance")
    def test_app_parameter_override(self, mock_app_instance):
        """Test QApplication parameter override."""
        # Create test theme
        (self.test_themes_dir / "light.qss").write_text("QWidget { color: white; }")

        # Setup mocks
        mock_app_global = Mock()
        mock_app_param = Mock()
        mock_app_instance.return_value = mock_app_global
        mock_app_param.topLevelWidgets.return_value = []

        # Pass app parameter - should use it instead of instance()
        self.theme_manager.apply_theme("light", app=mock_app_param)

        # Verify parameter app was used
        mock_app_param.setStyleSheet.assert_called()
        mock_app_global.setStyleSheet.assert_not_called()

    @patch("anivault.gui.themes.theme_manager.QApplication.instance")
    def test_validation_before_fallback(self, mock_app_instance):
        """Test theme name validation happens before fallback."""
        mock_app = Mock()
        mock_app_instance.return_value = mock_app

        # Invalid theme name should raise immediately (no fallback)
        with pytest.raises(ApplicationError, match="VALIDATION_ERROR"):
            self.theme_manager.apply_theme("../../../etc/passwd")

    @patch("anivault.gui.themes.theme_manager.QApplication.instance")
    def test_no_app_instance(self, mock_app_instance):
        """Test error when no QApplication instance available."""
        mock_app_instance.return_value = None

        # Should raise error
        with pytest.raises(ApplicationError) as exc_info:
            self.theme_manager.apply_theme("light")

        assert exc_info.value.code == ErrorCode.APPLICATION_ERROR
        assert "QApplication" in str(exc_info.value)


class TestThemeManagerCache:
    """Test cases for theme caching (Task 3.1)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_themes_dir = Path("test_themes_cache")
        self.theme_manager = ThemeManager(self.test_themes_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_themes_dir.exists():
            import shutil

            shutil.rmtree(self.test_themes_dir)

    def test_cache_hit_on_repeated_load(self):
        """Test that cache is used on repeated theme loads."""
        # Create test theme
        theme_content = "QWidget { color: white; }"
        theme_path = self.test_themes_dir / "light.qss"
        theme_path.write_text(theme_content)

        # Load theme first time
        content1 = self.theme_manager.load_theme_content("light")
        assert content1 == theme_content

        # Modify file content (but keep same path)
        # Cache should still return old content if mtime unchanged
        import time

        time.sleep(0.01)  # Ensure different mtime
        theme_path.write_text("QWidget { color: black; }")

        # Load again - should get NEW content (mtime changed)
        content2 = self.theme_manager.load_theme_content("light")
        assert content2 == "QWidget { color: black; }"

    def test_cache_stores_mtime(self):
        """Test that cache stores mtime correctly."""
        # Create test theme
        theme_path = self.test_themes_dir / "light.qss"
        theme_path.write_text("QWidget { color: white; }")

        # Load theme
        self.theme_manager.load_theme_content("light")

        # Check cache structure
        assert theme_path in self.theme_manager._qss_cache
        mtime, content = self.theme_manager._qss_cache[theme_path]
        assert isinstance(mtime, int)
        assert mtime > 0
        assert content == "QWidget { color: white; }"

    def test_cache_with_imports(self):
        """Test that cache works with @import directives."""
        # Create common.qss
        (self.test_themes_dir / "common.qss").write_text("QLabel { color: gray; }")

        # Create light.qss with import
        (self.test_themes_dir / "light.qss").write_text(
            '@import url("common.qss");\nQWidget { background: white; }'
        )

        # Load theme first time
        content1 = self.theme_manager.load_theme_content("light")
        assert "QLabel { color: gray; }" in content1
        assert "QWidget { background: white; }" in content1

        # Verify cache hit on second load
        content2 = self.theme_manager.load_theme_content("light")
        assert content2 == content1

    def test_cache_invalidation_on_file_change(self):
        """Test that cache is invalidated when file is modified."""
        # Create test theme
        theme_path = self.test_themes_dir / "light.qss"
        theme_path.write_text("QWidget { color: white; }")

        # Load theme
        content1 = self.theme_manager.load_theme_content("light")

        # Wait to ensure different mtime
        import time

        time.sleep(0.01)

        # Modify file
        theme_path.write_text("QWidget { color: black; }")

        # Load again - should get new content
        content2 = self.theme_manager.load_theme_content("light")
        assert content2 == "QWidget { color: black; }"
        assert content2 != content1
