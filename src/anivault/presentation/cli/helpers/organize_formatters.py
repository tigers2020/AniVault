"""Organize command formatting helpers.

Extracted from organize.py for better code organization.
Phase 2: Uses application DTOs (OrganizePlanItem, OrganizeResultItem) only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from anivault.application.dtos.organize import OrganizePlanItem, OrganizeResultItem
from anivault.presentation.cli.helpers.format_utils import format_size, get_file_size


def collect_organize_data(
    plan: list[OrganizePlanItem],
    _options: Any,  # OrganizeOptions - unused, kept for API compatibility  # pylint: disable=unused-argument
    moved_files: list[OrganizeResultItem] | None = None,
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
        source_path = operation.source_path
        destination_path = operation.destination_path

        file_size = get_file_size(source_path)
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
            "total_size_formatted": format_size(total_size),
            "success_rate": ((successful_moves / total_operations * 100) if total_operations > 0 else 0),
        },
        "operations": operations_data,
    }


def print_dry_run_plan(plan: list[OrganizePlanItem], console: Console) -> None:
    """Print dry run plan."""
    console.print("[bold blue]Dry Run - Organization Plan:[/bold blue]")
    console.print()

    for operation in plan:
        source, destination = _extract_operation_paths(operation)
        console.print(f"[yellow]Would move:[/yellow] {source}")
        console.print(f"[green]To:[/green] {destination}")
        console.print()

    console.print(f"[bold]Total operations: {len(plan)}[/bold]")


def print_execution_plan(plan: list[OrganizePlanItem], console: Console) -> None:
    """Print execution plan."""
    console.print("[bold blue]Organization Plan:[/bold blue]")
    console.print()

    for operation in plan:
        source, destination = _extract_operation_paths(operation)
        console.print(f"[yellow]Will move:[/yellow] {source}")
        console.print(f"[green]To:[/green] {destination}")
        console.print()


def _extract_operation_paths(operation: OrganizePlanItem) -> tuple[Path, Path]:
    """Extract source/destination paths from operation."""
    return operation.source_path_obj, operation.destination_path_obj
