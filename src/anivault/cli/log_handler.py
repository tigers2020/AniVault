"""Log command handler for AniVault CLI.

Refactored to use decorator pattern for cleaner, more maintainable code.
Core logic moved to cli.helpers.log module.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.common.path_utils import extract_directory_path
from anivault.cli.common.setup_decorator import setup_handler
from anivault.cli.helpers.log import collect_log_list_data, print_log_list
from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants import CLI, CLIDefaults, FileSystem, LogCommands
from anivault.shared.constants.cli import CLIMessages
from anivault.shared.types.cli import CLIDirectoryPath, LogOptions

if TYPE_CHECKING:
    from rich.console import Console

logger = logging.getLogger(__name__)


@setup_handler(supports_json=True)
@handle_cli_errors(operation="handle_log", command_name="log")
def handle_log_command(options: LogOptions, **kwargs: Any) -> int:
    """Handle the log command.

    Args:
        options: Validated log command options
        **kwargs: Injected by decorators (console, logger_adapter)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    from rich.console import Console as RichConsole

    console: Console = kwargs.get("console") or RichConsole()
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(
        CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.LOG)
    )

    # Extract log directory path
    log_dir = extract_directory_path(options.log_dir)

    # Check if JSON output is enabled
    context = get_cli_context()
    is_json_output = bool(context and context.is_json_output_enabled())

    # Handle list command
    if options.log_command == LogCommands.LIST:
        if is_json_output:
            log_data = collect_log_list_data(log_dir)
            output = format_json_output(
                success=True,
                command=CLIMessages.CommandNames.LOG,
                data=log_data,
            )
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
            return CLIDefaults.EXIT_SUCCESS

        exit_code = print_log_list(log_dir, console)
        if exit_code == CLIDefaults.EXIT_SUCCESS:
            logger_adapter.info(
                CLI.INFO_COMMAND_COMPLETED.format(command=CLIMessages.CommandNames.LOG)
            )
        return exit_code

    # Unknown command
    if is_json_output:
        error_output = format_json_output(
            success=False,
            command=CLIMessages.CommandNames.LOG,
            errors=[CLIMessages.Error.NO_LOG_COMMAND],
        )
        sys.stdout.buffer.write(error_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    else:
        console.print("[red]Error: No log command specified[/red]")

    return CLIDefaults.EXIT_ERROR


def log_command(
    command: str = typer.Argument(
        ...,
        help="Log command to execute (list, show, tail)",
    ),
    log_dir: Path = typer.Option(
        Path(FileSystem.LOG_DIRECTORY),
        "--log-dir",
        help="Directory containing log files",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
) -> None:
    """Manage and view log files.

    This command provides utilities for viewing and managing AniVault log files.
    It can list available log files, show log contents, and tail log files in real-time.

    Examples:
        # List all log files
        anivault log list

        # List log files in custom directory
        anivault log list --log-dir /custom/logs

        # Show log file contents
        anivault log show app.log

        # Tail log file in real-time
        anivault log tail app.log --follow
    """
    try:
        # Create and validate options using Pydantic
        options = LogOptions(
            log_command=command,
            log_dir=CLIDirectoryPath(path=log_dir),
        )

        # Call the handler with validated options
        exit_code = handle_log_command(options)

        if exit_code != CLIDefaults.EXIT_SUCCESS:
            raise typer.Exit(exit_code)

    except Exception as e:
        # Handle validation errors
        from rich.console import Console

        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(CLIDefaults.EXIT_ERROR) from e
