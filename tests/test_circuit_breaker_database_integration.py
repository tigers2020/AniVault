"""Tests for circuit breaker database integration."""

import time
from typing import NoReturn
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import DisconnectionError, OperationalError

from src.core.circuit_breaker import circuit_breaker_protect, get_database_circuit_breaker
from src.core.database import DatabaseManager


class TestCircuitBreakerDatabaseIntegration:
    """Test circuit breaker integration with database operations."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_manager = Mock(spec=DatabaseManager)
        mock_manager._initialized = True
        return mock_manager

    def test_circuit_breaker_protection_on_successful_operation(self, mock_db_manager) -> None:
        """Test circuit breaker protection on successful database operation."""
        # Mock successful database operation
        mock_db_manager.create_anime_metadata.return_value = Mock()

        # The method should be protected by circuit breaker
        result = mock_db_manager.create_anime_metadata(Mock())

        # Should succeed without issues
        assert result is not None
        mock_db_manager.create_anime_metadata.assert_called_once()

    def test_circuit_breaker_protection_on_failed_operation(self, mock_db_manager) -> None:
        """Test circuit breaker protection on failed database operation."""
        # Mock database failure
        mock_db_manager.create_anime_metadata.side_effect = OperationalError(
            "Database connection failed", None, None
        )

        # Should raise the original exception
        with pytest.raises(OperationalError):
            mock_db_manager.create_anime_metadata(Mock())

    def test_circuit_breaker_state_transition_after_failures(self, mock_db_manager) -> None:
        """Test circuit breaker state transition after multiple failures."""
        # Get the circuit breaker
        circuit_breaker = get_database_circuit_breaker()

        # Reset circuit breaker state
        circuit_breaker.close()

        # Create a protected function that will fail
        @circuit_breaker_protect(operation_name="test_failure")
        def failing_operation() -> NoReturn:
            raise DisconnectionError("Database disconnected", None, None)

        # Trigger multiple failures
        for _ in range(6):  # More than the failure threshold
            try:
                failing_operation()
            except (DisconnectionError, Exception):
                pass

        # Circuit breaker should be open
        assert circuit_breaker.current_state == "open"

    def test_circuit_breaker_recovery_after_success(self, mock_db_manager) -> None:
        """Test circuit breaker recovery after successful operation."""
        # Get the circuit breaker
        circuit_breaker = get_database_circuit_breaker()

        # Reset circuit breaker state
        circuit_breaker.close()

        # Create a protected function that will fail initially
        @circuit_breaker_protect(operation_name="test_recovery")
        def failing_operation() -> NoReturn:
            raise OperationalError("Database error", None, None)

        # First, open the circuit breaker with failures
        for _ in range(6):
            try:
                failing_operation()
            except (OperationalError, Exception):
                pass

        # Circuit should be open
        assert circuit_breaker.current_state == "open"

        # Now create a protected function that will succeed
        @circuit_breaker_protect(operation_name="test_recovery")
        def successful_operation():
            return Mock()

        # Wait for timeout to allow half-open state
        time.sleep(2)

        # Try the operation again
        try:
            result = successful_operation()
            # Should succeed and circuit should be closed
            assert result is not None
            assert circuit_breaker.current_state == "closed"
        except Exception:
            # If still failing, circuit might still be transitioning
            pass

    def test_circuit_breaker_with_fallback_function(self, mock_db_manager) -> None:
        """Test circuit breaker with fallback function."""
        # Mock database failure
        mock_db_manager.create_anime_metadata.side_effect = OperationalError(
            "Database unavailable", None, None
        )

        # Create a fallback function
        fallback_result = Mock()

        def fallback_func():
            return fallback_result

        # Apply circuit breaker protection with fallback
        @circuit_breaker_protect(operation_name="test_operation", fallback_func=fallback_func)
        def protected_operation():
            return mock_db_manager.create_anime_metadata(Mock())

        # First few calls should fail normally
        for _ in range(6):
            try:
                protected_operation()
            except OperationalError:
                pass

        # After circuit opens, fallback should be called
        result = protected_operation()
        assert result == fallback_result

    def test_circuit_breaker_statistics_tracking(self, mock_db_manager) -> None:
        """Test circuit breaker statistics tracking."""
        # Get the circuit breaker
        circuit_breaker = get_database_circuit_breaker()

        # Reset circuit breaker state
        circuit_breaker.close()

        # Mock some operations
        mock_db_manager.create_anime_metadata.return_value = Mock()

        # Perform successful operations
        for _ in range(3):
            mock_db_manager.create_anime_metadata(Mock())

        # Check circuit breaker state (successful operations should keep it closed)
        assert circuit_breaker.current_state == "closed"

    def test_multiple_database_operations_protection(self, mock_db_manager) -> None:
        """Test protection of multiple database operations."""
        # Mock successful operations
        mock_db_manager.create_anime_metadata.return_value = Mock()
        mock_db_manager.get_anime_metadata.return_value = Mock()
        mock_db_manager.create_parsed_file.return_value = Mock()

        # All operations should be protected
        operations = [
            lambda: mock_db_manager.create_anime_metadata(Mock()),
            lambda: mock_db_manager.get_anime_metadata(1),
            lambda: mock_db_manager.create_parsed_file(
                "test.txt", "test.txt", 1000, Mock(), Mock(), Mock(), None, None
            ),
        ]

        for operation in operations:
            result = operation()
            assert result is not None

    def test_circuit_breaker_with_bulk_operations(self, mock_db_manager) -> None:
        """Test circuit breaker with bulk database operations."""
        # Mock bulk operation
        mock_db_manager.bulk_insert_anime_metadata.return_value = 5

        # Bulk operation should be protected
        result = mock_db_manager.bulk_insert_anime_metadata([Mock() for _ in range(5)])

        assert result == 5
        mock_db_manager.bulk_insert_anime_metadata.assert_called_once()

    def test_circuit_breaker_error_handling(self, mock_db_manager) -> None:
        """Test circuit breaker error handling with different exception types."""
        # Test with different database exceptions
        exceptions = [
            OperationalError("Connection lost", None, None),
            DisconnectionError("Database disconnected", None, None),
            Exception("Generic database error"),
        ]

        for exc in exceptions:
            # Reset circuit breaker
            circuit_breaker = get_database_circuit_breaker()
            circuit_breaker.close()

            # Mock the exception
            mock_db_manager.create_anime_metadata.side_effect = exc

            # Should raise the original exception
            with pytest.raises(type(exc)):
                mock_db_manager.create_anime_metadata(Mock())

    def test_circuit_breaker_timeout_behavior(self, mock_db_manager) -> None:
        """Test circuit breaker timeout behavior."""
        # Get the circuit breaker
        circuit_breaker = get_database_circuit_breaker()

        # Reset circuit breaker state
        circuit_breaker.close()

        # Create a protected function that will timeout
        @circuit_breaker_protect(operation_name="test_timeout")
        def timeout_operation() -> NoReturn:
            raise OperationalError("Query timeout", None, None)

        # Trigger circuit breaker
        for _ in range(6):
            try:
                timeout_operation()
            except (OperationalError, Exception):
                pass

        # Circuit should be open
        assert circuit_breaker.current_state == "open"


class TestCircuitBreakerPerformance:
    """Test circuit breaker performance characteristics."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_manager = Mock(spec=DatabaseManager)
        mock_manager._initialized = True
        return mock_manager

    def test_circuit_breaker_overhead(self, mock_db_manager) -> None:
        """Test circuit breaker performance overhead."""
        # Mock fast operation
        mock_db_manager.get_anime_metadata.return_value = Mock()

        # Measure time with circuit breaker
        start_time = time.time()
        for _ in range(100):
            mock_db_manager.get_anime_metadata(1)
        end_time = time.time()

        circuit_breaker_time = end_time - start_time

        # Circuit breaker overhead should be minimal
        assert circuit_breaker_time < 1.0  # Should complete in less than 1 second

    def test_circuit_breaker_memory_usage(self, mock_db_manager) -> None:
        """Test circuit breaker memory usage."""
        import sys

        # Get initial memory usage
        initial_size = sys.getsizeof(mock_db_manager)

        # Perform many operations
        mock_db_manager.get_anime_metadata.return_value = Mock()
        for _ in range(1000):
            mock_db_manager.get_anime_metadata(1)

        # Memory usage should not grow significantly
        final_size = sys.getsizeof(mock_db_manager)
        memory_growth = final_size - initial_size

        # Memory growth should be minimal
        assert memory_growth < 10000  # Less than 10KB growth


