"""
CLI Command Router Module

This module handles command routing for the AniVault CLI.
It separates the command routing logic from the main CLI module to follow
the Single Responsibility Principle.
"""

from __future__ import annotations

from argparse import Namespace
from typing import Any, Callable

from anivault.shared.errors import ApplicationError, ErrorCode

# Command handler registry
COMMAND_HANDLERS: dict[str, Callable[[Namespace], int]] = {}


def register_command_handler(command: str, handler: Callable[[Namespace], int]) -> None:
    """
    Register a command handler function.

    Args:
        command: Command name
        handler: Handler function that takes Namespace args and returns int
    """
    COMMAND_HANDLERS[command] = handler


def route_command(args: Namespace) -> int:
    """
    Route a parsed command to the appropriate handler.

    Args:
        args: Parsed command line arguments

    Returns:
        int: Exit code from the command handler

    Raises:
        ApplicationError: If no handler is found for the command
    """
    try:
        command = args.command

        if not command:
            raise ApplicationError(
                ErrorCode.INVALID_COMMAND,
                "No command specified",
            )

        handler = get_handler_for_command(command)
        if not handler:
            raise ApplicationError(
                ErrorCode.INVALID_COMMAND,
                f"Unknown command: {command}",
            )

        return handler(args)

    except ApplicationError:
        raise
    except Exception as e:
        raise ApplicationError(
            ErrorCode.COMMAND_EXECUTION_FAILED,
            f"Failed to execute command '{args.command}': {e}",
        ) from e


def get_handler_for_command(command: str) -> Callable[[Namespace], int] | None:
    """
    Get the handler function for a specific command.

    Args:
        command: Command name

    Returns:
        Callable or None: Handler function if found, None otherwise
    """
    return COMMAND_HANDLERS.get(command)


def validate_command(command: str) -> bool:
    """
    Validate that a command is supported.

    Args:
        command: Command name to validate

    Returns:
        bool: True if command is supported, False otherwise
    """
    return command in COMMAND_HANDLERS


def get_available_commands() -> list[str]:
    """
    Get list of available commands.

    Returns:
        list[str]: List of available command names
    """
    return list(COMMAND_HANDLERS.keys())


def get_command_info() -> dict[str, dict[str, Any]]:
    """
    Get information about all registered commands.

    Returns:
        dict[str, dict[str, Any]]: Command information dictionary
    """
    return {
        command: {
            "handler": handler,
            "docstring": handler.__doc__ or "No description available",
        }
        for command, handler in COMMAND_HANDLERS.items()
    }
