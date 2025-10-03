"""
Common CLI Options Module

This module provides a centralized system for handling common CLI options
across all AniVault commands. It ensures consistency and simplifies future
modifications to global options.

The common options include:
- --verbose: Enable verbose output (shortcut for --log-level DEBUG)
- --log-level: Set the logging level
- --json: Enable machine-readable JSON output
- --version: Show version information (applied to main parser)
"""

import argparse
from typing import Any

from anivault.shared.constants import APPLICATION_VERSION


def get_common_options_parser() -> argparse.ArgumentParser:
    """
    Create a reusable ArgumentParser with common CLI options.

    This parser is designed to be used as a parent parser for all subcommands,
    ensuring consistent global options across the entire CLI.

    Returns:
        argparse.ArgumentParser: Parser with common options configured

    Example:
        >>> common_parser = get_common_options_parser()
        >>> subparser = main_parser.add_subparsers().add_parser(
        ...     "scan",
        ...     parents=[common_parser]
        ... )
    """
    parser = argparse.ArgumentParser(add_help=False)

    # Verbose option - shortcut for --log-level DEBUG
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output (equivalent to --log-level DEBUG)",
    )

    # Log level option
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )

    # JSON output option
    parser.add_argument(
        "--json",
        action="store_true",
        help="Enable machine-readable JSON output instead of human-readable format",
    )

    return parser


def get_version_argument() -> dict[str, Any]:
    """
    Get version argument configuration for the main parser.

    Returns:
        Dict[str, Any]: Configuration dictionary for argparse.add_argument()
    """
    return {
        "action": "version",
        "version": f"AniVault {APPLICATION_VERSION}",
        "help": "Show version information and exit",
    }


def validate_common_options(args: argparse.Namespace) -> None:
    """
    Validate common options and apply any necessary transformations.

    Args:
        args: Parsed command line arguments

    Raises:
        ValueError: If conflicting options are provided
    """
    # If verbose is enabled, override log level to DEBUG
    if hasattr(args, "verbose") and args.verbose:
        if hasattr(args, "log_level"):
            args.log_level = "DEBUG"


def is_verbose_output_enabled(args: argparse.Namespace) -> bool:
    """
    Check if verbose output is enabled.

    Args:
        args: Parsed command line arguments

    Returns:
        bool: True if verbose output is enabled
    """
    return getattr(args, "verbose", False)


def is_json_output_enabled(args: argparse.Namespace) -> bool:
    """
    Check if JSON output is enabled.

    Args:
        args: Parsed command line arguments

    Returns:
        bool: True if JSON output is enabled
    """
    return getattr(args, "json", False)


def get_effective_log_level(args: argparse.Namespace) -> str:
    """
    Get the effective log level after applying verbose override.

    Args:
        args: Parsed command line arguments

    Returns:
        str: Effective log level
    """
    if is_verbose_output_enabled(args):
        return "DEBUG"
    return getattr(args, "log_level", "INFO")
