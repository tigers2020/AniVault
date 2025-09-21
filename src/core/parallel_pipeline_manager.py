"""Parallel pipeline manager for orchestrating file processing tasks.

This module provides functionality to execute file processing pipeline stages
in parallel where possible, while maintaining proper dependency resolution
and result handling.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .models import AnimeFile, FileGroup
from .pipeline_stages import PipelineStage
from .result_collector import ResultCollector, StageResult
from .thread_executor_manager import get_thread_executor_manager
from .services.file_processing_tasks import (
    ConcreteFileScanningTask,
    ConcreteFileGroupingTask,
    ConcreteFileParsingTask,
    ConcreteMetadataRetrievalTask,
    ConcreteGroupBasedMetadataRetrievalTask,
    ConcreteFileMovingTask,
)


# Logger for this module
logger = logging.getLogger(__name__)




@dataclass
class PipelineTask:
    """Represents a pipeline task with its dependencies and metadata."""
    stage: PipelineStage
    task_factory: Callable[[], Any]
    dependencies: Set[PipelineStage]
    result_handler: Optional[Callable[[Any], None]] = None
    progress_callback: Optional[Callable[[int, int], None]] = None


class ParallelPipelineManager:
    """Manages parallel execution of file processing pipeline stages.
    
    This class orchestrates the execution of pipeline stages, ensuring that
    dependencies are respected while maximizing parallelization opportunities.
    """

    def __init__(self, max_workers: int = 4):
        """Initialize the parallel pipeline manager.
        
        Args:
            max_workers: Maximum number of worker threads for pipeline orchestration
        """
        self.max_workers = max_workers
        self.executor_manager = get_thread_executor_manager()
        self.running_futures: Dict[PipelineStage, Future] = {}
        self.completed_stages: Set[PipelineStage] = set()
        self.stage_results: Dict[PipelineStage, Any] = {}
        self.task_definitions: Dict[PipelineStage, PipelineTask] = {}
        self._cancelled = False

    def add_task_definition(
        self,
        stage: PipelineStage,
        task_factory: Callable[[], Any],
        dependencies: Set[PipelineStage],
        result_handler: Optional[Callable[[Any], None]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """Add a task definition to the pipeline.
        
        Args:
            stage: The pipeline stage
            task_factory: Function that creates the task instance
            dependencies: Set of stages that must complete before this stage
            result_handler: Optional handler for stage results
            progress_callback: Optional progress callback
        """
        self.task_definitions[stage] = PipelineTask(
            stage=stage,
            task_factory=task_factory,
            dependencies=dependencies,
            result_handler=result_handler,
            progress_callback=progress_callback,
        )
        logger.debug(f"Added task definition for stage: {stage}")

    def execute_pipeline(self) -> Dict[PipelineStage, StageResult]:
        """Execute the pipeline with parallelization where possible.
        
        Returns:
            Dictionary mapping stage names to their detailed results
        """
        logger.info("Starting parallel pipeline execution")
        self._cancelled = False
        self.completed_stages.clear()
        self.stage_results.clear()
        self.running_futures.clear()

        # Initialize result collector
        result_collector = ResultCollector()

        try:
            # Use ThreadPoolExecutor for pipeline orchestration
            with self.executor_manager.get_general_executor() as executor:
                # Continue until all stages are completed
                while len(self.completed_stages) < len(self.task_definitions) and not self._cancelled:
                    # Find stages that are ready to run (dependencies satisfied)
                    ready_stages = self._get_ready_stages()
                    
                    if not ready_stages:
                        # No stages ready, wait for current tasks to complete
                        self._wait_for_completion(executor)
                        continue

                    # Submit ready stages to executor
                    for stage in ready_stages:
                        if stage not in self.running_futures:
                            self._submit_stage(executor, stage)

                    # Process completed tasks with enhanced result collection
                    self._process_completed_tasks_with_collector(executor, result_collector)

            if self._cancelled:
                logger.info("Pipeline execution cancelled")
            else:
                logger.info("Pipeline execution completed successfully")

            # Get final results from collector
            final_results = result_collector.get_overall_summary()
            logger.info(f"Pipeline summary: {final_results}")

            return result_collector.stage_results

        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            self.cancel_pipeline()
            raise

    def _get_ready_stages(self) -> Set[PipelineStage]:
        """Get stages that are ready to run (dependencies satisfied).
        
        Returns:
            Set of stages ready for execution
        """
        ready_stages = set()
        
        for stage, task_def in self.task_definitions.items():
            # Skip if already running or completed
            if stage in self.running_futures or stage in self.completed_stages:
                continue
                
            # Check if all dependencies are satisfied
            if task_def.dependencies.issubset(self.completed_stages):
                ready_stages.add(stage)
                
        return ready_stages

    def _submit_stage(self, executor: ThreadPoolExecutor, stage: PipelineStage) -> None:
        """Submit a stage to the executor.
        
        Args:
            executor: ThreadPoolExecutor instance
            stage: Stage to submit
        """
        task_def = self.task_definitions[stage]
        
        # Create and submit the task
        task = task_def.task_factory()
        future = executor.submit(self._execute_stage_task, stage, task)
        self.running_futures[stage] = future
        
        logger.debug(f"Submitted stage {stage} to executor")

    def _execute_stage_task(self, stage: PipelineStage, task: Any) -> Any:
        """Execute a stage task and return the result.
        
        Args:
            stage: The pipeline stage
            task: Task instance to execute
            
        Returns:
            Task execution result
        """
        try:
            logger.debug(f"Executing stage {stage}")
            
            # Execute the task
            if hasattr(task, 'execute'):
                result = task.execute()
            else:
                logger.warning(f"Task for stage {stage} does not have execute method")
                result = None
                
            logger.info(f"Stage {stage} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Stage {stage} failed: {e}", exc_info=True)
            raise

    def _process_completed_tasks(self, executor: ThreadPoolExecutor) -> None:
        """Process completed tasks and handle their results.
        
        Args:
            executor: ThreadPoolExecutor instance
        """
        completed_futures = []
        
        for stage, future in self.running_futures.items():
            if future.done():
                completed_futures.append((stage, future))
        
        for stage, future in completed_futures:
            self._handle_completed_stage(stage, future)

    def _process_completed_tasks_with_collector(
        self, 
        executor: ThreadPoolExecutor, 
        result_collector: ResultCollector
    ) -> None:
        """Process completed tasks with enhanced result collection.
        
        Args:
            executor: ThreadPoolExecutor instance
            result_collector: ResultCollector instance for detailed result handling
        """
        completed_futures = []
        
        for stage, future in self.running_futures.items():
            if future.done():
                completed_futures.append((stage, future))
        
        if completed_futures:
            # Create future-to-stage mapping for result collector
            future_to_stage = {future: stage for stage, future in completed_futures}
            
            # Use result collector to process completed futures
            collector_results = result_collector.collect_results_from_futures(future_to_stage)
            
            # Update our internal state and call result handlers
            for stage, future in completed_futures:
                self._handle_completed_stage_with_collector(stage, future, collector_results)

    def _handle_completed_stage_with_collector(
        self, 
        stage: PipelineStage, 
        future: Future, 
        collector_results: Dict[PipelineStage, StageResult]
    ) -> None:
        """Handle a completed stage with enhanced result collection.
        
        Args:
            stage: The completed stage
            future: Future object containing the result
            collector_results: Results from the result collector
        """
        try:
            # Update internal state
            self.completed_stages.add(stage)
            
            # Remove from running futures
            if stage in self.running_futures:
                del self.running_futures[stage]
            
            # Get detailed stage result from collector
            stage_result = collector_results.get(stage)
            if stage_result:
                self.stage_results[stage] = stage_result
                
                # Log detailed results
                if stage_result.success:
                    if stage_result.has_partial_success:
                        logger.info(
                            f"Stage {stage} completed with partial success: "
                            f"{stage_result.successful_tasks}/{stage_result.total_tasks} tasks succeeded"
                        )
                    else:
                        logger.info(f"Stage {stage} completed successfully: {stage_result.total_tasks} tasks")
                else:
                    logger.warning(f"Stage {stage} failed: {stage_result.failed_tasks} tasks failed")
                    
                # Log errors if any
                if stage_result.errors:
                    for error in stage_result.errors[:3]:  # Log first 3 errors
                        logger.warning(f"Stage {stage} error: {error}")
            
            # Call result handler if provided
            task_def = self.task_definitions.get(stage)
            if task_def and task_def.result_handler:
                try:
                    # Pass the stage result to the handler
                    task_def.result_handler(stage_result)
                except Exception as e:
                    logger.error(f"Result handler for stage {stage} failed: {e}")
            
            logger.debug(f"Stage {stage} result handled successfully")
            
        except Exception as e:
            logger.error(f"Failed to handle completed stage {stage}: {e}")
            self.completed_stages.add(stage)  # Mark as completed to avoid retry
            if stage in self.running_futures:
                del self.running_futures[stage]

    def _handle_completed_stage(self, stage: PipelineStage, future: Future) -> None:
        """Handle a completed stage.
        
        Args:
            stage: The completed stage
            future: Future object containing the result
        """
        try:
            # Get the result
            result = future.result()
            self.stage_results[stage] = result
            self.completed_stages.add(stage)
            
            # Remove from running futures
            del self.running_futures[stage]
            
            # Call result handler if provided
            task_def = self.task_definitions[stage]
            if task_def.result_handler:
                try:
                    task_def.result_handler(result)
                except Exception as e:
                    logger.error(f"Result handler for stage {stage} failed: {e}")
            
            logger.info(f"Stage {stage} result handled successfully")
            
        except Exception as e:
            logger.error(f"Failed to handle completed stage {stage}: {e}")
            self.completed_stages.add(stage)  # Mark as completed to avoid retry
            if stage in self.running_futures:
                del self.running_futures[stage]

    def _wait_for_completion(self, executor: ThreadPoolExecutor) -> None:
        """Wait for at least one running task to complete.
        
        Args:
            executor: ThreadPoolExecutor instance
        """
        if not self.running_futures:
            return
            
        # Use as_completed to wait for at least one task
        futures = list(self.running_futures.values())
        for future in as_completed(futures, timeout=1.0):
            # Find which stage completed
            for stage, stage_future in self.running_futures.items():
                if stage_future == future:
                    self._handle_completed_stage(stage, future)
                    break
            break  # Only process one completion per call

    def cancel_pipeline(self) -> None:
        """Cancel the pipeline execution."""
        logger.info("Cancelling pipeline execution")
        self._cancelled = True
        
        # Cancel running futures
        for stage, future in self.running_futures.items():
            if not future.done():
                future.cancel()
                logger.debug(f"Cancelled stage {stage}")

    def get_progress(self) -> Dict[str, Any]:
        """Get current pipeline progress information.
        
        Returns:
            Dictionary with progress information
        """
        total_stages = len(self.task_definitions)
        completed_count = len(self.completed_stages)
        running_count = len(self.running_futures)
        
        return {
            "total_stages": total_stages,
            "completed_stages": completed_count,
            "running_stages": running_count,
            "progress_percentage": (completed_count / total_stages) * 100 if total_stages > 0 else 0,
            "completed_stage_names": [stage.value for stage in self.completed_stages],
            "running_stage_names": [stage.value for stage in self.running_futures.keys()],
        }
