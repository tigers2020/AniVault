"""Unit tests for consistency scheduler and background jobs."""

from datetime import datetime, timezone
from typing import NoReturn
from unittest.mock import Mock, patch

import pytest

from src.core.consistency_reporter import ConsistencyReporter
from src.core.consistency_scheduler import (
    ConsistencyJob,
    ConsistencyScheduler,
    add_global_job,
    get_global_scheduler,
    start_global_scheduler,
    stop_global_scheduler,
)
from src.core.consistency_validator import (
    ConflictSeverity,
    ConflictType,
    ConsistencyValidator,
    DataConflict,
)
from src.core.metadata_cache import MetadataCache
from src.core.reconciliation_strategies import (
    ReconciliationEngine,
    ReconciliationResult,
    ReconciliationStrategy,
)


class TestConsistencyJob:
    """Test ConsistencyJob functionality."""

    @pytest.fixture
    def mock_validator(self):
        """Create a mock consistency validator."""
        validator = Mock(spec=ConsistencyValidator)
        validator.validate_all_consistency.return_value = []
        return validator

    @pytest.fixture
    def mock_reconciliation_engine(self):
        """Create a mock reconciliation engine."""
        engine = Mock(spec=ReconciliationEngine)
        engine.reconcile_conflicts.return_value = ReconciliationResult(
            success=True,
            strategy_used=ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH,
            conflicts_resolved=0,
            conflicts_failed=0,
            details=[],
            errors=[],
        )
        return engine

    @pytest.fixture
    def mock_reporter(self):
        """Create a mock consistency reporter."""
        reporter = Mock(spec=ConsistencyReporter)
        mock_report = Mock()
        mock_report.id = 1
        reporter.create_report.return_value = mock_report
        return reporter

    @pytest.fixture
    def job(self, mock_validator, mock_reconciliation_engine, mock_reporter):
        """Create a consistency job."""
        return ConsistencyJob(
            job_id="test_job",
            validator=mock_validator,
            reconciliation_engine=mock_reconciliation_engine,
            reporter=mock_reporter,
            strategy=ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH,
            enabled=True,
        )

    def test_job_creation(self, job) -> None:
        """Test job object creation."""
        assert job.job_id == "test_job"
        assert job.enabled is True
        assert job.strategy == ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH
        assert job.last_run is None
        assert job.last_result is None
        assert job.run_count == 0
        assert job.error_count == 0

    def test_job_execution_success_no_conflicts(
        self, job, mock_validator, mock_reconciliation_engine, mock_reporter
    ) -> None:
        """Test successful job execution with no conflicts."""
        mock_validator.validate_all_consistency.return_value = []

        result = job.execute()

        assert result["job_id"] == "test_job"
        assert result["report_id"] == 1
        assert result["status"] == "success"
        assert result["conflicts_found"] == 0
        assert result["conflicts_resolved"] == 0
        assert result["conflicts_failed"] == 0
        assert result["strategy_used"] == "database_is_source_of_truth"
        assert result["reconciliation_success"] is True

        # Check reporter calls
        mock_reporter.create_report.assert_called_once()
        mock_reporter.update_report_with_conflicts.assert_called_once()
        mock_reporter.update_report_with_resolution.assert_called_once()

        # Check job state
        assert job.last_run is not None
        assert job.run_count == 1
        assert job.error_count == 0

    def test_job_execution_success_with_conflicts(
        self, job, mock_validator, mock_reconciliation_engine, mock_reporter
    ) -> None:
        """Test successful job execution with conflicts."""
        # Create mock conflicts
        conflicts = [
            DataConflict(
                conflict_type=ConflictType.MISSING_IN_CACHE,
                entity_type="anime_metadata",
                entity_id=12345,
                db_data={"tmdb_id": 12345, "title": "Test Anime"},
                severity=ConflictSeverity.MEDIUM,
            )
        ]
        mock_validator.validate_all_consistency.return_value = conflicts

        # Mock reconciliation result
        reconciliation_result = ReconciliationResult(
            success=True,
            strategy_used=ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH,
            conflicts_resolved=1,
            conflicts_failed=0,
            details=["Resolved conflict 1"],
            errors=[],
        )
        mock_reconciliation_engine.reconcile_conflicts.return_value = reconciliation_result

        result = job.execute()

        assert result["job_id"] == "test_job"
        assert result["report_id"] == 1
        assert result["status"] == "success"
        assert result["conflicts_found"] == 1
        assert result["conflicts_resolved"] == 1
        assert result["conflicts_failed"] == 0
        assert len(result["conflicts"]) == 1
        assert len(result["reconciliation_details"]) == 1

        # Check reporter calls
        mock_reporter.create_report.assert_called_once()
        mock_reporter.update_report_with_conflicts.assert_called_once()
        mock_reporter.update_report_with_resolution.assert_called_once()

    def test_job_execution_error(self, job, mock_validator, mock_reporter) -> None:
        """Test job execution with error."""
        mock_validator.validate_all_consistency.side_effect = Exception("Validation failed")

        result = job.execute()

        assert result["job_id"] == "test_job"
        assert result["report_id"] == 1
        assert result["status"] == "error"
        assert "Validation failed" in result["error"]
        assert result["conflicts_found"] == 0
        assert result["conflicts_resolved"] == 0
        assert result["conflicts_failed"] == 0

        # Check reporter calls
        mock_reporter.create_report.assert_called_once()
        mock_reporter.update_report_with_error.assert_called_once()

        # Check job state
        assert job.last_run is not None
        assert job.run_count == 1
        assert job.error_count == 1

    def test_job_execution_disabled(self, job) -> None:
        """Test job execution when disabled."""
        job.enabled = False

        result = job.execute()

        assert result["job_id"] == "test_job"
        assert result["status"] == "disabled"
        assert result["message"] == "Job is disabled"

        # Check job state (should not change)
        assert job.last_run is None
        assert job.run_count == 0
        assert job.error_count == 0

    def test_conflict_to_dict(self, job) -> None:
        """Test conversion of conflict to dictionary."""
        conflict = DataConflict(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="anime_metadata",
            entity_id=12345,
            severity=ConflictSeverity.HIGH,
            details="Version mismatch detected",
        )

        result = job._conflict_to_dict(conflict)

        assert result["conflict_type"] == "version_mismatch"
        assert result["entity_type"] == "anime_metadata"
        assert result["entity_id"] == 12345
        assert result["severity"] == "high"
        assert result["details"] == "Version mismatch detected"
        assert "detected_at" in result


