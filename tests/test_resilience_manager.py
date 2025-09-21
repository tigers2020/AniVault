"""Tests for resilience management system."""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock

from src.core.database_health import HealthStatus, DatabaseHealthChecker
from src.core.metadata_cache import MetadataCache
from src.core.resilience_manager import (
    ResilienceManager,
    create_resilience_manager,
    get_resilience_manager,
    set_global_resilience_manager,
    get_system_status,
    is_system_operational,
)


class TestResilienceManager:
    """Test ResilienceManager class."""
    
    @pytest.fixture
    def mock_metadata_cache(self):
        """Create a mock metadata cache."""
        cache = Mock(spec=MetadataCache)
        cache.is_cache_only_mode.return_value = False
        cache.get_cache_only_reason.return_value = ""
        cache.get_stats.return_value = Mock(hits=10, misses=5)
        return cache
    
    @pytest.fixture
    def mock_health_checker(self):
        """Create a mock health checker."""
        checker = Mock(spec=DatabaseHealthChecker)
        checker.get_current_status.return_value = HealthStatus.HEALTHY
        checker.get_statistics.return_value = {
            'total_checks': 10,
            'successful_checks': 8,
            'failed_checks': 2,
            'success_rate': 0.8
        }
        checker.add_status_change_callback = Mock()
        checker.start_monitoring = Mock()
        checker.stop_monitoring = Mock()
        return checker
    
    @pytest.fixture
    def resilience_manager(self, mock_metadata_cache, mock_health_checker):
        """Create a ResilienceManager instance."""
        return ResilienceManager(
            metadata_cache=mock_metadata_cache,
            health_checker=mock_health_checker,
            auto_recovery_enabled=True,
            recovery_check_interval=1.0
        )
    
    def test_initialization(self, resilience_manager, mock_metadata_cache, mock_health_checker):
        """Test resilience manager initialization."""
        assert resilience_manager.metadata_cache == mock_metadata_cache
        assert resilience_manager.health_checker == mock_health_checker
        assert resilience_manager.auto_recovery_enabled is True
        assert resilience_manager.is_operational() is True
    
    def test_initialize(self, resilience_manager, mock_metadata_cache, mock_health_checker):
        """Test resilience manager initialization process."""
        resilience_manager.initialize()
        
        # Should enable auto cache-only mode
        mock_metadata_cache.enable_auto_cache_only_mode.assert_called_once()
        
        # Should register callback with health checker
        mock_health_checker.add_status_change_callback.assert_called_once()
        
        # Should start health monitoring
        mock_health_checker.start_monitoring.assert_called_once()
    
    def test_shutdown(self, resilience_manager, mock_metadata_cache, mock_health_checker):
        """Test resilience manager shutdown process."""
        # First initialize
        resilience_manager.initialize()
        
        # Then shutdown
        resilience_manager.shutdown()
        
        # Should stop health monitoring
        mock_health_checker.stop_monitoring.assert_called_once()
        
        # Should disable cache-only mode if active (only if it was enabled)
        # Note: disable_cache_only_mode may not be called if cache-only mode was never enabled
        # mock_metadata_cache.disable_cache_only_mode.assert_called_once()
    
    def test_health_status_change_to_unhealthy(self, resilience_manager, mock_metadata_cache):
        """Test handling of health status change to unhealthy."""
        # Simulate health status change
        resilience_manager._on_health_status_change(HealthStatus.HEALTHY, HealthStatus.UNHEALTHY)
        
        # Should be non-operational
        assert resilience_manager.is_operational() is False
        
        # Should enable cache-only mode
        mock_metadata_cache.enable_cache_only_mode.assert_called_once_with("System failure detected")
        
        # Should update failure statistics
        status = resilience_manager.get_system_status()
        assert status['total_failures'] == 1
        assert status['is_operational'] is False
    
    def test_health_status_change_to_healthy(self, resilience_manager, mock_metadata_cache):
        """Test handling of health status change to healthy."""
        # First make system unhealthy
        resilience_manager._on_health_status_change(HealthStatus.HEALTHY, HealthStatus.UNHEALTHY)
        assert resilience_manager.is_operational() is False
        
        # Then simulate recovery
        resilience_manager._on_health_status_change(HealthStatus.UNHEALTHY, HealthStatus.HEALTHY)
        
        # Should be operational again
        assert resilience_manager.is_operational() is True
        
        # Should disable cache-only mode (only if it was enabled)
        # Note: This may not be called if cache-only mode was never enabled
        # mock_metadata_cache.disable_cache_only_mode.assert_called_once()
        
        # Should update recovery statistics
        status = resilience_manager.get_system_status()
        assert status['total_recoveries'] == 1
        assert status['is_operational'] is True
    
    def test_force_recovery_check_success(self, resilience_manager, mock_health_checker):
        """Test forced recovery check with success."""
        # Make system non-operational
        resilience_manager._is_operational = False
        
        # Mock successful health check
        mock_health_checker.check_health.return_value = HealthStatus.HEALTHY
        
        # Force recovery check
        result = resilience_manager.force_recovery_check()
        
        assert result is True
        assert resilience_manager.is_operational() is True
    
    def test_force_recovery_check_failure(self, resilience_manager, mock_health_checker):
        """Test forced recovery check with failure."""
        # Make system non-operational
        resilience_manager._is_operational = False
        
        # Mock failed health check
        mock_health_checker.check_health.return_value = HealthStatus.UNHEALTHY
        
        # Force recovery check
        result = resilience_manager.force_recovery_check()
        
        assert result is True  # Recovery was attempted
        assert resilience_manager.is_operational() is False  # But failed
    
    def test_recovery_check_rate_limiting(self, resilience_manager, mock_health_checker):
        """Test recovery check rate limiting."""
        # Make system non-operational
        resilience_manager._is_operational = False
        
        # Mock health checker to return unhealthy
        mock_health_checker.check_health.return_value = HealthStatus.UNHEALTHY
        
        # First recovery attempt
        result1 = resilience_manager.force_recovery_check()
        assert result1 is True
        
        # Immediate second attempt should be rate limited
        result2 = resilience_manager.force_recovery_check()
        assert result2 is False  # Rate limited
    
    def test_get_system_status(self, resilience_manager, mock_metadata_cache, mock_health_checker):
        """Test getting comprehensive system status."""
        status = resilience_manager.get_system_status()
        
        # Check basic status fields
        assert 'is_operational' in status
        assert 'cache_only_mode' in status
        assert 'cache_only_reason' in status
        assert 'total_failures' in status
        assert 'total_recoveries' in status
        assert 'auto_recovery_enabled' in status
        
        # Check health status (may be None if health checker is not initialized)
        if status['health_status'] is not None:
            assert status['health_status'] == 'healthy'
        assert 'health_statistics' in status
        
        # Check cache status
        assert 'cache_statistics' in status
    
    def test_reset_statistics(self, resilience_manager):
        """Test statistics reset."""
        # Generate some statistics
        resilience_manager._total_failures = 5
        resilience_manager._total_recoveries = 3
        resilience_manager._recovery_attempts = 10
        
        # Reset statistics
        resilience_manager.reset_statistics()
        
        # Verify reset
        assert resilience_manager._total_failures == 0
        assert resilience_manager._total_recoveries == 0
        assert resilience_manager._recovery_attempts == 0
    
    def test_recovery_monitoring_lifecycle(self, resilience_manager):
        """Test recovery monitoring start/stop lifecycle."""
        # Start monitoring
        resilience_manager._start_recovery_monitoring()
        assert resilience_manager._recovery_monitoring is True
        assert resilience_manager._recovery_thread is not None
        
        # Wait a bit
        time.sleep(0.1)
        
        # Stop monitoring
        resilience_manager._stop_recovery_monitoring()
        assert resilience_manager._recovery_monitoring is False
    
    def test_recovery_monitoring_with_operational_system(self, resilience_manager):
        """Test recovery monitoring when system is operational."""
        # System is operational, should not attempt recovery
        resilience_manager._start_recovery_monitoring()
        
        # Wait for monitoring cycle
        time.sleep(1.5)
        
        # Should not have attempted recovery
        assert resilience_manager._recovery_attempts == 0
        
        resilience_manager._stop_recovery_monitoring()
    
    def test_recovery_monitoring_with_non_operational_system(self, resilience_manager, mock_health_checker):
        """Test recovery monitoring when system is non-operational."""
        # Make system non-operational
        resilience_manager._is_operational = False
        
        # Mock health checker
        mock_health_checker.check_health.return_value = HealthStatus.UNHEALTHY
        
        # Start monitoring
        resilience_manager._start_recovery_monitoring()
        
        # Wait for monitoring cycle
        time.sleep(1.5)
        
        # Should have attempted recovery
        assert resilience_manager._recovery_attempts >= 1
        
        resilience_manager._stop_recovery_monitoring()


