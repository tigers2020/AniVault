"""Organize command helper functions.

Extracted from organize_handler.py for better code organization.
Contains core organization pipeline logic.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.config import Settings
from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, ScannedFile
from anivault.core.organizer.executor import OperationResult
from anivault.core.organizer.organize_service import (
    execute_organization_plan as core_execute_plan,
)
from anivault.core.organizer.organize_service import (
    generate_enhanced_organization_plan as core_generate_enhanced_plan,
)
from anivault.core.organizer.organize_service import (
    generate_organization_plan as core_generate_plan,
)
from anivault.core.parser.models import ParsingResult
from anivault.core.pipeline import run_pipeline
from anivault.shared.constants import QueueConfig, WorkerConfig
from anivault.shared.constants.cli import CLIFormatting, CLIMessages
from anivault.shared.types.cli import OrganizeOptions
from anivault.shared.utils.metadata_converter import MetadataConverter

logger = logging.getLogger(__name__)


def get_scanned_files(options: OrganizeOptions, directory: Path, console: Console) -> list[ScannedFile]:
    """Get scanned files for organization.

    Args:
        options: Organize options
        directory: Directory to scan
        console: Rich console

    Returns:
        List of scanned files
    """

    progress_manager = create_progress_manager(disabled=options.json_output)

    with progress_manager.spinner(CLIMessages.Info.SCANNING_FILES):
        file_results = run_pipeline(
            root_path=str(directory),
            extensions=options.extensions.split(","),
            num_workers=WorkerConfig.DEFAULT,
            max_queue_size=QueueConfig.DEFAULT_SIZE,
        )

    if not file_results:
        if not options.json_output:
            console.print(
                CLIFormatting.format_colored_message(
                    CLIMessages.Info.NO_ANIME_FILES_FOUND,
                    "warning",
                ),
            )
        return []

    scanned_files: list[ScannedFile] = []
    for metadata in file_results:
        parsing_result = MetadataConverter.file_metadata_to_parsing_result(metadata)
        scanned_file = ScannedFile(
            file_path=metadata.file_path,
            metadata=parsing_result,
        )
        scanned_files.append(scanned_file)

    if not scanned_files and not options.json_output:
        console.print(
            CLIFormatting.format_colored_message(
                "No valid anime files found to organize",
                "warning",
            ),
        )

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
    return core_generate_plan(scanned_files, settings=settings)


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
    destination = options.destination if options.destination else "Anime"
    return core_generate_enhanced_plan(scanned_files, destination=destination)


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

    progress_manager = create_progress_manager(disabled=options.json_output)

    with progress_manager.spinner("Organizing files..."):
        moved_files = core_execute_plan(
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


def _get_file_size_safe(file_path: str) -> int:
    """Get file size safely, returning 0 on error.

    Args:
        file_path: Path to file

    Returns:
        File size in bytes, or 0 if error
    """
    try:
        return Path(file_path).stat().st_size
    except (OSError, TypeError):
        return 0


def _extract_parsing_result_data(parsing_result: ParsingResult) -> dict[str, object]:
    """Extract parsing result data for JSON output.

    Args:
        parsing_result: Parsing result object

    Returns:
        Dictionary with parsing result data
    """
    return {
        "title": parsing_result.title,
        "episode": parsing_result.episode,
        "season": parsing_result.season,
        "quality": parsing_result.quality,
        "source": parsing_result.source,
        "codec": parsing_result.codec,
        "audio": parsing_result.audio,
        "release_group": parsing_result.release_group,
        "confidence": parsing_result.confidence,
        "parser_used": parsing_result.parser_used,
        "additional_info": (asdict(parsing_result.additional_info) if hasattr(parsing_result, "additional_info") else {}),
    }


def _format_file_size_human_readable(size_bytes: float) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 GB")
    """
    bytes_per_unit = 1024.0

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < bytes_per_unit:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= bytes_per_unit
    return f"{size_bytes:.1f} PB"


def collect_organize_data(
    plan: list[FileOperation],
    _options: OrganizeOptions,  # Unused, kept for API compatibility  # pylint: disable=unused-argument
    moved_files: list[OperationResult] | None = None,
    operation_id: str | None = None,
    *,
    is_dry_run: bool = False,
) -> dict[str, object]:
    """Collect organize data for JSON output.

    Args:
        plan: Organization plan
        _options: Organize options (unused, kept for API compatibility)
        is_dry_run: Whether dry run
        moved_files: List of moved files
        operation_id: Operation ID

    Returns:
        Organize statistics
    """
    total_operations = len(plan)
    successful_moves = len(moved_files) if moved_files else 0

    operations_data = []
    total_size = 0

    for operation in plan:
        source_path = str(operation.source_path)
        destination_path = str(operation.destination_path)

        file_size = _get_file_size_safe(source_path)
        total_size += file_size

        operation_info = {
            "source_path": source_path,
            "destination_path": destination_path,
            "file_name": Path(source_path).name,
            "file_size": file_size,
            "file_extension": Path(source_path).suffix.lower(),
        }

        operations_data.append(operation_info)

    return {
        "organize_summary": {
            "total_operations": total_operations,
            "successful_moves": successful_moves,
            "is_dry_run": is_dry_run,
            "operation_id": operation_id,
            "total_size_bytes": total_size,
            "total_size_formatted": _format_file_size_human_readable(total_size),
            "success_rate": ((successful_moves / total_operations * 100) if total_operations > 0 else 0),
        },
        "operations": operations_data,
    }


def print_dry_run_plan(plan: list[FileOperation], console: Console) -> None:
    """Print dry run plan.

    Args:
        plan: Organization plan
        console: Rich console
    """
    console.print("[bold blue]Dry Run - Organization Plan:[/bold blue]")
    console.print()

    for operation in plan:
        source, destination = _extract_operation_paths(operation)
        console.print(f"[yellow]Would move:[/yellow] {source}")
        console.print(f"[green]To:[/green] {destination}")
        console.print()

    console.print(f"[bold]Total operations: {len(plan)}[/bold]")


def print_execution_plan(plan: list[FileOperation], console: Console) -> None:
    """Print execution plan.

    Args:
        plan: Organization plan
        console: Rich console
    """
    console.print("[bold blue]Organization Plan:[/bold blue]")
    console.print()

    for operation in plan:
        source, destination = _extract_operation_paths(operation)
        console.print(f"[yellow]Will move:[/yellow] {source}")
        console.print(f"[green]To:[/green] {destination}")
        console.print()


def _extract_operation_paths(operation: FileOperation) -> tuple[Path, Path]:
    """Extract source/destination paths from various operation types."""
    return operation.source_path, operation.destination_path
