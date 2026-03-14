"""Scan worker for GUI v2."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from anivault.app.use_cases.scan_use_case import ScanUseCase
from anivault.gui_v2.models import OperationError, OperationProgress
from anivault.gui_v2.workers.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class ScanWorker(BaseWorker):
    """Worker that runs the scan pipeline.

    Scan progress is reported from the pipeline's scanner (a threading.Thread),
    so progress is stored thread-safely and the main thread polls via
    get_latest_progress() to avoid signals queued to a blocked QThread.
    """

    def __init__(self, root_path: Path, extensions: list[str]) -> None:
        super().__init__()
        self._root_path = root_path
        self._extensions = extensions
        self._progress_lock = threading.Lock()
        self._latest_progress: OperationProgress | None = None
        self._progress_flusher: object | None = None
        self._last_flush_time: float = 0.0
        self._flush_interval_sec: float = 0.15

    def set_progress_flusher(self, flusher: object) -> None:
        """Set the QObject that has flush_worker_progress() slot (main thread)."""
        self._progress_flusher = flusher

    def get_latest_progress(self) -> OperationProgress | None:
        """Return and clear the latest progress (called from main thread)."""
        with self._progress_lock:
            p = self._latest_progress
            self._latest_progress = None
            return p

    def run(self) -> None:
        """Run the scan pipeline in a separate thread so this QThread is not blocked.

        Progress and finished are emitted from the pipeline thread; Qt queues them
        to the main thread, so the UI can update while the pipeline runs.
        """
        if self.is_cancelled():
            self.finished.emit([])
            return

        self.progress.emit(
            OperationProgress(
                current=0,
                total=0,
                stage="scanning",
                message="스캔 시작",
            )
        )

        def on_scan_progress(files_scanned: int) -> None:
            with self._progress_lock:
                self._latest_progress = OperationProgress(
                    current=files_scanned,
                    total=0,
                    stage="scanning",
                    message=f"스캔 중... {files_scanned}개 파일",
                )
            if self._progress_flusher is None or not hasattr(self._progress_flusher, "flush_requested"):
                return
            now = time.monotonic()
            if files_scanned == 1 or (now - self._last_flush_time) >= self._flush_interval_sec:
                self._last_flush_time = now
                self._progress_flusher.flush_requested.emit()
                # Yield GIL so main thread can process events and repaint
                time.sleep(0)

        def run_pipeline_in_thread() -> None:
            try:
                logger.info("Starting pipeline scan: root_path=%s, extensions=%s", self._root_path, self._extensions)
                scan_use_case = ScanUseCase()
                results = scan_use_case.execute(
                    self._root_path,
                    extensions=self._extensions,
                    progress_callback=on_scan_progress,
                )
                logger.info("Pipeline returned %d results", len(results))
                metadata_list = results
                self.progress.emit(
                    OperationProgress(
                        current=len(metadata_list),
                        total=len(metadata_list),
                        stage="scanning",
                        message="스캔 완료",
                    )
                )
                self.finished.emit(metadata_list)
                logger.info("Emitted finished signal with %d FileMetadata objects", len(metadata_list))
            except Exception as exc:
                logger.exception("Scan pipeline failed")
                self._emit_error(
                    OperationError(
                        code="SCAN_FAILED",
                        message="스캔 중 오류가 발생했습니다.",
                        detail=str(exc),
                    )
                )

        pipeline_thread = threading.Thread(target=run_pipeline_in_thread, daemon=True)
        pipeline_thread.start()
