"""Integration module for synchronization scheduler.

This module provides easy-to-use functions for integrating the synchronization
scheduler with the AniVault application.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from .metadata_cache import MetadataCache
from .sync_config import SyncSchedulerConfig, create_quick_sync_setup, get_global_config_manager
from .sync_scheduler import SyncJobResult, SyncScheduler, SyncTrigger

# Configure logging
logger = logging.getLogger(__name__)


class SyncIntegrationManager:
    """Manager for integrating synchronization with the application."""

    def __init__(self, metadata_cache: MetadataCache | None = None) -> None:
        """Initialize the sync integration manager.

        Args:
            metadata_cache: MetadataCache instance
        """
        self.metadata_cache = metadata_cache or MetadataCache()
        self.sync_scheduler: SyncScheduler | None = None
        self.config_manager = get_global_config_manager()
        self.is_initialized = False

    def initialize(
        self,
        enable_consistency: bool = True,
        enable_incremental: bool = True,
        enable_full_sync: bool = False,
        custom_intervals: dict[str, int] | None = None,
        scheduler_config: SyncSchedulerConfig | None = None,
    ) -> None:
        """Initialize the synchronization system.

        Args:
            enable_consistency: Enable consistency validation jobs
            enable_incremental: Enable incremental synchronization jobs
            enable_full_sync: Enable full synchronization jobs
            custom_intervals: Custom intervals for specific job types
            scheduler_config: Custom scheduler configuration
        """
        if self.is_initialized:
            logger.warning("Sync integration is already initialized")
            return

        # Create sync scheduler
        self.sync_scheduler = SyncScheduler(metadata_cache=self.metadata_cache)

        # Create job configurations
        job_configs = create_quick_sync_setup(
            enable_consistency=enable_consistency,
            enable_incremental=enable_incremental,
            enable_full_sync=enable_full_sync,
            custom_intervals=custom_intervals,
        )

        # Add jobs to scheduler
        for config in job_configs:
            self.sync_scheduler.add_job(config)
            logger.info(f"Added sync job: {config.job_id} (type: {config.job_type.value})")

        # Apply custom scheduler configuration
        if scheduler_config:
            self.config_manager.scheduler_config = scheduler_config

        self.is_initialized = True
        logger.info("Sync integration initialized successfully")

    def start_scheduler(self, check_interval: int | None = None) -> None:
        """Start the synchronization scheduler.

        Args:
            check_interval: How often to check for jobs to run (seconds)
        """
        if not self.is_initialized:
            raise RuntimeError("Sync integration not initialized. Call initialize() first.")

        if not self.sync_scheduler:
            raise RuntimeError("Sync scheduler not available")

        interval = check_interval or self.config_manager.scheduler_config.check_interval_seconds
        self.sync_scheduler.start_scheduler(interval)
        logger.info(f"Sync scheduler started with {interval}s check interval")

    def stop_scheduler(self) -> None:
        """Stop the synchronization scheduler."""
        if not self.sync_scheduler:
            logger.warning("Sync scheduler not available")
            return

        self.sync_scheduler.stop_scheduler()
        logger.info("Sync scheduler stopped")

    def add_callback(self, callback: Callable[[SyncJobResult], None]) -> None:
        """Add a callback for job execution results.

        Args:
            callback: Function to call with job results
        """
        if not self.sync_scheduler:
            raise RuntimeError("Sync scheduler not available")

        self.sync_scheduler.add_callback(callback)
        logger.debug("Added sync job callback")

    def run_job_now(
        self, job_id: str, trigger: SyncTrigger = SyncTrigger.MANUAL
    ) -> SyncJobResult | None:
        """Run a specific job immediately.

        Args:
            job_id: ID of the job to run
            trigger: What triggered this execution

        Returns:
            Job execution result or None if job not found
        """
        if not self.sync_scheduler:
            raise RuntimeError("Sync scheduler not available")

        return self.sync_scheduler.run_job_now(job_id, trigger)

    def run_all_jobs_now(
        self, trigger: SyncTrigger = SyncTrigger.MANUAL
    ) -> dict[str, SyncJobResult]:
        """Run all enabled jobs immediately.

        Args:
            trigger: What triggered this execution

        Returns:
            Dictionary mapping job IDs to their execution results
        """
        if not self.sync_scheduler:
            raise RuntimeError("Sync scheduler not available")

        return self.sync_scheduler.run_all_jobs_now(trigger)

    def get_job_status(self, job_id: str) -> dict[str, Any] | None:
        """Get status of a specific job.

        Args:
            job_id: ID of the job

        Returns:
            Job status information or None if job not found
        """
        if not self.sync_scheduler:
            return None

        return self.sync_scheduler.get_job_status(job_id)

    def get_all_job_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all jobs.

        Returns:
            Dictionary mapping job IDs to their status information
        """
        if not self.sync_scheduler:
            return {}

        return self.sync_scheduler.get_all_job_status()

    def add_custom_job(
        self,
        job_id: str,
        job_type: str,
        interval_seconds: int,
        enabled: bool = True,
        trigger_types: list[str] | None = None,
        entity_types: list[str] | None = None,
        priority: int = 3,
    ) -> bool:
        """Add a custom synchronization job.

        Args:
            job_id: Unique identifier for the job
            job_type: Type of job ('consistency_validation', 'incremental_sync', 'full_sync')
            interval_seconds: Interval between executions
            enabled: Whether the job is enabled
            trigger_types: Types of triggers that can start the job
            entity_types: Types of entities to synchronize
            priority: Job priority (lower = higher priority)

        Returns:
            True if job was added successfully
        """
        if not self.sync_scheduler:
            raise RuntimeError("Sync scheduler not available")

        # Convert string types to enums
        from .sync_enums import SyncEntityType
        from .sync_scheduler import SyncJobType, SyncTrigger

        job_type_enum = SyncJobType(job_type)

        trigger_enums = []
        if trigger_types:
            for trigger in trigger_types:
                trigger_enums.append(SyncTrigger(trigger))
        else:
            trigger_enums = [SyncTrigger.SCHEDULED]

        entity_enums = []
        if entity_types:
            for entity in entity_types:
                entity_enums.append(SyncEntityType(entity))
        else:
            entity_enums = [SyncEntityType.TMDB_METADATA, SyncEntityType.PARSED_FILES]

        # Create job configuration
        from .sync_scheduler import SyncJobConfig

        config = SyncJobConfig(
            job_id=job_id,
            job_type=job_type_enum,
            interval_seconds=interval_seconds,
            enabled=enabled,
            trigger_types=trigger_enums,
            entity_types=entity_enums,
            priority=priority,
        )

        # Add job to scheduler
        self.sync_scheduler.add_job(config)
        logger.info(f"Added custom sync job: {job_id}")
        return True

    def remove_job(self, job_id: str) -> bool:
        """Remove a synchronization job.

        Args:
            job_id: ID of the job to remove

        Returns:
            True if job was removed, False if not found
        """
        if not self.sync_scheduler:
            return False

        return self.sync_scheduler.remove_job(job_id)

    def enable_job(self, job_id: str) -> bool:
        """Enable a synchronization job.

        Args:
            job_id: ID of the job to enable

        Returns:
            True if job was enabled, False if not found
        """
        if not self.sync_scheduler or job_id not in self.sync_scheduler.jobs:
            return False

        job = self.sync_scheduler.jobs[job_id]
        job.config.enabled = True
        logger.info(f"Enabled sync job: {job_id}")
        return True

    def disable_job(self, job_id: str) -> bool:
        """Disable a synchronization job.

        Args:
            job_id: ID of the job to disable

        Returns:
            True if job was disabled, False if not found
        """
        if not self.sync_scheduler or job_id not in self.sync_scheduler.jobs:
            return False

        job = self.sync_scheduler.jobs[job_id]
        job.config.enabled = False
        logger.info(f"Disabled sync job: {job_id}")
        return True

    def get_scheduler_info(self) -> dict[str, Any]:
        """Get information about the scheduler.

        Returns:
            Dictionary containing scheduler information
        """
        if not self.sync_scheduler:
            return {"status": "not_initialized"}

        return {
            "status": "running" if self.sync_scheduler.running else "stopped",
            "is_initialized": self.is_initialized,
            "job_count": len(self.sync_scheduler.jobs),
            "enabled_jobs": len([j for j in self.sync_scheduler.jobs.values() if j.config.enabled]),
            "scheduler_config": {
                "check_interval_seconds": self.config_manager.scheduler_config.check_interval_seconds,
                "max_concurrent_jobs": self.config_manager.scheduler_config.max_concurrent_jobs,
                "job_timeout_seconds": self.config_manager.scheduler_config.job_timeout_seconds,
            },
        }