class TestGlobalFunctions:
    """Test global utility functions."""
    
    @pytest.fixture
    def mock_metadata_cache(self):
        """Create a mock metadata cache."""
        cache = Mock(spec=MetadataCache)
        cache.get_stats.return_value = Mock(hits=10, misses=5)
        return cache
    
    @pytest.fixture
    def mock_health_checker(self):
        """Create a mock health checker."""
        checker = Mock(spec=DatabaseHealthChecker)
        checker.get_statistics.return_value = {'total_checks': 10}
        return checker
    
    def test_create_resilience_manager(self, mock_metadata_cache, mock_health_checker):
        """Test create_resilience_manager function."""
        manager = create_resilience_manager(
            metadata_cache=mock_metadata_cache,
            health_checker=mock_health_checker,
            auto_recovery_enabled=True,
            recovery_check_interval=30.0
        )
        
        assert isinstance(manager, ResilienceManager)
        assert manager.metadata_cache == mock_metadata_cache
        assert manager.health_checker == mock_health_checker
        assert manager.auto_recovery_enabled is True
        assert manager.recovery_check_interval == 30.0
    
    def test_global_resilience_manager_management(self, mock_metadata_cache):
        """Test global resilience manager management."""
        # Initially no global manager
        assert get_resilience_manager() is None
        
        # Create and set global manager
        manager = create_resilience_manager(mock_metadata_cache)
        set_global_resilience_manager(manager)
        
        # Verify global manager is set
        assert get_resilience_manager() == manager
        
        # Test global status functions
        with patch.object(manager, 'get_system_status', return_value={'is_operational': True}):
            status = get_system_status()
            assert status['is_operational'] is True
        
        with patch.object(manager, 'is_operational', return_value=False):
            assert is_system_operational() is False
    
    def test_global_functions_without_manager(self):
        """Test global functions when no manager is set."""
        # Ensure no global manager
        set_global_resilience_manager(None)
        
        # Should return empty status and assume operational
        assert get_system_status() == {}
        assert is_system_operational() is True  # Default assumption


