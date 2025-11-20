"""
Tests for error handling in AutoScanner module.

Focuses on failure-first testing for silent failure removal.
Tests:
1. Configuration load errors should raise ConfigurationError
2. Error messages should be informative
3. Callers should handle errors appropriately
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from anivault.config.auto_scanner import AutoScanner
from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext


class TestShouldAutoScanOnStartupFailures:
    """Test error handling in should_auto_scan_on_startup method."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path) -> None:
        """Set up test fixtures."""
        # Create a temporary config file path
        config_path = tmp_path / "config.toml"
        config_path.touch()
        self.scanner = AutoScanner(config_path)

    def test_config_load_error_raises_application_error(self, monkeypatch) -> None:
        """Configuration load error should raise ApplicationError with context."""
        # Given: get_config() raises exception
        load_error = RuntimeError("Config file corrupted")

        def mock_get_config():
            raise ApplicationError(
                ErrorCode.CONFIGURATION_ERROR,
                "Failed to check auto scan configuration",
                ErrorContext(operation="should_auto_scan_on_startup"),
                load_error,
            )

        monkeypatch.setattr("anivault.config.auto_scanner.get_config", mock_get_config)

        # When & Then: should raise ApplicationError
        with pytest.raises(ApplicationError) as exc_info:
            self.scanner.should_auto_scan_on_startup()

        # Verify error details
        assert exc_info.value.code == ErrorCode.CONFIGURATION_ERROR
        assert "check auto scan configuration" in str(exc_info.value).lower()

    def test_permission_error_raises_application_error(self, monkeypatch) -> None:
        """Permission error should raise ApplicationError."""
        # Given: permission denied on config file
        permission_error = PermissionError("Access denied to config file")

        def mock_get_config():
            raise ApplicationError(
                ErrorCode.CONFIGURATION_ERROR,
                "Failed to check auto scan configuration",
                ErrorContext(operation="should_auto_scan_on_startup"),
                permission_error,
            )

        monkeypatch.setattr("anivault.config.auto_scanner.get_config", mock_get_config)

        # When & Then: should raise ApplicationError
        with pytest.raises(ApplicationError) as exc_info:
            self.scanner.should_auto_scan_on_startup()

        assert exc_info.value.code == ErrorCode.CONFIGURATION_ERROR

    def test_success_returns_bool_and_folder_path(self, monkeypatch) -> None:
        """Successful check should return tuple as before."""
        # Given: valid configuration
        mock_config = Mock()
        mock_folders = Mock()
        mock_folders.auto_scan_on_startup = True
        mock_folders.source_folder = "/test/folder"
        mock_config.folders = mock_folders

        monkeypatch.setattr(
            "anivault.config.auto_scanner.get_config",
            lambda: mock_config,
        )

        # Mock FolderValidator to return valid
        with patch("anivault.config.auto_scanner.FolderValidator") as mock_validator:
            mock_validator.validate_folder_path.return_value = (True, "")

            # When
            should_scan, folder_path = self.scanner.should_auto_scan_on_startup()

            # Then
            assert should_scan is True
            assert folder_path == "/test/folder"

    def test_disabled_returns_false_empty_string(self, monkeypatch) -> None:
        """When disabled, should return False with empty string (normal case)."""
        # Given: auto scan disabled
        mock_config = Mock()
        mock_folders = Mock()
        mock_folders.auto_scan_on_startup = False
        mock_config.folders = mock_folders

        monkeypatch.setattr(
            "anivault.config.auto_scanner.get_config",
            lambda: mock_config,
        )

        # When
        should_scan, folder_path = self.scanner.should_auto_scan_on_startup()

        # Then
        assert should_scan is False
        assert folder_path == ""


