"""Organize command handler for AniVault CLI.

Orchestration entry point: Container → OrganizeUseCase → helper (format only).
OperationLogManager usage is permitted here as a post-execution I/O step.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from dependency_injector.wiring import Provide, inject
from rich.console import Console as RichConsole

from anivault.app.use_cases.organize_use_case import OrganizeUseCase
from anivault.cli.common.context import get_cli_context
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.common.setup_decorator import setup_handler
from anivault.cli.helpers.organize import (
    collect_organize_data,
    confirm_organization,
    print_dry_run_plan,
    print_execution_plan,
    print_organization_results,
)
from anivault.cli.json_formatter import format_json_output
from anivault.containers import Container
from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, ScannedFile
from anivault.core.organizer.executor import OperationResult
from anivault.shared.constants import CLI, QueueConfig, WorkerConfig
from anivault.shared.constants.cli import CLIMessages
from anivault.shared.types.cli import CLIDirectoryPath, OrganizeOptions

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private pipeline helpers
# ---------------------------------------------------------------------------


@inject
def _scan_files(
    directory: Path,
    options: OrganizeOptions,
    console: RichConsole,
    *,
    use_case: OrganizeUseCase = Provide[Container.organize_use_case],
) -> list[ScannedFile]:
    """Scan directory using OrganizeUseCase.

    Args:
        directory: Directory to scan
        options: Organize command options
        console: Rich console
        use_case: Injected OrganizeUseCase

    Returns:
        List of ScannedFile instances; empty list when nothing found
    """
    from anivault.cli.progress import create_progress_manager
    from anivault.shared.constants.cli import CLIFormatting

    progress_manager = create_progress_manager(disabled=options.json_output)
    with progress_manager.spinner(CLIMessages.Info.SCANNING_FILES):
        scanned_files = use_case.scan(
            root_path=str(directory),
            extensions=options.extensions.split(","),
            num_workers=WorkerConfig.DEFAULT,
            max_queue_size=QueueConfig.DEFAULT_SIZE,
        )

    if not scanned_files and not options.json_output:
        console.print(
            CLIFormatting.format_colored_message(
                CLIMessages.Info.NO_ANIME_FILES_FOUND,
                "warning",
            )
        )

    return scanned_files


@inject
def _build_plan(
    scanned_files: list[ScannedFile],
    options: OrganizeOptions,
    *,
    use_case: OrganizeUseCase = Provide[Container.organize_use_case],
) -> list[FileOperation]:
    """Generate organization plan via OrganizeUseCase.

    Args:
        scanned_files: Files to organize
        options: Organize command options
        use_case: Injected OrganizeUseCase

    Returns:
        Organization plan
    """
    if options.enhanced:
        destination = options.destination if options.destination else "Anime"
        return use_case.generate_enhanced_plan(scanned_files, destination=destination)
    return use_case.generate_plan(scanned_files)


@inject
def _execute_plan(
    plan: list[FileOperation],
    source_directory: Path,
    options: OrganizeOptions,
    *,
    use_case: OrganizeUseCase = Provide[Container.organize_use_case],
) -> list[OperationResult]:
    """Execute organization plan via OrganizeUseCase.

    Args:
        plan: Organization plan to execute
        source_directory: Source directory path
        options: Organize command options
        use_case: Injected OrganizeUseCase

    Returns:
        List of OperationResult instances
    """
    from anivault.cli.progress import create_progress_manager

    progress_manager = create_progress_manager(disabled=options.json_output)
    with progress_manager.spinner("Organizing files..."):
        return use_case.execute_plan(plan, source_directory)


# ---------------------------------------------------------------------------
# Command entry point
# ---------------------------------------------------------------------------


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

    logger_adapter.info(CLI.INFO_COMMAND_STARTED.format(command=CLIMessages.CommandNames.ORGANIZE))

    directory = options.directory.path if hasattr(options.directory, "path") else Path(str(options.directory))

    # 1. Scan
    scanned_files = _scan_files(directory, options, console)
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

    # 2. Build plan
    plan = _build_plan(scanned_files, options)

    # 3. Dry-run
    if options.dry_run:
        if options.json_output:
            organize_data = collect_organize_data(plan, options, is_dry_run=True)
            json_output = format_json_output(
                success=True,
                command=CLIMessages.CommandNames.ORGANIZE,
                data=organize_data,
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            print_dry_run_plan(plan, console)
        return 0

    # 4. Show plan + confirm
    if not options.json_output:
        print_execution_plan(plan, console)

    if not options.yes and not options.json_output:
        if not confirm_organization(console):
            return 0

    # 5. Execute
    moved_files = _execute_plan(plan, directory, options)

    # 6. Save operation log (permitted handler-side I/O, not delegated to helper)
    operation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path: str | None = None
    try:
        log_manager = OperationLogManager(Path.cwd())
        saved = log_manager.save_plan(plan)
        log_path = str(saved)
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        logger_adapter.warning("Could not save operation log: %s", e)

    # 7. Output results via helper (formatter only)
    print_organization_results(
        plan,
        options,
        console,
        moved_files=moved_files,
        operation_id=operation_id,
        log_path=log_path,
    )

    logger_adapter.info(CLI.INFO_COMMAND_COMPLETED.format(command=CLIMessages.CommandNames.ORGANIZE))
    return 0


def organize_command(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
