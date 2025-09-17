"""
Base ViewModel class for AniVault application.

This module provides the foundational ViewModel class that all other ViewModels
inherit from, implementing common functionality and PyQt signal/slot mechanisms.
"""

from __future__ import annotations

import logging
import threading
from abc import abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

from PyQt5.QtCore import QMutex, QMutexLocker, QObject, pyqtSignal, pyqtSlot

from ..core.models import ProcessingState
from ..core.services.file_pipeline_worker import FilePipelineWorker, WorkerTask

# Type variable for ViewModel subclasses
T = TypeVar("T", bound="BaseViewModel")

# Logger for this module
logger = logging.getLogger(__name__)


class BaseViewModel(QObject):
    """
    Base class for all ViewModels in the MVVM architecture.

    This class provides common functionality including:
    - Signal/slot mechanisms for UI updates
    - Property change notifications
    - Error handling and logging
    - State management
    - Command pattern implementation

    Attributes:
        processing_state: Shared processing state object
        _properties: Dictionary of property values
        _commands: Dictionary of available commands
        _is_initialized: Whether the ViewModel has been initialized
    """

    # Common signals that all ViewModels can emit
    property_changed = pyqtSignal(str, object)  # property_name, new_value
    error_occurred = pyqtSignal(str)  # error_message
    status_changed = pyqtSignal(str)  # status_message
    data_loaded = pyqtSignal()  # when data is loaded
    data_saved = pyqtSignal()  # when data is saved
    command_started = pyqtSignal(str)  # command_name when command starts
    command_finished = pyqtSignal(str, bool)  # command_name, success
    validation_failed = pyqtSignal(str, str)  # property_name, error_message

    # Worker-related signals
    worker_task_started = pyqtSignal(str)  # task_name
    worker_task_progress = pyqtSignal(str, int)  # task_name, progress_percentage
    worker_task_finished = pyqtSignal(str, object, bool)  # task_name, result, success
    worker_task_error = pyqtSignal(str, str)  # task_name, error_message
    worker_finished = pyqtSignal()  # when worker finishes all tasks

    def __init__(self, parent: QObject | None = None) -> None:
        """
        Initialize the BaseViewModel.

        Args:
            parent: Parent QObject for Qt object hierarchy
        """
        super().__init__(parent)

        # Initialize properties
        self._properties: dict[str, Any] = {}
        self._commands: dict[str, Callable] = {}
        self._is_initialized: bool = False

        # Thread safety mechanisms
        self._property_mutex = QMutex()
        self._command_mutex = QMutex()
        self._python_lock = threading.Lock()

        # Validation rules for properties
        self._validation_rules: dict[str, Callable[[Any], bool]] = {}
        self._validation_messages: dict[str, str] = {}

        # Command execution tracking
        self._executing_commands: set = set()

        # Worker management
        self._worker: FilePipelineWorker | None = None
        self._worker_mutex = threading.Lock()

        # Create or get shared processing state
        self.processing_state = ProcessingState()

        # Connect to processing state signals
        self.processing_state.error_occurred.connect(self._on_processing_error)
        self.processing_state.status_message_updated.connect(self._on_status_changed)

        logger.debug(f"Initialized {self.__class__.__name__}")

    def initialize(self) -> None:
        """
        Initialize the ViewModel after construction.

        This method should be called after the ViewModel is created to set up
        any required resources or connections. Subclasses should override this
        method to perform their specific initialization.
        """
        if self._is_initialized:
            logger.warning(f"{self.__class__.__name__} already initialized")
            return

        self._setup_commands()
        self._setup_properties()
        self._is_initialized = True

        logger.info(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    def _setup_commands(self) -> None:
        """
        Set up available commands for this ViewModel.

        Subclasses must implement this method to define their specific commands.
        Commands should be added to self._commands dictionary.
        """
        pass

    @abstractmethod
    def _setup_properties(self) -> None:
        """
        Set up initial property values for this ViewModel.

        Subclasses must implement this method to define their specific properties.
        Properties should be added to self._properties dictionary.
        """
        pass

    def get_property(self, name: str, default: Any = None) -> Any:
        """
        Get a property value by name.

        Args:
            name: Property name
            default: Default value if property doesn't exist

        Returns:
            Property value or default
        """
        with QMutexLocker(self._property_mutex):
            return self._properties.get(name, default)

    def set_property(
        self, name: str, value: Any, notify: bool = True, validate: bool = True
    ) -> None:
        """
        Set a property value and optionally notify listeners.

        Args:
            name: Property name
            value: New property value
            notify: Whether to emit property_changed signal
            validate: Whether to validate the value before setting
        """
        # Validate the value if validation is enabled
        if validate and name in self._validation_rules:
            if not self._validate_property(name, value):
                error_msg = self._validation_messages.get(
                    name, f"Invalid value for property '{name}'"
                )
                self.validation_failed.emit(name, error_msg)
                logger.warning(f"Validation failed for property '{name}': {error_msg}")
                return

        old_value = self._properties.get(name)
        self._properties[name] = value

        if notify and old_value != value:
            self.property_changed.emit(name, value)
            logger.debug(f"Property '{name}' changed: {old_value} -> {value}")

    def has_property(self, name: str) -> bool:
        """
        Check if a property exists.

        Args:
            name: Property name

        Returns:
            True if property exists
        """
        with QMutexLocker(self._property_mutex):
            return name in self._properties

    def get_all_properties(self) -> dict[str, Any]:
        """
        Get all properties as a dictionary.

        Returns:
            Dictionary of all properties
        """
        with QMutexLocker(self._property_mutex):
            return self._properties.copy()

    def execute_command(self, command_name: str, *args, **kwargs) -> Any:
        """
        Execute a command by name.

        Args:
            command_name: Name of the command to execute
            *args: Positional arguments for the command
            **kwargs: Keyword arguments for the command

        Returns:
            Command result

        Raises:
            KeyError: If command doesn't exist
            Exception: If command execution fails
        """
        # Check if command exists
        if command_name not in self._commands:
            error_msg = f"Command '{command_name}' not found"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            raise KeyError(error_msg)

        # Check if command is already executing (non-blocking check)
        if command_name in self._executing_commands:
            error_msg = f"Command '{command_name}' is already executing"
            logger.warning(error_msg)
            self.error_occurred.emit(error_msg)
            raise RuntimeError(error_msg)

        # Mark command as executing
        self._executing_commands.add(command_name)

        # Emit command started signal
        print(f"DEBUG: About to emit command_started signal for {command_name}")  # 강제 출력
        self.command_started.emit(command_name)
        print(f"DEBUG: command_started signal emitted for {command_name}")  # 강제 출력

        try:
            print(f"DEBUG: About to execute command function for {command_name}")  # 강제 출력
            logger.debug(f"Executing command '{command_name}' with args={args}, kwargs={kwargs}")
            logger.debug(f"Command function: {self._commands[command_name]}")
            result = self._commands[command_name](*args, **kwargs)
            print(
                f"DEBUG: Command {command_name} executed successfully, result: {result}"
            )  # 강제 출력
            logger.debug(f"Command '{command_name}' completed successfully with result: {result}")
            print(f"DEBUG: About to emit command_finished signal for {command_name}")  # 강제 출력
            self.command_finished.emit(command_name, True)
            print(f"DEBUG: command_finished signal emitted for {command_name}")  # 강제 출력
            return result
        except Exception as e:
            error_msg = f"Command '{command_name}' failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            self.command_finished.emit(command_name, False)
            raise
        finally:
            # Remove command from executing set
            self._executing_commands.discard(command_name)

    def add_command(self, name: str, func: Callable) -> None:
        """
        Add a command to this ViewModel.

        Args:
            name: Command name
            func: Function to execute for this command
        """
        with QMutexLocker(self._command_mutex):
            self._commands[name] = func
            logger.debug(f"Added command '{name}'")

    def remove_command(self, name: str) -> bool:
        """
        Remove a command from this ViewModel.

        Args:
            name: Command name

        Returns:
            True if command was removed, False if not found
        """
        with QMutexLocker(self._command_mutex):
            if name in self._commands:
                del self._commands[name]
                logger.debug(f"Removed command '{name}'")
                return True
            return False

    def get_available_commands(self) -> list[str]:
        """
        Get list of available command names.

        Returns:
            List of command names
        """
        with QMutexLocker(self._command_mutex):
            return list(self._commands.keys())

    def has_command(self, name: str) -> bool:
        """
        Check if a command exists.

        Args:
            name: Command name

        Returns:
            True if command exists
        """
        with QMutexLocker(self._command_mutex):
            return name in self._commands

    def bind_to_property(self, property_name: str, callback: Callable[[Any], None]) -> None:
        """
        Bind a callback to property changes.

        Args:
            property_name: Name of the property to bind to
            callback: Function to call when property changes
        """
        self.property_changed.connect(
            lambda name, value: callback(value) if name == property_name else None
        )
        logger.debug(f"Bound callback to property '{property_name}'")

    def bind_to_error(self, callback: Callable[[str], None]) -> None:
        """
        Bind a callback to error events.

        Args:
            callback: Function to call when an error occurs
        """
        self.error_occurred.connect(callback)
        logger.debug("Bound callback to error events")

    def bind_to_status(self, callback: Callable[[str], None]) -> None:
        """
        Bind a callback to status changes.

        Args:
            callback: Function to call when status changes
        """
        self.status_changed.connect(callback)
        logger.debug("Bound callback to status changes")

    def add_validation_rule(
        self, property_name: str, validator: Callable[[Any], bool], error_message: str = ""
    ) -> None:
        """
        Add a validation rule for a property.

        Args:
            property_name: Name of the property to validate
            validator: Function that returns True if value is valid
            error_message: Error message to show when validation fails
        """
        self._validation_rules[property_name] = validator
        self._validation_messages[property_name] = error_message
        logger.debug(f"Added validation rule for property '{property_name}'")

    def remove_validation_rule(self, property_name: str) -> bool:
        """
        Remove a validation rule for a property.

        Args:
            property_name: Name of the property

        Returns:
            True if rule was removed, False if not found
        """
        if property_name in self._validation_rules:
            del self._validation_rules[property_name]
            del self._validation_messages[property_name]
            logger.debug(f"Removed validation rule for property '{property_name}'")
            return True
        return False

    def _validate_property(self, property_name: str, value: Any) -> bool:
        """
        Validate a property value using its validation rule.

        Args:
            property_name: Name of the property
            value: Value to validate

        Returns:
            True if value is valid
        """
        if property_name not in self._validation_rules:
            return True

        try:
            return self._validation_rules[property_name](value)
        except Exception as e:
            logger.error(f"Validation rule for '{property_name}' failed: {e}")
            return False

    def validate_all_properties(self) -> dict[str, str]:
        """
        Validate all properties that have validation rules.

        Returns:
            Dictionary of property names to error messages for invalid properties
        """
        errors = {}
        with QMutexLocker(self._property_mutex):
            for property_name, value in self._properties.items():
                if not self._validate_property(property_name, value):
                    error_msg = self._validation_messages.get(
                        property_name, f"Invalid value for property '{property_name}'"
                    )
                    errors[property_name] = error_msg

        return errors

    def is_command_executing(self, command_name: str) -> bool:
        """
        Check if a command is currently executing.

        Args:
            command_name: Name of the command to check

        Returns:
            True if command is executing
        """
        with QMutexLocker(self._command_mutex):
            return command_name in self._executing_commands

    def get_executing_commands(self) -> list[str]:
        """
        Get list of currently executing commands.

        Returns:
            List of executing command names
        """
        with QMutexLocker(self._command_mutex):
            return list(self._executing_commands)

    def create_worker(self) -> FilePipelineWorker:
        """
        Create and configure a new FilePipelineWorker.

        Returns:
            Configured FilePipelineWorker instance
        """
        with self._worker_mutex:
            if self._worker is not None:
                logger.warning("Worker already exists, cleaning up old worker")
                self._cleanup_worker()

            self._worker = FilePipelineWorker(self)
            self._worker.set_processing_state(self.processing_state)

            # Connect worker signals to ViewModel signals
            self._worker.task_started.connect(self.worker_task_started.emit)
            self._worker.task_progress.connect(self.worker_task_progress.emit)
            self._worker.task_finished.connect(self.worker_task_finished.emit)
            self._worker.task_error.connect(self.worker_task_error.emit)
            self._worker.worker_finished.connect(self.worker_finished.emit)

            logger.debug("Created new FilePipelineWorker")
            return self._worker

    def get_worker(self) -> FilePipelineWorker | None:
        """
        Get the current worker instance.

        Returns:
            Current worker or None if not created
        """
        with self._worker_mutex:
            return self._worker

    def has_worker(self) -> bool:
        """
        Check if a worker is currently available.

        Returns:
            True if worker exists
        """
        with self._worker_mutex:
            return self._worker is not None

    def is_worker_running(self) -> bool:
        """
        Check if the worker is currently running.

        Returns:
            True if worker is running
        """
        with self._worker_mutex:
            return self._worker is not None and self._worker.is_running()

    def add_worker_task(self, task: WorkerTask) -> None:
        """
        Add a task to the worker queue.

        Args:
            task: Task to add to the worker queue
        """
        with self._worker_mutex:
            if self._worker is None:
                raise RuntimeError("Worker not created. Call create_worker() first.")

            self._worker.add_task(task)
            logger.debug(f"Added task '{task.get_name()}' to worker queue")

    def add_worker_tasks(self, tasks: list[WorkerTask]) -> None:
        """
        Add multiple tasks to the worker queue.

        Args:
            tasks: List of tasks to add
        """
        with self._worker_mutex:
            if self._worker is None:
                raise RuntimeError("Worker not created. Call create_worker() first.")

            self._worker.add_tasks(tasks)
            logger.debug(f"Added {len(tasks)} tasks to worker queue")

    def start_worker(self) -> None:
        """
        Start the worker thread.
        """
        with self._worker_mutex:
            if self._worker is None:
                raise RuntimeError("Worker not created. Call create_worker() first.")

            if self._worker.is_running():
                logger.warning("Worker is already running")
                return

            logger.info("Starting worker thread...")
            self._worker.start()
            logger.info(f"Worker thread started, running: {self._worker.is_running()}")

    def stop_worker(self, force: bool = False) -> None:
        """
        Stop the worker thread.

        Args:
            force: Whether to force stop immediately
        """
        with self._worker_mutex:
            if self._worker is None:
                logger.warning("No worker to stop")
                return

            if not self._worker.is_running():
                logger.warning("Worker is not running")
                return

            if force:
                self._worker.force_stop()
                logger.debug("Force stopped worker")
            else:
                self._worker.stop()
                logger.debug("Requested worker to stop")

    def wait_for_worker(self, timeout: int = 30000) -> bool:
        """
        Wait for the worker to complete all tasks.

        Args:
            timeout: Maximum time to wait in milliseconds

        Returns:
            True if worker completed, False if timeout
        """
        with self._worker_mutex:
            if self._worker is None:
                logger.warning("No worker to wait for")
                return True

            return self._worker.wait_for_completion(timeout)

    def wait_for_worker_start(self, timeout: int = 1000) -> bool:
        """
        Wait for the worker to actually start running.

        Args:
            timeout: Maximum time to wait in milliseconds

        Returns:
            True if worker started, False if timeout
        """
        with self._worker_mutex:
            if self._worker is None:
                logger.warning("No worker to wait for start")
                return False

            return self._worker.wait_for_start(timeout)

    def get_worker_queue_size(self) -> int:
        """
        Get the number of pending tasks in the worker queue.

        Returns:
            Number of pending tasks
        """
        with self._worker_mutex:
            if self._worker is None:
                return 0
            return self._worker.get_queue_size()

    def clear_worker_tasks(self) -> None:
        """Clear all pending tasks from the worker queue."""
        with self._worker_mutex:
            if self._worker is None:
                logger.warning("No worker to clear tasks from")
                return

            self._worker.clear_tasks()
            logger.debug("Cleared worker task queue")

    def _cleanup_worker(self) -> None:
        """Clean up the current worker."""
        if self._worker is not None:
            if self._worker.is_running():
                self._worker.stop()
                self._worker.wait_for_completion(5000)  # Wait up to 5 seconds

            # Disconnect signals
            self._worker.task_started.disconnect()
            self._worker.task_progress.disconnect()
            self._worker.task_finished.disconnect()
            self._worker.task_error.disconnect()
            self._worker.worker_finished.disconnect()

            self._worker = None
            logger.debug("Cleaned up worker")

    @pyqtSlot(str)
    def _on_processing_error(self, error_message: str) -> None:
        """
        Handle processing errors from the processing state.

        Args:
            error_message: Error message from processing state
        """
        logger.error(f"Processing error: {error_message}")
        self.error_occurred.emit(error_message)

    @pyqtSlot(str)
    def _on_status_changed(self, status_message: str) -> None:
        """
        Handle status changes from the processing state.

        Args:
            status_message: Status message from processing state
        """
        logger.debug(f"Status changed: {status_message}")
        self.status_changed.emit(status_message)

    def reset(self) -> None:
        """
        Reset the ViewModel to its initial state.

        This method should be overridden by subclasses to reset their
        specific state while maintaining the base functionality.
        """
        self._properties.clear()
        self._commands.clear()
        self._is_initialized = False
        self.processing_state.reset()

        logger.info(f"Reset {self.__class__.__name__}")

    def cleanup(self) -> None:
        """
        Clean up resources used by this ViewModel.

        This method should be called when the ViewModel is no longer needed
        to ensure proper cleanup of resources.
        """
        # Wait for any executing commands to finish
        with QMutexLocker(self._command_mutex):
            if self._executing_commands:
                logger.warning(
                    f"Cleaning up ViewModel with executing commands: {self._executing_commands}"
                )
                # Note: In a real application, you might want to wait or cancel these commands

        # Disconnect all signals safely
        try:
            self.property_changed.disconnect()
        except TypeError:
            pass  # No connections to disconnect

        try:
            self.error_occurred.disconnect()
        except TypeError:
            pass

        try:
            self.status_changed.disconnect()
        except TypeError:
            pass

        try:
            self.data_loaded.disconnect()
        except TypeError:
            pass

        try:
            self.data_saved.disconnect()
        except TypeError:
            pass

        try:
            self.command_started.disconnect()
        except TypeError:
            pass

        try:
            self.command_finished.disconnect()
        except TypeError:
            pass

        try:
            self.validation_failed.disconnect()
        except TypeError:
            pass

        # Disconnect from processing state
        self.processing_state.error_occurred.disconnect(self._on_processing_error)
        self.processing_state.status_message_updated.disconnect(self._on_status_changed)

        # Clear internal state
        with QMutexLocker(self._property_mutex):
            self._properties.clear()

        with QMutexLocker(self._command_mutex):
            self._commands.clear()
            self._executing_commands.clear()

        # Clear validation rules
        self._validation_rules.clear()
        self._validation_messages.clear()

        # Clean up worker
        self._cleanup_worker()

        logger.info(f"Cleaned up {self.__class__.__name__}")

    def __repr__(self) -> str:
        """Return string representation of this ViewModel."""
        return f"{self.__class__.__name__}(initialized={self._is_initialized})"

    def __str__(self) -> str:
        """Return human-readable string representation."""
        return f"{self.__class__.__name__} with {len(self._properties)} properties and {len(self._commands)} commands"


class ViewModelFactory:
    """
    Factory class for creating ViewModel instances.

    This class provides a centralized way to create ViewModel instances
    with proper initialization and dependency injection.
    """

    _viewmodels: dict[str, type[BaseViewModel]] = {}

    @classmethod
    def register_viewmodel(cls, name: str, viewmodel_class: type[BaseViewModel]) -> None:
        """
        Register a ViewModel class.

        Args:
            name: Name to register the ViewModel under
            viewmodel_class: ViewModel class to register
        """
        if not issubclass(viewmodel_class, BaseViewModel):
            raise ValueError(f"Class {viewmodel_class} must inherit from BaseViewModel")

        cls._viewmodels[name] = viewmodel_class
        logger.info(f"Registered ViewModel '{name}' as {viewmodel_class.__name__}")

    @classmethod
    def create_viewmodel(cls, name: str, parent: QObject | None = None, **kwargs) -> BaseViewModel:
        """
        Create a ViewModel instance by name.

        Args:
            name: Registered name of the ViewModel
            parent: Parent QObject
            **kwargs: Additional arguments for ViewModel constructor

        Returns:
            Created ViewModel instance

        Raises:
            KeyError: If ViewModel name is not registered
        """
        if name not in cls._viewmodels:
            raise KeyError(f"ViewModel '{name}' not registered")

        viewmodel_class = cls._viewmodels[name]
        instance = viewmodel_class(parent, **kwargs)
        instance.initialize()

        logger.info(f"Created ViewModel '{name}' as {instance.__class__.__name__}")
        return instance

    @classmethod
    def get_registered_viewmodels(cls) -> list[str]:
        """
        Get list of registered ViewModel names.

        Returns:
            List of registered ViewModel names
        """
        return list(cls._viewmodels.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a ViewModel is registered.

        Args:
            name: ViewModel name to check

        Returns:
            True if ViewModel is registered
        """
        return name in cls._viewmodels
