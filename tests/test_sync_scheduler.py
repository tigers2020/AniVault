"""Tests for the synchronization scheduler.

This module contains comprehensive tests for the sync scheduler functionality,
including job execution, scheduling, and integration features.
"""

import time
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.core.incremental_sync import IncrementalSyncManager, IncrementalSyncResult
from src.core.metadata_cache import MetadataCache
from src.core.sync_config import SyncConfigManager, SyncSchedulerConfig, create_quick_sync_setup
from src.core.sync_integration import SyncIntegrationManager, initialize_sync_system
from src.core.sync_monitoring import SyncOperationStatus
from src.core.sync_scheduler import (
    SyncEntityType,
    SyncJob,
    SyncJobConfig,
    SyncJobResult,
    SyncJobType,
    SyncScheduler,
    SyncTrigger,
    get_global_sync_scheduler,
)


class TestSyncJobConfig:
    """Test SyncJobConfig functionality."""

    def test_config_creation(self) -> None:
        """Test creating a sync job configuration."""
        config = SyncJobConfig(
            job_id="test_job",
            job_type=SyncJobType.INCREMENTAL_SYNC,
            interval_seconds=60,
            enabled=True,
            trigger_types=[SyncTrigger.SCHEDULED],
            entity_types=[SyncEntityType.TMDB_METADATA],
            priority=1,
        )

        assert config.job_id == "test_job"
        assert config.job_type == SyncJobType.INCREMENTAL_SYNC
        assert config.interval_seconds == 60
        assert config.enabled is True
        assert SyncTrigger.SCHEDULED in config.trigger_types
        assert SyncEntityType.TMDB_METADATA in config.entity_types
        assert config.priority == 1

    def test_config_defaults(self) -> None:
        """Test configuration defaults."""
        config = SyncJobConfig(
            job_id="test_job", job_type=SyncJobType.CONSISTENCY_VALIDATION, interval_seconds=300
        )

        assert config.enabled is True
        assert SyncTrigger.SCHEDULED in config.trigger_types
        assert SyncEntityType.TMDB_METADATA in config.entity_types
        assert SyncEntityType.PARSED_FILES in config.entity_types
        assert config.priority == 1


