"""CLI error handling decorator.

This module provides a decorator for standardizing error handling in CLI functions,
eliminating repetitive try-except blocks across command handlers.
"""

from __future__ import annotations

import functools
import logging
import sys
from typing import Any, Callable, TypeVar

from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants.cli import CLIFormatting, CLIMessages
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
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract options from args/kwargs to check for json_output
            options = _extract_options(args, kwargs)

            try:
                return func(*args, **kwargs)

            except ApplicationError as e:
                _handle_application_error(e, options, operation, command_name)

            except InfrastructureError as e:
                _handle_infrastructure_error(e, options, operation, command_name)

            except Exception as e:  # noqa: BLE001
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
        json_output = None

    return MockOptions()


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
    if options.json_output is not None:
        # JSON output mode
        json_output = format_json_output(
            success=False,
            command=command_name,
            errors=[f"{CLIMessages.Error.APPLICATION_ERROR}{error.message}"],
            data={
                CLIMessages.StatusKeys.ERROR_CODE: error.code,
                CLIMessages.StatusKeys.CONTEXT: error.context,
            },
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        # Rich console output
        from rich.console import Console

        console = Console()
        console.print(
            CLIFormatting.format_colored_message(
                f"Application error during {operation}: {error.message}",
                "error",
            ),
        )

    logger.exception(
        "%s in %s",
        CLIMessages.Error.APPLICATION_ERROR,
        operation,
        extra={
            CLIMessages.StatusKeys.CONTEXT: error.context,
            CLIMessages.StatusKeys.ERROR_CODE: error.code,
        },
    )

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
    if options.json_output is not None:
        # JSON output mode
        json_output = format_json_output(
            success=False,
            command=command_name,
            errors=[f"Infrastructure error: {error.message}"],
            data={
                CLIMessages.StatusKeys.ERROR_CODE: error.code,
                CLIMessages.StatusKeys.CONTEXT: error.context,
            },
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        # Rich console output
        from rich.console import Console

        console = Console()
        console.print(
            CLIFormatting.format_colored_message(
                f"Infrastructure error during {operation}: {error.message}",
                "error",
            ),
        )

    logger.exception(
        "Infrastructure error in %s",
        operation,
        extra={
            CLIMessages.StatusKeys.CONTEXT: error.context,
            CLIMessages.StatusKeys.ERROR_CODE: error.code,
        },
    )

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
    if options.json_output is not None:
        # JSON output mode
        json_output = format_json_output(
            success=False,
            command=command_name,
            errors=[f"Unexpected error: {error!s}"],
            data={
                CLIMessages.StatusKeys.ERROR_CODE: ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
            },
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        # Rich console output
        from rich.console import Console

        console = Console()
        console.print(
            CLIFormatting.format_colored_message(
                f"Unexpected error during {operation}: {error}",
                "error",
            ),
        )

    logger.exception(
        "%s during %s",
        CLIMessages.Error.UNEXPECTED_ERROR_DURING_VALIDATION,
        operation,
    )

    raise ApplicationError(
        ErrorCode.CLI_FILE_ORGANIZATION_FAILED,
        f"Failed during {operation}",
        ErrorContext(
            operation=operation,
            additional_data={"original_error": str(error)},
        ),
        original_error=error,
    ) from error

