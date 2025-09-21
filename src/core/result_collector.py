"""Result collection and error handling utilities for parallel pipeline execution.

This module provides functionality to collect and handle results from Future objects
with robust error handling for individual tasks and comprehensive result aggregation.
"""

from __future__ import annotations

import logging
from concurrent.futures import Future, as_completed
from dataclasses import dataclass, field
from typing import Any

from .pipeline_stages import PipelineStage

# Logger for this module
logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Represents the result of an individual task execution."""

    success: bool
    result: Any = None
    error: Exception | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Post-initialization to ensure consistency."""
        if self.error and not self.error_message:
            self.error_message = str(self.error)


@dataclass
class StageResult:
    """Represents the aggregated result of a pipeline stage."""

    stage: PipelineStage
    success: bool
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    results: list[TaskResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100

    @property
    def has_partial_success(self) -> bool:
        """Check if there are both successful and failed tasks."""
        return self.successful_tasks > 0 and self.failed_tasks > 0


class ResultCollector:
    """Collects and handles results from Future objects with comprehensive error handling.

    This class provides functionality to collect results from concurrent tasks,
    handle errors gracefully, and aggregate results for pipeline stages.
    """

    def __init__(self):
        """Initialize the result collector."""
        self.stage_results: dict[PipelineStage, StageResult] = {}
        self.completed_futures: set[Future] = set()
        self.failed_futures: set[Future] = set()

    def collect_results_from_futures(
        self, future_to_stage: dict[Future, PipelineStage], timeout: float | None = None
    ) -> dict[PipelineStage, StageResult]:
        """Collect results from multiple Future objects.

        Args:
            future_to_stage: Dictionary mapping Future objects to their pipeline stages
            timeout: Optional timeout for waiting for results

        Returns:
            Dictionary mapping stage names to their aggregated results
        """
        logger.debug(f"Collecting results from {len(future_to_stage)} futures")

        # Initialize stage results
        for stage in set(future_to_stage.values()):
            self.stage_results[stage] = StageResult(
                stage=stage, success=True, total_tasks=0, successful_tasks=0, failed_tasks=0
            )

        # Process completed futures
        try:
            futures = list(future_to_stage.keys())
            for future in as_completed(futures, timeout=timeout):
                stage = future_to_stage[future]
                self._process_completed_future(future, stage)
                self.completed_futures.add(future)

        except Exception as e:
            logger.error(f"Error during result collection: {e}", exc_info=True)
            self._handle_collection_error(e, future_to_stage)

        # Finalize stage results
        self._finalize_stage_results()

        logger.info(f"Result collection completed for {len(self.stage_results)} stages")
        return self.stage_results.copy()

    def _process_completed_future(self, future: Future, stage: PipelineStage) -> None:
        """Process a completed future and update stage results.

        Args:
            future: The completed Future object
            stage: The pipeline stage this future belongs to
        """
        stage_result = self.stage_results[stage]
        stage_result.total_tasks += 1

        try:
            # Get the result from the future
            result = future.result()

            # Create a successful task result
            task_result = TaskResult(
                success=True, result=result, metadata={"stage": stage.value, "completed_at": "now"}
            )

            stage_result.results.append(task_result)
            stage_result.successful_tasks += 1

            logger.debug(f"Successfully processed future for stage {stage}")

        except Exception as e:
            # Handle the exception
            error_message = f"Task failed in stage {stage}: {e!s}"
            logger.warning(error_message, exc_info=True)

            # Create a failed task result
            task_result = TaskResult(
                success=False,
                error=e,
                error_message=error_message,
                metadata={"stage": stage.value, "failed_at": "now"},
            )

            stage_result.results.append(task_result)
            stage_result.errors.append(error_message)
            stage_result.failed_tasks += 1
            self.failed_futures.add(future)

            logger.debug(f"Failed to process future for stage {stage}: {e}")

    def _handle_collection_error(
        self, error: Exception, future_to_stage: dict[Future, PipelineStage]
    ) -> None:
        """Handle errors that occur during result collection.

        Args:
            error: The exception that occurred
            future_to_stage: Dictionary mapping futures to stages
        """
        logger.error(f"Collection error: {error}", exc_info=True)

        # Mark all remaining futures as failed
        for future, stage in future_to_stage.items():
            if future not in self.completed_futures:
                stage_result = self.stage_results[stage]
                stage_result.total_tasks += 1
                stage_result.failed_tasks += 1
                stage_result.success = False

                error_message = f"Collection failed for stage {stage}: {error!s}"
                stage_result.errors.append(error_message)

                task_result = TaskResult(
                    success=False,
                    error=error,
                    error_message=error_message,
                    metadata={"stage": stage.value, "collection_failed_at": "now"},
                )

                stage_result.results.append(task_result)

    def _finalize_stage_results(self) -> None:
        """Finalize stage results by determining overall success status."""
        for stage_result in self.stage_results.values():
            # Determine overall stage success
            if stage_result.failed_tasks == 0:
                stage_result.success = True
            elif stage_result.successful_tasks == 0:
                stage_result.success = False
            else:
                # Partial success - stage succeeded but with some failures
                stage_result.success = True
                logger.info(
                    f"Stage {stage_result.stage} completed with partial success: "
                    f"{stage_result.successful_tasks}/{stage_result.total_tasks} tasks succeeded"
                )

    def get_stage_summary(self, stage: PipelineStage) -> dict[str, Any]:
        """Get a summary of results for a specific stage.

        Args:
            stage: The pipeline stage

        Returns:
            Dictionary with stage result summary
        """
        if stage not in self.stage_results:
            return {"error": f"No results found for stage {stage}"}

        stage_result = self.stage_results[stage]

        return {
            "stage": stage.value,
            "success": stage_result.success,
            "success_rate": stage_result.success_rate,
            "total_tasks": stage_result.total_tasks,
            "successful_tasks": stage_result.successful_tasks,
            "failed_tasks": stage_result.failed_tasks,
            "has_partial_success": stage_result.has_partial_success,
            "error_count": len(stage_result.errors),
            "errors": stage_result.errors[:5],  # Limit to first 5 errors
        }

    def get_overall_summary(self) -> dict[str, Any]:
        """Get an overall summary of all stage results.

        Returns:
            Dictionary with overall pipeline summary
        """
        total_stages = len(self.stage_results)
        successful_stages = sum(1 for sr in self.stage_results.values() if sr.success)
        failed_stages = total_stages - successful_stages

        total_tasks = sum(sr.total_tasks for sr in self.stage_results.values())
        total_successful = sum(sr.successful_tasks for sr in self.stage_results.values())
        total_failed = sum(sr.failed_tasks for sr in self.stage_results.values())

        return {
            "total_stages": total_stages,
            "successful_stages": successful_stages,
            "failed_stages": failed_stages,
            "total_tasks": total_tasks,
            "successful_tasks": total_successful,
            "failed_tasks": total_failed,
            "overall_success_rate": (
                (total_successful / total_tasks * 100) if total_tasks > 0 else 0
            ),
            "stage_summaries": {
                stage.value: self.get_stage_summary(stage) for stage in self.stage_results.keys()
            },
        }

    def has_failures(self) -> bool:
        """Check if there were any failures during execution.

        Returns:
            True if there were any failures, False otherwise
        """
        return any(not sr.success for sr in self.stage_results.values())

    def get_failed_stages(self) -> list[PipelineStage]:
        """Get a list of stages that had failures.

        Returns:
            List of stages with failures
        """
        return [stage for stage, sr in self.stage_results.items() if not sr.success]

    def get_successful_results(self, stage: PipelineStage) -> list[Any]:
        """Get only the successful results for a specific stage.

        Args:
            stage: The pipeline stage

        Returns:
            List of successful results
        """
        if stage not in self.stage_results:
            return []

        stage_result = self.stage_results[stage]
        return [task_result.result for task_result in stage_result.results if task_result.success]

    def get_failed_tasks(self, stage: PipelineStage) -> list[TaskResult]:
        """Get only the failed tasks for a specific stage.

        Args:
            stage: The pipeline stage

        Returns:
            List of failed task results
        """
        if stage not in self.stage_results:
            return []

        stage_result = self.stage_results[stage]
        return [task_result for task_result in stage_result.results if not task_result.success]
