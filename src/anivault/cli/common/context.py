"""
CLI Context Management Module

This module provides a centralized system for managing global CLI state
using Pydantic models and ContextVar. It ensures type safety and thread-safe
access to shared configuration across all Typer commands.

The context includes:
- verbose: Verbosity level (int, count-based)
- log_level: Logging level (str, enum-based)
- json_output: JSON output mode (bool)
"""

from __future__ import annotations

import contextvars
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    """Log level enumeration for type safety."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CliContext(BaseModel):
    """
    CLI context model for managing global state.

    This model holds all shared configuration that needs to be accessed
    across different Typer commands. It provides type safety and validation
    through Pydantic.

    Attributes:
        verbose: Verbosity level (0 = normal, 1+ = verbose)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Whether to output in JSON format
        benchmark: Whether benchmark mode is enabled
    """

    verbose: int = Field(
        default=0,
        ge=0,
        description="Verbosity level (0 = normal, 1+ = verbose)",
    )

    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level",
    )

    json_output: bool = Field(
        default=False,
        description="Whether to output in JSON format",
    )

    benchmark: bool = Field(
        default=False,
        description="Whether benchmark mode is enabled",
    )

    def is_verbose(self) -> bool:
        """Check if verbose mode is enabled."""
        return self.verbose > 0

    def get_effective_log_level(self) -> str:
        """
        Get the effective log level after applying verbose override.

        If verbose is enabled, force log level to DEBUG.

        Returns:
            str: Effective log level
        """
        if self.is_verbose():
            return LogLevel.DEBUG.value
        return self.log_level.value

    def is_json_output_enabled(self) -> bool:
        """Check if JSON output is enabled."""
        return self.json_output

    def is_verbose_output_enabled(self) -> bool:
        """Check if verbose output is enabled."""
        return self.is_verbose()

    def is_benchmark_enabled(self) -> bool:
        """Check if benchmark mode is enabled."""
        return self.benchmark


def validate_directory(directory_path: str) -> Path:
    """
    Validate that the given path is a valid directory.

    Args:
        directory_path: Path to validate

    Returns:
        Path: Validated Path object

    Raises:
        ApplicationError: If directory is invalid
    """
    from pathlib import Path

    from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

    # Handle DirectoryPath objects
    if hasattr(directory_path, "path"):
        directory_path = directory_path.path

    path = Path(directory_path)

    if not path.exists():
        raise ApplicationError(
            ErrorCode.FILE_NOT_FOUND,
            f"Directory does not exist: {path}",
            ErrorContext(
                operation="validate_directory",
                additional_data={"path": str(path)},
            ),
        )

    if not path.is_dir():
        raise ApplicationError(
            ErrorCode.VALIDATION_ERROR,
            f"Path is not a directory: {path}",
            ErrorContext(
                operation="validate_directory",
                additional_data={"path": str(path)},
            ),
        )

    return path


# Global context variable for thread-safe access
cli_context_var: contextvars.ContextVar[CliContext | None] = contextvars.ContextVar(
    "cli_context",
    default=None,
)


def get_cli_context() -> CliContext:
    """
    Get the current CLI context.

    This function provides a clean and typed API for command functions
    to access global settings. It returns a default context if none
    has been set.

    Returns:
        CliContext: Current CLI context

    Raises:
        RuntimeError: If context has not been initialized
    """
    context = cli_context_var.get()
    if context is None:
        raise RuntimeError(
            "CLI context has not been initialized. "
            "Make sure to call the main callback before accessing context.",
        )
    return context


def set_cli_context(context: CliContext) -> None:
    """
    Set the current CLI context.

    This function is typically called by the main callback to initialize
    the global context with parsed command-line options.

    Args:
        context: The CLI context to set
    """
    cli_context_var.set(context)


def clear_cli_context() -> None:
    """Clear the current CLI context."""
    cli_context_var.set(None)
