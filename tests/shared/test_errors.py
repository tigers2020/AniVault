"""
Tests for AniVault Error Handling System

This module tests the error handling system including:
- ErrorCode enum functionality
- ErrorContext data structure
- AniVaultError base class
- Domain, Infrastructure, and Application error classes
- Convenience functions for common error scenarios
"""

from pathlib import Path

import pytest

from anivault.shared.errors import (
    AniVaultError,
    ApplicationError,
    DomainError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
    create_api_error,
    create_config_error,
    create_file_not_found_error,
    create_parsing_error,
    create_permission_denied_error,
    create_validation_error,
)


class TestErrorCode:
    """Test ErrorCode enum functionality."""

    def test_error_code_values(self):
        """Test that error codes have correct string values."""
        assert ErrorCode.FILE_NOT_FOUND == "FILE_NOT_FOUND"
        assert ErrorCode.NETWORK_ERROR == "NETWORK_ERROR"
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.PARSING_ERROR == "PARSING_ERROR"
        assert ErrorCode.CACHE_ERROR == "CACHE_ERROR"
        assert ErrorCode.CONFIG_ERROR == "CONFIG_ERROR"
        assert ErrorCode.APPLICATION_ERROR == "APPLICATION_ERROR"

    def test_error_code_enum_inheritance(self):
        """Test that ErrorCode inherits from str and Enum."""
        assert isinstance(ErrorCode.FILE_NOT_FOUND, str)
        assert isinstance(ErrorCode.FILE_NOT_FOUND, ErrorCode)


class TestErrorContext:
    """Test ErrorContext data structure."""

    def test_error_context_creation(self):
        """Test ErrorContext creation with all fields."""
        context = ErrorContext(
            file_path="/test/path",
            operation="test_operation",
            user_id="test_user",
            additional_data={"key": "value"},
        )

        assert context.file_path == "/test/path"
        assert context.operation == "test_operation"
        assert context.user_id == "test_user"
        assert context.additional_data == {"key": "value"}

    def test_error_context_defaults(self):
        """Test ErrorContext creation with default values."""
        context = ErrorContext()

        assert context.file_path is None
        assert context.operation is None
        assert context.user_id is None
        assert context.additional_data is None

    def test_error_context_to_dict(self):
        """Test ErrorContext to_dict method."""
        context = ErrorContext(
            file_path="/test/path",
            operation="test_operation",
            additional_data={"key": "value"},
        )

        result = context.to_dict()
        expected = {
            "file_path": "/test/path",
            "operation": "test_operation",
            "user_id": None,
            "additional_data": {"key": "value"},
        }

        assert result == expected


class TestAniVaultError:
    """Test AniVaultError base class."""

    def test_anivault_error_creation(self):
        """Test AniVaultError creation with all parameters."""
        context = ErrorContext(file_path="/test/path")
        original_error = ValueError("Original error")

        error = AniVaultError(
            ErrorCode.FILE_NOT_FOUND, "Test error message", context, original_error
        )

        assert error.code == ErrorCode.FILE_NOT_FOUND
        assert error.message == "Test error message"
        assert error.context == context
        assert error.original_error == original_error

    def test_anivault_error_without_context(self):
        """Test AniVaultError creation without context."""
        error = AniVaultError(ErrorCode.VALIDATION_ERROR, "Test validation error")

        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.message == "Test validation error"
        assert isinstance(error.context, ErrorContext)
        assert error.original_error is None

    def test_anivault_error_string_representation(self):
        """Test AniVaultError string representation."""
        error = AniVaultError(ErrorCode.PARSING_ERROR, "Parsing failed")

        assert str(error) == "PARSING_ERROR: Parsing failed"
        assert f"{error}" == "PARSING_ERROR: Parsing failed"

    def test_anivault_error_inheritance(self):
        """Test that AniVaultError inherits from Exception."""
        error = AniVaultError(ErrorCode.APPLICATION_ERROR, "Test error")

        assert isinstance(error, Exception)
        assert isinstance(error, AniVaultError)

    def test_anivault_error_to_dict(self):
        """Test AniVaultError to_dict method."""
        context = ErrorContext(file_path="/test/path", operation="test_operation")
        original_error = ValueError("Original error")

        error = AniVaultError(
            ErrorCode.CACHE_ERROR, "Cache operation failed", context, original_error
        )

        result = error.to_dict()
        expected = {
            "code": "CACHE_ERROR",
            "message": "Cache operation failed",
            "context": {
                "file_path": "/test/path",
                "operation": "test_operation",
                "user_id": None,
                "additional_data": None,
            },
            "original_error": "Original error",
        }

        assert result == expected