class TestConsistencyScheduler:
    """Test ConsistencyScheduler functionality."""

    @pytest.fixture
    def mock_metadata_cache(self):
        """Create a mock metadata cache."""
        return Mock(spec=MetadataCache)

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        return Mock()

    @pytest.fixture
    def scheduler(self, mock_metadata_cache, mock_db_manager):
        """Create a consistency scheduler."""
        return ConsistencyScheduler(metadata_cache=mock_metadata_cache, db_manager=mock_db_manager)

    def test_scheduler_creation(self, scheduler) -> None:
        """Test scheduler object creation."""
        assert len(scheduler.jobs) == 0
        assert scheduler.running is False
        assert scheduler.scheduler_thread is None
        assert len(scheduler.callbacks) == 0

    def test_add_job(self, scheduler) -> None:
        """Test adding a job to the scheduler."""
        job = scheduler.add_job(
            job_id="test_job",
            interval_seconds=300,
            strategy=ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH,
            enabled=True,
        )

        assert job.job_id == "test_job"
        assert job.enabled is True
        assert job.strategy == ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH
        assert "test_job" in scheduler.jobs
        assert scheduler.jobs["test_job"] == job

    def test_remove_job(self, scheduler) -> None:
        """Test removing a job from the scheduler."""
        scheduler.add_job("test_job", 300)

        result = scheduler.remove_job("test_job")

        assert result is True
        assert "test_job" not in scheduler.jobs

        # Try to remove non-existent job
        result = scheduler.remove_job("nonexistent")
        assert result is False

    def test_run_job_now(self, scheduler) -> None:
        """Test running a job immediately."""
        job = scheduler.add_job("test_job", 300)

        with patch.object(job, "execute") as mock_execute:
            mock_execute.return_value = {"status": "success"}
            result = scheduler.run_job_now("test_job")

        assert result is not None
        assert result["status"] == "success"
        mock_execute.assert_called_once()

    def test_run_job_now_not_found(self, scheduler) -> None:
        """Test running a non-existent job."""
        result = scheduler.run_job_now("nonexistent")
        assert result is None

    def test_run_all_jobs_now(self, scheduler) -> None:
        """Test running all enabled jobs immediately."""
        job1 = scheduler.add_job("job1", 300, enabled=True)
        scheduler.add_job("job2", 300, enabled=False)  # Disabled
        job3 = scheduler.add_job("job3", 300, enabled=True)

        with (
            patch.object(job1, "execute") as mock_execute1,
            patch.object(job3, "execute") as mock_execute3,
        ):
            mock_execute1.return_value = {"status": "success", "job_id": "job1"}
            mock_execute3.return_value = {"status": "success", "job_id": "job3"}

            results = scheduler.run_all_jobs_now()

        assert len(results) == 2  # Only enabled jobs
        assert "job1" in results
        assert "job2" not in results
        assert "job3" in results
        mock_execute1.assert_called_once()
        mock_execute3.assert_called_once()

    def test_get_job_status(self, scheduler) -> None:
        """Test getting job status."""
        scheduler.add_job("test_job", 300)

        status = scheduler.get_job_status("test_job")

        assert status is not None
        assert status["job_id"] == "test_job"
        assert status["enabled"] is True
        assert status["strategy"] == "database_is_source_of_truth"
        assert status["last_run"] is None
        assert status["run_count"] == 0
        assert status["error_count"] == 0

    def test_get_job_status_not_found(self, scheduler) -> None:
        """Test getting status for non-existent job."""
        status = scheduler.get_job_status("nonexistent")
        assert status is None

    def test_get_all_job_status(self, scheduler) -> None:
        """Test getting status for all jobs."""
        scheduler.add_job("job1", 300)
        scheduler.add_job("job2", 600)

        all_status = scheduler.get_all_job_status()

        assert len(all_status) == 2
        assert "job1" in all_status
        assert "job2" in all_status

    def test_add_callback(self, scheduler) -> None:
        """Test adding a callback function."""
        callback = Mock()
        scheduler.add_callback(callback)

        assert callback in scheduler.callbacks

    def test_remove_callback(self, scheduler) -> None:
        """Test removing a callback function."""
        callback = Mock()
        scheduler.add_callback(callback)

        result = scheduler.remove_callback(callback)
        assert result is True
        assert callback not in scheduler.callbacks

        # Try to remove non-existent callback
        result = scheduler.remove_callback(Mock())
        assert result is False

    def test_callback_notification(self, scheduler) -> None:
        """Test callback notification after job execution."""
        callback = Mock()
        scheduler.add_callback(callback)

        job = scheduler.add_job("test_job", 300)

        with patch.object(job, "execute") as mock_execute:
            mock_execute.return_value = {"status": "success"}
            scheduler.run_job_now("test_job")

        callback.assert_called_once_with({"status": "success"})

    def test_callback_error_handling(self, scheduler) -> None:
        """Test error handling in callbacks."""

        def failing_callback(result) -> NoReturn:
            raise Exception("Callback failed")

        callback = Mock()
        scheduler.add_callback(failing_callback)
        scheduler.add_callback(callback)

        job = scheduler.add_job("test_job", 300)

        with patch.object(job, "execute") as mock_execute:
            mock_execute.return_value = {"status": "success"}
            scheduler.run_job_now("test_job")

        # Both callbacks should be called despite the first one failing
        callback.assert_called_once_with({"status": "success"})

    def test_scheduler_start_stop(self, scheduler) -> None:
        """Test starting and stopping the scheduler."""
        # Start scheduler
        scheduler.start_scheduler(check_interval=1)
        assert scheduler.running is True
        assert scheduler.scheduler_thread is not None
        assert scheduler.scheduler_thread.is_alive()

        # Stop scheduler
        scheduler.stop_scheduler()
        assert scheduler.running is False

    def test_scheduler_already_running(self, scheduler) -> None:
        """Test starting scheduler when already running."""
        scheduler.start_scheduler()
        assert scheduler.running is True

        # Try to start again
        scheduler.start_scheduler()
        assert scheduler.running is True

    def test_scheduler_not_running(self, scheduler) -> None:
        """Test stopping scheduler when not running."""
        assert scheduler.running is False
        scheduler.stop_scheduler()
        assert scheduler.running is False


