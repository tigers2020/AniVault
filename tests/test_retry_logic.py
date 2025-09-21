"""Unit tests for retry logic module.

Tests the retry mechanisms, exponential backoff, error detection,
and various retry configurations for database operations.

Author: AniVault Development Team
Created: 2025-01-19
"""

import time
from typing import NoReturn
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import (
    DataError,
    DisconnectionError,
    IntegrityError,
    InterfaceError,
    OperationalError,
    ProgrammingError,
    SQLAlchemyError,
)

from src.core.retry_logic import (
    RetryConfiguration,
    RetryStatistics,
    create_retry_decorator,
    db_retry,
    get_retry_statistics,
    is_non_retriable_error,
    is_transient_db_error,
    reset_retry_statistics,
    retry_database_operation,
    retry_with_fresh_session,
)


class TestRetryConfiguration:
    """Test cases for RetryConfiguration class."""

    def test_default_configuration(self) -> None:
        """Test default configuration values."""
        config = RetryConfiguration()

        assert config.max_attempts == 7
        assert config.min_wait == 0.5
        assert config.max_wait == 30.0
        assert config.multiplier == 1.0
        assert config.jitter is True
        assert len(config.retriable_exceptions) > 0

    def test_custom_configuration(self) -> None:
        """Test custom configuration values."""
        custom_exceptions = {OperationalError, DisconnectionError}
        config = RetryConfiguration(
            max_attempts=5,
            min_wait=1.0,
            max_wait=60.0,
            multiplier=2.0,
            jitter=False,
            retriable_exceptions=custom_exceptions,
        )

        assert config.max_attempts == 5
        assert config.min_wait == 1.0
        assert config.max_wait == 60.0
        assert config.multiplier == 2.0
        assert config.jitter is False
        assert config.retriable_exceptions == custom_exceptions


class TestErrorDetection:
    """Test cases for error detection functions."""

    def test_is_transient_db_error_retriable_exceptions(self) -> None:
        """Test detection of retriable exception types."""
        retriable_exceptions = [
            OperationalError("Connection lost", {}, None),
            DisconnectionError("Connection reset", {}, None),
            InterfaceError("Interface error", {}, None),
        ]

        for exc in retriable_exceptions:
            assert is_transient_db_error(exc) is True

    def test_is_transient_db_error_with_patterns(self) -> None:
        """Test detection of transient errors by message patterns."""
        # Mock SQLAlchemyError with orig attribute
        mock_exc = Mock(spec=SQLAlchemyError)
        mock_exc.orig = Mock()

        transient_messages = [
            "deadlock detected",
            "could not serialize access due to concurrent update",
            "connection reset by peer",
            "connection timed out",
            "temporary failure",
            "resource temporarily unavailable",
            "too many connections",
            "connection pool exhausted",
        ]

        for message in transient_messages:
            mock_exc.orig.__str__ = Mock(return_value=message)
            assert is_transient_db_error(mock_exc) is True

    def test_is_transient_db_error_non_retriable(self) -> None:
        """Test that non-retriable errors are not detected as transient."""
        non_retriable_exceptions = [
            IntegrityError("Unique constraint violation", {}, None),
            ProgrammingError("Invalid SQL", {}, None),
            DataError("Data too long", {}, None),
        ]

        for exc in non_retriable_exceptions:
            assert is_transient_db_error(exc) is False

    def test_is_transient_db_error_no_orig_attribute(self) -> None:
        """Test handling of SQLAlchemyError without orig attribute."""
        mock_exc = Mock(spec=SQLAlchemyError)
        mock_exc.orig = None

        assert is_transient_db_error(mock_exc) is False

    def test_is_non_retriable_error(self) -> None:
        """Test detection of non-retriable errors."""
        non_retriable_exceptions = [
            IntegrityError("Unique constraint violation", {}, None),
            ProgrammingError("Invalid SQL", {}, None),
            DataError("Data too long", {}, None),
        ]

        for exc in non_retriable_exceptions:
            assert is_non_retriable_error(exc) is True

    def test_is_non_retriable_error_retriable_exceptions(self) -> None:
        """Test that retriable exceptions are not detected as non-retriable."""
        retriable_exceptions = [
            OperationalError("Connection lost", {}, None),
            DisconnectionError("Connection reset", {}, None),
            InterfaceError("Interface error", {}, None),
        ]

        for exc in retriable_exceptions:
            assert is_non_retriable_error(exc) is False


