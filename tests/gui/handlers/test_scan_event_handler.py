"""Tests for ScanEventHandler.

This module tests the scan event handler functionality,
ensuring proper handling of scan lifecycle events.
"""

from pathlib import Path
from unittest.mock import Mock, call, patch

import pytest

from anivault.gui.handlers.scan_event_handler import ScanEventHandler
from anivault.gui.models import FileItem


class TestScanEventHandler:
    """Test cases for ScanEventHandler."""

    @pytest.fixture
    def mock_status_manager(self):
        """Create a mock StatusManager."""
        mock_mgr = Mock()
        mock_mgr.show_message = Mock()
        return mock_mgr

    @pytest.fixture
    def mock_state_model(self):
        """Create a mock StateModel."""
        mock_model = Mock()
        mock_model.add_scanned_files = Mock()
        return mock_model

    @pytest.fixture
    def mock_scan_controller(self):
        """Create a mock ScanController."""
        mock_ctrl = Mock()
        mock_ctrl.group_files = Mock()
        return mock_ctrl

    @pytest.fixture
    def mock_callback(self):
        """Create a mock callback function."""
        return Mock()

    @pytest.fixture
    def handler(
        self, mock_status_manager, mock_state_model, mock_scan_controller, mock_callback
    ):
        """Create a ScanEventHandler instance for testing."""
        return ScanEventHandler(
            status_manager=mock_status_manager,
            state_model=mock_state_model,
            scan_controller=mock_scan_controller,
            update_file_tree_callback=mock_callback,
        )

    @pytest.fixture
    def mock_file_items(self):
        """Create mock FileItem objects."""
        return [
            FileItem(file_path=Path("/test/anime1.mkv"), status="scanned"),
            FileItem(file_path=Path("/test/anime2.mkv"), status="scanned"),
            FileItem(file_path=Path("/test/anime3.mkv"), status="scanned"),
        ]

    def test_initialization(
        self,
        handler,
        mock_status_manager,
        mock_state_model,
        mock_scan_controller,
        mock_callback,
    ):
        """Test ScanEventHandler initialization."""
        assert handler is not None
        assert handler._status_manager is mock_status_manager
        assert handler._state_model is mock_state_model
        assert handler._scan_controller is mock_scan_controller
        assert handler._update_file_tree_callback is mock_callback
        assert handler._logger.name == "ScanEventHandler"

    def test_on_scan_started_shows_status(self, handler, mock_status_manager):
        """Test on_scan_started displays status message."""
        # Act
        handler.on_scan_started()

        # Assert
        mock_status_manager.show_message.assert_called_once_with(
            "Scanning for media files...", 0
        )

    def test_on_scan_progress_shows_progress(self, handler, mock_status_manager):
        """Test on_scan_progress displays progress percentage."""
        # Arrange
        progress = 45

        # Act
        handler.on_scan_progress(progress)

        # Assert
        mock_status_manager.show_message.assert_called_once_with(
            f"Scanning... {progress}%", 0
        )

    def test_on_scan_progress_multiple_updates(self, handler, mock_status_manager):
        """Test on_scan_progress handles multiple progress updates."""
        # Arrange
        progress_values = [0, 25, 50, 75, 100]

        # Act
        for progress in progress_values:
            handler.on_scan_progress(progress)

        # Assert
        assert mock_status_manager.show_message.call_count == len(progress_values)
        calls = [call(f"Scanning... {p}%", 0) for p in progress_values]
        mock_status_manager.show_message.assert_has_calls(calls)

    def test_on_scan_finished_updates_state_model(
        self, handler, mock_state_model, mock_file_items
    ):
        """Test on_scan_finished updates state model with scanned files."""
        # Act
        handler.on_scan_finished(mock_file_items)

        # Assert
        mock_state_model.add_scanned_files.assert_called_once_with(mock_file_items)

    def test_on_scan_finished_shows_completion_message(
        self, handler, mock_status_manager, mock_file_items
    ):
        """Test on_scan_finished displays completion message."""
        # Act
        handler.on_scan_finished(mock_file_items)

        # Assert
        expected_message = f"Scan complete. Found {len(mock_file_items)} files"
        mock_status_manager.show_message.assert_called_with(expected_message, 0)

    def test_on_scan_finished_triggers_grouping(
        self, handler, mock_scan_controller, mock_file_items
    ):
        """Test on_scan_finished triggers file grouping."""
        # Act
        handler.on_scan_finished(mock_file_items)

        # Assert
        mock_scan_controller.group_files.assert_called_once_with(mock_file_items)

    def test_on_scan_finished_no_files_skips_grouping(
        self, handler, mock_scan_controller
    ):
        """Test on_scan_finished skips grouping when no files found."""
        # Arrange
        empty_list = []

        # Act
        handler.on_scan_finished(empty_list)

        # Assert
        mock_scan_controller.group_files.assert_not_called()

    def test_on_scan_finished_grouping_failure(
        self, handler, mock_scan_controller, mock_status_manager, mock_file_items
    ):
        """Test on_scan_finished handles grouping failure gracefully."""
        # Arrange
        mock_scan_controller.group_files.side_effect = ValueError("Grouping failed")

        # Act
        handler.on_scan_finished(mock_file_items)

        # Assert - Should not raise exception
        # Check that error status was shown
        calls = mock_status_manager.show_message.call_args_list
        error_call = [c for c in calls if "Grouping failed" in str(c)]
        assert len(error_call) > 0

    @patch("anivault.gui.handlers.scan_event_handler.DialogTitles")
    @patch("anivault.gui.handlers.base_event_handler.QMessageBox")
    def test_on_scan_error_shows_error_dialog(
        self, mock_qmessagebox, mock_dialog_titles, handler
    ):
        """Test on_scan_error displays error dialog."""
        # Arrange
        error_message = "Permission denied"
        mock_dialog_titles.SCAN_ERROR = "Scan Error"

        # Act
        handler.on_scan_error(error_message)

        # Assert
        mock_qmessagebox.warning.assert_called_once()
        args = mock_qmessagebox.warning.call_args[0]
        assert "Failed to scan directory" in args[2]
        assert error_message in args[2]

    @patch("anivault.gui.handlers.scan_event_handler.DialogTitles")
    @patch("anivault.gui.handlers.base_event_handler.QMessageBox")
    def test_on_scan_error_logs_error(
        self, mock_qmessagebox, mock_dialog_titles, handler
    ):
        """Test on_scan_error logs error message."""
        # Arrange
        error_message = "Directory not found"
        mock_dialog_titles.SCAN_ERROR = "Scan Error"

        # Act
        with patch.object(handler._logger, "error") as mock_log:
            handler.on_scan_error(error_message)

        # Assert
        # Logger.error is called twice: once in on_scan_error, once in _show_error
        assert mock_log.call_count >= 1
        # Check that error message is logged
        logged_messages = [str(call) for call in mock_log.call_args_list]
        assert any(error_message in msg for msg in logged_messages)

    def test_on_files_grouped_calls_callback(self, handler, mock_callback):
        """Test on_files_grouped calls the update file tree callback."""
        # Arrange
        from anivault.core.file_grouper import Group

        # Create FileItem instances
        file1 = FileItem(file_path=Path("/test/anime_s01e01.mkv"), status="grouped")
        file2 = FileItem(file_path=Path("/test/anime_s02e01.mkv"), status="grouped")

        grouped_files = [
            Group(title="Anime Season 1", files=[file1]),
            Group(title="Anime Season 2", files=[file2]),
        ]

        # Expected dict conversion (using same FileItem instances)
        expected_dict = {
            "Anime Season 1": [file1],
            "Anime Season 2": [file2],
        }

        # Act
        handler.on_files_grouped(grouped_files)

        # Assert
        mock_callback.assert_called_once_with(expected_dict)

    def test_on_files_grouped_empty_dict(self, handler, mock_callback):
        """Test on_files_grouped handles empty grouped files."""
        # Arrange
        empty_groups = []

        # Act
        handler.on_files_grouped(empty_groups)

        # Assert
        mock_callback.assert_called_once_with({})

    def test_on_scan_finished_single_file(
        self, handler, mock_status_manager, mock_scan_controller
    ):
        """Test on_scan_finished handles single file."""
        # Arrange
        single_file = [FileItem(file_path=Path("/test/anime.mkv"), status="scanned")]

        # Act
        handler.on_scan_finished(single_file)

        # Assert
        mock_scan_controller.group_files.assert_called_once_with(single_file)
        expected_message = "Scan complete. Found 1 files"
        mock_status_manager.show_message.assert_called_with(expected_message, 0)

    def test_on_scan_error_empty_message(self, handler):
        """Test on_scan_error handles empty error message."""
        # Arrange
        empty_message = ""

        # Act - Should not raise exception
        with patch("anivault.gui.handlers.base_event_handler.QMessageBox"):
            handler.on_scan_error(empty_message)

        # Assert - No exception raised

    def test_on_scan_error_special_characters(self, handler):
        """Test on_scan_error handles special characters in error message."""
        # Arrange
        special_message = "Error: <>&\"'\\n\\t\r"

        # Act - Should not raise exception
        with patch("anivault.gui.handlers.base_event_handler.QMessageBox"):
            handler.on_scan_error(special_message)

        # Assert - No exception raised

    def test_inheritance_from_base_handler(self, handler):
        """Test ScanEventHandler properly inherits from BaseEventHandler."""
        # Assert
        from anivault.gui.handlers.base_event_handler import BaseEventHandler

        assert isinstance(handler, BaseEventHandler)
        assert hasattr(handler, "_show_status")
        assert hasattr(handler, "_show_error")
