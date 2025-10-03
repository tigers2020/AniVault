"""
AniVault Typer CLI Application

This is the main Typer-based CLI application for AniVault.
It provides a modern, type-safe command-line interface with automatic
help generation, shell completion, and better error handling.
"""

from __future__ import annotations

from typing import Annotated

import typer

from anivault.cli.common.context import CliContext, LogLevel, set_cli_context
from anivault.cli.common.options import (
    json_output_option,
    log_level_option,
    verbose_option,
    version_option,
)

# Create the main Typer app
app = typer.Typer(
    name="anivault",
    help="AniVault - Advanced Anime Collection Management System",
    add_completion=False,  # Will be enabled later
    rich_markup_mode="rich",  # Enable rich formatting
    no_args_is_help=True,
    invoke_without_command=True,  # Allow running without subcommands
)

# Version information
__version__ = "0.1.0"


def version_callback(value: bool) -> None:
    """Print version information and exit."""
    if value:
        typer.echo(f"AniVault CLI v{__version__}")
        raise typer.Exit


def main_callback(
    verbose: Annotated[int, verbose_option],
    log_level: Annotated[LogLevel, log_level_option],
    json_output: Annotated[bool, json_output_option],
    version: Annotated[bool, version_option],
) -> None:
    """
    Main callback function for processing common options.

    This function is called before any command is executed and sets up
    the global CLI context with the parsed options.

    Args:
        verbose: Verbosity level (count-based)
        log_level: Logging level (enum-based)
        json_output: Whether to output in JSON format
        version: Whether to show version information
    """
    # Handle version option first
    if version:
        version_callback(True)

    # Create and set the CLI context
    context = CliContext(
        verbose=verbose,
        log_level=log_level,
        json_output=json_output,
    )
    set_cli_context(context)


@app.callback()
def main(
    verbose: Annotated[int, verbose_option],
    log_level: Annotated[LogLevel, log_level_option],
    json_output: Annotated[bool, json_output_option],
    version: Annotated[bool, version_option],
) -> None:
    """
    AniVault - Advanced Anime Collection Management System.

    A comprehensive tool for organizing anime collections with TMDB integration,
    intelligent file matching, and automated organization capabilities.
    """
    # Process the common options
    main_callback(verbose, log_level, json_output, version)


if __name__ == "__main__":
    app()
