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
from anivault.shared.constants import (
    CLICommands,
    CLIDefaults,
    CLIHelp,
    CLIOptions,
    FileSystem,
)

# Version information
__version__ = CLIDefaults.VERSION


def version_callback(value: bool) -> None:
    """Print version information and exit."""
    if value:
        typer.echo(CLIHelp.VERSION_TEXT.format(version=__version__))
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
    name=CLIHelp.APP_NAME,
    help=CLIHelp.APP_DESCRIPTION,
    add_completion=True,  # Enable shell completion support
    rich_markup_mode=CLIHelp.APP_STYLE,  # Enable rich formatting
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
    """Main CLI callback with error handling."""
    try:
        # Process the common options
        main_callback(verbose, log_level, json_output, version)
    except Exception as e:
        # Import here to avoid circular imports
        from anivault.cli.common.error_handler import handle_cli_error

        exit_code = handle_cli_error(e, "main-callback", json_output)
        raise typer.Exit(exit_code) from e


@app.command(CLICommands.SCAN)
def scan_command_typer(
    directory: Path = typer.Argument(
        ...,
        help=CLIHelp.SCAN_DIRECTORY_HELP,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(
        True,
        CLIOptions.RECURSIVE,
        CLIOptions.RECURSIVE_SHORT,
        help=CLIHelp.SCAN_RECURSIVE_HELP,
    ),
    include_subtitles: bool = typer.Option(
        True,
        CLIOptions.INCLUDE_SUBTITLES,
        help=CLIHelp.SCAN_INCLUDE_SUBTITLES_HELP,
    ),
    include_metadata: bool = typer.Option(
        True,
        CLIOptions.INCLUDE_METADATA,
        help=CLIHelp.SCAN_INCLUDE_METADATA_HELP,
    ),
    output_file: Path | None = typer.Option(
        None,
        CLIOptions.OUTPUT,
        CLIOptions.OUTPUT_SHORT,
        help=CLIHelp.SCAN_OUTPUT_HELP,
        writable=True,
    ),
    json_output: bool = typer.Option(
        False,
        CLIOptions.JSON,
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


@app.command(CLICommands.MATCH)
def match_command_typer(
    directory: Path = typer.Argument(
        ...,
        help=CLIHelp.MATCH_DIRECTORY_HELP,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        CLIOptions.RECURSIVE_SHORT,
        help=CLIHelp.MATCH_RECURSIVE_HELP,
    ),
    include_subtitles: bool = typer.Option(
        True,
        "--include-subtitles/--no-include-subtitles",
        help=CLIHelp.MATCH_INCLUDE_SUBTITLES_HELP,
    ),
    include_metadata: bool = typer.Option(
        True,
        "--include-metadata/--no-include-metadata",
        help=CLIHelp.MATCH_INCLUDE_METADATA_HELP,
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output",
        CLIOptions.OUTPUT_SHORT,
        help="Output file for match results (JSON format)",
        writable=True,
    ),
    json_output: bool = typer.Option(
        False,
        CLIOptions.JSON,
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
        json_output,
    )


@app.command(CLICommands.ORGANIZE)
def organize_command_typer(
    directory: Path = typer.Argument(
        ...,
        help=CLIHelp.ORGANIZE_DIRECTORY_HELP,
        callback=create_validator(DirectoryPath),
    ),
    dry_run: bool = typer.Option(
        CLIDefaults.DEFAULT_DRY_RUN,
        CLIOptions.DRY_RUN,
        help=CLIHelp.ORGANIZE_DRY_RUN_HELP,
    ),
    yes: bool = typer.Option(
        CLIDefaults.DEFAULT_YES,
        CLIOptions.YES,
        CLIOptions.YES_SHORT,
        help=CLIHelp.ORGANIZE_YES_HELP,
    ),
    enhanced: bool = typer.Option(
        False,
        "--enhanced",
        help="Use enhanced organization with grouping and Korean titles",
    ),
    destination: str = typer.Option(
        CLIDefaults.DEFAULT_DESTINATION,
        CLIOptions.DESTINATION,
        CLIOptions.DESTINATION_SHORT,
        help=CLIHelp.ORGANIZE_DESTINATION_HELP,
    ),
    extensions: str = typer.Option(
        "mkv,mp4,avi,mov,wmv,flv,webm,m4v",
        "--extensions",
        help="Comma-separated list of video file extensions to process",
    ),
    json_output: bool = typer.Option(
        CLIDefaults.DEFAULT_JSON,
        CLIOptions.JSON,
        help=CLIHelp.ORGANIZE_JSON_HELP,
    ),
) -> None:
    # Call the organize command
    organize_command(
        directory,
        dry_run,
        yes,
        enhanced,
        destination,
        extensions,
        json_output,
    )


@app.command(CLICommands.RUN)
def run_command_typer(
    directory: Path = typer.Argument(
        ...,
        help=CLIHelp.RUN_DIRECTORY_HELP,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        CLIOptions.RECURSIVE_SHORT,
        help=CLIHelp.RUN_RECURSIVE_HELP,
    ),
    include_subtitles: bool = typer.Option(
        True,
        "--include-subtitles/--no-include-subtitles",
        help=CLIHelp.RUN_INCLUDE_SUBTITLES_HELP,
    ),
    include_metadata: bool = typer.Option(
        True,
        "--include-metadata/--no-include-metadata",
        help=CLIHelp.RUN_INCLUDE_METADATA_HELP,
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output",
        CLIOptions.OUTPUT_SHORT,
        help=CLIHelp.RUN_OUTPUT_HELP,
        writable=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help=CLIHelp.RUN_DRY_RUN_HELP,
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        CLIOptions.YES_SHORT,
        help=CLIHelp.RUN_YES_HELP,
    ),
    json_output: bool = typer.Option(
        False,
        CLIOptions.JSON,
        help=CLIHelp.RUN_JSON_HELP,
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


@app.command(CLICommands.LOG)
def log_command_typer(
    command: str = typer.Argument(
        ...,
        help=CLIHelp.LOG_HELP,
    ),
    log_dir: Path = typer.Option(
        Path(FileSystem.LOG_DIRECTORY),
        CLIOptions.LOG_DIR,
        help=CLIHelp.LOG_DIR_HELP,
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


@app.command(CLICommands.ROLLBACK)
def rollback_command_typer(
    log_id: str = typer.Argument(
        ...,
        help=CLIHelp.ROLLBACK_LOG_ID_HELP,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help=CLIHelp.ROLLBACK_DRY_RUN_HELP,
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        CLIOptions.YES_SHORT,
        help=CLIHelp.ROLLBACK_YES_HELP,
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


@app.command(CLICommands.VERIFY)
def verify_command_typer(
    tmdb: bool = typer.Option(
        False,
        "--tmdb",
        help=CLIHelp.VERIFY_TMDB_HELP,
    ),
    all_components: bool = typer.Option(
        False,
        "--all",
        help=CLIHelp.VERIFY_ALL_HELP,
    ),
) -> None:
    # Call the verify command
    verify_command(tmdb, all_components)


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        import logging
        import sys

        logger = logging.getLogger(__name__)
        logger.info("Command interrupted by user")
        sys.exit(1)
    except SystemExit:
        # Re-raise SystemExit to preserve exit codes
        raise
    except Exception as e:  # noqa: BLE001
        # Handle unexpected errors with structured logging
        import sys

        from anivault.cli.common.error_handler import handle_cli_error

        exit_code = handle_cli_error(e, "typer-app")
        sys.exit(exit_code)