class TestSyncJob:
    """Test SyncJob functionality."""

    @pytest.fixture
    def mock_metadata_cache(self):
        """Create a mock metadata cache."""
        return Mock(spec=MetadataCache)

    @pytest.fixture
    def mock_incremental_sync_manager(self):
        """Create a mock incremental sync manager."""
        manager = Mock(spec=IncrementalSyncManager)
        manager.sync_entity_type.return_value = IncrementalSyncResult(
            entity_type=SyncEntityType.TMDB_METADATA,
            records_found=10,
            records_processed=10,
            records_updated=5,
            records_inserted=2,
            sync_duration_ms=100.0,
            status=SyncOperationStatus.SUCCESS,
        )
        return manager

    @pytest.fixture
    def mock_consistency_job(self):
        """Create a mock consistency job."""
        job = Mock()
        job.execute.return_value = {
            "status": "success",
            "conflicts_found": 0,
            "conflicts_resolved": 0,
            "duration_seconds": 1.0,
        }
        return job

    @pytest.fixture
    def sync_job_config(self):
        """Create a sync job configuration."""
        return SyncJobConfig(
            job_id="test_job",
            job_type=SyncJobType.INCREMENTAL_SYNC,
            interval_seconds=60,
            entity_types=[SyncEntityType.TMDB_METADATA],
        )

    def test_job_creation(
        self, sync_job_config, mock_metadata_cache, mock_incremental_sync_manager
    ) -> None:
        """Test creating a sync job."""
        job = SyncJob(
            config=sync_job_config,
            metadata_cache=mock_metadata_cache,
            incremental_sync_manager=mock_incremental_sync_manager,
        )

        assert job.config == sync_job_config
        assert job.metadata_cache == mock_metadata_cache
        assert job.incremental_sync_manager == mock_incremental_sync_manager
        assert job.run_count == 0
        assert job.error_count == 0
        assert job.is_running is False

    def test_job_execution_incremental_sync(
        self, sync_job_config, mock_metadata_cache, mock_incremental_sync_manager
    ) -> None:
        """Test executing an incremental sync job."""
        job = SyncJob(
            config=sync_job_config,
            metadata_cache=mock_metadata_cache,
            incremental_sync_manager=mock_incremental_sync_manager,
        )

        result = job.execute(SyncTrigger.MANUAL)

        assert isinstance(result, SyncJobResult)
        assert result.job_id == "test_job"
        assert result.job_type == SyncJobType.INCREMENTAL_SYNC
        assert result.trigger == SyncTrigger.MANUAL
        assert result.status == SyncOperationStatus.SUCCESS
        assert result.records_processed == 10
        assert result.records_updated == 5
        assert result.records_inserted == 2
        assert job.run_count == 1
        assert job.error_count == 0

    def test_job_execution_consistency_validation(
        self, mock_metadata_cache, mock_consistency_job
    ) -> None:
        """Test executing a consistency validation job."""
        config = SyncJobConfig(
            job_id="consistency_job",
            job_type=SyncJobType.CONSISTENCY_VALIDATION,
            interval_seconds=300,
        )

        job = SyncJob(
            config=config, metadata_cache=mock_metadata_cache, consistency_job=mock_consistency_job
        )

        result = job.execute(SyncTrigger.MANUAL)

        assert isinstance(result, SyncJobResult)
        assert result.job_id == "consistency_job"
        assert result.job_type == SyncJobType.CONSISTENCY_VALIDATION
        assert result.status == SyncOperationStatus.SUCCESS
        assert result.conflicts_found == 0
        assert result.conflicts_resolved == 0
        assert job.run_count == 1

    def test_job_execution_disabled(self, sync_job_config, mock_metadata_cache) -> None:
        """Test executing a disabled job."""
        sync_job_config.enabled = False

        job = SyncJob(config=sync_job_config, metadata_cache=mock_metadata_cache)

        result = job.execute(SyncTrigger.MANUAL)

        assert result.status == SyncOperationStatus.SKIPPED
        assert "disabled" in result.error_message
        assert job.run_count == 1

    def test_job_execution_already_running(
        self, sync_job_config, mock_metadata_cache, mock_incremental_sync_manager
    ) -> None:
        """Test executing a job that's already running."""
        job = SyncJob(
            config=sync_job_config,
            metadata_cache=mock_metadata_cache,
            incremental_sync_manager=mock_incremental_sync_manager,
        )

        # Simulate job already running
        job.is_running = True

        result = job.execute(SyncTrigger.MANUAL)

        assert result.status == SyncOperationStatus.FAILED
        assert "already running" in result.error_message

    def test_job_should_run(self, sync_job_config, mock_metadata_cache) -> None:
        """Test job should_run logic."""
        job = SyncJob(config=sync_job_config, metadata_cache=mock_metadata_cache)

        current_time = time.time()

        # First run should execute
        assert job.should_run(current_time) is True

        # After first run, should not run immediately
        job.last_run = datetime.fromtimestamp(current_time - 30, tz=timezone.utc)
        assert job.should_run(current_time) is False

        # After interval, should run again
        job.last_run = datetime.fromtimestamp(current_time - 70, tz=timezone.utc)
        assert job.should_run(current_time) is True

    def test_job_status(self, sync_job_config, mock_metadata_cache) -> None:
        """Test getting job status."""
        job = SyncJob(config=sync_job_config, metadata_cache=mock_metadata_cache)

        status = job.get_status()

        assert status["job_id"] == "test_job"
        assert status["job_type"] == SyncJobType.INCREMENTAL_SYNC.value
        assert status["enabled"] is True
        assert status["interval_seconds"] == 60
        assert status["run_count"] == 0
        assert status["error_count"] == 0
        assert status["is_running"] is False


