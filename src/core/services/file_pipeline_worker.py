"""
File Pipeline Worker for AniVault application.

This module provides a QThread-based background worker for handling
file processing operations without blocking the UI thread.
"""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Optional

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from ..models import AnimeFile, FileGroup, ProcessingState

# Logger for this module
logger = logging.getLogger(__name__)


class WorkerTask(ABC):
    """
    Abstract base class for worker tasks.

    This class defines the interface that all worker tasks must implement
    to be executed by the FilePipelineWorker.
    """

    @abstractmethod
    def execute(self) -> Any:
        """
        Execute the task.

        Returns:
            Task result
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of this task.

        Returns:
            Task name
        """
        pass

    def get_progress_message(self) -> str:
        """
        Get a progress message for this task.

        Returns:
            Progress message
        """
        return f"Executing {self.get_name()}"


class FilePipelineWorker(QThread):
    """
    QThread-based background worker for file processing operations.

    This worker handles heavy processing tasks in a separate thread to
    prevent UI blocking. It provides signals for progress updates and
    result delivery.
    """

    # Signals for communication with ViewModel
    task_started = pyqtSignal(str)  # task_name
    task_progress = pyqtSignal(str, int)  # task_name, progress_percentage
    task_finished = pyqtSignal(str, object, bool)  # task_name, result, success
    task_error = pyqtSignal(str, str)  # task_name, error_message
    worker_finished = pyqtSignal()  # when worker thread finishes

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """
        Initialize the FilePipelineWorker.

        Args:
            parent: Parent QObject for Qt object hierarchy
        """
        super().__init__(parent)

        # Task queue and execution state
        self._task_queue: list[WorkerTask] = []
        self._current_task: Optional[WorkerTask] = None
        self._is_running: bool = False
        self._should_stop: bool = False

        # Thread safety
        self._queue_mutex = threading.Lock()
        self._state_mutex = threading.Lock()

        # Processing state reference
        self._processing_state: Optional[ProcessingState] = None

        logger.debug("FilePipelineWorker initialized")

    def set_processing_state(self, processing_state: ProcessingState) -> None:
        """
        Set the processing state object for progress updates.

        Args:
            processing_state: ProcessingState instance
        """
        self._processing_state = processing_state
        logger.debug("Processing state set")

    def add_task(self, task: WorkerTask) -> None:
        """
        Add a task to the worker queue.

        Args:
            task: Task to add to the queue
        """
        with self._queue_mutex:
            self._task_queue.append(task)
            logger.debug(f"Added task '{task.get_name()}' to queue")

    def add_tasks(self, tasks: list[WorkerTask]) -> None:
        """
        Add multiple tasks to the worker queue.

        Args:
            tasks: List of tasks to add
        """
        with self._queue_mutex:
            self._task_queue.extend(tasks)
            logger.debug(f"Added {len(tasks)} tasks to queue")

    def clear_tasks(self) -> None:
        """Clear all pending tasks from the queue."""
        with self._queue_mutex:
            self._task_queue.clear()
            logger.debug("Cleared task queue")

    def get_queue_size(self) -> int:
        """
        Get the number of pending tasks.

        Returns:
            Number of pending tasks
        """
        with self._queue_mutex:
            return len(self._task_queue)

    def is_running(self) -> bool:
        """
        Check if the worker is currently running.

        Returns:
            True if worker is running
        """
        with self._state_mutex:
            return self._is_running

    def stop(self) -> None:
        """Request the worker to stop after current task completes."""
        with self._state_mutex:
            self._should_stop = True
        logger.debug("Stop requested")

    def force_stop(self) -> None:
        """Force the worker to stop immediately."""
        with self._state_mutex:
            self._should_stop = True
        self.terminate()  # Force terminate the thread
        logger.warning("Worker force stopped")

    def run(self) -> None:
        """
        Main worker thread execution loop.

        This method runs in the background thread and processes tasks
        from the queue until stopped or no more tasks remain.
        """
        logger.info("Worker thread started")

        with self._state_mutex:
            self._is_running = True
            self._should_stop = False

        try:
            while not self._should_stop:
                # Get next task
                task = None
                with self._queue_mutex:
                    if self._task_queue:
                        task = self._task_queue.pop(0)
                        logger.debug(f"Retrieved task: {task.get_name()}")
                    else:
                        logger.debug("No tasks in queue")

                if task is None:
                    # No more tasks, exit the loop
                    logger.debug("No more tasks, exiting worker loop")
                    with self._state_mutex:
                        self._is_running = False
                    break

                # Execute the task
                logger.debug(f"Executing task: {task.get_name()}")
                self._execute_task(task)

        except Exception as e:
            logger.error(f"Worker thread error: {e}", exc_info=True)
        finally:
            with self._state_mutex:
                self._is_running = False

            logger.info("Worker thread finished")
            self.worker_finished.emit()

    def wait_for_start(self, timeout_ms: int = 1000) -> bool:
        """
        Wait for the worker to actually start running.

        Args:
            timeout_ms: Maximum time to wait in milliseconds

        Returns:
            True if worker started, False if timeout
        """
        import time

        start_time = time.time()
        timeout_seconds = timeout_ms / 1000.0

        while time.time() - start_time < timeout_seconds:
            if self.is_running():
                return True
            time.sleep(0.01)  # 10ms intervals

        return False

    def _execute_task(self, task: WorkerTask) -> None:
        """
        Execute a single task.

        Args:
            task: Task to execute
        """
        task_name = task.get_name()
        logger.debug(f"Starting task: {task_name}")

        # Update current task
        with self._state_mutex:
            self._current_task = task

        # Emit task started signal
        self.task_started.emit(task_name)

        # Update processing state if available
        if self._processing_state:
            self._processing_state.status_message = task.get_progress_message()

        try:
            # Execute the task
            result = task.execute()

            # Emit success signal
            self.task_finished.emit(task_name, result, True)
            logger.debug(f"Task '{task_name}' completed successfully")

        except Exception as e:
            error_msg = f"Task '{task_name}' failed: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # Emit error signal
            self.task_error.emit(task_name, error_msg)

            # Emit task finished signal with failure
            self.task_finished.emit(task_name, None, False)

            # Update processing state if available
            if self._processing_state:
                self._processing_state.add_error(error_msg)

        finally:
            # Clear current task
            with self._state_mutex:
                self._current_task = None

    def get_current_task(self) -> Optional[WorkerTask]:
        """
        Get the currently executing task.

        Returns:
            Current task or None if no task is executing
        """
        with self._state_mutex:
            return self._current_task

    def wait_for_completion(self, timeout: int = 30000) -> bool:
        """
        Wait for the worker to complete all tasks.

        Args:
            timeout: Maximum time to wait in milliseconds

        Returns:
            True if worker completed, False if timeout
        """
        import time

        start_time = time.time()
        timeout_seconds = timeout / 1000.0

        while time.time() - start_time < timeout_seconds:
            if not self.is_running():
                return True
            time.sleep(0.01)  # 10ms intervals

        return False


