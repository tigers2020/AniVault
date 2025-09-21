"""Unit tests for circuit breaker module.

Tests the circuit breaker functionality, state transitions, error handling,
and integration with database operations.

Author: AniVault Development Team
Created: 2025-01-19
"""

import time
from typing import NoReturn
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import (
    DisconnectionError,
    IntegrityError,
    OperationalError,
    TimeoutError,
)

from src.core.circuit_breaker import (
    CircuitBreakerConfiguration,
    CircuitBreakerManager,
    CircuitState,
    DatabaseCircuitBreakerListener,
    circuit_breaker_manager,
    circuit_breaker_protect,
    create_database_circuit_breaker,
    get_circuit_breaker_health,
    get_database_circuit_breaker,
    is_circuit_breaker_open,
)


class TestCircuitBreakerConfiguration:
    """Test cases for CircuitBreakerConfiguration class."""

    def test_default_configuration(self) -> None:
        """Test default configuration values."""
        config = CircuitBreakerConfiguration()

        assert config.fail_max == 5
        assert config.reset_timeout == 30
        assert config.call_timeout == 10
        assert config.name == "database_circuit_breaker"
        assert len(config.expected_exception) > 0
        assert len(config.exclude) > 0

    def test_custom_configuration(self) -> None:
        """Test custom configuration values."""
        custom_exceptions = {OperationalError, DisconnectionError}
        custom_exclude = {IntegrityError}

        config = CircuitBreakerConfiguration(
            fail_max=3,
            reset_timeout=60,
            call_timeout=5,
            expected_exception=custom_exceptions,
            exclude=custom_exclude,
            name="custom_circuit_breaker",
        )

        assert config.fail_max == 3
        assert config.reset_timeout == 60
        assert config.call_timeout == 5
        assert config.expected_exception == custom_exceptions
        assert config.exclude == custom_exclude
        assert config.name == "custom_circuit_breaker"


class TestDatabaseCircuitBreakerListener:
    """Test cases for DatabaseCircuitBreakerListener class."""

    def test_listener_initialization(self) -> None:
        """Test listener initialization."""
        listener = DatabaseCircuitBreakerListener()
        assert listener.logger is not None

    def test_listener_with_custom_logger(self) -> None:
        """Test listener with custom logger name."""
        listener = DatabaseCircuitBreakerListener("custom_logger")
        assert listener.logger.name == "custom_logger"

    def test_before_call(self) -> None:
        """Test before_call method."""
        listener = DatabaseCircuitBreakerListener()
        mock_cb = Mock()
        mock_cb.name = "test_circuit"
        mock_cb.current_state = "closed"
        mock_func = Mock()
        mock_func.__name__ = "test_function"

        # Should not raise any exceptions
        listener.before_call(mock_cb, mock_func, "arg1", "arg2", kwarg1="value1")

    def test_on_success(self) -> None:
        """Test on_success method."""
        listener = DatabaseCircuitBreakerListener()
        mock_cb = Mock()
        mock_cb.name = "test_circuit"
        mock_cb.current_state = "closed"
        mock_func = Mock()
        mock_func.__name__ = "test_function"

        # Should not raise any exceptions
        listener.on_success(mock_cb, mock_func, "arg1", "arg2", kwarg1="value1")

    def test_on_failure(self) -> None:
        """Test on_failure method."""
        listener = DatabaseCircuitBreakerListener()
        mock_cb = Mock()
        mock_cb.name = "test_circuit"
        mock_cb.current_state = "closed"
        mock_func = Mock()
        mock_func.__name__ = "test_function"
        mock_exc = OperationalError("Connection lost", {}, None)

        # Should not raise any exceptions
        listener.on_failure(mock_cb, mock_func, mock_exc, "arg1", "arg2", kwarg1="value1")

    def test_on_timeout(self) -> None:
        """Test on_timeout method."""
        listener = DatabaseCircuitBreakerListener()
        mock_cb = Mock()
        mock_cb.name = "test_circuit"
        mock_cb.current_state = "closed"
        mock_func = Mock()
        mock_func.__name__ = "test_function"
        mock_exc = TimeoutError("Operation timed out")

        # Should not raise any exceptions
        listener.on_timeout(mock_cb, mock_func, mock_exc, "arg1", "arg2", kwarg1="value1")

    def test_on_open(self) -> None:
        """Test on_open method."""
        listener = DatabaseCircuitBreakerListener()
        mock_cb = Mock()
        mock_cb.name = "test_circuit"
        mock_cb.fail_count = 5
        mock_cb.fail_max = 5

        # Should not raise any exceptions
        listener.on_open(mock_cb)

    def test_on_half_open(self) -> None:
        """Test on_half_open method."""
        listener = DatabaseCircuitBreakerListener()
        mock_cb = Mock()
        mock_cb.name = "test_circuit"

        # Should not raise any exceptions
        listener.on_half_open(mock_cb)

    def test_on_close(self) -> None:
        """Test on_close method."""
        listener = DatabaseCircuitBreakerListener()
        mock_cb = Mock()
        mock_cb.name = "test_circuit"

        # Should not raise any exceptions
        listener.on_close(mock_cb)


