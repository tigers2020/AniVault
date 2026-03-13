"""CLI setup decorator module.

This module provides a decorator for standardizing CLI handler initialization,
including Console creation, logging setup, and option validation.

The setup_handler decorator eliminates repetitive initialization code across
command handlers, improving maintainability and consistency.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, TypeVar

from rich.console import Console

from anivault.cli.common.validation import (
    ensure_json_mode_consistency,
    normalize_extensions_list,
    validate_directory_with_context,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def setup_handler(
    *,
    requires_directory: bool = False,
    supports_json: bool = False,
    allow_dry_run: bool = False,
    require_console: bool = True,
) -> Callable[[F], F]:
    """Decorator for standardized CLI handler initialization.

    This decorator handles common initialization tasks:
    1. Directory validation (if requires_directory=True)
    2. Option validation (JSON mode consistency, dry-run+yes check)
    3. Rich Console creation (if require_console=True and not JSON mode)
    4. LoggerAdapter creation with operation context
    5. Extension normalization (if options has extensions attribute)

    The decorated function receives enhanced arguments:
    - console: Rich Console instance (if require_console=True)
    - logger_adapter: LoggerAdapter with command context

    Args:
        requires_directory: Whether directory validation is required
        supports_json: Whether handler supports JSON output mode
        allow_dry_run: Whether handler supports dry-run mode
        require_console: Whether Rich Console should be created

    Returns:
        Decorated function with initialization handling

    Example:
        >>> @setup_handler(requires_directory=True, supports_json=True)
        ... @handle_cli_errors(operation="scan_files", command_name="scan")
        ... def handle_scan_command(options, console, logger_adapter):
        ...     # Core logic only - initialization is handled
        ...     return scan_pipeline(options.directory)

    Note:
        This decorator should be applied BEFORE handle_cli_errors decorator
        to ensure initialization happens before error handling.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            options = _extract_options(args, kwargs)
            _validate_directory_if_required(options, requires_directory, func.__name__)
            _validate_option_combinations(options, allow_dry_run, func.__name__)
            _normalize_extensions_if_present(options)
            console = _resolve_console(require_console, supports_json, options)
            logger_adapter = _create_logger_adapter(func.__name__)
            if console is not None:
                kwargs["console"] = console
            kwargs["logger_adapter"] = logger_adapter
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def _validate_directory_if_required(
    options: Any,
    requires_directory: bool,
    operation: str,
) -> None:
    """Validate and update directory on options when required."""
    if not requires_directory or not hasattr(options, "directory"):
        return
    raw_dir = options.directory.path if hasattr(options.directory, "path") else options.directory
    validated_dir = validate_directory_with_context(raw_dir, operation=operation)
    if hasattr(options.directory, "path"):
        options.directory.path = validated_dir
    else:
        options.directory = validated_dir


def _validate_option_combinations(
    options: Any,
    allow_dry_run: bool,
    command_name: str,
) -> None:
    """Validate option combinations (e.g. JSON mode consistency)."""
    if allow_dry_run:
        ensure_json_mode_consistency(options, command_name)


def _normalize_extensions_if_present(options: Any) -> None:
    """Normalize extensions on options when present and string."""
    if hasattr(options, "extensions") and isinstance(options.extensions, str):
        options.extensions = normalize_extensions_list(options.extensions)


def _resolve_console(
    require_console: bool,
    supports_json: bool,
    options: Any,
) -> Console | None:
    """Create Rich Console when required and not in JSON mode."""
    if not require_console:
        return None
    is_json_mode = supports_json and hasattr(options, "json_output") and options.json_output
    return None if is_json_mode else Console()


def _create_logger_adapter(command_name: str) -> logging.LoggerAdapter[Any]:
    """Create LoggerAdapter with command context."""
    return logging.LoggerAdapter(
        logger,
        extra={"command": command_name, "operation": command_name},
    )


def _extract_options(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    """Extract options from function arguments.

    Args:
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Options instance (first arg with expected attributes)

    Raises:
        ValueError: If no options object found
    """
    # Try to find options in args (usually first argument)
    for arg in args:
        if hasattr(arg, "directory") or hasattr(arg, "json_output"):
            return arg

    # Try to find in kwargs
    if "options" in kwargs:
        return kwargs["options"]

    # Fallback: Return first arg (assume it's options)
    if args:
        return args[0]

    msg = "No options object found in function arguments"
    raise ValueError(msg)
