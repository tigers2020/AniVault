"""Unit tests for TMDBEventHandler.

This module tests the TMDBEventHandler class, which processes TMDB matching
events from the TMDBController. Tests cover all event handlers and verify
proper integration with dependencies.
"""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from anivault.gui.handlers.tmdb_event_handler import TMDBEventHandler


class TestTMDBEventHandlerInit:
    """Tests for TMDBEventHandler initialization."""

    def test_init_with_all_dependencies(self) -> None:
        """Test initialization with all required dependencies."""
        status_manager = Mock()
        state_model = Mock()
        tmdb_controller = Mock()
        tmdb_progress_dialog = Mock()
        enable_callback = Mock()
        regroup_callback = Mock()

        handler = TMDBEventHandler(
            status_manager=status_manager,
            state_model=state_model,
            tmdb_controller=tmdb_controller,
            tmdb_progress_dialog=tmdb_progress_dialog,
            enable_organize_callback=enable_callback,
            regroup_callback=regroup_callback,
        )

        assert handler._status_manager is status_manager
        assert handler._state_model is state_model
        assert handler._tmdb_controller is tmdb_controller
        assert handler._tmdb_progress_dialog is tmdb_progress_dialog
        assert handler._enable_organize_callback is enable_callback
        assert handler._regroup_callback is regroup_callback

    def test_init_with_optional_dependencies(self) -> None:
        """Test initialization with optional dependencies set to None."""
        status_manager = Mock()
        state_model = Mock()
        tmdb_controller = Mock()

        handler = TMDBEventHandler(
            status_manager=status_manager,
            state_model=state_model,
            tmdb_controller=tmdb_controller,
        )

        assert handler._status_manager is status_manager
        assert handler._state_model is state_model
        assert handler._tmdb_controller is tmdb_controller
        assert handler._tmdb_progress_dialog is None
        assert handler._enable_organize_callback is None
        assert handler._regroup_callback is None


class TestSetProgressDialog:
    """Tests for set_progress_dialog method."""

    def test_set_progress_dialog(self) -> None:
        """Test setting progress dialog after initialization."""
        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=Mock(),
        )

        dialog = Mock()
        handler.set_progress_dialog(dialog)

        assert handler._tmdb_progress_dialog is dialog

    def test_clear_progress_dialog(self) -> None:
        """Test clearing progress dialog by setting to None."""
        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=Mock(),
            tmdb_progress_dialog=Mock(),
        )

        handler.set_progress_dialog(None)

        assert handler._tmdb_progress_dialog is None


class TestOnTMDBMatchingStarted:
    """Tests for on_tmdb_matching_started handler."""

    @patch.object(TMDBEventHandler, "_show_status")
    def test_on_tmdb_matching_started_shows_status(
        self,
        mock_show_status: MagicMock,
    ) -> None:
        """Test that matching started shows status message."""
        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=Mock(),
        )

        handler.on_tmdb_matching_started()

        mock_show_status.assert_called_once_with("TMDB matching started...")