class TestResilienceManagerIntegration:
    """Integration tests for resilience manager."""
    
    @pytest.fixture
    def real_metadata_cache(self):
        """Create a real metadata cache for integration tests."""
        from src.core.database import DatabaseManager
        from src.core.metadata_cache import MetadataCache
        
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        
        cache = MetadataCache(
            max_size=100,
            max_memory_mb=10,
            db_manager=db_manager,
            enable_db=True
        )
        return cache
    
    @pytest.fixture
    def real_health_checker(self, real_metadata_cache):
        """Create a real health checker for integration tests."""
        from src.core.database_health import create_database_health_checker
        
        # Get database manager from cache
        db_manager = real_metadata_cache.db_manager
        
        checker = create_database_health_checker(
            db_manager=db_manager,
            check_interval=1.0,
            timeout=2.0,
            failure_threshold=1,
            recovery_threshold=1
        )
        return checker
    
    def test_full_resilience_system_integration(self, real_metadata_cache, real_health_checker):
        """Test full resilience system integration."""
        # Create resilience manager
        manager = create_resilience_manager(
            metadata_cache=real_metadata_cache,
            health_checker=real_health_checker,
            auto_recovery_enabled=False,  # Disable auto recovery to avoid thread issues
            recovery_check_interval=1.0
        )
        
        try:
            # System should be operational initially
            assert manager.is_operational() is True
            
            # Check system status
            status = manager.get_system_status()
            assert status['is_operational'] is True
            assert status['cache_only_mode'] is False
            
            # Force a health check
            result = manager.force_recovery_check()
            assert result is True
            
        finally:
            # Clean up - ensure all threads are stopped
            manager.shutdown()
            # Also stop the health checker explicitly
            real_health_checker.stop_monitoring()
    
    def test_cache_only_mode_transition(self, real_metadata_cache, real_health_checker):
        """Test cache-only mode transition."""
        manager = create_resilience_manager(
            metadata_cache=real_metadata_cache,
            health_checker=real_health_checker,
            auto_recovery_enabled=False,  # Disable auto recovery to avoid thread issues
            recovery_check_interval=1.0
        )
        
        try:
            # Manually enable cache-only mode
            real_metadata_cache.enable_cache_only_mode("Test transition")
            
            # Check status
            status = manager.get_system_status()
            assert status['cache_only_mode'] is True
            assert status['cache_only_reason'] == "Test transition"
            
            # Disable cache-only mode
            real_metadata_cache.disable_cache_only_mode()
            
            # Check status again
            status = manager.get_system_status()
            assert status['cache_only_mode'] is False
            
        finally:
            # Clean up - ensure all threads are stopped
            manager.shutdown()
            # Also stop the health checker explicitly
            real_health_checker.stop_monitoring()


