"""
Synchronization scheduler for cache-database synchronization operations.

This module provides a comprehensive scheduler that can handle both consistency
validation and incremental synchronization tasks at configurable intervals.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass

from .consistency_scheduler import ConsistencyScheduler, ConsistencyJob
from .incremental_sync import IncrementalSyncManager, IncrementalSyncResult
from .sync_enums import SyncEntityType
from .metadata_cache import MetadataCache
from .sync_monitoring import SyncOperationType, SyncOperationStatus, sync_monitor

# Configure logging
logger = logging.getLogger(__name__)


class SyncJobType(Enum):
    """Types of synchronization jobs."""
    CONSISTENCY_VALIDATION = "consistency_validation"
    INCREMENTAL_SYNC = "incremental_sync"
    FULL_SYNC = "full_sync"


class SyncTrigger(Enum):
    """Types of triggers that can initiate synchronization."""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    STARTUP = "startup"
    DATA_CHANGE = "data_change"
    ERROR_RECOVERY = "error_recovery"


@dataclass
class SyncJobConfig:
    """Configuration for a synchronization job."""
    job_id: str
    job_type: SyncJobType
    interval_seconds: int
    enabled: bool = True
    trigger_types: List[SyncTrigger] = None
    entity_types: List[SyncEntityType] = None
    priority: int = 1  # Lower number = higher priority
    max_retries: int = 3
    retry_delay_seconds: int = 30
    timeout_seconds: int = 300
    
    def __post_init__(self):
        if self.trigger_types is None:
            self.trigger_types = [SyncTrigger.SCHEDULED]
        if self.entity_types is None:
            self.entity_types = [SyncEntityType.TMDB_METADATA, SyncEntityType.PARSED_FILES]


@dataclass
class SyncJobResult:
    """Result of a synchronization job execution."""
    job_id: str
    job_type: SyncJobType
    trigger: SyncTrigger
    status: SyncOperationStatus
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    records_processed: int = 0
    records_updated: int = 0
    records_inserted: int = 0
    conflicts_found: int = 0
    conflicts_resolved: int = 0
    error_message: Optional[str] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class SyncJob:
    """Represents a synchronization job that can be scheduled."""
    
    def __init__(
        self,
        config: SyncJobConfig,
        metadata_cache: MetadataCache,
        incremental_sync_manager: Optional[IncrementalSyncManager] = None,
        consistency_job: Optional[ConsistencyJob] = None
    ):
        self.config = config
        self.metadata_cache = metadata_cache
        self.incremental_sync_manager = incremental_sync_manager
        self.consistency_job = consistency_job
        
        # Job state
        self.last_run: Optional[datetime] = None
        self.last_result: Optional[SyncJobResult] = None
        self.run_count = 0
        self.error_count = 0
        self.retry_count = 0
        self.is_running = False
        
        # Lock for thread safety
        self._lock = threading.Lock()
    
    def execute(self, trigger: SyncTrigger = SyncTrigger.MANUAL) -> SyncJobResult:
        """Execute the synchronization job.
        
        Args:
            trigger: What triggered this execution
            
        Returns:
            SyncJobResult containing execution details
        """
        with self._lock:
            if self.is_running:
                logger.warning(f"Job {self.config.job_id} is already running, skipping")
                return SyncJobResult(
                    job_id=self.config.job_id,
                    job_type=self.config.job_type,
                    trigger=trigger,
                    status=SyncOperationStatus.FAILED,
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    duration_seconds=0.0,
                    error_message="Job is already running"
                )
            
            if not self.config.enabled:
                logger.debug(f"Job {self.config.job_id} is disabled, skipping")
                return SyncJobResult(
                    job_id=self.config.job_id,
                    job_type=self.config.job_type,
                    trigger=trigger,
                    status=SyncOperationStatus.SKIPPED,
                    start_time=datetime.now(timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    duration_seconds=0.0,
                    error_message="Job is disabled"
                )
            
            self.is_running = True
            self.run_count += 1
        
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting sync job {self.config.job_id} (type: {self.config.job_type.value}, trigger: {trigger.value})")
        
        try:
            result = self._execute_job(trigger, start_time)
            
            # Update job state
            with self._lock:
                self.last_run = start_time
                self.last_result = result
                self.retry_count = 0  # Reset retry count on success
                if result.status == SyncOperationStatus.FAILED:
                    self.error_count += 1
            
            logger.info(f"Sync job {self.config.job_id} completed with status: {result.status.value}")
            return result
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            error_msg = f"Sync job {self.config.job_id} failed: {e}"
            logger.error(error_msg, exc_info=True)
            
            result = SyncJobResult(
                job_id=self.config.job_id,
                job_type=self.config.job_type,
                trigger=trigger,
                status=SyncOperationStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                error_message=str(e)
            )
            
            # Update job state
            with self._lock:
                self.last_run = start_time
                self.last_result = result
                self.error_count += 1
                self.retry_count += 1
            
            return result
        
        finally:
            with self._lock:
                self.is_running = False
    
    def _execute_job(self, trigger: SyncTrigger, start_time: datetime) -> SyncJobResult:
        """Execute the actual job logic based on job type.
        
        Args:
            trigger: What triggered this execution
            start_time: When the job started
            
        Returns:
            SyncJobResult containing execution details
        """
        if self.config.job_type == SyncJobType.CONSISTENCY_VALIDATION:
            return self._execute_consistency_job(trigger, start_time)
        elif self.config.job_type == SyncJobType.INCREMENTAL_SYNC:
            return self._execute_incremental_sync_job(trigger, start_time)
        elif self.config.job_type == SyncJobType.FULL_SYNC:
            return self._execute_full_sync_job(trigger, start_time)
        else:
            raise ValueError(f"Unknown job type: {self.config.job_type}")
    
    def _execute_consistency_job(self, trigger: SyncTrigger, start_time: datetime) -> SyncJobResult:
        """Execute consistency validation job.
        
        Args:
            trigger: What triggered this execution
            start_time: When the job started
            
        Returns:
            SyncJobResult containing execution details
        """
        if not self.consistency_job:
            raise ValueError("Consistency job not configured")
        
        # Execute the consistency job
        consistency_result = self.consistency_job.execute()
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        return SyncJobResult(
            job_id=self.config.job_id,
            job_type=self.config.job_type,
            trigger=trigger,
            status=SyncOperationStatus.SUCCESS if consistency_result["status"] == "success" else SyncOperationStatus.FAILED,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            conflicts_found=consistency_result.get("conflicts_found", 0),
            conflicts_resolved=consistency_result.get("conflicts_resolved", 0),
            error_message=consistency_result.get("error"),
            details=consistency_result
        )
    
    def _execute_incremental_sync_job(self, trigger: SyncTrigger, start_time: datetime) -> SyncJobResult:
        """Execute incremental synchronization job.
        
        Args:
            trigger: What triggered this execution
            start_time: When the job started
            
        Returns:
            SyncJobResult containing execution details
        """
        if not self.incremental_sync_manager:
            raise ValueError("Incremental sync manager not configured")
        
        total_records_processed = 0
        total_records_updated = 0
        total_records_inserted = 0
        sync_results = []
        
        # Execute incremental sync for each configured entity type
        for entity_type in self.config.entity_types:
            try:
                with sync_monitor.operation(
                    operation_type=SyncOperationType.INCREMENTAL_SYNC,
                    entity_type=entity_type.value
                ) as op:
                    result = self.incremental_sync_manager.sync_entity_type(entity_type)
                    sync_results.append(result)
                    
                    total_records_processed += result.records_processed
                    total_records_updated += result.records_updated
                    total_records_inserted += result.records_inserted
                    
                    op.set_status(SyncOperationStatus.SUCCESS if result.status == SyncOperationStatus.SUCCESS else SyncOperationStatus.FAILED)
                    op.set_records_processed(result.records_processed)
                    
            except Exception as e:
                logger.error(f"Incremental sync failed for {entity_type.value}: {e}")
                sync_results.append(IncrementalSyncResult(
                    entity_type=entity_type,
                    records_found=0,
                    records_processed=0,
                    records_updated=0,
                    records_inserted=0,
                    sync_duration_ms=0.0,
                    status=SyncOperationStatus.FAILED,
                    error_message=str(e)
                ))
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Determine overall status
        overall_status = SyncOperationStatus.SUCCESS
        error_messages = []
        
        for result in sync_results:
            if result.status == SyncOperationStatus.FAILED:
                overall_status = SyncOperationStatus.FAILED
                if result.error_message:
                    error_messages.append(f"{result.entity_type.value}: {result.error_message}")
        
        return SyncJobResult(
            job_id=self.config.job_id,
            job_type=self.config.job_type,
            trigger=trigger,
            status=overall_status,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            records_processed=total_records_processed,
            records_updated=total_records_updated,
            records_inserted=total_records_inserted,
            error_message="; ".join(error_messages) if error_messages else None,
            details={"sync_results": [self._sync_result_to_dict(r) for r in sync_results]}
        )
    
    def _execute_full_sync_job(self, trigger: SyncTrigger, start_time: datetime) -> SyncJobResult:
        """Execute full synchronization job.
        
        Args:
            trigger: What triggered this execution
            start_time: When the job started
            
        Returns:
            SyncJobResult containing execution details
        """
        if not self.incremental_sync_manager:
            raise ValueError("Incremental sync manager not configured")
        
        total_records_processed = 0
        total_records_updated = 0
        total_records_inserted = 0
        sync_results = []
        
        # Execute full sync for each configured entity type
        for entity_type in self.config.entity_types:
            try:
                with sync_monitor.operation(
                    operation_type=SyncOperationType.FULL_SYNC,
                    entity_type=entity_type.value
                ) as op:
                    result = self.incremental_sync_manager.sync_entity_type(entity_type, force_full_sync=True)
                    sync_results.append(result)
                    
                    total_records_processed += result.records_processed
                    total_records_updated += result.records_updated
                    total_records_inserted += result.records_inserted
                    
                    op.set_status(SyncOperationStatus.SUCCESS if result.status == SyncOperationStatus.SUCCESS else SyncOperationStatus.FAILED)
                    op.set_records_processed(result.records_processed)
                    
            except Exception as e:
                logger.error(f"Full sync failed for {entity_type.value}: {e}")
                sync_results.append(IncrementalSyncResult(
                    entity_type=entity_type,
                    records_found=0,
                    records_processed=0,
                    records_updated=0,
                    records_inserted=0,
                    sync_duration_ms=0.0,
                    status=SyncOperationStatus.FAILED,
                    error_message=str(e)
                ))
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Determine overall status
        overall_status = SyncOperationStatus.SUCCESS
        error_messages = []
        
        for result in sync_results:
            if result.status == SyncOperationStatus.FAILED:
                overall_status = SyncOperationStatus.FAILED
                if result.error_message:
                    error_messages.append(f"{result.entity_type.value}: {result.error_message}")
        
        return SyncJobResult(
            job_id=self.config.job_id,
            job_type=self.config.job_type,
            trigger=trigger,
            status=overall_status,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            records_processed=total_records_processed,
            records_updated=total_records_updated,
            records_inserted=total_records_inserted,
            error_message="; ".join(error_messages) if error_messages else None,
            details={"sync_results": [self._sync_result_to_dict(r) for r in sync_results]}
        )
    
    def _sync_result_to_dict(self, result: IncrementalSyncResult) -> Dict[str, Any]:
        """Convert IncrementalSyncResult to dictionary for serialization.
        
        Args:
            result: Sync result to convert
            
        Returns:
            Dictionary representation of the result
        """
        return {
            "entity_type": result.entity_type.value,
            "records_found": result.records_found,
            "records_processed": result.records_processed,
            "records_updated": result.records_updated,
            "records_inserted": result.records_inserted,
            "sync_duration_ms": result.sync_duration_ms,
            "status": result.status.value,
            "error_message": result.error_message
        }
    
    def should_run(self, current_time: float) -> bool:
        """Check if the job should run based on its configuration.
        
        Args:
            current_time: Current timestamp
            
        Returns:
            True if the job should run
        """
        if not self.config.enabled or self.is_running:
            return False
        
        if self.last_run is None:
            return True
        
        time_since_last_run = current_time - self.last_run.timestamp()
        return time_since_last_run >= self.config.interval_seconds
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the job.
        
        Returns:
            Dictionary containing job status information
        """
        with self._lock:
            return {
                "job_id": self.config.job_id,
                "job_type": self.config.job_type.value,
                "enabled": self.config.enabled,
                "interval_seconds": self.config.interval_seconds,
                "trigger_types": [t.value for t in self.config.trigger_types],
                "entity_types": [e.value for e in self.config.entity_types],
                "priority": self.config.priority,
                "last_run": self.last_run.isoformat() if self.last_run else None,
                "run_count": self.run_count,
                "error_count": self.error_count,
                "retry_count": self.retry_count,
                "is_running": self.is_running,
                "last_result": {
                    "status": self.last_result.status.value if self.last_result else None,
                    "duration_seconds": self.last_result.duration_seconds if self.last_result else None,
                    "records_processed": self.last_result.records_processed if self.last_result else None,
                    "error_message": self.last_result.error_message if self.last_result else None
                } if self.last_result else None
            }


