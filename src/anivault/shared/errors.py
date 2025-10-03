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

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """Error codes for AniVault application.

    This enum serves as the single source of truth for all error codes
    used throughout the application.
    """

    # File System Errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    DIRECTORY_NOT_FOUND = "DIRECTORY_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
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
    INVALID_CONFIG = "INVALID_CONFIG"

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

    # Business Logic Errors
    BUSINESS_LOGIC_ERROR = "BUSINESS_LOGIC_ERROR"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"

    # Rate Limiting and Concurrency Errors
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    CONCURRENCY_ERROR = "CONCURRENCY_ERROR"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    RESOURCE_CLEANUP_ERROR = "RESOURCE_CLEANUP_ERROR"

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


@dataclass
class ErrorContext:
    """Context information for errors.

    This class provides additional context information that helps
    with debugging and user-friendly error reporting.
    """

    file_path: str | None = None
    operation: str | None = None
    user_id: str | None = None
    additional_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging."""
        return {
            "file_path": self.file_path,
            "operation": self.operation,
            "user_id": self.user_id,
            "additional_data": self.additional_data,
        }


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
        """Convert error to dictionary for logging."""
        return {
            "code": self.code.value,
            "message": self.message,
            "context": self.context.to_dict(),
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
    additional_data = {"field": field} if field else None
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
    additional_data = {"config_key": config_key} if config_key else None
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