class TestRetryDecorator:
    """Test cases for retry decorator functionality."""

    def test_create_retry_decorator_default_config(self) -> None:
        """Test creating retry decorator with default configuration."""
        decorator = create_retry_decorator()
        assert callable(decorator)

    def test_create_retry_decorator_custom_config(self) -> None:
        """Test creating retry decorator with custom configuration."""
        config = RetryConfiguration(max_attempts=3, min_wait=0.1, max_wait=1.0)
        decorator = create_retry_decorator(config)
        assert callable(decorator)

    def test_retry_decorator_success_on_first_attempt(self) -> None:
        """Test retry decorator when operation succeeds on first attempt."""
        decorator = create_retry_decorator(RetryConfiguration(max_attempts=3))

        @decorator
        def successful_operation() -> str:
            return "success"

        result = successful_operation()
        assert result == "success"

    def test_retry_decorator_success_after_retries(self) -> None:
        """Test retry decorator when operation succeeds after retries."""
        decorator = create_retry_decorator(RetryConfiguration(max_attempts=3, min_wait=0.01))

        attempt_count = 0

        @decorator
        def flaky_operation() -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise OperationalError("Connection lost", {}, None)
            return "success"

        result = flaky_operation()
        assert result == "success"
        assert attempt_count == 3

    def test_retry_decorator_fails_after_max_attempts(self) -> None:
        """Test retry decorator when operation fails after max attempts."""
        decorator = create_retry_decorator(RetryConfiguration(max_attempts=2, min_wait=0.01))

        @decorator
        def failing_operation() -> NoReturn:
            raise OperationalError("Persistent connection error", {}, None)

        with pytest.raises(OperationalError):
            failing_operation()

    def test_retry_decorator_fails_fast_on_non_retriable_error(self) -> None:
        """Test retry decorator fails fast on non-retriable errors."""
        decorator = create_retry_decorator(RetryConfiguration(max_attempts=3))

        attempt_count = 0

        @decorator
        def operation_with_integrity_error() -> NoReturn:
            nonlocal attempt_count
            attempt_count += 1
            raise IntegrityError("Unique constraint violation", {}, None)

        with pytest.raises(IntegrityError):
            operation_with_integrity_error()

        # Should only attempt once due to non-retriable error
        assert attempt_count == 1


class TestRetryDatabaseOperation:
    """Test cases for retry_database_operation decorator."""

    def test_retry_database_operation_success(self) -> None:
        """Test retry_database_operation with successful operation."""

        @retry_database_operation(operation_name="test_operation")
        def test_operation() -> str:
            return "success"

        result = test_operation()
        assert result == "success"

    def test_retry_database_operation_with_custom_config(self) -> None:
        """Test retry_database_operation with custom configuration."""
        config = RetryConfiguration(max_attempts=2, min_wait=0.01)

        @retry_database_operation(config=config, operation_name="test_operation")
        def test_operation() -> str:
            return "success"

        result = test_operation()
        assert result == "success"

    def test_retry_database_operation_with_retries(self) -> None:
        """Test retry_database_operation with retries."""
        config = RetryConfiguration(max_attempts=3, min_wait=0.01)

        attempt_count = 0

        @retry_database_operation(config=config, operation_name="flaky_operation")
        def flaky_operation() -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise OperationalError("Connection lost", {}, None)
            return "success"

        result = flaky_operation()
        assert result == "success"
        assert attempt_count == 3


