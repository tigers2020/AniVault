"""Circuit breaker module for database operations.

This module provides circuit breaker functionality to prevent cascading failures
during database outages and protect the system from unresponsive database operations.

Author: AniVault Development Team
Created: 2025-01-19
"""

import logging
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any

from pybreaker import CircuitBreaker, CircuitBreakerError, CircuitBreakerListener
from sqlalchemy.exc import (
    DataError,
    DisconnectionError,
    IntegrityError,
    InterfaceError,
    OperationalError,
    ProgrammingError,
    TimeoutError,
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerConfiguration:
    """Configuration class for circuit breaker behavior."""

    def __init__(
        self,
        fail_max: int = 5,
        reset_timeout: int = 30,
        call_timeout: int | None = 10,
        expected_exception: set[type[Exception]] | None = None,
        exclude: set[type[Exception]] | None = None,
        name: str = "database_circuit_breaker",
    ):
        """Initialize circuit breaker configuration.

        Args:
            fail_max: Number of failures before opening the circuit
            reset_timeout: Time in seconds to stay open before half-opening
            call_timeout: Timeout for individual function calls (optional)
            expected_exception: Exceptions that should trip the circuit
            exclude: Exceptions that should NOT trip the circuit
            name: Name of the circuit breaker for logging
        """
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.call_timeout = call_timeout
        self.expected_exception = expected_exception or {
            OperationalError,
            DisconnectionError,
            InterfaceError,
            TimeoutError,
        }
        self.exclude = exclude or {
            IntegrityError,
            ProgrammingError,
            DataError,
        }
        self.name = name


class DatabaseCircuitBreakerListener(CircuitBreakerListener):
    """Listener for circuit breaker events with comprehensive logging."""

    def __init__(self, logger_name: str = __name__):
        """Initialize the listener.

        Args:
            logger_name: Name of the logger to use
        """
        self.logger = logging.getLogger(logger_name)

    def before_call(self, cb: CircuitBreaker, func: Callable, *args, **kwargs) -> None:
        """Called before a function is executed through the circuit breaker."""
        self.logger.debug(
            f"CircuitBreaker '{cb.name}' before_call for {func.__name__}. "
            f"State: {cb.current_state}"
        )

    def on_success(self, cb: CircuitBreaker, func: Callable, *args, **kwargs) -> None:
        """Called when a function executed through the circuit breaker succeeds."""
        self.logger.info(
            f"CircuitBreaker '{cb.name}' on_success for {func.__name__}. "
            f"State: {cb.current_state}"
        )

    def on_failure(
        self, cb: CircuitBreaker, func: Callable, exc: Exception, *args, **kwargs
    ) -> None:
        """Called when a function executed through the circuit breaker fails."""
        self.logger.warning(
            f"CircuitBreaker '{cb.name}' on_failure for {func.__name__} "
            f"with exception: {type(exc).__name__}. State: {cb.current_state}"
        )

    def on_timeout(
        self, cb: CircuitBreaker, func: Callable, exc: Exception, *args, **kwargs
    ) -> None:
        """Called when a function executed through the circuit breaker times out."""
        self.logger.error(
            f"CircuitBreaker '{cb.name}' on_timeout for {func.__name__} "
            f"with exception: {type(exc).__name__}. State: {cb.current_state}"
        )

    def on_open(self, cb: CircuitBreaker) -> None:
        """Called when the circuit breaker opens."""
        self.logger.error(
            f"CircuitBreaker '{cb.name}' OPENED! Database operations will be rejected. "
            f"Failures: {cb.fail_count}/{cb.fail_max}"
        )
        # TODO: Trigger alerting here (Task 7)

    def on_half_open(self, cb: CircuitBreaker) -> None:
        """Called when the circuit breaker transitions to half-open."""
        self.logger.warning(f"CircuitBreaker '{cb.name}' HALF-OPEN. Allowing a trial call.")

    def on_close(self, cb: CircuitBreaker) -> None:
        """Called when the circuit breaker closes."""
        self.logger.info(f"CircuitBreaker '{cb.name}' CLOSED. Database operations are now allowed.")
        # TODO: Trigger alerting here (Task 7)


class CircuitBreakerManager:
    """Manager class for circuit breaker instances."""

    def __init__(self):
        """Initialize the circuit breaker manager."""
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._listeners: dict[str, DatabaseCircuitBreakerListener] = {}

    def create_circuit_breaker(
        self,
        config: CircuitBreakerConfiguration,
        listener: DatabaseCircuitBreakerListener | None = None,
    ) -> CircuitBreaker:
        """Create a new circuit breaker instance.

        Args:
            config: Circuit breaker configuration
            listener: Optional custom listener

        Returns:
            Configured circuit breaker instance
        """
        if config.name in self._circuit_breakers:
            logger.warning(
                f"Circuit breaker '{config.name}' already exists. Returning existing instance."
            )
            return self._circuit_breakers[config.name]

        # Create listener if not provided
        if listener is None:
            listener = DatabaseCircuitBreakerListener()

        # Create circuit breaker
        # In pybreaker, exclude parameter contains exceptions that should NOT trip the circuit
        circuit_breaker = CircuitBreaker(
            fail_max=config.fail_max,
            reset_timeout=config.reset_timeout,
            exclude=tuple(config.exclude),
            listeners=[listener],
            name=config.name,
        )

        # Store references
        self._circuit_breakers[config.name] = circuit_breaker
        self._listeners[config.name] = listener

        logger.info(
            f"Created circuit breaker '{config.name}' with configuration: {config.__dict__}"
        )
        return circuit_breaker

    def get_circuit_breaker(self, name: str) -> CircuitBreaker | None:
        """Get an existing circuit breaker by name.

        Args:
            name: Name of the circuit breaker

        Returns:
            Circuit breaker instance or None if not found
        """
        return self._circuit_breakers.get(name)

    def get_all_circuit_breakers(self) -> dict[str, CircuitBreaker]:
        """Get all circuit breaker instances.

        Returns:
            Dictionary of circuit breaker instances
        """
        return self._circuit_breakers.copy()

    def get_circuit_breaker_state(self, name: str) -> CircuitState | None:
        """Get the current state of a circuit breaker.

        Args:
            name: Name of the circuit breaker

        Returns:
            Current state or None if not found
        """
        circuit_breaker = self.get_circuit_breaker(name)
        if circuit_breaker is None:
            return None

        state_map = {
            "closed": CircuitState.CLOSED,
            "open": CircuitState.OPEN,
            "half_open": CircuitState.HALF_OPEN,
        }

        return state_map.get(circuit_breaker.current_state, None)

    def get_circuit_breaker_stats(self, name: str) -> dict[str, Any] | None:
        """Get statistics for a circuit breaker.

        Args:
            name: Name of the circuit breaker

        Returns:
            Statistics dictionary or None if not found
        """
        circuit_breaker = self.get_circuit_breaker(name)
        if circuit_breaker is None:
            return None

        return {
            "name": circuit_breaker.name,
            "state": circuit_breaker.current_state,
            "fail_count": circuit_breaker.fail_counter,
            "fail_max": circuit_breaker.fail_max,
            "reset_timeout": circuit_breaker.reset_timeout,
        }

    def reset_circuit_breaker(self, name: str) -> bool:
        """Reset a circuit breaker to closed state.

        Args:
            name: Name of the circuit breaker

        Returns:
            True if reset successfully, False otherwise
        """
        circuit_breaker = self.get_circuit_breaker(name)
        if circuit_breaker is None:
            logger.warning(f"Cannot reset circuit breaker '{name}': not found")
            return False

        try:
            circuit_breaker.close()
            logger.info(f"Reset circuit breaker '{name}' to closed state")
            return True
        except Exception as e:
            logger.error(f"Failed to reset circuit breaker '{name}': {e}")
            return False


# Global circuit breaker manager instance
circuit_breaker_manager = CircuitBreakerManager()


def create_database_circuit_breaker(
    config: CircuitBreakerConfiguration | None = None,
    listener: DatabaseCircuitBreakerListener | None = None,
) -> CircuitBreaker:
    """Create a database circuit breaker with default configuration.

    Args:
        config: Optional custom configuration
        listener: Optional custom listener

    Returns:
        Configured circuit breaker instance
    """
    if config is None:
        config = CircuitBreakerConfiguration()

    return circuit_breaker_manager.create_circuit_breaker(config, listener)


def get_database_circuit_breaker(
    name: str = "database_circuit_breaker",
) -> CircuitBreaker | None:
    """Get the default database circuit breaker.

    Args:
        name: Name of the circuit breaker

    Returns:
        Circuit breaker instance or None if not found
    """
    return circuit_breaker_manager.get_circuit_breaker(name)


def circuit_breaker_protect(
    circuit_breaker: CircuitBreaker | None = None,
    operation_name: str | None = None,
    fallback_func: Callable | None = None,
):
    """Decorator to protect database operations with circuit breaker.

    Args:
        circuit_breaker: Circuit breaker instance to use
        operation_name: Name of the operation for logging
        fallback_func: Optional fallback function to call when circuit is open

    Example:
        @circuit_breaker_protect(operation_name="save_metadata")
        def save_metadata(session: Session, data: dict) -> bool:
            # Database operation here
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            op_name = operation_name or func.__name__
            cb = circuit_breaker or get_database_circuit_breaker()

            if cb is None:
                logger.warning(f"No circuit breaker available for operation: {op_name}")
                return func(*args, **kwargs)

            try:
                logger.debug(f"Executing protected operation: {op_name}")
                result = cb.call(func, *args, **kwargs)
                logger.debug(f"Successfully completed protected operation: {op_name}")
                return result
            except CircuitBreakerError as e:
                logger.warning(f"Circuit breaker is open for operation: {op_name}")
                if fallback_func:
                    logger.info(f"Executing fallback for operation: {op_name}")
                    return fallback_func()
                raise e
            except Exception as e:
                logger.error(f"Operation failed: {op_name}. Error: {e}")
                raise

        return wrapper

    return decorator


def is_circuit_breaker_open(circuit_breaker: CircuitBreaker | None = None) -> bool:
    """Check if the circuit breaker is open.

    Args:
        circuit_breaker: Circuit breaker instance to check

    Returns:
        True if circuit is open, False otherwise
    """
    cb = circuit_breaker or get_database_circuit_breaker()
    if cb is None:
        return False

    return cb.current_state == "open"


def get_circuit_breaker_health() -> dict[str, Any]:
    """Get health status of all circuit breakers.

    Returns:
        Dictionary containing health information
    """
    all_breakers = circuit_breaker_manager.get_all_circuit_breakers()
    health_info = {
        "total_breakers": len(all_breakers),
        "breakers": {},
    }

    for name, breaker in all_breakers.items():
        health_info["breakers"][name] = {
            "state": breaker.current_state,
            "fail_count": breaker.fail_counter,
            "fail_max": breaker.fail_max,
            "is_healthy": breaker.current_state == "closed",
        }

    return health_info


# Create default database circuit breaker
default_database_circuit_breaker = create_database_circuit_breaker()
