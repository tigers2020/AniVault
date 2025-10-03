"""
AniVault Typer CLI Application

This is the main Typer-based CLI application for AniVault.
It provides a modern, type-safe command-line interface with automatic
help generation, shell completion, and better error handling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from anivault.cli.common.context import CliContext, LogLevel, set_cli_context
from anivault.cli.common.options import (
    json_output_option,
    log_level_option,
    verbose_option,
    version_option,
)
from anivault.cli.match_handler import match_command
from anivault.cli.scan_handler import scan_command

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
        version_callback(value=True)

    # Create and set the CLI context
    context = CliContext(
        verbose=verbose,
        log_level=log_level,
        json_output=json_output,
    )
    set_cli_context(context)


# Create the main Typer app with callback
app = typer.Typer(
    name="anivault",
    help="AniVault - Advanced Anime Collection Management System",
    add_completion=False,  # Will be enabled later
    rich_markup_mode="rich",  # Enable rich formatting
    no_args_is_help=True,
    invoke_without_command=True,
)


@app.callback()
def main(
    verbose: Annotated[int, verbose_option] = 0,
    log_level: Annotated[LogLevel, log_level_option] = LogLevel.INFO,
    json_output: Annotated[bool, json_output_option] = False,
    version: Annotated[bool, version_option] = False,
) -> None:
    """
    AniVault - Advanced Anime Collection Management System.

    A comprehensive tool for organizing anime collections with TMDB integration,
    intelligent file matching, and automated organization capabilities.
    """
    # Process the common options
    main_callback(verbose, log_level, json_output, version)


@app.command("scan")
def scan_command_typer(
    directory: Path = typer.Argument(  # type: ignore[misc]
        ...,
        help="Directory to scan for anime files",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(  # type: ignore[misc]
        True,
        "--recursive",
        "-r",
        help="Scan directories recursively",
    ),
    include_subtitles: bool = typer.Option(  # type: ignore[misc]
        True,
        "--include-subtitles",
        help="Include subtitle files in scan",
    ),
    include_metadata: bool = typer.Option(  # type: ignore[misc]
        True,
        "--include-metadata",
        help="Include metadata files in scan",
    ),
    output_file: Path | None = typer.Option(  # type: ignore[misc]
        None,
        "--output",
        "-o",
        help="Output file for scan results (JSON format)",
        writable=True,
    ),
) -> None:
    """
    Scan directories for anime files and extract metadata.

    This command recursively scans the specified directory for anime files
    and extracts metadata using anitopy. It can optionally include subtitle
    and metadata files in the scan results.

    Examples:
        # Scan current directory
        anivault scan .

        # Scan with custom options
        anivault scan /path/to/anime --recursive --output results.json

        # Scan without subtitles
        anivault scan /path/to/anime --no-include-subtitles
    """
    # Call the scan command
    scan_command(
        directory,
        recursive,
        include_subtitles,
        include_metadata,
        output_file,
    )


@app.command("match")
def match_command_typer(
    directory: Path = typer.Argument(  # type: ignore[misc]
        ...,
        help="Directory to match anime files against TMDB database",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(  # type: ignore[misc]
        True,
        "--recursive/--no-recursive",
        "-r",
        help="Match files recursively in subdirectories",
    ),
    include_subtitles: bool = typer.Option(  # type: ignore[misc]
        True,
        "--include-subtitles/--no-include-subtitles",
        help="Include subtitle files in matching",
    ),
    include_metadata: bool = typer.Option(  # type: ignore[misc]
        True,
        "--include-metadata/--no-include-metadata",
        help="Include metadata files in matching",
    ),
    output_file: Path | None = typer.Option(  # type: ignore[misc]
        None,
        "--output",
        "-o",
        help="Output file for match results (JSON format)",
        writable=True,
    ),
) -> None:
    """
    Match anime files against TMDB database.

    This command takes scanned anime files and matches them against the TMDB database
    to find corresponding TV shows and movies. It uses intelligent matching algorithms
    to handle various naming conventions and provides detailed matching results.

    Examples:
        # Match files in current directory
        anivault match .

        # Match with custom options
        anivault match /path/to/anime --recursive --output results.json

        # Match without subtitles
        anivault match /path/to/anime --no-include-subtitles
    """
    # Call the match command
    match_command(
        directory,
        recursive,
        include_subtitles,
        include_metadata,
        output_file,
    )


if __name__ == "__main__":
    app()