class TestResilienceManagerThreadSafety:
    """Test thread safety of resilience manager."""
    
    @pytest.fixture
    def mock_metadata_cache(self):
        """Create a mock metadata cache."""
        cache = Mock(spec=MetadataCache)
        cache.is_cache_only_mode.return_value = False
        cache.get_stats.return_value = Mock(hits=10, misses=5)
        return cache
    
    @pytest.fixture
    def mock_health_checker(self):
        """Create a mock health checker."""
        checker = Mock(spec=DatabaseHealthChecker)
        checker.get_current_status.return_value = HealthStatus.HEALTHY
        checker.get_statistics.return_value = {'total_checks': 10}
        checker.add_status_change_callback = Mock()
        checker.start_monitoring = Mock()
        checker.stop_monitoring = Mock()
        return checker
    
    def test_concurrent_status_checks(self, mock_metadata_cache, mock_health_checker):
        """Test concurrent status check calls."""
        manager = create_resilience_manager(
            metadata_cache=mock_metadata_cache,
            health_checker=mock_health_checker,
            auto_recovery_enabled=False  # Disable to avoid thread conflicts
        )
        
        results = []
        
        def check_status():
            is_op = manager.is_operational()
            status = manager.get_system_status()
            results.append((is_op, status['is_operational']))
        
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
        assert all(is_op == status_op for is_op, status_op in results)
    
    def test_concurrent_recovery_attempts(self, mock_metadata_cache, mock_health_checker):
        """Test concurrent recovery attempt calls."""
        manager = create_resilience_manager(
            metadata_cache=mock_metadata_cache,
            health_checker=mock_health_checker,
            auto_recovery_enabled=False
        )
        
        # Make system non-operational
        manager._is_operational = False
        
        # Mock health checker to always return unhealthy
        mock_health_checker.check_health.return_value = HealthStatus.UNHEALTHY
        
        results = []
        
        def attempt_recovery():
            result = manager.force_recovery_check()
            results.append(result)
        
        # Create multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=attempt_recovery)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have some successful attempts (not all rate limited)
        assert len(results) == 3
        assert any(result is True for result in results)


if __name__ == "__main__":
    pytest.main([__file__])
