"""TMDB Event Handler for TMDB matching operations.

This module contains the TMDBEventHandler class that handles events emitted
by the TMDBController. It processes TMDB matching lifecycle events (started,
progress, finished, error, cancelled) and individual file match results.

The handler follows the BaseEventHandler pattern for consistent status messages
and error handling across the application.
"""

from __future__ import annotations

from typing import Callable

from anivault.gui.controllers.tmdb_controller import TMDBController
from anivault.gui.dialogs.tmdb_progress_dialog import TMDBProgressDialog
from anivault.gui.managers.status_manager import StatusManager
from anivault.gui.state_model import StateModel
from anivault.shared.constants.gui_messages import DialogTitles
from anivault.shared.models.metadata import FileMetadata

from .base_event_handler import BaseEventHandler


class TMDBEventHandler(BaseEventHandler):
    """Handler for TMDB matching events from TMDBController.

    This handler processes all TMDB matching lifecycle events and updates
    the UI accordingly. It maintains separation of concerns by using callbacks
    for workflow orchestration.

    Attributes:
        _state_model: StateModel instance for managing file state and metadata
        _tmdb_controller: TMDBController instance for accessing match results
        _tmdb_progress_dialog: Optional TMDBProgressDialog for progress display
        _enable_organize_callback: Callback to enable organize button
        _regroup_callback: Callback to regroup files by TMDB title

    Example:
        >>> handler = TMDBEventHandler(
        ...     status_manager=status_mgr,
        ...     state_model=state_mdl,
        ...     tmdb_controller=tmdb_ctrl,
        ...     tmdb_progress_dialog=progress_dlg,
        ...     enable_organize_callback=main_window.enable_organize_action,
        ...     regroup_callback=main_window._regroup_by_tmdb_title
        ... )
        >>> tmdb_controller.matching_started.connect(handler.on_tmdb_matching_started)
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        status_manager: StatusManager,
        state_model: StateModel,
        tmdb_controller: TMDBController,
        tmdb_progress_dialog: TMDBProgressDialog | None = None,
        enable_organize_callback: Callable[[], None] | None = None,
        regroup_callback: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the TMDB event handler.

        Args:
            status_manager: StatusManager for displaying status messages
            state_model: StateModel for managing file state and metadata
            tmdb_controller: TMDBController for accessing match results
            tmdb_progress_dialog: Optional TMDBProgressDialog for progress display
            enable_organize_callback: Callback to enable organize button after matching
            regroup_callback: Callback to regroup files by TMDB title
        """
        super().__init__(status_manager)
        self._state_model = state_model
        self._tmdb_controller = tmdb_controller
        self._tmdb_progress_dialog = tmdb_progress_dialog
        self._enable_organize_callback = enable_organize_callback
        self._regroup_callback = regroup_callback

    def set_progress_dialog(self, dialog: TMDBProgressDialog | None) -> None:
        """Set the progress dialog instance.

        This allows updating the dialog reference after handler creation,
        useful when the dialog is created on-demand.

        Args:
            dialog: TMDBProgressDialog instance or None to clear
        """
        self._tmdb_progress_dialog = dialog

    def on_tmdb_matching_started(self) -> None:
        """Handle TMDB matching started signal.

        Displays a status message indicating that matching has begun.
        """
        self._show_status("TMDB matching started...")

    def on_tmdb_file_matched(self, result: FileMetadata) -> None:
        """Handle TMDB file matched signal (NO Any!).

        Processes individual file match results by updating the state model
        with the match status and metadata.

        Args:
            result: FileMetadata object containing:
                - file_path: Path - Path to the matched file
                - file_name: str - Name of the file
                - tmdb_id: int | None - TMDB ID if matched
                - title: str | None - TMDB title if matched
                - Other TMDB metadata fields
        """
        # FileMetadata is a dataclass, access attributes directly
        file_path = result.file_path
        file_name = file_path.name if file_path else "Unknown"
        status = "matched" if result.tmdb_id is not None else "unknown"

        # Update state model
        if hasattr(self, "_state_model") and self._state_model:
            self._state_model.update_file_status(file_path, status)

            # Save TMDB metadata to FileItem directly (NO dict!)
            # Access _scanned_files directly (not the copy from .scanned_files property)
            if hasattr(self._state_model, "_scanned_files"):
                for file_item in self._state_model._scanned_files:  # pylint: disable=protected-access
                    if file_item.file_path == file_path:
                        file_item.metadata = result  # FileMetadata object directly!
                        self._logger.debug(
                            "Updated FileItem metadata for: %s (tmdb_id=%s, title=%s)",
                            file_name,
                            result.tmdb_id,
                            result.title if result.tmdb_id else "No match",
                        )
                        break

        self._logger.debug("File matched: %s - %s", file_name, status)

    def on_tmdb_matching_progress(self, progress: int) -> None:
        """Handle TMDB matching progress signal.

        Updates both the progress dialog and status bar with current progress.

        Args:
            progress: Matching progress percentage (0-100)
        """
        if self._tmdb_progress_dialog:
            self._tmdb_progress_dialog.update_progress(progress)
        self._show_status(f"TMDB matching... {progress}%")

    def on_tmdb_matching_finished(self, _results: list[object]) -> None:
        """Handle TMDB matching finished signal.

        Processes matching completion by:
        1. Displaying completion status with match counts
        2. Updating the progress dialog
        3. Enabling the organize button if files were matched
        4. Triggering final file regrouping by TMDB title (ensures last batch is updated)

        Args:
            _results: Match results (unused, required by signal signature)
        """
        matched_count = self._tmdb_controller.get_matched_files_count()
        total_count = self._tmdb_controller.get_total_files_count()

        if self._tmdb_progress_dialog:
            self._tmdb_progress_dialog.show_completion(matched_count, total_count)

        self._show_status(f"TMDB matching completed: {matched_count}/{total_count} matched")
        self._logger.info(
            "TMDB matching completed: %d/%d files matched",
            matched_count,
            total_count,
        )

        # Enable organize button if any files matched
        if matched_count > 0 and self._enable_organize_callback:
            self._enable_organize_callback()
            self._logger.debug("Organize button enabled (%d files matched)", matched_count)

        # Update UI with match results - re-group files with updated TMDB metadata
        if self._regroup_callback:
            self._regroup_callback()

    def on_tmdb_matching_error(self, error_msg: str) -> None:
        """Handle TMDB matching error signal.

        Processes matching errors by displaying both a status message and
        an error dialog to the user, and updating the progress dialog.

        Args:
            error_msg: Error message describing what went wrong
        """
        if self._tmdb_progress_dialog:
            self._tmdb_progress_dialog.show_error(error_msg)

        self._logger.error("TMDB matching error: %s", error_msg)
        self._show_error(
            f"Failed to match files:\n{error_msg}",
            DialogTitles.TMDB_ERROR,
        )

    def on_tmdb_matching_cancelled(self) -> None:
        """Handle TMDB matching cancellation signal.

        Cleans up the progress dialog and displays a cancellation message.
        """
        if self._tmdb_progress_dialog:
            self._tmdb_progress_dialog.close()
            self._tmdb_progress_dialog = None

        self._show_status("TMDB matching cancelled")
        self._logger.info("TMDB matching cancelled by user")

    def on_progress_dialog_cancelled(self) -> None:
        """Handle cancellation from the progress dialog.

        This is called when the user cancels matching via the progress dialog.
        It triggers the controller's cancel operation and resets the matching flag.
        """
        self._tmdb_controller.cancel_matching()

        # Ensure is_matching flag is reset to prevent auto-restart
        self._tmdb_controller.is_matching = False
