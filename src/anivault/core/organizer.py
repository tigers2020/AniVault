"""
File organization engine for AniVault.

This module provides the FileOrganizer class that handles the planning
and execution of file organization operations based on scanned anime metadata.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from anivault.config.settings import AppConfig, Settings
from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, OperationType, ScannedFile


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
        self.settings = settings or Settings.from_environment()
        self.app_config = self.settings.app

    def _construct_destination_path(self, scanned_file: ScannedFile) -> Path:
        """
        Construct the destination path for a scanned file.

        This method builds the target file path based on the file's metadata
        and the configured naming convention.

        Args:
            scanned_file: ScannedFile instance containing file and metadata information.

        Returns:
            Path object representing the destination path for the file.
        """
        # Get metadata from the parsed result
        metadata = scanned_file.metadata
        
        # Extract series information
        series_title = metadata.anime_title or "Unknown Series"
        season_number = metadata.season_number
        episode_number = metadata.episode_number
        episode_title = metadata.episode_title
        
        # Clean series title for filesystem compatibility
        series_title = self._sanitize_filename(series_title)
        
        # Build directory structure: Series/Season XX/
        base_dir = Path("Anime")  # Base directory for anime files
        
        if season_number is not None:
            season_dir = f"Season {season_number:02d}"
            series_dir = base_dir / series_title / season_dir
        else:
            series_dir = base_dir / series_title
        
        # Build filename
        filename_parts = [series_title]
        
        if season_number is not None:
            filename_parts.append(f"S{season_number:02d}")
        
        if episode_number is not None:
            filename_parts.append(f"E{episode_number:02d}")
        
        if episode_title:
            episode_title = self._sanitize_filename(episode_title)
            filename_parts.append(episode_title)
        
        # Join filename parts
        base_filename = " - ".join(filename_parts)
        
        # Add file extension
        filename = f"{base_filename}{scanned_file.extension}"
        
        return series_dir / filename

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename for filesystem compatibility.

        Args:
            filename: Original filename to sanitize.

        Returns:
            Sanitized filename safe for filesystem use.
        """
        # Characters not allowed in filenames on most filesystems
        invalid_chars = '<>:"/\\|?*'
        
        # Replace invalid characters with underscores
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(' .')
        
        # Replace multiple spaces/underscores with single underscore
        import re
        sanitized = re.sub(r'[_\s]+', '_', sanitized)
        
        # Ensure filename is not empty
        if not sanitized:
            sanitized = "Unknown"
        
        return sanitized

    def generate_plan(self, scanned_files: list[ScannedFile]) -> list[FileOperation]:
        """
        Generate a plan of file operations for organizing scanned files.

        This method creates a list of FileOperation objects representing
        the proposed file moves without actually executing them.

        Args:
            scanned_files: List of ScannedFile objects to organize.

        Returns:
            List of FileOperation objects representing the organization plan.
        """
        operations: list[FileOperation] = []
        
        for scanned_file in scanned_files:
            # Skip files that don't have sufficient metadata
            if not scanned_file.metadata.anime_title:
                continue
            
            # Construct destination path
            destination_path = self._construct_destination_path(scanned_file)
            
            # Skip if source and destination are the same
            if scanned_file.file_path.resolve() == destination_path.resolve():
                continue
            
            # Create file operation
            operation = FileOperation(
                operation_type=OperationType.MOVE,
                source_path=scanned_file.file_path,
                destination_path=destination_path,
            )
            
            operations.append(operation)
        
        return operations

    def execute_plan(
        self,
        plan: list[FileOperation],
        operation_id: str,
        no_log: bool = False,
    ) -> list[tuple[str, str]]:
        """
        Execute a plan of file operations.

        This method performs the actual file system operations based on
        the provided plan, including directory creation and file moves.

        Args:
            plan: List of FileOperation objects to execute.
            operation_id: Unique identifier for this operation.
            no_log: If True, skip logging the operation.

        Returns:
            List of tuples containing (source_path, destination_path) for moved files.

        Raises:
            OSError: If file operations fail.
        """
        moved_files: list[tuple[str, str]] = []
        
        for operation in plan:
            try:
                # Ensure destination directory exists
                destination_dir = operation.destination_path.parent
                destination_dir.mkdir(parents=True, exist_ok=True)
                
                # Perform the file move
                if operation.operation_type == OperationType.MOVE:
                    shutil.move(str(operation.source_path), str(operation.destination_path))
                    moved_files.append((
                        str(operation.source_path),
                        str(operation.destination_path)
                    ))
                elif operation.operation_type == OperationType.COPY:
                    shutil.copy2(str(operation.source_path), str(operation.destination_path))
                    moved_files.append((
                        str(operation.source_path),
                        str(operation.destination_path)
                    ))
                    
            except (OSError, shutil.Error) as e:
                # Log the error but continue with other operations
                print(f"Failed to move {operation.source_path} to {operation.destination_path}: {e}")
                continue
        
        # Log the operation if requested
        if not no_log and moved_files:
            try:
                self.log_manager.save_plan(plan)
            except Exception as e:
                print(f"Warning: Failed to save operation log: {e}")
        
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