class TestGlobalScheduler:
    """Test global scheduler functionality."""

    def test_get_global_scheduler(self) -> None:
        """Test getting global scheduler instance."""
        scheduler1 = get_global_scheduler()
        scheduler2 = get_global_scheduler()

        # Should return the same instance
        assert scheduler1 is scheduler2

    def test_add_global_job(self) -> None:
        """Test adding a job to the global scheduler."""
        job = add_global_job(
            job_id="global_test_job",
            interval_seconds=300,
            strategy=ReconciliationStrategy.LAST_MODIFIED_WINS,
            enabled=True,
        )

        assert job.job_id == "global_test_job"
        assert job.strategy == ReconciliationStrategy.LAST_MODIFIED_WINS
        assert job.enabled is True

    def test_start_stop_global_scheduler(self) -> None:
        """Test starting and stopping the global scheduler."""
        # Start global scheduler
        start_global_scheduler(check_interval=1)

        # Get scheduler and check it's running
        scheduler = get_global_scheduler()
        assert scheduler.running is True

        # Stop global scheduler
        stop_global_scheduler()
        assert scheduler.running is False

    def test_global_scheduler_integration(self) -> None:
        """Test integration of global scheduler with jobs."""
        # Create a mock database manager for the reporter
        mock_db_manager = Mock()
        mock_session = Mock()

        # Create a context manager mock
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=mock_session)
        context_manager.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = context_manager

        # Mock the report object with proper datetime attributes
        mock_report = Mock()
        mock_report.id = 1
        mock_report.started_at = datetime.now(timezone.utc)
        mock_session.get.return_value = mock_report

        # Add a job with proper reporter
        add_global_job("integration_test", 300, db_manager=mock_db_manager)

        # Start scheduler
        start_global_scheduler(check_interval=1)

        try:
            # Run job immediately
            scheduler = get_global_scheduler()
            result = scheduler.run_job_now("integration_test")

            assert result is not None
            assert result["job_id"] == "integration_test"

        finally:
            # Clean up
            stop_global_scheduler()
            scheduler.remove_job("integration_test")
