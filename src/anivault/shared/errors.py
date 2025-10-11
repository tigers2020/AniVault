"""
AniVault Error Handling Module

This module defines the error handling system for AniVault, providing
structured error classes with context information and user-friendly messages.

The error hierarchy follows these principles:
- One Source of Truth: All error codes are defined in ErrorCode enum
- Structured Context: ErrorContext provides additional information
- User-friendly Messages: Errors can be converted to user-friendly messages
- Proper Exception Chaining: Original exceptions are preserved
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Union

from pydantic import ConfigDict, field_validator

from anivault.shared.types.base import BaseTypeModel

# Type alias for primitive context values (str, int, float, bool only)
PrimitiveContextValue = Union[str, int, float, bool]

# Default keys to mask in safe_dict for PII protection
SAFE_DICT_MASK_KEYS: tuple[str, ...] = ("user_id",)


class ErrorCode(str, Enum):
    """Error codes for AniVault application.

    This enum serves as the single source of truth for all error codes
    used throughout the application.
    """

    # File System Errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    DIRECTORY_NOT_FOUND = "DIRECTORY_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FILE_PERMISSION_DENIED = "FILE_PERMISSION_DENIED"
    INVALID_PATH = "INVALID_PATH"
    DIRECTORY_CREATION_FAILED = "DIRECTORY_CREATION_FAILED"
    FILE_ACCESS_DENIED = "FILE_ACCESS_DENIED"

    # Network and API Errors
    NETWORK_ERROR = "NETWORK_ERROR"
    API_RATE_LIMIT = "API_RATE_LIMIT"
    API_AUTHENTICATION_FAILED = "API_AUTHENTICATION_FAILED"
    API_REQUEST_FAILED = "API_REQUEST_FAILED"
    API_TIMEOUT = "API_TIMEOUT"
    API_SERVER_ERROR = "API_SERVER_ERROR"

    # TMDB API Specific Errors
    TMDB_API_CONNECTION_ERROR = "TMDB_API_CONNECTION_ERROR"
    TMDB_API_AUTHENTICATION_ERROR = "TMDB_API_AUTHENTICATION_ERROR"
    TMDB_API_RATE_LIMIT_EXCEEDED = "TMDB_API_RATE_LIMIT_EXCEEDED"
    TMDB_API_REQUEST_FAILED = "TMDB_API_REQUEST_FAILED"
    TMDB_API_TIMEOUT = "TMDB_API_TIMEOUT"
    TMDB_API_SERVER_ERROR = "TMDB_API_SERVER_ERROR"

    # File Grouping and Organization Errors
    FILE_GROUPING_FAILED = "FILE_GROUPING_FAILED"
    ORGANIZATION_PLAN_FAILED = "ORGANIZATION_PLAN_FAILED"
    RESOLUTION_DETECTION_FAILED = "RESOLUTION_DETECTION_FAILED"
    RESOLUTION_GROUPING_FAILED = "RESOLUTION_GROUPING_FAILED"
    RESOLUTION_COMPARISON_FAILED = "RESOLUTION_COMPARISON_FAILED"
    SUBTITLE_MATCHING_FAILED = "SUBTITLE_MATCHING_FAILED"
    SUBTITLE_GROUPING_FAILED = "SUBTITLE_GROUPING_FAILED"
    TMDB_API_INVALID_RESPONSE = "TMDB_API_INVALID_RESPONSE"
    TMDB_API_MEDIA_NOT_FOUND = "TMDB_API_MEDIA_NOT_FOUND"
    TMDB_API_INVALID_MEDIA_TYPE = "TMDB_API_INVALID_MEDIA_TYPE"

    # File System Errors
    FILE_ACCESS_ERROR = "FILE_ACCESS_ERROR"
    FILE_DELETE_ERROR = "FILE_DELETE_ERROR"
    FILE_CREATE_ERROR = "FILE_CREATE_ERROR"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    FILE_WRITE_ERROR = "FILE_WRITE_ERROR"

    # Validation Errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    INVALID_METADATA = "INVALID_METADATA"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    TYPE_COERCION_ERROR = "TYPE_COERCION_ERROR"

    # Parsing Errors
    PARSING_ERROR = "PARSING_ERROR"
    FILENAME_PARSE_FAILED = "FILENAME_PARSE_FAILED"
    METADATA_PARSE_FAILED = "METADATA_PARSE_FAILED"

    # Cache Errors
    CACHE_ERROR = "CACHE_ERROR"
    CACHE_READ_FAILED = "CACHE_READ_FAILED"
    CACHE_WRITE_FAILED = "CACHE_WRITE_FAILED"
    CACHE_CORRUPTION = "CACHE_CORRUPTION"
    CACHE_CORRUPTED = "CACHE_CORRUPTED"
    CACHE_SERIALIZATION_ERROR = "CACHE_SERIALIZATION_ERROR"

    # Configuration Errors
    CONFIG_ERROR = "CONFIG_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    MISSING_CONFIG = "MISSING_CONFIG"
    CONFIG_MISSING = "CONFIG_MISSING"  # Alias for consistency
    INVALID_CONFIG = "INVALID_CONFIG"
    CONFIG_INVALID = "CONFIG_INVALID"  # Alias for consistency

    # Security Errors
    INVALID_TOKEN = "INVALID_TOKEN"  # noqa: S105  # nosec B105 - Error code constant
    TOKEN_EXPIRED = "TOKEN_EXPIRED"  # noqa: S105  # nosec B105 - Error code constant
    TOKEN_MALFORMED = "TOKEN_MALFORMED"  # noqa: S105  # nosec B105 - Error code constant
    ENCRYPTION_FAILED = "ENCRYPTION_FAILED"
    DECRYPTION_FAILED = "DECRYPTION_FAILED"

    # Dependency Errors
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"
    DEPENDENCY_VERSION_MISMATCH = "DEPENDENCY_VERSION_MISMATCH"

    # Application Errors
    APPLICATION_ERROR = "APPLICATION_ERROR"
    UNKNOWN_COMMAND = "UNKNOWN_COMMAND"
    OPERATION_CANCELLED = "OPERATION_CANCELLED"
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"

    # CLI Errors
    INVALID_COMMAND = "INVALID_COMMAND"
    COMMAND_EXECUTION_FAILED = "COMMAND_EXECUTION_FAILED"
    CLI_COMMAND_FAILED = "CLI_COMMAND_FAILED"
    CLI_INVALID_ARGUMENTS = "CLI_INVALID_ARGUMENTS"
    CLI_CONFIGURATION_ERROR = "CLI_CONFIGURATION_ERROR"
    CLI_DIRECTORY_VALIDATION_FAILED = "CLI_DIRECTORY_VALIDATION_FAILED"
    CLI_SCAN_COMMAND_FAILED = "CLI_SCAN_COMMAND_FAILED"
    CLI_ORGANIZE_COMMAND_FAILED = "CLI_ORGANIZE_COMMAND_FAILED"
    CLI_MATCH_COMMAND_FAILED = "CLI_MATCH_COMMAND_FAILED"
    CLI_VERIFY_COMMAND_FAILED = "CLI_VERIFY_COMMAND_FAILED"
    CLI_ROLLBACK_COMMAND_FAILED = "CLI_ROLLBACK_COMMAND_FAILED"
    CLI_PIPELINE_EXECUTION_FAILED = "CLI_PIPELINE_EXECUTION_FAILED"
    CLI_METADATA_ENRICHMENT_FAILED = "CLI_METADATA_ENRICHMENT_FAILED"
    CLI_FILE_ORGANIZATION_FAILED = "CLI_FILE_ORGANIZATION_FAILED"
    CLI_ROLLBACK_EXECUTION_FAILED = "CLI_ROLLBACK_EXECUTION_FAILED"

    # CLI Entrypoint Errors
    CLI_UNEXPECTED_ERROR = "CLI_UNEXPECTED_ERROR"
    CLI_COMMAND_INTERRUPTED = "CLI_COMMAND_INTERRUPTED"
    CLI_OUTPUT_ERROR = "CLI_OUTPUT_ERROR"

    # Business Logic Errors
    BUSINESS_LOGIC_ERROR = "BUSINESS_LOGIC_ERROR"
    DATA_PROCESSING_ERROR = "DATA_PROCESSING_ERROR"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"

    # Rate Limiting and Concurrency Errors
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    CONCURRENCY_ERROR = "CONCURRENCY_ERROR"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    RESOURCE_CLEANUP_ERROR = "RESOURCE_CLEANUP_ERROR"

    # Infrastructure Errors
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"

    # Pipeline Errors
    PIPELINE_INITIALIZATION_ERROR = "PIPELINE_INITIALIZATION_ERROR"
    PIPELINE_EXECUTION_ERROR = "PIPELINE_EXECUTION_ERROR"
    PIPELINE_SHUTDOWN_ERROR = "PIPELINE_SHUTDOWN_ERROR"
    PIPELINE_COMPONENT_ERROR = "PIPELINE_COMPONENT_ERROR"
    QUEUE_OPERATION_ERROR = "QUEUE_OPERATION_ERROR"
    WORKER_POOL_ERROR = "WORKER_POOL_ERROR"
    SCANNER_ERROR = "SCANNER_ERROR"
    PARSER_ERROR = "PARSER_ERROR"
    COLLECTOR_ERROR = "COLLECTOR_ERROR"


class ErrorContextModel(BaseTypeModel):
    """Context information for errors.

    This class provides additional context information that helps
    with debugging and user-friendly error reporting.

    Uses Pydantic BaseTypeModel for type safety and automatic validation.
    Only primitive types (str, int, float, bool) are allowed in additional_data
    to ensure safe serialization and prevent sensitive data leakage.

    Attributes:
        file_path: Optional file path associated with the error
        operation: Optional operation name that caused the error
        user_id: Optional user ID (should be masked in logs)
        additional_data: Optional dict with primitive values only
    """

    model_config = ConfigDict(
        extra="forbid",  # Strict mode: reject unknown fields
        frozen=True,  # Immutable: cannot modify after creation
        populate_by_name=True,  # Accept both field names and aliases
        str_strip_whitespace=True,  # Auto-strip whitespace from strings
    )

    file_path: str | None = None
    operation: str | None = None
    user_id: str | None = None
    additional_data: dict[str, PrimitiveContextValue] | None = None

    @field_validator("additional_data", mode="before")
    @classmethod
    def _coerce_primitives(
        cls, value: dict[str, Any] | None
    ) -> dict[str, PrimitiveContextValue] | None:
        """Coerce additional_data values to primitives.

        Converts Path, Enum, Decimal to primitive types.
        Raises ValueError for unconvertible types (wrapped in ValidationError by Pydantic).

        Args:
            value: Input dictionary or None

        Returns:
            Dictionary with primitive values only, or None

        Raises:
            ValueError: If value is not a dict or contains unconvertible types
        """
        if value is None:
            return None

        if not isinstance(value, dict):
            error_msg = f"additional_data must be dict, got {type(value).__name__}"
            raise ValueError(error_msg)  # noqa: TRY004 - Pydantic validator pattern

        coerced: dict[str, PrimitiveContextValue] = {}
        for key, val in value.items():
            if isinstance(val, (str, int, float, bool)):
                coerced[key] = val
            elif isinstance(val, Path):
                coerced[key] = str(val)
            elif isinstance(val, Enum):
                coerced[key] = val.value
            elif isinstance(val, Decimal):
                coerced[key] = float(val)
            else:
                error_msg = (
                    f"Cannot coerce {type(val).__name__} to primitive type. "
                    f"Only str, int, float, bool, Path, Enum, Decimal are allowed."
                )
                raise ValueError(error_msg)  # noqa: TRY004 - Pydantic validator pattern

        return coerced

    def safe_dict(self, *, mask_keys: tuple[str, ...] | None = None) -> dict[str, Any]:
        """Export context as dict with PII masking.

        This method provides safe serialization for logging and error reporting
        by excluding sensitive fields and ensuring additional_data is never None.

        Args:
            mask_keys: Fields to exclude from output. Defaults to SAFE_DICT_MASK_KEYS.1

        Returns:
            Dictionary with masked sensitive fields and guaranteed additional_data key.

        Example:
            >>> context = ErrorContext(user_id="12345", file_path="/test")
            >>> context.safe_dict()
            {'file_path': '/test', 'operation': None, 'additional_data': {}}
            >>> # user_id is masked by default
        """
        if mask_keys is None:
            mask_keys = SAFE_DICT_MASK_KEYS

        data = self.model_dump(mode="python", exclude_none=True, exclude=set(mask_keys))

        # Ensure additional_data is always present (never None) for consumers
        if "additional_data" not in data or data.get("additional_data") is None:
            data["additional_data"] = {}

        return data


# Legacy alias for backwards compatibility
# NOTE: Deprecated - Use ErrorContextModel directly in new code
ErrorContext = ErrorContextModel


class AniVaultError(Exception):
    """Base exception class for all AniVault errors.

    This class provides the foundation for all custom errors in the
    AniVault application, following the structured error handling pattern.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        context: ErrorContext | None = None,
        original_error: Exception | None = None,
    ) -> None:
        """Initialize AniVaultError.

        Args:
            code: Error code from ErrorCode enum
            message: Human-readable error message
            context: Additional context information
            original_error: Original exception that caused this error
        """
        self.code = code
        self.message = message
        self.context = context or ErrorContext()
        self.original_error = original_error

        # Create formatted error message
        formatted_message = f"{code.value}: {message}"
        super().__init__(formatted_message)

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"{self.code.value}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for logging with PII masking.

        Uses ErrorContextModel.safe_dict() for automatic serialization
        with sensitive field masking (e.g., user_id).

        Returns:
            Dictionary representation of the error with code, message,
            masked context, and original_error (if present)
        """
        return {
            "code": self.code.value,
            "message": self.message,
            "context": self.context.safe_dict(),
            "original_error": str(self.original_error) if self.original_error else None,
        }


class DomainError(AniVaultError):
    """Domain-specific errors.

    These errors occur when business logic rules are violated
    or domain constraints are not met.

    Examples:
    - Invalid file format for anime files
    - Metadata parsing failures
    - Business rule violations
    """


class InfrastructureError(AniVaultError):
    """Infrastructure-related errors.

    These errors occur when interacting with external systems
    like file system, network, APIs, or databases.

    Examples:
    - File not found
    - Network connection failures
    - API authentication errors
    - Permission denied
    """


class ApplicationError(AniVaultError):
    """Application-level errors.

    These errors occur at the application layer, typically
    related to configuration, command handling, or application flow.

    Examples:
    - Invalid command line arguments
    - Configuration errors
    - Application state errors
    """


class DataProcessingError(AniVaultError):
    """Data processing errors.

    These errors occur during data manipulation, parsing,
    or business logic processing.

    Examples:
    - Data parsing failures
    - Business rule violations
    - Data validation errors
    - KeyError, ValueError, TypeError during data processing
    """


class SecurityError(AniVaultError):
    """Security-related errors.

    These errors occur when security constraints are violated,
    secrets are missing, or authentication/authorization fails.

    Examples:
    - Missing API keys or secrets
    - Invalid authentication credentials
    - Permission denied
    - Security configuration errors
    - Encryption/decryption failures
    """


# Convenience functions for common error scenarios
def create_file_not_found_error(
    file_path: str,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> InfrastructureError:
    """Create a file not found error with context."""
    context = ErrorContext(
        file_path=file_path,
        operation=operation,
    )
    return InfrastructureError(
        ErrorCode.FILE_NOT_FOUND,
        f"File not found: {file_path}",
        context,
        original_error,
    )


def create_permission_denied_error(
    path: str,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> InfrastructureError:
    """Create a permission denied error with context."""
    context = ErrorContext(
        file_path=path,
        operation=operation,
    )
    return InfrastructureError(
        ErrorCode.PERMISSION_DENIED,
        f"Permission denied: {path}",
        context,
        original_error,
    )


def create_validation_error(
    message: str,
    field: str | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> DomainError:
    """Create a validation error with context."""
    additional_data: dict[str, PrimitiveContextValue] | None = (
        {"field": field} if field else None
    )
    context = ErrorContext(
        operation=operation,
        additional_data=additional_data,
    )
    return DomainError(
        ErrorCode.VALIDATION_ERROR,
        message,
        context,
        original_error,
    )


def create_api_error(
    message: str,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> InfrastructureError:
    """Create an API error with context."""
    context = ErrorContext(
        operation=operation,
    )
    return InfrastructureError(
        ErrorCode.API_REQUEST_FAILED,
        message,
        context,
        original_error,
    )


def create_parsing_error(
    message: str,
    file_path: str | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> DomainError:
    """Create a parsing error with context."""
    context = ErrorContext(
        file_path=file_path,
        operation=operation,
    )
    return DomainError(
        ErrorCode.PARSING_ERROR,
        message,
        context,
        original_error,
    )


def create_config_error(
    message: str,
    config_key: str | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> ApplicationError:
    """Create a configuration error with context."""
    additional_data: dict[str, PrimitiveContextValue] | None = (
        {"config_key": config_key} if config_key else None
    )
    context = ErrorContext(
        operation=operation,
        additional_data=additional_data,
    )
    return ApplicationError(
        ErrorCode.CONFIG_ERROR,
        message,
        context,
        original_error,
    )


def create_data_processing_error(
    message: str,
    field: str | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> DataProcessingError:
    """Create a data processing error with context."""
    additional_data: dict[str, PrimitiveContextValue] | None = (
        {"field": field} if field else None
    )
    context = ErrorContext(
        operation=operation,
        additional_data=additional_data,
    )
    return DataProcessingError(
        ErrorCode.DATA_PROCESSING_ERROR,
        message,
        context,
        original_error,
    )


class CliError(ApplicationError):
    """CLI-specific error with enhanced context for command-line operations."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        context: ErrorContext | None = None,
        original_error: Exception | None = None,
        command: str | None = None,
        exit_code: int = 1,
    ):
        super().__init__(code, message, context, original_error)
        self.command = command
        self.exit_code = exit_code


