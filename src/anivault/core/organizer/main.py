"""
File organization engine for AniVault.

This module provides the FileOrganizer class that handles the planning
and execution of file organization operations based on scanned anime metadata.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, OperationType, ScannedFile
from anivault.core.organizer.executor import FileOperationExecutor
from anivault.core.organizer.path_builder import PathBuilder, PathContext
from anivault.core.organizer.resolution import ResolutionAnalyzer

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
        settings: Any | None = None,
    ) -> None:
        """
        Initialize the FileOrganizer.

        Args:
            log_manager: OperationLogManager instance for logging operations.
            settings: Settings instance containing configuration. If None, loads default settings.
        """
        self.log_manager = log_manager
        from anivault.config.settings import load_settings

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
        Generate a plan of file operations based on scanned files.

        This method analyzes scanned files, determines their destination paths,
        and creates a list of FileOperation objects (move/copy) to achieve
        the desired organization.

        Args:
            scanned_files: List of ScannedFile objects to organize.

        Returns:
            List of FileOperation objects representing the organization plan.
        """
        operations: list[FileOperation] = []

        # Use ResolutionAnalyzer service
        resolution_summaries = self._resolution_analyzer.analyze_series(scanned_files)
        # Convert ResolutionSummary objects to dict[str, bool] for compatibility
        series_has_mixed_resolutions = {
            title: summary.has_mixed_resolutions
            for title, summary in resolution_summaries.items()
        }

        for scanned_file in scanned_files:
            # Determine if the series has mixed resolutions
            series_title = self._path_builder._extract_series_title(scanned_file)
            has_mixed_resolutions = series_has_mixed_resolutions.get(
                series_title, False
            )

            # Construct destination path using PathBuilder service
            # Use folders config (same as original organizer.py)
            target_folder = (
                Path(self.settings.folders.target_folder)
                if self.settings.folders
                else Path()
            )
            media_type = (
                self.settings.folders.media_type if self.settings.folders else "anime"
            )
            organize_by_resolution = (
                self.settings.folders.organize_by_resolution
                if self.settings.folders
                else False
            )

            path_context = PathContext(
                scanned_file=scanned_file,
                series_has_mixed_resolutions=has_mixed_resolutions,
                target_folder=target_folder,
                media_type=media_type,
                organize_by_resolution=organize_by_resolution,
            )
            destination_path = self._path_builder.build_path(path_context)

            # Skip if source and destination are the same
            if scanned_file.file_path.resolve() == destination_path.resolve():
                continue

            # Create file operation for main file
            operation = FileOperation(
                operation_type=OperationType.MOVE,
                source_path=scanned_file.file_path,
                destination_path=destination_path,
            )
            operations.append(operation)

            # Find and add matching subtitle files using FileOperationExecutor
            subtitle_operations = self._executor.find_matching_subtitles(
                scanned_file,
                destination_path,
            )
            operations.extend(subtitle_operations)

        return operations

    def execute_plan(
        self,
        plan: list[FileOperation],
        operation_id: str,
        no_log: bool = False,
    ) -> list[tuple[str, str]]:
        """
        Execute a plan of file operations.

        This method delegates to FileOperationExecutor for actual execution,
        providing a clean separation of concerns and improved testability.

        Args:
            plan: List of FileOperation objects to execute.
            operation_id: Unique identifier for this operation.
            no_log: If True, skip logging the operation.

        Returns:
            List of tuples containing (source_path, destination_path) for moved files.
        """
        # Delegate to FileOperationExecutor
        results = self._executor.execute_batch(
            operations=plan,
            dry_run=False,
            operation_id=operation_id,
            no_log=no_log,
        )

        # Convert results to legacy format for backward compatibility
        moved_files: list[tuple[str, str]] = [
            (result.source_path, result.destination_path)
            for result in results
            if result.success and not result.skipped
        ]

        return moved_files

    def organize(
        self,
        scanned_files: list[ScannedFile],
        dry_run: bool = False,
        no_log: bool = False,
    ) -> list[FileOperation] | list[tuple[str, str]]:
        """
        Organize scanned files according to their metadata.

        This is the main public method that orchestrates the planning
        and execution of file organization operations.

        Args:
            scanned_files: List of ScannedFile objects to organize.
            dry_run: If True, return the plan without executing it.
            no_log: If True, skip logging the operation.

        Returns:
            If dry_run is True, returns the list of FileOperation objects.
            If dry_run is False, returns the list of moved file tuples.
        """
        # Generate the organization plan
        plan = self.generate_plan(scanned_files)

        if dry_run:
            return plan

        # Execute the plan
        operation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        moved_files = self.execute_plan(plan, operation_id, no_log)

        return moved_files
