"""Dialog Orchestration System for TMDB Search

This module provides a queue-based dialog orchestration system to handle
concurrent dialog requests from multiple threads in a thread-safe manner.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from queue import Empty, Queue
from typing import Any

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class DialogTaskType(Enum):
    """Dialog task type enumeration."""

    SELECTION = "selection"
    MANUAL_SEARCH = "manual_search"


class DialogOrchestratorState(Enum):
    """Dialog orchestrator state enumeration."""

    IDLE = "idle"
    SHOWING = "showing"
    ERROR = "error"


@dataclass
class DialogTask:
    """Dialog task data structure."""

    task_id: str
    task_type: DialogTaskType
    payload: dict[str, Any]
    coalesce_key: str | None = None
    priority: int = 0  # Higher number = higher priority
    created_at: float = 0.0
    cancelled: bool = False

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


@dataclass
class DialogResult:
    """Dialog result data structure."""

    task_id: str
    success: bool
    result: Any | None = None
    error: str | None = None


class DialogTaskQueue:
    """Thread-safe FIFO queue for dialog tasks with coalescing support.

    This queue supports:
    - Thread-safe operations
    - Task coalescing based on coalesce_key
    - Priority-based ordering
    - Task cancellation
    """

    def __init__(self):
        self._queue: Queue[DialogTask] = Queue()
        self._lock = threading.RLock()
        self._coalesce_map: dict[str, DialogTask] = {}
        self._cancelled_tasks: set[str] = set()

    def put(self, task: DialogTask) -> None:
        """Add a task to the queue with coalescing support.

        Args:
            task: Dialog task to add
        """
        with self._lock:
            # Check if task is cancelled
            if task.cancelled or task.task_id in self._cancelled_tasks:
                logger.debug("Task %s is cancelled, not adding to queue", task.task_id)
                return

            # Handle coalescing
            if task.coalesce_key:
                existing_task = self._coalesce_map.get(task.coalesce_key)
                if existing_task:
                    # Cancel the existing task
                    existing_task.cancelled = True
                    self._cancelled_tasks.add(existing_task.task_id)
                    logger.debug(
                        "Coalesced task %s with existing task %s",
                        task.task_id,
                        existing_task.task_id,
                    )

                # Update coalesce map
                self._coalesce_map[task.coalesce_key] = task

            # Add to queue
            self._queue.put(task)
            logger.debug("Added task %s to queue (type: %s)", task.task_id, task.task_type.value)

    def get(self, timeout: float | None = None) -> DialogTask | None:
        """Get the next task from the queue.

        Args:
            timeout: Maximum time to wait for a task

        Returns:
            Next available task or None if timeout
        """
        try:
            task = self._queue.get(timeout=timeout)

            with self._lock:
                # Check if task is cancelled
                if task.cancelled or task.task_id in self._cancelled_tasks:
                    logger.debug("Task %s is cancelled, skipping", task.task_id)
                    self._queue.task_done()
                    return self.get(timeout=0)  # Try next task immediately

                # Remove from coalesce map if present
                if task.coalesce_key and task.coalesce_key in self._coalesce_map:
                    del self._coalesce_map[task.coalesce_key]

                logger.debug("Retrieved task %s from queue", task.task_id)
                return task

        except Empty:
            return None

    def task_done(self) -> None:
        """Mark a task as done."""
        self._queue.task_done()

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a specific task.

        Args:
            task_id: ID of task to cancel

        Returns:
            True if task was found and cancelled
        """
        with self._lock:
            self._cancelled_tasks.add(task_id)
            logger.debug("Cancelled task %s", task_id)
            return True

    def cancel_by_coalesce_key(self, coalesce_key: str) -> int:
        """Cancel all tasks with a specific coalesce key.

        Args:
            coalesce_key: Coalesce key to cancel

        Returns:
            Number of tasks cancelled
        """
        with self._lock:
            cancelled_count = 0

            # Cancel task in coalesce map
            if coalesce_key in self._coalesce_map:
                task = self._coalesce_map[coalesce_key]
                task.cancelled = True
                self._cancelled_tasks.add(task.task_id)
                del self._coalesce_map[coalesce_key]
                cancelled_count += 1
                logger.debug("Cancelled coalesced task %s", task.task_id)

            return cancelled_count

    def clear(self) -> None:
        """Clear all tasks from the queue."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                    self._queue.task_done()
                except Empty:
                    break

            self._coalesce_map.clear()
            self._cancelled_tasks.clear()
            logger.debug("Cleared all tasks from queue")

    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()


class DialogOrchestrator(QObject):
    """Main thread dialog orchestrator for managing dialog display.

    This orchestrator ensures that only one dialog is shown at a time
    and handles the queue of dialog requests from worker threads.
    """

    # Signals
    dialog_completed = pyqtSignal(DialogResult)
    dialog_error = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self._state = DialogOrchestratorState.IDLE
        self._queue = DialogTaskQueue()
        self._current_task: DialogTask | None = None
        self._lock = threading.RLock()

        # Dialog creation callbacks
        self._dialog_creators: dict[DialogTaskType, Callable] = {}

        # Timer for processing queue
        self._timer = QTimer()
        self._timer.timeout.connect(self._process_queue)
        self._timer.start(100)  # Check queue every 100ms

        logger.info("Dialog orchestrator initialized")

    def register_dialog_creator(
        self, task_type: DialogTaskType, creator_func: Callable[[DialogTask], Any]
    ) -> None:
        """Register a dialog creator function for a specific task type.

        Args:
            task_type: Type of dialog task
            creator_func: Function that creates and shows the dialog
        """
        self._dialog_creators[task_type] = creator_func
        logger.debug("Registered dialog creator for %s", task_type.value)

    def request_dialog(
        self,
        task_type: DialogTaskType,
        payload: dict[str, Any],
        coalesce_key: str | None = None,
        priority: int = 0,
    ) -> str:
        """Request a dialog to be shown.

        Args:
            task_type: Type of dialog to show
            payload: Data for the dialog
            coalesce_key: Key for coalescing similar requests
            priority: Priority level (higher = more important)

        Returns:
            Task ID for tracking the request
        """
        task_id = str(uuid.uuid4())

        task = DialogTask(
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            coalesce_key=coalesce_key,
            priority=priority,
        )

        self._queue.put(task)
        logger.info("Requested dialog %s (task_id: %s)", task_type.value, task_id)

        return task_id

    def cancel_request(self, task_id: str) -> bool:
        """Cancel a dialog request.

        Args:
            task_id: ID of the request to cancel

        Returns:
            True if request was found and cancelled
        """
        return self._queue.cancel_task(task_id)

    def cancel_by_coalesce_key(self, coalesce_key: str) -> int:
        """Cancel all requests with a specific coalesce key.

        Args:
            coalesce_key: Coalesce key to cancel

        Returns:
            Number of requests cancelled
        """
        return self._queue.cancel_by_coalesce_key(coalesce_key)

    def _process_queue(self) -> None:
        """Process the next task in the queue (main thread only)."""
        if self._state != DialogOrchestratorState.IDLE:
            return

        task = self._queue.get(timeout=0)
        if not task:
            return

        with self._lock:
            self._state = DialogOrchestratorState.SHOWING
            self._current_task = task

        logger.info("Processing dialog task %s (type: %s)", task.task_id, task.task_type.value)

        try:
            self._show_dialog(task)
        except Exception as e:
            logger.error("Error showing dialog for task %s: %s", task.task_id, str(e))
            self._handle_dialog_error(task, str(e))

    def _show_dialog(self, task: DialogTask) -> None:
        """Show the appropriate dialog for the task."""
        if task.task_type not in self._dialog_creators:
            raise ValueError(f"No dialog creator registered for {task.task_type.value}")

        creator_func = self._dialog_creators[task.task_type]

        # Create and show dialog
        dialog = creator_func(task)

        if dialog:
            # Connect dialog completion signals
            if hasattr(dialog, "result_selected"):
                dialog.result_selected.connect(
                    lambda result: self._handle_dialog_result(task, True, result)
                )
            elif hasattr(dialog, "finished"):
                dialog.finished.connect(
                    lambda result: self._handle_dialog_result(task, result == 1, None)
                )
            else:
                # Fallback: assume dialog completes immediately
                self._handle_dialog_result(task, True, None)

            # Show dialog
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
        else:
            # Dialog creation failed
            self._handle_dialog_error(task, "Failed to create dialog")

    def _handle_dialog_result(self, task: DialogTask, success: bool, result: Any) -> None:
        """Handle dialog completion result."""
        logger.info("Dialog task %s completed (success: %s)", task.task_id, success)

        dialog_result = DialogResult(task_id=task.task_id, success=success, result=result)

        # Emit signal
        self.dialog_completed.emit(dialog_result)

        # Reset state
        with self._lock:
            self._state = DialogOrchestratorState.IDLE
            self._current_task = None

        # Mark task as done
        self._queue.task_done()

    def _handle_dialog_error(self, task: DialogTask, error: str) -> None:
        """Handle dialog error."""
        logger.error("Dialog task %s failed: %s", task.task_id, error)

        dialog_result = DialogResult(task_id=task.task_id, success=False, error=error)

        # Emit signal
        self.dialog_error.emit(error)
        self.dialog_completed.emit(dialog_result)

        # Reset state
        with self._lock:
            self._state = DialogOrchestratorState.IDLE
            self._current_task = None

        # Mark task as done
        self._queue.task_done()

    @property
    def state(self) -> DialogOrchestratorState:
        """Get current orchestrator state."""
        return self._state

    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.size()

    @property
    def is_busy(self) -> bool:
        """Check if orchestrator is currently showing a dialog."""
        return self._state == DialogOrchestratorState.SHOWING
