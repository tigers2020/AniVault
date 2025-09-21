"""Tests for parallel pipeline manager functionality."""

import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime

from src.core.models import AnimeFile, FileGroup
from src.core.parallel_pipeline_manager import ParallelPipelineManager, PipelineStage, PipelineTask


class TestParallelPipelineManager(unittest.TestCase):

    def setUp(self):
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

    def tearDown(self):
        self.pipeline_manager.cancel_pipeline()

    def test_pipeline_manager_initialization(self):
        """Test that pipeline manager initializes correctly."""
        self.assertEqual(self.pipeline_manager.max_workers, 2)
        self.assertIsNotNone(self.pipeline_manager.executor_manager)
        self.assertEqual(len(self.pipeline_manager.task_definitions), 0)
        self.assertEqual(len(self.pipeline_manager.running_futures), 0)
        self.assertEqual(len(self.pipeline_manager.completed_stages), 0)
        self.assertFalse(self.pipeline_manager._cancelled)

    def test_add_task_definition(self):
        """Test adding task definitions to the pipeline."""
        def mock_task_factory():
            return MagicMock()

        def mock_result_handler(result):
            pass

        def mock_progress_callback(progress, total):
            pass

        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.SCANNING,
            task_factory=mock_task_factory,
            dependencies=set(),
            result_handler=mock_result_handler,
            progress_callback=mock_progress_callback,
        )

        self.assertEqual(len(self.pipeline_manager.task_definitions), 1)
        self.assertIn(PipelineStage.SCANNING, self.pipeline_manager.task_definitions)

        task_def = self.pipeline_manager.task_definitions[PipelineStage.SCANNING]
        self.assertEqual(task_def.stage, PipelineStage.SCANNING)
        self.assertEqual(task_def.dependencies, set())
        self.assertEqual(task_def.result_handler, mock_result_handler)
        self.assertEqual(task_def.progress_callback, mock_progress_callback)

    def test_get_ready_stages_no_dependencies(self):
        """Test getting ready stages when there are no dependencies."""
        def mock_task_factory():
            return MagicMock()

        self.pipeline_manager.add_task_definition(
            stage=PipelineStage.SCANNING,
            task_factory=mock_task_factory,
            dependencies=set(),
        )

        ready_stages = self.pipeline_manager._get_ready_stages()
        self.assertEqual(ready_stages, {PipelineStage.SCANNING})

    def test_get_ready_stages_with_dependencies(self):
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
        self.assertEqual(ready_stages, {PipelineStage.SCANNING})

        # Mark scanning as completed
        self.pipeline_manager.completed_stages.add(PipelineStage.SCANNING)

        # Now grouping should be ready
        ready_stages = self.pipeline_manager._get_ready_stages()
        self.assertEqual(ready_stages, {PipelineStage.GROUPING})

    def test_execute_stage_task_success(self):
        """Test successful execution of a stage task."""
        mock_task = MagicMock()
        mock_task.execute.return_value = "test_result"

        result = self.pipeline_manager._execute_stage_task(PipelineStage.SCANNING, mock_task)

        self.assertEqual(result, "test_result")
        mock_task.execute.assert_called_once()

    def test_execute_stage_task_failure(self):
        """Test failure handling in stage task execution."""
        mock_task = MagicMock()
        mock_task.execute.side_effect = Exception("Test error")

        with self.assertRaises(Exception) as context:
            self.pipeline_manager._execute_stage_task(PipelineStage.SCANNING, mock_task)

        self.assertEqual(str(context.exception), "Test error")

    def test_execute_stage_task_no_execute_method(self):
        """Test handling of task without execute method."""
        mock_task = MagicMock()
        del mock_task.execute  # Remove execute method

        result = self.pipeline_manager._execute_stage_task(PipelineStage.SCANNING, mock_task)

        self.assertIsNone(result)

    def test_handle_completed_stage_success(self):
        """Test handling of a successfully completed stage."""
        mock_future = MagicMock()
        mock_future.result.return_value = "test_result"

        def mock_result_handler(result):
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

        self.assertIn(PipelineStage.SCANNING, self.pipeline_manager.completed_stages)
        self.assertEqual(self.pipeline_manager.stage_results[PipelineStage.SCANNING], "test_result")
        self.assertTrue(mock_result_handler.called)
        self.assertEqual(mock_result_handler.result, "test_result")
        self.assertNotIn(PipelineStage.SCANNING, self.pipeline_manager.running_futures)

    def test_handle_completed_stage_failure(self):
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
        self.assertIn(PipelineStage.SCANNING, self.pipeline_manager.completed_stages)

    def test_handle_completed_stage_result_handler_failure(self):
        """Test handling when result handler fails."""
        mock_future = MagicMock()
        mock_future.result.return_value = "test_result"

        def failing_result_handler(result):
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
        self.assertIn(PipelineStage.SCANNING, self.pipeline_manager.completed_stages)

    def test_cancel_pipeline(self):
        """Test pipeline cancellation."""
        self.pipeline_manager._cancelled = False

        # Add a mock future
        mock_future = MagicMock()
        mock_future.done.return_value = False
        self.pipeline_manager.running_futures[PipelineStage.SCANNING] = mock_future

        self.pipeline_manager.cancel_pipeline()

        self.assertTrue(self.pipeline_manager._cancelled)
        mock_future.cancel.assert_called_once()

    def test_get_progress(self):
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

        self.assertEqual(progress["total_stages"], 2)
        self.assertEqual(progress["completed_stages"], 1)
        self.assertEqual(progress["running_stages"], 1)
        self.assertEqual(progress["progress_percentage"], 50.0)
        self.assertIn("scanning", progress["completed_stage_names"])
        self.assertIn("grouping", progress["running_stage_names"])

    def test_get_progress_empty_pipeline(self):
        """Test getting progress for empty pipeline."""
        progress = self.pipeline_manager.get_progress()

        self.assertEqual(progress["total_stages"], 0)
        self.assertEqual(progress["completed_stages"], 0)
        self.assertEqual(progress["running_stages"], 0)
        self.assertEqual(progress["progress_percentage"], 0)


if __name__ == "__main__":
    unittest.main()
