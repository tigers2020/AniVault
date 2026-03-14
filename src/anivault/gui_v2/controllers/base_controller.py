"""Base controller for GUI v2 operations."""

from __future__ import annotations

import logging
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from anivault.gui_v2.app_context import AppContext
from anivault.gui_v2.models import OperationError, OperationProgress

logger = logging.getLogger(__name__)


class BaseController(QObject):
    """Base controller for long-running operations."""

    operation_started = Signal()
    operation_progress = Signal(OperationProgress)
    operation_finished = Signal(object)
    operation_error = Signal(OperationError)
    flush_requested = Signal()

    def __init__(self, app_context: AppContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.app_context = app_context
        self._thread: QThread | None = None
        self._worker: QObject | None = None
        self._running = False
        self._progress_poll_interval_ms = 100
        self._progress_poll_timer: QTimer | None = None
        self.flush_requested.connect(self.flush_worker_progress)

    @property
    def is_running(self) -> bool:
        """Return True if an operation is currently running."""
        return self._running

    def cancel(self) -> None:
        """Cancel the current operation if possible."""
        if self._worker and hasattr(self._worker, "cancel"):
            logger.info("Cancelling current operation")
            cancel_method: Callable[[], None] = self._worker.cancel
            cancel_method()

    def _start_worker(self, worker: QObject) -> None:
        """Start a worker in a new thread and connect common signals."""
        if self._running:
            logger.warning("Operation already running, ignoring new request")
            return

        self._worker = worker
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        run_slot = getattr(self._worker, "run")  # noqa: B009
        self._thread.started.connect(run_slot)
        self._connect_worker_signals()
        self._thread.finished.connect(self._thread.deleteLater)

        self._running = True
        self.operation_started.emit()
        self._thread.start()

        if hasattr(self._worker, "set_progress_flusher"):
            self._worker.set_progress_flusher(self)
        if hasattr(self._worker, "get_latest_progress"):
            self._progress_poll_timer = QTimer(self)
            self._progress_poll_timer.setInterval(self._progress_poll_interval_ms)
            self._progress_poll_timer.setSingleShot(False)
            self._progress_poll_timer.timeout.connect(self._poll_worker_progress)
            self._progress_poll_timer.start()

    def _poll_worker_progress(self) -> None:
        """Poll worker for progress (timer or flusher)."""
        if not self._running or not self._worker:
            return
        get_latest = getattr(self._worker, "get_latest_progress", None)
        if callable(get_latest):
            progress = get_latest()
            if progress is not None:
                self.operation_progress.emit(progress)

    @Slot()
    def flush_worker_progress(self) -> None:
        """Slot: read latest progress from worker and emit (called from main thread via flush_requested.emit())."""
        if not self._running or not self._worker:
            return
        get_latest = getattr(self._worker, "get_latest_progress", None)
        if callable(get_latest):
            progress = get_latest()
            if progress is not None:
                self.operation_progress.emit(progress)

    def _connect_worker_signals(self) -> None:
        """Connect worker signals to controller signals."""
        if not self._worker or not self._thread:
            return

        if hasattr(self._worker, "progress"):
            self._worker.progress.connect(self.operation_progress)
        if hasattr(self._worker, "finished"):
            self._worker.finished.connect(self._on_worker_finished)
        if hasattr(self._worker, "error"):
            self._worker.error.connect(self._on_worker_error)

    def _on_worker_finished(self, result: Any) -> None:
        """Handle worker completion."""
        self._running = False
        self._stop_progress_poll_timer()
        self.operation_finished.emit(result)
        self._cleanup_worker()

    def _on_worker_error(self, error: Any) -> None:
        """Handle worker error."""
        self._running = False
        self._stop_progress_poll_timer()
        self.operation_error.emit(error)
        self._cleanup_worker()

    def _stop_progress_poll_timer(self) -> None:
        """Stop and clear the progress poll timer."""
        if self._progress_poll_timer is not None:
            self._progress_poll_timer.stop()
            self._progress_poll_timer = None

    def _cleanup_worker(self) -> None:
        """Clean up worker and thread resources."""
        self._stop_progress_poll_timer()
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
