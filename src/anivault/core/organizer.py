"""
File organization engine for AniVault.

This module provides the FileOrganizer class that handles the planning
and execution of file organization operations based on scanned anime metadata.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from anivault.config.settings import Settings
from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, OperationType, ScannedFile

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
        # Get metadata from the parsed result (ParsingResult dataclass)
        metadata = scanned_file.metadata

        # Extract series information
        # Priority: TMDB matched title > parsed title > "Unknown Series"
        match_result = metadata.other_info.get("match_result")
        if match_result:
            # Use TMDB matched title (Korean title from MatchResult dataclass)
            series_title = match_result.title
        else:
            # Fallback to parsed title
            series_title = metadata.title or "Unknown Series"
        
        season_number = metadata.season
        episode_number = metadata.episode
        episode_title = metadata.other_info.get("episode_title")

        # Clean series title for filesystem compatibility
        series_title = self._sanitize_filename(series_title)

        # Get organization settings
        from anivault.config.settings import Settings
        settings = Settings()
        
        # Build directory structure: target_folder/media_type/season_##/korean_title/
        target_folder = Path(settings.organization.target_folder)
        media_type = settings.organization.media_type
        
        if season_number is not None:
            season_dir = f"Season {season_number:02d}"
            series_dir = target_folder / media_type / season_dir / series_title
        else:
            series_dir = target_folder / media_type / series_title

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
            sanitized = sanitized.replace(char, "_")

        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(" .")

        # Replace multiple spaces/underscores with single underscore
        import re

        sanitized = re.sub(r"[_\s]+", "_", sanitized)

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
            if not scanned_file.metadata.title:
                continue
            
            # Skip files without TMDB match result (only organize matched files)
            match_result = scanned_file.metadata.other_info.get("match_result")
            if not match_result:
                logger.debug("Skipping file without TMDB match: %s", scanned_file.file_path.name)
                continue

            # Construct destination path
            destination_path = self._construct_destination_path(scanned_file)

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
            
            # Find and add matching subtitle files
            subtitle_operations = self._find_matching_subtitles(scanned_file, destination_path)
            operations.extend(subtitle_operations)

        return operations

    def _find_matching_subtitles(self, scanned_file: ScannedFile, destination_path: Path) -> list[FileOperation]:
        """Find matching subtitle files for a video file.
        
        Args:
            scanned_file: The video file to find subtitles for
            destination_path: Destination path for the video file
            
        Returns:
            List of FileOperation objects for matching subtitle files
        """
        from anivault.core.subtitle_matcher import SubtitleMatcher
        
        operations: list[FileOperation] = []
        subtitle_matcher = SubtitleMatcher()
        
        # Find matching subtitle files
        matching_subtitles = subtitle_matcher.find_matching_subtitles(scanned_file.file_path)
        
        for subtitle_path in matching_subtitles:
            # Create destination path for subtitle (same directory as video)
            subtitle_dest = destination_path.parent / subtitle_path.name
            
            # Skip if source and destination are the same
            if subtitle_path.resolve() == subtitle_dest.resolve():
                continue
                
            # Create file operation for subtitle
            operation = FileOperation(
                operation_type=OperationType.MOVE,
                source_path=subtitle_path,
                destination_path=subtitle_dest,
            )
            operations.append(operation)
            
            logger.debug("Found matching subtitle: %s -> %s", subtitle_path.name, subtitle_dest)
        
        return operations

    def execute_plan(
        self,
        plan: list[FileOperation],
        operation_id: str,  # noqa: ARG002
        no_log: bool = False,
    ) -> list[tuple[str, str]]:
        """
        Execute a plan of file operations.

        This method orchestrates the execution of file operations by delegating
        to specialized methods for validation, execution, and logging.

        Args:
            plan: List of FileOperation objects to execute.
            operation_id: Unique identifier for this operation.
            no_log: If True, skip logging the operation.

        Returns:
            List of tuples containing (source_path, destination_path) for moved files.
        """
        moved_files: list[tuple[str, str]] = []

        for operation in plan:
            try:
                # Validate operation before execution
                self._validate_operation(operation)

                # Ensure destination directory exists
                self._ensure_destination_directory(operation.destination_path)

                # Execute the file operation
                result = self._execute_file_operation(operation)
                if result:
                    moved_files.append(result)

            except FileNotFoundError as e:
                self._handle_operation_error(operation, e)
                continue
            except FileExistsError as e:
                self._handle_operation_error(operation, e)
                continue
            except (OSError, shutil.Error) as e:
                self._handle_operation_error(operation, e)
                continue

        # Log the operation if requested
        self._log_operation_if_needed(plan, moved_files, no_log)

        return moved_files

    def _validate_operation(self, operation: FileOperation) -> None:
        """Validate a file operation before execution.

        Args:
            operation: FileOperation to validate

        Raises:
            OSError: If validation fails
        """
        # Check if source file exists
        if not operation.source_path.exists():
            msg = f"Source file does not exist: {operation.source_path}"
            raise OSError(msg)

        # Check if source is a file (not directory)
        if not operation.source_path.is_file():
            msg = f"Source path is not a file: {operation.source_path}"
            raise OSError(msg)

        # Check if destination parent directory is writable
        destination_parent = operation.destination_path.parent
        if destination_parent.exists() and not destination_parent.is_dir():
            msg = f"Destination parent is not a directory: {destination_parent}"
            raise OSError(
                msg,
            )

    def _ensure_destination_directory(self, destination_path: Path) -> None:
        """Ensure the destination directory exists.

        Args:
            destination_path: Path to the destination file

        Raises:
            OSError: If directory creation fails
        """
        destination_dir = destination_path.parent
        destination_dir.mkdir(parents=True, exist_ok=True)

    def _execute_file_operation(
        self,
        operation: FileOperation,
    ) -> tuple[str, str] | None:
        """Execute a single file operation.

        Args:
            operation: FileOperation to execute

        Returns:
            Tuple of (source_path, destination_path) if successful, None otherwise

        Raises:
            FileNotFoundError: If source file is not found
            FileExistsError: If destination file already exists
            IOError: If other filesystem-related error occurs
        """
        if operation.operation_type == OperationType.MOVE:
            try:
                shutil.move(
                    str(operation.source_path),
                    str(operation.destination_path),
                )
                return (str(operation.source_path), str(operation.destination_path))
            except FileNotFoundError as e:
                msg = f"Source file not found: {operation.source_path}"
                raise FileNotFoundError(
                    msg,
                ) from e
            except FileExistsError as e:
                msg = (
                    f"File already exists at destination: {operation.destination_path}"
                )
                raise FileExistsError(
                    msg,
                ) from e
            except OSError as e:
                msg = f"IO error occurred for {operation.source_path}: {e}"
                raise OSError(
                    msg,
                ) from e

        elif operation.operation_type == OperationType.COPY:
            try:
                shutil.copy2(
                    str(operation.source_path),
                    str(operation.destination_path),
                )
                return (str(operation.source_path), str(operation.destination_path))
            except FileNotFoundError as e:
                msg = f"Source file not found: {operation.source_path}"
                raise FileNotFoundError(
                    msg,
                ) from e
            except FileExistsError as e:
                msg = (
                    f"File already exists at destination: {operation.destination_path}"
                )
                raise FileExistsError(
                    msg,
                ) from e
            except OSError as e:
                msg = f"IO error occurred for {operation.source_path}: {e}"
                raise OSError(
                    msg,
                ) from e

        # Note: All operation types covered above (MOVE, COPY)

    def _handle_operation_error(
        self,
        operation: FileOperation,
        error: Exception,
    ) -> None:
        """Handle errors that occur during file operations.

        Args:
            operation: FileOperation that failed
            error: Exception that occurred
        """
        if isinstance(error, FileNotFoundError):
            logger.error(
                "Source file not found, skipping: '%s'",
                operation.source_path,
            )
        elif isinstance(error, FileExistsError):
            logger.error(
                "File already exists at destination, skipping: '%s'",
                operation.destination_path,
            )
        elif isinstance(error, IOError):
            logger.error(
                "An unexpected IO error occurred for '%s': %s",
                operation.source_path,
                error,
            )
        else:
            logger.error(
                "Failed to move %s to %s: %s",
                operation.source_path,
                operation.destination_path,
                error,
            )

    def _log_operation_if_needed(
        self,
        plan: list[FileOperation],
        moved_files: list[tuple[str, str]],
        no_log: bool,
    ) -> None:
        """Log the operation if logging is enabled and files were moved.

        Args:
            plan: List of FileOperation objects
            moved_files: List of successfully moved files
            no_log: If True, skip logging
        """
        if not no_log and moved_files:
            try:
                self.log_manager.save_plan(plan)
            except Exception as e:  # noqa: BLE001
                print(f"Warning: Failed to save operation log: {e}")

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
