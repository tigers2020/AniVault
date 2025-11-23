"""Scan Event Handler for file scanning operations.

This module contains the ScanEventHandler class that handles events emitted
by the ScanController. It processes scan lifecycle events (started, progress,
finished, error) and file grouping results.

The handler follows the BaseEventHandler pattern for consistent status messages
and error handling across the application.
"""

from __future__ import annotations

from typing import Callable

from anivault.core.file_grouper import Group
from anivault.gui.controllers.scan_controller import ScanController
from anivault.gui.managers.status_manager import StatusManager
from anivault.gui.models import FileItem
from anivault.gui.state_model import StateModel
from anivault.shared.constants.gui_messages import DialogTitles

from .base_event_handler import BaseEventHandler


class ScanEventHandler(BaseEventHandler):
    """Handler for scan-related events from ScanController.

    This handler processes all scan lifecycle events and updates the UI
    accordingly. It maintains separation of concerns by not directly
    manipulating UI elements, instead using callbacks and the state model.

    Attributes:
        _state_model: StateModel instance for managing file state
        _scan_controller: ScanController instance for triggering grouping
        _update_file_tree_callback: Callback to update the file tree view

    Example:
        >>> handler = ScanEventHandler(
        ...     status_manager=status_mgr,
        ...     state_model=state_mdl,
        ...     scan_controller=scan_ctrl,
        ...     update_file_tree_callback=main_window.update_file_tree_with_groups
        ... )
        >>> scan_controller.scan_started.connect(handler.on_scan_started)
    """

    def __init__(
        self,
        status_manager: StatusManager,
        state_model: StateModel,
        scan_controller: ScanController,
        update_file_tree_callback: Callable[[dict[str, list[FileItem]]], None],
    ) -> None:
        """Initialize the scan event handler.

        Args:
            status_manager: StatusManager for displaying status messages
            state_model: StateModel for managing scanned files
            scan_controller: ScanController for triggering file grouping
            update_file_tree_callback: Callback to update the file tree view
                with grouped files (typically MainWindow.update_file_tree_with_groups)
        """
        super().__init__(status_manager)
        self._state_model = state_model
        self._scan_controller = scan_controller
        self._update_file_tree_callback = update_file_tree_callback

    def on_scan_started(self) -> None:
        """Handle scan started signal.

        Displays a status message indicating that scanning has begun.
        """
        self._show_status("Scanning for media files...")

    def on_scan_progress(self, progress: int) -> None:
        """Handle scan progress signal.

        Updates the status bar with the current scan progress.

        Args:
            progress: Scan progress percentage (0-100)
        """
        self._show_status(f"Scanning... {progress}%")

    def on_scan_finished(self, file_items: list[FileItem]) -> None:
        """Handle scan finished signal.

        Processes scan completion by:
        1. Adding scanned files to the state model
        2. Displaying completion message
        3. Triggering file grouping if files were found

        Args:
            file_items: List of FileItem objects found during scan
        """
        # Update state model
        self._state_model.add_scanned_files(file_items)

        self._show_status(f"Scan complete. Found {len(file_items)} files")
        self._logger.info("File scan completed successfully")

        # Start file grouping after scan completion
        if file_items:
            try:
                self._scan_controller.group_files(file_items)
            except ValueError as e:
                self._logger.exception("File grouping failed")
                self._show_status(f"Grouping failed: {e}")

    def on_scan_error(self, error_msg: str) -> None:
        """Handle scan error signal.

        Processes scan errors by displaying both a status message and
        an error dialog to the user.

        Args:
            error_msg: Error message describing what went wrong
        """
        self._logger.error("File scan error: %s", error_msg)
        self._show_error(
            f"Failed to scan directory:\n{error_msg}",
            DialogTitles.SCAN_ERROR,
        )

    def on_files_grouped(self, grouped_files: list[Group]) -> None:
        """Handle files grouped signal.

        Updates the file tree view with the grouped files. Note that TMDB
        auto-start logic is intentionally NOT included here to maintain
        separation of concerns - that workflow orchestration remains in
        MainWindow.

        Args:
            grouped_files: List of Group objects (NO dict!)
        """
        # Convert list[Group] to dict for view updater callback (temporary compatibility)
        # ScannedFile and FileItem have compatible interfaces for display purposes
        from typing import cast

        grouped_dict = {
            group.title: cast("list[FileItem]", group.files) for group in grouped_files
        }
        self._update_file_tree_callback(grouped_dict)