class TestSyncScheduler:
    """Test SyncScheduler functionality."""

    @pytest.fixture
    def mock_metadata_cache(self):
        """Create a mock metadata cache."""
        return Mock(spec=MetadataCache)

    @pytest.fixture
    def mock_incremental_sync_manager(self):
        """Create a mock incremental sync manager."""
        manager = Mock(spec=IncrementalSyncManager)
        manager.sync_entity_type.return_value = IncrementalSyncResult(
            entity_type=SyncEntityType.TMDB_METADATA,
            records_found=5,
            records_processed=5,
            records_updated=2,
            records_inserted=1,
            sync_duration_ms=50.0,
            status=SyncOperationStatus.SUCCESS,
        )
        return manager

    @pytest.fixture
    def sync_scheduler(self, mock_metadata_cache, mock_incremental_sync_manager):
        """Create a sync scheduler for testing."""
        scheduler = SyncScheduler(
            metadata_cache=mock_metadata_cache,
            incremental_sync_manager=mock_incremental_sync_manager,
        )
        return scheduler

    def test_scheduler_creation(self, mock_metadata_cache) -> None:
        """Test creating a sync scheduler."""
        scheduler = SyncScheduler(metadata_cache=mock_metadata_cache)

        assert scheduler.metadata_cache == mock_metadata_cache
        assert len(scheduler.jobs) == 0
        assert scheduler.running is False
        assert len(scheduler.callbacks) == 0

    def test_add_job(self, sync_scheduler) -> None:
        """Test adding a job to the scheduler."""
        config = SyncJobConfig(
            job_id="test_job", job_type=SyncJobType.INCREMENTAL_SYNC, interval_seconds=60
        )

        job = sync_scheduler.add_job(config)

        assert isinstance(job, SyncJob)
        assert "test_job" in sync_scheduler.jobs
        assert sync_scheduler.jobs["test_job"] == job

    def test_remove_job(self, sync_scheduler) -> None:
        """Test removing a job from the scheduler."""
        config = SyncJobConfig(
            job_id="test_job", job_type=SyncJobType.INCREMENTAL_SYNC, interval_seconds=60
        )

        sync_scheduler.add_job(config)
        assert "test_job" in sync_scheduler.jobs

        result = sync_scheduler.remove_job("test_job")
        assert result is True
        assert "test_job" not in sync_scheduler.jobs

        # Try to remove non-existent job
        result = sync_scheduler.remove_job("nonexistent")
        assert result is False

    def test_run_job_now(self, sync_scheduler, mock_incremental_sync_manager) -> None:
        """Test running a job immediately."""
        config = SyncJobConfig(
            job_id="test_job",
            job_type=SyncJobType.INCREMENTAL_SYNC,
            interval_seconds=60,
            entity_types=[SyncEntityType.TMDB_METADATA],
        )

        sync_scheduler.add_job(config)

        result = sync_scheduler.run_job_now("test_job", SyncTrigger.MANUAL)

        assert isinstance(result, SyncJobResult)
        assert result.job_id == "test_job"
        assert result.status == SyncOperationStatus.SUCCESS
        assert result.records_processed == 5

        # Verify the incremental sync manager was called
        mock_incremental_sync_manager.sync_entity_type.assert_called_once_with(
            SyncEntityType.TMDB_METADATA
        )

    def test_run_job_now_not_found(self, sync_scheduler) -> None:
        """Test running a non-existent job."""
        result = sync_scheduler.run_job_now("nonexistent", SyncTrigger.MANUAL)
        assert result is None

    def test_run_all_jobs_now(self, sync_scheduler, mock_incremental_sync_manager) -> None:
        """Test running all enabled jobs immediately."""
        # Add multiple jobs
        config1 = SyncJobConfig(
            job_id="job1",
            job_type=SyncJobType.INCREMENTAL_SYNC,
            interval_seconds=60,
            entity_types=[SyncEntityType.TMDB_METADATA],
        )
        config2 = SyncJobConfig(
            job_id="job2",
            job_type=SyncJobType.INCREMENTAL_SYNC,
            interval_seconds=120,
            entity_types=[SyncEntityType.PARSED_FILES],
        )
        config3 = SyncJobConfig(
            job_id="job3",
            job_type=SyncJobType.INCREMENTAL_SYNC,
            interval_seconds=180,
            enabled=False,  # Disabled job
        )

        sync_scheduler.add_job(config1)
        sync_scheduler.add_job(config2)
        sync_scheduler.add_job(config3)

        results = sync_scheduler.run_all_jobs_now(SyncTrigger.MANUAL)

        # Should only run enabled jobs
        assert len(results) == 2
        assert "job1" in results
        assert "job2" in results
        assert "job3" not in results

        # Both jobs should have succeeded
        assert results["job1"].status == SyncOperationStatus.SUCCESS
        assert results["job2"].status == SyncOperationStatus.SUCCESS

    def test_get_job_status(self, sync_scheduler) -> None:
        """Test getting job status."""
        config = SyncJobConfig(
            job_id="test_job", job_type=SyncJobType.INCREMENTAL_SYNC, interval_seconds=60
        )

        sync_scheduler.add_job(config)

        status = sync_scheduler.get_job_status("test_job")
        assert status is not None
        assert status["job_id"] == "test_job"
        assert status["enabled"] is True

        # Non-existent job
        status = sync_scheduler.get_job_status("nonexistent")
        assert status is None

    def test_get_all_job_status(self, sync_scheduler) -> None:
        """Test getting all job statuses."""
        config1 = SyncJobConfig(
            job_id="job1", job_type=SyncJobType.INCREMENTAL_SYNC, interval_seconds=60
        )
        config2 = SyncJobConfig(
            job_id="job2", job_type=SyncJobType.CONSISTENCY_VALIDATION, interval_seconds=300
        )

        sync_scheduler.add_job(config1)
        sync_scheduler.add_job(config2)

        all_status = sync_scheduler.get_all_job_status()

        assert len(all_status) == 2
        assert "job1" in all_status
        assert "job2" in all_status

    def test_callback_management(self, sync_scheduler) -> None:
        """Test adding and removing callbacks."""

        def test_callback(result) -> None:
            pass

        # Add callback
        sync_scheduler.add_callback(test_callback)
        assert len(sync_scheduler.callbacks) == 1
        assert test_callback in sync_scheduler.callbacks

        # Remove callback
        result = sync_scheduler.remove_callback(test_callback)
        assert result is True
        assert len(sync_scheduler.callbacks) == 0
        assert test_callback not in sync_scheduler.callbacks

        # Try to remove non-existent callback
        result = sync_scheduler.remove_callback(test_callback)
        assert result is False


