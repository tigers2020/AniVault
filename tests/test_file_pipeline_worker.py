"""
Tests for FilePipelineWorker and related components.

This module tests the FilePipelineWorker functionality, including
task execution, signal emission, and thread safety.
"""

import threading
import time
from unittest.mock import Mock

import pytest
from PyQt5.QtTest import QSignalSpy
from PyQt5.QtWidgets import QApplication

from src.core.models import AnimeFile, FileGroup, ProcessingState
from src.core.services.file_pipeline_worker import (
    FileGroupingTask,
    FileMovingTask,
    FileParsingTask,
    FilePipelineWorker,
    FileScanningTask,
    MetadataRetrievalTask,
    WorkerTask,
)
from src.viewmodels.base_viewmodel import BaseViewModel


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    app.quit()


class TestWorkerTask:
    """Test WorkerTask abstract base class."""

    def test_worker_task_interface(self) -> None:
        """Test that WorkerTask enforces the required interface."""

        class TestTask(WorkerTask):
            def execute(self):
                return "test_result"

            def get_name(self):
                return "TestTask"

        task = TestTask()
        assert task.execute() == "test_result"
        assert task.get_name() == "TestTask"
        assert task.get_progress_message() == "Executing TestTask"

    def test_worker_task_progress_message(self) -> None:
        """Test custom progress message."""

        class TestTask(WorkerTask):
            def execute(self):
                return "test_result"

            def get_name(self):
                return "TestTask"

            def get_progress_message(self):
                return "Custom progress message"

        task = TestTask()
        assert task.get_progress_message() == "Custom progress message"


class TestFileScanningTask:
    """Test FileScanningTask functionality."""

    def test_file_scanning_task_creation(self) -> None:
        """Test FileScanningTask creation and basic properties."""
        task = FileScanningTask(
            scan_directories=["/path1", "/path2"], supported_extensions=[".mkv", ".mp4"]
        )

        assert task.get_name() == "File Scanning"
        assert "Scanning 2 directories" in task.get_progress_message()
        assert task.scan_directories == ["/path1", "/path2"]
        assert task.supported_extensions == [".mkv", ".mp4"]

    def test_file_scanning_task_execution(self) -> None:
        """Test FileScanningTask execution."""
        task = FileScanningTask(scan_directories=["/test/path"], supported_extensions=[".mkv"])

        result = task.execute()
        assert isinstance(result, list)
        assert len(result) == 0  # Empty list as placeholder


class TestFileGroupingTask:
    """Test FileGroupingTask functionality."""

    def test_file_grouping_task_creation(self) -> None:
        """Test FileGroupingTask creation and basic properties."""
        files = [Mock(spec=AnimeFile) for _ in range(5)]
        task = FileGroupingTask(files, similarity_threshold=0.8)

        assert task.get_name() == "File Grouping"
        assert "Grouping 5 files" in task.get_progress_message()
        assert task.files == files
        assert task.similarity_threshold == 0.8

    def test_file_grouping_task_execution(self) -> None:
        """Test FileGroupingTask execution."""
        files = [Mock(spec=AnimeFile) for _ in range(3)]
        task = FileGroupingTask(files, similarity_threshold=0.7)

        result = task.execute()
        assert isinstance(result, list)
        assert len(result) == 0  # Empty list as placeholder


class TestFileParsingTask:
    """Test FileParsingTask functionality."""

    def test_file_parsing_task_creation(self) -> None:
        """Test FileParsingTask creation and basic properties."""
        files = [Mock(spec=AnimeFile) for _ in range(10)]
        task = FileParsingTask(files)

        assert task.get_name() == "File Parsing"
        assert "Parsing information from 10 files" in task.get_progress_message()
        assert task.files == files

    def test_file_parsing_task_execution(self) -> None:
        """Test FileParsingTask execution."""
        files = [Mock(spec=AnimeFile) for _ in range(5)]
        task = FileParsingTask(files)

        result = task.execute()
        assert result == files  # Returns files as-is in placeholder


