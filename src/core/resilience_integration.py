"""Resilience integration for AniVault application.

This module provides integration functions to set up the complete resilience
system including database health monitoring, circuit breakers, retry logic,
and fallback strategies.
"""

from __future__ import annotations

import logging

from .database import DatabaseManager
from .database_health import create_database_health_checker
from .logging_utils import log_operation_error
from .metadata_cache import MetadataCache
from .resilience_manager import create_resilience_manager, set_global_resilience_manager

# Configure logging
logger = logging.getLogger(__name__)


def setup_resilience_system(
    db_manager: DatabaseManager,
    metadata_cache: MetadataCache,
    health_check_interval: float = 30.0,
    health_check_timeout: float = 5.0,
    health_failure_threshold: int = 3,
    health_recovery_threshold: int = 2,
    auto_recovery_enabled: bool = True,
    recovery_check_interval: float = 60.0,
) -> None:
    """Set up the complete resilience system for the application.

    This function initializes and configures all resilience mechanisms:
    - Database health monitoring
    - Circuit breaker protection
    - Retry logic with exponential backoff
    - Cache-only fallback mode
    - Automatic recovery

    Args:
        db_manager: Database manager instance
        metadata_cache: Metadata cache instance
        health_check_interval: Health check interval in seconds
        health_check_timeout: Health check timeout in seconds
        health_failure_threshold: Failures before marking unhealthy
        health_recovery_threshold: Successes before marking healthy
        auto_recovery_enabled: Whether to enable automatic recovery
        recovery_check_interval: Recovery check interval in seconds
    """
    logger.info("Setting up resilience system")

    try:
        # Create and configure database health checker
        health_checker = create_database_health_checker(
            db_manager=db_manager,
            check_interval=health_check_interval,
            timeout=health_check_timeout,
            failure_threshold=health_failure_threshold,
            recovery_threshold=health_recovery_threshold,
        )

        logger.info("Created database health checker")

        # Create resilience manager
        resilience_manager = create_resilience_manager(
            metadata_cache=metadata_cache,
            health_checker=health_checker,
            auto_recovery_enabled=auto_recovery_enabled,
            recovery_check_interval=recovery_check_interval,
        )

        logger.info("Created resilience manager")

        # Set as global instance
        set_global_resilience_manager(resilience_manager)

        # Initialize the resilience system
        resilience_manager.initialize()

        logger.info("Resilience system setup complete")

    except Exception as e:
        log_operation_error("setup resilience system", e)
        raise


def shutdown_resilience_system() -> None:
    """Shutdown the resilience system gracefully."""
    logger.info("Shutting down resilience system")

    try:
        from .resilience_manager import get_resilience_manager

        resilience_manager = get_resilience_manager()
        if resilience_manager:
            resilience_manager.shutdown()
            logger.info("Resilience system shutdown complete")
        else:
            logger.warning("No resilience manager found to shutdown")

    except Exception as e:
        log_operation_error("resilience system shutdown", e)


def get_resilience_status() -> dict:
    """Get the current resilience system status.

    Returns:
        Dictionary containing resilience system status
    """
    try:
        from .resilience_manager import get_resilience_manager

        resilience_manager = get_resilience_manager()
        if resilience_manager:
            return resilience_manager.get_system_status()
        else:
            return {"error": "No resilience manager available"}

    except Exception as e:
        log_operation_error("get resilience status", e)
        return {"error": str(e)}


def force_recovery_check() -> bool:
    """Force a recovery check and attempt recovery if possible.

    Returns:
        True if recovery was attempted, False otherwise
    """
    try:
        from .resilience_manager import get_resilience_manager

        resilience_manager = get_resilience_manager()
        if resilience_manager:
            return resilience_manager.force_recovery_check()
        else:
            logger.warning("No resilience manager available for recovery check")
            return False

    except Exception as e:
        log_operation_error("forced recovery check", e)
        return False
