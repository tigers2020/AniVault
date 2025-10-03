"""
JSON Output Formatter for AniVault CLI

This module provides a centralized JSON formatter that can be used by all CLI commands
to produce machine-readable output when the --json flag is used.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import orjson


def format_json_output(
    success: bool,
    command: str,
    data: Any | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> bytes:
    """
    Format command output as JSON.

    Args:
        success: Whether the command executed successfully
        command: The command name (e.g., "scan", "match")
        data: The command's output data
        errors: List of error messages
        warnings: List of warning messages

    Returns:
        JSON-encoded bytes ready for output

    Example:
        >>> output = format_json_output(
        ...     success=True,
        ...     command="scan",
        ...     data={"files_found": 10, "files_processed": 8}
        ... )
        >>> print(output.decode())
        {
          "success": true,
          "timestamp": "2023-10-03T10:30:00Z",
          "command": "scan",
          "data": {
            "files_found": 10,
            "files_processed": 8
          },
          "errors": [],
          "warnings": []
        }
    """
    # Ensure errors and warnings are lists
    if errors is None:
        errors = []
    if warnings is None:
        warnings = []

    # If there are errors, success should be False
    if errors:
        success = False

    # Create the JSON structure
    json_data = {
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "data": data,
        "errors": errors,
        "warnings": warnings,
    }

    try:
        # Serialize to JSON using orjson for performance
        return orjson.dumps(
            json_data,
            option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2,
        )
    except (TypeError, ValueError) as e:
        # If serialization fails, return an error response
        error_data = {
            "success": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "data": None,
            "errors": [f"JSON serialization failed: {e!s}"],
            "warnings": [],
        }
        return orjson.dumps(
            error_data,
            option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2,
        )


def safe_json_serialize(obj: Any) -> Any:
    """
    Safely serialize an object to JSON-serializable format.

    Args:
        obj: Object to serialize

    Returns:
        JSON-serializable representation of the object

    Example:
        >>> safe_json_serialize({"key": "value"})
        {'key': 'value'}
        >>> safe_json_serialize(Path("/some/path"))
        '/some/path'
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [safe_json_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): safe_json_serialize(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return safe_json_serialize(obj.__dict__)
    if hasattr(obj, "__str__"):
        return str(obj)
    return str(obj)


def format_success_output(command: str, data: Any) -> bytes:
    """
    Convenience function to format successful command output.

    Args:
        command: The command name
        data: The command's output data

    Returns:
        JSON-encoded bytes for successful output
    """
    return format_json_output(success=True, command=command, data=data)


def format_error_output(command: str, errors: list[str]) -> bytes:
    """
    Convenience function to format error output.

    Args:
        command: The command name
        errors: List of error messages

    Returns:
        JSON-encoded bytes for error output
    """
    return format_json_output(success=False, command=command, errors=errors)


def is_json_serializable(obj: Any) -> bool:
    """
    Check if an object is JSON serializable.

    Args:
        obj: Object to check

    Returns:
        True if the object is JSON serializable, False otherwise
    """
    try:
        orjson.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False
