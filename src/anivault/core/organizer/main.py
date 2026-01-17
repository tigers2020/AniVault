"""
File organization engine for AniVault.

This module provides the FileOrganizer class that handles the planning
and execution of file organization operations based on scanned anime metadata.
"""

from __future__ import annotations

import logging
import os
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

    def organize(self, scanned_files: list[ScannedFile], dry_run: bool = True) -> list[FileOperation] | list[OperationResult]:
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
        results = self.execute_plan(plan)
        self._cleanup_empty_leaf_dirs(scanned_files)
        return results

    def cleanup_empty_dirs_for_paths(
        self, 
        source_paths: list[Path], 
        source_root: Path | None = None,
    ) -> None:
        """Remove empty leaf directories under source roots for given paths.
        
        Args:
            source_paths: List of source file paths that were moved
            source_root: Optional source root directory. If provided, cleanup will
                        start from this root instead of finding common path from files.
        """
        if not source_paths:
            return
        
        # Use provided source_root if available, otherwise find common path
        if source_root and source_root.exists() and source_root.is_dir():
            roots = [source_root]
        else:
            roots = self._collect_cleanup_roots_from_paths(source_paths)
        
        for root in roots:
            removed_count = self._remove_empty_leaf_dirs(root)
            if removed_count > 0:
                logger.info(
                    "Removed %d empty directories under %s",
                    removed_count,
                    root,
                )

    def _build_destination_path(self, scanned_file: ScannedFile) -> Path:
        """
        Build destination path for a scanned file.

        Args:
            scanned_file: The ScannedFile to build path for.

        Returns:
            Path object for the destination.
        """
        if not scanned_file.metadata:
            return Path.home() / FileSystem.OUTPUT_DIRECTORY / scanned_file.file_path.name

        # Get settings for path context (handle None case)
        if self.settings.folders is None:
            target_folder = Path.home() / FileSystem.OUTPUT_DIRECTORY
            media_type = FolderDefaults.DEFAULT_MEDIA_TYPE
            organize_by_resolution = FolderDefaults.ORGANIZE_BY_RESOLUTION
            organize_by_year = FolderDefaults.ORGANIZE_BY_YEAR
            logger.error(
                "Folder settings not found in self.settings! Using defaults: resolution=%s, year=%s",
                organize_by_resolution,
                organize_by_year,
            )
        else:
            default_target = str(Path.home() / FileSystem.OUTPUT_DIRECTORY)
            target_folder = Path(self.settings.folders.target_folder or default_target)
            media_type = self.settings.folders.media_type or FolderDefaults.DEFAULT_MEDIA_TYPE
            organize_by_resolution = self.settings.folders.organize_by_resolution
            organize_by_year = self.settings.folders.organize_by_year
            logger.debug(
                "FileOrganizer settings: resolution=%s, year=%s, target=%s, media_type=%s",
                organize_by_resolution,
                organize_by_year,
                target_folder,
                media_type,
            )

        # Determine if series has mixed resolutions
        summaries = self._resolution_analyzer.analyze_series([scanned_file])
        series_has_mixed_resolutions = any(summary.has_mixed_resolutions for _, summary in summaries) if summaries.size > 0 else False

        # Create path context
        context = PathContext(
            scanned_file=scanned_file,
            series_has_mixed_resolutions=series_has_mixed_resolutions,
            target_folder=target_folder,
            media_type=media_type,
            organize_by_resolution=organize_by_resolution,
            organize_by_year=organize_by_year,
        )
        
        logger.debug(
            "Building path for %s with context: resolution=%s, year=%s, target=%s",
            scanned_file.file_path.name[:50],
            organize_by_resolution,
            organize_by_year,
            target_folder,
        )

        organized_path = self._path_builder.build_path(context)
        
        logger.debug(
            "Built path: %s -> %s",
            scanned_file.file_path.name[:50],
            organized_path,
        )

        return organized_path

    def _cleanup_empty_leaf_dirs(self, scanned_files: list[ScannedFile]) -> None:
        """Remove empty leaf directories under source roots after organizing."""
        roots = self._collect_cleanup_roots_from_paths([scanned_file.file_path for scanned_file in scanned_files])
        for root in roots:
            removed_count = self._remove_empty_leaf_dirs(root)
            if removed_count > 0:
                logger.info(
                    "Removed %d empty directories under %s",
                    removed_count,
                    root,
                )

    @staticmethod
    def _collect_cleanup_roots_from_paths(source_paths: list[Path]) -> list[Path]:
        """Collect common source roots for cleanup."""
        if not source_paths:
            return []
        grouped: dict[str, list[Path]] = {}
        for source_path in source_paths:
            parent = source_path.parent
            anchor = parent.anchor or parent.drive
            grouped.setdefault(anchor, []).append(parent)

        roots: list[Path] = []
        for parents in grouped.values():
            if not parents:
                continue
            try:
                common_path = Path(os.path.commonpath([str(p) for p in parents]))
            except ValueError:
                continue
            if common_path.exists() and common_path.is_dir():
                roots.append(common_path)

        return roots

    @staticmethod
    def _remove_empty_leaf_dirs(root: Path) -> int:
        """Remove empty leaf directories under a root path.
        
        Uses iterative approach to handle os.walk snapshot issue:
        os.walk captures directory structure at start, so after removing
        a child directory, parent may appear empty but os.walk still sees it
        as non-empty. We iterate until no more empty directories are found.
        """
        if not root.exists() or not root.is_dir():
            return 0

        total_removed = 0
        max_iterations = 100  # Safety limit to prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            removed_this_iteration = 0
            root_str = str(root)
            
            # Walk bottom-up to remove leaf directories first
            for dirpath, dirnames, filenames in os.walk(root_str, topdown=False):
                if dirpath == root_str:
                    continue
                
                # Check if directory is actually empty (not just in snapshot)
                dir_path = Path(dirpath)
                if not dir_path.exists():
                    continue
                    
                try:
                    # Re-check actual contents (not snapshot)
                    actual_contents = list(dir_path.iterdir())
                    
                    if not actual_contents:
                        # Directory is actually empty, remove it
                        dir_path.rmdir()
                        removed_this_iteration += 1
                except OSError as e:
                    logger.warning("Failed to remove empty directory: %s: %s", dirpath, e)
            
            total_removed += removed_this_iteration
            
            # If no directories were removed this iteration, we're done
            if removed_this_iteration == 0:
                break
        
        if iteration >= max_iterations:
            logger.warning("Reached max iterations (%d) when removing empty directories under %s", max_iterations, root)

        return total_removed
