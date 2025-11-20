"""
Tests for AniVault error handling system.

This module contains comprehensive unit tests for the error hierarchy
defined in anivault.shared.errors module.
"""

from decimal import Decimal
from enum import Enum
from pathlib import Path

import pytest
from pydantic import ValidationError

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
        assert context.additional_data is None  # Pydantic model: None is default

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

    def test_model_dump_serialization(self):
        """Test converting ErrorContext to dictionary using model_dump()."""
        additional_data = {"key": "value"}
        context = ErrorContext(
            file_path="/test/path",
            operation="test_operation",
            user_id="user123",
            additional_data=additional_data,
        )

        result = context.model_dump()
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

        # Attempting to modify any attribute should raise ValidationError (Pydantic frozen)
        with pytest.raises(ValidationError):
            context.file_path = "/new/path"

        with pytest.raises(ValidationError):
            context.operation = "new_operation"

        with pytest.raises(ValidationError):
            context.additional_data = {"new": "data"}

    def test_additional_data_none_default(self):
        """Test that ErrorContext with no additional_data defaults to None."""
        context1 = ErrorContext()
        context2 = ErrorContext()

        # Both should be None by default (not shared empty dict)
        assert context1.additional_data is None
        assert context2.additional_data is None

        # Creating with explicit dict works
        context3 = ErrorContext(additional_data={"key": "value"})
        assert context3.additional_data == {"key": "value"}

    def test_equality_comparison(self):
        """Test that two ErrorContext instances with same data are equal."""
        context1 = ErrorContext(
            file_path="/test/path",
            operation="test_op",
            user_id="user123",
            additional_data={"key": "value"},
        )
        context2 = ErrorContext(
            file_path="/test/path",
            operation="test_op",
            user_id="user123",
            additional_data={"key": "value"},
        )

        assert context1 == context2

    def test_repr_format(self):
        """Test that auto-generated __repr__ works correctly."""
        context = ErrorContext(file_path="/test/path", operation="test_op")

        repr_str = repr(context)
        assert "ErrorContext" in repr_str
        assert "file_path='/test/path'" in repr_str
        assert "operation='test_op'" in repr_str


class TestErrorContextSafeDict:
    """Test cases for ErrorContext safe_dict PII masking."""

    def test_safe_dict_masks_user_id_by_default(self):
        """Test that user_id is masked by default."""
        context = ErrorContext(
            user_id="sensitive_user_123",
            file_path="/test/path",
            operation="test_op",
        )

        safe = context.safe_dict()
        assert "user_id" not in safe
        assert safe["file_path"] == "/test/path"
        assert safe["operation"] == "test_op"

    def test_safe_dict_ensures_additional_data_present(self):
        """Test that additional_data is always present (never None)."""
        context1 = ErrorContext()
        assert "additional_data" in context1.safe_dict()
        assert context1.safe_dict()["additional_data"] == {}

        context2 = ErrorContext(additional_data=None)
        assert "additional_data" in context2.safe_dict()
        assert context2.safe_dict()["additional_data"] == {}

    def test_safe_dict_preserves_additional_data(self):
        """Test that existing additional_data is preserved."""
        context = ErrorContext(additional_data={"key": "value", "count": 42})

        safe = context.safe_dict()
        assert safe["additional_data"] == {"key": "value", "count": 42}

    def test_safe_dict_custom_mask_keys(self):
        """Test custom mask keys."""
        context = ErrorContext(
            user_id="user123",
            file_path="/secret/path",
            operation="secret_op",
        )

        # Mask file_path and operation instead
        safe = context.safe_dict(mask_keys=("file_path", "operation"))
        assert "file_path" not in safe
        assert "operation" not in safe
        assert safe["user_id"] == "user123"  # Not masked

    def test_safe_dict_empty_mask_keys(self):
        """Test with empty mask keys (no masking)."""
        context = ErrorContext(
            user_id="user123", file_path="/test", operation="test_op"
        )

        safe = context.safe_dict(mask_keys=())
        assert safe["user_id"] == "user123"
        assert safe["file_path"] == "/test"
        assert safe["operation"] == "test_op"

    def test_safe_dict_excludes_none_values(self):
        """Test that None values are excluded by default."""
        context = ErrorContext(file_path="/test", operation=None)

        safe = context.safe_dict()
        assert "file_path" in safe
        assert "operation" not in safe  # None excluded
        assert "user_id" not in safe  # None and masked


