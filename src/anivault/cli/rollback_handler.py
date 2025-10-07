"""Rollback command handler for AniVault CLI.

This module contains the business logic for the rollback command,
separated for better maintainability and single responsibility principle.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.models import RollbackOptions
from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants import CLI
from anivault.shared.constants.cli import CLIMessages
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)

logger = logging.getLogger(__name__)


def handle_rollback_command(options: RollbackOptions) -> int:
    """Handle the rollback command.

    Args:
        options: Validated rollback options

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(
        CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.ROLLBACK),
    )

    try:
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            return _handle_rollback_command_json(options)
        return _handle_rollback_command_console(options)

    except ApplicationError as e:
        logger.exception(
            "%sin rollback command",
            CLIMessages.Error.APPLICATION_ERROR,
            extra={
                CLIMessages.StatusKeys.CONTEXT: e.context,
                CLIMessages.StatusKeys.ERROR_CODE: e.code,
            },
        )
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.ROLLBACK,
                errors=[f"{CLIMessages.Error.APPLICATION_ERROR}{e.message}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        return 1
    except InfrastructureError as e:
        logger.exception(
            "%sin rollback command",
            CLIMessages.Error.INFRASTRUCTURE_ERROR,
            extra={
                CLIMessages.StatusKeys.CONTEXT: e.context,
                CLIMessages.StatusKeys.ERROR_CODE: e.code,
            },
        )
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.ROLLBACK,
                errors=[f"{CLIMessages.Error.INFRASTRUCTURE_ERROR}{e.message}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        return 1
    except (FileNotFoundError, PermissionError, OSError) as e:
        # Handle file system errors
        logger.exception("File system error in rollback command")
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.ROLLBACK,
                errors=[f"File system error: {e}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        # Handle data processing errors
        logger.exception("Data processing error in rollback command")
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.ROLLBACK,
                errors=[f"Data processing error: {e}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
    except Exception as e:
        # Handle unexpected errors
        logger.exception("Unexpected error in rollback command")
        context = get_cli_context()
        if context and context.is_json_output_enabled():
            error_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.ROLLBACK,
                errors=[f"Unexpected error: {e}"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
        return 1


def _handle_rollback_command_json(options: RollbackOptions) -> int:
    """Handle rollback command with JSON output.

    Args:
        options: Validated rollback options

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        rollback_data = _collect_rollback_data(options)
        if rollback_data is None:
            error_output = format_json_output(
                success=False,
                command=CLIMessages.CommandNames.ROLLBACK,
                errors=["Failed to collect rollback data"],
            )
            sys.stdout.buffer.write(error_output)
            sys.stdout.buffer.write(b"\n")
            return 1

        output = format_json_output(
            success=True,
            command=CLIMessages.CommandNames.ROLLBACK,
            data=rollback_data,
        )
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.write(b"\n")
        return 0

    except Exception as e:
        error_output = format_json_output(
            success=False,
            command=CLIMessages.CommandNames.ROLLBACK,
            errors=[f"Error during rollback operation: {e}"],
        )
        sys.stdout.buffer.write(error_output)
        sys.stdout.buffer.write(b"\n")
        logger.exception("Error in rollback command JSON output")
        return 1


def _handle_rollback_command_console(options: RollbackOptions) -> int:
    """Handle rollback command with console output.

    Args:
        options: Validated rollback options

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        result = _run_rollback_command(options)

        if result == 0:
            logger.info(CLI.INFO_COMMAND_COMPLETED.format(command="rollback"))
        else:
            logger.error("Rollback command failed with exit code %s", result)

        return result

    except ApplicationError as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Application error during rollback: {e.message}[/red]")
        logger.exception(
            "Application error during rollback",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except InfrastructureError as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Infrastructure error during rollback: {e.message}[/red]")
        logger.exception(
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


def _collect_rollback_data(options: RollbackOptions) -> dict[str, Any] | None:
    """Collect rollback data for JSON output.

    Args:
        options: Validated rollback options

    Returns:
        Dictionary containing rollback data, or None if error
    """
    try:
        from pathlib import Path

        from anivault.core.log_manager import OperationLogManager
        from anivault.core.rollback_manager import RollbackManager

        # Get rollback log path
        log_manager = OperationLogManager(Path.cwd())
        log_path = log_manager.get_log_by_id(options.log_id)

        if log_path is None:
            return {
                "error": f"Log with ID {options.log_id} not found",
                "rollback_plan": [],
                "executable_plan": [],
                "skipped_operations": [],
            }

        # Generate rollback plan
        rollback_manager = RollbackManager(log_manager)
        rollback_plan = rollback_manager.generate_rollback_plan(str(log_path))

        if rollback_plan is None:
            return {
                "error": "Failed to generate rollback plan",
                "rollback_plan": [],
                "executable_plan": [],
                "skipped_operations": [],
            }

        if not rollback_plan:
            return {
                "message": "No rollback operations needed",
                "rollback_plan": [],
                "executable_plan": [],
                "skipped_operations": [],
            }

        # Validate plan and partition operations
        executable_plan, skipped_operations = _validate_rollback_plan_for_json(
            rollback_plan,
        )

        # Collect operation data
        rollback_plan_data = []
        for operation in rollback_plan:
            rollback_plan_data.append(
                {
                    "source_path": str(operation.source_path),
                    "destination_path": str(operation.destination_path),
                    "operation_type": "MOVE",
                },
            )

        executable_plan_data = []
        for operation in executable_plan:
            executable_plan_data.append(
                {
                    "source_path": str(operation.source_path),
                    "destination_path": str(operation.destination_path),
                    "operation_type": "MOVE",
                },
            )

        skipped_operations_data = []
        for operation in skipped_operations:
            skipped_operations_data.append(
                {
                    "source_path": str(operation.source_path),
                    "destination_path": str(operation.destination_path),
                    "operation_type": "MOVE",
                    "reason": "Source file not found",
                },
            )

        return {
            "log_id": options.log_id,
            "log_path": str(log_path),
            "rollback_plan": rollback_plan_data,
            "executable_plan": executable_plan_data,
            "skipped_operations": skipped_operations_data,
            "total_operations": len(rollback_plan),
            "executable_count": len(executable_plan),
            "skipped_count": len(skipped_operations),
            "dry_run": options.dry_run,
        }

    except (OSError, ValueError, KeyError, AttributeError):
        # Handle specific I/O and data processing errors
        logger.exception("Error collecting rollback data")
        return None
    except Exception:
        # Handle unexpected errors
        logger.exception("Unexpected error collecting rollback data")
        return None


def _validate_rollback_plan_for_json(
    rollback_plan: list[Any],
) -> tuple[list[Any], list[Any]]:
    """Validate rollback plan for JSON output.

    Args:
        rollback_plan: List of FileOperation objects

    Returns:
        Tuple of (executable_plan, skipped_operations)
    """

    executable_plan = []
    skipped_operations = []

    for operation in rollback_plan:
        if Path(operation.source_path).exists():
            executable_plan.append(operation)
        else:
            skipped_operations.append(operation)

    return executable_plan, skipped_operations


def _run_rollback_command(options: RollbackOptions) -> int:  # noqa: PLR0911
    """Run the rollback command.

    Args:
        options: Validated rollback options

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        console = _setup_rollback_console()
        
        # Get log path (raises exception on error)
        log_path = _get_rollback_log_path(options, console)
        
        # Generate rollback plan (raises exception on error)
        rollback_plan = _generate_rollback_plan(log_path, console)

        if not rollback_plan:
            console.print("[yellow]No rollback operations needed[/yellow]")
            return 0

        return _execute_rollback_plan(rollback_plan, options, console)

    except ApplicationError as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Application error during rollback: {e.message}[/red]")
        logger.exception(
            "Application error during rollback",
            extra={"context": e.context, "error_code": e.code},
        )
        return 1
    except InfrastructureError as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Infrastructure error during rollback: {e.message}[/red]")
        logger.exception(
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


def _setup_rollback_console() -> Any:
    """Setup console for rollback command."""
    from rich.console import Console

    return Console()


def _get_rollback_log_path(options: RollbackOptions, console: Any) -> Path:
    """Get rollback log path.
    
    Args:
        options: Rollback options
        console: Console (unused, kept for backward compatibility)
    
    Returns:
        Path to rollback log file
    
    Raises:
        ApplicationError: If log path cannot be determined or log not found
        InfrastructureError: If log file access fails
    """
    from pathlib import Path
    from anivault.core.log_manager import OperationLogManager

    try:
        log_manager = OperationLogManager(Path.cwd())
        log_path = log_manager.get_log_by_id(options.log_id)
        
        if log_path is None:
            raise ApplicationError(
                code=ErrorCode.FILE_NOT_FOUND,
                message=f"Rollback log with ID '{options.log_id}' not found",
                context={"log_id": options.log_id, "operation": "get_rollback_log_path"},
            )
        
        return log_path
        
    except (ApplicationError, InfrastructureError):
        # Re-raise AniVault errors as-is
        raise
    except OSError as e:
        raise InfrastructureError(
            code=ErrorCode.FILE_ACCESS_ERROR,
            message=f"Failed to access rollback log: {e}",
            context={"log_id": options.log_id, "operation": "get_rollback_log_path"},
            original_error=e,
        ) from e
    except Exception as e:
        raise ApplicationError(
            code=ErrorCode.APPLICATION_ERROR,
            message=f"Unexpected error getting rollback log path: {e}",
            context={"log_id": options.log_id, "operation": "get_rollback_log_path"},
            original_error=e,
        ) from e


def _generate_rollback_plan(log_path: Path, console: Any) -> list:
    """Generate rollback plan.
    
    Args:
        log_path: Path to rollback log file
        console: Console (unused, kept for backward compatibility)
    
    Returns:
        List of rollback operations
    
    Raises:
        ApplicationError: If rollback plan generation fails
        InfrastructureError: If log file cannot be read
    """
    from pathlib import Path
    from anivault.core.log_manager import OperationLogManager
    from anivault.core.rollback_manager import RollbackManager

    try:
        log_manager = OperationLogManager(Path.cwd())
        rollback_manager = RollbackManager(log_manager)
        rollback_plan = rollback_manager.generate_rollback_plan(log_path)
        
        if rollback_plan is None:
            raise ApplicationError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Failed to generate rollback plan from log: {log_path}",
                context={"log_path": str(log_path), "operation": "generate_rollback_plan"},
            )
        
        return rollback_plan
        
    except (ApplicationError, InfrastructureError):
        # Re-raise AniVault errors as-is
        raise
    except OSError as e:
        raise InfrastructureError(
            code=ErrorCode.FILE_READ_ERROR,
            message=f"Failed to read rollback log file: {e}",
            context={"log_path": str(log_path), "operation": "generate_rollback_plan"},
            original_error=e,
        ) from e
    except Exception as e:
        raise ApplicationError(
            code=ErrorCode.APPLICATION_ERROR,
            message=f"Unexpected error generating rollback plan: {e}",
            context={"log_path": str(log_path), "operation": "generate_rollback_plan"},
            original_error=e,
        ) from e


def _execute_rollback_plan(
    rollback_plan: Any,
    options: RollbackOptions,
    console: Any,
) -> int:
    """Execute rollback plan with file existence validation."""
    if options.dry_run:
        _print_rollback_dry_run_plan(rollback_plan, console)
        return 0

    # Validate plan and partition operations
    executable_plan, skipped_operations = _validate_rollback_plan(
        rollback_plan,
        console,
    )

    if not executable_plan:
        console.print("[yellow]No executable rollback operations found[/yellow]")
        if skipped_operations:
            _print_skipped_operations(skipped_operations, console)
        return 0

    _print_rollback_execution_plan(executable_plan, console)

    if not options.yes:
        if not _confirm_rollback(console):
            return 0

    return _perform_rollback(executable_plan, options, skipped_operations, console)


def _confirm_rollback(console: Any) -> bool:
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


def _perform_rollback(
    rollback_plan: Any,
    options: RollbackOptions,
    skipped_operations: Any = None,
    console: Any = None,
) -> int:
    """Perform the actual rollback.

    Args:
        rollback_plan: List of executable FileOperation objects
        options: Validated rollback options
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
        moved_files = organizer.execute_plan(
            rollback_plan,
            f"rollback-{options.log_id}",
        )

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
        logger.exception(
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
        logger.exception(
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


def _validate_rollback_plan(
    rollback_plan: Any,
    console: Any,
) -> tuple[list[Any], list[Any]]:
    """Validate rollback plan and partition operations based on file existence.

    Args:
        rollback_plan: List of FileOperation objects
        console: Rich console instance

    Returns:
        Tuple of (executable_plan, skipped_operations)
    """

    executable_plan = []
    skipped_operations = []

    for operation in rollback_plan:
        if Path(operation.source_path).exists():
            executable_plan.append(operation)
        else:
            skipped_operations.append(operation)

    return executable_plan, skipped_operations


def _print_skipped_operations(skipped_operations: Any, console: Any) -> None:
    """Print information about skipped operations to the console.

    Args:
        skipped_operations: List of FileOperation objects that were skipped
        console: Rich console instance
    """
    if not skipped_operations:
        return

    console.print(
        f"\n[yellow]Skipped {len(skipped_operations)} operations (source files not found):[/yellow]",
    )
    for operation in skipped_operations:
        console.print(
            f"  [dim]• {operation.source_path} → {operation.destination_path}[/dim]",
        )
    console.print()


def _print_rollback_dry_run_plan(plan: Any, console: Any) -> None:
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


def _print_rollback_execution_plan(plan: Any, console: Any) -> None:
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


def rollback_command(
    log_id: str = typer.Argument(
        ...,
        help="ID of the operation log to rollback",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be rolled back without actually moving files",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts and proceed with rollback",
    ),
) -> None:
    """
    Rollback file organization operations from a previous session.

    This command allows you to undo file organization operations by rolling back
    files to their original locations based on operation logs. It can show what
    would be rolled back without making changes using --dry-run.

    Examples:
        # Rollback operations from log ID "2024-01-15_143022"
        anivault rollback 2024-01-15_143022

        # Preview what would be rolled back without making changes
        anivault rollback 2024-01-15_143022 --dry-run

        # Rollback without confirmation prompts
        anivault rollback 2024-01-15_143022 --yes
    """
    try:
        # Create and validate options using Pydantic model
        options = RollbackOptions(
            log_id=log_id,
            dry_run=dry_run,
            yes=yes,
        )

        # Call the handler with validated options
        exit_code = handle_rollback_command(options)

        if exit_code != 0:
            raise typer.Exit(exit_code)

    except (ValueError, ValidationError) as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Validation error: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Unexpected error: {e}[/red]")
        logger.exception("%sin rollback command", CLIMessages.Error.UNEXPECTED_ERROR)
        raise typer.Exit(1) from e
