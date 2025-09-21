"""Tests for database health monitoring system."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.core.database import DatabaseManager
from src.core.database_health import (
    DatabaseHealthChecker,
    HealthStatus,
    create_database_health_checker,
    get_database_health_checker,
    set_global_health_checker,
    get_database_health_status,
    is_database_healthy,
)


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_status_values(self):
        """Test HealthStatus enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestDatabaseHealthChecker:
    """Test DatabaseHealthChecker class."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_manager = Mock(spec=DatabaseManager)
        mock_manager._initialized = True
        return mock_manager

    @pytest.fixture
    def health_checker(self, mock_db_manager):
        """Create a DatabaseHealthChecker instance."""
        return DatabaseHealthChecker(
            db_manager=mock_db_manager,
            check_interval=1.0,  # Fast interval for testing
            timeout=0.5,
            failure_threshold=2,
            recovery_threshold=1,
        )

    def test_initialization(self, health_checker):
        """Test health checker initialization."""
        assert health_checker.check_interval == 1.0
        assert health_checker.timeout == 0.5
        assert health_checker.failure_threshold == 2
        assert health_checker.recovery_threshold == 1
        assert health_checker.get_current_status() == HealthStatus.UNKNOWN

    def test_successful_health_check(self, health_checker, mock_db_manager):
        """Test successful health check."""
        # Mock successful database query
        mock_session = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result

        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context

        status = health_checker.check_health()

        assert status == HealthStatus.HEALTHY
        assert health_checker.get_current_status() == HealthStatus.HEALTHY
        assert health_checker.get_last_success_time() is not None

    def test_failed_health_check(self, health_checker, mock_db_manager):
        """Test failed health check."""
        # Mock database failure
        mock_db_manager.get_session.side_effect = Exception("Database connection failed")

        status = health_checker.check_health()

        assert status == HealthStatus.UNHEALTHY
        assert health_checker.get_current_status() == HealthStatus.UNHEALTHY
        assert health_checker.get_last_failure_time() is not None

    def test_failure_threshold(self, health_checker, mock_db_manager):
        """Test failure threshold behavior."""
        # Mock consecutive failures
        mock_db_manager.get_session.side_effect = Exception("Database connection failed")

        # First failure - should still be UNKNOWN
        health_checker.check_health()
        assert health_checker.get_current_status() == HealthStatus.UNHEALTHY

        # Second failure - should trigger threshold
        health_checker.check_health()
        assert health_checker.get_current_status() == HealthStatus.UNHEALTHY

    def test_recovery_threshold(self, health_checker, mock_db_manager):
        """Test recovery threshold behavior."""
        # First, make system unhealthy
        mock_db_manager.get_session.side_effect = Exception("Database connection failed")
        health_checker.check_health()
        health_checker.check_health()
        assert health_checker.get_current_status() == HealthStatus.UNHEALTHY

        # Then simulate recovery
        mock_session = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result

        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.side_effect = None
        mock_db_manager.get_session.return_value = mock_context

        # First success after failure
        health_checker.check_health()
        assert health_checker.get_current_status() == HealthStatus.HEALTHY

    def test_monitoring_lifecycle(self, health_checker):
        """Test monitoring start/stop lifecycle."""
        # Start monitoring
        health_checker.start_monitoring()
        assert health_checker._monitoring is True
        assert health_checker._monitor_thread is not None

        # Wait a bit for thread to start
        time.sleep(0.1)

        # Stop monitoring
        health_checker.stop_monitoring()
        assert health_checker._monitoring is False

    def test_status_change_callbacks(self, health_checker, mock_db_manager):
        """Test status change callbacks."""
        callback_calls = []

        def callback(old_status, new_status):
            callback_calls.append((old_status, new_status))

        health_checker.add_status_change_callback(callback)

        # Mock successful check to trigger status change
        mock_session = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result

        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context

        health_checker.check_health()

        assert len(callback_calls) == 1
        assert callback_calls[0] == (HealthStatus.UNKNOWN, HealthStatus.HEALTHY)

    def test_statistics(self, health_checker, mock_db_manager):
        """Test health check statistics."""
        # Mock alternating success/failure
        call_count = [0]  # Use list to make it mutable in nested function

        def mock_session_side_effect(*args, **kwargs):
            call_count[0] += 1

            if call_count[0] % 2 == 0:
                # Success - return a context manager
                mock_session = Mock()
                mock_result = Mock()
                mock_result.fetchone.return_value = (1,)
                mock_session.execute.return_value = mock_result

                mock_context = Mock()
                mock_context.__enter__ = Mock(return_value=mock_session)
                mock_context.__exit__ = Mock(return_value=None)
                return mock_context
            else:
                # Failure
                raise Exception("Database connection failed")

        mock_db_manager.get_session.side_effect = mock_session_side_effect

        # Perform multiple checks
        for _ in range(4):
            health_checker.check_health()

        stats = health_checker.get_statistics()

        assert stats['total_checks'] == 4
        assert stats['successful_checks'] == 2
        assert stats['failed_checks'] == 2
        assert stats['success_rate'] == 0.5

    def test_custom_health_check_query(self, mock_db_manager):
        """Test custom health check query."""
        health_checker = DatabaseHealthChecker(
            db_manager=mock_db_manager,
            health_check_query="SELECT COUNT(*) FROM test_table"
        )

        mock_session = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (10,)
        mock_session.execute.return_value = mock_result

        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context

        health_checker.check_health()

        # Verify the custom query was used
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args[0]
        assert "SELECT COUNT(*) FROM test_table" in str(call_args[0])


class TestGlobalFunctions:
    """Test global utility functions."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_manager = Mock(spec=DatabaseManager)
        mock_manager._initialized = True
        return mock_manager

    def test_create_database_health_checker(self, mock_db_manager):
        """Test create_database_health_checker function."""
        checker = create_database_health_checker(
            db_manager=mock_db_manager,
            check_interval=30.0,
            timeout=5.0,
            failure_threshold=3,
            recovery_threshold=2
        )

        assert isinstance(checker, DatabaseHealthChecker)
        assert checker.check_interval == 30.0
        assert checker.timeout == 5.0
        assert checker.failure_threshold == 3
        assert checker.recovery_threshold == 2

    def test_global_health_checker_management(self, mock_db_manager):
        """Test global health checker management."""
        # Initially no global checker
        assert get_database_health_checker() is None

        # Create and set global checker
        checker = create_database_health_checker(mock_db_manager)
        set_global_health_checker(checker)

        # Verify global checker is set
        assert get_database_health_checker() is checker

        # Test global status functions
        with patch.object(checker, 'get_current_status', return_value=HealthStatus.HEALTHY):
            assert get_database_health_status() == HealthStatus.HEALTHY
            assert is_database_healthy() is True

        with patch.object(checker, 'get_current_status', return_value=HealthStatus.UNHEALTHY):
            assert get_database_health_status() == HealthStatus.UNHEALTHY
            assert is_database_healthy() is False

    def test_global_functions_without_checker(self):
        """Test global functions when no checker is set."""
        # Ensure no global checker
        set_global_health_checker(None)

        assert get_database_health_status() == HealthStatus.UNKNOWN
        assert is_database_healthy() is False  # Unknown status is treated as unhealthy


