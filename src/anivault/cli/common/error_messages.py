"""CLI Error Message Module.

This module provides standardized error message formatting for CLI commands,
integrating JSON, Rich console, and structured logging outputs.

The module follows these principles:
- One Source of Truth: Central place for all CLI error messages
- Path Masking: Sensitive paths are automatically masked
- Structured Logging: Error context is formatted for logging
- I18N Ready: Message catalog for future localization
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import orjson

from anivault.shared.constants.cli import CLIFormatting
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)

logger = logging.getLogger(__name__)


@dataclass
class ErrorMessageContext:
    """Context information for error message formatting.

    Attributes:
        error: The error instance (ApplicationError or InfrastructureError)
        operation: Operation name where error occurred
        command_name: CLI command name (scan, match, organize, etc.)
        additional_data: Extra data for error context
    """

    error: ApplicationError | InfrastructureError | Exception
    operation: str
    command_name: str
    additional_data: dict[str, Any] = field(default_factory=dict)


def build_console_message(context: ErrorMessageContext) -> str:
    """Build Rich console error message.

    Args:
        context: Error message context

    Returns:
        Formatted error message for Rich console output

    Example:
        >>> ctx = ErrorMessageContext(
        ...     error=ApplicationError(...),
        ...     operation="scan_files",
        ...     command_name="scan"
        ... )
        >>> message = build_console_message(ctx)
        >>> console.print(message)
    """
    # Determine error type
    if isinstance(context.error, ApplicationError):
        error_type = "Application error"
        error_code = context.error.code
        error_message = context.error.message
    elif isinstance(context.error, InfrastructureError):
        error_type = "Infrastructure error"
        error_code = context.error.code
        error_message = context.error.message
    else:
        error_type = "Unexpected error"
        error_code = ErrorCode.CLI_UNEXPECTED_ERROR
        error_message = str(context.error)

    # Build base message
    message_parts = [f"{error_type} during {context.operation}: {error_message}"]

    # Add masked paths if available
    if hasattr(context.error, "context") and context.error.context:
        error_ctx = context.error.context
        if error_ctx.additional_data:
            file_path = error_ctx.additional_data.get("file_path")
            if file_path:
                masked_path = mask_sensitive_paths(str(file_path))
                message_parts.append(f"  File: {masked_path}")

    # Add recovery hint from message catalog
    recovery_hint = _get_recovery_hint(error_code)
    if recovery_hint:
        message_parts.append(f"  💡 {recovery_hint}")

    formatted_message = "\n".join(message_parts)

    # Apply Rich formatting
    return CLIFormatting.format_colored_message(formatted_message, "error")


def build_json_payload(
    context: ErrorMessageContext,
    success: bool = False,
) -> bytes:
    """Build JSON error payload for machine-readable output.

    Args:
        context: Error message context
        success: Success flag (always False for errors)

    Returns:
        Serialized JSON payload as bytes (UTF-8 encoded)

    Example:
        >>> ctx = ErrorMessageContext(...)
        >>> payload = build_json_payload(ctx)
        >>> sys.stdout.buffer.write(payload)
    """
    # Extract error details
    if isinstance(context.error, (ApplicationError, InfrastructureError)):
        error_code = context.error.code
        error_message = context.error.message
        error_ctx = context.error.context if hasattr(context.error, "context") else None
    else:
        error_code = ErrorCode.CLI_UNEXPECTED_ERROR
        error_message = str(context.error)
        error_ctx = None

    # Build error data (StatusKeys values are lowercase)
    error_data: dict[str, Any] = {
        "error_code": error_code,
        "operation": context.operation,
    }

    # Add context if available
    if error_ctx:
        # Mask sensitive paths in context
        masked_context = _mask_context_paths(error_ctx)
        error_data["context"] = masked_context

    # Add additional data
    if context.additional_data:
        error_data.update(context.additional_data)

    # Build full payload
    payload = {
        "success": success,
        "command": context.command_name,
        "errors": [error_message],
        "data": error_data,
    }

    # Serialize with orjson (fast, preserves UTF-8)
    return orjson.dumps(payload, option=orjson.OPT_INDENT_2)


def build_log_context(context: ErrorMessageContext) -> dict[str, Any]:
    """Build structured logging context.

    Args:
        context: Error message context

    Returns:
        Dictionary for logging extra context

    Example:
        >>> ctx = ErrorMessageContext(...)
        >>> log_ctx = build_log_context(ctx)
        >>> logger.error("Failed operation", extra=log_ctx)
    """
    log_context: dict[str, Any] = {
        "operation": context.operation,
        "command": context.command_name,
    }

    # Extract error details
    if isinstance(context.error, (ApplicationError, InfrastructureError)):
        log_context["error_code"] = context.error.code
        if hasattr(context.error, "context") and context.error.context:
            # Mask sensitive paths before logging
            masked_context = _mask_context_paths(context.error.context)
            log_context["context"] = masked_context
    else:
        log_context["error_code"] = ErrorCode.CLI_UNEXPECTED_ERROR
        log_context["error_type"] = type(context.error).__name__

    # Add additional data
    if context.additional_data:
        log_context["additional_data"] = context.additional_data

    return log_context


def mask_sensitive_paths(path_str: str) -> str:
    """Mask sensitive paths for security.

    Converts absolute paths to home-relative paths for privacy.
    Also handles common user directory patterns even when not under actual home.

    Args:
        path_str: Path string to mask

    Returns:
        Masked path string

    Example:
        >>> mask_sensitive_paths("/home/user/projects/anime")
        "~/projects/anime"
        >>> mask_sensitive_paths("C:\\Users\\user\\Videos")
        "~\\Videos"
    """
    try:
        path = Path(path_str)
        home = Path.home()

        # Try to mask paths under actual home directory
        try:
            if path.is_absolute() and path.is_relative_to(home):
                rel_path = path.relative_to(home)
                # Use OS-appropriate separator
                separator = "\\" if "\\" in path_str else "/"
                return f"~{separator}{rel_path}"
        except (ValueError, AttributeError):
            pass

        # Fallback: Pattern-based masking for common user directories
        import re

        # Unix-style: /home/username/...
        unix_pattern = r"/home/[^/]+/"
        if re.search(unix_pattern, path_str):
            masked = re.sub(unix_pattern, "~/", path_str)
            return masked

        # Windows-style: C:\Users\username\...
        windows_pattern = r"[A-Z]:\\Users\\[^\\]+\\"
        if re.search(windows_pattern, path_str, re.IGNORECASE):
            masked = re.sub(windows_pattern, "~\\", path_str, flags=re.IGNORECASE)
            return masked

        # For non-home paths, return as-is
        return path_str

    except (ValueError, RuntimeError):
        # If path operations fail, return original
        return path_str


def _mask_context_paths(context: ErrorContext) -> dict[str, Any]:
    """Mask paths in error context.

    Args:
        context: Error context with potential file paths

    Returns:
        Context dictionary with masked paths
    """
    context_dict: dict[str, Any] = {}

    # Add operation
    if context.operation:
        context_dict["operation"] = context.operation

    # Process additional_data
    if context.additional_data:
        masked_data = {}
        for key, value in context.additional_data.items():
            # Mask path-like values
            if isinstance(value, (str, Path)) and (
                "path" in key.lower() or "file" in key.lower()
            ):
                masked_data[key] = mask_sensitive_paths(str(value))
            else:
                masked_data[key] = value
        context_dict["additional_data"] = masked_data

    return context_dict


def _get_recovery_hint(error_code: ErrorCode | str) -> str | None:
    """Get recovery hint from message catalog.

    Args:
        error_code: Error code to look up

    Returns:
        Recovery hint or None if not available

    Note:
        This is the foundation for future i18n support.
        Currently returns English hints.
    """
    # Message catalog (future-i18n: can be loaded from external file)
    # Using ErrorCode enum values as keys for type safety
    recovery_hints: dict[ErrorCode, str] = {
        ErrorCode.FILE_NOT_FOUND: "Check if the file path exists",
        ErrorCode.DIRECTORY_NOT_FOUND: "Verify the directory path",
        ErrorCode.PERMISSION_DENIED: "Check file permissions or run with appropriate privileges",
        ErrorCode.FILE_PERMISSION_DENIED: "Ensure you have read/write access to the file",
        ErrorCode.API_RATE_LIMIT: "Wait a moment and try again",
        ErrorCode.API_TIMEOUT: "Check your network connection",
        ErrorCode.NETWORK_ERROR: "Verify your internet connection",
        ErrorCode.TMDB_API_AUTHENTICATION_ERROR: "Check your TMDB API key",
        ErrorCode.TMDB_API_RATE_LIMIT_EXCEEDED: "Wait for rate limit to reset",
        ErrorCode.VALIDATION_ERROR: "Review the input data format",
        ErrorCode.PARSING_ERROR: "Check the filename format",
        ErrorCode.CACHE_ERROR: "Try clearing the cache with --clear-cache",
        ErrorCode.CONFIG_ERROR: "Review your configuration file",
        ErrorCode.INVALID_CONFIG: "Check the configuration format",
    }

    # Handle both ErrorCode enum and string lookups
    if isinstance(error_code, ErrorCode):
        return recovery_hints.get(error_code)

    # Try to convert string to ErrorCode
    try:
        error_enum = ErrorCode(error_code)
        return recovery_hints.get(error_enum)
    except (ValueError, KeyError):
        return None


# Message catalog for future localization
# future-i18n: This can be externalized to JSON/YAML files per locale
MESSAGE_CATALOG: dict[str, dict[str, str]] = {
    "en": {
        "application_error_prefix": "Application error during",
        "infrastructure_error_prefix": "Infrastructure error during",
        "unexpected_error_prefix": "Unexpected error during",
        "file_label": "File",
        "hint_prefix": "💡",
    },
    # "ko": { ... }  # Korean translations
    # "ja": { ... }  # Japanese translations
}


def get_message_catalog(locale: str = "en") -> dict[str, str]:
    """Get message catalog for locale.

    Args:
        locale: Locale code (default: "en")

    Returns:
        Message catalog dictionary

    Note:
        future-i18n: Load from external files based on locale
    """
    return MESSAGE_CATALOG.get(locale, MESSAGE_CATALOG["en"])
