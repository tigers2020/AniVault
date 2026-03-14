"""Scan controller for GUI v2."""

from __future__ import annotations

import logging
import multiprocessing
from pathlib import Path
from queue import Empty

from PySide6.QtCore import QTimer

from anivault.app.use_cases.scan_use_case import run_scan_in_process
from anivault.gui_v2.app_context import AppContext
from anivault.gui_v2.controllers.base_controller import BaseController
from anivault.gui_v2.models import OperationError, OperationProgress
from anivault.shared.constants.file_formats import SubtitleFormats, VideoFormats
from anivault.shared.constants.gui_constants import ScanQueueMessageKind

logger = logging.getLogger(__name__)

_SCAN_POLL_INTERVAL_MS = 80


class ScanController(BaseController):
    """Controller for running directory scans.

    Uses a separate process for scanning so the GUI thread is never blocked by GIL or
    pipeline work; progress is read from a queue on a timer.
    """

    def __init__(self, app_context: AppContext) -> None:
        super().__init__(app_context)
        self._scan_process: multiprocessing.Process | None = None
        self._scan_queue: multiprocessing.Queue | None = None
        self._scan_poll_timer: QTimer | None = None
        self._scan_running = False

    def scan_directory(self, directory: Path) -> None:
        """Start scanning a directory."""
        if not directory.exists() or not directory.is_dir():
            self.operation_error.emit(
                OperationError(
                    code="INVALID_PATH",
                    message="유효하지 않은 디렉터리입니다.",
                    detail=str(directory),
                )
            )
            return
        self._start_scan_process(directory, list(VideoFormats.ALL_EXTENSIONS))

    def cancel(self) -> None:
        """Cancel the current scan process if running."""
        if self._scan_running and self._scan_process is not None:
            logger.info("Cancelling scan process")
            self._scan_process.terminate()
            self._stop_scan_process()
            self.operation_finished.emit([])
        else:
            super().cancel()

    def cleanup(self) -> None:
        """Stop scan process if running. Call on app/window shutdown so the child process does not outlive the app."""
        if self._scan_process is not None or self._scan_running:
            self._stop_scan_process()

    def scan_subtitle_directory(self, directory: Path) -> None:
        """Start scanning a directory for subtitle files only."""
        if not directory.exists() or not directory.is_dir():
            self.operation_error.emit(
                OperationError(
                    code="INVALID_PATH",
                    message="유효하지 않은 디렉터리입니다.",
                    detail=str(directory),
                )
            )
            return
        self._start_scan_process(directory, list(SubtitleFormats.EXTENSIONS))

    def _start_scan_process(self, directory: Path, extensions: list[str]) -> None:
        """Run scan in a subprocess and poll queue on main thread."""
        if self._scan_running:
            logger.warning("Scan already running, ignoring")
            return
        ctx = multiprocessing.get_context("spawn")
        self._scan_queue = ctx.Queue()
        self._scan_process = ctx.Process(
            target=run_scan_in_process,
            args=(str(directory), extensions, self._scan_queue),
        )
        self._scan_process.start()
        self._scan_running = True
        self._running = True
        self.operation_started.emit()
        self.operation_progress.emit(
            OperationProgress(current=0, total=0, stage="scanning", message="스캔 시작")
        )
        self._scan_poll_timer = QTimer(self)
        self._scan_poll_timer.setInterval(_SCAN_POLL_INTERVAL_MS)
        self._scan_poll_timer.timeout.connect(self._poll_scan_queue)
        self._scan_poll_timer.start()

    def _poll_scan_queue(self) -> None:
        """Drain scan queue and emit progress/finished/error (runs on main thread)."""
        if self._scan_queue is None or self._scan_process is None:
            return
        while True:
            try:
                msg = self._scan_queue.get_nowait()
            except Empty:
                break
            kind, payload = msg
            if kind == ScanQueueMessageKind.STARTED:
                continue  # process ready, wait for progress/result
            elif kind == ScanQueueMessageKind.PROGRESS:
                self.operation_progress.emit(
                    OperationProgress(
                        current=payload["current"],
                        total=payload.get("total", 0),
                        stage="scanning",
                        message=payload.get("message"),
                    )
                )
            elif kind == ScanQueueMessageKind.RESULT:
                self._stop_scan_process()
                self.operation_finished.emit(payload)
                return
            elif kind == ScanQueueMessageKind.ERROR:
                self._stop_scan_process()
                self.operation_error.emit(
                    OperationError(code="SCAN_FAILED", message="스캔 중 오류가 발생했습니다.", detail=payload)
                )
                return
            elif kind == ScanQueueMessageKind.DONE:
                self._stop_scan_process()
                return

        if not self._scan_process.is_alive() and self._scan_queue is not None:
            try:
                self._scan_queue.get_nowait()
            except Empty:
                self._stop_scan_process()
                self.operation_error.emit(
                    OperationError(
                        code="SCAN_FAILED",
                        message="스캔 프로세스가 예기치 않게 종료되었습니다.",
                        detail="",
                    )
                )

    def _stop_scan_process(self) -> None:
        """Stop poll timer and join process."""
        if self._scan_poll_timer is not None:
            self._scan_poll_timer.stop()
            self._scan_poll_timer = None
        if self._scan_process is not None:
            self._scan_process.join(timeout=5.0)
            if self._scan_process.is_alive():
                self._scan_process.terminate()
                self._scan_process.join(timeout=2.0)
            self._scan_process = None
        self._scan_queue = None
        self._scan_running = False
        self._running = False
