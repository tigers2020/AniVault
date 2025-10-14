"""Organize command helper functions.

Extracted from organize_handler.py for better code organization.
Contains core organization pipeline logic.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

from anivault.cli.common.error_decorator import handle_cli_errors
from anivault.cli.json_formatter import format_json_output
from anivault.cli.progress import create_progress_manager
from anivault.core.file_grouper import FileGrouper
from anivault.core.log_manager import OperationLogManager
from anivault.core.organizer import FileOrganizer
from anivault.core.resolution_detector import ResolutionDetector
from anivault.core.subtitle_matcher import SubtitleMatcher
from anivault.services.tmdb_client import TMDBClient
from anivault.shared.constants import Language, QueueConfig, WorkerConfig
from anivault.shared.constants.cli import CLIFormatting, CLIMessages
from anivault.shared.types.cli import OrganizeOptions

logger = logging.getLogger(__name__)


def get_scanned_files(
    options: OrganizeOptions, directory: Path, console: Console
) -> list[Any]:
    """Get scanned files for organization.

    Args:
        options: Organize options
        directory: Directory to scan
        console: Rich console

    Returns:
        List of scanned files
    """
    from anivault.core.models import ScannedFile
    from anivault.core.pipeline.main import run_pipeline

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

    scanned_files = []
    for result in file_results:
        if CLIMessages.StatusKeys.PARSING_RESULT in result:
            scanned_file = ScannedFile(
                file_path=Path(result[CLIMessages.StatusKeys.FILE_PATH]),
                metadata=result[CLIMessages.StatusKeys.PARSING_RESULT],
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
def generate_organization_plan(scanned_files: list[Any]) -> list[Any]:
    """Generate organization plan.

    Args:
        scanned_files: List of scanned files

    Returns:
        Organization plan
    """
    log_manager = OperationLogManager(Path.cwd())
    organizer = FileOrganizer(log_manager=log_manager)
    return organizer.generate_plan(scanned_files)


@handle_cli_errors(
    operation="generate_enhanced_organization_plan", command_name="organize"
)
def generate_enhanced_organization_plan(
    scanned_files: list[Any],
    options: OrganizeOptions,
) -> list[Any]:
    """Generate enhanced organization plan with grouping.

    Args:
        scanned_files: List of scanned files
        options: Organize options

    Returns:
        Enhanced organization plan
    """
    grouper = FileGrouper(similarity_threshold=0.7)
    resolution_detector = ResolutionDetector()
    subtitle_matcher = SubtitleMatcher()
    tmdb_client = TMDBClient(language=Language.KOREAN)  # noqa: F841

    file_groups = grouper.group_files(scanned_files)
    operations = []

    for group in file_groups:
        best_file = resolution_detector.find_highest_resolution(group.files)
        if not best_file:
            continue

        korean_title = group.title
        subtitles = subtitle_matcher.find_matching_subtitles(
            best_file,
            best_file.file_path.parent,
        )

        destination_base = options.destination if options.destination else "Anime"
        high_res_path = (
            Path(destination_base)
            / korean_title
            / f"Season {best_file.metadata.season or 1:02d}"
        )
        low_res_path = (
            Path(destination_base)
            / "low_res"
            / korean_title
            / f"Season {best_file.metadata.season or 1:02d}"
        )

        operations.append(
            {
                "source": best_file.file_path,
                "destination": high_res_path / best_file.file_path.name,
                "type": "move",
                "is_highest_resolution": True,
            }
        )

        for subtitle in subtitles:
            operations.append(
                {
                    "source": subtitle,
                    "destination": high_res_path / subtitle.name,
                    "type": "move",
                    "is_subtitle": True,
                }
            )

        for file in group.files:
            if file != best_file:
                operations.append(
                    {
                        "source": file.file_path,
                        "destination": low_res_path / file.file_path.name,
                        "type": "move",
                        "is_highest_resolution": False,
                    }
                )

    return operations


def execute_organization_plan(
    plan: list[Any],
    options: OrganizeOptions,
    console: Console,
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

    return perform_organization(plan, options)


def confirm_organization(console: Console) -> bool:
    """Ask for confirmation.

    Args:
        console: Rich console

    Returns:
        True if confirmed
    """
    try:
        from rich.prompt import Confirm

        if not Confirm.ask("Do you want to proceed?"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return False
        return True
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/yellow]")
        return False


@handle_cli_errors(operation="perform_organization", command_name="organize")
def perform_organization(plan: list[Any], options: OrganizeOptions) -> int:
    """Perform the actual organization.

    Args:
        plan: Organization plan
        options: Organize options

    Returns:
        Exit code
    """
    from rich.console import Console

    console = Console()
    log_manager = OperationLogManager(Path.cwd())
    organizer = FileOrganizer(log_manager=log_manager)

    operation_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    progress_manager = create_progress_manager(disabled=options.json_output)

    with progress_manager.spinner("Organizing files..."):
        moved_files = organizer.execute_plan(plan, operation_id)

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
        except Exception as e:  # noqa: BLE001
            console.print(
                f"[bold yellow]Warning: Could not save operation log: {e}[/bold yellow]"
            )
    else:
        console.print("[yellow]No files were moved[/yellow]")

    return 0


def collect_organize_data(
    plan: list[Any],
    options: OrganizeOptions,
    is_dry_run: bool = False,
    moved_files: list[Any] | None = None,
    operation_id: str | None = None,
) -> dict[str, Any]:
    """Collect organize data for JSON output.

    Args:
        plan: Organization plan
        options: Organize options
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
        source_path = str(operation.source_file.file_path)
        destination_path = str(operation.destination_path)

        try:
            file_size = Path(source_path).stat().st_size
            total_size += file_size
        except (OSError, TypeError):
            file_size = 0

        operation_info = {
            "source_path": source_path,
            "destination_path": destination_path,
            "file_name": Path(source_path).name,
            "file_size": file_size,
            "file_extension": Path(source_path).suffix.lower(),
        }

        if (
            hasattr(operation.source_file, "parsing_result")
            and operation.source_file.parsing_result
        ):
            parsing_result = operation.source_file.parsing_result
            operation_info["parsing_result"] = {
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
                "other_info": parsing_result.other_info,
            }

        operations_data.append(operation_info)

    def format_size(size_bytes: float) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    return {
        "organize_summary": {
            "total_operations": total_operations,
            "successful_moves": successful_moves,
            "is_dry_run": is_dry_run,
            "operation_id": operation_id,
            "total_size_bytes": total_size,
            "total_size_formatted": format_size(total_size),
            "success_rate": (
                (successful_moves / total_operations * 100)
                if total_operations > 0
                else 0
            ),
        },
        "operations": operations_data,
    }


def print_dry_run_plan(plan: list[Any], console: Console) -> None:
    """Print dry run plan.

    Args:
        plan: Organization plan
        console: Rich console
    """
    console.print("[bold blue]Dry Run - Organization Plan:[/bold blue]")
    console.print()

    for operation in plan:
        source = operation.source_file.file_path
        destination = operation.destination_path
        console.print(f"[yellow]Would move:[/yellow] {source}")
        console.print(f"[green]To:[/green] {destination}")
        console.print()

    console.print(f"[bold]Total operations: {len(plan)}[/bold]")


def print_execution_plan(plan: list[Any], console: Console) -> None:
    """Print execution plan.

    Args:
        plan: Organization plan
        console: Rich console
    """
    console.print("[bold blue]Organization Plan:[/bold blue]")
    console.print()

    for operation in plan:
        source = operation.source_file.file_path
        destination = operation.destination_path
        console.print(f"[yellow]Will move:[/yellow] {source}")
        console.print(f"[green]To:[/green] {destination}")
        console.print()
