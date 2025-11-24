"""Organize Event Handler for file organization operations.

This module contains the OrganizeEventHandler class that handles events emitted
by the OrganizeController. It processes organization plan generation, execution
progress, and completion events.

The handler follows the BaseEventHandler pattern for consistent status messages
and error handling across the application.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QMessageBox

from anivault.core.models import FileOperation
from anivault.core.organizer.executor import OperationResult
from anivault.gui.controllers.organize_controller import OrganizeController
from anivault.gui.controllers.scan_controller import ScanController
from anivault.gui.dialogs.organize_progress_dialog import OrganizeProgressDialog
from anivault.gui.managers.status_manager import StatusManager
from anivault.gui.state_model import StateModel
from anivault.shared.constants.gui_messages import DialogTitles

from .base_event_handler import BaseEventHandler


class OrganizeEventHandler(BaseEventHandler):
    """Handler for file organization events from OrganizeController.

    This handler processes all organization lifecycle events including plan
    generation, execution progress, and completion. It maintains separation
    of concerns by using callbacks for workflow orchestration.

    Attributes:
        _state_model: StateModel instance for managing application state
        _scan_controller: ScanController for triggering directory rescans
        _organize_controller: OrganizeController for accessing organization state
        _organize_progress_dialog: Optional OrganizeProgressDialog for progress display
        _show_preview_callback: Callback to show organization preview dialog
        _execute_plan_callback: Callback to execute organization plan

    Example:
        >>> handler = OrganizeEventHandler(
        ...     status_manager=status_mgr,
        ...     state_model=state_mdl,
        ...     scan_controller=scan_ctrl,
        ...     organize_controller=org_ctrl,
        ...     show_preview_callback=main_window.show_organize_preview,
        ...     execute_plan_callback=main_window.execute_organize_plan
        ... )
        >>> org_controller.plan_generated.connect(handler.on_plan_generated)
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        status_manager: StatusManager,
        state_model: StateModel,
        scan_controller: ScanController,
        organize_controller: OrganizeController,
        organize_progress_dialog: OrganizeProgressDialog | None = None,
        show_preview_callback: Callable[[list[FileOperation]], None] | None = None,
        execute_plan_callback: Callable[[list[FileOperation]], None] | None = None,
    ) -> None:
        """Initialize the organize event handler.

        Args:
            status_manager: StatusManager for displaying status messages
            state_model: StateModel for managing application state
            scan_controller: ScanController for triggering directory rescans
            organize_controller: OrganizeController for organization operations
            organize_progress_dialog: Optional OrganizeProgressDialog for progress
            show_preview_callback: Callback to show organization preview dialog
            execute_plan_callback: Callback to execute organization plan
        """
        super().__init__(status_manager)
        self._state_model = state_model
        self._scan_controller = scan_controller
        self._organize_controller = organize_controller
        self._organize_progress_dialog = organize_progress_dialog
        self._show_preview_callback = show_preview_callback
        self._execute_plan_callback = execute_plan_callback
        self._current_plan: list[FileOperation] | None = None

    def set_progress_dialog(self, dialog: OrganizeProgressDialog | None) -> None:
        """Set the progress dialog instance.

        This allows updating the dialog reference after handler creation,
        useful when the dialog is created on-demand.

        Args:
            dialog: OrganizeProgressDialog instance or None to clear
        """
        self._organize_progress_dialog = dialog

    def on_plan_generated(self, plan: list[FileOperation]) -> None:
        """Handle organization plan generated signal.

        Processes the generated organization plan by showing a preview dialog
        to the user. If the user accepts, the plan is executed.

        Args:
            plan: List of FileOperation objects describing the organization plan
        """
        if not plan:
            QMessageBox.information(
                None,
                "정리 불필요",
                "모든 파일이 이미 올바른 위치에 있습니다.",
            )
            return

        # Store current plan
        self._current_plan = plan

        # Show preview via callback
        if self._show_preview_callback:
            self._show_preview_callback(plan)
        else:
            self._logger.warning("No preview callback configured")

    def on_organization_started(self) -> None:
        """Handle organization started signal.

        Displays a status message indicating that organization has begun.
        """
        self._show_status("파일 정리 시작...")

    def on_file_organized(self, result: OperationResult) -> None:
        """Handle file organized signal (NO Any!).

        Processes individual file organization results and updates the
        progress dialog if available.

        Args:
            result: Dictionary containing:
                - source: Source file path
                - destination: Destination file path
                - success: Whether operation succeeded
                - error: Error message if failed
        """
        success = result.success
        source = result.source_path

        if success:
            self._logger.debug("File organized: %s", source)
        else:
            error = result.message or "Unknown error"
            self._logger.error("File organization failed: %s - %s", source, error)

        # Update progress dialog if available
        if self._organize_progress_dialog:
            # Convert OperationResult to dict for dialog (legacy interface)
            result_dict = {
                "success": str(result.success),
                "source": result.source_path,
                "destination": result.destination_path,
                "error": result.message or "",
            }
            self._organize_progress_dialog.add_file_result(result_dict)

    def on_organization_progress(self, progress: int, filename: str) -> None:
        """Handle organization progress signal.

        Updates the progress dialog and status bar with current progress.

        Args:
            progress: Organization progress percentage (0-100)
            filename: Name of the file currently being processed
        """
        if self._organize_progress_dialog:
            self._organize_progress_dialog.update_progress(progress, filename)

        self._show_status(f"파일 정리 중... {progress}% ({filename})")

    def on_organization_finished(self, results: list[OperationResult]) -> None:
        """Handle organization finished signal.

        Processes organization completion by:
        1. Displaying completion status in the progress dialog
        2. Triggering a directory rescan to update the file list
        3. Showing a completion message

        Args:
            results: List of organization operation results
        """
        if not self._current_plan:
            self._logger.warning("No plan available for completion handling")
            return

        # Show completion in progress dialog
        if self._organize_progress_dialog:
            success_count = len([r for r in results if r.success])
            total_count = len(self._current_plan)
            self._organize_progress_dialog.show_completion(
                success_count,
                total_count,
            )

        # Trigger directory rescan
        self._rescan_after_organization(self._current_plan)

        self._logger.info(
            "Organization completed: %d operations",
            len(self._current_plan),
        )

    def on_organization_error(self, error_msg: str) -> None:
        """Handle organization error signal.

        Processes organization errors by displaying both a status message
        and an error dialog to the user, and updating the progress dialog.

        Args:
            error_msg: Error message describing what went wrong
        """
        if self._organize_progress_dialog:
            self._organize_progress_dialog.show_error(error_msg)

        self._logger.error("Organization error: %s", error_msg)
        self._show_error(
            f"파일 정리 중 오류 발생:\n{error_msg}",
            DialogTitles.ORGANIZE_ERROR,
        )

    def on_organization_cancelled(self) -> None:
        """Handle organization cancellation signal.

        Displays a cancellation message to the user.
        """
        if self._organize_progress_dialog:
            self._organize_progress_dialog.show_error("사용자에 의해 취소되었습니다.")

        self._show_status("파일 정리가 취소되었습니다.")
        self._logger.info("Organization cancelled by user")

    def _rescan_after_organization(self, plan: list[FileOperation]) -> None:
        """Rescan source directory after file organization.

        This method triggers a fresh scan of the source directory to update
        the file list, removing organized files and showing any new files.

        Args:
            plan: List of FileOperation objects that were executed
        """
        # Get the source directory from the current state
        source_directory = self._state_model.selected_directory

        if not source_directory:
            self._logger.warning("No source directory set, cannot rescan")
            return

        removed_count = len(plan)

        self._logger.info(
            "Rescanning source directory after organizing %d files: %s",
            removed_count,
            source_directory,
        )

        # Update status bar with rescanning message
        self._show_status("파일 정리 완료, 디렉토리 다시 스캔 중...")

        # Trigger a fresh scan of the directory
        self._scan_controller.scan_directory(source_directory)
