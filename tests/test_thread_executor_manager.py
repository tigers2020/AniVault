"""Tests for ThreadExecutorManager."""

import os
import unittest
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

from src.core.thread_executor_manager import (
    ThreadExecutorManager,
    get_thread_executor_manager,
    cleanup_thread_executors
)


class TestThreadExecutorManager(unittest.TestCase):
    """Test cases for ThreadExecutorManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = ThreadExecutorManager()

    def tearDown(self):
        """Clean up after tests."""
        self.manager.shutdown_all(wait=False)

    def test_initialization(self):
        """Test that ThreadExecutorManager initializes correctly."""
        self.assertIsNotNone(self.manager._tmdb_max_workers)
        self.assertIsNotNone(self.manager._file_scan_max_workers)
        self.assertIsNotNone(self.manager._general_max_workers)

        # Verify worker counts are reasonable
        self.assertGreater(self.manager._tmdb_max_workers, 0)
        self.assertGreater(self.manager._file_scan_max_workers, 0)
        self.assertGreater(self.manager._general_max_workers, 0)

        # TMDB workers should be higher than others (I/O-bound)
        self.assertGreaterEqual(self.manager._tmdb_max_workers,
                               self.manager._file_scan_max_workers)

    def test_tmdb_worker_calculation(self):
        """Test TMDB worker calculation logic."""
        with patch('os.cpu_count', return_value=8):
            manager = ThreadExecutorManager()
            workers = manager._calculate_tmdb_workers()

            # Should be higher than CPU count for I/O-bound tasks
            self.assertGreater(workers, 8)
            # Should not exceed reasonable limits
            self.assertLessEqual(workers, 64)
            # Should have minimum workers
            self.assertGreaterEqual(workers, 8)

    def test_file_scan_worker_calculation(self):
        """Test file scan worker calculation logic."""
        with patch('os.cpu_count', return_value=4):
            manager = ThreadExecutorManager()
            workers = manager._calculate_file_scan_workers()

            # Should be based on CPU count for disk I/O
            expected_min = 4
            expected_max = 8  # 2 * cpu_count
            self.assertGreaterEqual(workers, expected_min)
            self.assertLessEqual(workers, expected_max)

    def test_general_worker_calculation(self):
        """Test general worker calculation logic."""
        with patch('os.cpu_count', return_value=4):
            manager = ThreadExecutorManager()
            workers = manager._calculate_general_workers()

            # Should be moderate for mixed workloads
            expected_min = 4
            expected_max = 24
            self.assertGreaterEqual(workers, expected_min)
            self.assertLessEqual(workers, expected_max)

    def test_get_tmdb_executor(self):
        """Test getting TMDB executor."""
        executor = self.manager.get_tmdb_executor()

        self.assertIsInstance(executor, ThreadPoolExecutor)
        self.assertEqual(executor._max_workers, self.manager._tmdb_max_workers)
        self.assertFalse(executor._shutdown)

    def test_get_file_scan_executor(self):
        """Test getting file scan executor."""
        executor = self.manager.get_file_scan_executor()

        self.assertIsInstance(executor, ThreadPoolExecutor)
        self.assertEqual(executor._max_workers, self.manager._file_scan_max_workers)
        self.assertFalse(executor._shutdown)

    def test_get_general_executor(self):
        """Test getting general executor."""
        executor = self.manager.get_general_executor()

        self.assertIsInstance(executor, ThreadPoolExecutor)
        self.assertEqual(executor._max_workers, self.manager._general_max_workers)
        self.assertFalse(executor._shutdown)

    def test_get_executor_for_operation(self):
        """Test getting executor for specific operation types."""
        # Test TMDB operation
        tmdb_executor = self.manager.get_executor_for_operation("tmdb")
        self.assertEqual(tmdb_executor._max_workers, self.manager._tmdb_max_workers)

        # Test file scan operation
        scan_executor = self.manager.get_executor_for_operation("file_scan")
        self.assertEqual(scan_executor._max_workers, self.manager._file_scan_max_workers)

        # Test general operation
        general_executor = self.manager.get_executor_for_operation("general")
        self.assertEqual(general_executor._max_workers, self.manager._general_max_workers)

        # Test invalid operation type
        with self.assertRaises(ValueError):
            self.manager.get_executor_for_operation("invalid")

    def test_executor_reuse(self):
        """Test that executors are reused when called multiple times."""
        executor1 = self.manager.get_tmdb_executor()
        executor2 = self.manager.get_tmdb_executor()

        # Should return the same instance
        self.assertIs(executor1, executor2)

    def test_shutdown_all(self):
        """Test shutting down all executors."""
        # Get executors to create them
        self.manager.get_tmdb_executor()
        self.manager.get_file_scan_executor()
        self.manager.get_general_executor()

        # Shutdown all
        self.manager.shutdown_all(wait=False)

        # Verify all are shutdown
        self.assertTrue(self.manager._tmdb_executor._shutdown)
        self.assertTrue(self.manager._file_scan_executor._shutdown)
        self.assertTrue(self.manager._general_executor._shutdown)

    def test_get_configuration_info(self):
        """Test getting configuration information."""
        config = self.manager.get_configuration_info()

        self.assertIn("system_cpu_count", config)
        self.assertIn("tmdb_max_workers", config)
        self.assertIn("file_scan_max_workers", config)
        self.assertIn("general_max_workers", config)
        self.assertIn("tmdb_executor_active", config)
        self.assertIn("file_scan_executor_active", config)
        self.assertIn("general_executor_active", config)

        # Verify values match internal state
        self.assertEqual(config["tmdb_max_workers"], self.manager._tmdb_max_workers)
        self.assertEqual(config["file_scan_max_workers"], self.manager._file_scan_max_workers)
        self.assertEqual(config["general_max_workers"], self.manager._general_max_workers)


class TestGlobalFunctions(unittest.TestCase):
    """Test cases for global functions."""

    def tearDown(self):
        """Clean up after tests."""
        cleanup_thread_executors()

    def test_get_thread_executor_manager_singleton(self):
        """Test that get_thread_executor_manager returns singleton."""
        manager1 = get_thread_executor_manager()
        manager2 = get_thread_executor_manager()

        # Should return the same instance
        self.assertIs(manager1, manager2)

    def test_cleanup_thread_executors(self):
        """Test cleaning up thread executors."""
        # Get manager to create it
        manager = get_thread_executor_manager()
        manager.get_tmdb_executor()

        # Cleanup
        cleanup_thread_executors()

        # Manager should be None after cleanup
        from src.core.thread_executor_manager import _thread_executor_manager
        self.assertIsNone(_thread_executor_manager)


class TestWorkerCountScenarios(unittest.TestCase):
    """Test worker count calculations for different system configurations."""

    def test_low_cpu_count(self):
        """Test with low CPU count."""
        with patch('os.cpu_count', return_value=2):
            manager = ThreadExecutorManager()

            # Should still have reasonable worker counts
            self.assertGreaterEqual(manager._tmdb_max_workers, 8)
            self.assertGreaterEqual(manager._file_scan_max_workers, 4)
            self.assertGreaterEqual(manager._general_max_workers, 4)

    def test_high_cpu_count(self):
        """Test with high CPU count."""
        with patch('os.cpu_count', return_value=32):
            manager = ThreadExecutorManager()

            # Should cap at reasonable limits
            self.assertLessEqual(manager._tmdb_max_workers, 64)
            self.assertLessEqual(manager._file_scan_max_workers, 32)
            self.assertLessEqual(manager._general_max_workers, 24)

    def test_no_cpu_count(self):
        """Test when os.cpu_count() returns None."""
        with patch('os.cpu_count', return_value=None):
            manager = ThreadExecutorManager()

            # Should use default values
            self.assertGreater(manager._tmdb_max_workers, 0)
            self.assertGreater(manager._file_scan_max_workers, 0)
            self.assertGreater(manager._general_max_workers, 0)


if __name__ == '__main__':
    unittest.main()
