"""
CLI Utilities Module

This module provides common utility functions for the AniVault CLI.
It separates utility functions from the main CLI module to follow
the Single Responsibility Principle.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.theme import Theme

from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    InfrastructureError,
)


def setup_console(theme: Theme | None = None) -> Console:
    """
    Create and configure a Rich Console instance for CLI output.

    Args:
        theme: Optional Rich theme to apply

    Returns:
        Console: Configured Rich console instance

    Raises:
        ApplicationError: If console setup fails
    """
    try:
        # Default theme for AniVault CLI
        if theme is None:
            theme = Theme(
                {
                    "info": "cyan",
                    "warning": "yellow",
                    "error": "red",
                    "success": "green",
                    "bold": "bold white",
                    "dim": "dim white",
                },
            )

        console = Console(theme=theme)
        return console

    except Exception as e:
        raise ApplicationError(
            ErrorCode.CONFIGURATION_ERROR,
            f"Failed to setup console: {e}",
        ) from e


def validate_directory(directory_path: str) -> Path:
    """
    Validate that a directory path exists and is accessible.

    Args:
        directory_path: Path to validate

    Returns:
        Path: Validated directory path

    Raises:
        InfrastructureError: If directory is invalid or inaccessible
    """
    try:
        path = Path(directory_path)

        if not path.exists():
            raise InfrastructureError(
                ErrorCode.DIRECTORY_NOT_FOUND,
                f"Directory '{directory_path}' does not exist",
            )

        if not path.is_dir():
            raise InfrastructureError(
                ErrorCode.INVALID_PATH,
                f"'{directory_path}' is not a directory",
            )

        # Check read permissions
        if not os.access(path, os.R_OK):
            raise InfrastructureError(
                ErrorCode.PERMISSION_DENIED,
                f"No read permission for directory '{directory_path}'",
            )

        return path

    except InfrastructureError:
        raise
    except Exception as e:
        raise InfrastructureError(
            ErrorCode.VALIDATION_ERROR,
            f"Directory validation failed: {e}",
        ) from e


def display_error_message(console: Console, error: Any, context: str = "") -> None:
    """
    Display an error message using Rich console formatting.

    Args:
        console: Rich console instance
        error: Error object or message
        context: Additional context information
    """
    try:
        if isinstance(error, (ApplicationError, InfrastructureError)):
            # Use structured error information
            message = error.message
            if context:
                message = f"{message}\n\nContext: {context}"

            console.print(f"[error]Error: {message}[/error]")

            # Log additional context if available
            if hasattr(error, "context") and error.context:
                console.print(f"[dim]Additional details: {error.context}[/dim]")
        else:
            # Handle generic errors
            message = str(error)
            if context:
                message = f"{message}\n\nContext: {context}"

            console.print(f"[error]Error: {message}[/error]")

    except Exception:
        # Fallback to basic error display
        console.print(f"[error]Error: {error!s}[/error]")
        if context:
            console.print(f"[dim]Context: {context}[/dim]")


def display_success_message(
    console: Console,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Display a success message using Rich console formatting.

    Args:
        console: Rich console instance
        message: Success message to display
        details: Optional dictionary of additional details to display
    """
    try:
        console.print(f"[success]✓ {message}[/success]")

        if details:
            for key, value in details.items():
                console.print(f"[dim]  {key}: {value}[/dim]")

    except Exception:
        # Fallback to basic success display
        console.print(f"[green]✓ {message}[/green]")


def display_warning_message(
    console: Console,
    message: str,
    details: str | None = None,
) -> None:
    """
    Display a warning message using Rich console formatting.

    Args:
        console: Rich console instance
        message: Warning message to display
        details: Optional additional details
    """
    try:
        console.print(f"[warning]⚠ {message}[/warning]")

        if details:
            console.print(f"[dim]  {details}[/dim]")

    except Exception:
        # Fallback to basic warning display
        console.print(f"[yellow]⚠ {message}[/yellow]")


def display_info_message(
    console: Console,
    message: str,
    details: str | None = None,
) -> None:
    """
    Display an info message using Rich console formatting.

    Args:
        console: Rich console instance
        message: Info message to display
        details: Optional additional details
    """
    try:
        console.print(f"[info]i {message}[/info]")

        if details:
            console.print(f"[dim]  {details}[/dim]")

    except Exception:
        # Fallback to basic info display
        console.print(f"[cyan]i {message}[/cyan]")


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted file size string
    """
    try:
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1

        if i == 0:
            return f"{int(size)} {size_names[i]}"
        return f"{size:.1f} {size_names[i]}"

    except Exception:
        return f"{size_bytes} B"


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        str: Formatted duration string
    """
    try:
        if seconds < 60:
            return f"{seconds:.1f}s"
        if seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"

    except Exception:
        return f"{seconds:.1f}s"


def format_percentage(value: float, total: float) -> str:
    """
    Format percentage value.

    Args:
        value: Current value
        total: Total value

    Returns:
        str: Formatted percentage string
    """
    try:
        if total == 0:
            return "0.0%"

        percentage = (value / total) * 100
        return f"{percentage:.1f}%"

    except Exception:
        return "0.0%"


def ensure_directory_exists(directory_path: str) -> Path:
    """
    Ensure that a directory exists, creating it if necessary.

    Args:
        directory_path: Path to the directory

    Returns:
        Path: Directory path

    Raises:
        InfrastructureError: If directory creation fails
    """
    try:
        path = Path(directory_path)

        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        if not path.is_dir():
            raise InfrastructureError(
                ErrorCode.INVALID_PATH,
                f"'{directory_path}' is not a directory",
            )

        return path

    except InfrastructureError:
        raise
    except Exception as e:
        raise InfrastructureError(
            ErrorCode.DIRECTORY_CREATION_FAILED,
            f"Failed to create directory '{directory_path}': {e}",
        ) from e


def get_file_extension(file_path: str) -> str:
    """
    Get file extension from file path.

    Args:
        file_path: Path to the file

    Returns:
        str: File extension (including the dot)
    """
    try:
        return Path(file_path).suffix.lower()
    except Exception:
        return ""


def is_video_file(file_path: str, supported_extensions: list) -> bool:
    """
    Check if a file is a supported video file.

    Args:
        file_path: Path to the file
        supported_extensions: List of supported video extensions

    Returns:
        bool: True if file is a supported video file
    """
    try:
        extension = get_file_extension(file_path)
        return extension in supported_extensions
    except Exception:
        return False


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length of the result
        suffix: Suffix to add when truncating

    Returns:
        str: Truncated string
    """
    try:
        if len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    except Exception:
        return text


def safe_filename(filename: str) -> str:
    """
    Convert a string to a safe filename by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        str: Safe filename
    """
    try:
        # Define invalid characters for filenames
        invalid_chars = '<>:"/\\|?*'

        # Replace invalid characters with underscores
        safe_name = filename
        for char in invalid_chars:
            safe_name = safe_name.replace(char, "_")

        # Remove leading/trailing spaces and dots
        safe_name = safe_name.strip(" .")

        # Ensure it's not empty
        if not safe_name:
            safe_name = "unnamed"

        return safe_name

    except Exception:
        return "unnamed"
