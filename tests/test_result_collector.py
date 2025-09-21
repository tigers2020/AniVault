"""Tests for result collector functionality."""

import unittest
from unittest.mock import MagicMock, patch
from concurrent.futures import Future
from datetime import datetime

from src.core.result_collector import ResultCollector, TaskResult, StageResult
from src.core.pipeline_stages import PipelineStage


class TestResultCollector(unittest.TestCase):

    def setUp(self):
        self.result_collector = ResultCollector()

    def test_result_collector_initialization(self):
        """Test that result collector initializes correctly."""
        self.assertEqual(len(self.result_collector.stage_results), 0)
        self.assertEqual(len(self.result_collector.completed_futures), 0)
        self.assertEqual(len(self.result_collector.failed_futures), 0)

    def test_task_result_creation(self):
        """Test TaskResult creation and properties."""
        # Successful task result
        success_result = TaskResult(
            success=True,
            result="test_result",
            metadata={"stage": "test"}
        )
        
        self.assertTrue(success_result.success)
        self.assertEqual(success_result.result, "test_result")
        self.assertIsNone(success_result.error)
        self.assertIsNone(success_result.error_message)
        self.assertEqual(success_result.metadata["stage"], "test")

        # Failed task result
        error = Exception("Test error")
        failed_result = TaskResult(
            success=False,
            error=error,
            error_message="Test error message",
            metadata={"stage": "test"}
        )
        
        self.assertFalse(failed_result.success)
        self.assertEqual(failed_result.error, error)
        self.assertEqual(failed_result.error_message, "Test error message")

    def test_stage_result_properties(self):
        """Test StageResult properties and calculations."""
        stage_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=10,
            successful_tasks=8,
            failed_tasks=2
        )
        
        self.assertEqual(stage_result.success_rate, 80.0)
        self.assertTrue(stage_result.has_partial_success)
        self.assertEqual(len(stage_result.results), 0)
        self.assertEqual(len(stage_result.errors), 0)

    def test_collect_results_from_futures_success(self):
        """Test collecting results from successful futures."""
        # Create mock futures
        future1 = Future()
        future2 = Future()
        
        # Set results
        future1.set_result("result1")
        future2.set_result("result2")
        
        future_to_stage = {
            future1: PipelineStage.SCANNING,
            future2: PipelineStage.GROUPING
        }
        
        results = self.result_collector.collect_results_from_futures(future_to_stage)
        
        self.assertEqual(len(results), 2)
        self.assertIn(PipelineStage.SCANNING, results)
        self.assertIn(PipelineStage.GROUPING, results)
        
        # Check scanning stage results
        scanning_result = results[PipelineStage.SCANNING]
        self.assertTrue(scanning_result.success)
        self.assertEqual(scanning_result.total_tasks, 1)
        self.assertEqual(scanning_result.successful_tasks, 1)
        self.assertEqual(scanning_result.failed_tasks, 0)
        self.assertEqual(len(scanning_result.results), 1)
        self.assertTrue(scanning_result.results[0].success)
        self.assertEqual(scanning_result.results[0].result, "result1")

    def test_collect_results_from_futures_with_failures(self):
        """Test collecting results from futures with failures."""
        # Create mock futures
        future1 = Future()
        future2 = Future()
        
        # Set results - one success, one failure
        future1.set_result("success_result")
        future2.set_exception(Exception("Test error"))
        
        future_to_stage = {
            future1: PipelineStage.SCANNING,
            future2: PipelineStage.SCANNING  # Same stage, mixed results
        }
        
        results = self.result_collector.collect_results_from_futures(future_to_stage)
        
        self.assertEqual(len(results), 1)  # Only one stage
        self.assertIn(PipelineStage.SCANNING, results)
        
        # Check scanning stage results
        scanning_result = results[PipelineStage.SCANNING]
        self.assertTrue(scanning_result.success)  # Overall success due to partial success
        self.assertEqual(scanning_result.total_tasks, 2)
        self.assertEqual(scanning_result.successful_tasks, 1)
        self.assertEqual(scanning_result.failed_tasks, 1)
        self.assertTrue(scanning_result.has_partial_success)
        self.assertEqual(len(scanning_result.results), 2)
        self.assertEqual(len(scanning_result.errors), 1)

    def test_collect_results_from_futures_all_failures(self):
        """Test collecting results when all futures fail."""
        # Create mock futures
        future1 = Future()
        future2 = Future()
        
        # Set exceptions
        future1.set_exception(Exception("Error 1"))
        future2.set_exception(Exception("Error 2"))
        
        future_to_stage = {
            future1: PipelineStage.SCANNING,
            future2: PipelineStage.SCANNING
        }
        
        results = self.result_collector.collect_results_from_futures(future_to_stage)
        
        # Check scanning stage results
        scanning_result = results[PipelineStage.SCANNING]
        self.assertFalse(scanning_result.success)  # Complete failure
        self.assertEqual(scanning_result.total_tasks, 2)
        self.assertEqual(scanning_result.successful_tasks, 0)
        self.assertEqual(scanning_result.failed_tasks, 2)
        self.assertFalse(scanning_result.has_partial_success)
        self.assertEqual(len(scanning_result.results), 2)
        self.assertEqual(len(scanning_result.errors), 2)

    def test_get_stage_summary(self):
        """Test getting stage summary."""
        # Create a stage result with mixed success
        stage_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=5,
            successful_tasks=3,
            failed_tasks=2
        )
        stage_result.errors = ["Error 1", "Error 2"]
        
        self.result_collector.stage_results[PipelineStage.SCANNING] = stage_result
        
        summary = self.result_collector.get_stage_summary(PipelineStage.SCANNING)
        
        self.assertEqual(summary["stage"], "scanning")
        self.assertTrue(summary["success"])
        self.assertEqual(summary["success_rate"], 60.0)
        self.assertEqual(summary["total_tasks"], 5)
        self.assertEqual(summary["successful_tasks"], 3)
        self.assertEqual(summary["failed_tasks"], 2)
        self.assertTrue(summary["has_partial_success"])
        self.assertEqual(summary["error_count"], 2)
        self.assertEqual(len(summary["errors"]), 2)

    def test_get_stage_summary_nonexistent_stage(self):
        """Test getting summary for nonexistent stage."""
        summary = self.result_collector.get_stage_summary(PipelineStage.SCANNING)
        
        self.assertIn("error", summary)
        self.assertIn("No results found", summary["error"])

    def test_get_overall_summary(self):
        """Test getting overall summary."""
        # Create multiple stage results
        scanning_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=3,
            successful_tasks=3,
            failed_tasks=0
        )
        
        grouping_result = StageResult(
            stage=PipelineStage.GROUPING,
            success=True,
            total_tasks=2,
            successful_tasks=1,
            failed_tasks=1
        )
        
        self.result_collector.stage_results[PipelineStage.SCANNING] = scanning_result
        self.result_collector.stage_results[PipelineStage.GROUPING] = grouping_result
        
        summary = self.result_collector.get_overall_summary()
        
        self.assertEqual(summary["total_stages"], 2)
        self.assertEqual(summary["successful_stages"], 2)
        self.assertEqual(summary["failed_stages"], 0)
        self.assertEqual(summary["total_tasks"], 5)
        self.assertEqual(summary["successful_tasks"], 4)
        self.assertEqual(summary["failed_tasks"], 1)
        self.assertEqual(summary["overall_success_rate"], 80.0)
        self.assertIn("stage_summaries", summary)

    def test_has_failures(self):
        """Test checking for failures."""
        # Initially no failures
        self.assertFalse(self.result_collector.has_failures())
        
        # Add a failed stage
        failed_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=False,
            total_tasks=1,
            successful_tasks=0,
            failed_tasks=1
        )
        self.result_collector.stage_results[PipelineStage.SCANNING] = failed_result
        
        self.assertTrue(self.result_collector.has_failures())

    def test_get_failed_stages(self):
        """Test getting failed stages."""
        # Add mixed results
        success_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=1,
            successful_tasks=1,
            failed_tasks=0
        )
        
        failed_result = StageResult(
            stage=PipelineStage.GROUPING,
            success=False,
            total_tasks=1,
            successful_tasks=0,
            failed_tasks=1
        )
        
        self.result_collector.stage_results[PipelineStage.SCANNING] = success_result
        self.result_collector.stage_results[PipelineStage.GROUPING] = failed_result
        
        failed_stages = self.result_collector.get_failed_stages()
        
        self.assertEqual(len(failed_stages), 1)
        self.assertIn(PipelineStage.GROUPING, failed_stages)

    def test_get_successful_results(self):
        """Test getting successful results for a stage."""
        # Create stage result with mixed success
        stage_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=3,
            successful_tasks=2,
            failed_tasks=1
        )
        
        # Add task results
        stage_result.results = [
            TaskResult(success=True, result="result1"),
            TaskResult(success=False, error=Exception("Error")),
            TaskResult(success=True, result="result2")
        ]
        
        self.result_collector.stage_results[PipelineStage.SCANNING] = stage_result
        
        successful_results = self.result_collector.get_successful_results(PipelineStage.SCANNING)
        
        self.assertEqual(len(successful_results), 2)
        self.assertIn("result1", successful_results)
        self.assertIn("result2", successful_results)

    def test_get_failed_tasks(self):
        """Test getting failed tasks for a stage."""
        # Create stage result with mixed success
        stage_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=3,
            successful_tasks=1,
            failed_tasks=2
        )
        
        # Add task results
        error1 = Exception("Error 1")
        error2 = Exception("Error 2")
        stage_result.results = [
            TaskResult(success=True, result="success_result"),
            TaskResult(success=False, error=error1),
            TaskResult(success=False, error=error2)
        ]
        
        self.result_collector.stage_results[PipelineStage.SCANNING] = stage_result
        
        failed_tasks = self.result_collector.get_failed_tasks(PipelineStage.SCANNING)
        
        self.assertEqual(len(failed_tasks), 2)
        self.assertEqual(failed_tasks[0].error, error1)
        self.assertEqual(failed_tasks[1].error, error2)


if __name__ == "__main__":
    unittest.main()
