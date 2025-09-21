"""Tests for parallel pipeline manager functionality."""

import unittest
from datetime import datetime
from pathlib import Path
from typing import NoReturn
from unittest.mock import MagicMock

import pytest

from src.core.models import AnimeFile
from src.core.parallel_pipeline_manager import ParallelPipelineManager, PipelineStage


class TestParallelPipelineManager(unittest.TestCase):
    """Test cases for parallel pipeline manager functionality."""

    def setUp(self) -> None:
        """Set up test fixtures before each test method."""
        self.pipeline_manager = ParallelPipelineManager(max_workers=2)

        # Create test files
        self.test_files = []
        for i in range(3):
            file = AnimeFile(
                file_path=Path(f"/path/to/anime/Test Anime {i}.mp4"),
                filename=f"Test Anime {i}.mp4",
                file_size=1024 * 1024,
                file_extension=".mp4",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            self.test_files.append(file)

    def tearDown(self) -> None:
        """Clean up test fixtures after each test method."""
        self.pipeline_manager.cancel_pipeline()

    def test_pipeline_manager_initialization(self) -> None:
        """Test that pipeline manager initializes correctly."""
        assert self.pipeline_manager.max_workers == 2
        assert self.pipeline_manager.executor_manager is not None
        assert len(self.pipeline_manager.task_definitions) == 0
        assert len(self.pipeline_manager.running_futures) == 0
        assert len(self.pipeline_manager.completed_stages) == 0
        assert not self.pipeline_manager._cancelled

    def test_add_task_definition(self) -> None:
        """Test adding task definitions to the pipeline."""

        def mock_task_factory():
            return MagicMock()

        def mock_result_handler(result) -> None:
            pass

        def mock_progress_callback(progress, total) -> None:
            pass

        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.SCANNING,
            task_factory=mock_task_factory,
            dependencies=set(),
            result_handler=mock_result_handler,
            progress_callback=mock_progress_callback,
        )

        assert len(self.pipeline_manager.task_definitions) == 1
        assert PipelineStage.SCANNING in self.pipeline_manager.task_definitions

        task_def = self.pipeline_manager.task_definitions[PipelineStage.SCANNING]
        assert task_def.stage == PipelineStage.SCANNING
        assert task_def.dependencies == set()
        assert task_def.result_handler == mock_result_handler
        assert task_def.progress_callback == mock_progress_callback

    def test_get_ready_stages_no_dependencies(self) -> None:
        """Test getting ready stages when there are no dependencies."""

        def mock_task_factory():
            return MagicMock()

        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.SCANNING,
            task_factory=mock_task_factory,
            dependencies=set(),
        )

        ready_stages = self.pipeline_manager._get_ready_stages()
        assert ready_stages == {PipelineStage.SCANNING}

    def test_get_ready_stages_with_dependencies(self) -> None:
        """Test getting ready stages with dependencies."""

        def mock_task_factory():
            return MagicMock()

        # Add scanning task (no dependencies)
        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.SCANNING,
            task_factory=mock_task_factory,
            dependencies=set(),
        )

        # Add grouping task (depends on scanning)
        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.GROUPING,
            task_factory=mock_task_factory,
            dependencies={PipelineStage.SCANNING},
        )

        # Initially only scanning should be ready
        ready_stages = self.pipeline_manager._get_ready_stages()
        assert ready_stages == {PipelineStage.SCANNING}

        # Mark scanning as completed
        self.pipeline_manager.completed_stages.add(PipelineStage.SCANNING)

        # Now grouping should be ready
        ready_stages = self.pipeline_manager._get_ready_stages()
        assert ready_stages == {PipelineStage.GROUPING}

    def test_execute_stage_task_success(self) -> None:
        """Test successful execution of a stage task."""
        mock_task = MagicMock()
        mock_task.execute.return_value = "test_result"

        result = self.pipeline_manager._execute_stage_task(PipelineStage.SCANNING, mock_task)

        assert result == "test_result"
        mock_task.execute.assert_called_once()

    def test_execute_stage_task_failure(self) -> None:
        """Test failure handling in stage task execution."""
        mock_task = MagicMock()
        mock_task.execute.side_effect = Exception("Test error")

        with pytest.raises(Exception) as context:
            self.pipeline_manager._execute_stage_task(PipelineStage.SCANNING, mock_task)

        assert str(context.value) == "Test error"

    def test_execute_stage_task_no_execute_method(self) -> None:
        """Test handling of task without execute method."""
        mock_task = MagicMock()
        del mock_task.execute  # Remove execute method

        result = self.pipeline_manager._execute_stage_task(PipelineStage.SCANNING, mock_task)

        assert result is None

    def test_handle_completed_stage_success(self) -> None:
        """Test handling of a successfully completed stage."""
        mock_future = MagicMock()
        mock_future.result.return_value = "test_result"

        def mock_result_handler(result) -> None:
            mock_result_handler.called = True
            mock_result_handler.result = result

        mock_result_handler.called = False
        mock_result_handler.result = None

        # Add task definition first
        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.SCANNING,
            task_factory=MagicMock,
            dependencies=set(),
            result_handler=mock_result_handler,
        )

        # Add to running futures to simulate a running task
        self.pipeline_manager.running_futures[PipelineStage.SCANNING] = mock_future

        self.pipeline_manager._handle_completed_stage(PipelineStage.SCANNING, mock_future)

        assert PipelineStage.SCANNING in self.pipeline_manager.completed_stages
        assert self.pipeline_manager.stage_results[PipelineStage.SCANNING] == "test_result"
        assert mock_result_handler.called
        assert mock_result_handler.result == "test_result"
        assert PipelineStage.SCANNING not in self.pipeline_manager.running_futures

    def test_handle_completed_stage_failure(self) -> None:
        """Test handling of a failed stage."""
        mock_future = MagicMock()
        mock_future.result.side_effect = Exception("Test error")

        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.SCANNING,
            task_factory=MagicMock,
            dependencies=set(),
        )

        # Should not raise exception
        self.pipeline_manager._handle_completed_stage(PipelineStage.SCANNING, mock_future)

        # Stage should still be marked as completed to avoid retry
        assert PipelineStage.SCANNING in self.pipeline_manager.completed_stages

    def test_handle_completed_stage_result_handler_failure(self) -> None:
        """Test handling when result handler fails."""
        mock_future = MagicMock()
        mock_future.result.return_value = "test_result"

        def failing_result_handler(result) -> NoReturn:
            raise Exception("Handler error")

        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.SCANNING,
            task_factory=MagicMock,
            dependencies=set(),
            result_handler=failing_result_handler,
        )

        # Should not raise exception
        self.pipeline_manager._handle_completed_stage(PipelineStage.SCANNING, mock_future)

        # Stage should still be marked as completed
        assert PipelineStage.SCANNING in self.pipeline_manager.completed_stages

    def test_cancel_pipeline(self) -> None:
        """Test pipeline cancellation."""
        self.pipeline_manager._cancelled = False

        # Add a mock future
        mock_future = MagicMock()
        mock_future.done.return_value = False
        self.pipeline_manager.running_futures[PipelineStage.SCANNING] = mock_future

        self.pipeline_manager.cancel_pipeline()

        assert self.pipeline_manager._cancelled
        mock_future.cancel.assert_called_once()

    def test_get_progress(self) -> None:
        """Test getting pipeline progress information."""
        # Add task definitions
        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.SCANNING,
            task_factory=MagicMock,
            dependencies=set(),
        )
        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.GROUPING,
            task_factory=MagicMock,
            dependencies={PipelineStage.SCANNING},
        )

        # Mark scanning as completed
        self.pipeline_manager.completed_stages.add(PipelineStage.SCANNING)

        # Add running future for grouping
        mock_future = MagicMock()
        self.pipeline_manager.running_futures[PipelineStage.GROUPING] = mock_future

        progress = self.pipeline_manager.get_progress()

        assert progress["total_stages"] == 2
        assert progress["completed_stages"] == 1
        assert progress["running_stages"] == 1
        assert progress["progress_percentage"] == 50.0
        assert "scanning" in progress["completed_stage_names"]
        assert "grouping" in progress["running_stage_names"]

    def test_get_progress_empty_pipeline(self) -> None:
        """Test getting progress for empty pipeline."""
        progress = self.pipeline_manager.get_progress()

        assert progress["total_stages"] == 0
        assert progress["completed_stages"] == 0
        assert progress["running_stages"] == 0
        assert progress["progress_percentage"] == 0


if __name__ == "__main__":
    unittest.main()
