"""
Run command handler for AniVault CLI.

This module provides the implementation for the 'run' command, which orchestrates
the complete anime organization workflow (scan, match, organize) in sequence.
"""

import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.models import RunOptions
from anivault.cli.json_formatter import format_json_output
from anivault.cli.match_handler import handle_match_command
from anivault.cli.organize_handler import handle_organize_command
from anivault.cli.progress import create_progress_manager
from anivault.cli.scan_handler import _handle_scan_command
from anivault.shared.errors import ApplicationError, ErrorCode
from anivault.utils.logging_config import get_logger

logger = get_logger(__name__)


def handle_run_command(options: RunOptions) -> int:  # noqa: PLR0911  # noqa: PLR0911
    """
    Handle the run command which orchestrates scan, match, and organize.

    Args:
        options: Run command options

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Validate directory
        directory = options.directory.path
        if not directory.exists():
            error_msg = f"Directory does not exist: {directory}"
            if options.json_output:
                json_output = format_json_output(
                    success=False,
                    command="run",
                    errors=[error_msg],
                    data={
                        "error_code": ErrorCode.FILE_NOT_FOUND,
                        "directory": str(directory),
                    },
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                logger.error(error_msg)
            return 1

        if not directory.is_dir():
            error_msg = f"Path is not a directory: {directory}"
            if options.json_output:
                json_output = format_json_output(
                    success=False,
                    command="run",
                    errors=[error_msg],
                    data={
                        "error_code": ErrorCode.VALIDATION_ERROR,
                        "directory": str(directory),
                    },
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                logger.error(error_msg)
            return 1

        # Initialize console and progress manager
        console = Console()
        progress_manager = create_progress_manager(
            disabled=options.json_output,
        )

        # Collect run data for JSON output
        run_data = {
            "workflow_summary": {
                "directory": str(directory),
                "extensions": options.extensions,
                "dry_run": options.dry_run,
                "skip_scan": options.skip_scan,
                "skip_match": options.skip_match,
                "skip_organize": options.skip_organize,
                "max_workers": options.max_workers,
                "batch_size": options.batch_size,
            },
            "steps": [],
        }

        # Step 1: Scan (if not skipped)
        if not options.skip_scan:
            if not options.json_output:
                console.print(
                    "\n[bold blue]Step 1: Scanning for anime files...[/bold blue]",
                )

            with progress_manager.spinner("Scanning files..."):
                scan_result = _run_scan_step(options, directory, console)
                run_data["steps"].append(scan_result)

                if scan_result["status"] != "success":
                    return _handle_run_error("Scan step failed", run_data, options)

        # Step 2: Match (if not skipped)
        if not options.skip_match:
            if not options.json_output:
                console.print(
                    "\n[bold blue]Step 2: Matching files with TMDB...[/bold blue]",
                )

            with progress_manager.spinner("Matching files..."):
                match_result = _run_match_step(options, directory, console)
                run_data["steps"].append(match_result)

                if match_result["status"] != "success":
                    return _handle_run_error("Match step failed", run_data, options)

        # Step 3: Organize (if not skipped)
        if not options.skip_organize:
            if not options.json_output:
                console.print("\n[bold blue]Step 3: Organizing files...[/bold blue]")

            with progress_manager.spinner("Organizing files..."):
                organize_result = _run_organize_step(options, directory, console)
                run_data["steps"].append(organize_result)

                if organize_result["status"] != "success":
                    return _handle_run_error("Organize step failed", run_data, options)

        # Success - output results
        if options.json_output:
            json_output = format_json_output(success=True, command="run", data=run_data)
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            console.print(
                "\n[bold green]✓ Run workflow completed successfully![/bold green]",
            )
            _print_run_summary(run_data, console)

        return 0

    except ApplicationError as e:
        logger.exception("Application error in run command: %s", e.message)
        if options.json_output:
            json_output = format_json_output(
                success=False,
                command="run",
                errors=[f"Application error: {e.message}"],
                data={"error_code": e.code, "context": e.context},
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        return 1

    except Exception as e:
        logger.exception("Unexpected error in run command")
        if options.json_output:
            json_output = format_json_output(
                success=False,
                command="run",
                errors=[f"Unexpected error: {e!s}"],
                data={"error_type": type(e).__name__},
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        return 1


def _run_scan_step(
    options: RunOptions,
    directory: Path,
    console: Console,
) -> dict[str, Any]:
    """
    Run the scan step of the workflow.

    Args:
        options: Run command options
        directory: Directory to scan
        console: Rich console instance

    Returns:
        Dictionary containing scan step results
    """
    try:
        # Create scan args
        scan_args = _create_scan_args(options, directory)

        # Run scan command
        scan_exit_code = _handle_scan_command(scan_args)

        if scan_exit_code == 0:
            return {
                "step": "scan",
                "status": "success",
                "message": "Files scanned successfully",
            }
        return {
            "step": "scan",
            "status": "error",
            "message": "Scan command failed",
            "exit_code": scan_exit_code,
        }

    except Exception as e:
        logger.exception("Error in scan step")
        return {
            "step": "scan",
            "status": "error",
            "message": f"Scan step error: {e!s}",
        }


def _run_match_step(
    options: RunOptions,
    directory: Path,
    console: Console,
) -> dict[str, Any]:
    """
    Run the match step of the workflow.

    Args:
        options: Run command options
        directory: Directory to match
        console: Rich console instance

    Returns:
        Dictionary containing match step results
    """
    try:
        # Create match args
        match_args = _create_match_args(options, directory)

        # Run match command
        match_exit_code = handle_match_command(match_args)

        if match_exit_code == 0:
            return {
                "step": "match",
                "status": "success",
                "message": "Files matched successfully",
            }
        return {
            "step": "match",
            "status": "error",
            "message": "Match command failed",
            "exit_code": match_exit_code,
        }

    except Exception as e:
        logger.exception("Error in match step")
        return {
            "step": "match",
            "status": "error",
            "message": f"Match step error: {e!s}",
        }


def _run_organize_step(
    options: RunOptions,
    directory: Path,
    console: Console,
) -> dict[str, Any]:
    """
    Run the organize step of the workflow.

    Args:
        options: Run command options
        directory: Directory to organize
        console: Rich console instance

    Returns:
        Dictionary containing organize step results
    """
    try:
        # Create organize args
        organize_args = _create_organize_args(options, directory)

        # Run organize command
        organize_exit_code = handle_organize_command(organize_args)

        if organize_exit_code == 0:
            return {
                "step": "organize",
                "status": "success",
                "message": "Files organized successfully",
            }
        return {
            "step": "organize",
            "status": "error",
            "message": "Organize command failed",
            "exit_code": organize_exit_code,
        }

    except Exception as e:
        logger.exception("Error in organize step")
        return {
            "step": "organize",
            "status": "error",
            "message": f"Organize step error: {e!s}",
        }


def _create_scan_args(options: RunOptions, directory: Path) -> Any:
    """Create scan command arguments from run arguments."""

    class ScanArgs:
        def __init__(self, run_options, directory):
            self.directory = str(directory)
            self.extensions = run_options.extensions
            self.recursive = True
            self.verbose = getattr(run_options, "verbose", False)
            self.log_level = getattr(run_options, "log_level", "INFO")
            self.json = getattr(run_options, "json_output", False)
            self.no_enrich = False  # Default to enrich metadata
            self.workers = getattr(
                run_options,
                "max_workers",
                4,
            )  # Default to 4 workers
            self.rate_limit = getattr(
                run_options,
                "rate_limit",
                50,
            )  # Default to 50 requests per second
            self.concurrent = getattr(
                run_options,
                "max_workers",
                4,
            )  # Default to 4 concurrent operations
            self.output = None  # Default to no output file

    return ScanArgs(options, directory)


def _create_match_args(options: RunOptions, directory: Path) -> Any:
    """Create match command arguments from run arguments."""

    class MatchArgs:
        def __init__(self, run_options, directory):
            self.directory = str(directory)
            self.extensions = run_options.extensions
            self.recursive = True
            self.max_workers = run_options.max_workers
            self.batch_size = run_options.batch_size
            self.verbose = getattr(run_options, "verbose", False)
            self.log_level = getattr(run_options, "log_level", "INFO")
            self.json = getattr(run_options, "json_output", False)
            self.cache_dir = "cache"  # Default cache directory
            self.rate_limit = getattr(
                run_options,
                "rate_limit",
                50,
            )  # Default to 50 requests per second
            self.concurrent = getattr(
                run_options,
                "max_workers",
                4,
            )  # Default to 4 concurrent operations
            self.workers = getattr(
                run_options,
                "max_workers",
                4,
            )  # Default to 4 workers

    return MatchArgs(options, directory)


def _create_organize_args(options: RunOptions, directory: Path) -> Any:
    """Create organize command arguments from run arguments."""

    class OrganizeArgs:
        def __init__(self, run_options, directory):
            self.directory = str(directory)
            self.extensions = run_options.extensions
            self.dry_run = run_options.dry_run
            self.yes = run_options.yes
            self.verbose = getattr(run_options, "verbose", False)
            self.log_level = getattr(run_options, "log_level", "INFO")
            self.json = getattr(run_options, "json_output", False)

    return OrganizeArgs(options, directory)


def _handle_run_error(
    error_message: str,
    run_data: dict[str, Any],
    options: RunOptions,
) -> int:
    """
    Handle run workflow errors.

    Args:
        error_message: Error message to display
        run_data: Run data dictionary
        options: Run command options

    Returns:
        Exit code (1 for error)
    """
    if options.json_output:
        json_output = format_json_output(
            success=False,
            command="run",
            errors=[error_message],
            data=run_data,
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        logger.error(error_message)

    return 1


def _print_run_summary(run_data: dict[str, Any], console: Console) -> None:
    """
    Print a summary of the run workflow results.

    Args:
        run_data: Run data dictionary
        console: Rich console instance
    """
    console.print("\n[bold]Workflow Summary:[/bold]")

    workflow_summary = run_data["workflow_summary"]
    console.print(f"  Directory: {workflow_summary['directory']}")
    console.print(f"  Extensions: {', '.join(workflow_summary['extensions'])}")
    console.print(f"  Dry Run: {workflow_summary['dry_run']}")
    console.print(f"  Max Workers: {workflow_summary['max_workers']}")
    console.print(f"  Batch Size: {workflow_summary['batch_size']}")

    console.print("\n[bold]Steps Completed:[/bold]")
    for step in run_data["steps"]:
        status_icon = "✓" if step["status"] == "success" else "✗"
        status_color = "green" if step["status"] == "success" else "red"
        console.print(
            f"  {status_icon} {step['step'].title()}: "
            f"[{status_color}]{step['status']}[/{status_color}] - {step['message']}",
        )


def run_command(
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
    try:
        # Get CLI context for global options
        context = get_cli_context()

        # Validate arguments using Pydantic model
        from anivault.cli.common.models import DirectoryPath

        run_options = RunOptions(
            directory=DirectoryPath(path=directory),
            recursive=recursive,
            include_subtitles=include_subtitles,
            include_metadata=include_metadata,
            dry_run=dry_run,
            yes=yes,
            json_output=bool(json),
            verbose=context.verbose if context else 0,
        )

        # Call the handler with Pydantic model
        exit_code = handle_run_command(run_options)

        if exit_code != 0:
            raise typer.Exit(exit_code)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)
