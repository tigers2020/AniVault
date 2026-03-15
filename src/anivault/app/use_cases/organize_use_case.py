"""Organize use case (Phase 5).

Orchestrates organization pipeline: scan → generate plan → execute plan.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from anivault.config import Settings
from anivault.core.models import FileOperation, ScannedFile
from anivault.core.organizer.organize_service import (
    execute_organization_plan as core_execute_plan,
)
from anivault.core.organizer.organize_service import (
    generate_enhanced_organization_plan as core_generate_enhanced_plan,
)
from anivault.core.organizer.executor import OperationResult
from anivault.core.organizer.organize_service import (
    generate_organization_plan as core_generate_plan,
)
from anivault.core.pipeline import run_pipeline
from anivault.shared.constants import QueueConfig, WorkerConfig
from anivault.shared.models.metadata import FileMetadata
from anivault.shared.utils.metadata_converter import MetadataConverter


class OrganizeUseCase:
    """Use case for organizing anime files into structured directories."""

    def _scanned_file_from_metadata(self, metadata: FileMetadata) -> ScannedFile:
        """Convert a single FileMetadata to ScannedFile (single source for organize conversion)."""
        parsing_result = MetadataConverter.file_metadata_to_parsing_result(metadata)
        return ScannedFile(
            file_path=metadata.file_path,
            metadata=parsing_result,
        )

    def _scanned_files_from_metadata(
        self, files: Sequence[FileMetadata]
    ) -> list[ScannedFile]:
        """Convert FileMetadata list to ScannedFile list (single source for organize conversion)."""
        return [self._scanned_file_from_metadata(m) for m in files]

    def scan(
        self,
        root_path: str | Path,
        extensions: list[str],
        num_workers: int | None = None,
        max_queue_size: int | None = None,
    ) -> list[ScannedFile]:
        """Scan directory and return ScannedFile list.

        Args:
            root_path: Directory to scan
            extensions: File extensions to include
            num_workers: Worker count (default: WorkerConfig.DEFAULT)
            max_queue_size: Queue size (default: QueueConfig.DEFAULT_SIZE)

        Returns:
            List of ScannedFile instances
        """
        file_results: list[FileMetadata] = run_pipeline(
            root_path=str(root_path),
            extensions=extensions,
            num_workers=num_workers or WorkerConfig.DEFAULT,
            max_queue_size=max_queue_size or QueueConfig.DEFAULT_SIZE,
        )
        return self._scanned_files_from_metadata(file_results)

    def generate_plan(
        self,
        scanned_files: list[ScannedFile],
        *,
        settings: Settings | None = None,
    ) -> list[FileOperation]:
        """Generate organization plan.

        Args:
            scanned_files: List of scanned files
            settings: Optional settings override

        Returns:
            List of FileOperation
        """
        return core_generate_plan(scanned_files, settings=settings)

    def generate_enhanced_plan(
        self,
        scanned_files: list[ScannedFile],
        destination: str = "Anime",
    ) -> list[FileOperation]:
        """Generate enhanced organization plan with grouping.

        Args:
            scanned_files: List of scanned files
            destination: Base destination directory name

        Returns:
            List of FileOperation
        """
        return core_generate_enhanced_plan(scanned_files, destination=destination)

    def generate_plan_from_metadata(
        self,
        files: list[FileMetadata],
        settings: Settings | None = None,
    ) -> list[FileOperation]:
        """Generate organization plan from FileMetadata list.

        Args:
            files: List of FileMetadata (e.g. from scan/match results).
            settings: Optional settings override.

        Returns:
            List of FileOperation.
        """
        scanned = self._scanned_files_from_metadata(files)
        return self.generate_plan(scanned, settings=settings)

    def generate_enhanced_plan_from_metadata(
        self,
        files: list[FileMetadata],
        destination: str = "Anime",
    ) -> list[FileOperation]:
        """Generate enhanced organization plan from FileMetadata list.

        Args:
            files: List of FileMetadata (e.g. from scan/match results).
            destination: Base destination directory name.

        Returns:
            List of FileOperation.
        """
        scanned = self._scanned_files_from_metadata(files)
        return self.generate_enhanced_plan(scanned, destination=destination)

    def execute_plan(
        self,
        plan: list[FileOperation],
        source_directory: Path,
        *,
        settings: Settings | None = None,
    ) -> list[OperationResult]:
        """Execute organization plan.

        Args:
            plan: Organization plan
            source_directory: Source directory path
            settings: Optional settings override

        Returns:
            List of move results (from core_execute_plan)
        """
        return core_execute_plan(
            plan,
            source_directory,
            settings=settings,
        )

    def save_plan_log(
        self,
        plan: list[FileOperation],
        base_path: Path | None = None,
    ) -> str | None:
        """Persist the operation plan to a log file.

        R5: Moved from cli/organize_handler so the handler layer never imports
        OperationLogManager (anivault.core) directly.

        Args:
            plan:      Organization plan to save.
            base_path: Directory for the log file (defaults to CWD).

        Returns:
            Absolute path of the saved log file as a string, or None on error.
        """
        from anivault.core.log_manager import OperationLogManager

        try:
            log_manager = OperationLogManager(base_path or Path.cwd())
            saved = log_manager.save_plan(plan)
            return str(saved)
        except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            return None
