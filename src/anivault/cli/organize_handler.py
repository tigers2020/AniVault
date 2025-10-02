"""Organize command handler for AniVault CLI.

This module contains the business logic for the organize command,
separated for better maintainability and single responsibility principle.
"""

import logging
from typing import Any

from anivault.shared.constants.system import (
    CLI_INFO_COMMAND_COMPLETED,
    CLI_INFO_COMMAND_STARTED,
)

logger = logging.getLogger(__name__)


def handle_organize_command(args: Any) -> int:
    """Handle the organize command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger.info(CLI_INFO_COMMAND_STARTED.format(command="organize"))

    try:
        console = _setup_organize_console()
        directory = _validate_organize_directory(args, console)
        if directory is None:
            return 1

        scanned_files = _get_scanned_files(args, directory, console)
        if not scanned_files:
            return 0

        plan = _generate_organization_plan(scanned_files)
        return _execute_organization_plan(plan, args, console)

    except Exception as e:
        from rich.console import Console

        console = Console()
        console.print(f"[red]Error during organization: {e}[/red]")
        logger.exception("Error in organize command")
        return 1


def _setup_organize_console():
    """Setup console for organize command."""
    from rich.console import Console

    return Console()


def _validate_organize_directory(args, console):
    """Validate directory for organize command."""
    try:
        from anivault.cli.utils import validate_directory

        directory = validate_directory(args.directory)
        console.print(f"[green]Organizing files in: {directory}[/green]")
        return directory
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return None


def _get_scanned_files(args, directory, console):
    """Get scanned files for organization."""
    from anivault.core.pipeline.main import run_pipeline
    from anivault.shared.constants.system import DEFAULT_QUEUE_SIZE, DEFAULT_WORKERS

    file_results = run_pipeline(
        root_path=str(directory),
        extensions=args.extensions,
        num_workers=DEFAULT_WORKERS,
        max_queue_size=DEFAULT_QUEUE_SIZE,
    )

    if not file_results:
        console.print(
            "[yellow]No anime files found in the specified directory[/yellow]",
        )
        return []

    # Convert file results to ScannedFile objects
    from pathlib import Path

    from anivault.core.models import ScannedFile

    scanned_files = []
    for result in file_results:
        if "parsing_result" in result:
            scanned_file = ScannedFile(
                file_path=Path(result["file_path"]),
                parsing_result=result["parsing_result"],
            )
            scanned_files.append(scanned_file)

    if not scanned_files:
        console.print("[yellow]No valid anime files found to organize[/yellow]")
        return []

    return scanned_files


def _generate_organization_plan(scanned_files):
    """Generate organization plan."""
    from pathlib import Path

    from anivault.core.log_manager import OperationLogManager
    from anivault.core.organizer import FileOrganizer

    log_manager = OperationLogManager(Path.cwd())
    organizer = FileOrganizer(log_manager=log_manager)
    return organizer.generate_plan(scanned_files)


def _execute_organization_plan(plan, args, console):
    """Execute organization plan."""
    if args.dry_run:
        _print_dry_run_plan_impl(plan, console)
        logger.info(CLI_INFO_COMMAND_COMPLETED.format(command="organize"))
        return 0

    _print_execution_plan_impl(plan, console)

    if not args.yes:
        if not _confirm_organization(console):
            return 0

    return _perform_organization(plan)


def _confirm_organization(console):
    """Ask for confirmation."""
    try:
        from rich.prompt import Confirm

        if not Confirm.ask("Do you want to proceed?"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return False
        return True
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/yellow]")
        return False


def _perform_organization(plan):
    """Perform the actual organization."""
    from datetime import datetime
    from pathlib import Path

    from rich.console import Console

    from anivault.core.log_manager import OperationLogManager
    from anivault.core.organizer import FileOrganizer

    console = Console()
    log_manager = OperationLogManager(Path.cwd())
    organizer = FileOrganizer(log_manager=log_manager)

    operation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    moved_files = organizer.execute_plan(plan, operation_id)

    if moved_files:
        console.print(f"[green]Successfully organized {len(moved_files)} files[/green]")
        try:
            saved_log_path = log_manager.save_plan(plan, operation_id)
            console.print(f"[grey62]Operation logged to: {saved_log_path}[/grey62]")
        except Exception as e:
            console.print(
                f"[bold yellow]Warning: Could not save operation log: {e}[/bold yellow]",
            )
    else:
        console.print("[yellow]No files were moved[/yellow]")

    logger.info(CLI_INFO_COMMAND_COMPLETED.format(command="organize"))
    return 0


def _print_dry_run_plan_impl(plan, console):
    """Print dry run plan."""
    console.print("[bold blue]Dry Run - Organization Plan:[/bold blue]")
    console.print()

    for operation in plan:
        source = operation.source_file.file_path
        destination = operation.destination_path
        console.print(f"[yellow]Would move:[/yellow] {source}")
        console.print(f"[green]To:[/green] {destination}")
        console.print()

    console.print(f"[bold]Total operations: {len(plan)}[/bold]")


def _print_execution_plan_impl(plan, console):
    """Print execution plan."""
    console.print("[bold blue]Organization Plan:[/bold blue]")
    console.print()

    for operation in plan:
        source = operation.source_file.file_path
        destination = operation.destination_path
        console.print(f"[yellow]Will move:[/yellow] {source}")
        console.print(f"[green]To:[/green] {destination}")
        console.print()

    console.print(f"[bold]Total operations: {len(plan)}[/bold]")
