"""
Tests for TMDBController

This module contains unit tests for the TMDBController class,
verifying its business logic and signal handling.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult
from anivault.gui.controllers.tmdb_controller import TMDBController
from anivault.gui.models import FileItem


class TestTMDBController:
    """Test cases for TMDBController."""

    @pytest.fixture
    def tmdb_controller(self):
        """Create a TMDBController instance for testing."""
        return TMDBController()

    @pytest.fixture
    def tmdb_controller_with_api_key(self):
        """Create a TMDBController with API key for testing."""
        return TMDBController(api_key="test_api_key")  # pragma: allowlist secret

    @pytest.fixture
    def mock_file_item(self):
        """Create a mock FileItem for testing."""
        return FileItem(file_path=Path("/test/path/anime.mkv"), status="scanned")

    @pytest.fixture
    def mock_scanned_file(self):
        """Create a mock ScannedFile for testing TMDBController."""
        parsing_result = ParsingResult(
            title="Test Anime",
            episode=1,
            season=1,
        )
        return ScannedFile(
            file_path=Path("/test/path/anime.mkv"),
            metadata=parsing_result,
            file_size=1024,
            last_modified=0.0,
        )

    def test_tmdb_controller_initialization(self, tmdb_controller):
        """Test TMDBController initialization."""
        assert tmdb_controller is not None
        assert tmdb_controller.api_key is None
        assert tmdb_controller.tmdb_thread is None
        assert tmdb_controller.tmdb_worker is None
        assert tmdb_controller.is_matching is False
        assert tmdb_controller.match_results == []

    def test_tmdb_controller_initialization_with_api_key(
        self, tmdb_controller_with_api_key
    ):
        """Test TMDBController initialization with API key."""
        assert tmdb_controller_with_api_key is not None
        assert tmdb_controller_with_api_key.api_key == "test_api_key"  # pragma: allowlist secret
        assert tmdb_controller_with_api_key.has_api_key is True

    def test_set_api_key(self, tmdb_controller):
        """Test setting API key."""
        assert tmdb_controller.has_api_key is False

        tmdb_controller.set_api_key("new_api_key")

        assert tmdb_controller.api_key == "new_api_key"
        assert tmdb_controller.has_api_key is True

    def test_match_files_empty_list(self, tmdb_controller_with_api_key):
        """Test match_files with empty file list."""
        with pytest.raises(ValueError, match="Files list cannot be empty"):
            tmdb_controller_with_api_key.match_files([])

    def test_match_files_no_api_key(self, tmdb_controller, mock_scanned_file):
        """Test match_files without API key."""
        with pytest.raises(ValueError, match="TMDB API key is required"):
            tmdb_controller.match_files([mock_scanned_file])

    def test_match_files_already_matching(
        self, tmdb_controller_with_api_key, mock_scanned_file
    ):
        """Test match_files when already matching."""
        tmdb_controller_with_api_key.is_matching = True

        with pytest.raises(RuntimeError, match="Matching is already in progress"):
            tmdb_controller_with_api_key.match_files([mock_scanned_file])

    @patch("anivault.gui.controllers.tmdb_controller.TMDBMatchingWorker")
    @patch("anivault.gui.controllers.tmdb_controller.QThread")
    def test_match_files_success(
        self,
        mock_thread_class,
        mock_worker_class,
        tmdb_controller_with_api_key,
        mock_scanned_file,
    ):
        """Test successful file matching."""
        # Mock the worker and thread
        mock_worker = Mock()
        mock_thread = Mock()
        mock_worker_class.return_value = mock_worker
        mock_thread_class.return_value = mock_thread

        # Start matching
        tmdb_controller_with_api_key.match_files([mock_scanned_file])

        # Verify worker and thread were created
        mock_worker_class.assert_called_once_with("test_api_key")
        mock_thread_class.assert_called_once()

        # Verify worker was moved to thread
        mock_worker.moveToThread.assert_called_once_with(mock_thread)

        # Verify signals were connected
        assert mock_thread.started.connect.called
        assert mock_worker.matching_started.connect.called
        assert mock_worker.matching_finished.connect.called

        # Verify thread was started
        mock_thread.start.assert_called_once()
        assert tmdb_controller_with_api_key.is_matching is True

    def test_cancel_matching_not_matching(self, tmdb_controller):
        """Test cancel_matching when not matching."""
        # Should not raise any exception
        tmdb_controller.cancel_matching()

    def test_cancel_matching_in_progress(self, tmdb_controller):
        """Test cancel_matching when matching is in progress."""
        tmdb_controller.is_matching = True
        mock_worker = Mock()
        tmdb_controller.tmdb_worker = mock_worker

        tmdb_controller.cancel_matching()

        mock_worker.cancel_matching.assert_called_once()

    def test_get_match_result_found(self, tmdb_controller):
        """Test get_match_result when result is found."""
        # Set up match results
        expected_result = {
            "file_path": "/test/path/anime.mkv",
            "match_result": {"title": "Test Anime"},
            "status": "matched",
        }
        tmdb_controller.match_results = [expected_result]

        result = tmdb_controller.get_match_result("/test/path/anime.mkv")

        assert result == expected_result

    def test_get_match_result_not_found(self, tmdb_controller):
        """Test get_match_result when result is not found."""
        tmdb_controller.match_results = []

        result = tmdb_controller.get_match_result("/test/path/anime.mkv")

        assert result is None

    def test_get_matched_files_count(self, tmdb_controller):
        """Test get_matched_files_count."""
        # No results
        assert tmdb_controller.get_matched_files_count() == 0

        # Add results with some matches
        tmdb_controller.match_results = [
            {
                "file_path": "/test1.mkv",
                "match_result": {"title": "Anime 1"},
                "status": "matched",
            },
            {"file_path": "/test2.mkv", "match_result": None, "status": "no_match"},
            {
                "file_path": "/test3.mkv",
                "match_result": {"title": "Anime 3"},
                "status": "matched",
            },
        ]

        assert tmdb_controller.get_matched_files_count() == 2

    def test_get_total_files_count(self, tmdb_controller):
        """Test get_total_files_count."""
        # No results
        assert tmdb_controller.get_total_files_count() == 0

        # Add results
        tmdb_controller.match_results = [
            {"file_path": "/test1.mkv", "status": "matched"},
            {"file_path": "/test2.mkv", "status": "no_match"},
            {"file_path": "/test3.mkv", "status": "matched"},
        ]

        assert tmdb_controller.get_total_files_count() == 3

    def test_is_operation_in_progress_property(self, tmdb_controller):
        """Test is_operation_in_progress method."""
        # Initially not in progress
        assert tmdb_controller.is_operation_in_progress() is False

        # Set matching in progress
        tmdb_controller.is_matching = True
        assert tmdb_controller.is_operation_in_progress() is True

        # Clear matching
        tmdb_controller.is_matching = False
        assert tmdb_controller.is_operation_in_progress() is False

    def test_signal_emissions(self, tmdb_controller):
        """Test that signals are properly emitted."""
        # Mock signal receivers
        matching_started_received = False
        file_matched_received = False
        matching_progress_received = False
        matching_finished_received = False
        matching_error_received = False
        matching_cancelled_received = False

        def on_matching_started():
            nonlocal matching_started_received
            matching_started_received = True

        def on_file_matched(result):
            nonlocal file_matched_received
            file_matched_received = True

        def on_matching_progress(progress):
            nonlocal matching_progress_received
            matching_progress_received = True

        def on_matching_finished(results):
            nonlocal matching_finished_received
            matching_finished_received = True

        def on_matching_error(error):
            nonlocal matching_error_received
            matching_error_received = True

        def on_matching_cancelled():
            nonlocal matching_cancelled_received
            matching_cancelled_received = True

        # Connect signals
        tmdb_controller.matching_started.connect(on_matching_started)
        tmdb_controller.file_matched.connect(on_file_matched)
        tmdb_controller.matching_progress.connect(on_matching_progress)
        tmdb_controller.matching_finished.connect(on_matching_finished)
        tmdb_controller.matching_error.connect(on_matching_error)
        tmdb_controller.matching_cancelled.connect(on_matching_cancelled)

        # Emit signals
        tmdb_controller.matching_started.emit()
        tmdb_controller.file_matched.emit({"file_path": "/test.mkv"})
        tmdb_controller.matching_progress.emit(50)
        tmdb_controller.matching_finished.emit([{"file_path": "/test.mkv"}])
        tmdb_controller.matching_error.emit("Test error")
        tmdb_controller.matching_cancelled.emit()

        # Verify signals were received
        assert matching_started_received is True
        assert file_matched_received is True
        assert matching_progress_received is True
        assert matching_finished_received is True
        assert matching_error_received is True
        assert matching_cancelled_received is True

    def test_signal_handler_methods(self, tmdb_controller):
        """Test internal signal handler methods."""
        # Test matching started handler
        tmdb_controller._on_matching_started()
        assert tmdb_controller.is_matching is True  # Should set is_matching to True

        # Test file matched handler
        result = {
            "file_path": "/test.mkv",
            "file_name": "test.mkv",
            "status": "matched",
        }
        tmdb_controller._on_file_matched(result)
        # Should not raise exception

        # Test matching progress handler
        tmdb_controller._on_matching_progress(75)
        # Should not raise exception

        # Test matching finished handler
        results = [{"file_path": "/test.mkv", "match_result": {"title": "Test"}}]
        tmdb_controller._on_matching_finished(results)
        assert tmdb_controller.match_results == results
        assert tmdb_controller.is_matching is False

        # Test matching error handler
        tmdb_controller.is_matching = True
        tmdb_controller._on_matching_error("Test error")
        assert tmdb_controller.is_matching is False

        # Test matching cancelled handler
        tmdb_controller.is_matching = True
        tmdb_controller._on_matching_cancelled()
        assert tmdb_controller.is_matching is False
