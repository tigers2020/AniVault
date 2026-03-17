"""Organize command handler for AniVault CLI.

Orchestration entry point: Container → OrganizeUseCase → helper (format only).

Phase 4: presentation → core import 0. Internal helpers receive/return opaque
lists (use case internal format). Formatters receive only application DTOs
(OrganizePlanItem, OrganizeResultItem).
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

from anivault.application.dtos.organize import file_operation_to_dto, operation_result_to_dto
from anivault.application.use_cases.organize_use_case import OrganizeUseCase
from anivault.presentation.cli.common.context import get_cli_context
from anivault.presentation.cli.common.error_decorator import handle_cli_errors
from anivault.presentation.cli.common.setup_decorator import setup_handler
from anivault.presentation.cli.helpers.organize import (
    collect_organize_data,
    confirm_organization,
    print_dry_run_plan,
    print_execution_plan,
    print_organization_results,
)
from anivault.presentation.cli.json_formatter import format_json_output
from anivault.infrastructure.composition import Container
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
) -> list:
    """Scan directory using OrganizeUseCase.

    Returns opaque use-case internal format. Do NOT pass to formatters;
    convert to DTO via use case or handler before display.
    """
    from anivault.presentation.cli.progress import create_progress_manager
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
    scanned_files: list,
    options: OrganizeOptions,
    *,
    use_case: OrganizeUseCase = Provide[Container.organize_use_case],
) -> list:
    """Generate organization plan via OrganizeUseCase.

    Plan is internal; formatter receives plan_dtos (OrganizePlanItem list).
    """
    if options.enhanced:
        destination = options.destination if options.destination else "Anime"
        return use_case.generate_enhanced_plan(scanned_files, destination=destination)
    return use_case.generate_plan(scanned_files)


@inject
def _save_operation_log(
    plan: list,
    *,
    use_case: OrganizeUseCase = Provide[Container.organize_use_case],
) -> str | None:
    """Persist the operation plan log via OrganizeUseCase."""
    return use_case.save_plan_log(plan)


@inject
def _execute_plan(
    plan: list,
    source_directory: Path,
    options: OrganizeOptions,
    *,
    use_case: OrganizeUseCase = Provide[Container.organize_use_case],
) -> list:
    """Execute organization plan via OrganizeUseCase.

    Returns opaque use-case result list; convert to OrganizeResultItem for display.
    """
    from anivault.presentation.cli.progress import create_progress_manager

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
    plan_dtos = [file_operation_to_dto(op) for op in plan]

    # 3. Dry-run
    if options.dry_run:
        if options.json_output:
            organize_data = collect_organize_data(plan_dtos, options, is_dry_run=True)
            json_output = format_json_output(
                success=True,
                command=CLIMessages.CommandNames.ORGANIZE,
                data=organize_data,
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            print_dry_run_plan(plan_dtos, console)
        return 0

    # 4. Show plan + confirm
    if not options.json_output:
        print_execution_plan(plan_dtos, console)

    if not options.yes and not options.json_output:
        if not confirm_organization(console):
            return 0

    # 5. Execute
    moved_files = _execute_plan(plan, directory, options)
    moved_dtos = [operation_result_to_dto(r) for r in moved_files]

    # 6. Save operation log via OrganizeUseCase (R5: no direct core import in handler)
    operation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path: str | None = _save_operation_log(plan)

    # 7. Output results via helper (formatter only, DTOs only)
    print_organization_results(
        plan_dtos,
        options,
        console,
        moved_files=moved_dtos,
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
