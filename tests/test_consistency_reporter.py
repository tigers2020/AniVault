"""Tests for consistency reporter module."""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock

from src.core.consistency_reporter import ConsistencyReporter, ReportSummary
from src.core.consistency_validator import ConflictType, ConflictSeverity, DataConflict
from src.core.reconciliation_strategies import ReconciliationStrategy, ReconciliationResult
from src.core.database import ConsistencyReport, ConsistencyConflict


class TestConsistencyReporter:
    """Test cases for ConsistencyReporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.db_manager = Mock()
        self.session = Mock()
        
        # Create a context manager mock
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=self.session)
        context_manager.__exit__ = Mock(return_value=None)
        self.db_manager.get_session.return_value = context_manager
        
        self.reporter = ConsistencyReporter(self.db_manager)
    
    def test_create_report(self):
        """Test creating a new report."""
        # Mock database response
        mock_report = Mock()
        mock_report.id = 1
        self.session.add.return_value = None
        self.session.commit.return_value = None
        self.session.refresh.return_value = None
        
        # Test creating report
        report = self.reporter.create_report("test_job", "manual")
        
        # Verify report creation
        assert report.job_id == "test_job"
        assert report.report_type == "manual"
        assert report.status == "running"
        assert report.started_at is not None
        
        # Verify database operations
        self.session.add.assert_called_once()
        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once()
    
    def test_update_report_with_conflicts(self):
        """Test updating report with detected conflicts."""
        # Mock report
        mock_report = Mock()
        mock_report.id = 1
        mock_report.started_at = datetime.now(timezone.utc)
        self.session.get.return_value = mock_report
        
        # Create test conflicts
        conflicts = [
            DataConflict(
                conflict_type=ConflictType.VERSION_MISMATCH,
                severity=ConflictSeverity.HIGH,
                entity_type="AnimeMetadata",
                entity_id=1,
                details="Version mismatch detected",
                db_data={"version": 2},
                cache_data={"version": 1}
            ),
            DataConflict(
                conflict_type=ConflictType.DATA_MISMATCH,
                severity=ConflictSeverity.MEDIUM,
                entity_type="ParsedFile",
                entity_id=2,
                details="Data mismatch detected",
                db_data={"title": "Anime A"},
                cache_data={"title": "Anime B"}
            )
        ]
        
        # Test updating report
        self.reporter.update_report_with_conflicts(1, conflicts)
        
        # Verify report updates
        assert mock_report.total_conflicts_detected == 2
        assert mock_report.completed_at is not None
        assert mock_report.duration_seconds is not None
        
        # Verify conflicts by type
        conflicts_by_type = json.loads(mock_report.conflicts_by_type)
        assert conflicts_by_type["version_mismatch"] == 1
        assert conflicts_by_type["data_mismatch"] == 1

        # Verify conflicts by severity
        conflicts_by_severity = json.loads(mock_report.conflicts_by_severity)
        assert conflicts_by_severity["high"] == 1
        assert conflicts_by_severity["medium"] == 1
        
        # Verify database operations
        self.session.commit.assert_called_once()
    
    def test_update_report_with_resolution(self):
        """Test updating report with resolution results."""
        # Mock report
        mock_report = Mock()
        self.session.get.return_value = mock_report
        
        # Create test resolution results
        resolution_results = [
            ReconciliationResult(
                success=True,
                strategy_used=ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH,
                conflicts_resolved=1,
                conflicts_failed=0,
                details=["Successfully resolved"],
                errors=[]
            ),
            ReconciliationResult(
                success=False,
                strategy_used=ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH,
                conflicts_resolved=0,
                conflicts_failed=1,
                details=[],
                errors=["Failed to resolve"]
            )
        ]
        
        # Test updating report
        self.reporter.update_report_with_resolution(
            1, resolution_results, ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH, "partial"
        )
        
        # Verify report updates
        assert mock_report.total_conflicts_resolved == 1
        assert mock_report.resolution_strategy == "database_is_source_of_truth"
        assert mock_report.status == "partial"
        
        # Verify resolution results
        resolution_results_dict = json.loads(mock_report.resolution_results)
        assert resolution_results_dict["successful"] == 1
        assert resolution_results_dict["failed"] == 1
        assert resolution_results_dict["total"] == 2
        
        # Verify database operations
        self.session.commit.assert_called_once()
    
    def test_update_report_with_error(self):
        """Test updating report with error information."""
        # Mock report
        mock_report = Mock()
        mock_report.started_at = datetime.now(timezone.utc)
        self.session.get.return_value = mock_report
        
        # Test updating report with error
        error_details = {"exception_type": "ValueError", "traceback": "test error"}
        self.reporter.update_report_with_error(1, "Test error", error_details, "failed")
        
        # Verify report updates
        assert mock_report.error_message == "Test error"
        assert mock_report.status == "failed"
        assert mock_report.completed_at is not None
        assert mock_report.duration_seconds is not None
        
        # Verify error details
        error_details_dict = json.loads(mock_report.error_details)
        assert error_details_dict["exception_type"] == "ValueError"
        assert error_details_dict["traceback"] == "test error"
        
        # Verify database operations
        self.session.commit.assert_called_once()
    
    def test_get_report(self):
        """Test retrieving a specific report."""
        # Mock report
        mock_report = Mock()
        self.session.get.return_value = mock_report
        
        # Test getting report
        report = self.reporter.get_report(1)
        
        # Verify report retrieval
        assert report == mock_report
        self.session.get.assert_called_once_with(ConsistencyReport, 1)
    
    def test_get_reports_by_job(self):
        """Test retrieving reports by job ID."""
        # Mock query results
        mock_reports = [Mock(), Mock()]
        mock_query = Mock()
        mock_filtered = Mock()
        mock_ordered = Mock()
        mock_ordered.all.return_value = mock_reports
        mock_filtered.order_by.return_value = mock_ordered
        mock_query.filter.return_value = mock_filtered
        self.session.query.return_value = mock_query

        # Test getting reports by job
        reports = self.reporter.get_reports_by_job("test_job")

        # Verify reports retrieval
        assert reports == mock_reports
        self.session.query.assert_called_once_with(ConsistencyReport)
        mock_query.filter.assert_called_once()
        mock_filtered.order_by.assert_called_once()
        mock_ordered.all.assert_called_once()
    
    def test_get_recent_reports(self):
        """Test retrieving recent reports."""
        # Mock query results
        mock_reports = [Mock(), Mock()]
        mock_query = Mock()
        mock_ordered = Mock()
        mock_limited = Mock()
        mock_limited.all.return_value = mock_reports
        mock_ordered.limit.return_value = mock_limited
        mock_query.order_by.return_value = mock_ordered
        self.session.query.return_value = mock_query

        # Test getting recent reports
        reports = self.reporter.get_recent_reports(5)

        # Verify reports retrieval
        assert reports == mock_reports
        self.session.query.assert_called_once_with(ConsistencyReport)
        mock_query.order_by.assert_called_once()
        mock_ordered.limit.assert_called_once_with(5)
        mock_limited.all.assert_called_once()
    
    def test_get_report_summary(self):
        """Test getting report summary."""
        # Mock report with JSON data
        mock_report = Mock()
        mock_report.id = 1
        mock_report.total_conflicts_detected = 5
        mock_report.conflicts_by_type = '{"VERSION_MISMATCH": 3, "DATA_MISMATCH": 2}'
        mock_report.conflicts_by_severity = '{"HIGH": 2, "MEDIUM": 3}'
        mock_report.resolution_results = '{"successful": 4, "failed": 1, "total": 5}'
        mock_report.duration_seconds = 10.5
        mock_report.status = "success"
        
        # Mock get_report method to return the mock report
        self.reporter.get_report = Mock(return_value=mock_report)
        
        # Test getting report summary
        summary = self.reporter.get_report_summary(1)
        
        # Verify summary
        assert isinstance(summary, ReportSummary)
        assert summary.total_conflicts == 5
        assert summary.conflicts_by_type["VERSION_MISMATCH"] == 3
        assert summary.conflicts_by_type["DATA_MISMATCH"] == 2
        assert summary.conflicts_by_severity["HIGH"] == 2
        assert summary.conflicts_by_severity["MEDIUM"] == 3
        assert summary.resolution_success_rate == 0.8  # 4/5
        assert summary.duration_seconds == 10.5
        assert summary.status == "success"
    
    def test_get_report_summary_not_found(self):
        """Test getting report summary when report not found."""
        # Mock report not found
        self.session.get.return_value = None
        
        # Test getting report summary
        summary = self.reporter.get_report_summary(999)
        
        # Verify summary
        assert summary is None
    
    def test_generate_detailed_report(self):
        """Test generating detailed report."""
        # Mock report
        mock_report = Mock()
        mock_report.id = 1
        mock_report.job_id = "test_job"
        mock_report.report_type = "manual"
        mock_report.status = "success"
        mock_report.started_at = datetime.now(timezone.utc)
        mock_report.completed_at = datetime.now(timezone.utc)
        mock_report.duration_seconds = 10.5
        mock_report.total_conflicts_detected = 2
        mock_report.total_conflicts_resolved = 2
        mock_report.conflicts_by_type = '{"VERSION_MISMATCH": 2}'
        mock_report.conflicts_by_severity = '{"HIGH": 2}'
        mock_report.resolution_strategy = "database_is_source_of_truth"
        mock_report.resolution_results = '{"successful": 2, "failed": 0, "total": 2}'
        mock_report.error_message = None
        mock_report.error_details = None
        
        # Mock conflicts
        mock_conflicts = [
            Mock(
                id=1,
                conflict_type="VERSION_MISMATCH",
                conflict_severity="HIGH",
                entity_type="AnimeMetadata",
                entity_id=1,
                conflict_description="Version mismatch",
                database_data='{"version": 2}',
                cache_data='{"version": 1}',
                resolution_strategy="DATABASE_WINS",
                resolution_status="success",
                resolution_message="Resolved",
                resolution_timestamp=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
        ]
        
        # Mock query for conflicts
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = mock_conflicts
        self.session.query.return_value = mock_query
        
        # Mock get_report method to return the mock report
        self.reporter.get_report = Mock(return_value=mock_report)

        # Test generating detailed report
        detailed_report = self.reporter.generate_detailed_report(1)
        
        # Verify detailed report structure
        assert detailed_report["report_id"] == 1
        assert detailed_report["job_id"] == "test_job"
        assert detailed_report["report_type"] == "manual"
        assert detailed_report["status"] == "success"
        assert detailed_report["summary"]["total_conflicts_detected"] == 2
        assert detailed_report["summary"]["total_conflicts_resolved"] == 2
        assert len(detailed_report["conflicts"]) == 1
        assert detailed_report["conflicts"][0]["conflict_type"] == "VERSION_MISMATCH"
        assert detailed_report["error"] is None
    
    def test_update_conflict_resolution(self):
        """Test updating conflict resolution."""
        # Mock conflict
        mock_conflict = Mock()
        self.session.get.return_value = mock_conflict
        
        # Test updating conflict resolution
        self.reporter.update_conflict_resolution(
            1, ReconciliationStrategy.CACHE_IS_SOURCE_OF_TRUTH, True, "Successfully resolved"
        )
        
        # Verify conflict updates
        assert mock_conflict.resolution_strategy == "cache_is_source_of_truth"
        assert mock_conflict.resolution_status == "success"
        assert mock_conflict.resolution_message == "Successfully resolved"
        assert mock_conflict.resolution_timestamp is not None
        
        # Verify database operations
        self.session.commit.assert_called_once()
    
    def test_cleanup_old_reports(self):
        """Test cleaning up old reports."""
        # Mock old reports and conflicts
        mock_old_conflicts = [Mock(), Mock()]
        mock_old_reports = [Mock(), Mock()]
        
        # Mock query for old conflicts
        mock_conflict_query = Mock()
        mock_conflict_query.join.return_value.filter.return_value.all.return_value = mock_old_conflicts
        self.session.query.return_value = mock_conflict_query
        
        # Mock query for old reports
        mock_report_query = Mock()
        mock_report_query.filter.return_value.all.return_value = mock_old_reports
        self.session.query.side_effect = [mock_conflict_query, mock_report_query]
        
        # Test cleanup
        deleted_count = self.reporter.cleanup_old_reports(30)
        
        # Verify cleanup
        assert deleted_count == 2
        assert mock_conflict_query.join.called
        assert mock_report_query.filter.called
        self.session.commit.assert_called_once()
    
    def test_report_not_found_error(self):
        """Test error handling when report not found."""
        # Mock report not found
        self.session.get.return_value = None
        
        # Test updating non-existent report
        with pytest.raises(ValueError, match="Report 999 not found"):
            self.reporter.update_report_with_conflicts(999, [])
        
        with pytest.raises(ValueError, match="Report 999 not found"):
            self.reporter.update_report_with_resolution(999, [], ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH)
        
        with pytest.raises(ValueError, match="Report 999 not found"):
            self.reporter.update_report_with_error(999, "Test error")
    
    def test_conflict_not_found_error(self):
        """Test error handling when conflict not found."""
        # Mock conflict not found
        self.session.get.return_value = None
        
        # Test updating non-existent conflict
        with pytest.raises(ValueError, match="Conflict 999 not found"):
            self.reporter.update_conflict_resolution(999, ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH, True)
