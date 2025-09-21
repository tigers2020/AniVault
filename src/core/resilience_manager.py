"""Resilience management system for AniVault application.

This module provides a unified resilience management system that orchestrates
circuit breakers, retry logic, fallback strategies, and health checks to ensure
robust operation during database failures and recovery.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from .circuit_breaker import CircuitBreakerManager, get_database_circuit_breaker
from .database_health import (
    DatabaseHealthChecker,
    HealthStatus,
    set_global_health_checker,
)
from .metadata_cache import MetadataCache
from .retry_logic import get_retry_statistics, reset_retry_statistics

# Configure logging
logger = logging.getLogger(__name__)


class ResilienceManager:
    """Unified resilience management system.

    This class orchestrates all resilience mechanisms including circuit breakers,
    retry logic, health checks, and fallback strategies to provide robust
    database operation with automatic recovery.
    """

    def __init__(
        self,
        metadata_cache: MetadataCache,
        health_checker: DatabaseHealthChecker | None = None,
        circuit_breaker_manager: CircuitBreakerManager | None = None,
        auto_recovery_enabled: bool = True,
        recovery_check_interval: float = 60.0,
    ) -> None:
        """Initialize the resilience manager.

        Args:
            metadata_cache: Metadata cache instance to manage
            health_checker: Database health checker instance
            circuit_breaker_manager: Circuit breaker manager instance
            auto_recovery_enabled: Whether to enable automatic recovery
            recovery_check_interval: Interval for recovery checks in seconds
        """
        self.metadata_cache = metadata_cache
        self.health_checker = health_checker
        self.circuit_breaker_manager = circuit_breaker_manager or CircuitBreakerManager()
        self.auto_recovery_enabled = auto_recovery_enabled
        self.recovery_check_interval = recovery_check_interval

        # State management
        self._is_operational = True
        self._last_recovery_attempt: float | None = None
        self._recovery_attempts = 0
        self._lock = threading.RLock()

        # Recovery monitoring
        self._recovery_monitoring = False
        self._recovery_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Statistics
        self._total_failures = 0
        self._total_recoveries = 0
        self._last_failure_time: float | None = None
        self._last_recovery_time: float | None = None

        # Setup health checker if provided
        if self.health_checker:
            self.health_checker.add_status_change_callback(self._on_health_status_change)
            set_global_health_checker(self.health_checker)

    def initialize(self) -> None:
        """Initialize the resilience management system."""
        with self._lock:
            logger.info("Initializing resilience management system")

            # Enable automatic cache-only mode in metadata cache
            self.metadata_cache.enable_auto_cache_only_mode()

            # Start health monitoring if available
            if self.health_checker:
                self.health_checker.start_monitoring()
                logger.info("Started database health monitoring")

            # Start recovery monitoring if enabled
            if self.auto_recovery_enabled:
                self._start_recovery_monitoring()

            logger.info("Resilience management system initialized")

    def shutdown(self) -> None:
        """Shutdown the resilience management system."""
        with self._lock:
            logger.info("Shutting down resilience management system")

            # Stop recovery monitoring
            self._stop_recovery_monitoring()

            # Stop health monitoring
            if self.health_checker:
                self.health_checker.stop_monitoring()

            # Disable cache-only mode
            if self.metadata_cache.is_cache_only_mode():
                self.metadata_cache.disable_cache_only_mode()

            logger.info("Resilience management system shutdown complete")

    def is_operational(self) -> bool:
        """Check if the system is currently operational.

        Returns:
            True if system is operational, False if in degraded mode
        """
        with self._lock:
            return self._is_operational

    def get_system_status(self) -> dict[str, Any]:
        """Get comprehensive system status.

        Returns:
            Dictionary containing system status information
        """
        with self._lock:
            status = {
                "is_operational": self._is_operational,
                "cache_only_mode": self.metadata_cache.is_cache_only_mode(),
                "cache_only_reason": self.metadata_cache.get_cache_only_reason(),
                "total_failures": self._total_failures,
                "total_recoveries": self._total_recoveries,
                "recovery_attempts": self._recovery_attempts,
                "last_failure_time": self._last_failure_time,
                "last_recovery_time": self._last_recovery_time,
                "last_recovery_attempt": self._last_recovery_attempt,
                "auto_recovery_enabled": self.auto_recovery_enabled,
                "recovery_monitoring": self._recovery_monitoring,
            }

            # Add health checker status
            if self.health_checker:
                status["health_status"] = self.health_checker.get_current_status().value
                status["health_statistics"] = self.health_checker.get_statistics()

            # Add circuit breaker status
            if self.circuit_breaker_manager:
                circuit_breaker = get_database_circuit_breaker()
                if circuit_breaker:
                    status["circuit_breaker_state"] = circuit_breaker.current_state
                    status["circuit_breaker_failure_count"] = circuit_breaker.fail_counter
                    status["circuit_breaker_success_count"] = circuit_breaker.success_counter

            # Add retry statistics
            try:
                retry_stats = get_retry_statistics()
                status["retry_statistics"] = retry_stats.__dict__ if retry_stats else {}
            except Exception as e:
                logger.warning(f"Could not get retry statistics: {e}")
                status["retry_statistics"] = {}

            # Add cache statistics
            cache_stats = self.metadata_cache.get_stats()
            status["cache_statistics"] = cache_stats.__dict__

            return status

    def force_recovery_check(self) -> bool:
        """Force a recovery check and attempt recovery if possible.

        Returns:
            True if recovery was attempted, False otherwise
        """
        with self._lock:
            logger.info("Performing forced recovery check")

            # Check current health status
            if self.health_checker:
                current_status = self.health_checker.check_health()
                logger.info(f"Current database health status: {current_status.value}")

                # Attempt recovery if unhealthy
                if current_status == HealthStatus.UNHEALTHY:
                    return self._attempt_recovery()
                elif current_status == HealthStatus.HEALTHY:
                    # System is healthy, ensure we're not in degraded mode
                    if not self._is_operational:
                        self._complete_recovery()
                    return True

            return False

    def reset_statistics(self) -> None:
        """Reset all resilience statistics."""
        with self._lock:
            logger.info("Resetting resilience statistics")

            self._total_failures = 0
            self._total_recoveries = 0
            self._recovery_attempts = 0
            self._last_failure_time = None
            self._last_recovery_time = None
            self._last_recovery_attempt = None

            # Reset retry statistics
            try:
                reset_retry_statistics()
            except Exception as e:
                logger.warning(f"Could not reset retry statistics: {e}")

            logger.info("Resilience statistics reset complete")

    def _on_health_status_change(self, old_status: HealthStatus, new_status: HealthStatus) -> None:
        """Handle database health status changes.

        Args:
            old_status: Previous health status
            new_status: New health status
        """
        with self._lock:
            logger.info(f"Health status changed: {old_status.value} -> {new_status.value}")

            if new_status == HealthStatus.UNHEALTHY:
                self._handle_failure()
            elif new_status == HealthStatus.HEALTHY and not self._is_operational:
                self._handle_recovery()

    def _handle_failure(self) -> None:
        """Handle system failure."""
        with self._lock:
            self._total_failures += 1
            self._last_failure_time = time.time()
            self._is_operational = False

            logger.warning(f"System failure detected (total failures: {self._total_failures})")

            # Enable cache-only mode if not already enabled
            if not self.metadata_cache.is_cache_only_mode():
                self.metadata_cache.enable_cache_only_mode("System failure detected")

    def _handle_recovery(self) -> None:
        """Handle system recovery."""
        with self._lock:
            logger.info("System recovery detected")
            self._complete_recovery()

    def _complete_recovery(self) -> None:
        """Complete system recovery."""
        with self._lock:
            self._total_recoveries += 1
            self._last_recovery_time = time.time()
            self._is_operational = True
            self._recovery_attempts = 0

            # Disable cache-only mode
            if self.metadata_cache.is_cache_only_mode():
                self.metadata_cache.disable_cache_only_mode()

            logger.info(f"System recovery completed (total recoveries: {self._total_recoveries})")

    def _attempt_recovery(self) -> bool:
        """Attempt system recovery.

        Returns:
            True if recovery was attempted, False otherwise
        """
        with self._lock:
            current_time = time.time()

            # Check if we should attempt recovery
            if (
                self._last_recovery_attempt
                and current_time - self._last_recovery_attempt < self.recovery_check_interval
            ):
                logger.debug("Recovery attempt too recent, skipping")
                return False

            self._last_recovery_attempt = current_time
            self._recovery_attempts += 1

            logger.info(f"Attempting system recovery (attempt {self._recovery_attempts})")

            try:
                # Perform recovery checks
                if self.health_checker:
                    # Force a health check
                    health_status = self.health_checker.check_health()

                    if health_status == HealthStatus.HEALTHY:
                        self._complete_recovery()
                        return True
                    else:
                        logger.warning(
                            f"Recovery attempt failed, health status: {health_status.value}"
                        )

                return True  # Recovery was attempted

            except Exception as e:
                logger.error(f"Recovery attempt failed with error: {e}")
                return True  # Recovery was attempted

    def _start_recovery_monitoring(self) -> None:
        """Start recovery monitoring in background thread."""
        with self._lock:
            if self._recovery_monitoring:
                logger.warning("Recovery monitoring is already running")
                return

            self._recovery_monitoring = True
            self._stop_event.clear()

            self._recovery_thread = threading.Thread(
                target=self._recovery_monitor_loop, name="ResilienceRecoveryMonitor", daemon=True
            )
            self._recovery_thread.start()

            logger.info(f"Started recovery monitoring (interval: {self.recovery_check_interval}s)")

    def _stop_recovery_monitoring(self) -> None:
        """Stop recovery monitoring."""
        with self._lock:
            if not self._recovery_monitoring:
                logger.warning("Recovery monitoring is not running")
                return

            self._recovery_monitoring = False
            self._stop_event.set()

            if self._recovery_thread and self._recovery_thread.is_alive():
                self._recovery_thread.join(timeout=5.0)

            logger.info("Stopped recovery monitoring")

    def _recovery_monitor_loop(self) -> None:
        """Main recovery monitoring loop running in background thread."""
        logger.debug("Recovery monitoring loop started")

        while not self._stop_event.is_set():
            try:
                # Only attempt recovery if system is not operational
                if not self._is_operational:
                    self._attempt_recovery()

                # Wait for next check or stop signal
                if self._stop_event.wait(self.recovery_check_interval):
                    break

            except Exception as e:
                logger.error(f"Error in recovery monitoring loop: {e}")
                # Continue monitoring even if individual check fails
                time.sleep(min(self.recovery_check_interval, 10.0))

        logger.debug("Recovery monitoring loop stopped")


# Global resilience manager instance
_resilience_manager: ResilienceManager | None = None


def create_resilience_manager(
    metadata_cache: MetadataCache,
    health_checker: DatabaseHealthChecker | None = None,
    auto_recovery_enabled: bool = True,
    recovery_check_interval: float = 60.0,
) -> ResilienceManager:
    """Create a resilience manager instance.

    Args:
        metadata_cache: Metadata cache to manage
        health_checker: Optional health checker instance
        auto_recovery_enabled: Whether to enable automatic recovery
        recovery_check_interval: Recovery check interval in seconds

    Returns:
        Configured resilience manager instance
    """
    return ResilienceManager(
        metadata_cache=metadata_cache,
        health_checker=health_checker,
        auto_recovery_enabled=auto_recovery_enabled,
        recovery_check_interval=recovery_check_interval,
    )


def get_resilience_manager() -> ResilienceManager | None:
    """Get the global resilience manager instance.

    Returns:
        Global resilience manager instance or None if not created
    """
    return _resilience_manager


def set_global_resilience_manager(resilience_manager: ResilienceManager) -> None:
    """Set the global resilience manager instance.

    Args:
        resilience_manager: Resilience manager instance to set as global
    """
    global _resilience_manager
    _resilience_manager = resilience_manager


def get_system_status() -> dict[str, Any]:
    """Get the current system status.

    Returns:
        System status dictionary or empty dict if no manager available
    """
    if _resilience_manager:
        return _resilience_manager.get_system_status()
    return {}


def is_system_operational() -> bool:
    """Check if the system is currently operational.

    Returns:
        True if system is operational, False otherwise
    """
    if _resilience_manager:
        return _resilience_manager.is_operational()
    return True  # Assume operational if no manager
