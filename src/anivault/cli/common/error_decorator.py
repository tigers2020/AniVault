"""CLI error handling decorator.

This module provides a decorator for standardizing error handling in CLI functions,
eliminating repetitive try-except blocks across command handlers.

Refactored to use error_messages module for unified output formatting.
"""

from __future__ import annotations

import functools
import logging
import sys
from typing import Any, Callable, TypeVar

from rich.console import Console

from anivault.cli.common.error_messages import (
    ErrorMessageContext,
    build_console_message,
    build_json_payload,
    build_log_context,
)
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def handle_cli_errors(
    operation: str,
    command_name: str = "organize",
) -> Callable[[F], F]:
    """Decorator for standardized CLI error handling.

    This decorator wraps CLI functions to handle ApplicationError,
    InfrastructureError, and unexpected exceptions consistently,
    reducing code duplication across command handlers.

    The decorator:
    1. Catches ApplicationError, InfrastructureError, and generic exceptions
    2. Formats errors appropriately for JSON or Rich console output
    3. Logs errors with proper context
    4. Re-raises errors with CLI-specific error codes

    Args:
        operation: Operation name for error context (e.g., "get_scanned_files")
        command_name: CLI command name (default: "organize")

    Returns:
        Decorated function with error handling

    Example:
        >>> @handle_cli_errors(operation="scan_files", command_name="organize")
        ... def _get_scanned_files(options, directory, console):
        ...     return run_pipeline(...)  # No try-except needed!
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:  # pylint: disable=inconsistent-return-statements
            # Extract options from args/kwargs to check for json_output
            options = _extract_options(args, kwargs)

            try:
                return func(*args, **kwargs)

            except ApplicationError as e:
                _handle_application_error(e, options, operation, command_name)

            except InfrastructureError as e:
                _handle_infrastructure_error(e, options, operation, command_name)

            # pylint: disable-next=broad-exception-caught

            # pylint: disable-next=broad-exception-caught

            except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                # Must catch all exceptions to provide user-friendly CLI error messages
                _handle_unexpected_error(e, options, operation, command_name)

        return wrapper  # type: ignore[return-value]

    return decorator


def _extract_options(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    """Extract OrganizeOptions from function arguments.

    Args:
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        OrganizeOptions instance or object with json_output attribute
    """
    # Try to find options in args (usually first argument)
    for arg in args:
        if hasattr(arg, "json_output"):
            return arg

    # Try to find in kwargs
    if "options" in kwargs and hasattr(kwargs["options"], "json_output"):
        return kwargs["options"]

    # Fallback: Create mock options with json_output=None
    class MockOptions:
        """Mock options object for error decorator fallback.

        Used when json_output option is not available in the function arguments.
        """

        json_output = None

    return MockOptions()


def _output_error_message(
    context: ErrorMessageContext,
    options: Any,
) -> None:
    """Output error message to JSON or Rich console.

    Args:
        context: Error message context
        options: CLI options (for json_output check)
    """
    if options.json_output is not None:
        # JSON output mode
        payload = build_json_payload(context)
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        # Rich console output mode

        console = Console()
        message = build_console_message(context)
        console.print(message, markup=False)


def _handle_application_error(
    error: ApplicationError,
    options: Any,
    operation: str,
    command_name: str,
) -> None:
    """Handle ApplicationError consistently.

    Args:
        error: ApplicationError instance
        options: CLI options (for json_output check)
        operation: Operation name
        command_name: Command name

    Raises:
        ApplicationError: Always re-raises with CLI-specific error code
    """
    # Create error message context
    context = ErrorMessageContext(
        error=error,
        operation=operation,
        command_name=command_name,
    )

    # Output error message (JSON or Rich console)
    _output_error_message(context, options)

    # Log with structured context
    log_context = build_log_context(context)
    logger.exception(
        "Application error in %s",
        operation,
        extra=log_context,
    )

    # Re-raise with CLI-specific error code
    raise ApplicationError(
        ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
        f"Failed during {operation}",
        ErrorContext(
            operation=operation,
            additional_data={"original_error": str(error)},
        ),
        original_error=error,
    ) from error


def _handle_infrastructure_error(
    error: InfrastructureError,
    options: Any,
    operation: str,
    command_name: str,
) -> None:
    """Handle InfrastructureError consistently.

    Args:
        error: InfrastructureError instance
        options: CLI options (for json_output check)
        operation: Operation name
        command_name: Command name

    Raises:
        InfrastructureError: Always re-raises with CLI-specific error code
    """
    # Create error message context
    context = ErrorMessageContext(
        error=error,
        operation=operation,
        command_name=command_name,
    )

    # Output error message (JSON or Rich console)
    _output_error_message(context, options)

    # Log with structured context
    log_context = build_log_context(context)
    logger.exception(
        "Infrastructure error in %s",
        operation,
        extra=log_context,
    )

    # Re-raise with CLI-specific error code
    raise InfrastructureError(
        ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
        f"Failed during {operation}",
        ErrorContext(
            operation=operation,
            additional_data={"original_error": str(error)},
        ),
        original_error=error,
    ) from error


def _handle_unexpected_error(
    error: Exception,
    options: Any,
    operation: str,
    command_name: str,
) -> None:
    """Handle unexpected exceptions consistently.

    Args:
        error: Generic Exception
        options: CLI options (for json_output check)
        operation: Operation name
        command_name: Command name

    Raises:
        ApplicationError: Always re-raises as ApplicationError
    """
    # Create error message context
    context = ErrorMessageContext(
        error=error,
        operation=operation,
        command_name=command_name,
    )

    # Output error message (JSON or Rich console)
    _output_error_message(context, options)

    # Log with structured context
    log_context = build_log_context(context)
    logger.exception(
        "Unexpected error during %s",
        operation,
        extra=log_context,
    )

    # Re-raise as ApplicationError with CLI-specific error code
    raise ApplicationError(
        ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
        f"Failed during {operation}",
        ErrorContext(
            operation=operation,
            additional_data={"original_error": str(error)},
        ),
        original_error=error,
    ) from error