class TestErrorContextValidator:
    """Test cases for ErrorContext validator (_coerce_primitives)."""

    def test_primitive_types_passthrough(self):
        """Test that primitive types pass through unchanged."""
        context = ErrorContext(
            additional_data={
                "str_value": "test",
                "int_value": 42,
                "float_value": 3.14,
                "bool_value": True,
            }
        )

        assert context.additional_data["str_value"] == "test"
        assert context.additional_data["int_value"] == 42
        assert context.additional_data["float_value"] == 3.14
        assert context.additional_data["bool_value"] is True

    def test_path_conversion(self):
        """Test that Path objects are converted to strings."""
        test_path = Path("/test/path/file.txt")
        context = ErrorContext(additional_data={"file_path": test_path})

        # Path is converted to string (OS-dependent format)
        assert context.additional_data["file_path"] == str(test_path)
        assert isinstance(context.additional_data["file_path"], str)

    def test_enum_conversion(self):
        """Test that Enum values are converted to their values."""

        class TestEnum(Enum):
            VALUE_A = "a"
            VALUE_B = 42

        context = ErrorContext(
            additional_data={"enum_str": TestEnum.VALUE_A, "enum_int": TestEnum.VALUE_B}
        )

        assert context.additional_data["enum_str"] == "a"
        assert context.additional_data["enum_int"] == 42

    def test_decimal_conversion(self):
        """Test that Decimal values are converted to floats."""
        decimal_value = Decimal("123.456")
        context = ErrorContext(additional_data={"decimal_value": decimal_value})

        assert context.additional_data["decimal_value"] == 123.456
        assert isinstance(context.additional_data["decimal_value"], float)

    def test_mixed_types_conversion(self):
        """Test conversion of mixed types in additional_data."""

        class Status(Enum):
            PENDING = "pending"

        test_path = Path("/test/path")
        context = ErrorContext(
            additional_data={
                "str_val": "test",
                "int_val": 42,
                "path_val": test_path,
                "enum_val": Status.PENDING,
                "decimal_val": Decimal("99.99"),
            }
        )

        assert context.additional_data["str_val"] == "test"
        assert context.additional_data["int_val"] == 42
        assert context.additional_data["path_val"] == str(test_path)
        assert context.additional_data["enum_val"] == "pending"
        assert context.additional_data["decimal_val"] == 99.99

    def test_none_additional_data(self):
        """Test that None additional_data is preserved."""
        context = ErrorContext(additional_data=None)
        assert context.additional_data is None

    def test_invalid_dict_type_raises_error(self):
        """Test that non-dict additional_data raises TypeError via ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorContext(additional_data="not a dict")

        errors = exc_info.value.errors()
        # TypeError is now raised instead of ValueError
        assert any("additional_data must be dict" in str(err) for err in errors)

    def test_unconvertible_type_raises_error(self):
        """Test that unconvertible types raise TypeError."""

        class CustomClass:
            pass

        with pytest.raises(ValidationError) as exc_info:
            ErrorContext(additional_data={"custom": CustomClass()})

        errors = exc_info.value.errors()
        assert any("Cannot coerce" in str(err) for err in errors)

    def test_list_in_additional_data_raises_error(self):
        """Test that list values raise TypeError."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorContext(additional_data={"list_val": [1, 2, 3]})

        errors = exc_info.value.errors()
        assert any("Cannot coerce" in str(err) for err in errors)

    def test_dict_in_additional_data_raises_error(self):
        """Test that nested dict values raise TypeError."""
        with pytest.raises(ValidationError) as exc_info:
            ErrorContext(additional_data={"nested": {"key": "value"}})

        errors = exc_info.value.errors()
        assert any("Cannot coerce" in str(err) for err in errors)