class TestDomainError:
    """Test DomainError class."""

    def test_domain_error_inheritance(self):
        """Test that DomainError inherits from AniVaultError."""
        error = DomainError(ErrorCode.VALIDATION_ERROR, "Domain validation failed")

        assert isinstance(error, AniVaultError)
        assert isinstance(error, DomainError)
        assert isinstance(error, Exception)

    def test_domain_error_creation(self):
        """Test DomainError creation."""
        context = ErrorContext(operation="validate_data")
        error = DomainError(
            ErrorCode.INVALID_FILE_FORMAT, "Invalid anime file format", context
        )

        assert error.code == ErrorCode.INVALID_FILE_FORMAT
        assert error.message == "Invalid anime file format"
        assert error.context == context


class TestInfrastructureError:
    """Test InfrastructureError class."""

    def test_infrastructure_error_inheritance(self):
        """Test that InfrastructureError inherits from AniVaultError."""
        error = InfrastructureError(
            ErrorCode.NETWORK_ERROR, "Network connection failed"
        )

        assert isinstance(error, AniVaultError)
        assert isinstance(error, InfrastructureError)
        assert isinstance(error, Exception)

    def test_infrastructure_error_creation(self):
        """Test InfrastructureError creation."""
        context = ErrorContext(operation="api_call")
        original_error = ConnectionError("Connection timeout")

        error = InfrastructureError(
            ErrorCode.API_TIMEOUT, "API request timed out", context, original_error
        )

        assert error.code == ErrorCode.API_TIMEOUT
        assert error.message == "API request timed out"
        assert error.context == context
        assert error.original_error == original_error


class TestApplicationError:
    """Test ApplicationError class."""

    def test_application_error_inheritance(self):
        """Test that ApplicationError inherits from AniVaultError."""
        error = ApplicationError(ErrorCode.CONFIG_ERROR, "Configuration error")

        assert isinstance(error, AniVaultError)
        assert isinstance(error, ApplicationError)
        assert isinstance(error, Exception)

    def test_application_error_creation(self):
        """Test ApplicationError creation."""
        context = ErrorContext(additional_data={"config_file": "settings.yaml"})

        error = ApplicationError(
            ErrorCode.MISSING_CONFIG, "Required configuration missing", context
        )

        assert error.code == ErrorCode.MISSING_CONFIG
        assert error.message == "Required configuration missing"
        assert error.context == context