class TestGetFolderSettingsFailures:
    """Test error handling in get_folder_settings method."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path) -> None:
        """Set up test fixtures."""
        # Create a temporary config file path
        config_path = tmp_path / "config.toml"
        config_path.touch()
        self.scanner = AutoScanner(config_path)

    def test_config_load_error_raises_application_error(self, monkeypatch) -> None:
        """Configuration load error should raise ApplicationError."""
        # Given: get_config() raises exception
        load_error = RuntimeError("Database connection failed")

        def mock_get_config():
            raise ApplicationError(
                ErrorCode.CONFIGURATION_ERROR,
                "Failed to retrieve folder settings",
                ErrorContext(operation="get_folder_settings"),
                load_error,
            )

        monkeypatch.setattr("anivault.config.auto_scanner.get_config", mock_get_config)

        # When & Then: should raise ApplicationError
        with pytest.raises(ApplicationError) as exc_info:
            self.scanner.get_folder_settings()

        # Verify error details
        assert exc_info.value.code == ErrorCode.CONFIGURATION_ERROR
        assert "retrieve folder settings" in str(exc_info.value).lower()

    def test_file_not_found_raises_application_error(self, monkeypatch) -> None:
        """File not found should raise ApplicationError."""
        # Given: config file doesn't exist
        file_error = FileNotFoundError("Config file not found")

        def mock_get_config():
            raise ApplicationError(
                ErrorCode.CONFIGURATION_ERROR,
                "Failed to retrieve folder settings",
                ErrorContext(operation="get_folder_settings"),
                file_error,
            )

        monkeypatch.setattr("anivault.config.auto_scanner.get_config", mock_get_config)

        # When & Then: should raise ApplicationError
        with pytest.raises(ApplicationError) as exc_info:
            self.scanner.get_folder_settings()

        assert exc_info.value.code == ErrorCode.CONFIGURATION_ERROR

    def test_success_returns_folder_settings(self, monkeypatch) -> None:
        """Successful call should return FolderSettings object."""
        # Given: valid configuration
        mock_config = Mock()
        mock_folders = Mock()
        mock_config.folders = mock_folders

        monkeypatch.setattr(
            "anivault.config.auto_scanner.get_config",
            lambda: mock_config,
        )

        # When
        result = self.scanner.get_folder_settings()

        # Then
        assert result is mock_folders


class TestGetScanStatusErrorHandling:
    """Test get_scan_status handles get_folder_settings errors."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path) -> None:
        """Set up test fixtures."""
        # Create a temporary config file path
        config_path = tmp_path / "config.toml"
        config_path.touch()
        self.scanner = AutoScanner(config_path)

    def test_folder_settings_error_returns_error_dict_with_details(
        self,
        monkeypatch,
    ) -> None:
        """When get_folder_settings raises error, should return error dict with details."""

        # Given: get_folder_settings will raise ApplicationError
        def mock_get_config():
            raise ApplicationError(
                ErrorCode.CONFIGURATION_ERROR,
                "Failed to retrieve folder settings",
                ErrorContext(operation="get_folder_settings"),
                RuntimeError("DB error"),
            )

        monkeypatch.setattr("anivault.config.auto_scanner.get_config", mock_get_config)

        # When
        result = self.scanner.get_scan_status()

        # Then: should return error dict with meaningful error message
        assert result["enabled"] is False
        assert result["can_scan"] is False
        assert "error" in result
        # The error message should contain details about the failure
        assert "Failed" in result["error"] or "error" in result["error"].lower()


class TestAutoScanStartupCallerHandling:
    """Test that GUI app properly handles auto_scanner errors."""

    def test_check_auto_scan_startup_catches_application_error(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        """_check_auto_scan_startup should catch ApplicationError and log, not crash."""
        # This is a documentation test - showing expected behavior
        # Actual implementation will be in gui/app.py

        # Given: auto_scanner that raises ApplicationError
        config_path = tmp_path / "config.toml"
        config_path.touch()
        scanner = AutoScanner(config_path)

        def mock_get_config():
            raise ApplicationError(
                ErrorCode.CONFIGURATION_ERROR,
                "Config corrupted",
                ErrorContext(operation="should_auto_scan_on_startup"),
                RuntimeError("Config corrupted"),
            )

        monkeypatch.setattr("anivault.config.auto_scanner.get_config", mock_get_config)

        # When: calling should_auto_scan_on_startup
        # Then: should raise ApplicationError (not return False, "")
        with pytest.raises(ApplicationError):
            scanner.should_auto_scan_on_startup()

        # Note: The caller (gui/app.py:_check_auto_scan_startup) should catch
        # this exception, log it, and continue app startup gracefully