class TestSyncConfigManager:
    """Test SyncConfigManager functionality."""

    def test_config_manager_creation(self) -> None:
        """Test creating a config manager."""
        manager = SyncConfigManager()

        assert len(manager.configs) == 0
        assert isinstance(manager.scheduler_config, SyncSchedulerConfig)

    def test_add_predefined_configs(self) -> None:
        """Test adding predefined configurations."""
        manager = SyncConfigManager()
        manager.add_predefined_configs()

        assert len(manager.configs) > 0
        assert "consistency_validation" in manager.configs
        assert "incremental_sync" in manager.configs
        assert "full_sync" in manager.configs

    def test_get_config(self) -> None:
        """Test getting a configuration."""
        manager = SyncConfigManager()
        manager.add_predefined_configs()

        config = manager.get_config("consistency_validation")
        assert config is not None
        assert config.job_id == "consistency_validation"

        # Non-existent config
        config = manager.get_config("nonexistent")
        assert config is None

    def test_create_custom_config(self) -> None:
        """Test creating a custom configuration."""
        manager = SyncConfigManager()

        config = manager.create_custom_config(
            job_id="custom_job",
            job_type=SyncJobType.INCREMENTAL_SYNC,
            interval_seconds=45,
            enabled=False,
            priority=2,
        )

        assert config.job_id == "custom_job"
        assert config.job_type == SyncJobType.INCREMENTAL_SYNC
        assert config.interval_seconds == 45
        assert config.enabled is False
        assert config.priority == 2
        assert "custom_job" in manager.configs

    def test_update_config(self) -> None:
        """Test updating a configuration."""
        manager = SyncConfigManager()
        manager.add_predefined_configs()

        # Update existing config
        result = manager.update_config(
            "consistency_validation", enabled=False, interval_seconds=600
        )
        assert result is True

        config = manager.get_config("consistency_validation")
        assert config.enabled is False
        assert config.interval_seconds == 600

        # Try to update non-existent config
        result = manager.update_config("nonexistent", enabled=False)
        assert result is False

    def test_get_enabled_configs(self) -> None:
        """Test getting enabled configurations."""
        manager = SyncConfigManager()
        manager.add_predefined_configs()

        # Disable one config
        manager.update_config("consistency_validation", enabled=False)

        enabled_configs = manager.get_enabled_configs()

        # Should have all configs except the disabled one
        assert len(enabled_configs) == len(manager.configs) - 1
        assert "consistency_validation" not in enabled_configs
        assert "incremental_sync" in enabled_configs