class TestHealthCheckerIntegration:
    """Integration tests for health checker."""

    @pytest.fixture
    def real_db_manager(self):
        """Create a real database manager for integration tests."""
        from src.core.database import DatabaseManager
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        return db_manager

    def test_real_database_health_check(self, real_db_manager):
        """Test health check with real database."""
        checker = DatabaseHealthChecker(
            db_manager=real_db_manager,
            check_interval=1.0,
            timeout=5.0,
            failure_threshold=1,
            recovery_threshold=1
        )

        # Should succeed with real database
        status = checker.check_health()
        assert status == HealthStatus.HEALTHY

        # Statistics should be updated
        stats = checker.get_statistics()
        assert stats['total_checks'] == 1
        assert stats['successful_checks'] == 1
        assert stats['failed_checks'] == 0
        assert stats['success_rate'] == 1.0

    def test_monitoring_with_real_database(self, real_db_manager):
        """Test monitoring with real database."""
        checker = DatabaseHealthChecker(
            db_manager=real_db_manager,
            check_interval=0.5,  # Very fast for testing
            timeout=2.0,
            failure_threshold=1,
            recovery_threshold=1
        )

        # Start monitoring
        checker.start_monitoring()

        # Wait for at least one check
        time.sleep(1.0)

        # Stop monitoring
        checker.stop_monitoring()

        # Verify checks were performed
        stats = checker.get_statistics()
        assert stats['total_checks'] >= 1
        assert stats['is_monitoring'] is False


class TestHealthCheckerThreadSafety:
    """Test thread safety of health checker."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_manager = Mock(spec=DatabaseManager)
        mock_manager._initialized = True
        return mock_manager

    def test_concurrent_health_checks(self, mock_db_manager):
        """Test concurrent health check calls."""
        checker = DatabaseHealthChecker(
            db_manager=mock_db_manager,
            check_interval=1.0,
            timeout=0.5,
            failure_threshold=1,
            recovery_threshold=1
        )

        # Mock successful responses
        mock_session = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = (1,)
        mock_session.execute.return_value = mock_result

        # Create a proper context manager mock
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_session)
        mock_context.__exit__ = Mock(return_value=None)
        mock_db_manager.get_session.return_value = mock_context

        import threading
        import time

        results = []

        def perform_check():
            status = checker.check_health()
            results.append(status)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=perform_check)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All results should be successful
        assert len(results) == 5
        assert all(status == HealthStatus.HEALTHY for status in results)

        # Statistics should be consistent
        stats = checker.get_statistics()
        assert stats['total_checks'] == 5
        assert stats['successful_checks'] == 5


if __name__ == "__main__":
    pytest.main([__file__])
