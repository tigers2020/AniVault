"""Scheduled consistency validation and reconciliation job.

This module provides a background job that periodically executes consistency
validation and reconciliation processes to maintain data consistency between
the MetadataCache and database.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable

from .consistency_validator import ConsistencyValidator, DataConflict
from .reconciliation_strategies import ReconciliationEngine, ReconciliationStrategy, ReconciliationResult
from .consistency_reporter import ConsistencyReporter
from .metadata_cache import MetadataCache

# Configure logging
logger = logging.getLogger(__name__)


class ConsistencyJob:
    """Represents a consistency validation and reconciliation job."""
    
    def __init__(
        self,
        job_id: str,
        validator: ConsistencyValidator,
        reconciliation_engine: ReconciliationEngine,
        reporter: ConsistencyReporter,
        strategy: ReconciliationStrategy = ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH,
        enabled: bool = True
    ):
        self.job_id = job_id
        self.validator = validator
        self.reconciliation_engine = reconciliation_engine
        self.reporter = reporter
        self.strategy = strategy
        self.enabled = enabled
        self.last_run = None
        self.last_result = None
        self.run_count = 0
        self.error_count = 0
    
    def execute(self) -> Dict[str, Any]:
        """Execute the consistency validation and reconciliation job.
        
        Returns:
            Dictionary containing job execution results
        """
        if not self.enabled:
            return {
                "job_id": self.job_id,
                "status": "disabled",
                "message": "Job is disabled"
            }
        
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting consistency job {self.job_id}")
        
        # Create report
        report = self.reporter.create_report(
            job_id=self.job_id,
            report_type="scheduled",
            started_at=start_time
        )
        
        try:
            # Step 1: Validate consistency
            logger.debug(f"Job {self.job_id}: Starting consistency validation")
            conflicts = self.validator.validate_all_consistency()
            
            # Update report with conflicts
            self.reporter.update_report_with_conflicts(report.id, conflicts)
            
            # Step 2: Reconcile conflicts if any found
            reconciliation_result = None
            if conflicts:
                logger.info(f"Job {self.job_id}: Found {len(conflicts)} conflicts, starting reconciliation")
                reconciliation_result = self.reconciliation_engine.reconcile_conflicts(conflicts, self.strategy)
                
                # Update report with resolution results
                self.reporter.update_report_with_resolution(
                    report.id,
                    reconciliation_result.details if reconciliation_result else [],
                    self.strategy,
                    "success" if reconciliation_result and reconciliation_result.success else "partial"
                )
            else:
                logger.info(f"Job {self.job_id}: No conflicts found")
                # Update report with no conflicts
                self.reporter.update_report_with_resolution(
                    report.id,
                    [],
                    self.strategy,
                    "success"
                )
            
            # Step 3: Prepare results
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            result = {
                "job_id": self.job_id,
                "report_id": report.id,
                "status": "success",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "conflicts_found": len(conflicts),
                "conflicts_resolved": reconciliation_result.conflicts_resolved if reconciliation_result else 0,
                "conflicts_failed": reconciliation_result.conflicts_failed if reconciliation_result else 0,
                "strategy_used": self.strategy.value,
                "reconciliation_success": reconciliation_result.success if reconciliation_result else True,
                "conflicts": [self._conflict_to_dict(c) for c in conflicts],
                "reconciliation_details": reconciliation_result.details if reconciliation_result else [],
                "reconciliation_errors": reconciliation_result.errors if reconciliation_result else []
            }
            
            # Update job state
            self.last_run = end_time
            self.last_result = result
            self.run_count += 1
            
            logger.info(f"Job {self.job_id} completed successfully in {duration:.2f}s")
            return result
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            error_msg = f"Job {self.job_id} failed: {e}"
            logger.error(error_msg, exc_info=True)
            
            # Update report with error
            self.reporter.update_report_with_error(
                report.id,
                str(e),
                {"exception_type": type(e).__name__, "traceback": str(e)},
                "failed"
            )
            
            result = {
                "job_id": self.job_id,
                "report_id": report.id,
                "status": "error",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "error": str(e),
                "conflicts_found": 0,
                "conflicts_resolved": 0,
                "conflicts_failed": 0
            }
            
            # Update job state
            self.last_run = end_time
            self.last_result = result
            self.run_count += 1
            self.error_count += 1
            
            return result
    
    def _conflict_to_dict(self, conflict: DataConflict) -> Dict[str, Any]:
        """Convert DataConflict to dictionary for serialization.
        
        Args:
            conflict: Conflict to convert
            
        Returns:
            Dictionary representation of the conflict
        """
        return {
            "conflict_type": conflict.conflict_type.value,
            "entity_type": conflict.entity_type,
            "entity_id": conflict.entity_id,
            "severity": conflict.severity.value,
            "details": conflict.details,
            "detected_at": conflict.detected_at.isoformat()
        }


class ConsistencyScheduler:
    """Scheduler for consistency validation and reconciliation jobs."""
    
    def __init__(self, metadata_cache: Optional[MetadataCache] = None, db_manager=None):
        """Initialize the consistency scheduler.
        
        Args:
            metadata_cache: MetadataCache instance for validation
            db_manager: DatabaseManager instance for reporting
        """
        self.metadata_cache = metadata_cache or MetadataCache()
        self.db_manager = db_manager
        self.reporter = ConsistencyReporter(db_manager) if db_manager else None
        self.jobs: Dict[str, ConsistencyJob] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False
        self.stop_event = threading.Event()
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []
    
    def add_job(
        self,
        job_id: str,
        interval_seconds: int,
        strategy: ReconciliationStrategy = ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH,
        enabled: bool = True,
        db_manager=None
    ) -> ConsistencyJob:
        """Add a new consistency job.
        
        Args:
            job_id: Unique identifier for the job
            interval_seconds: Interval between job executions in seconds
            strategy: Reconciliation strategy to use
            enabled: Whether the job is enabled
            db_manager: Database manager for the reporter
            
        Returns:
            Created ConsistencyJob instance
        """
        validator = ConsistencyValidator(self.metadata_cache)
        reconciliation_engine = ReconciliationEngine(self.metadata_cache)
        
        # Use provided db_manager or fall back to self.db_manager
        reporter_db_manager = db_manager or self.db_manager
        reporter = ConsistencyReporter(reporter_db_manager) if reporter_db_manager else None
        
        job = ConsistencyJob(
            job_id=job_id,
            validator=validator,
            reconciliation_engine=reconciliation_engine,
            reporter=reporter,
            strategy=strategy,
            enabled=enabled
        )
        
        self.jobs[job_id] = job
        logger.info(f"Added consistency job {job_id} with {interval_seconds}s interval")
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a consistency job.
        
        Args:
            job_id: ID of the job to remove
            
        Returns:
            True if job was removed, False if not found
        """
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f"Removed consistency job {job_id}")
            return True
        return False
    
    def start_scheduler(self, check_interval: int = 60) -> None:
        """Start the consistency scheduler.
        
        Args:
            check_interval: How often to check for jobs to run (seconds)
        """
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.stop_event.clear()
        
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            args=(check_interval,),
            daemon=True,
            name="ConsistencyScheduler"
        )
        self.scheduler_thread.start()
        
        logger.info(f"Started consistency scheduler with {check_interval}s check interval")
    
    def stop_scheduler(self) -> None:
        """Stop the consistency scheduler."""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        self.running = False
        self.stop_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10)
        
        logger.info("Stopped consistency scheduler")
    
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add a callback function to be called after each job execution.
        
        Args:
            callback: Function to call with job results
        """
        self.callbacks.append(callback)
        logger.debug("Added job execution callback")
    
    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """Remove a callback function.
        
        Args:
            callback: Callback function to remove
            
        Returns:
            True if callback was removed, False if not found
        """
        try:
            self.callbacks.remove(callback)
            logger.debug("Removed job execution callback")
            return True
        except ValueError:
            return False
    
    def run_job_now(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Run a specific job immediately.
        
        Args:
            job_id: ID of the job to run
            
        Returns:
            Job execution results or None if job not found
        """
        if job_id not in self.jobs:
            logger.warning(f"Job {job_id} not found")
            return None
        
        job = self.jobs[job_id]
        logger.info(f"Running job {job_id} immediately")
        
        result = job.execute()
        self._notify_callbacks(result)
        
        return result
    
    def run_all_jobs_now(self) -> Dict[str, Dict[str, Any]]:
        """Run all enabled jobs immediately.
        
        Returns:
            Dictionary mapping job IDs to their execution results
        """
        results = {}
        
        for job_id, job in self.jobs.items():
            if job.enabled:
                logger.info(f"Running job {job_id} immediately")
                result = job.execute()
                results[job_id] = result
                self._notify_callbacks(result)
        
        return results
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a specific job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            Job status information or None if job not found
        """
        if job_id not in self.jobs:
            return None
        
        job = self.jobs[job_id]
        return {
            "job_id": job.job_id,
            "enabled": job.enabled,
            "strategy": job.strategy.value,
            "last_run": job.last_run.isoformat() if job.last_run else None,
            "run_count": job.run_count,
            "error_count": job.error_count,
            "last_result": job.last_result
        }
    
    def get_all_job_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all jobs.
        
        Returns:
            Dictionary mapping job IDs to their status information
        """
        return {job_id: self.get_job_status(job_id) for job_id in self.jobs.keys()}
    
    def _scheduler_loop(self, check_interval: int) -> None:
        """Main scheduler loop that runs in a separate thread.
        
        Args:
            check_interval: How often to check for jobs to run (seconds)
        """
        logger.info("Consistency scheduler loop started")
        
        while self.running and not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                for job_id, job in self.jobs.items():
                    if not job.enabled:
                        continue
                    
                    # Check if job should run
                    should_run = False
                    if job.last_run is None:
                        # First run
                        should_run = True
                    else:
                        # Check if enough time has passed
                        time_since_last_run = current_time - job.last_run.timestamp()
                        if time_since_last_run >= check_interval:
                            should_run = True
                    
                    if should_run:
                        logger.debug(f"Scheduler: Running job {job_id}")
                        result = job.execute()
                        self._notify_callbacks(result)
                
                # Sleep for a short time before next check
                self.stop_event.wait(timeout=min(check_interval, 60))
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # Sleep for a bit before retrying
                self.stop_event.wait(timeout=30)
        
        logger.info("Consistency scheduler loop stopped")
    
    def _notify_callbacks(self, result: Dict[str, Any]) -> None:
        """Notify all registered callbacks with job results.
        
        Args:
            result: Job execution result
        """
        for callback in self.callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in job callback: {e}", exc_info=True)


