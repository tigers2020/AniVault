"""Base Event Handler for GUI components.

This module provides BaseEventHandler, an abstract base class for all event handlers
in the AniVault GUI. It encapsulates common patterns for status messages and error
handling, ensuring consistency across all handler implementations.

Pattern:
    All event handlers inherit from BaseEventHandler and gain:
    - Consistent status message display (status bar + logging)
    - Consistent error handling (dialog + status bar + logging)
    - Logger instance named after the handler class
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from anivault.gui.managers.status_manager import StatusManager


class BaseEventHandler:
    """Base class for all event handlers.

    This class provides common functionality for event handlers including
    status message display and error handling. All handlers should inherit
    from this class to ensure consistent behavior.

    Attributes:
        _status_manager: StatusManager instance for displaying messages
        _logger: Logger instance for the handler class

    Example:
        >>> class MyHandler(BaseEventHandler):
        ...     def __init__(self, status_manager: StatusManager):
        ...         super().__init__(status_manager)
        ...
        ...     def on_event(self):
        ...         self._show_status("Processing...")
        ...         try:
        ...             # Handle event
        ...             pass
        ...         except Exception as e:
        ...             self._show_error(str(e), "Error Title")
    """

    def __init__(self, status_manager: StatusManager) -> None:
        """Initialize the base event handler.

        Args:
            status_manager: StatusManager instance for displaying status messages
        """
        self._status_manager = status_manager
        self._logger = logging.getLogger(self.__class__.__name__)

    def _show_status(self, message: str, timeout: int = 0) -> None:
        """Display a status message in the status bar and log it.

        This method provides a consistent way to show status updates across
        all handlers. The message is displayed in the status bar and logged
        at INFO level.

        Args:
            message: Status message to display
            timeout: Optional timeout in milliseconds (0 = no timeout)

        Example:
            >>> self._show_status("Scanning files...")
            >>> self._show_status("Complete!", timeout=3000)
        """
        self._status_manager.show_message(message, timeout)
        self._logger.info(message)

    def _show_error(self, message: str, title: str = "Error") -> None:
        """Display an error message via dialog, status bar, and logging.

        This method provides a consistent way to handle errors across all
        handlers. The error is:
        1. Shown in a warning dialog to the user
        2. Displayed in the status bar with "Error:" prefix
        3. Logged at ERROR level

        Args:
            message: Error message to display
            title: Dialog window title (default: "Error")

        Example:
            >>> self._show_error("Failed to scan directory", "Scan Error")
        """
        self._status_manager.show_message(f"Error: {message}")
        self._logger.error(message)
        QMessageBox.warning(None, title, message)