class TestSyncIntegrationManager:
    """Test SyncIntegrationManager functionality."""

    @pytest.fixture
    def mock_metadata_cache(self):
        """Create a mock metadata cache."""
        return Mock(spec=MetadataCache)

    def test_integration_manager_creation(self, mock_metadata_cache) -> None:
        """Test creating an integration manager."""
        manager = SyncIntegrationManager(metadata_cache=mock_metadata_cache)

        assert manager.metadata_cache == mock_metadata_cache
        assert manager.sync_scheduler is None
        assert manager.is_initialized is False

    def test_initialize(self, mock_metadata_cache) -> None:
        """Test initializing the integration manager."""
        manager = SyncIntegrationManager(metadata_cache=mock_metadata_cache)

        manager.initialize(enable_consistency=True, enable_incremental=True, enable_full_sync=False)

        assert manager.is_initialized is True
        assert manager.sync_scheduler is not None
        assert len(manager.sync_scheduler.jobs) >= 2  # At least consistency and incremental

    def test_initialize_already_initialized(self, mock_metadata_cache) -> None:
        """Test initializing an already initialized manager."""
        manager = SyncIntegrationManager(metadata_cache=mock_metadata_cache)
        manager.initialize()

        # Should not raise an error, just log a warning
        manager.initialize()
        assert manager.is_initialized is True

    def test_add_custom_job(self, mock_metadata_cache) -> None:
        """Test adding a custom job."""
        manager = SyncIntegrationManager(metadata_cache=mock_metadata_cache)
        manager.initialize()

        result = manager.add_custom_job(
            job_id="custom_job",
            job_type="incremental_sync",
            interval_seconds=45,
            enabled=True,
            priority=2,
        )

        assert result is True
        assert "custom_job" in manager.sync_scheduler.jobs

    def test_job_management(self, mock_metadata_cache) -> None:
        """Test job management operations."""
        manager = SyncIntegrationManager(metadata_cache=mock_metadata_cache)
        manager.initialize()

        # Add a custom job
        manager.add_custom_job("test_job", "incremental_sync", 60)

        # Enable job
        result = manager.enable_job("test_job")
        assert result is True

        # Disable job
        result = manager.disable_job("test_job")
        assert result is True

        # Remove job
        result = manager.remove_job("test_job")
        assert result is True
        assert "test_job" not in manager.sync_scheduler.jobs

    def test_get_scheduler_info(self, mock_metadata_cache) -> None:
        """Test getting scheduler information."""
        manager = SyncIntegrationManager(metadata_cache=mock_metadata_cache)

        # Not initialized
        info = manager.get_scheduler_info()
        assert info["status"] == "not_initialized"

        # Initialize
        manager.initialize()
        info = manager.get_scheduler_info()
        assert info["status"] == "stopped"
        assert info["is_initialized"] is True
        assert info["job_count"] > 0


class TestQuickSyncSetup:
    """Test quick sync setup functionality."""

    def test_create_quick_sync_setup_default(self) -> None:
        """Test creating quick sync setup with defaults."""
        configs = create_quick_sync_setup()

        assert len(configs) == 2  # consistency and incremental by default
        assert any(c.job_type == SyncJobType.CONSISTENCY_VALIDATION for c in configs)
        assert any(c.job_type == SyncJobType.INCREMENTAL_SYNC for c in configs)

    def test_create_quick_sync_setup_custom(self) -> None:
        """Test creating quick sync setup with custom settings."""
        configs = create_quick_sync_setup(
            enable_consistency=True,
            enable_incremental=True,
            enable_full_sync=True,
            custom_intervals={"consistency": 600, "incremental": 30},
        )

        assert len(configs) == 3  # all three types

        # Check custom intervals
        consistency_config = next(
            c for c in configs if c.job_type == SyncJobType.CONSISTENCY_VALIDATION
        )
        incremental_config = next(c for c in configs if c.job_type == SyncJobType.INCREMENTAL_SYNC)

        assert consistency_config.interval_seconds == 600
        assert incremental_config.interval_seconds == 30


class TestGlobalFunctions:
    """Test global functions."""

    def test_get_global_sync_scheduler(self) -> None:
        """Test getting global sync scheduler."""
        scheduler1 = get_global_sync_scheduler()
        scheduler2 = get_global_sync_scheduler()

        # Should return the same instance
        assert scheduler1 is scheduler2

    def test_initialize_sync_system(self) -> None:
        """Test initializing sync system."""
        manager = initialize_sync_system(
            enable_consistency=True,
            enable_incremental=True,
            start_scheduler=False,  # Don't start for testing
        )

        assert isinstance(manager, SyncIntegrationManager)
        assert manager.is_initialized is True
        assert manager.sync_scheduler is not None


if __name__ == "__main__":
    pytest.main([__file__])
