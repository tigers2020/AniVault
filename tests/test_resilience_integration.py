"""Tests for resilience integration system."""

from unittest.mock import Mock, patch

import pytest

from src.core.database import DatabaseManager
from src.core.metadata_cache import MetadataCache
from src.core.resilience_integration import (
    force_recovery_check,
    get_resilience_status,
    setup_resilience_system,
    shutdown_resilience_system,
)


class TestResilienceIntegration:
    """Test resilience integration functions."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_manager = Mock(spec=DatabaseManager)
        mock_manager._initialized = True
        return mock_manager

    @pytest.fixture
    def mock_metadata_cache(self):
        """Create a mock metadata cache."""
        cache = Mock(spec=MetadataCache)
        cache.is_cache_only_mode.return_value = False
        cache.get_cache_only_reason.return_value = ""
        cache.get_stats.return_value = Mock(hits=10, misses=5)
        return cache

    def test_setup_resilience_system_success(self, mock_db_manager, mock_metadata_cache) -> None:
        """Test successful resilience system setup."""
        with (
            patch(
                "src.core.resilience_integration.create_database_health_checker"
            ) as mock_create_checker,
            patch(
                "src.core.resilience_integration.create_resilience_manager"
            ) as mock_create_manager,
            patch(
                "src.core.resilience_integration.set_global_resilience_manager"
            ) as mock_set_global,
        ):

            # Mock the created objects
            mock_health_checker = Mock()
            mock_resilience_manager = Mock()

            mock_create_checker.return_value = mock_health_checker
            mock_create_manager.return_value = mock_resilience_manager

            # Setup resilience system
            setup_resilience_system(
                db_manager=mock_db_manager,
                metadata_cache=mock_metadata_cache,
                health_check_interval=30.0,
                health_check_timeout=5.0,
                health_failure_threshold=3,
                health_recovery_threshold=2,
                auto_recovery_enabled=True,
                recovery_check_interval=60.0,
            )

            # Verify health checker was created with correct parameters
            mock_create_checker.assert_called_once_with(
                db_manager=mock_db_manager,
                check_interval=30.0,
                timeout=5.0,
                failure_threshold=3,
                recovery_threshold=2,
            )

            # Verify resilience manager was created
            mock_create_manager.assert_called_once_with(
                metadata_cache=mock_metadata_cache,
                health_checker=mock_health_checker,
                auto_recovery_enabled=True,
                recovery_check_interval=60.0,
            )

            # Verify global manager was set
            mock_set_global.assert_called_once_with(mock_resilience_manager)

            # Verify initialization was called
            mock_resilience_manager.initialize.assert_called_once()

    def test_setup_resilience_system_failure(self, mock_db_manager, mock_metadata_cache) -> None:
        """Test resilience system setup failure."""
        with patch(
            "src.core.resilience_integration.create_database_health_checker"
        ) as mock_create_checker:
            # Mock creation failure
            mock_create_checker.side_effect = Exception("Health checker creation failed")

            # Should raise exception
            with pytest.raises(Exception, match="Health checker creation failed"):
                setup_resilience_system(
                    db_manager=mock_db_manager, metadata_cache=mock_metadata_cache
                )

    def test_shutdown_resilience_system_with_manager(self, mock_metadata_cache) -> None:
        """Test shutdown with existing manager."""
        with patch("src.core.resilience_integration.get_resilience_manager") as mock_get_manager:
            # Mock existing manager
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            # Shutdown system
            shutdown_resilience_system()

            # Verify shutdown was called
            mock_manager.shutdown.assert_called_once()

    def test_shutdown_resilience_system_without_manager(self) -> None:
        """Test shutdown without existing manager."""
        with patch("src.core.resilience_integration.get_resilience_manager") as mock_get_manager:
            # Mock no manager
            mock_get_manager.return_value = None

            # Should not raise exception
            shutdown_resilience_system()

    def test_shutdown_resilience_system_error(self) -> None:
        """Test shutdown with error."""
        with patch("src.core.resilience_integration.get_resilience_manager") as mock_get_manager:
            # Mock manager that raises exception on shutdown
            mock_manager = Mock()
            mock_manager.shutdown.side_effect = Exception("Shutdown failed")
            mock_get_manager.return_value = mock_manager

            # Should not raise exception (error is logged)
            shutdown_resilience_system()

    def test_get_resilience_status_with_manager(self, mock_metadata_cache) -> None:
        """Test getting resilience status with existing manager."""
        with patch("src.core.resilience_integration.get_resilience_manager") as mock_get_manager:
            # Mock manager with status
            mock_manager = Mock()
            expected_status = {
                "is_operational": True,
                "cache_only_mode": False,
                "health_status": "healthy",
            }
            mock_manager.get_system_status.return_value = expected_status
            mock_get_manager.return_value = mock_manager

            # Get status
            status = get_resilience_status()

            # Verify status
            assert status == expected_status
            mock_manager.get_system_status.assert_called_once()

    def test_get_resilience_status_without_manager(self) -> None:
        """Test getting resilience status without manager."""
        with patch("src.core.resilience_integration.get_resilience_manager") as mock_get_manager:
            # Mock no manager
            mock_get_manager.return_value = None

            # Get status
            status = get_resilience_status()

            # Should return error status
            assert status == {"error": "No resilience manager available"}

    def test_get_resilience_status_error(self) -> None:
        """Test getting resilience status with error."""
        with patch("src.core.resilience_integration.get_resilience_manager") as mock_get_manager:
            # Mock manager that raises exception
            mock_manager = Mock()
            mock_manager.get_system_status.side_effect = Exception("Status check failed")
            mock_get_manager.return_value = mock_manager

            # Get status
            status = get_resilience_status()

            # Should return error status
            assert "error" in status
            assert "Status check failed" in status["error"]

    def test_force_recovery_check_with_manager(self, mock_metadata_cache) -> None:
        """Test forced recovery check with existing manager."""
        with patch("src.core.resilience_integration.get_resilience_manager") as mock_get_manager:
            # Mock manager
            mock_manager = Mock()
            mock_manager.force_recovery_check.return_value = True
            mock_get_manager.return_value = mock_manager

            # Force recovery check
            result = force_recovery_check()

            # Verify result
            assert result is True
            mock_manager.force_recovery_check.assert_called_once()

    def test_force_recovery_check_without_manager(self) -> None:
        """Test forced recovery check without manager."""
        with patch("src.core.resilience_integration.get_resilience_manager") as mock_get_manager:
            # Mock no manager
            mock_get_manager.return_value = None

            # Force recovery check
            result = force_recovery_check()

            # Should return False
            assert result is False

    def test_force_recovery_check_error(self) -> None:
        """Test forced recovery check with error."""
        with patch("src.core.resilience_integration.get_resilience_manager") as mock_get_manager:
            # Mock manager that raises exception
            mock_manager = Mock()
            mock_manager.force_recovery_check.side_effect = Exception("Recovery check failed")
            mock_get_manager.return_value = mock_manager

            # Force recovery check
            result = force_recovery_check()

            # Should return False on error
            assert result is False


class TestResilienceIntegrationWithRealComponents:
    """Integration tests with real components."""

    @pytest.fixture
    def real_db_manager(self):
        """Create a real database manager."""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        return db_manager

    @pytest.fixture
    def real_metadata_cache(self, real_db_manager):
        """Create a real metadata cache."""
        cache = MetadataCache(
            max_size=100, max_memory_mb=10, db_manager=real_db_manager, enable_db=True
        )
        return cache

    def test_full_integration_setup_and_shutdown(
        self, real_db_manager, real_metadata_cache
    ) -> None:
        """Test full integration setup and shutdown."""
        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            health_check_interval=1.0,  # Fast for testing
            health_check_timeout=2.0,
            health_failure_threshold=1,
            health_recovery_threshold=1,
            auto_recovery_enabled=True,
            recovery_check_interval=1.0,
        )

        try:
            # Verify system is set up
            status = get_resilience_status()
            assert "error" not in status
            assert "is_operational" in status

            # Test forced recovery check
            result = force_recovery_check()
            assert isinstance(result, bool)

        finally:
            # Shutdown system
            shutdown_resilience_system()

    def test_integration_with_cache_only_mode(self, real_db_manager, real_metadata_cache) -> None:
        """Test integration with cache-only mode."""
        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            health_check_interval=1.0,
            health_check_timeout=2.0,
            health_failure_threshold=1,
            health_recovery_threshold=1,
            auto_recovery_enabled=False,  # Disable auto recovery for testing
        )

        try:
            # Manually enable cache-only mode
            real_metadata_cache.enable_cache_only_mode("Integration test")

            # Check status
            status = get_resilience_status()
            assert status["cache_only_mode"] is True
            assert status["cache_only_reason"] == "Integration test"

            # Disable cache-only mode
            real_metadata_cache.disable_cache_only_mode()

            # Check status again
            status = get_resilience_status()
            assert status["cache_only_mode"] is False

        finally:
            shutdown_resilience_system()

    def test_integration_error_handling(self, real_db_manager, real_metadata_cache) -> None:
        """Test integration error handling."""
        # Test with invalid parameters
        with pytest.raises(Exception):
            setup_resilience_system(db_manager=None, metadata_cache=real_metadata_cache)  # Invalid

        with pytest.raises(Exception):
            setup_resilience_system(db_manager=real_db_manager, metadata_cache=None)  # Invalid


class TestResilienceIntegrationConcurrency:
    """Test resilience integration with concurrent operations."""

    @pytest.fixture
    def real_db_manager(self):
        """Create a real database manager."""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        return db_manager

    @pytest.fixture
    def real_metadata_cache(self, real_db_manager):
        """Create a real metadata cache."""
        cache = MetadataCache(
            max_size=100, max_memory_mb=10, db_manager=real_db_manager, enable_db=True
        )
        return cache

    def test_concurrent_status_checks(self, real_db_manager, real_metadata_cache) -> None:
        """Test concurrent status check calls."""
        import threading

        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            auto_recovery_enabled=False,  # Disable to avoid conflicts
        )

        try:
            results = []

            def check_status() -> None:
                status = get_resilience_status()
                results.append(status)

            # Create multiple threads
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=check_status)
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # All results should be consistent
            assert len(results) == 5
            assert all("error" not in result for result in results)

        finally:
            shutdown_resilience_system()

    def test_concurrent_recovery_checks(self, real_db_manager, real_metadata_cache) -> None:
        """Test concurrent recovery check calls."""
        import threading

        # Setup resilience system
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            auto_recovery_enabled=False,
        )

        try:
            results = []

            def force_recovery() -> None:
                result = force_recovery_check()
                results.append(result)

            # Create multiple threads
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=force_recovery)
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # All results should be boolean
            assert len(results) == 3
            assert all(isinstance(result, bool) for result in results)

        finally:
            shutdown_resilience_system()


class TestResilienceIntegrationConfiguration:
    """Test different configuration scenarios."""

    @pytest.fixture
    def real_db_manager(self):
        """Create a real database manager."""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        return db_manager

    @pytest.fixture
    def real_metadata_cache(self, real_db_manager):
        """Create a real metadata cache."""
        cache = MetadataCache(
            max_size=100, max_memory_mb=10, db_manager=real_db_manager, enable_db=True
        )
        return cache

    def test_sensitive_monitoring_configuration(self, real_db_manager, real_metadata_cache) -> None:
        """Test sensitive monitoring configuration."""
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            health_check_interval=5.0,  # Very frequent
            health_failure_threshold=1,  # Very sensitive
            health_recovery_threshold=1,  # Very fast recovery
            auto_recovery_enabled=True,
            recovery_check_interval=10.0,
        )

        try:
            status = get_resilience_status()
            assert "error" not in status

        finally:
            shutdown_resilience_system()

    def test_stable_monitoring_configuration(self, real_db_manager, real_metadata_cache) -> None:
        """Test stable monitoring configuration."""
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            health_check_interval=120.0,  # Less frequent
            health_failure_threshold=5,  # Less sensitive
            health_recovery_threshold=3,  # More conservative recovery
            auto_recovery_enabled=True,
            recovery_check_interval=300.0,
        )

        try:
            status = get_resilience_status()
            assert "error" not in status

        finally:
            shutdown_resilience_system()

    def test_disabled_auto_recovery_configuration(
        self, real_db_manager, real_metadata_cache
    ) -> None:
        """Test disabled auto recovery configuration."""
        setup_resilience_system(
            db_manager=real_db_manager,
            metadata_cache=real_metadata_cache,
            auto_recovery_enabled=False,  # Disabled
        )

        try:
            status = get_resilience_status()
            assert "error" not in status
            assert status["auto_recovery_enabled"] is False

        finally:
            shutdown_resilience_system()


if __name__ == "__main__":
    pytest.main([__file__])