class TestMetadataRetrievalTask:
    """Test MetadataRetrievalTask functionality."""

    def test_metadata_retrieval_task_creation(self) -> None:
        """Test MetadataRetrievalTask creation and basic properties."""
        files = [Mock(spec=AnimeFile) for _ in range(8)]
        task = MetadataRetrievalTask(files, "test_api_key")

        assert task.get_name() == "Metadata Retrieval"
        assert "Retrieving metadata for 8 files" in task.get_progress_message()
        assert task.files == files
        assert task.api_key == "test_api_key"

    def test_metadata_retrieval_task_execution(self) -> None:
        """Test MetadataRetrievalTask execution."""
        files = [Mock(spec=AnimeFile) for _ in range(3)]
        task = MetadataRetrievalTask(files, "test_key")

        result = task.execute()
        assert result == files  # Returns files as-is in placeholder


class TestFileMovingTask:
    """Test FileMovingTask functionality."""

    def test_file_moving_task_creation(self) -> None:
        """Test FileMovingTask creation and basic properties."""
        groups = [Mock(spec=FileGroup) for _ in range(4)]
        task = FileMovingTask(groups, "/target/directory")

        assert task.get_name() == "File Moving"
        assert "Moving 4 file groups" in task.get_progress_message()
        assert task.groups == groups
        assert task.target_directory == "/target/directory"

    def test_file_moving_task_execution(self) -> None:
        """Test FileMovingTask execution."""
        groups = [Mock(spec=FileGroup) for _ in range(2)]
        task = FileMovingTask(groups, "/target")

        result = task.execute()
        assert isinstance(result, list)
        assert len(result) == 0  # Empty list as placeholder


class TestFilePipelineWorker:
    """Test FilePipelineWorker functionality."""

    def test_worker_initialization(self) -> None:
        """Test worker initialization."""
        worker = FilePipelineWorker()

        assert not worker.is_running()
        assert worker.get_queue_size() == 0
        assert worker.get_current_task() is None

    def test_worker_processing_state_setting(self) -> None:
        """Test setting processing state."""
        worker = FilePipelineWorker()
        processing_state = ProcessingState()

        worker.set_processing_state(processing_state)
        assert worker._processing_state == processing_state

    def test_worker_task_management(self) -> None:
        """Test task management operations."""
        worker = FilePipelineWorker()

        # Test adding single task
        task1 = FileScanningTask(["/path1"], [".mkv"])
        worker.add_task(task1)
        assert worker.get_queue_size() == 1

        # Test adding multiple tasks
        task2 = FileGroupingTask([], 0.7)
        task3 = FileParsingTask([])
        worker.add_tasks([task2, task3])
        assert worker.get_queue_size() == 3

        # Test clearing tasks
        worker.clear_tasks()
        assert worker.get_queue_size() == 0

    def test_worker_start_stop(self) -> None:
        """Test worker start and stop operations."""
        worker = FilePipelineWorker()

        # Add a simple task
        class QuickTask(WorkerTask):
            def execute(self):
                return "quick_result"

            def get_name(self):
                return "QuickTask"

        worker.add_task(QuickTask())

        # Start worker
        worker.start()

        # Wait for completion (this will wait for the worker to finish)
        success = worker.wait_for_completion(5000)  # 5 second timeout
        assert success, "Worker should complete successfully"

        # Worker should have finished
        assert not worker.is_running()

        # Clean up worker properly
        worker.quit()
        worker.wait()  # Wait for thread to finish

    def test_worker_force_stop(self) -> None:
        """Test worker force stop."""
        worker = FilePipelineWorker()

        # Add a long-running task
        class LongTask(WorkerTask):
            def execute(self):
                time.sleep(10)  # 10 second task
                return "long_result"

            def get_name(self):
                return "LongTask"

        worker.add_task(LongTask())
        worker.start()

        # Force stop immediately
        worker.force_stop()
        assert not worker.is_running()

        # Clean up worker properly
        worker.quit()
        worker.wait()  # Wait for thread to finish

    def test_worker_basic_functionality(self) -> None:
        """Test basic worker functionality."""
        worker = FilePipelineWorker()

        # Add a test task
        class TestTask(WorkerTask):
            def execute(self):
                return "test_result"

            def get_name(self):
                return "TestTask"

        worker.add_task(TestTask())
        worker.start()

        # Wait for completion
        success = worker.wait_for_completion(5000)
        assert success, "Worker should complete successfully"

        # Verify worker finished
        assert not worker.is_running()

        # Clean up worker properly
        worker.quit()
        worker.wait()  # Wait for thread to finish

    def test_worker_error_handling(self, qapp) -> None:
        """Test worker error handling and signal emission."""
        worker = FilePipelineWorker()

        # Create signal spies
        task_error_spy = QSignalSpy(worker.task_error)
        task_finished_spy = QSignalSpy(worker.task_finished)

        # Add a task that will fail
        class FailingTask(WorkerTask):
            def execute(self):
                raise Exception("Test error")

            def get_name(self):
                return "FailingTask"

        worker.add_task(FailingTask())
        worker.start()
        worker.wait_for_completion(5000)

        # Verify error signal was emitted
        assert len(task_error_spy) == 1
        assert task_error_spy[0][0] == "FailingTask"
        assert "Test error" in task_error_spy[0][1]

        # Verify task finished signal with failure
        assert len(task_finished_spy) == 1
        assert task_finished_spy[0][0] == "FailingTask"
        assert task_finished_spy[0][2] == False  # failure

        # Clean up worker properly
        worker.quit()
        worker.wait()  # Wait for thread to finish


