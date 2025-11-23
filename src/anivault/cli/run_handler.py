"""Run command handler for AniVault CLI.

Refactored to use decorator pattern for cleaner, more maintainable code.
This module orchestrates the complete workflow (scan, match, organize).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.common.path_utils import extract_directory_path
from anivault.cli.common.setup_decorator import setup_handler
from anivault.cli.json_formatter import format_json_output
from anivault.cli.match_handler import handle_match_command
from anivault.cli.organize_handler import handle_organize_command
from anivault.cli.scan_handler import handle_scan_command
from anivault.core.statistics import get_statistics_collector
from anivault.shared.constants import CLI, CLIDefaults
from anivault.shared.constants.cli import CLIFormatting, CLIMessages
from anivault.shared.types.cli import (
    CLIDirectoryPath,
    MatchOptions,
    OrganizeOptions,
    RunOptions,
    ScanOptions,
)

logger = logging.getLogger(__name__)


@setup_handler(requires_directory=True, supports_json=True, allow_dry_run=True)
@handle_cli_errors(operation="handle_run", command_name="run")
def handle_run_command(options: RunOptions, **kwargs: Any) -> int:
    """Handle the run command which orchestrates scan, match, and organize.

    Args:
        options: Validated run command options
        **kwargs: Injected by decorators (console, logger_adapter)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    from rich.console import Console as RichConsole

    console: Console = kwargs.get("console") or RichConsole()
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(
        CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.RUN)
    )

    # Extract directory path
    directory = extract_directory_path(options.directory)

    # Check if JSON output and benchmark mode are enabled
    context = get_cli_context()
    is_json_output = bool(context and context.is_json_output_enabled())
    is_benchmark = bool(context and context.is_benchmark_enabled())

    # Initialize statistics collector for benchmark mode
    stats_collector = get_statistics_collector() if is_benchmark else None

    # Initialize run data for tracking
    run_data: dict[str, Any] = {
        "workflow_summary": {
            CLIMessages.StatusKeys.DIRECTORY: str(directory),
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

    # Define pipeline steps
    pipeline_steps = [
        ("scan", options.skip_scan, "Scanning for anime files", _execute_scan_step),
        ("match", options.skip_match, "Matching files with TMDB", _execute_match_step),
        (
            "organize",
            options.skip_organize,
            "Organizing files",
            _execute_organize_step,
        ),
    ]

    # Execute pipeline steps
    for step_name, should_skip, step_message, step_func in pipeline_steps:
        if should_skip:
            continue

        # Print step header (console mode only)
        if not is_json_output:
            step_number = len(run_data["steps"]) + 1
            console.print(
                CLIFormatting.format_colored_message(
                    f"\nStep {step_number}: {step_message}...",
                    "info",
                )
            )

        # Start timing for benchmark mode
        if is_benchmark and stats_collector:
            stats_collector.start_timing(step_name)

        # Execute step
        step_result = step_func(options, directory, console)

        # End timing for benchmark mode
        if is_benchmark and stats_collector:
            stats_collector.end_timing(step_name)

        run_data["steps"].append(step_result)

        # Check for errors
        if step_result[CLIMessages.StatusKeys.STATUS] != "success":
            error_message = f"{step_name.title()} step failed"
            if is_json_output:
                _output_json_error(error_message, run_data)
            else:
                logger_adapter.error(error_message)
            return CLIDefaults.EXIT_ERROR

    # Calculate and display benchmark results if enabled
    if is_benchmark and stats_collector:
        _display_benchmark_results(stats_collector, console, is_json_output, run_data)

    # Success - output results
    if is_json_output:
        json_output = format_json_output(
            success=True,
            command=CLIMessages.CommandNames.RUN,
            data=run_data,
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        console.print(
            CLIFormatting.format_colored_message(
                "\n✓ Run workflow completed successfully!",
                "success",
            )
        )
        _print_run_summary(run_data, console)

    logger_adapter.info(
        CLI.INFO_COMMAND_COMPLETED.format(command=CLIMessages.CommandNames.RUN)
    )
    return CLIDefaults.EXIT_SUCCESS


def _execute_scan_step(
    options: RunOptions,
    directory: Path,
    console: Console,
) -> dict[str, Any]:
    """Execute scan step.

    Args:
        options: Run command options
        directory: Directory to scan
        console: Rich console instance

    Returns:
        Step result dictionary
    """
    try:
        scan_options = ScanOptions(
            directory=CLIDirectoryPath(path=directory),
            recursive=True,
            include_subtitles=options.include_subtitles,
            include_metadata=options.include_metadata,
            output=options.output,
            json_output=options.json_output,
        )

        exit_code = handle_scan_command(scan_options, console=console)

        if exit_code == CLIDefaults.EXIT_SUCCESS:
            return {
                CLIMessages.StatusKeys.STEP: "scan",
                CLIMessages.StatusKeys.STATUS: "success",
                "message": "Files scanned successfully",
            }
        return {
            CLIMessages.StatusKeys.STEP: "scan",
            CLIMessages.StatusKeys.STATUS: "error",
            "message": "Scan command failed",
            "exit_code": exit_code,
        }

    except Exception as e:
        logger.exception("Error in scan step")
        return {
            "step": "scan",
            "status": "error",
            "message": f"Scan step error: {e!s}",
        }


def _execute_match_step(
    options: RunOptions,
    directory: Path,
    console: Console,
) -> dict[str, Any]:
    """Execute match step.

    Args:
        options: Run command options
        directory: Directory to match
        console: Rich console instance

    Returns:
        Step result dictionary
    """
    try:
        match_options = MatchOptions(
            directory=CLIDirectoryPath(path=directory),
            recursive=True,
            include_subtitles=options.include_subtitles,
            include_metadata=options.include_metadata,
            output=options.output,
            json_output=options.json_output,
            verbose=bool(options.verbose),
        )

        exit_code = handle_match_command(match_options, console=console)

        if exit_code == CLIDefaults.EXIT_SUCCESS:
            return {
                "step": "match",
                "status": "success",
                "message": "Files matched successfully",
            }
        return {
            "step": "match",
            "status": "error",
            "message": "Match command failed",
            "exit_code": exit_code,
        }

    except Exception as e:
        logger.exception("Error in match step")
        return {
            "step": "match",
            "status": "error",
            "message": f"Match step error: {e!s}",
        }


def _execute_organize_step(
    options: RunOptions,
    directory: Path,
    console: Console,
) -> dict[str, Any]:
    """Execute organize step.

    Args:
        options: Run command options
        directory: Directory to organize
        console: Rich console instance

    Returns:
        Step result dictionary
    """
    try:
        organize_options = OrganizeOptions(
            directory=CLIDirectoryPath(path=directory),
            dry_run=options.dry_run,
            yes=options.yes,
            enhanced=False,  # Default to standard organization
            destination="Anime",  # Default destination
            extensions=",".join(
                options.extensions
            ),  # Convert list to comma-separated string
            json_output=options.json_output,
        )

        exit_code = handle_organize_command(organize_options, console=console)

        if exit_code == CLIDefaults.EXIT_SUCCESS:
            return {
                "step": "organize",
                "status": "success",
                "message": "Files organized successfully",
            }
        return {
            "step": "organize",
            "status": "error",
            "message": "Organize command failed",
            "exit_code": exit_code,
        }

    except Exception as e:
        logger.exception("Error in organize step")
        return {
            "step": "organize",
            "status": "error",
            "message": f"Organize step error: {e!s}",
        }


def _output_json_error(error_message: str, run_data: dict[str, Any]) -> None:
    """Output JSON error.

    Args:
        error_message: Error message
        run_data: Run data dictionary
    """
    json_output = format_json_output(
        success=False,
        command="run",
        errors=[error_message],
        data=run_data,
    )
    sys.stdout.buffer.write(json_output)
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def _display_benchmark_results(
    stats_collector: Any,
    console: Console,
    is_json_output: bool,
    run_data: dict[str, Any],
) -> None:
    """Display benchmark results with timing and throughput.

    Args:
        stats_collector: Statistics collector instance
        console: Rich console instance
        is_json_output: Whether JSON output is enabled
        run_data: Run data dictionary to update with benchmark info
    """
    timers = stats_collector.timers
    total_time = sum(timers.values())

    # Calculate total files processed (from metrics)
    total_files = stats_collector.metrics.total_files
    files_per_second = total_files / total_time if total_time > 0 else 0.0

    # Add benchmark data to run_data
    run_data["benchmark"] = {
        "timers": timers,
        "total_time": total_time,
        "total_files": total_files,
        "files_per_second": files_per_second,
    }

    if is_json_output:
        # JSON output is handled by the main output function
        return

    # Display benchmark results in console
    console.print("\n[bold cyan]Benchmark Results:[/bold cyan]")
    console.print("\n[bold]Step Timings:[/bold]")
    for step_name, duration in timers.items():
        console.print(f"  {step_name.title()}: {duration:.3f}s")

    console.print(f"\n[bold]Total Time:[/bold] {total_time:.3f}s")
    console.print(f"[bold]Total Files:[/bold] {total_files}")
    console.print(f"[bold]Throughput:[/bold] {files_per_second:.2f} files/second")


def _print_run_summary(run_data: dict[str, Any], console: Console) -> None:
    """Print workflow summary.

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
            f"[{status_color}]{step['status']}[/{status_color}] - {step['message']}"
        )


def run_command(
    directory: Path = typer.Argument(
        ...,
        help="Directory containing anime files to process",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        "-r",
        help="Process files recursively in subdirectories",
    ),
    include_subtitles: bool = typer.Option(
        True,
        "--include-subtitles/--no-include-subtitles",
        help="Include subtitle files in processing",
    ),
    include_metadata: bool = typer.Option(
        True,
        "--include-metadata/--no-include-metadata",
        help="Include metadata files in processing",
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file for processing results (JSON format)",
        writable=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be processed without actually processing files",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts and proceed with processing",
    ),
    json: bool = typer.Option(
        False,
        "--json",
        help="Output results in JSON format",
    ),
) -> None:
    """Run the complete anime organization workflow (scan, match, organize).

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
        run_options = RunOptions(
            directory=CLIDirectoryPath(path=directory),
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

        if exit_code != CLIDefaults.EXIT_SUCCESS:
            raise typer.Exit(exit_code)

    except ValueError as e:
        logger.exception("Validation error")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(CLIDefaults.EXIT_ERROR) from e
