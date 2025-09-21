"""Tests for ThreadExecutorManager."""

import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest

from src.core.thread_executor_manager import (
    ThreadExecutorManager,
    cleanup_thread_executors,
    get_thread_executor_manager,
)


class TestThreadExecutorManager(unittest.TestCase):
    """Test cases for ThreadExecutorManager."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.manager = ThreadExecutorManager()

    def tearDown(self) -> None:
        """Clean up after tests."""
        self.manager.shutdown_all(wait=False)

    def test_initialization(self) -> None:
        """Test that ThreadExecutorManager initializes correctly."""
        assert self.manager._tmdb_max_workers is not None
        assert self.manager._file_scan_max_workers is not None
        assert self.manager._general_max_workers is not None

        # Verify worker counts are reasonable
        assert self.manager._tmdb_max_workers > 0
        assert self.manager._file_scan_max_workers > 0
        assert self.manager._general_max_workers > 0

        # TMDB workers should be higher than others (I/O-bound)
        assert self.manager._tmdb_max_workers >= self.manager._file_scan_max_workers

    def test_tmdb_worker_calculation(self) -> None:
        """Test TMDB worker calculation logic."""
        with patch("os.cpu_count", return_value=8):
            manager = ThreadExecutorManager()
            workers = manager._calculate_tmdb_workers()

            # Should be higher than CPU count for I/O-bound tasks
            assert workers > 8
            # Should not exceed reasonable limits
            assert workers <= 64
            # Should have minimum workers
            assert workers >= 8

    def test_file_scan_worker_calculation(self) -> None:
        """Test file scan worker calculation logic."""
        with patch("os.cpu_count", return_value=4):
            manager = ThreadExecutorManager()
            workers = manager._calculate_file_scan_workers()

            # Should be based on CPU count for disk I/O
            expected_min = 4
            expected_max = 8  # 2 * cpu_count
            assert workers >= expected_min
            assert workers <= expected_max

    def test_general_worker_calculation(self) -> None:
        """Test general worker calculation logic."""
        with patch("os.cpu_count", return_value=4):
            manager = ThreadExecutorManager()
            workers = manager._calculate_general_workers()

            # Should be moderate for mixed workloads
            expected_min = 4
            expected_max = 24
            assert workers >= expected_min
            assert workers <= expected_max

    def test_get_tmdb_executor(self) -> None:
        """Test getting TMDB executor."""
        executor = self.manager.get_tmdb_executor()

        assert isinstance(executor, ThreadPoolExecutor)
        assert executor._max_workers == self.manager._tmdb_max_workers
        assert not executor._shutdown

    def test_get_file_scan_executor(self) -> None:
        """Test getting file scan executor."""
        executor = self.manager.get_file_scan_executor()

        assert isinstance(executor, ThreadPoolExecutor)
        assert executor._max_workers == self.manager._file_scan_max_workers
        assert not executor._shutdown

    def test_get_general_executor(self) -> None:
        """Test getting general executor."""
        executor = self.manager.get_general_executor()

        assert isinstance(executor, ThreadPoolExecutor)
        assert executor._max_workers == self.manager._general_max_workers
        assert not executor._shutdown

    def test_get_executor_for_operation(self) -> None:
        """Test getting executor for specific operation types."""
        # Test TMDB operation
        tmdb_executor = self.manager.get_executor_for_operation("tmdb")
        assert tmdb_executor._max_workers == self.manager._tmdb_max_workers

        # Test file scan operation
        scan_executor = self.manager.get_executor_for_operation("file_scan")
        assert scan_executor._max_workers == self.manager._file_scan_max_workers

        # Test general operation
        general_executor = self.manager.get_executor_for_operation("general")
        assert general_executor._max_workers == self.manager._general_max_workers

        # Test invalid operation type
        with pytest.raises(ValueError):
            self.manager.get_executor_for_operation("invalid")

    def test_executor_reuse(self) -> None:
        """Test that executors are reused when called multiple times."""
        executor1 = self.manager.get_tmdb_executor()
        executor2 = self.manager.get_tmdb_executor()

        # Should return the same instance
        assert executor1 is executor2

    def test_shutdown_all(self) -> None:
        """Test shutting down all executors."""
        # Get executors to create them
        self.manager.get_tmdb_executor()
        self.manager.get_file_scan_executor()
        self.manager.get_general_executor()

        # Shutdown all
        self.manager.shutdown_all(wait=False)

        # Verify all are shutdown
        assert self.manager._tmdb_executor._shutdown
        assert self.manager._file_scan_executor._shutdown
        assert self.manager._general_executor._shutdown

    def test_get_configuration_info(self) -> None:
        """Test getting configuration information."""
        config = self.manager.get_configuration_info()

        assert "system_cpu_count" in config
        assert "tmdb_max_workers" in config
        assert "file_scan_max_workers" in config
        assert "general_max_workers" in config
        assert "tmdb_executor_active" in config
        assert "file_scan_executor_active" in config
        assert "general_executor_active" in config

        # Verify values match internal state
        assert config["tmdb_max_workers"] == self.manager._tmdb_max_workers
        assert config["file_scan_max_workers"] == self.manager._file_scan_max_workers
        assert config["general_max_workers"] == self.manager._general_max_workers


class TestGlobalFunctions(unittest.TestCase):
    """Test cases for global functions."""

    def tearDown(self) -> None:
        """Clean up after tests."""
        cleanup_thread_executors()

    def test_get_thread_executor_manager_singleton(self) -> None:
        """Test that get_thread_executor_manager returns singleton."""
        manager1 = get_thread_executor_manager()
        manager2 = get_thread_executor_manager()

        # Should return the same instance
        assert manager1 is manager2

    def test_cleanup_thread_executors(self) -> None:
        """Test cleaning up thread executors."""
        # Get manager to create it
        manager = get_thread_executor_manager()
        manager.get_tmdb_executor()

        # Cleanup
        cleanup_thread_executors()

        # Manager should be None after cleanup
        from src.core.thread_executor_manager import _thread_executor_manager

        assert _thread_executor_manager is None


class TestWorkerCountScenarios(unittest.TestCase):
    """Test worker count calculations for different system configurations."""

    def test_low_cpu_count(self) -> None:
        """Test with low CPU count."""
        with patch("os.cpu_count", return_value=2):
            manager = ThreadExecutorManager()

            # Should still have reasonable worker counts
            assert manager._tmdb_max_workers >= 8
            assert manager._file_scan_max_workers >= 4
            assert manager._general_max_workers >= 4

    def test_high_cpu_count(self) -> None:
        """Test with high CPU count."""
        with patch("os.cpu_count", return_value=32):
            manager = ThreadExecutorManager()

            # Should cap at reasonable limits
            assert manager._tmdb_max_workers <= 64
            assert manager._file_scan_max_workers <= 32
            assert manager._general_max_workers <= 24

    def test_no_cpu_count(self) -> None:
        """Test when os.cpu_count() returns None."""
        with patch("os.cpu_count", return_value=None):
            manager = ThreadExecutorManager()

            # Should use default values
            assert manager._tmdb_max_workers > 0
            assert manager._file_scan_max_workers > 0
            assert manager._general_max_workers > 0


if __name__ == "__main__":
    unittest.main()