def create_cli_error(
    message: str,
    command: str | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
    exit_code: int = 1,
) -> CliError:
    """Create a CLI error with context."""
    additional_data: dict[str, PrimitiveContextValue] | None = (
        {"command": command} if command else None
    )
    context = ErrorContext(
        operation=operation,
        additional_data=additional_data,
    )
    return CliError(
        ErrorCode.CLI_UNEXPECTED_ERROR,
        message,
        context,
        original_error,
        command,
        exit_code,
    )


def create_cli_output_error(
    message: str,
    command: str | None = None,
    output_type: str | None = None,
    original_error: Exception | None = None,
) -> CliError:
    """Create a CLI output error with context."""
    additional_data: dict[str, PrimitiveContextValue] = {}
    if command is not None:
        additional_data["command"] = command
    if output_type is not None:
        additional_data["output_type"] = output_type

    context = ErrorContext(
        operation="cli_output",
        additional_data=additional_data if additional_data else None,
    )
    return CliError(
        ErrorCode.CLI_OUTPUT_ERROR,
        message,
        context,
        original_error,
        command,
        exit_code=1,
    )


class TypeCoercionError(DomainError):
    """Exception raised when type conversion/coercion fails.

    This exception wraps Pydantic ValidationError and provides
    structured context for debugging type conversion failures.

    Attributes:
        code: Error code (TYPE_COERCION_ERROR)
        message: Human-readable error message
        context: ErrorContext with model and data details
        original_error: Original Pydantic ValidationError
        model_name: Name of the target Pydantic model
        validation_errors: List of field-level validation errors

    Example:
        >>> from pydantic import ValidationError
        >>> try:
        ...     # Conversion attempt
        ...     pass
        ... except ValidationError as e:
        ...     raise TypeCoercionError(
        ...         code=ErrorCode.TYPE_COERCION_ERROR,
        ...         message="Failed to convert dict to TMDBGenre",
        ...         context=ErrorContext(operation="dict_to_model"),
        ...         original_error=e,
        ...         model_name="TMDBGenre",
        ...         validation_errors=e.errors()
        ...     )
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        context: ErrorContext | None = None,
        original_error: Exception | None = None,
        model_name: str | None = None,
        validation_errors: list[dict[str, Any]] | None = None,
    ):
        """Initialize TypeCoercionError.

        Args:
            code: Error code
            message: Error message
            context: Error context
            original_error: Original exception
            model_name: Target model class name
            validation_errors: Pydantic validation error details
        """
        super().__init__(code, message, context, original_error)
        self.model_name = model_name
        self.validation_errors = validation_errors or []


def create_type_coercion_error(
    message: str,
    model_name: str,
    validation_errors: list[dict[str, Any]] | None = None,
    operation: str | None = None,
    original_error: Exception | None = None,
) -> TypeCoercionError:
    """Create a type coercion error with context.

    Args:
        message: Error message
        model_name: Target Pydantic model name
        validation_errors: Pydantic validation error details
        operation: Operation being performed
        original_error: Original ValidationError

    Returns:
        TypeCoercionError instance

    Example:
        >>> from pydantic import ValidationError
        >>> try:
        ...     # Validation
        ...     pass
        ... except ValidationError as e:
        ...     error = create_type_coercion_error(
        ...         message="Invalid data for TMDBGenre",
        ...         model_name="TMDBGenre",
        ...         validation_errors=e.errors(),
        ...         operation="dict_to_model",
        ...         original_error=e
        ...     )
    """
    additional_data: dict[str, PrimitiveContextValue] = {
        "model_name": model_name,
        "validation_error_count": len(validation_errors) if validation_errors else 0,
    }
    context = ErrorContext(
        operation=operation or "type_conversion",
        additional_data=additional_data,
    )
    return TypeCoercionError(
        code=ErrorCode.TYPE_COERCION_ERROR,
        message=message,
        context=context,
        original_error=original_error,
        model_name=model_name,
        validation_errors=validation_errors,
    )