class TestOnTMDBFileMatched:
    """Tests for on_tmdb_file_matched handler."""

    def test_on_tmdb_file_matched_updates_state_model(self) -> None:
        """Test that file matched updates state model with status and metadata."""
        from pathlib import Path

        from anivault.gui.models import FileItem
        from anivault.shared.metadata_models import FileMetadata

        # Create FileItem with matching path
        file_item = FileItem(file_path=Path("/path/to/file.mkv"), status="scanned")

        state_model = Mock()
        state_model._scanned_files = [
            file_item
        ]  # Real list for iteration (direct access)

        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=state_model,
            tmdb_controller=Mock(),
        )

        result = FileMetadata(
            file_path=Path("/path/to/file.mkv"),
            file_type="mkv",
            title="Test Anime",
            tmdb_id=12345,
        )

        handler.on_tmdb_file_matched(result)

        # Verify state model updated
        state_model.update_file_status.assert_called_once_with(
            Path("/path/to/file.mkv"),
            "matched",
        )

        # Verify FileItem metadata was updated directly (NO dict!)
        assert file_item.metadata == result

    def test_on_tmdb_file_matched_without_match_result(self) -> None:
        """Test file matched when no match result is available."""
        from pathlib import Path

        from anivault.gui.models import FileItem
        from anivault.shared.metadata_models import FileMetadata

        file_item = FileItem(file_path=Path("/path/to/file.mkv"), status="scanned")

        state_model = Mock()
        state_model._scanned_files = [file_item]  # Direct access

        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=state_model,
            tmdb_controller=Mock(),
        )

        result = FileMetadata(
            file_path=Path("/path/to/file.mkv"),
            file_type="mkv",
            title="Test File",  # title cannot be empty
            tmdb_id=None,  # No match - this is what matters
        )

        handler.on_tmdb_file_matched(result)

        # Verify only status updated to "unknown" (when tmdb_id is None)
        state_model.update_file_status.assert_called_once_with(
            Path("/path/to/file.mkv"),
            "unknown",
        )

        # FileItem metadata should still be updated with the result (even without match)
        assert file_item.metadata == result

    def test_on_tmdb_file_matched_with_missing_fields(self) -> None:
        """Test file matched with missing dictionary fields."""
        from pathlib import Path

        from anivault.gui.models import FileItem
        from anivault.shared.metadata_models import FileMetadata

        file_item = FileItem(file_path=Path("unknown.mkv"), status="scanned")

        state_model = Mock()
        state_model._scanned_files = [file_item]  # Direct access

        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=state_model,
            tmdb_controller=Mock(),
        )

        result = FileMetadata(
            file_path=Path("unknown.mkv"),
            file_type="mkv",
            title="Unknown",  # Empty title would fail validation
            tmdb_id=None,
        )

        handler.on_tmdb_file_matched(result)

        # Verify defaults used
        state_model.update_file_status.assert_called_once()
        call_args = state_model.update_file_status.call_args
        assert call_args[0][1] == "unknown"  # Default status


class TestOnTMDBMatchingProgress:
    """Tests for on_tmdb_matching_progress handler."""

    @patch.object(TMDBEventHandler, "_show_status")
    def test_on_tmdb_matching_progress_updates_dialog_and_status(
        self,
        mock_show_status: MagicMock,
    ) -> None:
        """Test that progress updates both dialog and status bar."""
        dialog = Mock()
        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=Mock(),
            tmdb_progress_dialog=dialog,
        )

        handler.on_tmdb_matching_progress(50)

        dialog.update_progress.assert_called_once_with(50)
        mock_show_status.assert_called_once_with("TMDB matching... 50%")

    @patch.object(TMDBEventHandler, "_show_status")
    def test_on_tmdb_matching_progress_without_dialog(
        self,
        mock_show_status: MagicMock,
    ) -> None:
        """Test progress update when dialog is not set."""
        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=Mock(),
        )

        handler.on_tmdb_matching_progress(75)

        # Should still update status bar
        mock_show_status.assert_called_once_with("TMDB matching... 75%")


