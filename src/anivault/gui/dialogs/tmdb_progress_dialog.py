"""
TMDB Progress Dialog for AniVault GUI

This module contains the TMDBProgressDialog class that provides a progress
dialog specifically for TMDB matching operations with cancel functionality.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QLabel, QProgressDialog, QWidget

from anivault.shared.constants.gui_messages import (
    ButtonTexts,
    ProgressMessages,
)

logger = logging.getLogger(__name__)


class TMDBProgressDialog(QProgressDialog):
    """
    Custom progress dialog for TMDB matching operations.

    This dialog provides enhanced progress tracking with detailed status
    information and proper cancel handling for TMDB API operations.
    """

    # Signals
    cancelled = Signal()  # Emitted when user cancels the operation

    def __init__(self, parent: QWidget | None = None):
        """
        Initialize the TMDB progress dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Set dialog properties
        self.setWindowTitle("TMDB Matching Progress")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setMinimumHeight(150)

        # Initialize progress properties
        self.setRange(0, 100)
        self.setValue(0)
        self.setMinimumDuration(0)  # Show immediately

        # Customize dialog
        self._setup_ui()

        # Connect cancel signal
        self.canceled.connect(self._on_cancel_clicked)

        logger.info("TMDBProgressDialog initialized")

    def _setup_ui(self) -> None:
        """Set up the custom UI elements."""
        # Set initial label text
        self.setLabelText(ProgressMessages.PREPARING_TMDB)

        # Add custom status label
        self.status_label = QLabel(ProgressMessages.INITIALIZING_TMDB)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("statusLabel")

        # Add status label to the dialog
        # Note: QProgressDialog doesn't have a direct way to add custom widgets
        # We'll use the label text to show detailed status
        self.setLabelText(ProgressMessages.PREPARING_TMDB)

        # Customize cancel button text
        self.setCancelButtonText(ButtonTexts.CANCEL_MATCHING)

    def update_progress(self, value: int, status_message: str = "") -> None:
        """
        Update the progress dialog with new value and status.

        Args:
            value: Progress value (0-100)
            status_message: Optional status message to display
        """
        self.setValue(value)

        if status_message:
            self.setLabelText(status_message)
            logger.debug("Progress updated: %d%% - %s", value, status_message)
        # Default status based on progress
        elif value == 0:
            self.setLabelText(ProgressMessages.STARTING_TMDB)
        elif value < 100:
            self.setLabelText(ProgressMessages.MATCHING_IN_PROGRESS.format(percent=value))
        else:
            self.setLabelText(ProgressMessages.MATCHING_COMPLETE)

    def update_file_status(
        self,
        current_file: str,
        total_files: int,
        current_index: int,
    ) -> None:
        """
        Update the dialog with current file information.

        Args:
            current_file: Name of the current file being processed
            total_files: Total number of files to process
            current_index: Current file index (0-based)
        """
        progress = (
            int((current_index + 1) * 100 / total_files) if total_files > 0 else 0
        )

        # Truncate long filenames for display
        display_name = Path(current_file).name
        if len(display_name) > 40:
            display_name = display_name[:37] + "..."

        status_text = f"Processing: {display_name} ({current_index + 1}/{total_files})"
        self.update_progress(progress, status_text)

    def show_error(self, error_message: str) -> None:
        """
        Show an error message in the dialog.

        Args:
            error_message: Error message to display
        """
        self.setLabelText(f"Error: {error_message}")
        self.setValue(0)  # Reset progress
        logger.error("Progress dialog error: %s", error_message)

    def show_completion(self, total_matched: int, total_files: int) -> None:
        """
        Show completion message with statistics.

        Args:
            total_matched: Number of successfully matched files
            total_files: Total number of files processed
        """
        self.setValue(100)
        self.setLabelText(f"Completed! {total_matched}/{total_files} files matched")
        self.setCancelButtonText("Close")

        # Auto-close after 3 seconds
        QTimer.singleShot(3000, self.accept)

        logger.info(
            "TMDB matching completed: %d/%d files matched",
            total_matched,
            total_files,
        )

    def _on_cancel_clicked(self) -> None:
        """Handle cancel button clicked."""
        self.setLabelText("Cancelling TMDB matching...")
        self.setCancelButtonText("Cancelling...")
        self.canceled.disconnect()  # Prevent multiple cancel signals

        logger.info("TMDB matching cancelled by user")
        self.cancelled.emit()

    def reset(self) -> None:
        """Reset the dialog to initial state."""
        self.setValue(0)
        self.setLabelText("Preparing TMDB matching...")
        self.setCancelButtonText("Cancel Matching")

        # Reconnect cancel signal
        self.canceled.connect(self._on_cancel_clicked)

        logger.debug("TMDB progress dialog reset")
