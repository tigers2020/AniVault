"""Consistency reporting module for AniVault application.

This module provides functionality to generate, store, and retrieve
detailed reports of consistency validation runs and conflict resolution.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False

from .consistency_validator import DataConflict
from .database import ConsistencyConflict, ConsistencyReport, DatabaseManager
from .reconciliation_strategies import ReconciliationResult, ReconciliationStrategy

logger = logging.getLogger(__name__)


@dataclass
class ReportSummary:
    """Summary of a consistency validation report."""

    total_conflicts: int
    conflicts_by_type: dict[str, int]
    conflicts_by_severity: dict[str, int]
    resolution_success_rate: float
    duration_seconds: float | None
    status: str


class ConsistencyReporter:
    """Handles generation and storage of consistency validation reports."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize the consistency reporter.

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager

    def create_report(
        self, job_id: str, report_type: str = "manual", started_at: datetime | None = None
    ) -> ConsistencyReport:
        """Create a new consistency report.

        Args:
            job_id: Unique identifier for the job
            report_type: Type of report ('scheduled', 'manual', 'on_demand')
            started_at: When the validation started (defaults to now)

        Returns:
            Created ConsistencyReport instance
        """
        if started_at is None:
            started_at = datetime.now(timezone.utc)

        with self.db_manager.get_session() as session:
            report = ConsistencyReport(
                job_id=job_id, report_type=report_type, status="running", started_at=started_at
            )
            session.add(report)
            session.commit()
            session.refresh(report)
            return report

    def update_report_with_conflicts(
        self, report_id: int, conflicts: list[DataConflict], completed_at: datetime | None = None
    ) -> None:
        """Update report with detected conflicts.

        Args:
            report_id: ID of the report to update
            conflicts: List of detected conflicts
            completed_at: When validation completed (defaults to now)
        """
        if completed_at is None:
            completed_at = datetime.now(timezone.utc)

        with self.db_manager.get_session() as session:
            report = session.get(ConsistencyReport, report_id)
            if not report:
                raise ValueError(f"Report {report_id} not found")

            # Calculate conflict statistics
            conflicts_by_type = {}
            conflicts_by_severity = {}

            for conflict in conflicts:
                # Count by type
                conflict_type = conflict.conflict_type.value
                conflicts_by_type[conflict_type] = conflicts_by_type.get(conflict_type, 0) + 1

                # Count by severity
                severity = conflict.severity.value
                conflicts_by_severity[severity] = conflicts_by_severity.get(severity, 0) + 1

            # Update report (optimized JSON serialization)
            report.total_conflicts_detected = len(conflicts)
            if ORJSON_AVAILABLE:
                report.conflicts_by_type = orjson.dumps(conflicts_by_type).decode("utf-8")
                report.conflicts_by_severity = orjson.dumps(conflicts_by_severity).decode("utf-8")
            else:
                report.conflicts_by_type = json.dumps(conflicts_by_type)
                report.conflicts_by_severity = json.dumps(conflicts_by_severity)
            report.completed_at = completed_at
            report.duration_seconds = (completed_at - report.started_at).total_seconds()

            # Store individual conflicts
            for conflict in conflicts:
                self._store_conflict(session, report_id, conflict)

            session.commit()

    def update_report_with_resolution(
        self,
        report_id: int,
        resolution_results: list[ReconciliationResult],
        strategy: ReconciliationStrategy,
        status: str = "success",
    ) -> None:
        """Update report with resolution results.

        Args:
            report_id: ID of the report to update
            resolution_results: List of resolution results
            strategy: Strategy used for resolution
            status: Final status of the report
        """
        with self.db_manager.get_session() as session:
            report = session.get(ConsistencyReport, report_id)
            if not report:
                raise ValueError(f"Report {report_id} not found")

            # Calculate resolution statistics
            successful = sum(1 for result in resolution_results if result.success)
            failed = len(resolution_results) - successful

            resolution_results_dict = {
                "successful": successful,
                "failed": failed,
                "total": len(resolution_results),
            }

            # Update report (optimized JSON serialization)
            report.total_conflicts_resolved = successful
            report.resolution_strategy = strategy.value
            if ORJSON_AVAILABLE:
                report.resolution_results = orjson.dumps(resolution_results_dict).decode("utf-8")
            else:
                report.resolution_results = json.dumps(resolution_results_dict)
            report.status = status

            session.commit()

    def update_report_with_error(
        self,
        report_id: int,
        error_message: str,
        error_details: dict[str, Any] | None = None,
        status: str = "failed",
    ) -> None:
        """Update report with error information.

        Args:
            report_id: ID of the report to update
            error_message: Error message
            error_details: Additional error details
            status: Final status of the report
        """
        with self.db_manager.get_session() as session:
            report = session.get(ConsistencyReport, report_id)
            if not report:
                raise ValueError(f"Report {report_id} not found")

            report.error_message = error_message
            if error_details:
                if ORJSON_AVAILABLE:
                    report.error_details = orjson.dumps(error_details).decode("utf-8")
                else:
                    report.error_details = json.dumps(error_details)
            report.status = status
            report.completed_at = datetime.now(timezone.utc)
            report.duration_seconds = (report.completed_at - report.started_at).total_seconds()

            session.commit()

    def get_report(self, report_id: int) -> ConsistencyReport | None:
        """Get a specific report by ID.

        Args:
            report_id: ID of the report to retrieve

        Returns:
            ConsistencyReport instance or None if not found
        """
        with self.db_manager.get_session() as session:
            return session.get(ConsistencyReport, report_id)

    def get_reports_by_job(self, job_id: str) -> list[ConsistencyReport]:
        """Get all reports for a specific job.

        Args:
            job_id: Job ID to filter by

        Returns:
            List of ConsistencyReport instances
        """
        with self.db_manager.get_session() as session:
            return (
                session.query(ConsistencyReport)
                .filter(ConsistencyReport.job_id == job_id)
                .order_by(ConsistencyReport.started_at.desc())
                .all()
            )

    def get_recent_reports(self, limit: int = 10) -> list[ConsistencyReport]:
        """Get recent reports.

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of recent ConsistencyReport instances
        """
        with self.db_manager.get_session() as session:
            return (
                session.query(ConsistencyReport)
                .order_by(ConsistencyReport.started_at.desc())
                .limit(limit)
                .all()
            )

    def get_report_summary(self, report_id: int) -> ReportSummary | None:
        """Get a summary of a specific report.

        Args:
            report_id: ID of the report

        Returns:
            ReportSummary instance or None if not found
        """
        report = self.get_report(report_id)
        if not report:
            return None

        # Parse JSON fields
        conflicts_by_type = {}
        conflicts_by_severity = {}
        resolution_results = {}

        if report.conflicts_by_type:
            conflicts_by_type = json.loads(report.conflicts_by_type)
        if report.conflicts_by_severity:
            conflicts_by_severity = json.loads(report.conflicts_by_severity)
        if report.resolution_results:
            resolution_results = json.loads(report.resolution_results)

        # Calculate success rate
        resolution_success_rate = 0.0
        if resolution_results:
            total_resolved = resolution_results.get("total", 0)
            successful = resolution_results.get("successful", 0)
            if total_resolved > 0:
                resolution_success_rate = successful / total_resolved

        return ReportSummary(
            total_conflicts=report.total_conflicts_detected,
            conflicts_by_type=conflicts_by_type,
            conflicts_by_severity=conflicts_by_severity,
            resolution_success_rate=resolution_success_rate,
            duration_seconds=report.duration_seconds,
            status=report.status,
        )

    def generate_detailed_report(self, report_id: int) -> dict[str, Any]:
        """Generate a detailed report with all conflicts and resolutions.

        Args:
            report_id: ID of the report

        Returns:
            Dictionary containing detailed report information
        """
        report = self.get_report(report_id)
        if not report:
            return {}

        with self.db_manager.get_session() as session:
            conflicts = (
                session.query(ConsistencyConflict)
                .filter(ConsistencyConflict.report_id == report_id)
                .all()
            )

        # Parse JSON fields
        conflicts_by_type = {}
        conflicts_by_severity = {}
        resolution_results = {}

        if report.conflicts_by_type:
            conflicts_by_type = json.loads(report.conflicts_by_type)
        if report.conflicts_by_severity:
            conflicts_by_severity = json.loads(report.conflicts_by_severity)
        if report.resolution_results:
            resolution_results = json.loads(report.resolution_results)

        return {
            "report_id": report.id,
            "job_id": report.job_id,
            "report_type": report.report_type,
            "status": report.status,
            "started_at": report.started_at.isoformat(),
            "completed_at": report.completed_at.isoformat() if report.completed_at else None,
            "duration_seconds": report.duration_seconds,
            "summary": {
                "total_conflicts_detected": report.total_conflicts_detected,
                "total_conflicts_resolved": report.total_conflicts_resolved,
                "conflicts_by_type": conflicts_by_type,
                "conflicts_by_severity": conflicts_by_severity,
                "resolution_strategy": report.resolution_strategy,
                "resolution_results": resolution_results,
            },
            "conflicts": [
                {
                    "id": conflict.id,
                    "conflict_type": conflict.conflict_type,
                    "conflict_severity": conflict.conflict_severity,
                    "entity_type": conflict.entity_type,
                    "entity_id": conflict.entity_id,
                    "conflict_description": conflict.conflict_description,
                    "database_data": (
                        json.loads(conflict.database_data) if conflict.database_data else None
                    ),
                    "cache_data": json.loads(conflict.cache_data) if conflict.cache_data else None,
                    "resolution_strategy": conflict.resolution_strategy,
                    "resolution_status": conflict.resolution_status,
                    "resolution_message": conflict.resolution_message,
                    "resolution_timestamp": (
                        conflict.resolution_timestamp.isoformat()
                        if conflict.resolution_timestamp
                        else None
                    ),
                    "created_at": conflict.created_at.isoformat(),
                }
                for conflict in conflicts
            ],
            "error": (
                {
                    "message": report.error_message,
                    "details": json.loads(report.error_details) if report.error_details else None,
                }
                if report.error_message
                else None
            ),
        }

    def _store_conflict(self, session: Session, report_id: int, conflict: DataConflict) -> None:
        """Store a conflict in the database.

        Args:
            session: Database session
            report_id: ID of the report
            conflict: Conflict to store
        """
        # Optimized JSON serialization for conflict data
        db_data_str = None
        cache_data_str = None
        
        if conflict.db_data:
            if ORJSON_AVAILABLE:
                db_data_str = orjson.dumps(conflict.db_data).decode("utf-8")
            else:
                db_data_str = json.dumps(conflict.db_data)
        
        if conflict.cache_data:
            if ORJSON_AVAILABLE:
                cache_data_str = orjson.dumps(conflict.cache_data).decode("utf-8")
            else:
                cache_data_str = json.dumps(conflict.cache_data)
        
        conflict_record = ConsistencyConflict(
            report_id=report_id,
            conflict_type=conflict.conflict_type.value,
            conflict_severity=conflict.severity.value,
            entity_type=conflict.entity_type,
            entity_id=conflict.entity_id,
            conflict_description=conflict.details,
            database_data=db_data_str,
            cache_data=cache_data_str,
        )
        session.add(conflict_record)

    def update_conflict_resolution(
        self,
        conflict_id: int,
        strategy: ReconciliationStrategy,
        success: bool,
        message: str | None = None,
    ) -> None:
        """Update a conflict with resolution information.

        Args:
            conflict_id: ID of the conflict
            strategy: Strategy used for resolution
            success: Whether resolution was successful
            message: Resolution message
        """
        with self.db_manager.get_session() as session:
            conflict = session.get(ConsistencyConflict, conflict_id)
            if not conflict:
                raise ValueError(f"Conflict {conflict_id} not found")

            conflict.resolution_strategy = strategy.value
            conflict.resolution_status = "success" if success else "failed"
            conflict.resolution_message = message
            conflict.resolution_timestamp = datetime.now(timezone.utc)

            session.commit()

    def cleanup_old_reports(self, days_to_keep: int = 30) -> int:
        """Clean up old reports and conflicts.

        Args:
            days_to_keep: Number of days to keep reports

        Returns:
            Number of reports deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        with self.db_manager.get_session() as session:
            # Delete old conflicts first (due to foreign key constraint)
            old_conflicts = (
                session.query(ConsistencyConflict)
                .join(ConsistencyReport)
                .filter(ConsistencyReport.created_at < cutoff_date)
                .all()
            )

            for conflict in old_conflicts:
                session.delete(conflict)

            # Delete old reports
            old_reports = (
                session.query(ConsistencyReport)
                .filter(ConsistencyReport.created_at < cutoff_date)
                .all()
            )

            for report in old_reports:
                session.delete(report)

            session.commit()
            return len(old_reports)