class TestAniVaultError:
    """Test cases for base AniVaultError class."""

    def test_basic_error_creation(self):
        """Test creating a basic AniVaultError."""
        error = AniVaultError(ErrorCode.FILE_NOT_FOUND, "Test error message")

        assert error.code == ErrorCode.FILE_NOT_FOUND
        assert error.message == "Test error message"
        assert error.context is not None
        assert error.original_error is None

    def test_error_with_context(self):
        """Test creating AniVaultError with context."""
        context = ErrorContext(file_path="/test/path")
        error = AniVaultError(ErrorCode.PERMISSION_DENIED, "Permission denied", context)

        assert error.context == context
        assert error.context.file_path == "/test/path"

    def test_error_with_original_error(self):
        """Test creating AniVaultError with original error."""
        original = FileNotFoundError("Original error")
        error = AniVaultError(
            ErrorCode.FILE_NOT_FOUND, "File not found", original_error=original
        )

        assert error.original_error == original

    def test_str_representation(self):
        """Test string representation of AniVaultError."""
        error = AniVaultError(ErrorCode.VALIDATION_ERROR, "Validation failed")

        expected = "VALIDATION_ERROR: Validation failed"
        assert str(error) == expected

    def test_to_dict(self):
        """Test converting AniVaultError to dictionary with safe_dict PII masking."""
        context = ErrorContext(file_path="/test/path")
        original = ValueError("Original error")
        error = AniVaultError(
            ErrorCode.API_REQUEST_FAILED, "API request failed", context, original
        )

        result = error.to_dict()
        expected = {
            "code": "API_REQUEST_FAILED",
            "message": "API request failed",
            "context": context.safe_dict(),
            "original_error": "Original error",
        }
        assert result == expected

    def test_to_dict_masks_user_id(self):
        """Test that to_dict masks user_id via safe_dict."""
        context = ErrorContext(user_id="sensitive_user", file_path="/test/path")
        error = AniVaultError(ErrorCode.VALIDATION_ERROR, "Test error", context)

        result = error.to_dict()
        # user_id should be masked
        assert "user_id" not in result["context"]
        assert result["context"]["file_path"] == "/test/path"
        assert result["context"]["additional_data"] == {}

    def test_to_dict_without_original_error(self):
        """Test converting AniVaultError to dictionary without original error."""
        error = AniVaultError(ErrorCode.CONFIG_ERROR, "Configuration error")

        result = error.to_dict()
        assert result["original_error"] is None


class TestDomainError:
    """Test cases for DomainError class."""

    def test_domain_error_inheritance(self):
        """Test that DomainError inherits from AniVaultError."""
        error = DomainError(ErrorCode.VALIDATION_ERROR, "Business rule violation")

        assert isinstance(error, AniVaultError)
        assert isinstance(error, DomainError)
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.message == "Business rule violation"

    def test_domain_error_creation(self):
        """Test creating DomainError with context."""
        context = ErrorContext(operation="validate_data")
        error = DomainError(
            ErrorCode.INVALID_METADATA, "Invalid metadata format", context
        )

        assert error.context.operation == "validate_data"
        assert str(error) == "INVALID_METADATA: Invalid metadata format"


class TestInfrastructureError:
    """Test cases for InfrastructureError class."""

    def test_infrastructure_error_inheritance(self):
        """Test that InfrastructureError inherits from AniVaultError."""
        error = InfrastructureError(
            ErrorCode.NETWORK_ERROR, "Network connection failed"
        )

        assert isinstance(error, AniVaultError)
        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.NETWORK_ERROR
        assert error.message == "Network connection failed"

    def test_infrastructure_error_creation(self):
        """Test creating InfrastructureError with original error."""
        original = ConnectionError("Connection failed")
        error = InfrastructureError(
            ErrorCode.API_TIMEOUT, "API request timed out", original_error=original
        )

        assert error.original_error == original
        assert str(error) == "API_TIMEOUT: API request timed out"


class TestApplicationError:
    """Test cases for ApplicationError class."""

    def test_application_error_inheritance(self):
        """Test that ApplicationError inherits from AniVaultError."""
        error = ApplicationError(ErrorCode.CONFIG_ERROR, "Configuration error")

        assert isinstance(error, AniVaultError)
        assert isinstance(error, ApplicationError)
        assert error.code == ErrorCode.CONFIG_ERROR
        assert error.message == "Configuration error"

    def test_application_error_creation(self):
        """Test creating ApplicationError with context."""
        context = ErrorContext(additional_data={"config_key": "api_key"})
        error = ApplicationError(
            ErrorCode.CLI_INVALID_ARGUMENTS, "Invalid command line arguments", context
        )

        assert error.context.additional_data["config_key"] == "api_key"
        assert str(error) == "CLI_INVALID_ARGUMENTS: Invalid command line arguments"


