"""
CLI Error Handling Utilities

This module provides utilities for consistent error handling across CLI commands,
including standardized error output formatting and exception mapping.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

from anivault.shared.constants import CLIDefaults
from anivault.shared.errors import (
    AniVaultError,
    ApplicationError,
    CliError,
    ErrorCode,
    InfrastructureError,
    create_cli_error,
    create_cli_output_error,
)

logger = logging.getLogger(__name__)


def format_json_output(
    success: bool,
    command: str,
    errors: list[str] | None = None,
    data: dict[str, Any] | None = None,
) -> bytes:
    """Format error output as JSON.

    Args:
        success: Whether the operation was successful
        command: The command that was executed
        errors: List of error messages
        data: Additional data to include

    Returns:
        JSON-formatted bytes for output
    """
    output = {
        "success": success,
        "command": command,
        "timestamp": None,  # Will be set by calling code if needed
    }

    if errors:
        output["errors"] = errors

    if data:
        output["data"] = data

    return json.dumps(output, indent=2).encode("utf-8")


def handle_cli_error(
    error: Exception,
    command: str,
    json_output: bool = False,
) -> int:
    """Handle CLI errors with consistent formatting and logging.

    Args:
        error: The exception that occurred
        command: The CLI command being executed
        json_output: Whether to output JSON format

    Returns:
        Exit code for the CLI command
    """
    # Create structured error context for logging
    error_context = {
        "command": command,
        "error_type": type(error).__name__,
        "json_output": json_output,
    }

    # Map specific exception types to CLI errors
    if isinstance(error, CliError):
        cli_error = error
        error_context["error_code"] = cli_error.code.value
    elif isinstance(error, ApplicationError):
        cli_error = create_cli_error(
            message=f"Application error: {error.message}",
            command=command,
            original_error=error,
        )
        error_context["error_code"] = error.code.value
    elif isinstance(error, InfrastructureError):
        cli_error = create_cli_error(
            message=f"Infrastructure error: {error.message}",
            command=command,
            original_error=error,
        )
        error_context["error_code"] = error.code.value
    elif isinstance(error, (FileNotFoundError, PermissionError, OSError)):
        cli_error = create_cli_error(
            message=f"File system error: {error}",
            command=command,
            original_error=error,
        )
        error_context["error_category"] = "file_system"
    elif isinstance(error, (ValueError, KeyError, TypeError, AttributeError)):
        cli_error = create_cli_error(
            message=f"Data processing error: {error}",
            command=command,
            original_error=error,
        )
        error_context["error_category"] = "data_processing"
    elif isinstance(error, KeyboardInterrupt):
        cli_error = create_cli_error(
            message="Command interrupted by user",
            command=command,
            original_error=error,
            exit_code=130,  # Standard exit code for SIGINT
        )
        error_context["interrupt_type"] = "user_interrupt"
    else:
        # Handle unexpected errors with enhanced context
        cli_error = create_cli_error(
            message=f"Unexpected error: {error}",
            command=command,
            original_error=error,
        )
        error_context["error_category"] = "unexpected"

    # Log the error with structured context
    if isinstance(error, (KeyboardInterrupt, SystemExit)):
        # Don't log interrupts as exceptions
        logger.warning(
            "Command interrupted: %s",
            cli_error.message,
            extra={"context": error_context},
        )
    else:
        logger.exception(
            "CLI error in %s: %s",
            command,
            cli_error.message,
            extra={"context": error_context},
        )

    # Output error message
    if json_output:
        try:
            error_output = format_json_output(
                success=False,
                command=command,
                errors=[cli_error.message],
                data={
                    "error_code": cli_error.code.value,
                    "error_type": type(error).__name__,
                    "exit_code": cli_error.exit_code,
                    "context": error_context,
                },
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        except Exception as output_error:
            # Fallback to stderr if JSON output fails
            cli_output_error = create_cli_output_error(
                message=f"Failed to format JSON output: {output_error}",
                command=command,
                output_type="json",
                original_error=output_error,
            )
            logger.exception(
                "JSON output error: %s",
                cli_output_error.message,
                extra={"context": error_context},
            )
            sys.stderr.write(f"Error: {cli_error.message}\n")
            sys.stderr.write(f"JSON output failed: {cli_output_error.message}\n")
    else:
        # Text output
        sys.stderr.write(f"Error: {cli_error.message}\n")

    return cli_error.exit_code


def handle_specific_exceptions(
    error: Exception,
    command: str,
    json_output: bool = False,
) -> int:
    """Handle specific exception types with appropriate CLI error responses.

    Args:
        error: The exception that occurred
        command: The CLI command being executed
        json_output: Whether to output JSON format

    Returns:
        Exit code for the CLI command
    """
    if isinstance(error, AniVaultError):
        # AniVault errors already have proper context
        if isinstance(error, ApplicationError):
            logger.warning("Application error in %s: %s", command, error.message)
        elif isinstance(error, InfrastructureError):
            logger.error("Infrastructure error in %s: %s", command, error.message)

        if json_output:
            error_output = format_json_output(
                success=False,
                command=command,
                errors=[error.message],
                data={
                    "error_code": error.code.value,
                    "error_type": type(error).__name__,
                },
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            sys.stderr.write(f"Error: {error.message}\n")

        return CLIDefaults.EXIT_ERROR

    # Handle standard Python exceptions
    if isinstance(error, FileNotFoundError):
        error_msg = f"File not found: {error}"
        if json_output:
            error_output = format_json_output(
                success=False,
                command=command,
                errors=[error_msg],
                data={"error_code": ErrorCode.FILE_NOT_FOUND.value},
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            sys.stderr.write(f"Error: {error_msg}\n")
        return CLIDefaults.EXIT_ERROR

    if isinstance(error, PermissionError):
        error_msg = f"Permission denied: {error}"
        if json_output:
            error_output = format_json_output(
                success=False,
                command=command,
                errors=[error_msg],
                data={"error_code": ErrorCode.PERMISSION_DENIED.value},
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            sys.stderr.write(f"Error: {error_msg}\n")
        return CLIDefaults.EXIT_ERROR

    if isinstance(error, (ValueError, KeyError, TypeError, AttributeError)):
        error_msg = f"Data processing error: {error}"
        if json_output:
            error_output = format_json_output(
                success=False,
                command=command,
                errors=[error_msg],
                data={"error_code": ErrorCode.DATA_PROCESSING_ERROR.value},
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            sys.stderr.write(f"Error: {error_msg}\n")
        return CLIDefaults.EXIT_ERROR

    # Fallback for unexpected errors
    return handle_cli_error(error, command, json_output)


def log_cli_operation_success(
    command: str,
    duration_ms: float | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """Log successful CLI operation completion.

    Args:
        command: The CLI command that completed successfully
        duration_ms: Duration of the operation in milliseconds
        context: Additional context information
    """
    message = f"CLI command '{command}' completed successfully"
    if duration_ms is not None:
        message += f" in {duration_ms:.2f}ms"

    logger.info(message, extra={"context": context or {}})


def log_cli_operation_error(
    error: Exception,
    command: str,
    context: dict[str, Any] | None = None,
) -> None:
    """Log CLI operation error.

    Args:
        error: The exception that occurred
        command: The CLI command that failed
        context: Additional context information
    """
    if isinstance(error, AniVaultError):
        logger.error(
            "CLI command '%s' failed: %s",
            command,
            error.message,
            extra={
                "error_code": error.code.value,
                "context": context or {},
            },
        )
    else:
        logger.exception(
            "CLI command '%s' failed with unexpected error: %s",
            command,
            error,
            extra={"context": context or {}},
        )
