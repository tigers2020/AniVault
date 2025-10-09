"""
Tests for AniVault error handling system.

This module contains comprehensive unit tests for the error hierarchy
defined in anivault.shared.errors module.
"""

import dataclasses
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


class TestErrorContext:
    """Test cases for ErrorContext frozen dataclass."""

    def test_empty_context(self):
        """Test creating an empty ErrorContext."""
        context = ErrorContext()
        assert context.file_path is None
        assert context.operation is None
        assert context.user_id is None
        assert context.additional_data == {}  # Now returns empty dict instead of None

    def test_context_with_data(self):
        """Test creating ErrorContext with data."""
        additional_data = {"test": "value"}
        context = ErrorContext(
            file_path="/test/path",
            operation="test_operation",
            user_id="user123",
            additional_data=additional_data,
        )
        
        assert context.file_path == "/test/path"
        assert context.operation == "test_operation"
        assert context.user_id == "user123"
        assert context.additional_data == additional_data

    def test_asdict_serialization(self):
        """Test converting ErrorContext to dictionary using asdict()."""
        additional_data = {"key": "value"}
        context = ErrorContext(
            file_path="/test/path",
            operation="test_operation",
            user_id="user123",
            additional_data=additional_data,
        )
        
        result = dataclasses.asdict(context)
        expected = {
            "file_path": "/test/path",
            "operation": "test_operation",
            "user_id": "user123",
            "additional_data": additional_data,
        }
        assert result == expected

    def test_frozen_immutability(self):
        """Test that ErrorContext is immutable (frozen)."""
        context = ErrorContext(file_path="/test/path")
        
        # Attempting to modify any attribute should raise FrozenInstanceError
        with pytest.raises(dataclasses.FrozenInstanceError):
            context.file_path = "/new/path"
        
        with pytest.raises(dataclasses.FrozenInstanceError):
            context.operation = "new_operation"
        
        with pytest.raises(dataclasses.FrozenInstanceError):
            context.additional_data = {"new": "data"}

    def test_additional_data_factory(self):
        """Test that each ErrorContext instance gets its own additional_data dict."""
        context1 = ErrorContext()
        context2 = ErrorContext()
        
        # Each instance should have its own dict
        assert id(context1.additional_data) != id(context2.additional_data)
        
        # Modifying one shouldn't affect the other
        # (Note: The dict itself is mutable, but the field reference is immutable)
        context1.additional_data["key"] = "value1"
        assert "key" not in context2.additional_data

    def test_equality_comparison(self):
        """Test that two ErrorContext instances with same data are equal."""
        context1 = ErrorContext(
            file_path="/test/path",
            operation="test_op",
            user_id="user123",
            additional_data={"key": "value"}
        )
        context2 = ErrorContext(
            file_path="/test/path",
            operation="test_op",
            user_id="user123",
            additional_data={"key": "value"}
        )
        
        assert context1 == context2

    def test_repr_format(self):
        """Test that auto-generated __repr__ works correctly."""
        context = ErrorContext(
            file_path="/test/path",
            operation="test_op"
        )
        
        repr_str = repr(context)
        assert "ErrorContext" in repr_str
        assert "file_path='/test/path'" in repr_str
        assert "operation='test_op'" in repr_str


