"""Base worker for GUI v2 operations."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from anivault.gui_v2.models import OperationError, OperationProgress

logger = logging.getLogger(__name__)


class BaseWorker(QObject):
    """Base worker for long-running tasks."""

    progress = Signal(OperationProgress)
    finished = Signal(object)
    error = Signal(OperationError)

    def __init__(self) -> None:
        super().__init__()
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation."""
        self._cancelled = True
        logger.info("Worker cancellation requested")

    def is_cancelled(self) -> bool:
        """Return True if cancellation requested."""
        return self._cancelled

    @Slot()
    def run(self) -> None:
        """Run the worker task."""
        raise NotImplementedError

    def _emit_error(self, error: OperationError) -> None:
        """Emit an error signal."""
        self.error.emit(error)
