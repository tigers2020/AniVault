"""Organize use case (Phase 5).

Orchestrates organization pipeline: scan → generate plan → execute plan.
"""

from __future__ import annotations

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

        scanned_files: list[ScannedFile] = []
        for metadata in file_results:
            parsing_result = MetadataConverter.file_metadata_to_parsing_result(metadata)
            scanned_file = ScannedFile(
                file_path=metadata.file_path,
                metadata=parsing_result,
            )
            scanned_files.append(scanned_file)

        return scanned_files

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
