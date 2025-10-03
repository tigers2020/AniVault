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
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
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

    except ApplicationError as e:
        logger.error(
            "Application error in rollback command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except InfrastructureError as e:
        logger.error(
            "Infrastructure error in rollback command",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except Exception:
        logger.exception("Unexpected error in rollback command")
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

    except ApplicationError as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Application error during rollback: {e.message}[/red]")
        logger.error(
            "Application error during rollback",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except InfrastructureError as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Infrastructure error during rollback: {e.message}[/red]")
        logger.error(
            "Infrastructure error during rollback",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except Exception as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Unexpected error during rollback: {e}[/red]")
        logger.exception("Unexpected error during rollback")
        return 1


def _setup_rollback_console():
    """Setup console for rollback command."""
    from rich.console import Console

    return Console()


def _get_rollback_log_path(args, console):
    """Get rollback log path."""
    try:
        from pathlib import Path

        from anivault.core.log_manager import OperationLogManager

        log_manager = OperationLogManager(Path.cwd())
        return log_manager.get_log_by_id(args.log_id)
    except ApplicationError as e:
        console.print(f"[red]Application error: {e.message}[/red]")
        logger.error(
            "Failed to get rollback log path",
            extra={"context": e.context, "error_code": e.code},
        )
        return None
    except InfrastructureError as e:
        console.print(f"[red]Infrastructure error: {e.message}[/red]")
        logger.error(
            "Failed to get rollback log path",
            extra={"context": e.context, "error_code": e.code},
        )
        return None
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        logger.exception("Unexpected error getting rollback log path")
        return None


def _generate_rollback_plan(log_path, console):
    """Generate rollback plan."""
    try:
        from pathlib import Path

        from anivault.core.log_manager import OperationLogManager
        from anivault.core.rollback_manager import RollbackManager

        log_manager = OperationLogManager(Path.cwd())
        rollback_manager = RollbackManager(log_manager)
        return rollback_manager.generate_rollback_plan(log_path)
    except ApplicationError as e:
        console.print(
            f"[red]Application error generating rollback plan: {e.message}[/red]",
        )
        logger.error(
            "Failed to generate rollback plan",
            extra={"context": e.context, "error_code": e.code},
        )
        return None
    except InfrastructureError as e:
        console.print(
            f"[red]Infrastructure error generating rollback plan: {e.message}[/red]",
        )
        logger.error(
            "Failed to generate rollback plan",
            extra={"context": e.context, "error_code": e.code},
        )
        return None
    except Exception as e:
        console.print(f"[red]Unexpected error generating rollback plan: {e}[/red]")
        logger.exception("Unexpected error generating rollback plan")
        return None


def _execute_rollback_plan(rollback_plan, args, console):
    """Execute rollback plan with file existence validation."""
    if args.dry_run:
        _print_rollback_dry_run_plan(rollback_plan, console)
        return 0

    # Validate plan and partition operations
    executable_plan, skipped_operations = _validate_rollback_plan(
        rollback_plan, console
    )

    if not executable_plan:
        console.print("[yellow]No executable rollback operations found[/yellow]")
        if skipped_operations:
            _print_skipped_operations(skipped_operations, console)
        return 0

    _print_rollback_execution_plan(executable_plan, console)

    if not args.yes:
        if not _confirm_rollback(console):
            return 0

    return _perform_rollback(executable_plan, args, skipped_operations, console)


def _confirm_rollback(console):
    """Ask for rollback confirmation."""
    try:
        from prompt_toolkit.shortcuts import confirm

        if not confirm("Do you want to proceed with the rollback?"):
            console.print("[yellow]Rollback cancelled.[/yellow]")
            return False
        return True
    except KeyboardInterrupt:
        console.print("\n[yellow]Rollback cancelled.[/yellow]")
        return False


def _perform_rollback(rollback_plan, args, skipped_operations=None, console=None):
    """Perform the actual rollback.

    Args:
        rollback_plan: List of executable FileOperation objects
        args: Command line arguments
        skipped_operations: List of skipped FileOperation objects (optional)
        console: Rich console instance (optional)
    """
    try:
        from pathlib import Path

        from rich.console import Console

        from anivault.core.log_manager import OperationLogManager
        from anivault.core.organizer import FileOrganizer

        if console is None:
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

        # Print summary of skipped operations if any
        if skipped_operations:
            _print_skipped_operations(skipped_operations, console)

        return 0

    except ApplicationError as e:
        logger.error(
            "Rollback execution failed",
            extra={"context": e.context, "error_code": e.code},
        )
        raise ApplicationError(
            ErrorCode.CLI_ROLLBACK_EXECUTION_FAILED,
            "Failed to execute rollback plan",
            ErrorContext(
                operation="perform_rollback",
                additional_data={"plan_size": len(rollback_plan)},
            ),
            original_error=e,
        ) from e
    except InfrastructureError as e:
        logger.error(
            "Rollback execution failed",
            extra={"context": e.context, "error_code": e.code},
        )
        raise InfrastructureError(
            ErrorCode.CLI_ROLLBACK_EXECUTION_FAILED,
            "Failed to execute rollback plan",
            ErrorContext(
                operation="perform_rollback",
                additional_data={"plan_size": len(rollback_plan)},
            ),
            original_error=e,
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during rollback execution")
        raise ApplicationError(
            ErrorCode.CLI_ROLLBACK_EXECUTION_FAILED,
            "Failed to execute rollback plan",
            ErrorContext(
                operation="perform_rollback",
                additional_data={"plan_size": len(rollback_plan)},
            ),
            original_error=e,
        ) from e


def _validate_rollback_plan(rollback_plan, console):
    """Validate rollback plan and partition operations based on file existence.

    Args:
        rollback_plan: List of FileOperation objects
        console: Rich console instance

    Returns:
        Tuple of (executable_plan, skipped_operations)
    """
    import os

    from anivault.core.organizer import FileOperation

    executable_plan = []
    skipped_operations = []

    for operation in rollback_plan:
        if os.path.exists(operation.source_path):
            executable_plan.append(operation)
        else:
            skipped_operations.append(operation)

    return executable_plan, skipped_operations


def _print_skipped_operations(skipped_operations, console):
    """Print information about skipped operations to the console.

    Args:
        skipped_operations: List of FileOperation objects that were skipped
        console: Rich console instance
    """
    if not skipped_operations:
        return

    console.print(
        f"\n[yellow]Skipped {len(skipped_operations)} operations (source files not found):[/yellow]"
    )
    for operation in skipped_operations:
        console.print(
            f"  [dim]• {operation.source_path} → {operation.destination_path}[/dim]"
        )
    console.print()


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
