"""Scan use case (Phase 5, R5 update).

Orchestrates scan pipeline: run pipeline on directory and return FileMetadata list.
Shared by CLI scan handler and GUI scan worker.

R5: MetadataEnricher integration moved here from cli/scan_handler so that the
handler layer never imports from anivault.core or anivault.services directly.
"""

from __future__ import annotations

import multiprocessing
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.core.pipeline import run_pipeline
from anivault.shared.constants import QueueConfig
from anivault.shared.constants.core import ProcessingConfig
from anivault.shared.constants.file_formats import VideoFormats
from anivault.shared.constants.scan_messages import ScanQueueMessageKind
from anivault.shared.models.metadata import FileMetadata

if TYPE_CHECKING:
    from anivault.services.enricher import MetadataEnricher


def run_scan_in_process(
    root_path: str,
    extensions: list[str],
    queue: multiprocessing.Queue,
) -> None:
    """Run scan in a subprocess and put progress/result into queue (picklable entry point).

    Sends: (ScanQueueMessageKind.STARTED, None), (PROGRESS, {...}), (RESULT, list), (ERROR, str), (DONE, None).

    Logging: subprocess configures logging to logs/scan.log so pipeline/scanner messages
    (e.g. directory cache hits/misses) are visible there when using GUI.
    """
    import logging
    import traceback

    from anivault.shared.logging import configure_logging
    from anivault.utils.resource_path import get_project_root

    log_dir = get_project_root() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(
        level=logging.INFO,
        log_dir=str(log_dir),
        log_file="scan.log",
        enable_file=True,
        enable_console=False,
    )

    try:
        queue.put((ScanQueueMessageKind.STARTED, None))
    except Exception:  # queue may be broken in child  # noqa: BLE001
        pass
    try:
        use_case = ScanUseCase()

        def progress_cb(n: int) -> None:
            queue.put((ScanQueueMessageKind.PROGRESS, {"current": n, "total": 0, "message": f"스캔 중... {n}개 파일"}))

        results = use_case.execute(root_path, extensions=extensions, progress_callback=progress_cb)
        queue.put((ScanQueueMessageKind.RESULT, results))
    except Exception:  # noqa: BLE001
        queue.put((ScanQueueMessageKind.ERROR, traceback.format_exc()))
    finally:
        try:
            queue.put((ScanQueueMessageKind.DONE, None))
        except Exception:  # noqa: BLE001
            pass


class ScanUseCase:
    """Use case for scanning anime files in a directory.

    Args:
        enricher: Optional MetadataEnricher for TMDB enrichment after scanning.
                  When None, enrich_one() is a no-op that returns the input as-is.
    """

    def __init__(self, enricher: MetadataEnricher | None = None) -> None:
        self._enricher = enricher

    # ------------------------------------------------------------------
    # Enrichment helpers (R5: moved from cli/scan_handler)
    # ------------------------------------------------------------------

    def _file_metadata_to_parsing_result(self, metadata: FileMetadata) -> ParsingResult:
        """Convert FileMetadata to ParsingResult for TMDB enrichment."""
        return ParsingResult(
            title=metadata.title,
            episode=metadata.episode,
            season=metadata.season,
            year=metadata.year,
            quality=None,
            source=None,
            codec=None,
            audio=None,
            release_group=None,
            confidence=1.0,
            parser_used="file_metadata_converter",
            additional_info=ParsingAdditionalInfo(),
        )

    async def enrich_one(self, metadata: FileMetadata) -> FileMetadata:
        """Enrich a single FileMetadata with TMDB data.

        Returns the original FileMetadata unchanged when no enricher is configured.

        Args:
            metadata: FileMetadata to enrich.

        Returns:
            Enriched FileMetadata, or original when enricher is absent.
        """
        if self._enricher is None:
            return metadata
        parsing_result = self._file_metadata_to_parsing_result(metadata)
        enriched = await self._enricher.enrich_metadata(parsing_result)
        return enriched.to_file_metadata(metadata.file_path)

    def execute(
        self,
        directory: str | Path,
        extensions: list[str] | None = None,
        num_workers: int | None = None,
        max_queue_size: int | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> list[FileMetadata]:
        """Scan directory for anime files and return parsed metadata.

        Args:
            directory: Root directory to scan
            extensions: File extensions to include (default: VideoFormats.ALL_EXTENSIONS)
            num_workers: Worker count (default: from QueueConfig/CLI)
            max_queue_size: Queue size (default: QueueConfig.DEFAULT_SIZE)
            progress_callback: Optional callback with current files_scanned count (from scanner thread)

        Returns:
            List of FileMetadata instances
        """
        exts = extensions or list(VideoFormats.ALL_EXTENSIONS)
        pipeline_progress: Callable[[dict], None] | None = None
        if progress_callback is not None:

            def pipeline_progress(payload: dict) -> None:
                progress_callback(payload.get("files_scanned", 0))

        return run_pipeline(
            root_path=str(directory),
            extensions=exts,
            num_workers=(num_workers if num_workers is not None else ProcessingConfig.MAX_PROCESSING_WORKERS),
            max_queue_size=max_queue_size or QueueConfig.DEFAULT_SIZE,
            progress_callback=pipeline_progress,
        )
