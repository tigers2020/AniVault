"""Unit tests for OrganizeEventHandler.

This module tests the OrganizeEventHandler class, which processes file organization
events from the OrganizeController. Tests cover all event handlers and verify
proper integration with dependencies.
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from anivault.gui.handlers.organize_event_handler import OrganizeEventHandler


class TestOrganizeEventHandlerInit:
    """Tests for OrganizeEventHandler initialization."""

    def test_init_with_all_dependencies(self) -> None:
        """Test initialization with all required dependencies."""
        status_manager = Mock()
        state_model = Mock()
        scan_controller = Mock()
        organize_controller = Mock()
        organize_progress_dialog = Mock()
        show_preview_callback = Mock()
        execute_plan_callback = Mock()

        handler = OrganizeEventHandler(
            status_manager=status_manager,
            state_model=state_model,
            scan_controller=scan_controller,
            organize_controller=organize_controller,
            organize_progress_dialog=organize_progress_dialog,
            show_preview_callback=show_preview_callback,
            execute_plan_callback=execute_plan_callback,
        )

        assert handler._status_manager is status_manager
        assert handler._state_model is state_model
        assert handler._scan_controller is scan_controller
        assert handler._organize_controller is organize_controller
        assert handler._organize_progress_dialog is organize_progress_dialog
        assert handler._show_preview_callback is show_preview_callback
        assert handler._execute_plan_callback is execute_plan_callback

    def test_init_with_optional_dependencies(self) -> None:
        """Test initialization with optional dependencies set to None."""
        status_manager = Mock()
        state_model = Mock()
        scan_controller = Mock()
        organize_controller = Mock()

        handler = OrganizeEventHandler(
            status_manager=status_manager,
            state_model=state_model,
            scan_controller=scan_controller,
            organize_controller=organize_controller,
        )

        assert handler._status_manager is status_manager
        assert handler._state_model is state_model
        assert handler._scan_controller is scan_controller
        assert handler._organize_controller is organize_controller
        assert handler._organize_progress_dialog is None
        assert handler._show_preview_callback is None
        assert handler._execute_plan_callback is None


class TestSetProgressDialog:
    """Tests for set_progress_dialog method."""

    def test_set_progress_dialog(self) -> None:
        """Test setting progress dialog after initialization."""
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
        )

        dialog = Mock()
        handler.set_progress_dialog(dialog)

        assert handler._organize_progress_dialog is dialog

    def test_clear_progress_dialog(self) -> None:
        """Test clearing progress dialog by setting to None."""
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
            organize_progress_dialog=Mock(),
        )

        handler.set_progress_dialog(None)

        assert handler._organize_progress_dialog is None


class TestOnPlanGenerated:
    """Tests for on_plan_generated handler."""

    @patch("anivault.gui.handlers.organize_event_handler.QMessageBox")
    def test_on_plan_generated_with_empty_plan(
        self,
        mock_messagebox: Mock,
    ) -> None:
        """Test plan generated with empty plan shows info message."""
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
        )

        handler.on_plan_generated([])

        mock_messagebox.information.assert_called_once()
        assert "정리 불필요" in str(mock_messagebox.information.call_args)

    def test_on_plan_generated_with_plan_calls_callback(self) -> None:
        """Test plan generated with valid plan calls preview callback."""
        show_preview_callback = Mock()
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
            show_preview_callback=show_preview_callback,
        )

        plan = [Mock(), Mock(), Mock()]
        handler.on_plan_generated(plan)

        show_preview_callback.assert_called_once_with(plan)
        assert handler._current_plan == plan

    def test_on_plan_generated_without_callback(self) -> None:
        """Test plan generated without callback logs warning."""
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
        )

        plan = [Mock(), Mock()]

        # Should not raise error
        handler.on_plan_generated(plan)


class TestOnOrganizationStarted:
    """Tests for on_organization_started handler."""

    @patch.object(OrganizeEventHandler, "_show_status")
    def test_on_organization_started_shows_status(
        self,
        mock_show_status: Mock,
    ) -> None:
        """Test that organization started shows status message."""
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
        )

        handler.on_organization_started()

        mock_show_status.assert_called_once_with("파일 정리 시작...")


class TestOnFileOrganized:
    """Tests for on_file_organized handler."""

    def test_on_file_organized_success(self) -> None:
        """Test file organized with successful result."""
        dialog = Mock()
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
            organize_progress_dialog=dialog,
        )

        from anivault.core.organizer.executor import OperationResult

        result = OperationResult(
            operation="move",
            source_path="/path/to/source.mkv",
            destination_path="/path/to/dest.mkv",
            success=True,
        )

        handler.on_file_organized(result)

        # Verify dialog called with dict conversion
        dialog.add_file_result.assert_called_once()
        call_dict = dialog.add_file_result.call_args[0][0]
        assert call_dict["source"] == "/path/to/source.mkv"
        assert call_dict["destination"] == "/path/to/dest.mkv"
        assert call_dict["success"] == "True"

    def test_on_file_organized_failure(self) -> None:
        """Test file organized with failed result."""
        dialog = Mock()
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
            organize_progress_dialog=dialog,
        )

        from anivault.core.organizer.executor import OperationResult

        result = OperationResult(
            operation="move",
            source_path="/path/to/source.mkv",
            destination_path="/path/to/dest.mkv",
            success=False,
            message="Permission denied",
        )

        handler.on_file_organized(result)

        # Verify dialog called with dict conversion
        dialog.add_file_result.assert_called_once()
        call_dict = dialog.add_file_result.call_args[0][0]
        assert call_dict["source"] == "/path/to/source.mkv"
        assert call_dict["success"] == "False"
        assert call_dict["error"] == "Permission denied"

    def test_on_file_organized_without_dialog(self) -> None:
        """Test file organized when dialog is not set."""
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
        )

        from anivault.core.organizer.executor import OperationResult

        result = OperationResult(
            operation="move",
            source_path="/path/to/source.mkv",
            destination_path="",
            success=True,
        )

        # Should not raise error
        handler.on_file_organized(result)


class TestOnOrganizationProgress:
    """Tests for on_organization_progress handler."""

    @patch.object(OrganizeEventHandler, "_show_status")
    def test_on_organization_progress_updates_dialog_and_status(
        self,
        mock_show_status: Mock,
    ) -> None:
        """Test that progress updates both dialog and status bar."""
        dialog = Mock()
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
            organize_progress_dialog=dialog,
        )

        handler.on_organization_progress(50, "test_file.mkv")

        dialog.update_progress.assert_called_once_with(50, "test_file.mkv")
        mock_show_status.assert_called_once()
        assert "50%" in mock_show_status.call_args[0][0]
        assert "test_file.mkv" in mock_show_status.call_args[0][0]

    @patch.object(OrganizeEventHandler, "_show_status")
    def test_on_organization_progress_without_dialog(
        self,
        mock_show_status: Mock,
    ) -> None:
        """Test progress update when dialog is not set."""
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
        )

        handler.on_organization_progress(75, "another_file.mkv")

        # Should still update status bar
        mock_show_status.assert_called_once()


class TestOnOrganizationFinished:
    """Tests for on_organization_finished handler."""

    @patch.object(OrganizeEventHandler, "_rescan_after_organization")
    def test_on_organization_finished_with_results(
        self,
        mock_rescan: Mock,
    ) -> None:
        """Test organization finished with successful results."""
        dialog = Mock()
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
            organize_progress_dialog=dialog,
        )

        # Set current plan
        from anivault.core.organizer.executor import OperationResult

        plan = [Mock(), Mock(), Mock()]
        handler._current_plan = plan

        results = [
            OperationResult(
                operation="move",
                source_path="/path/1.mkv",
                destination_path="/dest/1.mkv",
                success=True,
            ),
            OperationResult(
                operation="move",
                source_path="/path/2.mkv",
                destination_path="/dest/2.mkv",
                success=True,
            ),
            OperationResult(
                operation="move",
                source_path="/path/3.mkv",
                destination_path="/dest/3.mkv",
                success=False,
                message="Error",
            ),
        ]

        handler.on_organization_finished(results)

        # Verify dialog updated with success count
        dialog.show_completion.assert_called_once_with(2, 3)

        # Verify rescan triggered
        mock_rescan.assert_called_once_with(plan)

    @patch.object(OrganizeEventHandler, "_rescan_after_organization")
    def test_on_organization_finished_without_plan(
        self,
        mock_rescan: Mock,
    ) -> None:
        """Test organization finished when no plan is available."""
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
        )

        results = [{"success": True}]

        # Should not raise error
        handler.on_organization_finished(results)

        # Should not call rescan
        mock_rescan.assert_not_called()


class TestOnOrganizationError:
    """Tests for on_organization_error handler."""

    @patch.object(OrganizeEventHandler, "_show_error")
    def test_on_organization_error_shows_error_dialog(
        self,
        mock_show_error: Mock,
    ) -> None:
        """Test that organization error shows error dialog and updates progress dialog."""
        dialog = Mock()
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
            organize_progress_dialog=dialog,
        )

        error_msg = "File system error"
        handler.on_organization_error(error_msg)

        dialog.show_error.assert_called_once_with(error_msg)
        mock_show_error.assert_called_once()
        assert "파일 정리 중 오류 발생" in mock_show_error.call_args[0][0]
        assert error_msg in mock_show_error.call_args[0][0]

    @patch.object(OrganizeEventHandler, "_show_error")
    def test_on_organization_error_without_dialog(
        self,
        mock_show_error: Mock,
    ) -> None:
        """Test organization error when dialog is not set."""
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
        )

        error_msg = "Network error"
        handler.on_organization_error(error_msg)

        # Should still show error dialog
        mock_show_error.assert_called_once()


class TestOnOrganizationCancelled:
    """Tests for on_organization_cancelled handler."""

    @patch.object(OrganizeEventHandler, "_show_status")
    def test_on_organization_cancelled_updates_dialog(
        self,
        mock_show_status: Mock,
    ) -> None:
        """Test that cancellation updates progress dialog."""
        dialog = Mock()
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
            organize_progress_dialog=dialog,
        )

        handler.on_organization_cancelled()

        dialog.show_error.assert_called_once_with("사용자에 의해 취소되었습니다.")
        mock_show_status.assert_called_once_with("파일 정리가 취소되었습니다.")

    @patch.object(OrganizeEventHandler, "_show_status")
    def test_on_organization_cancelled_without_dialog(
        self,
        mock_show_status: Mock,
    ) -> None:
        """Test cancellation when dialog is not set."""
        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            scan_controller=Mock(),
            organize_controller=Mock(),
        )

        # Should not raise error
        handler.on_organization_cancelled()

        mock_show_status.assert_called_once_with("파일 정리가 취소되었습니다.")


class TestRescanAfterOrganization:
    """Tests for _rescan_after_organization method."""

    @patch.object(OrganizeEventHandler, "_show_status")
    def test_rescan_triggers_scan_controller(
        self,
        mock_show_status: Mock,
    ) -> None:
        """Test that rescan triggers scan controller with correct directory."""
        state_model = Mock()
        state_model.selected_directory = "/test/directory"
        scan_controller = Mock()

        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=state_model,
            scan_controller=scan_controller,
            organize_controller=Mock(),
        )

        plan = [Mock(), Mock(), Mock()]
        handler._rescan_after_organization(plan)

        scan_controller.scan_directory.assert_called_once_with("/test/directory")
        mock_show_status.assert_called_once()
        assert "디렉토리 다시 스캔 중" in mock_show_status.call_args[0][0]

    def test_rescan_without_selected_directory(self) -> None:
        """Test rescan when no directory is selected."""
        state_model = Mock()
        state_model.selected_directory = None
        scan_controller = Mock()

        handler = OrganizeEventHandler(
            status_manager=Mock(),
            state_model=state_model,
            scan_controller=scan_controller,
            organize_controller=Mock(),
        )

        plan = [Mock(), Mock()]
        handler._rescan_after_organization(plan)

        # Should not trigger scan
        scan_controller.scan_directory.assert_not_called()
