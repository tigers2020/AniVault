"""Thread management utilities for GUI controllers.

This module provides common utilities for managing QThread and Worker instances
across GUI controllers, reducing code duplication and ensuring consistent patterns.

Design Principles:
- Consistent thread lifecycle management
- Proper cleanup and resource management
- Type-safe worker and thread handling
- Support for multiple controller patterns
"""

from __future__ import annotations

import logging
from typing import Any, Generic, TypeVar

from PySide6.QtCore import QObject, QThread

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=QObject)  # Worker type


class ThreadManager(Generic[T]):
    """Manages QThread and Worker lifecycle for GUI controllers.

    This class provides a consistent interface for creating, managing,
    and cleaning up worker threads across different controllers.

    Example:
        >>> manager = ThreadManager(worker_class=OrganizeWorker)
        >>> manager.start_worker(worker_args, signal_connections)
        >>> # ... later ...
        >>> manager.cleanup()
    """

    def __init__(self, worker_class: type[T]) -> None:
        """Initialize thread manager.

        Args:
            worker_class: Worker class to manage
        """
        self.worker_class = worker_class
        self.thread: QThread | None = None
        self.worker: T | None = None

    def start_worker(
        self,
        worker_args: tuple[Any, ...] | None = None,  # pylint: disable=unused-argument
        worker_kwargs: dict[str, Any] | None = None,
        signal_connections: dict[str, Any] | None = None,
    ) -> T:
        """Start worker in a new thread.

        Args:
            worker_args: Positional arguments for worker constructor
            worker_kwargs: Keyword arguments for worker constructor
            signal_connections: Dictionary mapping signal names to handlers

        Returns:
            Worker instance
        """
        self.cleanup()

        self.thread = QThread()
        worker_kwargs = worker_kwargs or {}
        self.worker = self.worker_class(**worker_kwargs)
        self.worker.moveToThread(self.thread)

        if signal_connections:
            for signal_name, handler in signal_connections.items():
                signal = getattr(self.worker, signal_name, None)
                if signal:
                    signal.connect(handler)

        self.thread.started.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.worker.deleteLater)

        self.thread.start()
        logger.debug("Started %s in thread", self.worker_class.__name__)

        return self.worker

    def cleanup(self) -> None:
        """Clean up existing thread and worker."""
        if self.thread and self.thread.isRunning():
            logger.debug("Cleaning up running thread")
            if self.worker and hasattr(self.worker, "cancel"):
                self.worker.cancel()
            self.thread.wait(5000)
        self.thread = None
        self.worker = None

    def is_running(self) -> bool:
        """Check if thread is currently running.

        Returns:
            True if thread is running, False otherwise
        """
        return self.thread is not None and self.thread.isRunning()