# Global sync integration manager
_global_sync_integration: SyncIntegrationManager | None = None


def get_global_sync_integration() -> SyncIntegrationManager:
    """Get the global sync integration manager instance.

    Returns:
        Global SyncIntegrationManager instance
    """
    global _global_sync_integration
    if _global_sync_integration is None:
        _global_sync_integration = SyncIntegrationManager()
    return _global_sync_integration


def initialize_sync_system(
    metadata_cache: MetadataCache | None = None,
    enable_consistency: bool = True,
    enable_incremental: bool = True,
    enable_full_sync: bool = False,
    custom_intervals: dict[str, int] | None = None,
    start_scheduler: bool = True,
) -> SyncIntegrationManager:
    """Initialize the synchronization system with default settings.

    Args:
        metadata_cache: MetadataCache instance
        enable_consistency: Enable consistency validation jobs
        enable_incremental: Enable incremental synchronization jobs
        enable_full_sync: Enable full synchronization jobs
        custom_intervals: Custom intervals for specific job types
        start_scheduler: Whether to start the scheduler immediately

    Returns:
        Initialized SyncIntegrationManager instance
    """
    manager = get_global_sync_integration()

    if metadata_cache:
        manager.metadata_cache = metadata_cache

    manager.initialize(
        enable_consistency=enable_consistency,
        enable_incremental=enable_incremental,
        enable_full_sync=enable_full_sync,
        custom_intervals=custom_intervals,
    )

    if start_scheduler:
        manager.start_scheduler()

    return manager


def create_sync_callback(
    log_results: bool = True,
    alert_on_failure: bool = True,
    custom_handler: Callable[[SyncJobResult], None] | None = None,
) -> Callable[[SyncJobResult], None]:
    """Create a callback function for sync job results.

    Args:
        log_results: Whether to log job results
        alert_on_failure: Whether to log alerts on failures
        custom_handler: Custom handler function

    Returns:
        Callback function
    """

    def callback(result: SyncJobResult) -> None:
        if log_results:
            if result.status.value == "success":
                logger.info(
                    f"Sync job {result.job_id} completed successfully: "
                    f"{result.records_processed} records processed in {result.duration_seconds:.2f}s"
                )
            else:
                log_level = logging.ERROR if alert_on_failure else logging.WARNING
                logger.log(
                    log_level,
                    f"Sync job {result.job_id} failed: {result.error_message or 'Unknown error'}",
                )

        if custom_handler:
            try:
                custom_handler(result)
            except Exception as e:
                logger.error(f"Error in custom sync callback: {e}", exc_info=True)

    return callback
