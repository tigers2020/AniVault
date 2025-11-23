"""Organize command handler for AniVault CLI.

Refactored to use decorator pattern for cleaner, more maintainable code.
Core logic moved to cli.helpers.organize module.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console as RichConsole

from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.common.setup_decorator import setup_handler
from anivault.cli.helpers.organize import (
    collect_organize_data,
    execute_organization_plan,
    generate_enhanced_organization_plan,
    generate_organization_plan,
    get_scanned_files,
)
from anivault.cli.json_formatter import format_json_output
from anivault.shared.constants import CLI
from anivault.shared.constants.cli import CLIMessages
from anivault.shared.types.cli import CLIDirectoryPath, OrganizeOptions

logger = logging.getLogger(__name__)


@setup_handler(requires_directory=True, supports_json=True, allow_dry_run=True)
@handle_cli_errors(operation="handle_organize", command_name="organize")
def handle_organize_command(options: OrganizeOptions, **kwargs: Any) -> int:
    """Handle the organize command.

    Args:
        options: Validated organize command options
        **kwargs: Injected by decorators (console, logger_adapter)

    Returns:
        Exit code (0 for success, non-zero for error)
    """

    console = kwargs.get("console") or RichConsole()
    logger_adapter = kwargs.get("logger_adapter", logger)

    logger_adapter.info(
        CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.ORGANIZE)
    )

    # Extract Path from DirectoryPath or use directly
    directory = (
        options.directory.path
        if hasattr(options.directory, "path")
        else Path(str(options.directory))
    )

    scanned_files = get_scanned_files(options, directory, console)
    if not scanned_files:
        if options.json_output:
            organize_data = collect_organize_data([], options, is_dry_run=False)
            json_output = format_json_output(
                success=True,
                command=CLIMessages.CommandNames.ORGANIZE,
                data=organize_data,
                warnings=["No anime files found to organize"],
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        return 0

    if options.enhanced:
        plan = generate_enhanced_organization_plan(scanned_files, options)
    else:
        plan = generate_organization_plan(scanned_files)

    result = execute_organization_plan(plan, options, console)

    if result == 0:
        logger_adapter.info(
            CLI.INFO_COMMAND_COMPLETED.format(command=CLIMessages.CommandNames.ORGANIZE)
        )

    return result


def organize_command(
    directory: Path = typer.Argument(
        ...,
        help="Directory containing scanned and matched anime files to organize",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be organized without actually moving files",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompts and proceed with organization",
    ),
    enhanced: bool = typer.Option(
        False,
        "--enhanced",
        help="Use enhanced organization with grouping and Korean titles",
    ),
    destination: str = typer.Option(
        "Anime",
        "--destination",
        "-d",
        help="Base destination directory for organized files",
    ),
    extensions: str = typer.Option(
        ".mkv,.mp4,.avi",
        "--extensions",
        "-e",
        help="Comma-separated list of file extensions to organize",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results in JSON format",
    ),
) -> None:
    """Organize anime files into structured directories.

    This command moves matched anime files into a structured directory hierarchy
    based on their metadata, creating organized folders for each series with
    proper season/episode naming.

    Examples:
        anivault organize .
        anivault organize /path/to/anime --dry-run
        anivault organize /path/to/anime --yes --destination ~/Anime
    """
    try:
        context = get_cli_context()

        organize_options = OrganizeOptions(
            directory=CLIDirectoryPath(path=directory),
            dry_run=dry_run,
            yes=yes,
            enhanced=enhanced,
            destination=destination,
            extensions=extensions,
            json_output=json_output,
            verbose=bool(context.verbose) if context else False,
        )

        exit_code = handle_organize_command(organize_options)

        if exit_code != 0:
            raise typer.Exit(exit_code)

    except ValueError as e:
        logger.exception("Validation error")
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e
