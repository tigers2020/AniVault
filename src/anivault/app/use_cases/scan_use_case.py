"""Scan use case (Phase 5).

Orchestrates scan pipeline: run pipeline on directory and return FileMetadata list.
Shared by CLI scan handler and GUI scan worker.
"""

from __future__ import annotations

from pathlib import Path

from anivault.core.pipeline import run_pipeline
from anivault.shared.constants import QueueConfig
from anivault.shared.constants.file_formats import VideoFormats
from anivault.shared.models.metadata import FileMetadata


class ScanUseCase:
    """Use case for scanning anime files in a directory."""

    def execute(
        self,
        directory: str | Path,
        extensions: list[str] | None = None,
        num_workers: int | None = None,
        max_queue_size: int | None = None,
    ) -> list[FileMetadata]:
        """Scan directory for anime files and return parsed metadata.

        Args:
            directory: Root directory to scan
            extensions: File extensions to include (default: VideoFormats.ALL_EXTENSIONS)
            num_workers: Worker count (default: from QueueConfig/CLI)
            max_queue_size: Queue size (default: QueueConfig.DEFAULT_SIZE)

        Returns:
            List of FileMetadata instances
        """
        exts = extensions or list(VideoFormats.ALL_EXTENSIONS)
        kwargs: dict = {
            "root_path": str(directory),
            "extensions": exts,
            "max_queue_size": max_queue_size or QueueConfig.DEFAULT_SIZE,
        }
        if num_workers is not None:
            kwargs["num_workers"] = num_workers
        return run_pipeline(**kwargs)
