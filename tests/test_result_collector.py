"""Tests for result collector functionality."""

import unittest
from concurrent.futures import Future

from src.core.pipeline_stages import PipelineStage
from src.core.result_collector import ResultCollector, StageResult, TaskResult


class TestResultCollector(unittest.TestCase):
    """Test cases for result collector functionality."""

    def setUp(self) -> None:
        """Set up test fixtures before each test method."""
        self.result_collector = ResultCollector()

    def test_result_collector_initialization(self) -> None:
        """Test that result collector initializes correctly."""
        assert len(self.result_collector.stage_results) == 0
        assert len(self.result_collector.completed_futures) == 0
        assert len(self.result_collector.failed_futures) == 0

    def test_task_result_creation(self) -> None:
        """Test TaskResult creation and properties."""
        # Successful task result
        success_result = TaskResult(success=True, result="test_result", metadata={"stage": "test"})

        assert success_result.success
        assert success_result.result == "test_result"
        assert success_result.error is None
        assert success_result.error_message is None
        assert success_result.metadata["stage"] == "test"

        # Failed task result
        error = Exception("Test error")
        failed_result = TaskResult(
            success=False,
            error=error,
            error_message="Test error message",
            metadata={"stage": "test"},
        )

        assert not failed_result.success
        assert failed_result.error == error
        assert failed_result.error_message == "Test error message"

    def test_stage_result_properties(self) -> None:
        """Test StageResult properties and calculations."""
        stage_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=10,
            successful_tasks=8,
            failed_tasks=2,
        )

        assert stage_result.success_rate == 80.0
        assert stage_result.has_partial_success
        assert len(stage_result.results) == 0
        assert len(stage_result.errors) == 0

    def test_collect_results_from_futures_success(self) -> None:
        """Test collecting results from successful futures."""
        # Create mock futures
        future1 = Future()
        future2 = Future()

        # Set results
        future1.set_result("result1")
        future2.set_result("result2")

        future_to_stage = {future1: PipelineStage.SCANNING, future2: PipelineStage.GROUPING}

        results = self.result_collector.collect_results_from_futures(future_to_stage)

        assert len(results) == 2
        assert PipelineStage.SCANNING in results
        assert PipelineStage.GROUPING in results

        # Check scanning stage results
        scanning_result = results[PipelineStage.SCANNING]
        assert scanning_result.success
        assert scanning_result.total_tasks == 1
        assert scanning_result.successful_tasks == 1
        assert scanning_result.failed_tasks == 0
        assert len(scanning_result.results) == 1
        assert scanning_result.results[0].success
        assert scanning_result.results[0].result == "result1"

    def test_collect_results_from_futures_with_failures(self) -> None:
        """Test collecting results from futures with failures."""
        # Create mock futures
        future1 = Future()
        future2 = Future()

        # Set results - one success, one failure
        future1.set_result("success_result")
        future2.set_exception(Exception("Test error"))

        future_to_stage = {
            future1: PipelineStage.SCANNING,
            future2: PipelineStage.SCANNING,  # Same stage, mixed results
        }

        results = self.result_collector.collect_results_from_futures(future_to_stage)

        assert len(results) == 1  # Only one stage
        assert PipelineStage.SCANNING in results

        # Check scanning stage results
        scanning_result = results[PipelineStage.SCANNING]
        assert scanning_result.success  # Overall success due to partial success
        assert scanning_result.total_tasks == 2
        assert scanning_result.successful_tasks == 1
        assert scanning_result.failed_tasks == 1
        assert scanning_result.has_partial_success
        assert len(scanning_result.results) == 2
        assert len(scanning_result.errors) == 1

    def test_collect_results_from_futures_all_failures(self) -> None:
        """Test collecting results when all futures fail."""
        # Create mock futures
        future1 = Future()
        future2 = Future()

        # Set exceptions
        future1.set_exception(Exception("Error 1"))
        future2.set_exception(Exception("Error 2"))

        future_to_stage = {future1: PipelineStage.SCANNING, future2: PipelineStage.SCANNING}

        results = self.result_collector.collect_results_from_futures(future_to_stage)

        # Check scanning stage results
        scanning_result = results[PipelineStage.SCANNING]
        assert not scanning_result.success  # Complete failure
        assert scanning_result.total_tasks == 2
        assert scanning_result.successful_tasks == 0
        assert scanning_result.failed_tasks == 2
        assert not scanning_result.has_partial_success
        assert len(scanning_result.results) == 2
        assert len(scanning_result.errors) == 2

    def test_get_stage_summary(self) -> None:
        """Test getting stage summary."""
        # Create a stage result with mixed success
        stage_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=5,
            successful_tasks=3,
            failed_tasks=2,
        )
        stage_result.errors = ["Error 1", "Error 2"]

        self.result_collector.stage_results[PipelineStage.SCANNING] = stage_result

        summary = self.result_collector.get_stage_summary(PipelineStage.SCANNING)

        assert summary["stage"] == "scanning"
        assert summary["success"]
        assert summary["success_rate"] == 60.0
        assert summary["total_tasks"] == 5
        assert summary["successful_tasks"] == 3
        assert summary["failed_tasks"] == 2
        assert summary["has_partial_success"]
        assert summary["error_count"] == 2
        assert len(summary["errors"]) == 2

    def test_get_stage_summary_nonexistent_stage(self) -> None:
        """Test getting summary for nonexistent stage."""
        summary = self.result_collector.get_stage_summary(PipelineStage.SCANNING)

        assert "error" in summary
        assert "No results found" in summary["error"]

    def test_get_overall_summary(self) -> None:
        """Test getting overall summary."""
        # Create multiple stage results
        scanning_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=3,
            successful_tasks=3,
            failed_tasks=0,
        )

        grouping_result = StageResult(
            stage=PipelineStage.GROUPING,
            success=True,
            total_tasks=2,
            successful_tasks=1,
            failed_tasks=1,
        )

        self.result_collector.stage_results[PipelineStage.SCANNING] = scanning_result
        self.result_collector.stage_results[PipelineStage.GROUPING] = grouping_result

        summary = self.result_collector.get_overall_summary()

        assert summary["total_stages"] == 2
        assert summary["successful_stages"] == 2
        assert summary["failed_stages"] == 0
        assert summary["total_tasks"] == 5
        assert summary["successful_tasks"] == 4
        assert summary["failed_tasks"] == 1
        assert summary["overall_success_rate"] == 80.0
        assert "stage_summaries" in summary

    def test_has_failures(self) -> None:
        """Test checking for failures."""
        # Initially no failures
        assert not self.result_collector.has_failures()

        # Add a failed stage
        failed_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=False,
            total_tasks=1,
            successful_tasks=0,
            failed_tasks=1,
        )
        self.result_collector.stage_results[PipelineStage.SCANNING] = failed_result

        assert self.result_collector.has_failures()

    def test_get_failed_stages(self) -> None:
        """Test getting failed stages."""
        # Add mixed results
        success_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=1,
            successful_tasks=1,
            failed_tasks=0,
        )

        failed_result = StageResult(
            stage=PipelineStage.GROUPING,
            success=False,
            total_tasks=1,
            successful_tasks=0,
            failed_tasks=1,
        )

        self.result_collector.stage_results[PipelineStage.SCANNING] = success_result
        self.result_collector.stage_results[PipelineStage.GROUPING] = failed_result

        failed_stages = self.result_collector.get_failed_stages()

        assert len(failed_stages) == 1
        assert PipelineStage.GROUPING in failed_stages

    def test_get_successful_results(self) -> None:
        """Test getting successful results for a stage."""
        # Create stage result with mixed success
        stage_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=3,
            successful_tasks=2,
            failed_tasks=1,
        )

        # Add task results
        stage_result.results = [
            TaskResult(success=True, result="result1"),
            TaskResult(success=False, error=Exception("Error")),
            TaskResult(success=True, result="result2"),
        ]

        self.result_collector.stage_results[PipelineStage.SCANNING] = stage_result

        successful_results = self.result_collector.get_successful_results(PipelineStage.SCANNING)

        assert len(successful_results) == 2
        assert "result1" in successful_results
        assert "result2" in successful_results

    def test_get_failed_tasks(self) -> None:
        """Test getting failed tasks for a stage."""
        # Create stage result with mixed success
        stage_result = StageResult(
            stage=PipelineStage.SCANNING,
            success=True,
            total_tasks=3,
            successful_tasks=1,
            failed_tasks=2,
        )

        # Add task results
        error1 = Exception("Error 1")
        error2 = Exception("Error 2")
        stage_result.results = [
            TaskResult(success=True, result="success_result"),
            TaskResult(success=False, error=error1),
            TaskResult(success=False, error=error2),
        ]

        self.result_collector.stage_results[PipelineStage.SCANNING] = stage_result

        failed_tasks = self.result_collector.get_failed_tasks(PipelineStage.SCANNING)

        assert len(failed_tasks) == 2
        assert failed_tasks[0].error == error1
        assert failed_tasks[1].error == error2


if __name__ == "__main__":
    unittest.main()
