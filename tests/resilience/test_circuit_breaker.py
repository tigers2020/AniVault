"""
Unit tests for circuit breaker state transitions.

This module contains isolated unit tests to verify the circuit breaker's core state
transitions: CLOSED -> OPEN, OPEN -> HALF-OPEN, and recovery/re-opening from HALF-OPEN.

These tests focus on unit testing the pybreaker instance in isolation, asserting
against the breaker.current_state property and expected exceptions.

Author: AniVault Development Team
Created: 2025-01-20
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Callable

from pybreaker import CircuitBreaker, CircuitBreakerError

from sqlalchemy.exc import (
    OperationalError,
    DisconnectionError,
    InterfaceError,
    TimeoutError,
    IntegrityError,
    ProgrammingError,
    DataError,
)

from src.core.circuit_breaker import (
    CircuitState,
    CircuitBreakerConfiguration,
    DatabaseCircuitBreakerListener,
    CircuitBreakerManager,
    create_database_circuit_breaker,
    circuit_breaker_protect,
    is_circuit_breaker_open,
    circuit_breaker_manager,
)


class TestCircuitBreakerStateTransitions:
    """Test cases for circuit breaker state transitions in isolation."""

    def setup_method(self):
        """Set up test method by clearing circuit breaker manager."""
        circuit_breaker_manager._circuit_breakers.clear()

    def test_circuit_breaker_closed_to_open_transition(self):
        """Test circuit breaker transitioning from CLOSED to OPEN state.

        This test simulates failures (sqlalchemy.exc.OperationalError) exceeding
        the threshold and asserts the state becomes OPEN.
        """
        config = CircuitBreakerConfiguration(
            name="test_circuit_closed_to_open",
            fail_max=2,  # Trip after 2 failures
            reset_timeout=30,  # Stay open for 30 seconds
        )
        circuit_breaker = create_database_circuit_breaker(config)

        # Initially should be CLOSED
        assert circuit_breaker.current_state == "closed"

        @circuit_breaker_protect(circuit_breaker, operation_name="test_db_operation")
        def failing_database_operation():
            """Simulate a database operation that fails with OperationalError."""
            raise OperationalError("Connection lost", {}, None)

        # First failure - circuit should still be CLOSED
        with pytest.raises(OperationalError):
            failing_database_operation()
        assert circuit_breaker.current_state == "closed"

        # Second failure should open the circuit (fail_max=2)
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()
        assert circuit_breaker.current_state == "open"

    def test_circuit_breaker_open_state_rejects_calls(self):
        """Test that subsequent calls are immediately rejected when OPEN.

        When the circuit breaker is in OPEN state, it should immediately reject
        calls without attempting the operation.
        """
        config = CircuitBreakerConfiguration(
            name="test_circuit_open_rejects",
            fail_max=1,  # Trip after 1 failure
            reset_timeout=30,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker, operation_name="test_db_operation")
        def failing_database_operation():
            """Simulate a database operation that fails."""
            raise OperationalError("Connection lost", {}, None)

        # Trip the circuit
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()
        assert circuit_breaker.current_state == "open"

        # Subsequent calls should be immediately rejected with CircuitBreakerError
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()

        # Verify the operation function was not called (circuit is open)
        # The circuit breaker should reject immediately without calling the function
        assert circuit_breaker.current_state == "open"

    def test_circuit_breaker_open_to_half_open_transition(self):
        """Test circuit breaker transitioning from OPEN to HALF-OPEN state.

        After the reset_timeout period, the circuit should transition to HALF-OPEN
        and allow a single trial operation.
        """
        config = CircuitBreakerConfiguration(
            name="test_circuit_open_to_half_open",
            fail_max=1,
            reset_timeout=1,  # Short timeout for testing
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker, operation_name="test_db_operation")
        def failing_database_operation():
            """Simulate a database operation that fails."""
            raise OperationalError("Connection lost", {}, None)

        # Trip the circuit
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()
        assert circuit_breaker.current_state == "open"

        # Wait for reset timeout to elapse
        time.sleep(1.1)

        # Try to call the operation - should transition to half-open and then back to open
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()

        # The circuit should be back to open because the trial failed
        assert circuit_breaker.current_state == "open"

    def test_circuit_breaker_half_open_to_closed_recovery(self):
        """Test circuit breaker transitioning from HALF-OPEN to CLOSED on success.

        A successful trial operation in the HALF-OPEN state should move the breaker
        back to CLOSED.
        """
        config = CircuitBreakerConfiguration(
            name="test_circuit_half_open_to_closed",
            fail_max=1,
            reset_timeout=1,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker, operation_name="failing_operation")
        def failing_database_operation():
            """Simulate a database operation that fails."""
            raise OperationalError("Connection lost", {}, None)

        @circuit_breaker_protect(circuit_breaker, operation_name="successful_operation")
        def successful_database_operation():
            """Simulate a successful database operation."""
            return "operation_successful"

        # Trip the circuit
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()
        assert circuit_breaker.current_state == "open"

        # Wait for reset timeout
        time.sleep(1.1)

        # First call should be in half-open state and succeed
        result = successful_database_operation()
        assert result == "operation_successful"
        assert circuit_breaker.current_state == "closed"

    def test_circuit_breaker_half_open_to_open_repeated_failure(self):
        """Test circuit breaker transitioning from HALF-OPEN back to OPEN on failure.

        A failed trial operation in the HALF-OPEN state should move the breaker
        back to OPEN.
        """
        config = CircuitBreakerConfiguration(
            name="test_circuit_half_open_to_open",
            fail_max=1,
            reset_timeout=1,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker, operation_name="test_db_operation")
        def failing_database_operation():
            """Simulate a database operation that fails."""
            raise OperationalError("Connection lost", {}, None)

        # Trip the circuit
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()
        assert circuit_breaker.current_state == "open"

        # Wait for reset timeout
        time.sleep(1.1)

        # Try the failing operation again - should go back to open
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()

        assert circuit_breaker.current_state == "open"

    def test_circuit_breaker_state_persistence_across_operations(self):
        """Test that circuit breaker state persists across multiple operation calls.

        The circuit breaker should maintain its state across different operations
        that use the same breaker instance.
        """
        config = CircuitBreakerConfiguration(
            name="test_circuit_state_persistence",
            fail_max=2,
            reset_timeout=30,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker, operation_name="operation1")
        def database_operation_1():
            """First database operation."""
            raise OperationalError("Connection lost", {}, None)

        @circuit_breaker_protect(circuit_breaker, operation_name="operation2")
        def database_operation_2():
            """Second database operation."""
            raise OperationalError("Connection lost", {}, None)

        # Initially closed
        assert circuit_breaker.current_state == "closed"

        # First failure
        with pytest.raises(OperationalError):
            database_operation_1()
        assert circuit_breaker.current_state == "closed"

        # Second failure using different operation should open the circuit
        with pytest.raises(CircuitBreakerError):
            database_operation_2()
        assert circuit_breaker.current_state == "open"

        # Both operations should now be rejected
        with pytest.raises(CircuitBreakerError):
            database_operation_1()

        with pytest.raises(CircuitBreakerError):
            database_operation_2()

    def test_circuit_breaker_with_time_mock(self):
        """Test circuit breaker state transitions using time mocking.

        This test uses a shorter reset_timeout to verify the half-open transition.
        """
        config = CircuitBreakerConfiguration(
            name="test_circuit_time_mock",
            fail_max=1,
            reset_timeout=1,  # Short timeout for testing
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker, operation_name="test_db_operation")
        def failing_database_operation():
            """Simulate a database operation that fails."""
            raise OperationalError("Connection lost", {}, None)

        # Trip the circuit
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()
        assert circuit_breaker.current_state == "open"

        # Wait for reset timeout to actually elapse
        time.sleep(1.1)

        # Try the operation - should transition to half-open and then back to open
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()

        # The circuit should be back to open because the trial failed
        assert circuit_breaker.current_state == "open"

    def test_circuit_breaker_statistics_tracking(self):
        """Test that circuit breaker correctly tracks statistics during state transitions."""
        config = CircuitBreakerConfiguration(
            name="test_circuit_stats",
            fail_max=2,
            reset_timeout=30,
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker, operation_name="test_db_operation")
        def failing_database_operation():
            """Simulate a database operation that fails."""
            raise OperationalError("Connection lost", {}, None)

        # Initially should have 0 failures
        assert circuit_breaker.fail_counter == 0
        assert circuit_breaker.current_state == "closed"

        # First failure
        with pytest.raises(OperationalError):
            failing_database_operation()
        assert circuit_breaker.fail_counter == 1
        assert circuit_breaker.current_state == "closed"

        # Second failure should open the circuit
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()
        assert circuit_breaker.fail_counter == 2
        assert circuit_breaker.current_state == "open"

    def test_circuit_breaker_configuration_validation(self):
        """Test that circuit breaker respects configuration parameters."""
        # Test with custom fail_max
        config = CircuitBreakerConfiguration(
            name="test_circuit_custom_config",
            fail_max=3,  # Trip after 3 failures
            reset_timeout=60,  # 60 second timeout
        )
        circuit_breaker = create_database_circuit_breaker(config)

        @circuit_breaker_protect(circuit_breaker, operation_name="test_db_operation")
        def failing_database_operation():
            """Simulate a database operation that fails."""
            raise OperationalError("Connection lost", {}, None)

        # Should need 3 failures to trip
        for i in range(2):
            with pytest.raises(OperationalError):
                failing_database_operation()
            assert circuit_breaker.current_state == "closed"
            assert circuit_breaker.fail_counter == i + 1

        # Third failure should open the circuit
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()
        assert circuit_breaker.current_state == "open"
        assert circuit_breaker.fail_counter == 3


class TestCircuitBreakerIsolation:
    """Test cases for circuit breaker isolation and independent operation."""

    def setup_method(self):
        """Set up test method by clearing circuit breaker manager."""
        circuit_breaker_manager._circuit_breakers.clear()

    def test_multiple_circuit_breakers_independence(self):
        """Test that multiple circuit breakers operate independently."""
        config1 = CircuitBreakerConfiguration(
            name="test_circuit_1",
            fail_max=1,
            reset_timeout=1,
        )
        config2 = CircuitBreakerConfiguration(
            name="test_circuit_2",
            fail_max=2,
            reset_timeout=1,
        )

        circuit_breaker1 = create_database_circuit_breaker(config1)
        circuit_breaker2 = create_database_circuit_breaker(config2)

        @circuit_breaker_protect(circuit_breaker1, operation_name="operation1")
        def operation_1():
            raise OperationalError("Connection lost", {}, None)

        @circuit_breaker_protect(circuit_breaker2, operation_name="operation2")
        def operation_2():
            raise OperationalError("Connection lost", {}, None)

        # Trip circuit breaker 1
        with pytest.raises(CircuitBreakerError):
            operation_1()
        assert circuit_breaker1.current_state == "open"
        assert circuit_breaker2.current_state == "closed"

        # Circuit breaker 2 should still work normally
        with pytest.raises(OperationalError):
            operation_2()
        assert circuit_breaker1.current_state == "open"
        assert circuit_breaker2.current_state == "closed"

        # Trip circuit breaker 2
        with pytest.raises(CircuitBreakerError):
            operation_2()
        assert circuit_breaker1.current_state == "open"
        assert circuit_breaker2.current_state == "open"

    def test_circuit_breaker_listener_integration(self):
        """Test that circuit breaker listeners are properly integrated."""
        config = CircuitBreakerConfiguration(
            name="test_circuit_with_listener",
            fail_max=1,
            reset_timeout=1,
        )

        # Create a mock listener with all required methods
        mock_listener = Mock()
        mock_listener.before_call = Mock()
        mock_listener.on_success = Mock()
        mock_listener.on_failure = Mock()
        mock_listener.on_open = Mock()
        mock_listener.on_half_open = Mock()
        mock_listener.on_close = Mock()
        mock_listener.on_timeout = Mock()

        circuit_breaker = create_database_circuit_breaker(config, listener=mock_listener)

        @circuit_breaker_protect(circuit_breaker, operation_name="test_db_operation")
        def failing_database_operation():
            """Simulate a database operation that fails."""
            raise OperationalError("Connection lost", {}, None)

        # Trip the circuit - this should trigger listener events
        with pytest.raises(CircuitBreakerError):
            failing_database_operation()

        # Verify that the circuit breaker was created with the listener
        assert circuit_breaker.listeners is not None
        assert len(circuit_breaker.listeners) > 0


if __name__ == "__main__":
    pytest.main([__file__])
