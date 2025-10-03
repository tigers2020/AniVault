"""
Run command handler for AniVault CLI.

This module provides the implementation for the 'run' command, which orchestrates
the complete anime organization workflow (scan, match, organize) in sequence.
"""

import sys
from pathlib import Path
from typing import Any

from rich.console import Console

from anivault.cli.json_formatter import format_json_output
from anivault.cli.match_handler import handle_match_command
from anivault.cli.organize_handler import handle_organize_command
from anivault.cli.progress import create_progress_manager
from anivault.cli.scan_handler import _handle_scan_command
from anivault.shared.errors import ApplicationError
from anivault.shared.logging import get_logger

logger = get_logger(__name__)


def handle_run_command(args: Any) -> int:  # noqa: PLR0911
    """
    Handle the run command which orchestrates scan, match, and organize.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Validate directory
        from anivault.cli.common.context import get_cli_context, validate_directory

        try:
            directory = validate_directory(args.directory)
        except ApplicationError as e:
            context = get_cli_context()
            if context and context.is_json_output_enabled():
                json_output = format_json_output(
                    success=False,
                    command="run",
                    errors=[f"Application error: {e.message}"],
                    data={"error_code": e.code, "context": e.context},
                )
                sys.stdout.buffer.write(json_output)
                sys.stdout.buffer.write(b"\n")
                sys.stdout.buffer.flush()
            else:
                logger.exception("Application error: %s", e.message)
            return 1

        # Initialize console and progress manager
        console = Console()
        context = get_cli_context()
        progress_manager = create_progress_manager(
            disabled=context and context.is_json_output_enabled(),
        )

        # Collect run data for JSON output
        run_data = {
            "workflow_summary": {
                "directory": str(directory),
                "extensions": args.extensions,
                "dry_run": args.dry_run,
                "skip_scan": args.skip_scan,
                "skip_match": args.skip_match,
                "skip_organize": args.skip_organize,
                "max_workers": args.max_workers,
                "batch_size": args.batch_size,
            },
            "steps": [],
        }

        # Step 1: Scan (if not skipped)
        if not args.skip_scan:
            if not (context and context.is_json_output_enabled()):
                console.print(
                    "\n[bold blue]Step 1: Scanning for anime files...[/bold blue]",
                )

            with progress_manager.spinner("Scanning files..."):
                scan_result = _run_scan_step(args, directory, console)
                run_data["steps"].append(scan_result)

                if scan_result["status"] != "success":
                    return _handle_run_error("Scan step failed", run_data, args)

        # Step 2: Match (if not skipped)
        if not args.skip_match:
            if not (context and context.is_json_output_enabled()):
                console.print(
                    "\n[bold blue]Step 2: Matching files with TMDB...[/bold blue]",
                )

            with progress_manager.spinner("Matching files..."):
                match_result = _run_match_step(args, directory, console)
                run_data["steps"].append(match_result)

                if match_result["status"] != "success":
                    return _handle_run_error("Match step failed", run_data, args)

        # Step 3: Organize (if not skipped)
        if not args.skip_organize:
            if not (context and context.is_json_output_enabled()):
                console.print("\n[bold blue]Step 3: Organizing files...[/bold blue]")

            with progress_manager.spinner("Organizing files..."):
                organize_result = _run_organize_step(args, directory, console)
                run_data["steps"].append(organize_result)

                if organize_result["status"] != "success":
                    return _handle_run_error("Organize step failed", run_data, args)

        # Success - output results
        if context and context.is_json_output_enabled():
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
        if context and context.is_json_output_enabled():
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
        if context and context.is_json_output_enabled():
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


def _run_scan_step(args: Any, directory: Path, console: Console) -> dict[str, Any]:
    """
    Run the scan step of the workflow.

    Args:
        args: Parsed command line arguments
        directory: Directory to scan
        console: Rich console instance

    Returns:
        Dictionary containing scan step results
    """
    try:
        # Create scan args
        scan_args = _create_scan_args(args, directory)

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


def _run_match_step(args: Any, directory: Path, console: Console) -> dict[str, Any]:
    """
    Run the match step of the workflow.

    Args:
        args: Parsed command line arguments
        directory: Directory to match
        console: Rich console instance

    Returns:
        Dictionary containing match step results
    """
    try:
        # Create match args
        match_args = _create_match_args(args, directory)

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


def _run_organize_step(args: Any, directory: Path, console: Console) -> dict[str, Any]:
    """
    Run the organize step of the workflow.

    Args:
        args: Parsed command line arguments
        directory: Directory to organize
        console: Rich console instance

    Returns:
        Dictionary containing organize step results
    """
    try:
        # Create organize args
        organize_args = _create_organize_args(args, directory)

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


def _create_scan_args(args: Any, directory: Path) -> Any:
    """Create scan command arguments from run arguments."""

    class ScanArgs:
        def __init__(self, run_args, directory):
            self.directory = str(directory)
            self.extensions = run_args.extensions
            self.recursive = True
            self.verbose = getattr(run_args, "verbose", False)
            self.log_level = getattr(run_args, "log_level", "INFO")
            self.json = getattr(run_args, "json", False)

    return ScanArgs(args, directory)


def _create_match_args(args: Any, directory: Path) -> Any:
    """Create match command arguments from run arguments."""

    class MatchArgs:
        def __init__(self, run_args, directory):
            self.directory = str(directory)
            self.extensions = run_args.extensions
            self.recursive = True
            self.max_workers = run_args.max_workers
            self.batch_size = run_args.batch_size
            self.verbose = getattr(run_args, "verbose", False)
            self.log_level = getattr(run_args, "log_level", "INFO")
            self.json = getattr(run_args, "json", False)

    return MatchArgs(args, directory)


def _create_organize_args(args: Any, directory: Path) -> Any:
    """Create organize command arguments from run arguments."""

    class OrganizeArgs:
        def __init__(self, run_args, directory):
            self.directory = str(directory)
            self.extensions = run_args.extensions
            self.dry_run = run_args.dry_run
            self.yes = run_args.yes
            self.verbose = getattr(run_args, "verbose", False)
            self.log_level = getattr(run_args, "log_level", "INFO")
            self.json = getattr(run_args, "json", False)

    return OrganizeArgs(args, directory)


def _handle_run_error(error_message: str, run_data: dict[str, Any], args: Any) -> int:
    """
    Handle run workflow errors.

    Args:
        error_message: Error message to display
        run_data: Run data dictionary
        args: Parsed command line arguments

    Returns:
        Exit code (1 for error)
    """
    from anivault.cli.common.context import get_cli_context

    context = get_cli_context()
    if context and context.is_json_output_enabled():
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
