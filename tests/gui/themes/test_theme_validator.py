"""Tests for ThemeValidator class.

Tests validation logic for theme names and QSS import paths,
ensuring security and compatibility with PyInstaller bundle mode.
"""

from pathlib import Path

import pytest

from anivault.gui.themes.theme_validator import ThemeValidator
from anivault.shared.errors import ApplicationError, ErrorCode


class TestThemeValidator:
    """Test ThemeValidator input validation."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.test_themes_dir = Path("test_themes")
        self.test_base_dir = Path("test_base_themes")
        self.validator = ThemeValidator(
            themes_dir=self.test_themes_dir,
            base_theme_dir=self.test_base_dir,
        )

    def test_init_stores_directories(self) -> None:
        """Test validator stores theme directories."""
        assert self.validator.themes_dir == self.test_themes_dir
        assert self.validator.base_theme_dir == self.test_base_dir

    # Theme name validation tests
    def test_validate_theme_name_valid(self) -> None:
        """Test validation passes for valid theme names."""
        valid_names = [
            "light",
            "dark",
            "custom-theme",
            "my_theme_1",
            "Theme123",
        ]
        for name in valid_names:
            result = self.validator.validate_theme_name(name)
            assert result == name

    def test_validate_theme_name_empty(self) -> None:
        """Test validation rejects empty theme name."""
        with pytest.raises(ApplicationError) as exc_info:
            self.validator.validate_theme_name("")

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "cannot be empty" in exc_info.value.message

    def test_validate_theme_name_too_long(self) -> None:
        """Test validation rejects theme names over 50 characters."""
        long_name = "a" * 51
        with pytest.raises(ApplicationError) as exc_info:
            self.validator.validate_theme_name(long_name)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "too long" in exc_info.value.message

    def test_validate_theme_name_path_separators(self) -> None:
        """Test validation rejects theme names with path separators."""
        invalid_names = [
            "../etc/passwd",
            "theme/file",
            "theme\\file",
            "..theme",
            "theme..",
        ]
        for name in invalid_names:
            with pytest.raises(ApplicationError) as exc_info:
                self.validator.validate_theme_name(name)

            assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
            assert "path separators" in exc_info.value.message

    def test_validate_theme_name_invalid_characters(self) -> None:
        """Test validation rejects theme names with invalid characters."""
        invalid_names = [
            "theme@name",
            "theme#name",
            "theme$name",
            "theme name",
            "theme!",
        ]
        for name in invalid_names:
            with pytest.raises(ApplicationError) as exc_info:
                self.validator.validate_theme_name(name)

            assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
            assert "alphanumeric" in exc_info.value.message


class TestThemeValidatorImportPath:
    """Test ThemeValidator import path validation."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create temporary directories
        self.test_dir = Path("test_validator")
        self.themes_dir = self.test_dir / "themes"
        self.base_dir = self.test_dir / "base"

        self.themes_dir.mkdir(parents=True, exist_ok=True)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Create test files
        self.user_qss = self.themes_dir / "user.qss"
        self.user_qss.write_text("/* user theme */", encoding="utf-8")

        self.bundle_qss = self.base_dir / "common.qss"
        self.bundle_qss.write_text("/* bundle theme */", encoding="utf-8")

        self.validator = ThemeValidator(
            themes_dir=self.themes_dir,
            base_theme_dir=self.base_dir,
        )

    def teardown_method(self) -> None:
        """Clean up test files."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_validate_import_path_themes_dir(self) -> None:
        """Test validation allows paths within themes_dir."""
        result = self.validator.validate_import_path(self.user_qss)
        assert result == self.user_qss.resolve()

    def test_validate_import_path_base_theme_dir(self) -> None:
        """Test validation allows paths within base_theme_dir (CRITICAL BUG FIX)."""
        # This is the bug fix test - bundle themes can import common.qss
        result = self.validator.validate_import_path(self.bundle_qss)
        assert result == self.bundle_qss.resolve()

    def test_validate_import_path_outside_both(self) -> None:
        """Test validation rejects paths outside both directories."""
        outside_path = self.test_dir / "outside.qss"
        outside_path.write_text("/* outside */", encoding="utf-8")

        with pytest.raises(ApplicationError) as exc_info:
            self.validator.validate_import_path(outside_path)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "outside allowed directories" in exc_info.value.message
        assert "themes_dir" in exc_info.value.context.additional_data
        assert "base_theme_dir" in exc_info.value.context.additional_data

    def test_validate_import_path_traversal_attack(self) -> None:
        """Test validation blocks path traversal attacks."""
        # Try to access parent directory
        attack_path = self.themes_dir / ".." / ".." / "etc" / "passwd"

        with pytest.raises(ApplicationError) as exc_info:
            self.validator.validate_import_path(attack_path)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    def test_validate_import_path_resolves_relative(self) -> None:
        """Test validation resolves relative paths correctly."""
        # Create nested file
        nested_dir = self.themes_dir / "nested"
        nested_dir.mkdir(exist_ok=True)
        nested_qss = nested_dir / "theme.qss"
        nested_qss.write_text("/* nested */", encoding="utf-8")

        # Use relative path
        result = self.validator.validate_import_path(nested_qss)
        assert result == nested_qss.resolve()
        assert result.is_absolute()


class TestThemeValidatorBundleMode:
    """Test ThemeValidator in PyInstaller bundle mode scenarios."""

    def setup_method(self) -> None:
        """Set up test fixtures simulating bundle mode."""
        self.test_dir = Path("test_bundle_validator")

        # Simulate PyInstaller structure
        self.bundle_dir = self.test_dir / "_MEIPASS" / "resources" / "themes"
        self.user_dir = self.test_dir / "home" / ".anivault" / "themes"

        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        self.user_dir.mkdir(parents=True, exist_ok=True)

        # Create bundle themes
        (self.bundle_dir / "light.qss").write_text(
            "@import url('common.qss');", encoding="utf-8"
        )
        (self.bundle_dir / "common.qss").write_text(
            "/* common styles */", encoding="utf-8"
        )

        # Create user theme
        (self.user_dir / "custom.qss").write_text(
            "@import url('light.qss');", encoding="utf-8"
        )

        self.validator = ThemeValidator(
            themes_dir=self.user_dir,
            base_theme_dir=self.bundle_dir,
        )

    def teardown_method(self) -> None:
        """Clean up test files."""
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_bundle_theme_can_import_common(self) -> None:
        """Test bundle themes can import common.qss from base_theme_dir.

        This is the CRITICAL BUG FIX test case.
        Before: Failed because only themes_dir was validated
        After: Succeeds because both themes_dir AND base_theme_dir are validated
        """
        common_path = self.bundle_dir / "common.qss"
        result = self.validator.validate_import_path(common_path)
        assert result == common_path.resolve()

    def test_user_theme_can_import_bundle_common(self) -> None:
        """Test user themes can import bundle common.qss (cross-directory)."""
        common_path = self.bundle_dir / "common.qss"
        result = self.validator.validate_import_path(common_path)
        assert result == common_path.resolve()

    def test_bundle_theme_can_import_user_custom(self) -> None:
        """Test bundle themes can import user custom files (cross-directory)."""
        custom_path = self.user_dir / "custom.qss"
        result = self.validator.validate_import_path(custom_path)
        assert result == custom_path.resolve()

    def test_cannot_import_outside_both_directories(self) -> None:
        """Test imports outside both directories are rejected."""
        outside_path = self.test_dir / "outside.qss"
        outside_path.write_text("/* malicious */", encoding="utf-8")

        with pytest.raises(ApplicationError) as exc_info:
            self.validator.validate_import_path(outside_path)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "outside allowed directories" in exc_info.value.message