class FileScanningTask(WorkerTask):
    """
    Task for scanning directories for anime files.
    """

    def __init__(self, scan_directories: list[str], supported_extensions: list[str]) -> None:
        """
        Initialize the file scanning task.

        Args:
            scan_directories: List of directories to scan
            supported_extensions: List of supported file extensions
        """
        self.scan_directories = scan_directories
        self.supported_extensions = supported_extensions
        self._files: list[AnimeFile] = []

    def execute(self) -> list[AnimeFile]:
        """
        Execute the file scanning.

        Returns:
            List of found anime files
        """
        # This would integrate with the actual file scanner
        # For now, return empty list as placeholder
        logger.debug(f"Scanning directories: {self.scan_directories}")
        return self._files

    def get_name(self) -> str:
        """Get task name."""
        return "File Scanning"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Scanning {len(self.scan_directories)} directories for anime files"


class FileGroupingTask(WorkerTask):
    """
    Task for grouping similar anime files.
    """

    def __init__(self, files: list[AnimeFile], similarity_threshold: float = 0.7) -> None:
        """
        Initialize the file grouping task.

        Args:
            files: List of files to group
            similarity_threshold: Minimum similarity score for grouping
        """
        self.files = files
        self.similarity_threshold = similarity_threshold
        self._groups: list[FileGroup] = []

    def execute(self) -> list[FileGroup]:
        """
        Execute the file grouping.

        Returns:
            List of file groups
        """
        # This would integrate with the actual file grouper
        # For now, return empty list as placeholder
        logger.debug(f"Grouping {len(self.files)} files with threshold {self.similarity_threshold}")
        return self._groups

    def get_name(self) -> str:
        """Get task name."""
        return "File Grouping"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Grouping {len(self.files)} files into similar groups"


class FileParsingTask(WorkerTask):
    """
    Task for parsing anime file information.
    """

    def __init__(self, files: list[AnimeFile]) -> None:
        """
        Initialize the file parsing task.

        Args:
            files: List of files to parse
        """
        self.files = files
        self._parsed_files: list[AnimeFile] = []

    def execute(self) -> list[AnimeFile]:
        """
        Execute the file parsing.

        Returns:
            List of parsed files
        """
        # This would integrate with the actual file parser
        # For now, return the files as-is
        logger.debug(f"Parsing {len(self.files)} files")
        return self.files

    def get_name(self) -> str:
        """Get task name."""
        return "File Parsing"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Parsing information from {len(self.files)} files"


class MetadataRetrievalTask(WorkerTask):
    """
    Task for retrieving metadata from TMDB.
    """

    def __init__(self, files: list[AnimeFile], api_key: str) -> None:
        """
        Initialize the metadata retrieval task.

        Args:
            files: List of files to get metadata for
            api_key: TMDB API key
        """
        self.files = files
        self.api_key = api_key
        self._files_with_metadata: list[AnimeFile] = []

    def execute(self) -> list[AnimeFile]:
        """
        Execute the metadata retrieval.

        Returns:
            List of files with metadata
        """
        # This would integrate with the actual TMDB client
        # For now, return the files as-is
        logger.debug(f"Retrieving metadata for {len(self.files)} files")
        return self.files

    def get_name(self) -> str:
        """Get task name."""
        return "Metadata Retrieval"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Retrieving metadata for {len(self.files)} files"


class FileMovingTask(WorkerTask):
    """
    Task for moving and organizing files.
    """

    def __init__(self, groups: list[FileGroup], target_directory: str) -> None:
        """
        Initialize the file moving task.

        Args:
            groups: List of file groups to move
            target_directory: Target directory for organized files
        """
        self.groups = groups
        self.target_directory = target_directory
        self._moved_files: list[AnimeFile] = []

    def execute(self) -> list[AnimeFile]:
        """
        Execute the file moving.

        Returns:
            List of moved files
        """
        # This would integrate with the actual file mover
        # For now, return empty list as placeholder
        logger.debug(f"Moving {len(self.groups)} groups to {self.target_directory}")
        return self._moved_files

    def get_name(self) -> str:
        """Get task name."""
        return "File Moving"

    def get_progress_message(self) -> str:
        """Get progress message."""
        return f"Moving {len(self.groups)} file groups to target directory"
