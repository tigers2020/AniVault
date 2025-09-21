"""Database health monitoring for AniVault application.

This module provides database health checking capabilities to monitor
database connectivity and inform resilience mechanisms.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

from .database import DatabaseManager
from .logging_utils import log_operation_error

# Configure logging
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Database health status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DatabaseHealthChecker:
    """Database health checker with configurable monitoring.

    This class provides continuous health monitoring for database connections
    and can notify other components about health status changes.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        check_interval: float = 30.0,
        timeout: float = 5.0,
        failure_threshold: int = 3,
        recovery_threshold: int = 2,
        health_check_query: str = "SELECT 1",
    ) -> None:
        """Initialize the database health checker.

        Args:
            db_manager: Database manager instance to monitor
            check_interval: Interval between health checks in seconds
            timeout: Timeout for individual health checks in seconds
            failure_threshold: Number of consecutive failures before marking unhealthy
            recovery_threshold: Number of consecutive successes before marking healthy
            health_check_query: SQL query to use for health checks
        """
        self.db_manager = db_manager
        self.check_interval = check_interval
        self.timeout = timeout
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        self.health_check_query = health_check_query

        # Health state
        self._current_status = HealthStatus.UNKNOWN
        self._last_check_time: float | None = None
        self._last_success_time: float | None = None
        self._last_failure_time: float | None = None
        self._consecutive_failures = 0
        self._consecutive_successes = 0

        # Monitoring control
        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

        # Callbacks for status changes
        self._status_change_callbacks: list[Callable[[HealthStatus, HealthStatus], None]] = []

        # Statistics
        self._total_checks = 0
        self._successful_checks = 0
        self._failed_checks = 0

    def start_monitoring(self) -> None:
        """Start continuous health monitoring in a background thread."""
        with self._lock:
            if self._monitoring:
                logger.warning("Health monitoring is already running")
                return

            self._monitoring = True
            self._stop_event.clear()

            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, name="DatabaseHealthMonitor", daemon=True
            )
            self._monitor_thread.start()

            logger.info(f"Started database health monitoring (interval: {self.check_interval}s)")

    def stop_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        with self._lock:
            if not self._monitoring:
                logger.warning("Health monitoring is not running")
                return

            self._monitoring = False
            self._stop_event.set()

            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=5.0)

            logger.info("Stopped database health monitoring")

    def check_health(self) -> HealthStatus:
        """Perform a single health check.

        Returns:
            Current health status
        """
        with self._lock:
            start_time = time.time()
            self._last_check_time = start_time
            self._total_checks += 1

            try:
                # Perform health check with timeout
                self._perform_health_check()

                # Success
                self._consecutive_failures = 0
                self._consecutive_successes += 1
                self._last_success_time = start_time
                self._successful_checks += 1

                # Update status if needed
                new_status = self._determine_status_from_success()
                if new_status != self._current_status:
                    self._notify_status_change(self._current_status, new_status)
                    self._current_status = new_status

                duration = time.time() - start_time
                logger.debug(f"Database health check successful (duration: {duration:.3f}s)")

                return self._current_status

            except Exception as e:
                # Failure
                self._consecutive_successes = 0
                self._consecutive_failures += 1
                self._last_failure_time = start_time
                self._failed_checks += 1

                # Update status if needed
                new_status = self._determine_status_from_failure()
                if new_status != self._current_status:
                    self._notify_status_change(self._current_status, new_status)
                    self._current_status = new_status

                duration = time.time() - start_time
                logger.warning(f"Database health check failed (duration: {duration:.3f}s): {e}")

                return self._current_status

    def get_current_status(self) -> HealthStatus:
        """Get the current health status.

        Returns:
            Current health status
        """
        with self._lock:
            return self._current_status

    def get_last_check_time(self) -> float | None:
        """Get the timestamp of the last health check.

        Returns:
            Timestamp of last check or None if no checks performed
        """
        with self._lock:
            return self._last_check_time

    def get_last_success_time(self) -> float | None:
        """Get the timestamp of the last successful health check.

        Returns:
            Timestamp of last success or None if no successful checks
        """
        with self._lock:
            return self._last_success_time

    def get_last_failure_time(self) -> float | None:
        """Get the timestamp of the last failed health check.

        Returns:
            Timestamp of last failure or None if no failed checks
        """
        with self._lock:
            return self._last_failure_time

    def get_statistics(self) -> dict[str, Any]:
        """Get health check statistics.

        Returns:
            Dictionary containing health check statistics
        """
        with self._lock:
            return {
                "current_status": self._current_status.value,
                "total_checks": self._total_checks,
                "successful_checks": self._successful_checks,
                "failed_checks": self._failed_checks,
                "consecutive_successes": self._consecutive_successes,
                "consecutive_failures": self._consecutive_failures,
                "last_check_time": self._last_check_time,
                "last_success_time": self._last_success_time,
                "last_failure_time": self._last_failure_time,
                "success_rate": (
                    self._successful_checks / self._total_checks if self._total_checks > 0 else 0.0
                ),
                "is_monitoring": self._monitoring,
            }

    def add_status_change_callback(
        self, callback: Callable[[HealthStatus, HealthStatus], None]
    ) -> None:
        """Add a callback for status change notifications.

        Args:
            callback: Function to call when status changes (old_status, new_status)
        """
        with self._lock:
            self._status_change_callbacks.append(callback)

    def remove_status_change_callback(
        self, callback: Callable[[HealthStatus, HealthStatus], None]
    ) -> None:
        """Remove a status change callback.

        Args:
            callback: Callback to remove
        """
        with self._lock:
            if callback in self._status_change_callbacks:
                self._status_change_callbacks.remove(callback)

    def _monitor_loop(self) -> None:
        """Main monitoring loop running in background thread."""
        logger.debug("Database health monitoring loop started")

        while not self._stop_event.is_set():
            try:
                # Perform health check
                self.check_health()

                # Wait for next check or stop signal
                if self._stop_event.wait(self.check_interval):
                    break

            except Exception as e:
                log_operation_error("health monitoring loop", e)
                # Continue monitoring even if individual check fails
                time.sleep(min(self.check_interval, 5.0))

        logger.debug("Database health monitoring loop stopped")

    def _perform_health_check(self) -> None:
        """Perform the actual database health check."""
        if not self.db_manager:
            raise RuntimeError("Database manager not available")

        # Ensure database is initialized
        if not self.db_manager._initialized:
            self.db_manager.initialize()

        # Perform a simple query with timeout
        with self.db_manager.get_session() as session:
            from sqlalchemy import text

            result = session.execute(text(self.health_check_query))
            result.fetchone()  # Consume the result

    def _determine_status_from_success(self) -> HealthStatus:
        """Determine new status after a successful check."""
        if self._consecutive_successes >= self.recovery_threshold:
            return HealthStatus.HEALTHY
        elif self._current_status == HealthStatus.UNKNOWN:
            return HealthStatus.HEALTHY
        else:
            return self._current_status

    def _determine_status_from_failure(self) -> HealthStatus:
        """Determine new status after a failed check."""
        if self._consecutive_failures >= self.failure_threshold:
            return HealthStatus.UNHEALTHY
        elif self._current_status == HealthStatus.UNKNOWN:
            return HealthStatus.UNHEALTHY
        else:
            return self._current_status

    def _notify_status_change(self, old_status: HealthStatus, new_status: HealthStatus) -> None:
        """Notify all registered callbacks of status change."""
        logger.info(f"Database health status changed: {old_status.value} -> {new_status.value}")

        for callback in self._status_change_callbacks:
            try:
                callback(old_status, new_status)
            except Exception as e:
                log_operation_error("status change callback", e)


