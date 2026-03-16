"""Organize command helper functions.

Formatter/util only — confirmation, progress display, and result formatting.
All UseCase orchestration (scan, generate_plan, execute_plan) lives in organize_handler.py.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from rich.console import Console
from rich.prompt import Confirm

from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants.cli import CLIMessages
from anivault.shared.types.cli import OrganizeOptions

from anivault.cli.helpers.organize_formatters import (
    collect_organize_data,
    print_dry_run_plan,
    print_execution_plan,
)

if TYPE_CHECKING:
    from anivault.core.models import FileOperation
    from anivault.core.organizer.executor import OperationResult

logger = logging.getLogger(__name__)

__all__ = [
    "collect_organize_data",
    "confirm_organization",
    "print_dry_run_plan",
    "print_execution_plan",
    "print_organization_results",
]


def confirm_organization(console: Console) -> bool:
    """Ask user for confirmation before executing organization.

    Args:
        console: Rich console

    Returns:
        True if the user confirms, False otherwise
    """
    try:
        if not Confirm.ask("Do you want to proceed?"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return False
        return True
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/yellow]")
        return False


def print_organization_results(
    plan: list[FileOperation],
    options: OrganizeOptions,
    console: Console,
    moved_files: list[OperationResult] | None = None,
    operation_id: str | None = None,
    log_path: str | None = None,
) -> None:
    """Emit organization results as JSON or rich output.

    Receives already-executed results and formats them — no I/O side effects beyond
    printing. Log saving (OperationLogManager) happens in organize_handler before
    this function is called; the saved path is forwarded via log_path.

    Args:
        plan: Organization plan
        options: Organize command options
        console: Rich console
        moved_files: Execution results (None for dry-run)
        operation_id: Operation identifier string
        log_path: Path where the operation log was saved (displayed when not None)
    """
    if options.json_output:
        organize_data = collect_organize_data(
            plan,
            options,
            moved_files=moved_files,
            operation_id=operation_id,
        )
        json_output = format_json_output(
            success=True,
            command=CLIMessages.CommandNames.ORGANIZE,
            data=organize_data,
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
        return

    # TTY output
    if moved_files:
        console.print("\n[bold blue]File Organization Results:[/bold blue]")
        for result in moved_files:
            from pathlib import Path

            if result.success:
                console.print(f"[green]✅[/green] {Path(result.source_path).name}")
            else:
                console.print(
                    f"[red]❌[/red] {Path(result.source_path).name}: {result.message or 'Failed'}"
                )
        console.print()
        console.print(f"[green]Successfully organized {len(moved_files)} files[/green]")
        if log_path:
            console.print(f"[grey62]Operation logged to: {log_path}[/grey62]")
    else:
        console.print("[yellow]No files were moved[/yellow]")
