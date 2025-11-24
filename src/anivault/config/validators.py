"""Common validation functions for configuration fields.

This module provides reusable validation functions for Pydantic models
in the configuration system.
"""

from __future__ import annotations

from pathlib import Path


def validate_extension_format(ext: str) -> str:
    """Validate that a file extension starts with a dot.

    Args:
        ext: File extension to validate

    Returns:
        The validated extension

    Raises:
        ValueError: If extension doesn't start with a dot
    """
    if not ext.startswith("."):
        msg = f"Extension '{ext}' must start with a dot"
        raise ValueError(msg)
    return ext


def validate_extensions_list(extensions: list[str]) -> list[str]:
    """Validate a list of file extensions.

    Args:
        extensions: List of file extensions to validate

    Returns:
        The validated extensions list

    Raises:
        ValueError: If any extension doesn't start with a dot

    Example:
        >>> validate_extensions_list([".mkv", ".mp4", ".avi"])
        ['.mkv', '.mp4', '.avi']
    """
    if not extensions:
        return extensions

    # Fail-fast: Check all at once and report first error
    invalid_exts = [ext for ext in extensions if not ext.startswith(".")]
    if invalid_exts:
        msg = f"Extensions {invalid_exts} must start with a dot"
        raise ValueError(msg)

    return extensions


def validate_non_empty_string(value: str) -> str:
    """Validate that a string is non-empty after stripping.

    Args:
        value: String to validate

    Returns:
        The validated string

    Raises:
        ValueError: If string is empty or only whitespace
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Value must be a non-empty string")
    return value


def validate_patterns_list(patterns: list[str]) -> list[str]:
    """Validate a list of patterns are non-empty strings.

    Args:
        patterns: List of patterns to validate

    Returns:
        The validated patterns list

    Raises:
        ValueError: If any pattern is empty or not a string

    Example:
        >>> validate_patterns_list(["*.txt", "test_*"])
        ['*.txt', 'test_*']
    """
    if not patterns:
        return patterns

    # Fail-fast: Check all at once
    empty_patterns = [i for i, p in enumerate(patterns) if not isinstance(p, str) or not p.strip()]
    if empty_patterns:
        msg = f"Patterns at indices {empty_patterns} must be non-empty strings"
        raise ValueError(msg)

    return patterns


def validate_folder_path(path_str: str) -> str:
    """Validate a folder path.

    Args:
        path_str: Folder path string to validate

    Returns:
        The validated path string

    Raises:
        ValueError: If path is invalid
    """
    if path_str and path_str.strip():
        path = Path(path_str.strip())
        # Only validate format, don't check existence
        # This allows configuration before folders are created
        try:
            # Test if path can be resolved (format validation)
            _ = path.resolve()
        except (OSError, ValueError) as e:
            msg = f"Invalid folder path: {e}"
            raise ValueError(msg) from e
    return path_str


def validate_non_negative_int(value: int) -> int:
    """Validate that an integer is non-negative.

    Args:
        value: Integer to validate

    Returns:
        The validated integer

    Raises:
        ValueError: If value is negative
    """
    if value < 0:
        raise ValueError("Value must be non-negative")
    return value


__all__ = [
    "validate_extension_format",
    "validate_extensions_list",
    "validate_folder_path",
    "validate_non_empty_string",
    "validate_non_negative_int",
    "validate_patterns_list",
]
