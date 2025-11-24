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
            # Extract options from arguments
            options = _extract_options(args, kwargs)

            # Validate directory if required
            if requires_directory:
                if hasattr(options, "directory"):
                    # Validate using enhanced validation
                    validated_dir = validate_directory_with_context(
                        (options.directory.path if hasattr(options.directory, "path") else options.directory),
                        operation=func.__name__,
                    )
                    # Update options with validated directory
                    if hasattr(options.directory, "path"):
                        options.directory.path = validated_dir
                    else:
                        options.directory = validated_dir

            # Validate option combinations
            if allow_dry_run:
                ensure_json_mode_consistency(options, func.__name__)

            # Normalize extensions if present
            if hasattr(options, "extensions"):
                if isinstance(options.extensions, str):
                    options.extensions = normalize_extensions_list(options.extensions)

            # Create Rich Console if required and not in JSON mode
            console = None
            if require_console:
                # Skip console creation in JSON mode
                is_json_mode = supports_json and hasattr(options, "json_output") and options.json_output
                if not is_json_mode:
                    console = Console()

            # Create LoggerAdapter with command context
            logger_adapter = logging.LoggerAdapter(
                logger,
                extra={
                    "command": func.__name__,
                    "operation": func.__name__,
                },
            )

            # Call original function with enhanced arguments
            # Inject console and logger_adapter as keyword arguments
            if console is not None:
                kwargs["console"] = console
            kwargs["logger_adapter"] = logger_adapter

            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


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
