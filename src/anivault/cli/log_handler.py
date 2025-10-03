"""Log command handler for AniVault CLI.

This module contains the business logic for the log command,
separated for better maintainability and single responsibility principle.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

from anivault.cli.common_options import is_json_output_enabled
from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants import CLI

logger = logging.getLogger(__name__)


def handle_log_command(args: Any) -> int:
    """Handle the log command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI.INFO_COMMAND_STARTED.format(command="log"))

    try:
        if is_json_output_enabled(args):
            return _handle_log_command_json(args)
        return _handle_log_command_console(args)

    except Exception as e:
        if is_json_output_enabled(args):
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


def _handle_log_command_json(args: Any) -> int:
    """Handle log command with JSON output.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        if args.log_command == "list":
            log_data = _collect_log_list_data(args)
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


def _handle_log_command_console(args: Any) -> int:
    """Handle log command with console output.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        from rich.console import Console

        console = Console()

        if args.log_command == "list":
            result = _run_log_list_command_impl(args, console)
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


def _collect_log_list_data(args: Any) -> dict | None:
    """Collect log list data for JSON output.

    Args:
        args: Parsed command line arguments

    Returns:
        Dictionary containing log list data, or None if error
    """
    try:
        from pathlib import Path

        # Get log directory
        log_dir = Path(args.log_dir)
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


def _run_log_list_command_impl(args, console) -> int:
    """Run the log list command.

    Args:
        args: Parsed command line arguments
        console: Rich console instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        from pathlib import Path

        from rich.table import Table

        # Get log directory
        log_dir = Path(args.log_dir)
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
