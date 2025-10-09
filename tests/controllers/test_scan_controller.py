"""
Tests for ScanController

This module contains unit tests for the ScanController class,
verifying its business logic and signal handling.
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtCore import QObject

from anivault.gui.controllers.scan_controller import ScanController
from anivault.gui.models import FileItem


class TestScanController:
    """Test cases for ScanController."""

    @pytest.fixture
    def scan_controller(self):
        """Create a ScanController instance for testing."""
        return ScanController()

    @pytest.fixture
    def mock_file_item(self):
        """Create a mock FileItem for testing."""
        return FileItem(file_path=Path("/test/path/anime.mkv"), status="scanned")

    @pytest.fixture
    def temp_directory(self, tmp_path):
        """Create a temporary directory for testing."""
        return tmp_path

    def test_scan_controller_initialization(self, scan_controller):
        """Test ScanController initialization."""
        assert scan_controller is not None
        assert scan_controller.file_grouper is not None
        assert scan_controller.parser is not None
        assert scan_controller.scanner_thread is None
        assert scan_controller.scanner_worker is None
        assert scan_controller.is_scanning is False
        assert scan_controller.scanned_files == []

    def test_scan_directory_invalid_path(self, scan_controller):
        """Test scan_directory with invalid path."""
        # Test with None path
        with pytest.raises(ValueError, match="Invalid directory path"):
            scan_controller.scan_directory(None)

        # Test with non-existent path
        non_existent = Path("/non/existent/path")
        with pytest.raises(ValueError, match="Invalid directory path"):
            scan_controller.scan_directory(non_existent)

        # Test with file instead of directory
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=False):
                file_path = Path("/test/file.txt")
                with pytest.raises(ValueError, match="Path is not a directory"):
                    scan_controller.scan_directory(file_path)

    def test_scan_directory_already_scanning(self, scan_controller, temp_directory):
        """Test scan_directory when already scanning."""
        scan_controller.is_scanning = True

        # Should not raise exception, just log warning and return
        scan_controller.scan_directory(temp_directory)

    @patch("anivault.gui.controllers.scan_controller.FileScannerWorker")
    @patch("anivault.gui.controllers.scan_controller.QThread")
    def test_scan_directory_success(
        self, mock_thread_class, mock_worker_class, scan_controller, temp_directory
    ):
        """Test successful directory scanning."""
        # Mock the worker and thread
        mock_worker = Mock()
        mock_thread = Mock()
        mock_worker_class.return_value = mock_worker
        mock_thread_class.return_value = mock_thread

        # Create test files
        (temp_directory / "anime1.mkv").touch()
        (temp_directory / "anime2.avi").touch()

        # Start scanning
        scan_controller.scan_directory(temp_directory)

        # Verify worker and thread were created
        mock_worker_class.assert_called_once()
        mock_thread_class.assert_called_once()

        # Verify worker was moved to thread
        mock_worker.moveToThread.assert_called_once_with(mock_thread)

        # Verify signals were connected
        assert mock_thread.started.connect.called
        assert mock_worker.scan_started.connect.called
        assert mock_worker.scan_finished.connect.called

        # Verify thread was started
        mock_thread.start.assert_called_once()
        assert scan_controller.is_scanning is True

    def test_cancel_scan_not_scanning(self, scan_controller):
        """Test cancel_scan when not scanning."""
        # Should not raise any exception
        scan_controller.cancel_scan()

    def test_cancel_scan_in_progress(self, scan_controller):
        """Test cancel_scan when scanning is in progress."""
        scan_controller.is_scanning = True
        mock_worker = Mock()
        scan_controller.scanner_worker = mock_worker

        scan_controller.cancel_scan()

        mock_worker.cancel_scan.assert_called_once()

    def test_group_files_empty_list(self, scan_controller):
        """Test group_files with empty file list."""
        with pytest.raises(ValueError, match="Cannot group empty file list"):
            scan_controller.group_files([])

    @patch("anivault.gui.controllers.scan_controller.FileGrouper")
    def test_group_files_success(
        self, mock_grouper_class, scan_controller, mock_file_item
    ):
        """Test successful file grouping."""
        # Mock the grouper
        mock_grouper = Mock()
        mock_grouper_class.return_value = mock_grouper

        # Mock grouped result
        expected_groups = {"Test Anime": [mock_file_item]}
        mock_grouper.group_files.return_value = expected_groups

        # Create controller with mocked grouper
        scan_controller.file_grouper = mock_grouper

        # Group files
        result = scan_controller.group_files([mock_file_item])

        # Verify result
        assert result == expected_groups
        mock_grouper.group_files.assert_called_once()

    @patch("anivault.gui.controllers.scan_controller.AnitopyParser")
    def test_group_files_parser_error(
        self, mock_parser_class, scan_controller, mock_file_item
    ):
        """Test file grouping with parser error."""
        # Mock parser to raise exception
        mock_parser = Mock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse.side_effect = Exception("Parse error")

        # Create controller with mocked parser
        scan_controller.parser = mock_parser

        # Mock grouper
        mock_grouper = Mock()
        expected_groups = {"Test Anime": [mock_file_item]}
        mock_grouper.group_files.return_value = expected_groups
        scan_controller.file_grouper = mock_grouper

        # Group files (should handle parser error gracefully)
        result = scan_controller.group_files([mock_file_item])

        # Verify result still works despite parser error
        assert result == expected_groups
        mock_parser.parse.assert_called_once_with(mock_file_item.file_path.name)

    def test_has_scanned_files_property(self, scan_controller, mock_file_item):
        """Test has_scanned_files property."""
        # Initially no files
        assert scan_controller.has_scanned_files is False

        # Add files
        scan_controller.scanned_files = [mock_file_item]
        assert scan_controller.has_scanned_files is True

        # Clear files
        scan_controller.scanned_files = []
        assert scan_controller.has_scanned_files is False

    def test_scanned_files_count_property(self, scan_controller, mock_file_item):
        """Test scanned_files_count property."""
        # Initially no files
        assert scan_controller.scanned_files_count == 0

        # Add files
        scan_controller.scanned_files = [mock_file_item, mock_file_item]
        assert scan_controller.scanned_files_count == 2

        # Clear files
        scan_controller.scanned_files = []
        assert scan_controller.scanned_files_count == 0

    def test_signal_emissions(self, scan_controller):
        """Test that signals are properly emitted."""
        # Mock signal receiver
        scan_started_received = False
        scan_finished_received = False
        scan_error_received = False
        files_grouped_received = False

        def on_scan_started():
            nonlocal scan_started_received
            scan_started_received = True

        def on_scan_finished(files):
            nonlocal scan_finished_received
            scan_finished_received = True

        def on_scan_error(error):
            nonlocal scan_error_received
            scan_error_received = True

        def on_files_grouped(groups):
            nonlocal files_grouped_received
            files_grouped_received = True

        # Connect signals
        scan_controller.scan_started.connect(on_scan_started)
        scan_controller.scan_finished.connect(on_scan_finished)
        scan_controller.scan_error.connect(on_scan_error)
        scan_controller.files_grouped.connect(on_files_grouped)

        # Create a mock file item for testing
        test_file_item = FileItem(file_path=Path("/test/anime.mkv"), status="scanned")

        # Emit signals
        scan_controller.scan_started.emit()
        scan_controller.scan_finished.emit([test_file_item])
        scan_controller.scan_error.emit("Test error")
        scan_controller.files_grouped.emit({"Test": []})

        # Verify signals were received
        assert scan_started_received is True
        assert scan_finished_received is True
        assert scan_error_received is True
        assert files_grouped_received is True
