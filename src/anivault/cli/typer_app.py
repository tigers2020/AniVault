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
from anivault.cli.common.models import DirectoryPath
from anivault.cli.common.options import (
    json_output_option,
    log_level_option,
    verbose_option,
    version_option,
)
from anivault.cli.common.validation import create_validator
from anivault.cli.log_handler import log_command
from anivault.cli.match_handler import match_command
from anivault.cli.organize_handler import organize_command
from anivault.cli.rollback_handler import rollback_command
from anivault.cli.run_handler import run_command
from anivault.cli.scan_handler import scan_command
from anivault.cli.verify_handler import verify_command

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
    add_completion=True,  # Enable shell completion support
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
    json: bool = typer.Option(  # type: ignore[misc]
        False,
        "--json",
        help="Output results in JSON format",
    ),
) -> None:
    """
    Scan directories for anime files and extract metadata.

    This command recursively scans the specified directory for anime files
    and extracts metadata using anitopy. It can optionally include subtitle
    and metadata files in the scan results.

    The scan process includes:
    - File discovery based on supported extensions
    - Metadata extraction using anitopy parser
    - TMDB API enrichment for additional metadata
    - Progress tracking and error handling

    Supported file extensions: mkv, mp4, avi, mov, wmv, flv, webm, m4v
    Supported subtitle formats: srt, ass, ssa, vtt, smi, sub

    Examples:
        # Scan current directory with default settings
        anivault scan .

        # Scan specific directory with custom options
        anivault scan /path/to/anime --recursive --output results.json

        # Scan without subtitles (faster processing)
        anivault scan /path/to/anime --no-include-subtitles

        # Scan with verbose output for debugging
        anivault scan /path/to/anime --verbose

        # Save results to JSON file
        anivault scan /path/to/anime --output scan_results.json
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
    json: bool = typer.Option(  # type: ignore[misc]
        False,
        "--json",
        help="Output results in JSON format",
    ),
) -> None:
    """
    Match anime files against TMDB database.

    This command takes scanned anime files and matches them against the TMDB database
    to find corresponding TV shows and movies. It uses intelligent matching algorithms
    to handle various naming conventions and provides detailed matching results.

    The matching process includes:
    - Fuzzy string matching for anime titles
    - Episode and season number correlation
    - Quality and release group matching
    - Confidence scoring for match accuracy
    - Fallback strategies for difficult cases

    Matching algorithms:
    - Primary: Exact title and episode matching
    - Secondary: Fuzzy matching with confidence thresholds
    - Fallback: Manual review suggestions

    Examples:
        # Match files in current directory
        anivault match .

        # Match with custom options and save results
        anivault match /path/to/anime --recursive --output match_results.json

        # Match without subtitles (focus on video files only)
        anivault match /path/to/anime --no-include-subtitles

        # Match with verbose output to see matching details
        anivault match /path/to/anime --verbose

        # Match and output results in JSON format
        anivault match /path/to/anime --json
    """
    # Call the match command
    match_command(
        directory,
        recursive,
        include_subtitles,
        include_metadata,
        output_file,
    )


@app.command("organize")
def organize_command_typer(
    directory: Path = typer.Argument(  # type: ignore[misc]
        ...,
        help="Directory containing scanned and matched anime files to organize",
        callback=create_validator(DirectoryPath),
    ),
    dry_run: bool = typer.Option(  # type: ignore[misc]
        False,
        "--dry-run",
        help="Show what would be organized without actually moving files",
    ),
    yes: bool = typer.Option(  # type: ignore[misc]
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts and proceed with organization",
    ),
    json: bool = typer.Option(  # type: ignore[misc]
        False,
        "--json",
        help="Output results in JSON format",
    ),
    destination: str = typer.Option(  # type: ignore[misc]
        "Anime",
        "--destination",
        "-d",
        help="Destination directory for organized files",
    ),
) -> None:
    """
    Organize anime files into a structured directory layout.

    This command takes scanned and matched anime files and organizes them
    into a clean directory structure based on the TMDB metadata. It can
    create series folders, season subfolders, and rename files consistently.

    Examples:
        # Organize files in current directory (with confirmation)
        anivault organize .

        # Preview what would be organized without making changes
        anivault organize . --dry-run

        # Organize without confirmation prompts
        anivault organize . --yes
    """
    # Call the organize command
    organize_command(directory, dry_run, yes, json, destination)


@app.command("run")
def run_command_typer(
    directory: Path = typer.Argument(  # type: ignore[misc]
        ...,
        help="Directory containing anime files to process",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(  # type: ignore[misc]
        True,
        "--recursive/--no-recursive",
        "-r",
        help="Process files recursively in subdirectories",
    ),
    include_subtitles: bool = typer.Option(  # type: ignore[misc]
        True,
        "--include-subtitles/--no-include-subtitles",
        help="Include subtitle files in processing",
    ),
    include_metadata: bool = typer.Option(  # type: ignore[misc]
        True,
        "--include-metadata/--no-include-metadata",
        help="Include metadata files in processing",
    ),
    output_file: Path | None = typer.Option(  # type: ignore[misc]
        None,
        "--output",
        "-o",
        help="Output file for processing results (JSON format)",
        writable=True,
    ),
    dry_run: bool = typer.Option(  # type: ignore[misc]
        False,
        "--dry-run",
        help="Show what would be processed without actually processing files",
    ),
    yes: bool = typer.Option(  # type: ignore[misc]
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts and proceed with processing",
    ),
    json: bool = typer.Option(  # type: ignore[misc]
        False,
        "--json",
        help="Output results in JSON format",
    ),
) -> None:
    """
    Run the complete anime organization workflow (scan, match, organize).

    This command orchestrates the entire AniVault workflow in sequence:
    1. Scan directory for anime files and extract metadata
    2. Match files against TMDB database for accurate identification
    3. Organize files into structured directory layout

    Workflow phases:
    - Phase 1 (Scan): Discover and parse anime files using anitopy
    - Phase 2 (Match): Correlate parsed data with TMDB database
    - Phase 3 (Organize): Create organized directory structure

    Benefits of using 'run' vs individual commands:
    - Single command for complete workflow
    - Consistent options across all phases
    - Unified error handling and progress tracking
    - Atomic operation with rollback support

    Examples:
        # Run complete workflow on current directory
        anivault run .

        # Run with specific options and save results
        anivault run /path/to/anime --recursive --output workflow_results.json

        # Preview what would be processed without making changes
        anivault run . --dry-run

        # Run without confirmation prompts (automated mode)
        anivault run . --yes

        # Run with verbose output to see each phase
        anivault run /path/to/anime --verbose

        # Run with custom file extensions
        anivault run /path/to/anime --extensions "mkv,mp4"

        # Run and output results in JSON format
        anivault run /path/to/anime --json
    """
    # Call the run command
    run_command(
        directory,
        recursive,
        include_subtitles,
        include_metadata,
        output_file,
        dry_run,
        yes,
    )


@app.command("log")
def log_command_typer(
    command: str = typer.Argument(  # type: ignore[misc]
        ...,
        help="Log command to execute (list, show, tail)",
    ),
    log_dir: Path = typer.Option(  # type: ignore[misc]
        Path("logs"),
        "--log-dir",
        help="Directory containing log files",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
) -> None:
    """
    Manage and view log files.

    This command provides utilities for viewing and managing AniVault log files.
    It can list available log files, show log contents, and tail log files in real-time.

    Examples:
        # List all log files
        anivault log list

        # List log files in custom directory
        anivault log list --log-dir /custom/logs

        # Show log file contents
        anivault log show app.log

        # Tail log file in real-time
        anivault log tail app.log --follow
    """
    # Call the log command
    log_command(command, log_dir)


@app.command("rollback")
def rollback_command_typer(
    log_id: str = typer.Argument(  # type: ignore[misc]
        ...,
        help="ID of the operation log to rollback",
    ),
    dry_run: bool = typer.Option(  # type: ignore[misc]
        False,
        "--dry-run",
        help="Show what would be rolled back without actually moving files",
    ),
    yes: bool = typer.Option(  # type: ignore[misc]
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts and proceed with rollback",
    ),
) -> None:
    """
    Rollback file organization operations from a previous session.

    This command allows you to undo file organization operations by rolling back
    files to their original locations based on operation logs. It can show what
    would be rolled back without making changes using --dry-run.

    Examples:
        # Rollback operations from log ID "2024-01-15_143022"
        anivault rollback 2024-01-15_143022

        # Preview what would be rolled back without making changes
        anivault rollback 2024-01-15_143022 --dry-run

        # Rollback without confirmation prompts
        anivault rollback 2024-01-15_143022 --yes
    """
    # Call the rollback command
    rollback_command(log_id, dry_run, yes)


@app.command("verify")
def verify_command_typer(
    tmdb: bool = typer.Option(  # type: ignore[misc]
        False,
        "--tmdb",
        help="Verify TMDB API connectivity",
    ),
    all_components: bool = typer.Option(  # type: ignore[misc]
        False,
        "--all",
        help="Verify all components",
    ),
) -> None:
    """
    Verify system components and connectivity.

    This command allows you to verify that various system components are working
    correctly, including TMDB API connectivity and other system dependencies.

    Examples:
        # Verify TMDB API connectivity
        anivault verify --tmdb

        # Verify all components
        anivault verify --all

        # Verify with JSON output
        anivault verify --tmdb --json-output
    """
    # Call the verify command
    verify_command(tmdb, all_components)


if __name__ == "__main__":
    app()