class TestErrorConvenienceFunctions:
    """Test cases for error convenience functions."""

    def test_create_file_not_found_error(self):
        """Test create_file_not_found_error function."""
        error = create_file_not_found_error(
            "/test/file.txt", "read_file", FileNotFoundError("File not found")
        )

        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.FILE_NOT_FOUND
        assert error.message == "File not found: /test/file.txt"
        assert error.context.file_path == "/test/file.txt"
        assert error.context.operation == "read_file"
        assert isinstance(error.original_error, FileNotFoundError)

    def test_create_permission_denied_error(self):
        """Test create_permission_denied_error function."""
        error = create_permission_denied_error("/protected/path", "write_file")

        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.PERMISSION_DENIED
        assert error.message == "Permission denied: /protected/path"
        assert error.context.file_path == "/protected/path"
        assert error.context.operation == "write_file"

    def test_create_validation_error(self):
        """Test create_validation_error function."""
        error = create_validation_error(
            "Invalid email format", "email", "validate_user"
        )

        assert isinstance(error, DomainError)
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.message == "Invalid email format"
        assert error.context.operation == "validate_user"
        assert error.context.additional_data["field"] == "email"

    def test_create_api_error(self):
        """Test create_api_error function."""
        error = create_api_error(
            "API returned 500 error", "fetch_data", ConnectionError("Connection failed")
        )

        assert isinstance(error, InfrastructureError)
        assert error.code == ErrorCode.API_REQUEST_FAILED
        assert error.message == "API returned 500 error"
        assert error.context.operation == "fetch_data"
        assert isinstance(error.original_error, ConnectionError)

    def test_create_parsing_error(self):
        """Test create_parsing_error function."""
        error = create_parsing_error(
            "Failed to parse JSON", "/test/file.json", "parse_config"
        )

        assert isinstance(error, DomainError)
        assert error.code == ErrorCode.PARSING_ERROR
        assert error.message == "Failed to parse JSON"
        assert error.context.file_path == "/test/file.json"
        assert error.context.operation == "parse_config"

    def test_create_config_error(self):
        """Test create_config_error function."""
        error = create_config_error(
            "Missing required configuration", "database_url", "load_config"
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
            raise AniVaultError(ErrorCode.APPLICATION_ERROR, "Test error")

        assert exc_info.value.code == ErrorCode.APPLICATION_ERROR
        assert exc_info.value.message == "Test error"

    def test_raise_and_catch_domain_error(self):
        """Test raising and catching DomainError."""
        with pytest.raises(DomainError) as exc_info:
            raise DomainError(ErrorCode.BUSINESS_LOGIC_ERROR, "Business rule violation")

        assert exc_info.value.code == ErrorCode.BUSINESS_LOGIC_ERROR
        assert exc_info.value.message == "Business rule violation"

    def test_raise_and_catch_infrastructure_error(self):
        """Test raising and catching InfrastructureError."""
        with pytest.raises(InfrastructureError) as exc_info:
            raise InfrastructureError(
                ErrorCode.FILE_ACCESS_DENIED, "File access denied"
            )

        assert exc_info.value.code == ErrorCode.FILE_ACCESS_DENIED
        assert exc_info.value.message == "File access denied"

    def test_raise_and_catch_application_error(self):
        """Test raising and catching ApplicationError."""
        with pytest.raises(ApplicationError) as exc_info:
            raise ApplicationError(
                ErrorCode.CLI_COMMAND_FAILED, "Command execution failed"
            )

        assert exc_info.value.code == ErrorCode.CLI_COMMAND_FAILED
        assert exc_info.value.message == "Command execution failed"

    def test_catch_base_error_for_specific_errors(self):
        """Test catching base AniVaultError for specific error types."""
        try:
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Validation failed")
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
                ErrorCode.PARSING_ERROR, "Failed to parse data", original_error=original
            )
        except AniVaultError as e:
            assert e.original_error == original
            assert str(e.original_error) == "Original value error"
