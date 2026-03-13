"""
Optimized file organization engine using LinkedHashTable.

This module provides the OptimizedFileOrganizer class that leverages
LinkedHashTable for O(1) file operations and efficient duplicate detection.
"""

from __future__ import annotations

import logging
from pathlib import Path

from anivault.config import Settings, load_settings
from anivault.core.data_structures.linked_hash_table import LinkedHashTable
from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, OperationType, ScannedFile
from anivault.core.organizer.executor import FileOperationExecutor, OperationResult
from anivault.core.organizer.path_builder import PathBuilder
from anivault.core.organizer.resolution import ResolutionAnalyzer
from anivault.shared.errors import (
    AniVaultError,
    AniVaultFileError,
    AniVaultPermissionError,
    ErrorCode,
    ErrorContext,
)

logger = logging.getLogger(__name__)


def _validate_scanned_file(scanned_file: ScannedFile) -> None:
    """Validate ScannedFile before adding to cache. Raises on invalid input."""
    if not scanned_file:
        raise ValueError("ScannedFile cannot be None")
    if not hasattr(scanned_file, "file_path") or not hasattr(scanned_file, "metadata"):
        raise AttributeError("ScannedFile must have file_path and metadata attributes")
    if scanned_file.file_path is None:
        raise ValueError("ScannedFile.file_path cannot be None")


def _file_path_str(scanned_file: ScannedFile) -> str:
    """Return string path for logging/errors."""
    return str(scanned_file.file_path) if scanned_file.file_path else "Unknown"


