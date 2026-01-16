"""Base controller for GUI v2 operations."""

from __future__ import annotations

import logging
from typing import Any, Callable

from PySide6.QtCore import QObject, QThread, Signal

from anivault.gui_v2.app_context import AppContext
from anivault.gui_v2.models import OperationError, OperationProgress

logger = logging.getLogger(__name__)


class BaseController(QObject):
    """Base controller for long-running operations."""

    operation_started = Signal()
    operation_progress = Signal(OperationProgress)
    operation_finished = Signal(object)
    operation_error = Signal(OperationError)

    def __init__(self, app_context: AppContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.app_context = app_context
        self._thread: QThread | None = None
        self._worker: QObject | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Return True if an operation is currently running."""
        return self._running

    def cancel(self) -> None:
        """Cancel the current operation if possible."""
        if self._worker and hasattr(self._worker, "cancel"):
            logger.info("Cancelling current operation")
            cancel_method: Callable[[], None] = getattr(self._worker, "cancel")
            cancel_method()

    def _start_worker(self, worker: QObject) -> None:
        """Start a worker in a new thread and connect common signals."""
        if self._running:
            logger.warning("Operation already running, ignoring new request")
            return

        self._worker = worker
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)  # type: ignore[attr-defined]
        self._connect_worker_signals()
        self._thread.finished.connect(self._thread.deleteLater)

        self._running = True
        self.operation_started.emit()
        self._thread.start()

    def _connect_worker_signals(self) -> None:
        """Connect worker signals to controller signals."""
        if not self._worker or not self._thread:
            return

        if hasattr(self._worker, "progress"):
            self._worker.progress.connect(self.operation_progress)  # type: ignore[attr-defined]
        if hasattr(self._worker, "finished"):
            self._worker.finished.connect(self._on_worker_finished)  # type: ignore[attr-defined]
        if hasattr(self._worker, "error"):
            self._worker.error.connect(self._on_worker_error)  # type: ignore[attr-defined]

    def _on_worker_finished(self, result: Any) -> None:
        """Handle worker completion."""
        self._running = False
        self.operation_finished.emit(result)
        self._cleanup_worker()

    def _on_worker_error(self, error: Any) -> None:
        """Handle worker error."""
        self._running = False
        self.operation_error.emit(error)
        self._cleanup_worker()

    def _cleanup_worker(self) -> None:
        """Clean up worker and thread resources."""
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
