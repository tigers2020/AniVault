"""Log command helper functions.

This module contains the core business logic for the log command,
extracted for better maintainability and reusability.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from anivault.shared.constants import FileSystem
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)

if TYPE_CHECKING:
    from rich.console import Console

logger = logging.getLogger(__name__)


def collect_log_list_data(log_dir: Path) -> dict[str, Any]:
    """Collect log list data for JSON output.

    Args:
        log_dir: Log directory path

    Returns:
        Dictionary containing log list data

    Raises:
        InfrastructureError: If file system access fails
        ApplicationError: If data processing fails
    """
    try:
        # Check if log directory exists
        if not log_dir.exists():
            return {
                "error": f"Log directory does not exist: {log_dir}",
                "log_files": [],
                "total_files": 0,
            }

        # Find log files
        log_files = list(log_dir.glob(FileSystem.LOG_FILE_PATTERN))
        if not log_files:
            return {
                "message": "No log files found",
                "log_files": [],
                "total_files": 0,
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
            size_str = _format_file_size(size)

            # Format modification time
            modified_str = datetime.fromtimestamp(modified, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            log_data.append(
                {
                    "file": log_file.name,
                    "size": size_str,
                    "size_bytes": size,
                    "modified": modified_str,
                    "modified_timestamp": modified,
                }
            )

        return {
            "log_files": log_data,
            "total_files": len(log_data),
        }

    except OSError as e:
        raise InfrastructureError(
            code=ErrorCode.FILE_ACCESS_ERROR,
            message=f"Failed to access log files: {e}",
            context=ErrorContext(
                operation="collect_log_list_data",
                additional_data={
                    "log_dir": str(log_dir),
                    "error_type": type(e).__name__,
                },
            ),
            original_error=e,
        ) from e
    except (ValueError, KeyError, AttributeError) as e:
        raise ApplicationError(
            code=ErrorCode.DATA_PROCESSING_ERROR,
            message=f"Failed to process log data: {e}",
            context=ErrorContext(
                operation="collect_log_list_data",
                additional_data={
                    "log_dir": str(log_dir),
                    "error_type": type(e).__name__,
                },
            ),
            original_error=e,
        ) from e


def print_log_list(log_dir: Path, console: Console) -> int:
    """Print log list to console.

    Args:
        log_dir: Log directory path
        console: Rich console instance

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        from rich.table import Table

        # Check if log directory exists
        if not log_dir.exists():
            console.print(f"[red]Log directory does not exist: {log_dir}[/red]")
            return 1

        # Find log files
        log_files = list(log_dir.glob(FileSystem.LOG_FILE_PATTERN))
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
            size_str = _format_file_size(size)

            # Format modification time
            modified_str = datetime.fromtimestamp(modified, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            table.add_row(log_file.name, size_str, modified_str)

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[red]Error listing log files: {e}[/red]")
        logger.exception("Log list error")
        return 1


def _format_file_size(size: int) -> str:
    """Format file size in human-readable format.

    Args:
        size: File size in bytes

    Returns:
        Formatted file size string
    """
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