class OptimizedFileOrganizer:
    """
    Optimized file organization engine using LinkedHashTable.

    This class provides the same interface as FileOrganizer but uses
    LinkedHashTable internally for O(1) file operations and efficient
    duplicate detection. It is specifically designed for high-performance
    file organization with memory efficiency and type safety.

    Key Features:
    - O(1) average time complexity for file operations
    - Memory-efficient storage using __slots__
    - Polynomial hash function for better distribution
    - Automatic rehashing with 1.5x growth factor
    - Efficient duplicate detection using (title, episode) keys

    Args:
        log_manager: OperationLogManager instance for logging operations
        settings: Settings instance containing configuration

    Example:
        >>> organizer = OptimizedFileOrganizer(log_manager, settings)
        >>> organizer.add_file(scanned_file)
        >>> duplicates = organizer.find_duplicates()
        >>> plan = organizer.generate_plan(scanned_files)
    """

    def __init__(
        self,
        log_manager: OperationLogManager,
        settings: Settings | None = None,
    ) -> None:
        """
        Initialize the OptimizedFileOrganizer.

        Args:
            log_manager: OperationLogManager instance for logging operations.
            settings: Settings instance containing configuration. If None, loads default settings.
        """
        self.log_manager = log_manager

        self.settings = settings or load_settings()
        self.app_config = self.settings.app

        # Use LinkedHashTable for O(1) file operations
        self._file_cache = LinkedHashTable[tuple[str, int], list[ScannedFile]](
            initial_capacity=1024,
            load_factor=0.75,
        )

        self._resolution_analyzer = ResolutionAnalyzer(settings=self.settings)
        self._path_builder = PathBuilder(settings=self.settings)
        self._executor = FileOperationExecutor(
            log_manager=log_manager,
            settings=self.settings,
        )

    def add_file(self, scanned_file: ScannedFile) -> None:
        """
        Add a scanned file to the cache for processing.

        Args:
            scanned_file: The ScannedFile object to add to the cache.

        Raises:
            ValueError: If scanned_file is None or invalid.
            AttributeError: If scanned_file lacks required attributes.
        """
        _validate_scanned_file(scanned_file)
        try:
            self._add_file_to_cache_inner(scanned_file)
        except OSError as e:
            self._raise_add_file_error(scanned_file, e)
        except Exception as e:  # noqa: BLE001 - wrap unexpected errors as AniVaultError
            self._raise_add_file_error(scanned_file, e)

    def _add_file_to_cache_inner(self, scanned_file: ScannedFile) -> None:
        """Perform cache key computation and put/append. May raise file-related exceptions."""
        title = scanned_file.metadata.title if scanned_file.metadata else "Unknown"
        episode = scanned_file.metadata.episode if scanned_file.metadata else 0
        episode = episode if episode is not None else 0
        key = (title, episode)

        existing_files = self._file_cache.get(key)
        if existing_files:
            existing_files.append(scanned_file)
            logger.debug(
                "Added duplicate file to cache: %s (title: %s, episode: %d)",
                scanned_file.file_path.name,
                title,
                episode,
            )
        else:
            self._file_cache.put(key, [scanned_file])
            logger.debug(
                "Added file to cache: %s (title: %s, episode: %d)",
                scanned_file.file_path.name,
                title,
                episode,
            )

    def _raise_add_file_error(self, scanned_file: ScannedFile, e: Exception) -> None:
        """Map exception to AniVault error, log and re-raise. Never returns."""
        file_path_str = _file_path_str(scanned_file)
        context = ErrorContext(file_path=file_path_str, operation="add_file_to_cache")
        logger.exception("Failed to add file to cache: %s", file_path_str)

        if isinstance(e, FileNotFoundError):
            raise AniVaultFileError(
                ErrorCode.FILE_NOT_FOUND,
                f"File not found while adding to cache: {file_path_str}",
                context,
                original_error=e,
            ) from e
        if isinstance(e, PermissionError):
            raise AniVaultPermissionError(
                ErrorCode.PERMISSION_DENIED,
                f"Permission denied accessing file: {file_path_str}",
                context,
                original_error=e,
            ) from e
        if isinstance(e, OSError):
            raise AniVaultFileError(
                ErrorCode.FILE_ACCESS_ERROR,
                f"File system error while adding to cache: {file_path_str}",
                context,
                original_error=e,
            ) from e
        raise AniVaultError(
            ErrorCode.FILE_GROUPING_FAILED,
            f"Unexpected error while adding file to cache: {file_path_str}",
            context,
            original_error=e,
        ) from e

    def get_file(self, title: str, episode: int) -> ScannedFile | None:
        """
        Get a file from the cache by title and episode.

        Args:
            title: The title of the anime.
            episode: The episode number.

        Returns:
            The first ScannedFile matching the title and episode, or None if not found.
        """
        key = (title, episode)
        files = self._file_cache.get(key)
        return files[0] if files else None

    def find_duplicates(self) -> list[list[ScannedFile]]:
        """
        Find all duplicate files in the cache.

        Returns:
            A list of lists, where each inner list contains ScannedFile objects
            that are considered duplicates of each other.
        """
        duplicate_groups = []
        for _key, files in self._file_cache:
            if files and len(files) > 1:
                duplicate_groups.append(files)
        return duplicate_groups

    def _operations_for_duplicate_group(self, duplicate_group: list[ScannedFile]) -> list[FileOperation]:
        """Build move operations for one duplicate group (best file + duplicates)."""
        best_file = self._select_best_file(duplicate_group)
        ops: list[FileOperation] = [
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=best_file.file_path,
                destination_path=self._build_organization_path(best_file),
            )
        ]
        for file in duplicate_group:
            if file != best_file:
                ops.append(
                    FileOperation(
                        operation_type=OperationType.MOVE,
                        source_path=file.file_path,
                        destination_path=self._build_duplicate_path(file),
                    )
                )
        return ops

    def _operations_for_non_duplicates(
        self,
        cache_entries: list[tuple[tuple[str, int], list[ScannedFile]]],
        processed_paths: set[Path],
    ) -> list[FileOperation]:
        """Build move operations for files not in any duplicate group."""
        ops: list[FileOperation] = []
        for _key, files in cache_entries:
            for file in files:
                if file.file_path not in processed_paths:
                    ops.append(
                        FileOperation(
                            operation_type=OperationType.MOVE,
                            source_path=file.file_path,
                            destination_path=self._build_organization_path(file),
                        )
                    )
        return ops

    def generate_plan(self, scanned_files: list[ScannedFile]) -> list[FileOperation]:
        """
        Generate a file organization plan based on scanned files.

        Args:
            scanned_files: List of ScannedFile objects to organize.

        Returns:
            List of FileOperation objects representing the organization plan.
        """
        if not scanned_files:
            return []

        self._file_cache = LinkedHashTable[tuple[str, int], list[ScannedFile]](
            initial_capacity=max(len(scanned_files) * 2, 64),
            load_factor=0.75,
        )
        for scanned_file in scanned_files:
            self.add_file(scanned_file)

        duplicate_groups: list[list[ScannedFile]] = []
        cache_entries: list[tuple[tuple[str, int], list[ScannedFile]]] = []
        for key, files in self._file_cache:
            cache_entries.append((key, files))
            if files and len(files) > 1:
                duplicate_groups.append(files)

        operations: list[FileOperation] = []
        for duplicate_group in duplicate_groups:
            operations.extend(self._operations_for_duplicate_group(duplicate_group))

        processed_paths = {f.file_path for group in duplicate_groups for f in group}
        operations.extend(self._operations_for_non_duplicates(cache_entries, processed_paths))
        return operations

    def organize(self, scanned_files: list[ScannedFile], dry_run: bool = True) -> list[FileOperation] | list[OperationResult]:
        """
        Organize files based on the generated plan.

        Args:
            scanned_files: List of ScannedFile objects to organize.
            dry_run: If True, returns FileOperation objects without executing.
                    If False, executes operations and returns OperationResult objects.

        Returns:
            List of FileOperation objects
            (if dry_run=True) or OperationResult objects (if dry_run=False).
        """
        plan = self.generate_plan(scanned_files)

        if dry_run:
            return plan
        return self._executor.execute_batch(plan)

    def _select_best_file(self, files: list[ScannedFile]) -> ScannedFile:
        """
        Select the best file from a list of duplicates based on quality.

        Args:
            files: List of ScannedFile objects to choose from.

        Returns:
            The ScannedFile with the highest quality score.

        Raises:
            ValueError: If files list is empty.
        """
        if not files:
            raise ValueError("Cannot select from empty file list")

        best_file = files[0]
        best_score = self._extract_quality_score(best_file)

        for file in files[1:]:
            score = self._extract_quality_score(file)
            if score > best_score:
                best_file = file
                best_score = score

        return best_file

    def _extract_quality_score(self, file: ScannedFile) -> int:
        """
        Extract quality score from a ScannedFile.

        Args:
            file: The ScannedFile to extract quality from.

        Returns:
            Quality score as integer (higher is better).
        """
        if not file.metadata or not hasattr(file.metadata, "quality"):
            return 0

        quality = file.metadata.quality or ""
        quality_lower = quality.lower()

        # Quality scoring (higher is better)
        if "1080p" in quality_lower or "fhd" in quality_lower:
            return 1080
        if "720p" in quality_lower or "hd" in quality_lower:
            return 720
        if "480p" in quality_lower or "sd" in quality_lower:
            return 480
        if "360p" in quality_lower:
            return 360
        return 0

    def _build_duplicate_path(self, file: ScannedFile) -> Path:
        """
        Build path for duplicate file storage.

        Args:
            file: The ScannedFile to build path for.

        Returns:
            Path object for the duplicate file.
        """
        if not file.metadata:
            return Path.home() / "duplicates" / file.file_path.name

        title = file.metadata.title or "Unknown"
        episode = file.metadata.episode or 0
        quality = file.metadata.quality or "unknown"

        # Create title directory with underscores
        title_dir = title.replace(" ", "_")

        # Build duplicate path
        duplicate_path = Path.home() / "duplicates" / title_dir / f"E{episode:02d}_{quality}_{file.file_path.name}"

        return duplicate_path

    def _build_organization_path(self, file: ScannedFile) -> Path:
        """
        Build path for organized file storage.

        Args:
            file: The ScannedFile to build path for.

        Returns:
            Path object for the organized file.
        """
        if not file.metadata:
            return Path.home() / "organized" / file.file_path.name

        title = file.metadata.title or "Unknown"
        episode = file.metadata.episode or 0
        quality = file.metadata.quality or "unknown"

        # Create title directory
        title_dir = title.replace(" ", "_")

        # Build organization path
        organized_path = Path.home() / "organized" / title_dir / f"E{episode:02d}_{quality}_{file.file_path.name}"

        return organized_path

    @property
    def file_count(self) -> int:
        """
        Get the total number of files in the cache.

        Returns:
            Total number of files across all keys.
        """
        total_files = 0
        for _key, files in self._file_cache:
            if files:
                total_files += len(files)
        return total_files

    def clear_cache(self) -> None:
        """Clear all files from the cache."""
        self._file_cache = LinkedHashTable[tuple[str, int], list[ScannedFile]](
            initial_capacity=1024,
            load_factor=0.75,
        )
        logger.debug("File cache cleared")
