"""Rollback command handler for AniVault CLI.

Refactored to use decorator pattern for cleaner, more maintainable code.
Core logic moved to cli.helpers.rollback module.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import typer
from pydantic import ValidationError
from rich.console import Console

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.common.setup_decorator import setup_handler
from anivault.cli.helpers.rollback import (
    confirm_rollback,
    execute_rollback_plan,
    generate_rollback_plan,
    load_rollback_log,
    print_rollback_dry_run_plan,
    print_rollback_execution_plan,
    print_skipped_operations,
    validate_rollback_plan,
)
from anivault.cli.json_formatter import format_json_output
from anivault.core.models import FileOperation, OperationType
from anivault.shared.constants import CLI, CLIDefaults
from anivault.shared.constants.cli import CLIMessages
from anivault.shared.types.cli import RollbackOptions

logger = logging.getLogger(__name__)


@setup_handler(supports_json=True, allow_dry_run=True)
@handle_cli_errors(operation="handle_rollback", command_name="rollback")
def handle_rollback_command(options: RollbackOptions, **kwargs: Any) -> int:
    """Handle the rollback command.

    Args:
        options: Validated rollback options
        **kwargs: Injected by decorators (console, logger_adapter)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    from rich.console import Console as RichConsole

    console: Console = kwargs.get("console") or RichConsole()
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(
        CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.ROLLBACK)
    )

    # Check if JSON output is enabled
    context = get_cli_context()
    is_json_output = bool(context and context.is_json_output_enabled())

    # Load rollback log
    log_path = load_rollback_log(options.log_id)

    # Generate rollback plan
    rollback_plan = generate_rollback_plan(log_path)

    if not rollback_plan:
        if is_json_output:
            _output_json_no_operations(options)
        else:
            console.print("[yellow]No rollback operations needed[/yellow]")
        return CLIDefaults.EXIT_SUCCESS

    # Handle JSON output
    if is_json_output:
        return _handle_json_output(options, rollback_plan, log_path)

    # Handle dry-run mode
    if options.dry_run:
        print_rollback_dry_run_plan(rollback_plan, console)
        return CLIDefaults.EXIT_SUCCESS

    # Validate and partition operations
    executable_plan, skipped_operations = validate_rollback_plan(rollback_plan)

    if not executable_plan:
        console.print("[yellow]No executable rollback operations found[/yellow]")
        if skipped_operations:
            print_skipped_operations(skipped_operations, console)
        return CLIDefaults.EXIT_SUCCESS

    # Print execution plan
    print_rollback_execution_plan(executable_plan, console)

    # Confirm if not in yes mode
    if not options.yes:
        if not confirm_rollback(console):
            return CLIDefaults.EXIT_SUCCESS

    # Execute rollback
    execute_rollback_plan(executable_plan, options.log_id, console)

    # Print skipped operations summary
    if skipped_operations:
        print_skipped_operations(skipped_operations, console)

    logger_adapter.info(
        CLI.INFO_COMMAND_COMPLETED.format(command=CLIMessages.CommandNames.ROLLBACK)
    )
    return CLIDefaults.EXIT_SUCCESS


def _output_json_no_operations(options: RollbackOptions) -> None:
    """Output JSON for no operations case.

    Args:
        options: Rollback options
    """
    output = format_json_output(
        success=True,
        command=CLIMessages.CommandNames.ROLLBACK,
        data={
            "log_id": options.log_id,
            "message": "No rollback operations needed",
            "rollback_plan": [],
            "executable_plan": [],
            "skipped_operations": [],
            "total_operations": 0,
            "executable_count": 0,
            "skipped_count": 0,
            "dry_run": options.dry_run,
        },
    )
    sys.stdout.buffer.write(output)
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


def _handle_json_output(
    options: RollbackOptions,
    rollback_plan: list[FileOperation],
    log_path: Path,
) -> int:
    """Handle JSON output mode.

    Args:
        options: Rollback options
        rollback_plan: List of rollback operations
        log_path: Path to rollback log file

    Returns:
        Exit code
    """
    try:
        # Validate plan and partition operations
        executable_plan, skipped_operations = validate_rollback_plan(rollback_plan)

        # Convert operations to dict format
        rollback_plan_data = [
            {
                "source_path": str(op.source_path),
                "destination_path": str(op.destination_path),
                "operation_type": OperationType.MOVE.value,
            }
            for op in rollback_plan
        ]

        executable_plan_data = [
            {
                "source_path": str(op.source_path),
                "destination_path": str(op.destination_path),
                "operation_type": OperationType.MOVE.value,
            }
            for op in executable_plan
        ]

        skipped_operations_data = [
            {
                "source_path": str(op.source_path),
                "destination_path": str(op.destination_path),
                "operation_type": OperationType.MOVE.value,
                "reason": "Source file not found",
            }
            for op in skipped_operations
        ]

        output_data = {
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

        output = format_json_output(
            success=True,
            command=CLIMessages.CommandNames.ROLLBACK,
            data=output_data,
        )
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()

        return CLIDefaults.EXIT_SUCCESS

    except Exception as e:
        error_output = format_json_output(
            success=False,
            command=CLIMessages.CommandNames.ROLLBACK,
            errors=[f"Error during rollback operation: {e}"],
        )
        sys.stdout.buffer.write(error_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
        logger.exception("Error in rollback JSON output")
        return 1


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
    """Rollback file organization operations from a previous session.

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

        if exit_code != CLIDefaults.EXIT_SUCCESS:
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
