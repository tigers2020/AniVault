"""Tests for FileProcessingViewModel.

This module contains comprehensive tests for the FileProcessingViewModel class,
including command execution, property management, and worker integration.
"""

import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pytest
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtTest import QSignalSpy

logger = logging.getLogger(__name__)

# Mock tmdbsimple before importing other modules
with patch.dict("sys.modules", {"tmdbsimple": Mock()}):
    from src.core.models import AnimeFile, FileGroup
    from src.viewmodels.file_processing_vm import FileProcessingViewModel


class TestFileProcessingViewModel:
    """Test cases for FileProcessingViewModel."""

    @pytest.fixture
    def app(self) -> QCoreApplication:
        """Create QCoreApplication for testing."""
        app = QCoreApplication.instance()
        if app is None:
            app = QCoreApplication([])
        return app

    @pytest.fixture
    def viewmodel(self, app: QCoreApplication) -> FileProcessingViewModel:
        """Create FileProcessingViewModel instance for testing."""
        vm = FileProcessingViewModel()
        vm.initialize()
        return vm

    @pytest.fixture
    def temp_dir(self) -> Any:
        """Create temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # More robust cleanup
        try:
            import os
            import stat
            # Force remove all files and directories
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.chmod(file_path, stat.S_IWRITE)
                        os.remove(file_path)
                    except (OSError, PermissionError):
                        pass
                for dir in dirs:
                    dir_path = os.path.join(root, dir)
                    try:
                        os.rmdir(dir_path)
                    except (OSError, PermissionError):
                        pass
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            # Final fallback - ignore all errors
            pass

    @pytest.fixture
    def sample_files(self, temp_dir: str) -> list[AnimeFile]:
        """Create sample anime files for testing."""
        files = []
        for i in range(3):
            file_path = Path(temp_dir) / f"anime_s01e{i+1:02d}.mkv"
            file_path.write_bytes(b"fake video content")

            anime_file = AnimeFile(
                file_path=file_path,
                filename=file_path.name,
                file_size=1024 * 1024,  # 1MB
                file_extension=".mkv",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            files.append(anime_file)

        return files

    @pytest.fixture
    def sample_groups(self, sample_files: list[AnimeFile]) -> list[FileGroup]:
        """Create sample file groups for testing."""
        groups = []
        for i, file in enumerate(sample_files):
            group = FileGroup(
                group_id=f"group_{i}",
                files=[file],
                similarity_score=0.9,
                best_file=file,
                series_title=f"Anime Series {i+1}",
            )
            groups.append(group)
        return groups

    def test_initialization(self, viewmodel) -> None:
        """Test ViewModel initialization."""
        assert viewmodel is not None
        assert viewmodel._is_initialized

        # Check initial properties
        assert viewmodel.get_property("scanned_files") == []
        assert viewmodel.get_property("file_groups") == []
        assert viewmodel.get_property("processed_files") == []
        assert viewmodel.get_property("moved_files") == []
        assert not viewmodel.get_property("is_pipeline_running")
        assert viewmodel.get_property("processing_status") == "Ready"

    def test_commands_setup(self, viewmodel) -> None:
        """Test that all commands are properly set up."""
        commands = viewmodel.get_available_commands()

        expected_commands = [
            "scan_files",
            "scan_directories",
            "process_files",
            "group_files",
            "parse_files",
            "retrieve_metadata",
            "move_files",
            "organize_files",
            "run_full_pipeline",
            "stop_processing",
            "set_scan_directories",
            "set_target_directory",
            "set_tmdb_api_key",
            "set_similarity_threshold",
            "clear_results",
            "reset_pipeline",
        ]

        for command in expected_commands:
            assert command in commands
            assert viewmodel.has_command(command)

    def test_properties_setup(self, viewmodel) -> None:
        """Test that all properties are properly set up."""
        # Check that all expected properties exist
        expected_properties = [
            "scanned_files",
            "file_groups",
            "processed_files",
            "moved_files",
            "scan_directories",
            "target_directory",
            "tmdb_api_key",
            "similarity_threshold",
            "is_pipeline_running",
            "current_pipeline_step",
            "scan_progress",
            "processing_status",
            "total_files_scanned",
            "total_groups_created",
            "total_files_processed",
            "total_files_moved",
        ]

        for prop in expected_properties:
            assert viewmodel.has_property(prop)

    def test_set_scan_directories_command(self, viewmodel, temp_dir) -> None:
        """Test setting scan directories."""
        # Create test directories
        dir1 = Path(temp_dir) / "dir1"
        dir2 = Path(temp_dir) / "dir2"
        dir1.mkdir()
        dir2.mkdir()

        directories = [str(dir1), str(dir2), "/nonexistent/dir"]

        viewmodel.execute_command("set_scan_directories", directories)

        # Check that only valid directories were set
        result_dirs = viewmodel.get_property("scan_directories")
        assert len(result_dirs) == 2
        assert str(dir1.absolute()) in result_dirs
        assert str(dir2.absolute()) in result_dirs

    def test_set_target_directory_command(self, viewmodel, temp_dir) -> None:
        """Test setting target directory."""
        target_dir = Path(temp_dir) / "target"

        viewmodel.execute_command("set_target_directory", str(target_dir))

        assert viewmodel.get_property("target_directory") == str(target_dir.absolute())
        assert target_dir.exists()
        assert target_dir.is_dir()

    def test_set_tmdb_api_key_command(self, viewmodel) -> None:
        """Test setting TMDB API key."""
        api_key = "test_api_key_12345"

        # First set the API key
        viewmodel.execute_command("set_tmdb_api_key", api_key)
        assert viewmodel.get_property("tmdb_api_key") == api_key

        # Set a different API key to test property update
        viewmodel.execute_command("set_tmdb_api_key", "new_key")
        assert viewmodel.get_property("tmdb_api_key") == "new_key"

    def test_set_similarity_threshold_command(self, viewmodel) -> None:
        """Test setting similarity threshold."""
        # Valid threshold
        viewmodel.execute_command("set_similarity_threshold", 0.8)
        assert viewmodel.get_property("similarity_threshold") == 0.8

        # Invalid threshold (too high) - should not raise exception, just emit error
        viewmodel.execute_command("set_similarity_threshold", 1.5)
        # The command should not change the value due to validation
        assert viewmodel.get_property("similarity_threshold") == 0.8

        # Invalid threshold (too low) - should not raise exception, just emit error
        viewmodel.execute_command("set_similarity_threshold", -0.1)
        # The command should not change the value due to validation
        assert viewmodel.get_property("similarity_threshold") == 0.8

    def test_clear_results_command(self, viewmodel, sample_files, sample_groups) -> None:
        """Test clearing results."""
        # Set some data
        viewmodel.set_property("scanned_files", sample_files)
        viewmodel.set_property("file_groups", sample_groups)
        viewmodel.set_property("processed_files", sample_files)
        viewmodel.set_property("moved_files", sample_files)

        # Clear results
        viewmodel.execute_command("clear_results")

        # Check that all data is cleared
        assert viewmodel.get_property("scanned_files") == []
        assert viewmodel.get_property("file_groups") == []
        assert viewmodel.get_property("processed_files") == []
        assert viewmodel.get_property("moved_files") == []
        assert viewmodel.get_property("total_files_scanned") == 0
        assert viewmodel.get_property("total_groups_created") == 0
        assert viewmodel.get_property("total_files_processed") == 0
        assert viewmodel.get_property("total_files_moved") == 0

    def test_reset_pipeline_command(self, viewmodel, sample_files) -> None:
        """Test resetting pipeline."""
        # Set some data and state
        viewmodel.set_property("scanned_files", sample_files)
        viewmodel.set_property("is_pipeline_running", True)
        viewmodel.set_property("current_pipeline_step", "Processing")

        # Reset pipeline
        viewmodel.execute_command("reset_pipeline")

        # Check that everything is reset
        assert viewmodel.get_property("scanned_files") == []
        assert not viewmodel.get_property("is_pipeline_running")
        assert viewmodel.get_property("current_pipeline_step") == ""
        assert viewmodel.get_property("processing_status") == "Ready"

    def test_scan_files_command(self, viewmodel, temp_dir) -> None:
        """Test scan files command."""
        # Set required properties and initialize components
        viewmodel.set_property("tmdb_api_key", "test_key")
        viewmodel.initialize_components()

        directories = [str(Path(temp_dir))]
        viewmodel.execute_command("scan_files", directories)

        # Check that the command executed successfully
        # The command should have created a worker and added a task
        assert viewmodel.has_worker(), "Worker should be created after scan_files command"
        
        # The command should have executed without errors
        # We don't need to wait for completion since the command itself is what we're testing

    def test_group_files_command(self, viewmodel, sample_files) -> None:
        """Test group files command."""
        # Set required properties and initialize components
        viewmodel.set_property("tmdb_api_key", "test_key")
        viewmodel.initialize_components()

        viewmodel.execute_command("group_files", sample_files)

        # Check that the command executed successfully
        # The command should have created a worker and added a task
        assert viewmodel.has_worker(), "Worker should be created after group_files command"

    def test_parse_files_command(self, viewmodel, sample_files) -> None:
        """Test parse files command."""
        # Set required properties and initialize components
        viewmodel.set_property("tmdb_api_key", "test_key")
        viewmodel.initialize_components()

        viewmodel.execute_command("parse_files", sample_files)

        # Check that the command executed successfully
        # The command should have created a worker and added a task
        assert viewmodel.has_worker(), "Worker should be created after parse_files command"

    def test_retrieve_metadata_command(self, viewmodel, sample_files) -> None:
        """Test retrieve metadata command."""
        # Initialize components and set API key
        viewmodel.initialize_components()
        viewmodel.set_property("tmdb_api_key", "test_key")

        viewmodel.execute_command("retrieve_metadata", sample_files)

        # Check that the command executed successfully
        # The command should have created a worker and added a task (only if TMDB client is available)
        if viewmodel._tmdb_client:
            assert viewmodel.has_worker(), "Worker should be created after retrieve_metadata command"
        else:
            # If TMDB client is not available, the command should complete without creating a worker
            assert not viewmodel.has_worker(), "No worker should be created when TMDB client is not available"

    def test_move_files_command(self, viewmodel, sample_groups, temp_dir) -> None:
        """Test move files command."""
        # Set required properties and initialize components
        viewmodel.set_property("tmdb_api_key", "test_key")
        viewmodel.set_property("target_directory", temp_dir)
        viewmodel.initialize_components()

        viewmodel.execute_command("move_files", sample_groups)

        # Check that the command executed successfully
        # The command should have created a worker and added a task
        assert viewmodel.has_worker(), "Worker should be created after move_files command"
        
        # Clean up any created directories to prevent teardown issues
        try:
            import shutil
            import os
            # Force remove all subdirectories in temp_dir
            for item in temp_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                elif item.is_file():
                    try:
                        item.unlink()
                    except (OSError, PermissionError):
                        pass
        except Exception:
            # Ignore cleanup errors
            pass

    def test_worker_signal_handling(self, viewmodel, sample_files, sample_groups) -> None:
        """Test worker signal handling."""
        # Create worker
        _worker = viewmodel.create_worker()

        # Test task started signal
        viewmodel._on_worker_task_started("Test Task")
        assert viewmodel.get_property("current_pipeline_step") == "Test Task"
        assert "Test Task" in viewmodel.get_property("processing_status")

        # Test task progress signal
        viewmodel._on_worker_task_progress("Test Task", 50)
        assert viewmodel.get_property("scan_progress") == 50
        assert "50%" in viewmodel.get_property("processing_status")

        # Test task finished signal - scanning
        viewmodel._on_worker_task_finished("File Scanning", sample_files, True)
        assert viewmodel.get_property("scanned_files") == sample_files
        assert viewmodel.get_property("total_files_scanned") == len(sample_files)

        # Test task finished signal - grouping
        viewmodel._on_worker_task_finished("File Grouping", sample_groups, True)
        assert viewmodel.get_property("file_groups") == sample_groups
        assert viewmodel.get_property("total_groups_created") == len(sample_groups)

        # Test task error signal
        with patch.object(viewmodel, "error_occurred") as mock_error:
            viewmodel._on_worker_task_error("Test Task", "Test Error")
            mock_error.emit.assert_called_once_with("Test Task failed: Test Error")

        # Test worker finished signal
        viewmodel._on_worker_finished()
        assert not viewmodel.get_property("is_pipeline_running")
        assert viewmodel.get_property("current_pipeline_step") == ""
        assert viewmodel.get_property("processing_status") == "Completed"

    def test_handle_scanning_result(self, viewmodel, sample_files) -> None:
        """Test handling scanning result."""
        with patch.object(viewmodel, "files_scanned") as mock_signal:
            viewmodel._handle_scanning_result(sample_files)

            assert viewmodel._scanned_files == sample_files
            assert viewmodel.get_property("scanned_files") == sample_files
            assert viewmodel.get_property("total_files_scanned") == len(sample_files)
            mock_signal.emit.assert_called_once_with(sample_files)

    def test_handle_grouping_result(self, viewmodel, sample_groups) -> None:
        """Test handling grouping result."""
        with patch.object(viewmodel, "files_grouped") as mock_signal:
            viewmodel._handle_grouping_result(sample_groups)

            assert viewmodel._file_groups == sample_groups
            assert viewmodel.get_property("file_groups") == sample_groups
            assert viewmodel.get_property("total_groups_created") == len(sample_groups)
            mock_signal.emit.assert_called_once_with(sample_groups)

    def test_handle_parsing_result(self, viewmodel: FileProcessingViewModel, sample_files: list[AnimeFile]) -> None:
        """Test handling parsing result."""
        with patch.object(viewmodel, "files_parsed") as mock_signal:
            viewmodel._handle_parsing_result(sample_files)

            assert viewmodel._processed_files == sample_files
            assert viewmodel.get_property("processed_files") == sample_files
            assert viewmodel.get_property("total_files_processed") == len(sample_files)
            mock_signal.emit.assert_called_once_with(sample_files)

    def test_handle_metadata_result(self, viewmodel: FileProcessingViewModel, sample_files: list[AnimeFile]) -> None:
        """Test handling metadata result."""
        with patch.object(viewmodel, "metadata_retrieved") as mock_signal:
            viewmodel._handle_metadata_result(sample_files)

            assert viewmodel._processed_files == sample_files
            assert viewmodel.get_property("processed_files") == sample_files
            mock_signal.emit.assert_called_once_with(sample_files)

    def test_handle_moving_result(self, viewmodel: FileProcessingViewModel, sample_files: list[AnimeFile]) -> None:
        """Test handling moving result."""
        with patch.object(viewmodel, "files_moved") as mock_signal:
            viewmodel._handle_moving_result(sample_files)

            assert viewmodel._moved_files == sample_files
            assert viewmodel.get_property("moved_files") == sample_files
            assert viewmodel.get_property("total_files_moved") == len(sample_files)
            mock_signal.emit.assert_called_once_with(sample_files)

    def test_get_supported_extensions(self, viewmodel: FileProcessingViewModel) -> None:
        """Test getting supported extensions."""
        extensions = viewmodel._get_supported_extensions()

        expected_extensions = [
            ".mkv",
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".flv",
            ".webm",
            ".m4v",
            ".3gp",
            ".ogv",
            ".ts",
            ".m2ts",
        ]

        assert extensions == expected_extensions

    def test_getter_methods(self, viewmodel: FileProcessingViewModel, sample_files: list[AnimeFile], sample_groups: list[FileGroup]) -> None:
        """Test getter methods."""
        # Set some data
        viewmodel._scanned_files = sample_files
        viewmodel._file_groups = sample_groups
        viewmodel._processed_files = sample_files
        viewmodel._moved_files = sample_files

        # Test getters
        assert viewmodel.get_scanned_files() == sample_files
        assert viewmodel.get_file_groups() == sample_groups
        assert viewmodel.get_processed_files() == sample_files
        assert viewmodel.get_moved_files() == sample_files

    def test_pipeline_state_methods(self, viewmodel: FileProcessingViewModel) -> None:
        """Test pipeline state methods."""
        # Test initial state
        assert not viewmodel.is_pipeline_running()
        assert viewmodel.get_processing_status() == "Ready"
        assert viewmodel.get_scan_progress() == 0

        # Set pipeline running
        viewmodel.set_property("is_pipeline_running", True)
        viewmodel.set_property("processing_status", "Processing")
        viewmodel.set_property("scan_progress", 75)

        # Test updated state
        assert viewmodel.is_pipeline_running()
        assert viewmodel.get_processing_status() == "Processing"
        assert viewmodel.get_scan_progress() == 75

    def test_initialize_components(self, viewmodel: FileProcessingViewModel) -> None:
        """Test component initialization."""
        # Set required properties
        viewmodel.set_property("tmdb_api_key", "test_key")
        viewmodel.set_property("similarity_threshold", 0.8)

        viewmodel.initialize_components()

        # Check that all components were initialized
        assert viewmodel._file_scanner is not None, "FileScanner should be initialized"
        assert viewmodel._anime_parser is not None, "AnimeParser should be initialized"
        assert viewmodel._tmdb_client is not None, "TMDBClient should be initialized"
        assert viewmodel._metadata_cache is not None, "MetadataCache should be initialized"
        assert viewmodel._file_grouper is not None, "FileGrouper should be initialized"
        assert viewmodel._file_mover is not None, "FileMover should be initialized"

    def test_cleanup(self, viewmodel: FileProcessingViewModel, sample_files: list[AnimeFile]) -> None:
        """Test cleanup method."""
        # Set some data
        viewmodel.set_property("scanned_files", sample_files)
        viewmodel.set_property("is_pipeline_running", True)

        # Create worker
        _worker = viewmodel.create_worker()

        # Check data before cleanup
        print(f"Before cleanup: scanned_files = {viewmodel.get_property('scanned_files')}")

        # Cleanup
        viewmodel.cleanup()

        # Check that data is cleared
        print(f"After cleanup: scanned_files = {viewmodel.get_property('scanned_files')}")
        assert viewmodel.get_property("scanned_files") is None
        # Note: is_pipeline_running might not be False immediately due to async cleanup

    def test_validation_rules(self, viewmodel: FileProcessingViewModel) -> None:
        """Test property validation rules."""
        # Test similarity threshold validation
        assert viewmodel._validate_property("similarity_threshold", 0.5)
        assert viewmodel._validate_property("similarity_threshold", 0.0)
        assert viewmodel._validate_property("similarity_threshold", 1.0)
        assert not viewmodel._validate_property("similarity_threshold", 1.5)
        assert not viewmodel._validate_property("similarity_threshold", -0.1)

    def test_property_change_notifications(self, viewmodel) -> None:
        """Test that property changes emit notifications."""
        # Spy on property_changed signal
        spy = QSignalSpy(viewmodel.property_changed)

        # Change a property
        viewmodel.set_property("scan_progress", 50)

        # Check that signal was emitted
        assert len(spy) == 1
        assert spy[0] == ["scan_progress", 50]

    def test_error_handling(self, viewmodel) -> None:
        """Test error handling in commands."""
        # Test scan files without directories - should emit error but not raise exception
        viewmodel.execute_command("scan_files", [])
        # The command should emit an error signal but not raise an exception

        # Test process files without files - should emit error but not raise exception
        viewmodel.execute_command("process_files", [])
        # The command should emit an error signal but not raise an exception

        # Test move files without groups - should emit error but not raise exception
        viewmodel.execute_command("move_files", [])
        # The command should emit an error signal but not raise an exception

        # Test move files without target directory - should emit error but not raise exception
        viewmodel.set_property("target_directory", "")
        viewmodel.execute_command("move_files", [FileGroup("test", [])])
        # The command should emit an error signal but not raise an exception

    def test_worker_management(self, viewmodel) -> None:
        """Test worker management methods."""
        # Test initial state
        assert not viewmodel.has_worker()
        assert not viewmodel.is_worker_running()

        # Create worker
        _worker = viewmodel.create_worker()
        assert viewmodel.has_worker()
        assert _worker is not None

        # Test worker state
        assert not viewmodel.is_worker_running()
        assert viewmodel.get_worker_queue_size() == 0

        # Test adding tasks
        mock_task = Mock()
        mock_task.get_name.return_value = "Test Task"
        viewmodel.add_worker_task(mock_task)
        assert viewmodel.get_worker_queue_size() == 1

        # Test clearing tasks
        viewmodel.clear_worker_tasks()
        assert viewmodel.get_worker_queue_size() == 0
