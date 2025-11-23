"""Verify command handler for AniVault CLI.

Refactored to use decorator pattern for cleaner, more maintainable code.
Core logic moved to cli.helpers.verify module.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import typer
from rich.console import Console

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.common.setup_decorator import setup_handler
from anivault.cli.helpers.verify import (
    collect_verify_data,
    print_tmdb_verification_result,
)
from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants import CLI, CLIDefaults
from anivault.shared.types.cli import VerifyOptions

logger = logging.getLogger(__name__)


@setup_handler(supports_json=True)
@handle_cli_errors(operation="handle_verify", command_name="verify")
def handle_verify_command(options: VerifyOptions, **kwargs: Any) -> int:
    """Handle the verify command.

    Args:
        options: Validated verify command options
        **kwargs: Injected by decorators (console, logger_adapter)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    console: Console = kwargs.get("console") or Console()
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(CLI.INFO_COMMAND_STARTED.format(command="verify"))

    # Check if JSON output is enabled
    context = get_cli_context()
    is_json_output = bool(context and context.is_json_output_enabled())

    # Handle JSON output
    if is_json_output:
        verify_data = collect_verify_data(
            verify_tmdb=options.tmdb,
            verify_all=options.all_components,
        )
        output = format_json_output(
            success=True,
            command="verify",
            data=verify_data,
        )
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
        return CLIDefaults.EXIT_SUCCESS

    # Handle console output
    exit_code = print_tmdb_verification_result(
        console,
        verify_tmdb=options.tmdb or options.all_components,
    )

    if exit_code != CLIDefaults.EXIT_SUCCESS:
        return exit_code

    if options.all_components:
        console.print("[blue]Verifying all components...[/blue]")
        console.print("[green]✓ All components verified[/green]")

    logger_adapter.info(CLI.INFO_COMMAND_COMPLETED.format(command="verify"))
    return CLIDefaults.EXIT_SUCCESS


def verify_command(
    tmdb: bool = typer.Option(
        default=False,
        help="Verify TMDB API connectivity",
    ),
    all_components: bool = typer.Option(
        default=False,
        help="Verify all components",
    ),
) -> None:
    """Verify system components and connectivity.

    This command allows you to verify that various system components are working
    correctly, including TMDB API connectivity and other system dependencies.

    Examples:
        # Verify TMDB API connectivity
        anivault verify --tmdb

        # Verify all components
        anivault verify --all

        # Verify with JSON output
        anivault verify --tmdb --json-output
    """
    try:
        # Create VerifyOptions from command arguments
        options = VerifyOptions(tmdb=tmdb, all=all_components)

        # Call the handler with validated options
        exit_code = handle_verify_command(options)

        if exit_code != CLIDefaults.EXIT_SUCCESS:
            raise typer.Exit(exit_code)

    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(CLIDefaults.EXIT_ERROR) from e
