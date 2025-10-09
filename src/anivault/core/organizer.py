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
from typing import Any

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

    def _analyze_series_resolutions(
        self,
        scanned_files: list[ScannedFile],
    ) -> dict[str, bool]:
        """
        Analyze which series have mixed resolutions.

        Args:
            scanned_files: List of ScannedFile objects to analyze

        Returns:
            Dictionary mapping series title to whether it has mixed resolutions.
            True = has both high and low resolutions, False = single resolution type
        """
        from collections import defaultdict

        from anivault.shared.constants import VideoQuality

        # Group files by series title and collect their resolutions
        series_resolutions: dict[str, set[bool]] = defaultdict(set)

        for scanned_file in scanned_files:
            # Skip files without TMDB match
            match_result = scanned_file.metadata.other_info.get("match_result")
            if not match_result:
                continue

            series_title = match_result.title
            quality = scanned_file.metadata.quality

            # Determine if this file is high or low resolution
            is_high_res = VideoQuality.is_high_resolution(quality)
            series_resolutions[series_title].add(is_high_res)

        # Determine which series have mixed resolutions
        series_has_mixed: dict[str, bool] = {}
        for series_title, res_types in series_resolutions.items():
            # Mixed if we have both True (high) and False (low) resolutions
            series_has_mixed[series_title] = len(res_types) > 1

        logger.debug(
            "Resolution analysis: %d series, %d with mixed resolutions",
            len(series_has_mixed),
            sum(series_has_mixed.values()),
        )

        return series_has_mixed

    def _construct_destination_path(
        self,
        scanned_file: ScannedFile,
        series_has_mixed_resolutions: bool = False,
    ) -> Path:
        """
        Construct the destination path for a scanned file.

        This method builds the target file path based on the file's metadata
        and the configured naming convention.

        Args:
            scanned_file: ScannedFile instance containing file and metadata information.
            series_has_mixed_resolutions: Whether this series has files with different resolutions.
                If False (single resolution), all files use normal folder structure regardless of quality.

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
        # episode_number and episode_title available but not currently used in path construction
        # episode_number = metadata.episode  # noqa: ERA001
        # episode_title = metadata.other_info.get("episode_title")  # noqa: ERA001

        # Clean series title for filesystem compatibility
        series_title = self._sanitize_filename(series_title)

        # Get organization settings
        from anivault.config.settings import get_config

        config = get_config()

        # Use folders.target_folder if set, otherwise fallback to default
        if config.folders and config.folders.target_folder:
            target_folder = Path(config.folders.target_folder)
            media_type = config.folders.media_type
        else:
            # No target folder configured - must be set in config
            from anivault.shared.errors import ApplicationError, ErrorCode, ErrorContext

            raise ApplicationError(
                ErrorCode.CONFIGURATION_ERROR,
                "Target folder not configured. Please set folders.target_folder in config.toml or via GUI settings.",
                ErrorContext(operation="get_target_folder"),
            )

        # Default to Season 1 if no season specified
        if season_number is None:
            season_number = 1

        season_dir = f"Season {season_number:02d}"

        # Check if organize_by_resolution is enabled AND series has mixed resolutions
        if (
            config.folders
            and config.folders.organize_by_resolution
            and series_has_mixed_resolutions
        ):
            # Import VideoQuality for resolution classification
            from anivault.shared.constants import VideoQuality

            # Get resolution from metadata
            resolution = metadata.quality

            # Determine if high or low resolution
            if VideoQuality.is_high_resolution(resolution):
                # High resolution: normal folder structure
                series_dir = target_folder / media_type / series_title / season_dir
            else:
                # Low resolution: under low_res folder (only when series has mixed resolutions)
                series_dir = (
                    target_folder
                    / media_type
                    / VideoQuality.LOW_RES_FOLDER
                    / series_title
                    / season_dir
                )
        else:
            # Build path without resolution organization
            # (either feature disabled OR series has single resolution type)
            series_dir = target_folder / media_type / series_title / season_dir

        # Use original filename (as requested by user)
        original_filename = scanned_file.file_path.name

        return series_dir / original_filename

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

        # Replace multiple spaces with single space, keep underscores as spaces
        import re

        # Replace underscores with spaces
        sanitized = sanitized.replace("_", " ")
        # Replace multiple spaces with single space
        sanitized = re.sub(r"\s+", " ", sanitized)

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

        # Analyze which series have mixed resolutions (only if organize_by_resolution is enabled)
        from anivault.config.settings import get_config

        config = get_config()
        series_has_mixed_resolutions: dict[str, bool] = {}

        if config.folders and config.folders.organize_by_resolution:
            series_has_mixed_resolutions = self._analyze_series_resolutions(
                scanned_files,
            )

        for scanned_file in scanned_files:
            # Skip files that don't have sufficient metadata
            if not scanned_file.metadata.title:
                continue

            # Skip files without TMDB match result (only organize matched files)
            match_result = scanned_file.metadata.other_info.get("match_result")
            if not match_result:
                logger.debug(
                    "Skipping file without TMDB match: %s",
                    scanned_file.file_path.name,
                )
                continue

            # Get series title for resolution analysis
            series_title = match_result.title if match_result else None
            has_mixed_res = series_has_mixed_resolutions.get(series_title, False)

            # Construct destination path with mixed resolution info
            destination_path = self._construct_destination_path(
                scanned_file,
                series_has_mixed_resolutions=has_mixed_res,
            )

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
            subtitle_operations = self._find_matching_subtitles(
                scanned_file,
                destination_path,
            )
            operations.extend(subtitle_operations)

        return operations

    def _find_matching_subtitles(
        self,
        scanned_file: ScannedFile,
        destination_path: Path,
    ) -> list[FileOperation]:
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
        matching_subtitles = subtitle_matcher.find_matching_subtitles(
            scanned_file,  # Pass ScannedFile object
            scanned_file.file_path.parent,  # Search in video file's directory
        )

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

            logger.debug(
                "Found matching subtitle: %s -> %s",
                subtitle_path.name,
                subtitle_dest,
            )

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
        return None

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
