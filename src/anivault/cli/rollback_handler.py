"""Rollback command handler for AniVault CLI.

This module contains the business logic for the rollback command,
separated for better maintainability and single responsibility principle.
"""

import logging
from typing import Any

from anivault.shared.constants.system import (
    CLI_INFO_COMMAND_COMPLETED,
    CLI_INFO_COMMAND_STARTED,
)

logger = logging.getLogger(__name__)


def handle_rollback_command(args: Any) -> int:
    """Handle the rollback command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI_INFO_COMMAND_STARTED.format(command="rollback"))

    try:
        result = _run_rollback_command(args)

        if result == 0:
            logger.info(CLI_INFO_COMMAND_COMPLETED.format(command="rollback"))
        else:
            logger.error("Rollback command failed with exit code %s", result)

        return result

    except Exception:
        logger.exception("Error in rollback command")
        return 1


def _run_rollback_command(args) -> int:
    """Run the rollback command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        console = _setup_rollback_console()
        log_path = _get_rollback_log_path(args, console)
        if log_path is None:
            return 1

        rollback_plan = _generate_rollback_plan(log_path, console)
        if rollback_plan is None:
            return 1

        if not rollback_plan:
            console.print("[yellow]No rollback operations needed[/yellow]")
            return 0

        return _execute_rollback_plan(rollback_plan, args, console)

    except Exception as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Error during rollback: {e}[/red]")
        logger.exception("Rollback error")
        return 1


def _setup_rollback_console():
    """Setup console for rollback command."""
    from rich.console import Console

    return Console()


def _get_rollback_log_path(args, console):
    """Get rollback log path."""
    from pathlib import Path

    from anivault.core.log_manager import OperationLogManager

    log_manager = OperationLogManager(Path.cwd())
    try:
        return log_manager.get_log_by_id(args.log_id)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return None


def _generate_rollback_plan(log_path, console):
    """Generate rollback plan."""
    from anivault.core.rollback_manager import RollbackManager

    rollback_manager = RollbackManager()
    try:
        return rollback_manager.generate_plan_from_log(log_path)
    except Exception as e:
        console.print(f"[red]Error generating rollback plan: {e}[/red]")
        return None


def _execute_rollback_plan(rollback_plan, args, console):
    """Execute rollback plan."""
    if args.dry_run:
        _print_rollback_dry_run_plan(rollback_plan, console)
        return 0

    _print_rollback_execution_plan(rollback_plan, console)

    if not args.yes:
        if not _confirm_rollback(console):
            return 0

    return _perform_rollback(rollback_plan, args)


def _confirm_rollback(console):
    """Ask for rollback confirmation."""
    try:
        from prompt_toolkit import confirm

        if not confirm("Do you want to proceed with the rollback?"):
            console.print("[yellow]Rollback cancelled.[/yellow]")
            return False
        return True
    except KeyboardInterrupt:
        console.print("\n[yellow]Rollback cancelled.[/yellow]")
        return False


def _perform_rollback(rollback_plan, args):
    """Perform the actual rollback."""
    from pathlib import Path

    from rich.console import Console

    from anivault.core.log_manager import OperationLogManager
    from anivault.core.organizer import FileOrganizer

    console = Console()
    log_manager = OperationLogManager(Path.cwd())
    organizer = FileOrganizer(log_manager=log_manager)

    console.print("[blue]Executing rollback...[/blue]")
    moved_files = organizer.execute_plan(rollback_plan, f"rollback-{args.log_id}")

    if moved_files:
        console.print(
            f"[green]Successfully rolled back {len(moved_files)} files[/green]",
        )
    else:
        console.print("[yellow]No files were moved during rollback[/yellow]")

    return 0


def _print_rollback_dry_run_plan(plan, console):
    """Print the rollback dry run plan in a formatted way.

    Args:
        plan: List of FileOperation objects
        console: Rich console instance
    """
    if not plan:
        console.print("[yellow][DRY RUN] No rollback operations are needed.[/yellow]")
        return

    console.print("[bold blue][DRY RUN] Planned rollback operations:[/bold blue]")
    console.print()

    for i, operation in enumerate(plan, 1):
        source = operation.source_path
        destination = operation.destination_path
        console.print(
            f"[cyan]{i:3d}.[/cyan] [green]MOVE:[/green] '{source}' -> '{destination}'",
        )

    console.print()
    console.print(f"[bold]Total operations: {len(plan)}[/bold]")


def _print_rollback_execution_plan(plan, console):
    """Print the rollback execution plan in a formatted way.

    Args:
        plan: List of FileOperation objects
        console: Rich console instance
    """
    if not plan:
        console.print("[yellow]No rollback operations are needed.[/yellow]")
        return

    console.print(
        "[bold blue]The following rollback operations will be performed:[/bold blue]",
    )
    console.print()

    for i, operation in enumerate(plan, 1):
        source = operation.source_path
        destination = operation.destination_path
        console.print(
            f"[cyan]{i:3d}.[/cyan] [green]MOVE:[/green] '{source}' -> '{destination}'",
        )

    console.print()
    console.print(f"[bold]Total operations: {len(plan)}[/bold]")