# Global scheduler instance
_global_scheduler: Optional[ConsistencyScheduler] = None


def get_global_scheduler() -> ConsistencyScheduler:
    """Get the global consistency scheduler instance.
    
    Returns:
        Global ConsistencyScheduler instance
    """
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = ConsistencyScheduler()
    return _global_scheduler


def start_global_scheduler(check_interval: int = 60) -> None:
    """Start the global consistency scheduler.
    
    Args:
        check_interval: How often to check for jobs to run (seconds)
    """
    scheduler = get_global_scheduler()
    scheduler.start_scheduler(check_interval)


def stop_global_scheduler() -> None:
    """Stop the global consistency scheduler."""
    global _global_scheduler
    if _global_scheduler:
        _global_scheduler.stop_scheduler()


def add_global_job(
    job_id: str,
    interval_seconds: int,
    strategy: ReconciliationStrategy = ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH,
    enabled: bool = True,
    db_manager=None
) -> ConsistencyJob:
    """Add a job to the global scheduler.
    
    Args:
        job_id: Unique identifier for the job
        interval_seconds: Interval between job executions in seconds
        strategy: Reconciliation strategy to use
        enabled: Whether the job is enabled
        db_manager: Database manager for the reporter
        
    Returns:
        Created ConsistencyJob instance
    """
    scheduler = get_global_scheduler()
    return scheduler.add_job(job_id, interval_seconds, strategy, enabled, db_manager)
