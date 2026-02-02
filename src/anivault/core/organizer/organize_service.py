"""Core organize service - CLI/GUI agnostic business logic.

This module provides pure organization logic without presentation concerns
(console, JSON, progress UI). Both CLI and GUI layers use these functions.
"""

from __future__ import annotations

import logging
from pathlib import Path

from anivault.config import Settings
from anivault.core.file_grouper import FileGrouper
from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, OperationType, ScannedFile
from anivault.core.organizer.executor import OperationResult
from anivault.core.organizer.main import FileOrganizer
from anivault.core.resolution_detector import ResolutionDetector
from anivault.core.subtitle_matcher import SubtitleMatcher

logger = logging.getLogger(__name__)


def generate_organization_plan(
    scanned_files: list[ScannedFile],
    *,
    settings: Settings | None = None,
) -> list[FileOperation]:
    """Generate organization plan using FileOrganizer.

    Args:
        scanned_files: List of scanned files to organize.
        settings: Optional settings. If None, loads default settings.

    Returns:
        List of FileOperation representing the organization plan.
    """
    log_manager = OperationLogManager(Path.cwd())
    organizer = FileOrganizer(log_manager=log_manager, settings=settings)
    return organizer.generate_plan(scanned_files)


def _generate_destination_paths(destination_base: str, korean_title: str, season: int) -> tuple[Path, Path]:
    """Generate high and low resolution destination paths."""
    season_str = f"Season {season:02d}"
    high_res_path = Path(destination_base) / korean_title / season_str
    low_res_path = Path(destination_base) / "low_res" / korean_title / season_str
    return high_res_path, low_res_path


def _create_move_operation(source: Path, destination: Path) -> FileOperation:
    """Create a move operation."""
    return FileOperation(
        operation_type=OperationType.MOVE,
        source_path=source,
        destination_path=destination,
    )


def generate_enhanced_organization_plan(
    scanned_files: list[ScannedFile],
    destination: str = "Anime",
    *,
    similarity_threshold: float = 0.7,
) -> list[FileOperation]:
    """Generate enhanced organization plan with grouping.

    Uses FileGrouper, ResolutionDetector, SubtitleMatcher to create
    a plan that groups by title, picks best resolution, and moves subtitles.

    Args:
        scanned_files: List of scanned files to organize.
        destination: Base destination directory.
        similarity_threshold: Title similarity threshold for grouping.

    Returns:
        List of FileOperation representing the enhanced plan.
    """
    grouper = FileGrouper(similarity_threshold=similarity_threshold)
    resolution_detector = ResolutionDetector()
    subtitle_matcher = SubtitleMatcher()

    file_groups = grouper.group_files(scanned_files)
    operations: list[FileOperation] = []

    for group in file_groups:
        best_file = resolution_detector.find_highest_resolution(group.files)
        if not best_file:
            continue

        korean_title = group.title
        subtitles = subtitle_matcher.find_matching_subtitles(
            best_file,
            best_file.file_path.parent,
        )

        season = best_file.metadata.season or 1
        high_res_path, low_res_path = _generate_destination_paths(destination, korean_title, season)

        operations.append(
            _create_move_operation(
                best_file.file_path,
                high_res_path / best_file.file_path.name,
            )
        )

        for subtitle in subtitles:
            operations.append(
                _create_move_operation(
                    subtitle,
                    high_res_path / subtitle.name,
                )
            )

        for file in group.files:
            if file != best_file:
                operations.append(
                    _create_move_operation(
                        file.file_path,
                        low_res_path / file.file_path.name,
                    )
                )

    return operations


def execute_organization_plan(
    plan: list[FileOperation],
    source_directory: Path,
    *,
    settings: Settings | None = None,
) -> list[OperationResult]:
    """Execute organization plan - pure business logic, no UI.

    Performs file moves and cleanup of empty directories.
    Does not handle dry_run, confirmation, or output formatting.

    Args:
        plan: Organization plan to execute.
        source_directory: Source root for cleanup of empty dirs.
        settings: Optional settings. If None, loads default settings.

    Returns:
        List of OperationResult for each executed operation.
    """
    log_manager = OperationLogManager(Path.cwd())
    organizer = FileOrganizer(log_manager=log_manager, settings=settings)

    moved_files = organizer.execute_plan(plan)

    successful_sources = [Path(result.source_path) for result in moved_files if result.success]
    if successful_sources:
        try:
            organizer.cleanup_empty_dirs_for_paths(successful_sources, source_root=source_directory)
        except OSError as exc:
            logger.warning("Failed to cleanup empty directories: %s", exc)

    return moved_files