class TestFilePipelineWorkerIntegration:
    """Test FilePipelineWorker integration with ViewModel."""

    def test_viewmodel_worker_integration(self) -> None:
        """Test integration between BaseViewModel and FilePipelineWorker."""
        viewmodel = BaseViewModel()
        viewmodel.initialize()

        # Create worker through ViewModel
        worker = viewmodel.create_worker()
        assert worker is not None
        assert viewmodel.has_worker()
        assert not viewmodel.is_worker_running()

        # Add a test task
        class TestTask(WorkerTask):
            def execute(self):
                return "integration_test_result"

            def get_name(self):
                return "IntegrationTestTask"

        viewmodel.add_worker_task(TestTask())
        assert viewmodel.get_worker_queue_size() == 1

        # Start worker
        viewmodel.start_worker()

        # Wait for completion
        success = viewmodel.wait_for_worker(5000)
        assert success, "Worker should complete successfully"
        assert not viewmodel.is_worker_running()

        # Clean up worker properly
        if viewmodel.has_worker():
            viewmodel.stop_worker()
            viewmodel.wait_for_worker(5000)

    def test_viewmodel_worker_basic(self) -> None:
        """Test basic ViewModel worker functionality."""
        viewmodel = BaseViewModel()
        viewmodel.initialize()

        # Create worker and add task
        viewmodel.create_worker()

        class TestTask(WorkerTask):
            def execute(self):
                return "basic_test_result"

            def get_name(self):
                return "BasicTestTask"

        viewmodel.add_worker_task(TestTask())
        viewmodel.start_worker()

        # Wait for completion
        success = viewmodel.wait_for_worker(5000)
        assert success, "Worker should complete successfully"

        # Verify worker finished
        assert not viewmodel.is_worker_running()

        # Clean up worker properly
        if viewmodel.has_worker():
            viewmodel.stop_worker()
            viewmodel.wait_for_worker(5000)


class TestFilePipelineWorkerConcurrency:
    """Test FilePipelineWorker in concurrent scenarios."""

    def test_concurrent_task_addition(self) -> None:
        """Test adding tasks from multiple threads."""
        worker = FilePipelineWorker()
        results = []

        def add_tasks_worker(worker_id):
            for i in range(5):
                task = FileScanningTask([f"/path_{worker_id}_{i}"], [".mkv"])
                worker.add_task(task)
                results.append(worker.get_queue_size())

        # Create multiple threads adding tasks
        threads = []
        for i in range(3):
            thread = threading.Thread(target=add_tasks_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Verify final queue size
        assert worker.get_queue_size() == 15
        assert len(results) == 15

    def test_worker_lifecycle_management(self) -> None:
        """Test worker lifecycle management from multiple threads."""
        viewmodel = BaseViewModel()
        viewmodel.initialize()

        def worker_lifecycle_thread(thread_id):
            try:
                # Create worker
                worker = viewmodel.create_worker()

                # Add task
                task = FileScanningTask([f"/thread_{thread_id}"], [".mkv"])
                viewmodel.add_worker_task(task)

                # Start and wait
                viewmodel.start_worker()
                viewmodel.wait_for_worker(5000)

                # Clean up worker
                if viewmodel.has_worker():
                    viewmodel.stop_worker()
                    viewmodel.wait_for_worker(5000)

                return True
            except Exception:
                return False

        # Run multiple worker lifecycles concurrently
        threads = []
        results = []

        for i in range(3):
            thread = threading.Thread(target=lambda: results.append(worker_lifecycle_thread(i)))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All should succeed
        assert all(results)


if __name__ == "__main__":
    pytest.main([__file__])
