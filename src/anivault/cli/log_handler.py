"""Log command handler for AniVault CLI.

This module contains the business logic for the log command,
separated for better maintainability and single responsibility principle.
"""

import logging
from typing import Any

from anivault.shared.constants.system import (
    CLI_INFO_COMMAND_COMPLETED,
    CLI_INFO_COMMAND_STARTED,
)

logger = logging.getLogger(__name__)


def handle_log_command(args: Any) -> int:
    """Handle the log command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI_INFO_COMMAND_STARTED.format(command="log"))

    try:
        from rich.console import Console

        console = Console()

        if args.log_command == "list":
            result = _run_log_list_command_impl(args, console)
        else:
            console.print("[red]Error: No log command specified[/red]")
            result = 1

        if result == 0:
            logger.info(CLI_INFO_COMMAND_COMPLETED.format(command="log"))
        else:
            logger.error("Log command failed with exit code %s", result)

        return result

    except Exception as e:
        console.print(f"[red]Error during log operation: {e}[/red]")
        logger.exception("Error in log command")
        return 1


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
