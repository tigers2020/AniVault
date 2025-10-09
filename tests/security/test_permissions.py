"""Tests for security permissions utilities.

Tests follow the Failure-First pattern:
1. Test failure cases first
2. Test edge cases
3. Test happy path
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from anivault.security.permissions import (
    set_secure_file_permissions,
    validate_api_key_not_in_data,
)
from anivault.shared.errors import ApplicationError, ErrorCode


class TestSetSecureFilePermissions:
    """Test file permission setting functionality."""

    def test_set_permissions_file_not_found(self, tmp_path: Path) -> None:
        """Should raise error if file doesn't exist."""
        # Given
        non_existent = tmp_path / "nonexistent.db"

        # When & Then
        with pytest.raises(ApplicationError) as exc_info:
            set_secure_file_permissions(non_existent)

        assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND
        assert "does not exist" in exc_info.value.message

    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific test")
    def test_set_unix_permissions_success(self, tmp_path: Path) -> None:
        """Should set 600 permissions on Unix systems."""
        # Given
        test_file = tmp_path / "test.db"
        test_file.touch()

        # When
        set_secure_file_permissions(test_file)

        # Then
        stat_result = os.stat(test_file)
        file_mode = stat_result.st_mode & 0o777
        assert file_mode == 0o600, f"Expected 0o600, got {oct(file_mode)}"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_set_windows_permissions_success(self, tmp_path: Path) -> None:
        """Should set owner-only permissions on Windows."""
        # Given
        test_file = tmp_path / "test.db"
        test_file.touch()

        # When
        set_secure_file_permissions(test_file)

        # Then
        # On Windows, just verify no exception was raised
        # Actual ACL verification requires pywin32
        assert test_file.exists()


class TestValidateApiKeyNotInData:
    """Test API key validation functionality."""

    def test_api_key_in_root_level(self) -> None:
        """Should raise error if api_key is in root level."""
        # Given
        data = {  # pragma: allowlist secret
            "api_key": "sk-1234567890",
            "title": "Test Anime",
        }

        # When & Then
        with pytest.raises(ApplicationError) as exc_info:
            validate_api_key_not_in_data(data)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "sensitive data" in exc_info.value.message.lower()

    def test_api_key_in_nested_dict(self) -> None:
        """Should raise error if api_key is in nested dictionary."""
        # Given
        data = {
            "title": "Test Anime",
            "metadata": {
                "api_key": "sk-1234567890",
                "version": "1.0",
            },  # pragma: allowlist secret
        }

        # When & Then
        with pytest.raises(ApplicationError) as exc_info:
            validate_api_key_not_in_data(data)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "metadata.api_key" in exc_info.value.message

    def test_api_key_in_list(self) -> None:
        """Should raise error if api_key is in list of dictionaries."""
        # Given
        data = {  # pragma: allowlist secret
            "items": [
                {"title": "Anime 1"},
                {
                    "title": "Anime 2",
                    "secret": "confidential",
                },
            ]
        }

        # When & Then
        with pytest.raises(ApplicationError) as exc_info:
            validate_api_key_not_in_data(data)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "secret" in exc_info.value.message.lower()

    def test_various_sensitive_key_names(self) -> None:
        """Should detect various sensitive key patterns."""
        # Given
        sensitive_patterns = [  # pragma: allowlist secret
            {"apikey": "value"},
            {"api-key": "value"},
            {"secret": "value"},
            {"password": "value"},
            {"token": "value"},
            {"access_token": "value"},
            {"refresh_token": "value"},
        ]

        for data in sensitive_patterns:
            # When & Then
            with pytest.raises(ApplicationError) as exc_info:
                validate_api_key_not_in_data(data)

            assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    def test_safe_data_passes_validation(self) -> None:
        """Should pass validation for safe data."""
        # Given
        safe_data = {
            "title": "Attack on Titan",
            "id": 12345,
            "year": 2013,
            "genres": ["Action", "Drama"],
            "rating": 8.5,
            "metadata": {"source": "tmdb", "version": "1.0"},
        }

        # When & Then - Should not raise
        validate_api_key_not_in_data(safe_data)

    def test_empty_data_passes_validation(self) -> None:
        """Should pass validation for empty data."""
        # Given
        empty_data = {}

        # When & Then - Should not raise
        validate_api_key_not_in_data(empty_data)