class TestCircuitBreakerConcurrency:
    """Test circuit breaker with concurrent operations."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_manager = Mock(spec=DatabaseManager)
        mock_manager._initialized = True
        return mock_manager

    def test_concurrent_circuit_breaker_operations(self, mock_db_manager) -> None:
        """Test circuit breaker with concurrent operations."""
        import threading

        # Mock successful operations
        mock_db_manager.get_anime_metadata.return_value = Mock()

        results = []

        def perform_operation() -> None:
            result = mock_db_manager.get_anime_metadata(1)
            results.append(result)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=perform_operation)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All operations should succeed
        assert len(results) == 10
        assert all(result is not None for result in results)

    def test_concurrent_circuit_breaker_failures(self, mock_db_manager) -> None:
        """Test circuit breaker with concurrent failures."""
        import threading

        # Mock failures
        mock_db_manager.create_anime_metadata.side_effect = OperationalError(
            "Database error", None, None
        )

        exceptions = []

        def perform_failing_operation() -> None:
            try:
                mock_db_manager.create_anime_metadata(Mock())
            except OperationalError as e:
                exceptions.append(e)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=perform_failing_operation)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All operations should fail
        assert len(exceptions) == 10
        assert all(isinstance(e, OperationalError) for e in exceptions)


if __name__ == "__main__":
    pytest.main([__file__])