class TestAniVaultError:
    """Test cases for base AniVaultError class."""

    def test_basic_error_creation(self):
        """Test creating a basic AniVaultError."""
        error = AniVaultError(
            ErrorCode.FILE_NOT_FOUND,
            "Test error message"
        )
        
        assert error.code == ErrorCode.FILE_NOT_FOUND
        assert error.message == "Test error message"
        assert error.context is not None
        assert error.original_error is None

    def test_error_with_context(self):
        """Test creating AniVaultError with context."""
        context = ErrorContext(file_path="/test/path")
        error = AniVaultError(
            ErrorCode.PERMISSION_DENIED,
            "Permission denied",
            context
        )
        
        assert error.context == context
        assert error.context.file_path == "/test/path"

    def test_error_with_original_error(self):
        """Test creating AniVaultError with original error."""
        original = FileNotFoundError("Original error")
        error = AniVaultError(
            ErrorCode.FILE_NOT_FOUND,
            "File not found",
            original_error=original
        )
        
        assert error.original_error == original

    def test_str_representation(self):
        """Test string representation of AniVaultError."""
        error = AniVaultError(
            ErrorCode.VALIDATION_ERROR,
            "Validation failed"
        )
        
        expected = "VALIDATION_ERROR: Validation failed"
        assert str(error) == expected

    def test_to_dict(self):
        """Test converting AniVaultError to dictionary."""
        context = ErrorContext(file_path="/test/path")
        original = ValueError("Original error")
        error = AniVaultError(
            ErrorCode.API_REQUEST_FAILED,
            "API request failed",
            context,
            original
        )
        
        result = error.to_dict()
        expected = {
            "code": "API_REQUEST_FAILED",
            "message": "API request failed",
            "context": dataclasses.asdict(context),
            "original_error": "Original error",
        }
        assert result == expected

    def test_to_dict_without_original_error(self):
        """Test converting AniVaultError to dictionary without original error."""
        error = AniVaultError(
            ErrorCode.CONFIG_ERROR,
            "Configuration error"
        )
        
        result = error.to_dict()
        assert result["original_error"] is None


class TestDomainError:
    """Test cases for DomainError class."""

    def test_domain_error_inheritance(self):
        """Test that DomainError inherits from AniVaultError."""
        error = DomainError(
            ErrorCode.VALIDATION_ERROR,
            "Business rule violation"
        )
        
        assert isinstance(error, AniVaultError)
        assert isinstance(error, DomainError)
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.message == "Business rule violation"

    def test_domain_error_creation(self):
        """Test creating DomainError with context."""
        context = ErrorContext(operation="validate_data")
        error = DomainError(
            ErrorCode.INVALID_METADATA,
            "Invalid metadata format",
            context
        )
        
        assert error.context.operation == "validate_data"
        assert str(error) == "INVALID_METADATA: Invalid metadata format"


class TestInfrastructureError:
    """Test cases for InfrastructureError class."""

    def test_infrastructure_error_inheritance(self):
        """Test that InfrastructureError inherits from AniVaultError."""
        error = InfrastructureError(
            ErrorCode.NETWORK_ERROR,
            "Network connection failed"
        )
        
        assert isinstance(error, AniVaultError)
        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.NETWORK_ERROR
        assert error.message == "Network connection failed"

    def test_infrastructure_error_creation(self):
        """Test creating InfrastructureError with original error."""
        original = ConnectionError("Connection failed")
        error = InfrastructureError(
            ErrorCode.API_TIMEOUT,
            "API request timed out",
            original_error=original
        )
        
        assert error.original_error == original
        assert str(error) == "API_TIMEOUT: API request timed out"


class TestApplicationError:
    """Test cases for ApplicationError class."""

    def test_application_error_inheritance(self):
        """Test that ApplicationError inherits from AniVaultError."""
        error = ApplicationError(
            ErrorCode.CONFIG_ERROR,
            "Configuration error"
        )
        
        assert isinstance(error, AniVaultError)
        assert isinstance(error, ApplicationError)
        assert error.code == ErrorCode.CONFIG_ERROR
        assert error.message == "Configuration error"

    def test_application_error_creation(self):
        """Test creating ApplicationError with context."""
        context = ErrorContext(additional_data={"config_key": "api_key"})
        error = ApplicationError(
            ErrorCode.CLI_INVALID_ARGUMENTS,
            "Invalid command line arguments",
            context
        )
        
        assert error.context.additional_data["config_key"] == "api_key"
        assert str(error) == "CLI_INVALID_ARGUMENTS: Invalid command line arguments"


