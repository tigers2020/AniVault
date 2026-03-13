"""Organize command helper functions.

Extracted from organize_handler.py for better code organization.
Contains core organization pipeline logic.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from anivault.app.use_cases.organize_use_case import OrganizeUseCase
from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.config import Settings
from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, ScannedFile
from anivault.shared.constants import QueueConfig, WorkerConfig
from anivault.shared.constants.cli import CLIFormatting, CLIMessages
from anivault.shared.types.cli import OrganizeOptions

from .organize_formatters import (
    collect_organize_data,
    print_dry_run_plan,
    print_execution_plan,
)

logger = logging.getLogger(__name__)

__all__ = [
    "collect_organize_data",
    "confirm_organization",
    "execute_organization_plan",
    "generate_enhanced_organization_plan",
    "generate_organization_plan",
    "get_scanned_files",
    "perform_organization",
    "print_dry_run_plan",
    "print_execution_plan",
]


def get_scanned_files(options: OrganizeOptions, directory: Path, console: Console) -> list[ScannedFile]:
    """Get scanned files for organization.

    Args:
        options: Organize options
        directory: Directory to scan
        console: Rich console

    Returns:
        List of scanned files
    """
    use_case = OrganizeUseCase()
    progress_manager = create_progress_manager(disabled=options.json_output)

    with progress_manager.spinner(CLIMessages.Info.SCANNING_FILES):
        scanned_files = use_case.scan(
            root_path=str(directory),
            extensions=options.extensions.split(","),
            num_workers=WorkerConfig.DEFAULT,
            max_queue_size=QueueConfig.DEFAULT_SIZE,
        )

    if not scanned_files:
        if not options.json_output:
            console.print(
                CLIFormatting.format_colored_message(
                    CLIMessages.Info.NO_ANIME_FILES_FOUND,
                    "warning",
                ),
            )
        return []

    return scanned_files


@handle_cli_errors(operation="generate_organization_plan", command_name="organize")
def generate_organization_plan(
    scanned_files: list[ScannedFile],
    *,
    settings: Settings | None = None,
) -> list[FileOperation]:
    """Generate organization plan.

    Args:
        scanned_files: List of scanned files

    Returns:
        Organization plan
    """
    use_case = OrganizeUseCase()
    return use_case.generate_plan(scanned_files, settings=settings)


@handle_cli_errors(operation="generate_enhanced_organization_plan", command_name="organize")
def generate_enhanced_organization_plan(
    scanned_files: list[ScannedFile],
    options: OrganizeOptions,
) -> list[FileOperation]:
    """Generate enhanced organization plan with grouping.

    Args:
        scanned_files: List of scanned files
        options: Organize options

    Returns:
        Enhanced organization plan
    """
    use_case = OrganizeUseCase()
    destination = options.destination if options.destination else "Anime"
    return use_case.generate_enhanced_plan(scanned_files, destination=destination)


def execute_organization_plan(
    plan: list[FileOperation],
    options: OrganizeOptions,
    console: Console,
    *,
    settings: Settings | None = None,
) -> int:
    """Execute organization plan.

    Args:
        plan: Organization plan
        options: Organize options
        console: Rich console

    Returns:
        Exit code
    """
    if options.dry_run:
        if options.json_output:
            organize_data = collect_organize_data(plan, options, is_dry_run=True)
            json_output = format_json_output(
                success=True,
                command="organize",
                data=organize_data,
            )
            sys.stdout.buffer.write(json_output)
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.flush()
        else:
            print_dry_run_plan(plan, console)
        return 0

    if not options.json_output:
        print_execution_plan(plan, console)

    if not options.yes and not options.json_output:
        if not confirm_organization(console):
            return 0

    return perform_organization(plan, options, settings=settings)


def confirm_organization(console: Console) -> bool:
    """Ask for confirmation.

    Args:
        console: Rich console

    Returns:
        True if confirmed
    """
    try:
        if not Confirm.ask("Do you want to proceed?"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return False
        return True
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/yellow]")
        return False


@handle_cli_errors(operation="perform_organization", command_name="organize")
def perform_organization(
    plan: list[FileOperation],
    options: OrganizeOptions,
    *,
    settings: Settings | None = None,
) -> int:
    """Perform the actual organization.

    Args:
        plan: Organization plan
        options: Organize options

    Returns:
        Exit code
    """
    console = Console()  # pylint: disable=redefined-outer-name,reimported
    log_manager = OperationLogManager(Path.cwd())
    operation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    source_directory = options.directory.path if hasattr(options.directory, "path") else Path(str(options.directory))

    use_case = OrganizeUseCase()
    progress_manager = create_progress_manager(disabled=options.json_output)

    with progress_manager.spinner("Organizing files..."):
        moved_files = use_case.execute_plan(
            plan,
            source_directory,
            settings=settings,
        )

    # Print individual file results if not JSON output
    if not options.json_output and moved_files:
        console.print("\n[bold blue]File Organization Results:[/bold blue]")
        for result in moved_files:
            if result.success:
                console.print(f"[green]✅[/green] {Path(result.source_path).name}")
            else:
                console.print(f"[red]❌[/red] {Path(result.source_path).name}: {result.message or 'Failed'}")
        console.print()

    if options.json_output:
        organize_data = collect_organize_data(
            plan,
            options,
            moved_files=moved_files,
            operation_id=operation_id,
        )
        json_output = format_json_output(
            success=True,
            command="organize",
            data=organize_data,
        )
        sys.stdout.buffer.write(json_output)
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    elif moved_files:
        console.print(f"[green]Successfully organized {len(moved_files)} files[/green]")
        try:
            saved_log_path = log_manager.save_plan(plan)
            console.print(f"[grey62]Operation logged to: {saved_log_path}[/grey62]")
        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            console.print(f"[bold yellow]Warning: Could not save operation log: {e}[/bold yellow]")
    else:
        console.print("[yellow]No files were moved[/yellow]")

    return 0
