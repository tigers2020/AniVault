"""Rollback command helper functions.

This module contains the core business logic for the rollback command,
extracted for better maintainability and reusability.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from anivault.core.log_manager import LogFileNotFoundError, OperationLogManager
from anivault.core.models import FileOperation
from anivault.core.rollback_manager import RollbackManager
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)

if TYPE_CHECKING:
    from rich.console import Console

logger = logging.getLogger(__name__)


def load_rollback_log(log_id: str) -> Path:
    """Load rollback log by ID.

    Args:
        log_id: Operation log ID

    Returns:
        Path to rollback log file

    Raises:
        ApplicationError: If log not found
        InfrastructureError: If log file access fails
    """
    try:
        log_manager = OperationLogManager(Path.cwd())
        log_path = log_manager.get_log_by_id(log_id)
        return log_path

    except LogFileNotFoundError as e:
        raise ApplicationError(
            code=ErrorCode.FILE_NOT_FOUND,
            message=f"Rollback log with ID '{log_id}' not found",
            context=ErrorContext(
                operation="load_rollback_log",
                additional_data={"log_id": log_id},
            ),
            original_error=e,
        ) from e
    except OSError as e:
        raise InfrastructureError(
            code=ErrorCode.FILE_ACCESS_ERROR,
            message=f"Failed to access rollback log: {e}",
            context=ErrorContext(
                operation="load_rollback_log",
                additional_data={"log_id": log_id},
            ),
            original_error=e,
        ) from e


def generate_rollback_plan(log_path: Path) -> list[FileOperation]:
    """Generate rollback plan from log file.

    Args:
        log_path: Path to rollback log file

    Returns:
        List of FileOperation objects

    Raises:
        ApplicationError: If plan generation fails
        InfrastructureError: If log file cannot be read
    """
    try:
        log_manager = OperationLogManager(Path.cwd())
        rollback_manager = RollbackManager(log_manager)
        rollback_plan = rollback_manager.generate_rollback_plan(str(log_path))

        if rollback_plan is None:
            raise ApplicationError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Failed to generate rollback plan from log: {log_path}",
                context=ErrorContext(
                    file_path=str(log_path),
                    operation="generate_rollback_plan",
                ),
            )

        return rollback_plan

    except (ApplicationError, InfrastructureError):
        raise
    except OSError as e:
        raise InfrastructureError(
            code=ErrorCode.FILE_READ_ERROR,
            message=f"Failed to read rollback log file: {e}",
            context=ErrorContext(
                file_path=str(log_path),
                operation="generate_rollback_plan",
            ),
            original_error=e,
        ) from e


def validate_rollback_plan(
    rollback_plan: list[FileOperation],
) -> tuple[list[FileOperation], list[FileOperation]]:
    """Validate rollback plan and partition operations.

    Args:
        rollback_plan: List of FileOperation objects

    Returns:
        Tuple of (executable_plan, skipped_operations)
    """
    executable_plan: list[FileOperation] = []
    skipped_operations: list[FileOperation] = []

    for operation in rollback_plan:
        if Path(operation.source_path).exists():
            executable_plan.append(operation)
        else:
            skipped_operations.append(operation)

    return executable_plan, skipped_operations


def execute_rollback_plan(
    rollback_plan: list[FileOperation],
    log_id: str,
    console: Console,
) -> int:
    """Execute rollback plan.

    Args:
        rollback_plan: List of FileOperation objects to execute
        log_id: Operation log ID for tracking
        console: Rich console for output

    Returns:
        Number of files moved

    Raises:
        ApplicationError: If execution fails
        InfrastructureError: If file operations fail
    """
    try:
        from anivault.core.organizer import FileOrganizer

        log_manager = OperationLogManager(Path.cwd())
        organizer = FileOrganizer(log_manager=log_manager)

        console.print("[blue]Executing rollback...[/blue]")
        moved_files = organizer.execute_plan(rollback_plan)

        if moved_files:
            console.print(
                f"[green]Successfully rolled back {len(moved_files)} files[/green]"
            )
        else:
            console.print("[yellow]No files were moved during rollback[/yellow]")

        return len(moved_files)

    except (ApplicationError, InfrastructureError):
        raise
    except Exception as e:
        raise ApplicationError(
            code=ErrorCode.CLI_ROLLBACK_EXECUTION_FAILED,
            message="Failed to execute rollback plan",
            context=ErrorContext(
                operation="execute_rollback_plan",
                additional_data={"plan_size": len(rollback_plan)},
            ),
            original_error=e,
        ) from e


def print_rollback_dry_run_plan(plan: list[FileOperation], console: Console) -> None:
    """Print rollback dry run plan.

    Args:
        plan: List of FileOperation objects
        console: Rich console for output
    """
    if not plan:
        console.print("[yellow][DRY RUN] No rollback operations are needed.[/yellow]")
        return

    console.print("[bold blue][DRY RUN] Planned rollback operations:[/bold blue]")
    console.print()

    for i, operation in enumerate(plan, 1):
        console.print(
            f"[cyan]{i:3d}.[/cyan] [green]MOVE:[/green] "
            f"'{operation.source_path}' -> '{operation.destination_path}'"
        )

    console.print()
    console.print(f"[bold]Total operations: {len(plan)}[/bold]")


def print_rollback_execution_plan(plan: list[FileOperation], console: Console) -> None:
    """Print rollback execution plan.

    Args:
        plan: List of FileOperation objects
        console: Rich console for output
    """
    if not plan:
        console.print("[yellow]No rollback operations are needed.[/yellow]")
        return

    console.print(
        "[bold blue]The following rollback operations will be performed:[/bold blue]"
    )
    console.print()

    for i, operation in enumerate(plan, 1):
        console.print(
            f"[cyan]{i:3d}.[/cyan] [green]MOVE:[/green] "
            f"'{operation.source_path}' -> '{operation.destination_path}'"
        )

    console.print()
    console.print(f"[bold]Total operations: {len(plan)}[/bold]")


def print_skipped_operations(
    skipped_operations: list[FileOperation],
    console: Console,
) -> None:
    """Print skipped operations.

    Args:
        skipped_operations: List of skipped FileOperation objects
        console: Rich console for output
    """
    if not skipped_operations:
        return

    console.print(
        f"\n[yellow]Skipped {len(skipped_operations)} operations "
        f"(source files not found):[/yellow]"
    )
    for operation in skipped_operations:
        console.print(
            f"  [dim]• {operation.source_path} → {operation.destination_path}[/dim]"
        )
    console.print()


def confirm_rollback(console: Console) -> bool:
    """Ask for rollback confirmation.

    Args:
        console: Rich console for output

    Returns:
        True if confirmed, False otherwise
    """
    try:
        from prompt_toolkit.shortcuts import confirm

        if not confirm("Do you want to proceed with the rollback?"):
            console.print("[yellow]Rollback cancelled.[/yellow]")
            return False
        return True
    except KeyboardInterrupt:
        console.print("\n[yellow]Rollback cancelled.[/yellow]")
        return False