class SyncScheduler:
    """Comprehensive scheduler for synchronization operations."""
    
    def __init__(
        self,
        metadata_cache: Optional[MetadataCache] = None,
        incremental_sync_manager: Optional[IncrementalSyncManager] = None,
        consistency_scheduler: Optional[ConsistencyScheduler] = None
    ):
        """Initialize the synchronization scheduler.
        
        Args:
            metadata_cache: MetadataCache instance
            incremental_sync_manager: IncrementalSyncManager instance
            consistency_scheduler: ConsistencyScheduler instance
        """
        self.metadata_cache = metadata_cache or MetadataCache()
        self.incremental_sync_manager = incremental_sync_manager or IncrementalSyncManager(self.metadata_cache)
        self.consistency_scheduler = consistency_scheduler or ConsistencyScheduler(self.metadata_cache)
        
        # Job management
        self.jobs: Dict[str, SyncJob] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False
        self.stop_event = threading.Event()
        self.callbacks: List[Callable[[SyncJobResult], None]] = []
        
        # Lock for thread safety
        self._lock = threading.Lock()
    
    def add_job(self, config: SyncJobConfig) -> SyncJob:
        """Add a new synchronization job.
        
        Args:
            config: Job configuration
            
        Returns:
            Created SyncJob instance
        """
        # Create consistency job if needed
        consistency_job = None
        if config.job_type == SyncJobType.CONSISTENCY_VALIDATION:
            consistency_job = self.consistency_scheduler.add_job(
                job_id=f"{config.job_id}_consistency",
                interval_seconds=config.interval_seconds,
                enabled=config.enabled
            )
        
        # Create sync job
        job = SyncJob(
            config=config,
            metadata_cache=self.metadata_cache,
            incremental_sync_manager=self.incremental_sync_manager,
            consistency_job=consistency_job
        )
        
        with self._lock:
            self.jobs[config.job_id] = job
        
        logger.info(f"Added sync job {config.job_id} (type: {config.job_type.value}, interval: {config.interval_seconds}s)")
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a synchronization job.
        
        Args:
            job_id: ID of the job to remove
            
        Returns:
            True if job was removed, False if not found
        """
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                logger.info(f"Removed sync job {job_id}")
                return True
        return False
    
    def start_scheduler(self, check_interval: int = 30) -> None:
        """Start the synchronization scheduler.
        
        Args:
            check_interval: How often to check for jobs to run (seconds)
        """
        if self.running:
            logger.warning("Sync scheduler is already running")
            return
        
        self.running = True
        self.stop_event.clear()
        
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            args=(check_interval,),
            daemon=True,
            name="SyncScheduler"
        )
        self.scheduler_thread.start()
        
        logger.info(f"Started sync scheduler with {check_interval}s check interval")
    
    def stop_scheduler(self) -> None:
        """Stop the synchronization scheduler."""
        if not self.running:
            logger.warning("Sync scheduler is not running")
            return
        
        self.running = False
        self.stop_event.set()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10)
        
        logger.info("Stopped sync scheduler")
    
    def run_job_now(self, job_id: str, trigger: SyncTrigger = SyncTrigger.MANUAL) -> Optional[SyncJobResult]:
        """Run a specific job immediately.
        
        Args:
            job_id: ID of the job to run
            trigger: What triggered this execution
            
        Returns:
            Job execution result or None if job not found
        """
        with self._lock:
            if job_id not in self.jobs:
                logger.warning(f"Sync job {job_id} not found")
                return None
        
        job = self.jobs[job_id]
        logger.info(f"Running sync job {job_id} immediately (trigger: {trigger.value})")
        
        result = job.execute(trigger)
        self._notify_callbacks(result)
        
        return result
    
    def run_all_jobs_now(self, trigger: SyncTrigger = SyncTrigger.MANUAL) -> Dict[str, SyncJobResult]:
        """Run all enabled jobs immediately.
        
        Args:
            trigger: What triggered this execution
            
        Returns:
            Dictionary mapping job IDs to their execution results
        """
        results = {}
        
        with self._lock:
            jobs_to_run = [(job_id, job) for job_id, job in self.jobs.items() if job.config.enabled]
        
        # Sort by priority (lower number = higher priority)
        jobs_to_run.sort(key=lambda x: x[1].config.priority)
        
        for job_id, job in jobs_to_run:
            logger.info(f"Running sync job {job_id} immediately (trigger: {trigger.value})")
            result = job.execute(trigger)
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
        with self._lock:
            if job_id not in self.jobs:
                return None
            return self.jobs[job_id].get_status()
    
    def get_all_job_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status information for all jobs.
        
        Returns:
            Dictionary mapping job IDs to their status information
        """
        with self._lock:
            return {job_id: job.get_status() for job_id, job in self.jobs.items()}
    
    def add_callback(self, callback: Callable[[SyncJobResult], None]) -> None:
        """Add a callback function to be called after each job execution.
        
        Args:
            callback: Function to call with job results
        """
        self.callbacks.append(callback)
        logger.debug("Added sync job execution callback")
    
    def remove_callback(self, callback: Callable[[SyncJobResult], None]) -> bool:
        """Remove a callback function.
        
        Args:
            callback: Callback function to remove
            
        Returns:
            True if callback was removed, False if not found
        """
        try:
            self.callbacks.remove(callback)
            logger.debug("Removed sync job execution callback")
            return True
        except ValueError:
            return False
    
    def _scheduler_loop(self, check_interval: int) -> None:
        """Main scheduler loop that runs in a separate thread.
        
        Args:
            check_interval: How often to check for jobs to run (seconds)
        """
        logger.info("Sync scheduler loop started")
        
        while self.running and not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                # Get jobs that should run
                jobs_to_run = []
                with self._lock:
                    for job_id, job in self.jobs.items():
                        if job.should_run(current_time):
                            jobs_to_run.append((job_id, job))
                
                # Sort by priority (lower number = higher priority)
                jobs_to_run.sort(key=lambda x: x[1].config.priority)
                
                # Execute jobs
                for job_id, job in jobs_to_run:
                    logger.debug(f"Scheduler: Running sync job {job_id}")
                    result = job.execute(SyncTrigger.SCHEDULED)
                    self._notify_callbacks(result)
                
                # Sleep for a short time before next check
                self.stop_event.wait(timeout=min(check_interval, 60))
                
            except Exception as e:
                logger.error(f"Error in sync scheduler loop: {e}", exc_info=True)
                # Sleep for a bit before retrying
                self.stop_event.wait(timeout=30)
        
        logger.info("Sync scheduler loop stopped")
    
    def _notify_callbacks(self, result: SyncJobResult) -> None:
        """Notify all registered callbacks with job results.
        
        Args:
            result: Job execution result
        """
        for callback in self.callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in sync job callback: {e}", exc_info=True)


# Global scheduler instance
_global_sync_scheduler: Optional[SyncScheduler] = None


def get_global_sync_scheduler() -> SyncScheduler:
    """Get the global sync scheduler instance.
    
    Returns:
        Global SyncScheduler instance
    """
    global _global_sync_scheduler
    if _global_sync_scheduler is None:
        _global_sync_scheduler = SyncScheduler()
    return _global_sync_scheduler


def start_global_sync_scheduler(check_interval: int = 30) -> None:
    """Start the global sync scheduler.
    
    Args:
        check_interval: How often to check for jobs to run (seconds)
    """
    scheduler = get_global_sync_scheduler()
    scheduler.start_scheduler(check_interval)


def stop_global_sync_scheduler() -> None:
    """Stop the global sync scheduler."""
    global _global_sync_scheduler
    if _global_sync_scheduler:
        _global_sync_scheduler.stop_scheduler()


def add_global_sync_job(config: SyncJobConfig) -> SyncJob:
    """Add a job to the global sync scheduler.
    
    Args:
        config: Job configuration
        
    Returns:
        Created SyncJob instance
    """
    scheduler = get_global_sync_scheduler()
    return scheduler.add_job(config)
