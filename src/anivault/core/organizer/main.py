"""
File organization engine for AniVault.

This module provides the FileOrganizer class that handles the planning
and execution of file organization operations based on scanned anime metadata.
"""

from __future__ import annotations

import logging
from pathlib import Path

from anivault.config import Settings, load_settings
from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, OperationType, ScannedFile
from anivault.core.organizer.executor import FileOperationExecutor, OperationResult
from anivault.core.organizer.path_builder import PathBuilder, PathContext
from anivault.core.organizer.resolution import ResolutionAnalyzer
from anivault.shared.constants import FileSystem, FolderDefaults

logger = logging.getLogger(__name__)


class FileOrganizer:
    """
    File organization engine for anime files.

    This class handles the planning and execution of file organization operations,
    organizing anime files into a structured directory layout based on their metadata.
    """

    def __init__(
        self,
        log_manager: OperationLogManager,
        settings: Settings | None = None,
    ) -> None:
        """
        Initialize the FileOrganizer.

        Args:
            log_manager: OperationLogManager instance for logging operations.
            settings: Settings instance containing configuration. If None, loads default settings.
        """
        self.log_manager = log_manager
        self.settings = settings or load_settings()
        self.app_config = self.settings.app

        # Initialize service components
        self._resolution_analyzer = ResolutionAnalyzer(settings=self.settings)
        self._path_builder = PathBuilder(settings=self.settings)
        self._executor = FileOperationExecutor(
            log_manager=log_manager,
            settings=self.settings,
        )

    def generate_plan(self, scanned_files: list[ScannedFile]) -> list[FileOperation]:
        """
        Generate a file organization plan based on scanned files.

        Args:
            scanned_files: List of ScannedFile objects to organize.

        Returns:
            List of FileOperation objects representing the organization plan.
        """
        operations = []

        for scanned_file in scanned_files:
            try:
                # Build destination path
                destination_path = self._build_destination_path(scanned_file)

                # Create move operation
                operation = FileOperation(
                    operation_type=OperationType.MOVE,
                    source_path=scanned_file.file_path,
                    destination_path=destination_path,
                )
                operations.append(operation)

                # Find and add matching subtitle files
                subtitle_operations = self._executor.find_matching_subtitles(
                    scanned_file,
                    destination_path,
                )
                operations.extend(subtitle_operations)

            except (FileNotFoundError, PermissionError):
                logger.exception(
                    "Failed to create operation for %s",
                    scanned_file.file_path,
                )
                # Continue processing other files
                continue
            except OSError:
                logger.exception(
                    "Failed to create operation for %s",
                    scanned_file.file_path,
                )
                # Continue processing other files
                continue
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception(
                    "Failed to create operation for %s",
                    scanned_file.file_path,
                )
                # Continue processing other files
                continue

        return operations

    def execute_plan(self, operations: list[FileOperation]) -> list[OperationResult]:
        """
        Execute a file organization plan.

        Args:
            operations: List of FileOperation objects to execute.

        Returns:
            List[OperationResult]: List of OperationResult objects representing
                the execution results.
        """
        return self._executor.execute_batch(operations)

    def organize(
        self, scanned_files: list[ScannedFile], dry_run: bool = True
    ) -> list[FileOperation] | list[OperationResult]:
        """
        Organize files based on scanned files.

        Args:
            scanned_files: List of ScannedFile objects to organize.
            dry_run: If True, returns FileOperation objects without executing.
                    If False, executes operations and returns OperationResult objects.

        Returns:
            List of FileOperation objects (if dry_run=True) or OperationResult
                objects (if dry_run=False).
        """
        plan = self.generate_plan(scanned_files)

        if dry_run:
            return plan
        return self.execute_plan(plan)

    def _build_destination_path(self, scanned_file: ScannedFile) -> Path:
        """
        Build destination path for a scanned file.

        Args:
            scanned_file: The ScannedFile to build path for.

        Returns:
            Path object for the destination.
        """
        if not scanned_file.metadata:
            return (
                Path.home() / FileSystem.OUTPUT_DIRECTORY / scanned_file.file_path.name
            )

        # Get settings for path context (handle None case)
        if self.settings.folders is None:
            target_folder = Path.home() / FileSystem.OUTPUT_DIRECTORY
            media_type = FolderDefaults.DEFAULT_MEDIA_TYPE
            organize_by_resolution = FolderDefaults.ORGANIZE_BY_RESOLUTION
            organize_by_year = FolderDefaults.ORGANIZE_BY_YEAR
        else:
            default_target = str(Path.home() / FileSystem.OUTPUT_DIRECTORY)
            target_folder = Path(self.settings.folders.target_folder or default_target)
            media_type = (
                self.settings.folders.media_type or FolderDefaults.DEFAULT_MEDIA_TYPE
            )
            organize_by_resolution = self.settings.folders.organize_by_resolution
            organize_by_year = self.settings.folders.organize_by_year

        # Determine if series has mixed resolutions
        summaries = self._resolution_analyzer.analyze_series([scanned_file])
        series_has_mixed_resolutions = (
            any(summary.has_mixed_resolutions for _, summary in summaries)
            if summaries.size > 0
            else False
        )

        # Create path context
        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=series_has_mixed_resolutions,
            target_folder=target_folder,
            media_type=media_type,
            organize_by_resolution=organize_by_resolution,
            organize_by_year=organize_by_year,
        )

        organized_path = self._path_builder.build_path(context)

        return organized_path