class TestConvenienceFunctions:
    """Test convenience functions for creating common errors."""

    def test_create_file_not_found_error(self):
        """Test create_file_not_found_error function."""
        original_error = FileNotFoundError("File not found")

        error = create_file_not_found_error(
            "/test/file.mkv", "scan_directory", original_error
        )

        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.FILE_NOT_FOUND
        assert "File not found: /test/file.mkv" in error.message
        assert error.context.file_path == "/test/file.mkv"
        assert error.context.operation == "scan_directory"
        assert error.original_error == original_error

    def test_create_permission_denied_error(self):
        """Test create_permission_denied_error function."""
        error = create_permission_denied_error("/restricted/path", "write_file")

        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.PERMISSION_DENIED
        assert "Permission denied: /restricted/path" in error.message
        assert error.context.file_path == "/restricted/path"
        assert error.context.operation == "write_file"

    def test_create_validation_error(self):
        """Test create_validation_error function."""
        error = create_validation_error(
            "Invalid file format", "file_extension", "validate_file"
        )

        assert isinstance(error, DomainError)
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.message == "Invalid file format"
        assert error.context.operation == "validate_file"
        assert error.context.additional_data == {"field": "file_extension"}

    def test_create_api_error(self):
        """Test create_api_error function."""
        original_error = ConnectionError("Connection failed")

        error = create_api_error(
            "TMDB API request failed", "fetch_metadata", original_error
        )

        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.API_REQUEST_FAILED
        assert error.message == "TMDB API request failed"
        assert error.context.operation == "fetch_metadata"
        assert error.original_error == original_error

    def test_create_parsing_error(self):
        """Test create_parsing_error function."""
        error = create_parsing_error(
            "Failed to parse anime filename", "/anime/episode.mkv", "parse_filename"
        )

        assert isinstance(error, DomainError)
        assert error.code == ErrorCode.PARSING_ERROR
        assert error.message == "Failed to parse anime filename"
        assert error.context.file_path == "/anime/episode.mkv"
        assert error.context.operation == "parse_filename"

    def test_create_config_error(self):
        """Test create_config_error function."""
        error = create_config_error(
            "Missing API key configuration", "tmdb_api_key", "load_config"
        )

        assert isinstance(error, ApplicationError)
        assert error.code == ErrorCode.CONFIG_ERROR
        assert error.message == "Missing API key configuration"
        assert error.context.operation == "load_config"
        assert error.context.additional_data == {"config_key": "tmdb_api_key"}


class TestErrorHandlingIntegration:
    """Integration tests for error handling system."""

    def test_error_chaining(self):
        """Test that errors can be properly chained."""
        original_error = ValueError("Original validation error")

        context = ErrorContext(file_path="/test/file.mkv", operation="parse_metadata")

        domain_error = DomainError(
            ErrorCode.PARSING_ERROR, "Failed to parse metadata", context, original_error
        )

        assert domain_error.original_error == original_error
        assert str(domain_error.original_error) == "Original validation error"

    def test_error_context_preservation(self):
        """Test that error context is preserved through the chain."""
        context = ErrorContext(
            file_path="/anime/episode.mkv",
            operation="process_file",
            user_id="user123",
            additional_data={"episode": 1, "season": 1},
        )

        error = InfrastructureError(
            ErrorCode.FILE_ACCESS_DENIED, "Cannot access file", context
        )

        assert error.context.file_path == "/anime/episode.mkv"
        assert error.context.operation == "process_file"
        assert error.context.user_id == "user123"
        assert error.context.additional_data == {"episode": 1, "season": 1}

    def test_error_serialization(self):
        """Test that errors can be serialized for logging."""
        context = ErrorContext(
            file_path="/test/path",
            operation="test_operation",
            additional_data={"key": "value"},
        )

        error = ApplicationError(
            ErrorCode.APPLICATION_ERROR, "Test application error", context
        )

        serialized = error.to_dict()

        assert "code" in serialized
        assert "message" in serialized
        assert "context" in serialized
        assert serialized["code"] == "APPLICATION_ERROR"
        assert serialized["message"] == "Test application error"
        assert serialized["context"]["file_path"] == "/test/path"


@pytest.mark.parametrize(
    "error_class,expected_code",
    [
        (DomainError, ErrorCode.VALIDATION_ERROR),
        (InfrastructureError, ErrorCode.NETWORK_ERROR),
        (ApplicationError, ErrorCode.CONFIG_ERROR),
    ],
)
def test_error_class_inheritance(error_class, expected_code):
    """Parametrized test for error class inheritance."""
    error = error_class(expected_code, "Test message")

    assert isinstance(error, AniVaultError)
    assert isinstance(error, Exception)
    assert error.code == expected_code
    assert error.message == "Test message"
