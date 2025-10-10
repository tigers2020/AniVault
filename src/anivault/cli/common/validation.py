"""
Pydantic validation utilities for CLI commands.

This module provides reusable validation models and Typer callbacks
for consistent argument validation across CLI commands.

Enhanced validation functions integrate with error_messages module
for standardized error handling and reporting.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Callable

import typer
from pydantic import BaseModel, ValidationError, field_validator

from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext


def create_validator(model: type[BaseModel]) -> Callable[[Any], Any]:
    """
    Create a Typer callback function for Pydantic model validation.

    Args:
        model: Pydantic model class to validate against

    Returns:
        Typer callback function that validates input against the model

    Example:
        >>> validator = create_validator(DirectoryPath)
        >>> typer.Option(..., callback=validator)
    """

    def validator(value: Any) -> Any:
        """Validate value against the Pydantic model."""
        try:
            # Create model instance with the value
            if hasattr(model, "model_fields") and "path" in model.model_fields:
                instance = model(path=value)
                return getattr(instance, "path", value)
            instance = model(value=value)
            return getattr(instance, "value", value)
        except ValidationError as e:
            # Convert Pydantic validation error to Typer BadParameter
            error_messages = []
            for error in e.errors():
                field = error.get("loc", ("unknown",))[-1]
                message = error.get("msg", "Validation failed")
                error_messages.append(f"{field}: {message}")

            msg = f"Validation failed: {'; '.join(error_messages)}"
            raise typer.BadParameter(
                msg,
            ) from e
        except Exception as e:
            msg = f"Unexpected validation error: {e}"
            raise typer.BadParameter(msg) from e

    return validator


class NamingFormat(BaseModel):
    """Validated naming format string model."""

    value: str

    @field_validator("value", mode="before")
    @classmethod
    def validate_format_string(cls, v: Any) -> str:
        """Validate the naming format string."""
        if isinstance(v, dict):
            # Handle case where value is passed as dict
            if "format_string" in v:
                v = v["format_string"]
            elif "value" in v:
                v = v["value"]

        format_str = str(v)

        # Check for valid placeholders
        valid_placeholders = {
            "{series_name}",
            "{season}",
            "{episode}",
            "{title}",
            "{year}",
            "{quality}",
            "{resolution}",
            "{codec}",
        }

        # Find all placeholders in the format string (including format specifiers like :02d)
        placeholder_pattern = r"\{([^}:]+)(?::[^}]*)?\}"
        found_placeholders = set(re.findall(placeholder_pattern, format_str))
        # Convert to full placeholder format
        found_placeholders = {f"{{{p}}}" for p in found_placeholders}

        # Check for unclosed curly braces first
        open_braces = format_str.count("{")
        close_braces = format_str.count("}")
        if open_braces != close_braces:
            msg = f"Format string has mismatched braces: {open_braces} opening, {close_braces} closing"
            raise ValueError(
                msg,
            )

        # Check for invalid placeholders
        invalid_placeholders = found_placeholders - valid_placeholders
        if invalid_placeholders:
            msg = (
                f"Invalid placeholders found: {', '.join(sorted(invalid_placeholders))}. "
                f"Valid placeholders: {', '.join(sorted(valid_placeholders))}"
            )
            raise ValueError(
                msg,
            )

        # Check if at least one valid placeholder is present
        if not any(
            placeholder in valid_placeholders for placeholder in found_placeholders
        ):
            msg = (
                f"Format string must contain at least one valid placeholder. "
                f"Valid placeholders: {', '.join(sorted(valid_placeholders))}"
            )
            raise ValueError(
                msg,
            )

        return format_str


# ============================================================================
# Enhanced Validation Functions
# ============================================================================


def validate_directory_with_context(
    path_str: str | Path,
    operation: str,
) -> Path:
    """Validate directory path with proper error context.

    Args:
        path_str: Directory path to validate
        operation: Operation name for error context

    Returns:
        Validated Path object

    Raises:
        ApplicationError: If directory is invalid with proper error code

    Example:
        >>> directory = validate_directory_with_context(
        ...     "/path/to/anime",
        ...     "scan_files"
        ... )
    """
    path = Path(path_str)

    # Check if path exists
    if not path.exists():
        raise ApplicationError(
            ErrorCode.DIRECTORY_NOT_FOUND,
            f"Directory does not exist: {path}",
            ErrorContext(
                operation=operation,
                additional_data={"file_path": str(path)},
            ),
        )

    # Check if it's actually a directory
    if not path.is_dir():
        raise ApplicationError(
            ErrorCode.INVALID_PATH,
            f"Path is not a directory: {path}",
            ErrorContext(
                operation=operation,
                additional_data={"file_path": str(path)},
            ),
        )

    # Check if readable
    if not os.access(path, os.R_OK):
        raise ApplicationError(
            ErrorCode.FILE_PERMISSION_DENIED,
            f"Directory is not readable: {path}",
            ErrorContext(
                operation=operation,
                additional_data={"file_path": str(path)},
            ),
        )

    return path


def validate_file_path(
    path_str: str | Path,
    operation: str,
    must_exist: bool = True,
) -> Path:
    """Validate file path with proper error context.

    Args:
        path_str: File path to validate
        operation: Operation name for error context
        must_exist: Whether file must exist (default: True)

    Returns:
        Validated Path object

    Raises:
        ApplicationError: If file is invalid with proper error code

    Example:
        >>> file_path = validate_file_path(
        ...     "output.json",
        ...     "write_results",
        ...     must_exist=False
        ... )
    """
    path = Path(path_str)

    # Check existence if required
    if must_exist:
        if not path.exists():
            raise ApplicationError(
                ErrorCode.FILE_NOT_FOUND,
                f"File does not exist: {path}",
                ErrorContext(
                    operation=operation,
                    additional_data={"file_path": str(path)},
                ),
            )

        if not path.is_file():
            raise ApplicationError(
                ErrorCode.INVALID_PATH,
                f"Path is not a file: {path}",
                ErrorContext(
                    operation=operation,
                    additional_data={"file_path": str(path)},
                ),
            )

        # Check if readable
        if not os.access(path, os.R_OK):
            raise ApplicationError(
                ErrorCode.FILE_PERMISSION_DENIED,
                f"File is not readable: {path}",
                ErrorContext(
                    operation=operation,
                    additional_data={"file_path": str(path)},
                ),
            )

    # For output files, check if parent directory is writable
    else:
        parent = path.parent
        if not parent.exists():
            # Try to create parent directory
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ApplicationError(
                    ErrorCode.DIRECTORY_CREATION_FAILED,
                    f"Failed to create output directory: {parent}",
                    ErrorContext(
                        operation=operation,
                        additional_data={"file_path": str(parent)},
                    ),
                    original_error=e,
                ) from e

        # Check if writable
        if not os.access(parent, os.W_OK):
            raise ApplicationError(
                ErrorCode.FILE_PERMISSION_DENIED,
                f"Output directory is not writable: {parent}",
                ErrorContext(
                    operation=operation,
                    additional_data={"file_path": str(parent)},
                ),
            )

    return path


def ensure_json_mode_consistency(
    options: Any,
    operation: str,
) -> None:
    """Ensure JSON mode and console options are consistent.

    Validates that incompatible option combinations are not used together.

    Args:
        options: CLI options object with json_output attribute
        operation: Operation name for error context

    Raises:
        ApplicationError: If options are inconsistent

    Example:
        >>> ensure_json_mode_consistency(options, "organize_files")
    """
    # Check for conflicting flags
    if hasattr(options, "json_output") and hasattr(options, "verbose"):
        if options.json_output and options.verbose:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "Cannot use --json with --verbose (mutually exclusive)",
                ErrorContext(
                    operation=operation,
                    additional_data={
                        "json_output": options.json_output,
                        "verbose": options.verbose,
                    },
                ),
            )

    # Validate dry-run with yes flag
    if hasattr(options, "dry_run") and hasattr(options, "yes"):
        if options.dry_run and options.yes:
            raise ApplicationError(
                ErrorCode.VALIDATION_ERROR,
                "Cannot use --dry-run with --yes (--yes has no effect in dry-run mode)",
                ErrorContext(
                    operation=operation,
                    additional_data={
                        "dry_run": options.dry_run,
                        "yes": options.yes,
                    },
                ),
            )


def normalize_extensions_list(extensions: str | list[str]) -> list[str]:
    """Normalize file extensions to consistent format.

    Args:
        extensions: Comma-separated string or list of extensions

    Returns:
        List of normalized extensions (lowercase, with leading dot)

    Example:
        >>> normalize_extensions_list("mkv,MP4,avi")
        ['.mkv', '.mp4', '.avi']
        >>> normalize_extensions_list([".MKV", "mp4"])
        ['.mkv', '.mp4']
    """
    # Convert to list if string
    if isinstance(extensions, str):
        ext_list = [ext.strip() for ext in extensions.split(",")]
    else:
        ext_list = list(extensions)

    # Normalize each extension
    normalized = []
    for ext in ext_list:
        ext = ext.strip().lower()

        # Add leading dot if missing
        if ext and not ext.startswith("."):
            ext = f".{ext}"

        if ext:  # Skip empty strings
            normalized.append(ext)

    return normalized