class TestCircuitBreakerManager:
    """Test cases for CircuitBreakerManager class."""

    def setup_method(self) -> None:
        """Reset manager before each test."""
        self.manager = CircuitBreakerManager()

    def test_create_circuit_breaker(self) -> None:
        """Test creating a circuit breaker."""
        config = CircuitBreakerConfiguration(name="test_circuit")
        circuit_breaker = self.manager.create_circuit_breaker(config)

        assert circuit_breaker is not None
        assert circuit_breaker.name == "test_circuit"
        assert self.manager.get_circuit_breaker("test_circuit") == circuit_breaker

    def test_create_duplicate_circuit_breaker(self) -> None:
        """Test creating a duplicate circuit breaker."""
        config = CircuitBreakerConfiguration(name="test_circuit")
        circuit_breaker1 = self.manager.create_circuit_breaker(config)
        circuit_breaker2 = self.manager.create_circuit_breaker(config)

        assert circuit_breaker1 == circuit_breaker2

    def test_get_circuit_breaker(self) -> None:
        """Test getting a circuit breaker."""
        config = CircuitBreakerConfiguration(name="test_circuit")
        circuit_breaker = self.manager.create_circuit_breaker(config)

        retrieved = self.manager.get_circuit_breaker("test_circuit")
        assert retrieved == circuit_breaker

        not_found = self.manager.get_circuit_breaker("nonexistent")
        assert not_found is None

    def test_get_all_circuit_breakers(self) -> None:
        """Test getting all circuit breakers."""
        config1 = CircuitBreakerConfiguration(name="test_circuit1")
        config2 = CircuitBreakerConfiguration(name="test_circuit2")

        circuit_breaker1 = self.manager.create_circuit_breaker(config1)
        circuit_breaker2 = self.manager.create_circuit_breaker(config2)

        all_breakers = self.manager.get_all_circuit_breakers()
        assert len(all_breakers) == 2
        assert all_breakers["test_circuit1"] == circuit_breaker1
        assert all_breakers["test_circuit2"] == circuit_breaker2

    def test_get_circuit_breaker_state(self) -> None:
        """Test getting circuit breaker state."""
        config = CircuitBreakerConfiguration(name="test_circuit")
        self.manager.create_circuit_breaker(config)

        state = self.manager.get_circuit_breaker_state("test_circuit")
        assert state == CircuitState.CLOSED

        not_found = self.manager.get_circuit_breaker_state("nonexistent")
        assert not_found is None

    def test_get_circuit_breaker_stats(self) -> None:
        """Test getting circuit breaker statistics."""
        config = CircuitBreakerConfiguration(name="test_circuit")
        self.manager.create_circuit_breaker(config)

        stats = self.manager.get_circuit_breaker_stats("test_circuit")
        assert stats is not None
        assert stats["name"] == "test_circuit"
        assert stats["state"] == "closed"
        assert stats["fail_count"] == 0
        assert stats["fail_max"] == 5
        assert stats["reset_timeout"] == 30

        not_found = self.manager.get_circuit_breaker_stats("nonexistent")
        assert not_found is None

    def test_reset_circuit_breaker(self) -> None:
        """Test resetting a circuit breaker."""
        config = CircuitBreakerConfiguration(name="test_circuit")
        circuit_breaker = self.manager.create_circuit_breaker(config)

        # Mock the close method
        circuit_breaker.close = Mock()

        result = self.manager.reset_circuit_breaker("test_circuit")
        assert result is True
        circuit_breaker.close.assert_called_once()

        # Test resetting non-existent circuit breaker
        result = self.manager.reset_circuit_breaker("nonexistent")
        assert result is False


