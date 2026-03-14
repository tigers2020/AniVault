"""Scan use case (Phase 5).

Orchestrates scan pipeline: run pipeline on directory and return FileMetadata list.
Shared by CLI scan handler and GUI scan worker.
"""

from __future__ import annotations

import multiprocessing
from collections.abc import Callable
from pathlib import Path

from anivault.core.pipeline import run_pipeline
from anivault.shared.constants import QueueConfig
from anivault.shared.constants.core import ProcessingConfig
from anivault.shared.constants.file_formats import VideoFormats
from anivault.shared.models.metadata import FileMetadata


def run_scan_in_process(
    root_path: str,
    extensions: list[str],
    queue: multiprocessing.Queue,
) -> None:
    """Run scan in a subprocess and put progress/result into queue (picklable entry point).

    Sends: ("started", None), ("progress", {...}), ("result", list), ("error", str), ("done", None).
    """
    import traceback

    try:
        queue.put(("started", None))
    except Exception:  # noqa: S110  # queue may be broken in child
        pass
    try:
        use_case = ScanUseCase()
        def progress_cb(n: int) -> None:
            queue.put(("progress", {"current": n, "total": 0, "message": f"스캔 중... {n}개 파일"}))
        results = use_case.execute(root_path, extensions=extensions, progress_callback=progress_cb)
        queue.put(("result", results))
    except Exception:
        queue.put(("error", traceback.format_exc()))
    finally:
        try:
            queue.put(("done", None))
        except Exception:  # noqa: S110
            pass


class ScanUseCase:
    """Use case for scanning anime files in a directory."""

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