class TestOnTMDBMatchingFinished:
    """Tests for on_tmdb_matching_finished handler."""

    @patch.object(TMDBEventHandler, "_show_status")
    def test_on_tmdb_matching_finished_with_matches(
        self,
        mock_show_status: MagicMock,
    ) -> None:
        """Test matching finished with successful matches."""
        dialog = Mock()
        controller = Mock()
        controller.get_matched_files_count.return_value = 10
        controller.get_total_files_count.return_value = 15
        enable_callback = Mock()
        regroup_callback = Mock()

        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=controller,
            tmdb_progress_dialog=dialog,
            enable_organize_callback=enable_callback,
            regroup_callback=regroup_callback,
        )

        handler.on_tmdb_matching_finished([])

        # Verify dialog updated
        dialog.show_completion.assert_called_once_with(10, 15)

        # Verify status message
        mock_show_status.assert_called_once_with(
            "TMDB matching completed: 10/15 matched"
        )

        # Verify organize enabled and regrouped
        enable_callback.assert_called_once()
        regroup_callback.assert_called_once()

    @patch.object(TMDBEventHandler, "_show_status")
    def test_on_tmdb_matching_finished_with_no_matches(
        self,
        mock_show_status: MagicMock,
    ) -> None:
        """Test matching finished with no matches."""
        controller = Mock()
        controller.get_matched_files_count.return_value = 0
        controller.get_total_files_count.return_value = 15
        enable_callback = Mock()
        regroup_callback = Mock()

        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=controller,
            enable_organize_callback=enable_callback,
            regroup_callback=regroup_callback,
        )

        handler.on_tmdb_matching_finished([])

        # Verify organize NOT enabled
        enable_callback.assert_not_called()

        # Verify still regrouped
        regroup_callback.assert_called_once()

    @patch.object(TMDBEventHandler, "_show_status")
    def test_on_tmdb_matching_finished_without_callbacks(
        self,
        mock_show_status: MagicMock,
    ) -> None:
        """Test matching finished when callbacks are not provided."""
        controller = Mock()
        controller.get_matched_files_count.return_value = 5
        controller.get_total_files_count.return_value = 10

        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=controller,
        )

        # Should not raise error
        handler.on_tmdb_matching_finished([])

        mock_show_status.assert_called_once()


class TestOnTMDBMatchingError:
    """Tests for on_tmdb_matching_error handler."""

    @patch.object(TMDBEventHandler, "_show_error")
    def test_on_tmdb_matching_error_shows_error_dialog(
        self,
        mock_show_error: MagicMock,
    ) -> None:
        """Test that matching error shows error dialog and updates progress dialog."""
        dialog = Mock()
        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=Mock(),
            tmdb_progress_dialog=dialog,
        )

        error_msg = "API rate limit exceeded"
        handler.on_tmdb_matching_error(error_msg)

        dialog.show_error.assert_called_once_with(error_msg)
        mock_show_error.assert_called_once()
        assert "Failed to match files" in mock_show_error.call_args[0][0]
        assert error_msg in mock_show_error.call_args[0][0]

    @patch.object(TMDBEventHandler, "_show_error")
    def test_on_tmdb_matching_error_without_dialog(
        self,
        mock_show_error: MagicMock,
    ) -> None:
        """Test matching error when dialog is not set."""
        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=Mock(),
        )

        error_msg = "Network error"
        handler.on_tmdb_matching_error(error_msg)

        # Should still show error dialog
        mock_show_error.assert_called_once()


class TestOnTMDBMatchingCancelled:
    """Tests for on_tmdb_matching_cancelled handler."""

    @patch.object(TMDBEventHandler, "_show_status")
    def test_on_tmdb_matching_cancelled_closes_dialog(
        self,
        mock_show_status: MagicMock,
    ) -> None:
        """Test that cancellation closes progress dialog."""
        dialog = Mock()
        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=Mock(),
            tmdb_progress_dialog=dialog,
        )

        handler.on_tmdb_matching_cancelled()

        dialog.close.assert_called_once()
        assert handler._tmdb_progress_dialog is None
        mock_show_status.assert_called_once_with("TMDB matching cancelled")

    @patch.object(TMDBEventHandler, "_show_status")
    def test_on_tmdb_matching_cancelled_without_dialog(
        self,
        mock_show_status: MagicMock,
    ) -> None:
        """Test cancellation when dialog is not set."""
        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=Mock(),
        )

        # Should not raise error
        handler.on_tmdb_matching_cancelled()

        mock_show_status.assert_called_once_with("TMDB matching cancelled")


class TestOnProgressDialogCancelled:
    """Tests for on_progress_dialog_cancelled handler."""

    def test_on_progress_dialog_cancelled_stops_matching(self) -> None:
        """Test that progress dialog cancellation stops matching."""
        controller = Mock()
        controller.is_matching = True

        handler = TMDBEventHandler(
            status_manager=Mock(),
            state_model=Mock(),
            tmdb_controller=controller,
        )

        handler.on_progress_dialog_cancelled()

        controller.cancel_matching.assert_called_once()
        assert controller.is_matching is False