class TestCircuitBreakerIntegration:
    """Test cases for circuit breaker integration."""

    def setup_method(self) -> None:
        """Set up test method by clearing circuit breaker manager."""
        circuit_breaker_manager._circuit_breakers.clear()
        # Reset the default circuit breaker
        global default_database_circuit_breaker
        default_database_circuit_breaker = None
        # Force recreation of circuit breakers by clearing the manager's internal state
        circuit_breaker_manager._circuit_breakers = {}

    def test_create_database_circuit_breaker_default(self) -> None:
        """Test creating database circuit breaker with default config."""
        circuit_breaker = create_database_circuit_breaker()
        assert circuit_breaker is not None
        assert circuit_breaker.name == "database_circuit_breaker"

    def test_create_database_circuit_breaker_custom(self) -> None:
        """Test creating database circuit breaker with custom config."""
        config = CircuitBreakerConfiguration(
            name="custom_db_circuit",
            fail_max=3,
            reset_timeout=60,
        )
        circuit_breaker = create_database_circuit_breaker(config)
        assert circuit_breaker is not None
        assert circuit_breaker.name == "custom_db_circuit"

    def test_get_database_circuit_breaker(self) -> None:
        """Test getting database circuit breaker."""
        circuit_breaker = get_database_circuit_breaker()
        assert circuit_breaker is not None

        # Test with custom name
        custom_circuit = get_database_circuit_breaker("custom_name")
        assert custom_circuit is None  # Should not exist

    def test_circuit_breaker_protect_decorator_success(self) -> None:
        """Test circuit breaker protect decorator with successful operation."""
        config = CircuitBreakerConfiguration(
            name="test_circuit",
            fail_max=3,
            reset_timeout=1,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker, operation_name="test_operation")
        def test_operation() -> str:
            return "success"

        result = test_operation()
        assert result == "success"

    def test_circuit_breaker_protect_decorator_with_fallback(self) -> None:
        """Test circuit breaker protect decorator with fallback function."""
        config = CircuitBreakerConfiguration(
            name="test_circuit_fallback",
            fail_max=1,
            reset_timeout=1,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        def fallback_func() -> str:
            return "fallback_result"

        @circuit_breaker_protect(
            circuit_breaker,
            operation_name="test_operation",
            fallback_func=fallback_func,
        )
        def test_operation() -> NoReturn:
            raise OperationalError("Connection lost", {}, None)

        # First call should fail and trip the circuit
        with pytest.raises(OperationalError):
            test_operation()

        # Second call should use fallback since circuit is open
        result = test_operation()
        assert result == "fallback_result"

    def test_circuit_breaker_protect_decorator_no_circuit_breaker(self) -> None:
        """Test circuit breaker protect decorator without circuit breaker."""

        @circuit_breaker_protect(operation_name="test_operation")
        def test_operation() -> str:
            return "success"

        result = test_operation()
        assert result == "success"

    def test_is_circuit_breaker_open(self) -> None:
        """Test checking if circuit breaker is open."""
        config = CircuitBreakerConfiguration(
            name="test_circuit_open",
            fail_max=1,
            reset_timeout=1,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        # Initially closed
        assert not is_circuit_breaker_open(circuit_breaker)

        # Trip the circuit
        @circuit_breaker_protect(circuit_breaker)
        def failing_operation() -> NoReturn:
            raise OperationalError("Connection lost", {}, None)

        with pytest.raises(OperationalError):
            failing_operation()

        # Now should be open
        assert is_circuit_breaker_open(circuit_breaker)

    def test_get_circuit_breaker_health(self) -> None:
        """Test getting circuit breaker health information."""
        config1 = CircuitBreakerConfiguration(name="test_circuit1")
        config2 = CircuitBreakerConfiguration(name="test_circuit2")

        create_database_circuit_breaker(config1)
        create_database_circuit_breaker(config2)

        health = get_circuit_breaker_health()
        assert health["total_breakers"] >= 2
        assert "breakers" in health
        assert "test_circuit1" in health["breakers"]
        assert "test_circuit2" in health["breakers"]


class TestCircuitBreakerStateTransitions:
    """Test cases for circuit breaker state transitions."""

    def setup_method(self) -> None:
        """Set up test method by clearing circuit breaker manager."""
        circuit_breaker_manager._circuit_breakers.clear()
        # Reset the default circuit breaker
        global default_database_circuit_breaker
        default_database_circuit_breaker = None
        # Force recreation of circuit breakers by clearing the manager's internal state
        circuit_breaker_manager._circuit_breakers = {}

    def test_circuit_breaker_closed_to_open(self) -> None:
        """Test circuit breaker transitioning from closed to open."""
        config = CircuitBreakerConfiguration(
            name="test_circuit_closed_to_open",
            fail_max=2,
            reset_timeout=1,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        # Initially closed
        assert circuit_breaker.current_state == "closed"

        @circuit_breaker_protect(circuit_breaker)
        def failing_operation() -> NoReturn:
            raise OperationalError("Connection lost", {}, None)

        # First failure
        with pytest.raises(OperationalError):
            failing_operation()
        assert circuit_breaker.current_state == "closed"

        # Second failure should open the circuit
        with pytest.raises(OperationalError):
            failing_operation()
        assert circuit_breaker.current_state == "open"

    def test_circuit_breaker_open_to_half_open(self) -> None:
        """Test circuit breaker transitioning from open to half-open."""
        config = CircuitBreakerConfiguration(
            name="test_circuit_open_to_half_open",
            fail_max=1,
            reset_timeout=1,  # Short timeout for testing
        )
        circuit_breaker = create_database_circuit_breaker(config)

        # Trip the circuit
        @circuit_breaker_protect(circuit_breaker)
        def failing_operation() -> NoReturn:
            raise OperationalError("Connection lost", {}, None)

        with pytest.raises(OperationalError):
            failing_operation()

        assert circuit_breaker.current_state == "open"

        # Wait for reset timeout
        time.sleep(1.1)

        # Try to call the operation - should transition to half-open
        with pytest.raises(OperationalError):
            failing_operation()

        assert circuit_breaker.current_state == "half_open"

    def test_circuit_breaker_half_open_to_closed(self) -> None:
        """Test circuit breaker transitioning from half-open to closed."""
        config = CircuitBreakerConfiguration(
            name="test_circuit_half_open_to_closed",
            fail_max=1,
            reset_timeout=1,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        # Trip the circuit
        @circuit_breaker_protect(circuit_breaker)
        def failing_operation() -> NoReturn:
            raise OperationalError("Connection lost", {}, None)

        with pytest.raises(OperationalError):
            failing_operation()

        assert circuit_breaker.current_state == "open"

        # Wait for reset timeout
        time.sleep(1.1)

        # Define a successful operation
        @circuit_breaker_protect(circuit_breaker)
        def successful_operation() -> str:
            return "success"

        # First call should be in half-open state
        result = successful_operation()
        assert result == "success"
        assert circuit_breaker.current_state == "closed"

    def test_circuit_breaker_half_open_to_open(self) -> None:
        """Test circuit breaker transitioning from half-open back to open."""
        config = CircuitBreakerConfiguration(
            name="test_circuit_half_open_to_open",
            fail_max=1,
            reset_timeout=1,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        # Trip the circuit
        @circuit_breaker_protect(circuit_breaker)
        def failing_operation() -> NoReturn:
            raise OperationalError("Connection lost", {}, None)

        with pytest.raises(OperationalError):
            failing_operation()

        assert circuit_breaker.current_state == "open"

        # Wait for reset timeout
        time.sleep(1.1)

        # Try the failing operation again - should go back to open
        with pytest.raises(OperationalError):
            failing_operation()

        assert circuit_breaker.current_state == "open"


class TestCircuitBreakerExceptionHandling:
    """Test cases for circuit breaker exception handling."""

    def setup_method(self) -> None:
        """Set up test method by clearing circuit breaker manager."""
        circuit_breaker_manager._circuit_breakers.clear()
        # Reset the default circuit breaker
        global default_database_circuit_breaker
        default_database_circuit_breaker = None
        # Force recreation of circuit breakers by clearing the manager's internal state
        circuit_breaker_manager._circuit_breakers = {}

    def test_expected_exceptions_trip_circuit(self) -> None:
        """Test that expected exceptions trip the circuit."""
        config = CircuitBreakerConfiguration(
            name="test_circuit_expected_exceptions",
            fail_max=1,
            reset_timeout=1,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker)
        def operation_with_operational_error() -> NoReturn:
            raise OperationalError("Connection lost", {}, None)

        with pytest.raises(OperationalError):
            operation_with_operational_error()

        assert circuit_breaker.current_state == "open"

    def test_excluded_exceptions_dont_trip_circuit(self) -> None:
        """Test that excluded exceptions don't trip the circuit."""
        config = CircuitBreakerConfiguration(
            name="test_circuit",
            fail_max=1,
            reset_timeout=1,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker)
        def operation_with_integrity_error() -> NoReturn:
            raise IntegrityError("Unique constraint violation", {}, None)

        with pytest.raises(IntegrityError):
            operation_with_integrity_error()

        # Circuit should still be closed
        assert circuit_breaker.current_state == "closed"

    def test_circuit_breaker_with_custom_timeout_config(self) -> None:
        """Test circuit breaker with custom timeout configuration."""
        config = CircuitBreakerConfiguration(
            name="test_circuit",
            fail_max=1,
            reset_timeout=1,
            call_timeout=0.1,  # This will be ignored by pybreaker
        )
        circuit_breaker = create_database_circuit_breaker(config)

        # Should still work even with call_timeout parameter
        assert circuit_breaker is not None
        assert circuit_breaker.name == "test_circuit"


if __name__ == "__main__":
    pytest.main([__file__])