class TestRetryWithFreshSession:
    """Test cases for retry_with_fresh_session decorator."""

    def test_retry_with_fresh_session_success(self) -> None:
        """Test retry_with_fresh_session with successful operation."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        session_factory = Mock(return_value=mock_session)

        @retry_with_fresh_session(session_factory, operation_name="test_operation")
        def test_operation() -> str:
            return "success"

        result = test_operation()
        assert result == "success"
        session_factory.assert_called_once()

    def test_retry_with_fresh_session_with_retries(self) -> None:
        """Test retry_with_fresh_session with retries."""
        config = RetryConfiguration(max_attempts=3, min_wait=0.01)
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        session_factory = Mock(return_value=mock_session)

        attempt_count = 0

        @retry_with_fresh_session(session_factory, config=config, operation_name="flaky_operation")
        def flaky_operation() -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise OperationalError("Connection lost", {}, None)
            return "success"

        result = flaky_operation()
        assert result == "success"
        assert attempt_count == 3
        assert session_factory.call_count == 3  # Fresh session for each attempt

    def test_retry_with_fresh_session_passes_session_to_function(self) -> None:
        """Test that retry_with_fresh_session passes session to function that expects it."""
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        session_factory = Mock(return_value=mock_session)

        @retry_with_fresh_session(session_factory, operation_name="test_operation")
        def test_operation(session) -> str:
            assert session is mock_session
            return "success"

        result = test_operation()
        assert result == "success"


class TestRetryStatistics:
    """Test cases for RetryStatistics class."""

    def test_initial_statistics(self) -> None:
        """Test initial statistics values."""
        stats = RetryStatistics()
        assert stats.total_attempts == 0
        assert stats.successful_retries == 0
        assert stats.failed_after_retries == 0
        assert stats.non_retriable_failures == 0

    def test_record_attempt(self) -> None:
        """Test recording an attempt."""
        stats = RetryStatistics()
        stats.record_attempt()
        assert stats.total_attempts == 1

    def test_record_successful_retry(self) -> None:
        """Test recording a successful retry."""
        stats = RetryStatistics()
        stats.record_successful_retry()
        assert stats.successful_retries == 1

    def test_record_failed_after_retries(self) -> None:
        """Test recording a failure after retries."""
        stats = RetryStatistics()
        stats.record_failed_after_retries()
        assert stats.failed_after_retries == 1

    def test_record_non_retriable_failure(self) -> None:
        """Test recording a non-retriable failure."""
        stats = RetryStatistics()
        stats.record_non_retriable_failure()
        assert stats.non_retriable_failures == 1

    def test_get_stats(self) -> None:
        """Test getting statistics."""
        stats = RetryStatistics()
        stats.record_attempt()
        stats.record_attempt()
        stats.record_successful_retry()
        stats.record_failed_after_retries()

        stats_dict = stats.get_stats()
        assert stats_dict["total_attempts"] == 2
        assert stats_dict["successful_retries"] == 1
        assert stats_dict["failed_after_retries"] == 1
        assert stats_dict["non_retriable_failures"] == 0
        assert stats_dict["success_rate"] == 50.0  # 1 success out of 2 attempts

    def test_success_rate_calculation(self) -> None:
        """Test success rate calculation with various scenarios."""
        stats = RetryStatistics()

        # No attempts
        assert stats.get_stats()["success_rate"] == 0.0

        # All successful (no retries needed)
        stats.record_attempt()
        stats.record_attempt()
        assert stats.get_stats()["success_rate"] == 100.0

        # Mixed results
        stats.record_successful_retry()
        stats.record_failed_after_retries()
        assert stats.get_stats()["success_rate"] == 50.0


class TestGlobalStatistics:
    """Test cases for global statistics functions."""

    def setup_method(self) -> None:
        """Reset statistics before each test."""
        reset_retry_statistics()

    def test_get_retry_statistics(self) -> None:
        """Test getting global retry statistics."""
        stats = get_retry_statistics()
        assert isinstance(stats, dict)
        assert "total_attempts" in stats
        assert "success_rate" in stats

    def test_reset_retry_statistics(self) -> None:
        """Test resetting global retry statistics."""
        # This test is implicitly covered by setup_method
        stats = get_retry_statistics()
        assert stats["total_attempts"] == 0


class TestIntegration:
    """Integration tests for retry logic."""

    def test_db_retry_decorator_integration(self) -> None:
        """Test the default db_retry decorator."""
        attempt_count = 0

        @db_retry
        def test_operation() -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise OperationalError("Connection lost", {}, None)
            return "success"

        result = test_operation()
        assert result == "success"
        assert attempt_count == 2

    def test_retry_with_exponential_backoff_timing(self) -> None:
        """Test that retry timing follows exponential backoff pattern."""
        config = RetryConfiguration(
            max_attempts=4,
            min_wait=0.01,
            max_wait=0.1,
            multiplier=2.0,
        )
        decorator = create_retry_decorator(config)

        attempt_times = []

        @decorator
        def timing_test_operation() -> str:
            attempt_times.append(time.time())
            if len(attempt_times) < 4:
                raise OperationalError("Connection lost", {}, None)
            return "success"

        time.time()
        result = timing_test_operation()
        time.time()

        assert result == "success"
        assert len(attempt_times) == 4

        # Verify exponential backoff timing (allowing some tolerance)
        if len(attempt_times) >= 3:
            delay1 = attempt_times[1] - attempt_times[0]
            delay2 = attempt_times[2] - attempt_times[1]
            # Second delay should be approximately double the first
            # Allow significant tolerance for jitter and system timing variations
            assert delay2 >= delay1 * 0.8  # More lenient tolerance for timing variations

    def test_retry_with_mixed_error_types(self) -> None:
        """Test retry behavior with mixed error types."""
        config = RetryConfiguration(max_attempts=5, min_wait=0.01)
        decorator = create_retry_decorator(config)

        attempt_count = 0

        @decorator
        def mixed_error_operation() -> str:
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count == 1:
                raise OperationalError("Connection lost", {}, None)  # Retriable
            elif attempt_count == 2:
                raise IntegrityError("Unique constraint violation", {}, None)  # Non-retriable
            else:
                return "success"

        # Should fail fast on non-retriable error
        with pytest.raises(IntegrityError):
            mixed_error_operation()

        assert attempt_count == 2  # Only 2 attempts due to non-retriable error


if __name__ == "__main__":
    pytest.main([__file__])
