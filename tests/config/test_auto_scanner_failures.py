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
from anivault.shared.errors import ApplicationError, ErrorCode


class TestShouldAutoScanOnStartupFailures:
    """Test error handling in should_auto_scan_on_startup method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config_manager = Mock()
        self.scanner = AutoScanner(self.config_manager)

    def test_config_load_error_raises_application_error(self) -> None:
        """Configuration load error should raise ApplicationError with context."""
        # Given: config_manager.load_config() raises exception
        load_error = RuntimeError("Config file corrupted")
        self.config_manager.load_config.side_effect = load_error

        # When & Then: should raise ApplicationError
        with pytest.raises(ApplicationError) as exc_info:
            self.scanner.should_auto_scan_on_startup()

        # Verify error details
        assert exc_info.value.code == ErrorCode.CONFIGURATION_ERROR
        assert "check auto scan configuration" in str(exc_info.value).lower()
        assert exc_info.value.original_error == load_error
        assert "should_auto_scan_on_startup" in str(exc_info.value.context)

    def test_permission_error_raises_application_error(self) -> None:
        """Permission error should raise ApplicationError."""
        # Given: permission denied on config file
        permission_error = PermissionError("Access denied to config file")
        self.config_manager.load_config.side_effect = permission_error

        # When & Then: should raise ApplicationError
        with pytest.raises(ApplicationError) as exc_info:
            self.scanner.should_auto_scan_on_startup()

        assert exc_info.value.code == ErrorCode.CONFIGURATION_ERROR
        assert exc_info.value.original_error == permission_error

    def test_success_returns_bool_and_folder_path(self) -> None:
        """Successful check should return tuple as before."""
        # Given: valid configuration
        mock_config = Mock()
        mock_folders = Mock()
        mock_folders.auto_scan_on_startup = True
        mock_folders.source_folder = "/test/folder"
        mock_config.folders = mock_folders
        self.config_manager.load_config.return_value = mock_config

        # Mock FolderValidator to return valid
        with patch("anivault.config.auto_scanner.FolderValidator") as mock_validator:
            mock_validator.validate_folder_path.return_value = (True, "")

            # When
            should_scan, folder_path = self.scanner.should_auto_scan_on_startup()

            # Then
            assert should_scan is True
            assert folder_path == "/test/folder"

    def test_disabled_returns_false_empty_string(self) -> None:
        """When disabled, should return False with empty string (normal case)."""
        # Given: auto scan disabled
        mock_config = Mock()
        mock_folders = Mock()
        mock_folders.auto_scan_on_startup = False
        mock_config.folders = mock_folders
        self.config_manager.load_config.return_value = mock_config

        # When
        should_scan, folder_path = self.scanner.should_auto_scan_on_startup()

        # Then
        assert should_scan is False
        assert folder_path == ""


class TestGetFolderSettingsFailures:
    """Test error handling in get_folder_settings method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config_manager = Mock()
        self.scanner = AutoScanner(self.config_manager)

    def test_config_load_error_raises_application_error(self) -> None:
        """Configuration load error should raise ApplicationError."""
        # Given: config_manager.load_config() raises exception
        load_error = RuntimeError("Database connection failed")
        self.config_manager.load_config.side_effect = load_error

        # When & Then: should raise ApplicationError
        with pytest.raises(ApplicationError) as exc_info:
            self.scanner.get_folder_settings()

        # Verify error details
        assert exc_info.value.code == ErrorCode.CONFIGURATION_ERROR
        assert "retrieve folder settings" in str(exc_info.value).lower()
        assert exc_info.value.original_error == load_error
        assert "get_folder_settings" in str(exc_info.value.context)

    def test_file_not_found_raises_application_error(self) -> None:
        """File not found should raise ApplicationError."""
        # Given: config file doesn't exist
        file_error = FileNotFoundError("Config file not found")
        self.config_manager.load_config.side_effect = file_error

        # When & Then: should raise ApplicationError
        with pytest.raises(ApplicationError) as exc_info:
            self.scanner.get_folder_settings()

        assert exc_info.value.code == ErrorCode.CONFIGURATION_ERROR
        assert exc_info.value.original_error == file_error

    def test_success_returns_folder_settings(self) -> None:
        """Successful call should return FolderSettings object."""
        # Given: valid configuration
        mock_config = Mock()
        mock_folders = Mock()
        mock_config.folders = mock_folders
        self.config_manager.load_config.return_value = mock_config

        # When
        result = self.scanner.get_folder_settings()

        # Then
        assert result is mock_folders


class TestGetScanStatusErrorHandling:
    """Test get_scan_status handles get_folder_settings errors."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.config_manager = Mock()
        self.scanner = AutoScanner(self.config_manager)

    def test_folder_settings_error_returns_error_dict_with_details(self) -> None:
        """When get_folder_settings raises error, should return error dict with details."""
        # Given: get_folder_settings will raise ApplicationError
        self.config_manager.load_config.side_effect = RuntimeError("DB error")

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

    def test_check_auto_scan_startup_catches_application_error(self) -> None:
        """_check_auto_scan_startup should catch ApplicationError and log, not crash."""
        # This is a documentation test - showing expected behavior
        # Actual implementation will be in gui/app.py

        # Given: auto_scanner that raises ApplicationError
        config_manager = Mock()
        config_manager.load_config.side_effect = RuntimeError("Config corrupted")
        scanner = AutoScanner(config_manager)

        # When: calling should_auto_scan_on_startup
        # Then: should raise ApplicationError (not return False, "")
        with pytest.raises(ApplicationError):
            scanner.should_auto_scan_on_startup()

        # Note: The caller (gui/app.py:_check_auto_scan_startup) should catch
        # this exception, log it, and continue app startup gracefully

