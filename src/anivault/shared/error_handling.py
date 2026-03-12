"""Shared error handling utilities for AniVault.

This module provides common error handling functions used across CLI and GUI layers,
eliminating code duplication and ensuring consistent error handling patterns.

Design Principles:
- One Source of Truth for error handling logic
- Type-safe error mapping and conversion
- Consistent logging and output formatting
- Support for both CLI and GUI error handling
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, TypeVar

from anivault.shared.errors import (
    AniVaultError,
    ApplicationError,
    ErrorCode,
    ErrorContextModel,
    InfrastructureError,
)

logger = logging.getLogger(__name__)


def map_exception_to_anivault_error(
    error: Exception,
    operation: str,
    default_code: ErrorCode = ErrorCode.PIPELINE_EXECUTION_ERROR,
) -> AniVaultError:
    """Map a generic exception to an AniVaultError.

    This function provides a unified way to convert standard Python exceptions
    and other errors into AniVault's structured error types.

    Args:
        error: The exception to map
        operation: Operation name where error occurred
        default_code: Default error code if mapping fails

    Returns:
        AniVaultError instance (ApplicationError or InfrastructureError)

    Example:
        >>> try:
        ...     process_file(path)
        ... except FileNotFoundError as e:
        ...     error = map_exception_to_anivault_error(e, "process_file")
        ...     # Returns InfrastructureError with FILE_NOT_FOUND code
    """
    # Already an AniVaultError, return as-is
    if isinstance(error, AniVaultError):
        return error

    # Map standard exceptions to appropriate error types
    context = ErrorContextModel(
        operation=operation,
        additional_data={"original_error_type": type(error).__name__},
    )

    if isinstance(error, (FileNotFoundError, PermissionError, OSError)):
        return InfrastructureError(
            code=ErrorCode.FILE_NOT_FOUND if isinstance(error, FileNotFoundError) else ErrorCode.PERMISSION_DENIED,
            message=f"File system error: {error}",
            context=context,
            original_error=error,
        )

    if isinstance(error, (ValueError, KeyError, TypeError, AttributeError)):
        return ApplicationError(
            code=ErrorCode.DATA_PROCESSING_ERROR,
            message=f"Data processing error: {error}",
            context=context,
            original_error=error,
        )

    if isinstance(error, KeyboardInterrupt):
        return ApplicationError(
            code=ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
            message="Operation interrupted by user",
            context=context,
            original_error=error,
        )

    # Fallback: wrap as InfrastructureError
    return InfrastructureError(
        code=default_code,
        message=f"Unexpected error: {error}",
        context=context,
        original_error=error,
    )


def log_error_with_context(
    error: AniVaultError,
    operation: str,
    additional_context: dict[str, Any] | None = None,
) -> None:
    """Log an AniVaultError with structured context.

    Args:
        error: AniVaultError instance to log
        operation: Operation name where error occurred
        additional_context: Additional context data for logging
    """
    log_context: dict[str, Any] = {
        "operation": operation,
        "error_code": error.code.value,
        "error_type": type(error).__name__,
    }

    if additional_context:
        log_context.update(additional_context)

    if isinstance(error, ApplicationError):
        logger.warning(
            "Application error in %s: %s",
            operation,
            error.message,
            extra={"context": log_context},
        )
    elif isinstance(error, InfrastructureError):
        logger.error(
            "Infrastructure error in %s: %s",
            operation,
            error.message,
            extra={"context": log_context},
        )
    else:
        logger.exception(
            "AniVault error in %s: %s",
            operation,
            error.message,
            extra={"context": log_context},
        )


def create_error_context(
    operation: str,
    file_path: str | None = None,
    additional_data: dict[str, Any] | None = None,
) -> ErrorContextModel:
    """Create ErrorContextModel with common fields.

    Args:
        operation: Operation name
        file_path: Optional file path
        additional_data: Optional additional data

    Returns:
        ErrorContextModel instance
    """
    return ErrorContextModel(
        operation=operation,
        file_path=file_path,
        additional_data=additional_data,
    )


def _apply_file_path_to_context(
    error: AniVaultError,
    file_path: str,
) -> AniVaultError:
    """Return a new error with context updated to include file_path."""
    if not error.context:
        return error
    updated_context = ErrorContextModel(
        operation=error.context.operation,
        file_path=file_path,
        user_id=error.context.user_id,
        additional_data=error.context.additional_data,
    )
    if isinstance(error, ApplicationError):
        return ApplicationError(
            code=error.code,
            message=error.message,
            context=updated_context,
            original_error=error.original_error,
        )
    if isinstance(error, InfrastructureError):
        return InfrastructureError(
            code=error.code,
            message=error.message,
            context=updated_context,
            original_error=error.original_error,
        )
    return error


def _handle_anivault_error_in_decorator(
    error: AniVaultError,
    operation: str,
    file_path: str | None,
    reraise: bool,
) -> None:
    """Log AniVaultError and optionally re-raise. Returns None otherwise."""
    additional_ctx = {"file_path": file_path} if file_path else None
    log_error_with_context(error, operation, additional_context=additional_ctx)
    if reraise:
        raise error


def _handle_generic_error_in_decorator(
    error: Exception,
    operation: str,
    file_path: str | None,
    default_code: ErrorCode,
    reraise: bool,
) -> None:
    """Map exception to AniVaultError, optionally add file_path, log, and re-raise or return."""
    mapped = map_exception_to_anivault_error(error, operation, default_code=default_code)
    if file_path:
        mapped = _apply_file_path_to_context(mapped, file_path)
    log_error_with_context(mapped, operation)
    if reraise:
        raise mapped from error


F = TypeVar("F", bound=Callable[..., Any])


def handle_operation_errors(
    operation: str,
    *,
    file_path: str | None = None,
    default_code: ErrorCode = ErrorCode.APPLICATION_ERROR,
    reraise: bool = False,
) -> Callable[[F], F]:
    """Decorator for consistent error handling in operations.

    This decorator provides a standardized way to handle exceptions
    across GUI and Core modules, reducing code duplication.

    Args:
        operation: Operation name for error context
        file_path: Optional file path for error context
        default_code: Default error code if mapping fails
        reraise: Whether to re-raise the mapped error (default: False)

    Returns:
        Decorator function

    Example:
        >>> @handle_operation_errors(operation="process_file", file_path="/path/to/file")
        ... def process_file(path: Path) -> bool:
        ...     # Operation code - errors are automatically handled
        ...     return True
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except AniVaultError as e:
                _handle_anivault_error_in_decorator(e, operation, file_path, reraise)
                return None
            except Exception as e:  # noqa: BLE001 - decorator intentionally maps all exceptions to AniVaultError
                _handle_generic_error_in_decorator(e, operation, file_path, default_code, reraise)
                return None

        return wrapper  # type: ignore[return-value]

    return decorator
