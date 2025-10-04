"""Log command handler for AniVault CLI.

This module contains the business logic for the log command,
separated for better maintainability and single responsibility principle.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import typer

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.models import LogOptions, DirectoryPath
from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants import CLI

logger = logging.getLogger(__name__)


def handle_log_command(options: LogOptions) -> int:
    """Handle the log command.

    Args:
        options: Validated log command options

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI.INFO_COMMAND_STARTED.format(command="log"))

    try:
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            return _handle_log_command_json(options)
        return _handle_log_command_console(options)

    except Exception as e:
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command="log",
                errors=[f"Error during log operation: {e}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        else:
            from rich.console import Console

            console = Console()
            console.print(f"[red]Error during log operation: {e}[/red]")
        logger.exception("Error in log command")
        return 1


def _handle_log_command_json(options: LogOptions) -> int:
    """Handle log command with JSON output.

    Args:
        options: Validated log command options

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        if options.log_command == "list":
            log_data = _collect_log_list_data(options)
            if log_data is None:
                return 1

            output = format_json_output(
                success=True,
                command="log",
                data=log_data,
            )
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.write(b"\n")
            return 0
        error_output = format_json_output(
            success=False,
            command="log",
            errors=["No log command specified"],
        )
        sys.stdout.buffer.write(error_output)
        sys.stdout.buffer.write(b"\n")
        return 1

    except Exception as e:
        error_output = format_json_output(
            success=False,
            command="log",
            errors=[f"Error during log operation: {e}"],
        )
        sys.stdout.buffer.write(error_output)
        sys.stdout.buffer.write(b"\n")
        logger.exception("Error in log command JSON output")
        return 1


def _handle_log_command_console(options: LogOptions) -> int:
    """Handle log command with console output.

    Args:
        options: Validated log command options

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        from rich.console import Console

        console = Console()

        if options.log_command == "list":
            result = _run_log_list_command_impl(options, console)
        else:
            console.print("[red]Error: No log command specified[/red]")
            result = 1

        if result == 0:
            logger.info(CLI.INFO_COMMAND_COMPLETED.format(command="log"))
        else:
            logger.error("Log command failed with exit code %s", result)

        return result

    except Exception as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Error during log operation: {e}[/red]")
        logger.exception("Error in log command")
        return 1


def _collect_log_list_data(options: LogOptions) -> dict | None:
    """Collect log list data for JSON output.

    Args:
        options: Validated log command options

    Returns:
        Dictionary containing log list data, or None if error
    """
    try:
        from pathlib import Path

        # Get log directory
        log_dir = options.log_dir.path
        if not log_dir.exists():
            return {
                "error": f"Log directory does not exist: {log_dir}",
                "log_files": [],
            }

        # Find log files
        log_files = list(log_dir.glob("*.log"))
        if not log_files:
            return {
                "message": "No log files found",
                "log_files": [],
            }

        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Collect file information
        log_data = []
        for log_file in log_files:
            stat = log_file.stat()
            size = stat.st_size
            modified = stat.st_mtime

            # Format size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            # Format modification time
            from datetime import datetime, timezone

            modified_str = datetime.fromtimestamp(modified, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S",
            )

            log_data.append(
                {
                    "file": log_file.name,
                    "size": size_str,
                    "size_bytes": size,
                    "modified": modified_str,
                    "modified_timestamp": modified,
                },
            )

        return {
            "log_files": log_data,
            "total_files": len(log_data),
        }

    except Exception:
        logger.exception("Error collecting log list data")
        return None


def _run_log_list_command_impl(options: LogOptions, console) -> int:
    """Run the log list command.

    Args:
        options: Validated log command options
        console: Rich console instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        from pathlib import Path

        from rich.table import Table

        # Get log directory
        log_dir = options.log_dir.path
        if not log_dir.exists():
            console.print(f"[red]Log directory does not exist: {log_dir}[/red]")
            return 1

        # Find log files
        log_files = list(log_dir.glob("*.log"))
        if not log_files:
            console.print("[yellow]No log files found[/yellow]")
            return 0

        # Create table
        table = Table(title="Log Files")
        table.add_column("File", style="cyan")
        table.add_column("Size", style="blue")
        table.add_column("Modified", style="green")

        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Add rows
        for log_file in log_files:
            stat = log_file.stat()
            size = stat.st_size
            modified = stat.st_mtime

            # Format size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"

            # Format modification time
            from datetime import datetime, timezone

            modified_str = datetime.fromtimestamp(modified, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S",
            )

            table.add_row(
                log_file.name,
                size_str,
                modified_str,
            )

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[red]Error listing log files: {e}[/red]")
        logger.exception("Log list error")
        return 1


def log_command(
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
    try:
        # Create and validate options using Pydantic
        options = LogOptions(
            log_command=command,
            log_dir=DirectoryPath(path=log_dir)
        )
        
        # Call the handler with validated options
        exit_code = handle_log_command(options)
        
        if exit_code != 0:
            raise typer.Exit(exit_code)
            
    except Exception as e:
        # Handle validation errors
        from rich.console import Console
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