# Global health checker instance
_health_checker: DatabaseHealthChecker | None = None


def create_database_health_checker(
    db_manager: DatabaseManager,
    check_interval: float = 30.0,
    timeout: float = 5.0,
    failure_threshold: int = 3,
    recovery_threshold: int = 2,
) -> DatabaseHealthChecker:
    """Create a database health checker instance.

    Args:
        db_manager: Database manager to monitor
        check_interval: Interval between checks in seconds
        timeout: Timeout for individual checks in seconds
        failure_threshold: Failures before marking unhealthy
        recovery_threshold: Successes before marking healthy

    Returns:
        Configured health checker instance
    """
    return DatabaseHealthChecker(
        db_manager=db_manager,
        check_interval=check_interval,
        timeout=timeout,
        failure_threshold=failure_threshold,
        recovery_threshold=recovery_threshold,
    )


def get_database_health_checker() -> DatabaseHealthChecker | None:
    """Get the global database health checker instance.

    Returns:
        Global health checker instance or None if not created
    """
    return _health_checker


def set_global_health_checker(health_checker: DatabaseHealthChecker) -> None:
    """Set the global database health checker instance.

    Args:
        health_checker: Health checker instance to set as global
    """
    global _health_checker
    _health_checker = health_checker


def get_database_health_status() -> HealthStatus:
    """Get the current database health status.

    Returns:
        Current health status or UNKNOWN if no checker available
    """
    if _health_checker:
        return _health_checker.get_current_status()
    return HealthStatus.UNKNOWN


def is_database_healthy() -> bool:
    """Check if the database is currently healthy.

    Returns:
        True if database is healthy, False otherwise
    """
    return get_database_health_status() == HealthStatus.HEALTHY