class TestErrorConvenienceFunctions:
    """Test cases for error convenience functions."""

    def test_create_file_not_found_error(self):
        """Test create_file_not_found_error function."""
        error = create_file_not_found_error(
            "/test/file.txt",
            "read_file",
            FileNotFoundError("File not found")
        )
        
        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.FILE_NOT_FOUND
        assert error.message == "File not found: /test/file.txt"
        assert error.context.file_path == "/test/file.txt"
        assert error.context.operation == "read_file"
        assert isinstance(error.original_error, FileNotFoundError)

    def test_create_permission_denied_error(self):
        """Test create_permission_denied_error function."""
        error = create_permission_denied_error(
            "/protected/path",
            "write_file"
        )
        
        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.PERMISSION_DENIED
        assert error.message == "Permission denied: /protected/path"
        assert error.context.file_path == "/protected/path"
        assert error.context.operation == "write_file"

    def test_create_validation_error(self):
        """Test create_validation_error function."""
        error = create_validation_error(
            "Invalid email format",
            "email",
            "validate_user"
        )
        
        assert isinstance(error, DomainError)
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.message == "Invalid email format"
        assert error.context.operation == "validate_user"
        assert error.context.additional_data["field"] == "email"

    def test_create_api_error(self):
        """Test create_api_error function."""
        error = create_api_error(
            "API returned 500 error",
            "fetch_data",
            ConnectionError("Connection failed")
        )
        
        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.API_REQUEST_FAILED
        assert error.message == "API returned 500 error"
        assert error.context.operation == "fetch_data"
        assert isinstance(error.original_error, ConnectionError)

    def test_create_parsing_error(self):
        """Test create_parsing_error function."""
        error = create_parsing_error(
            "Failed to parse JSON",
            "/test/file.json",
            "parse_config"
        )
        
        assert isinstance(error, DomainError)
        assert error.code == ErrorCode.PARSING_ERROR
        assert error.message == "Failed to parse JSON"
        assert error.context.file_path == "/test/file.json"
        assert error.context.operation == "parse_config"

    def test_create_config_error(self):
        """Test create_config_error function."""
        error = create_config_error(
            "Missing required configuration",
            "database_url",
            "load_config"
        )
        
        assert isinstance(error, ApplicationError)
        assert error.code == ErrorCode.CONFIG_ERROR
        assert error.message == "Missing required configuration"
        assert error.context.operation == "load_config"
        assert error.context.additional_data["config_key"] == "database_url"


class TestErrorRaisingAndCatching:
    """Test cases for raising and catching errors."""

    def test_raise_and_catch_anivault_error(self):
        """Test raising and catching AniVaultError."""
        with pytest.raises(AniVaultError) as exc_info:
            raise AniVaultError(
                ErrorCode.APPLICATION_ERROR,
                "Test error"
            )
        
        assert exc_info.value.code == ErrorCode.APPLICATION_ERROR
        assert exc_info.value.message == "Test error"

    def test_raise_and_catch_domain_error(self):
        """Test raising and catching DomainError."""
        with pytest.raises(DomainError) as exc_info:
            raise DomainError(
                ErrorCode.BUSINESS_LOGIC_ERROR,
                "Business rule violation"
            )
        
        assert exc_info.value.code == ErrorCode.BUSINESS_LOGIC_ERROR
        assert exc_info.value.message == "Business rule violation"

    def test_raise_and_catch_infrastructure_error(self):
        """Test raising and catching InfrastructureError."""
        with pytest.raises(InfrastructureError) as exc_info:
            raise InfrastructureError(
                ErrorCode.FILE_ACCESS_DENIED,
                "File access denied"
            )
        
        assert exc_info.value.code == ErrorCode.FILE_ACCESS_DENIED
        assert exc_info.value.message == "File access denied"

    def test_raise_and_catch_application_error(self):
        """Test raising and catching ApplicationError."""
        with pytest.raises(ApplicationError) as exc_info:
            raise ApplicationError(
                ErrorCode.CLI_COMMAND_FAILED,
                "Command execution failed"
            )
        
        assert exc_info.value.code == ErrorCode.CLI_COMMAND_FAILED
        assert exc_info.value.message == "Command execution failed"

    def test_catch_base_error_for_specific_errors(self):
        """Test catching base AniVaultError for specific error types."""
        try:
            raise DomainError(
                ErrorCode.VALIDATION_ERROR,
                "Validation failed"
            )
        except AniVaultError as e:
            assert e.code == ErrorCode.VALIDATION_ERROR
            assert isinstance(e, DomainError)
        else:
            pytest.fail("Expected AniVaultError to be raised")

    def test_error_chain_preservation(self):
        """Test that original errors are preserved in the chain."""
        original = ValueError("Original value error")
        
        try:
            raise AniVaultError(
                ErrorCode.PARSING_ERROR,
                "Failed to parse data",
                original_error=original
            )
        except AniVaultError as e:
            assert e.original_error == original
            assert str(e.original_error) == "Original value error"
