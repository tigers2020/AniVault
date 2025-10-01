"""Unit tests for SemaphoreManager."""

import threading
import time
from unittest.mock import patch

import pytest

from anivault.services.semaphore_manager import SemaphoreManager


class TestSemaphoreManager:
    """Test cases for SemaphoreManager."""

    def test_initialization(self):
        """Test semaphore manager initialization."""
        manager = SemaphoreManager(concurrency_limit=5)

        assert manager.concurrency_limit == 5
        assert manager.get_active_count() == 0
        assert manager.get_available_count() == 5

    def test_initialization_default(self):
        """Test semaphore manager initialization with default values."""
        manager = SemaphoreManager()

        assert manager.concurrency_limit == 4
        assert manager.get_active_count() == 0
        assert manager.get_available_count() == 4

    def test_acquire_success(self):
        """Test successful semaphore acquisition."""
        manager = SemaphoreManager(concurrency_limit=2)

        # Should succeed
        assert manager.acquire() is True
        assert manager.get_active_count() == 1
        assert manager.get_available_count() == 1

        # Should succeed again
        assert manager.acquire() is True
        assert manager.get_active_count() == 2
        assert manager.get_available_count() == 0

    def test_acquire_timeout(self):
        """Test semaphore acquisition timeout."""
        manager = SemaphoreManager(concurrency_limit=1)

        # Acquire the only slot
        assert manager.acquire() is True

        # Should timeout when trying to acquire again
        start_time = time.time()
        assert manager.acquire(timeout=0.1) is False
        end_time = time.time()

        # Should have waited approximately 0.1 seconds
        assert end_time - start_time >= 0.1
        assert end_time - start_time < 0.2

    def test_acquire_no_timeout(self):
        """Test semaphore acquisition without timeout."""
        manager = SemaphoreManager(concurrency_limit=1)

        # Acquire the only slot
        assert manager.acquire() is True

        # Should block indefinitely (we'll test this with a thread)
        result = [None]

        def worker():
            result[0] = manager.acquire(timeout=None)

        thread = threading.Thread(target=worker)
        thread.start()

        # Let it block for a short time
        time.sleep(0.1)

        # Release the semaphore
        manager.release()

        # Wait for thread to complete
        thread.join(timeout=1.0)

        # Should have succeeded
        assert result[0] is True

    def test_release(self):
        """Test semaphore release."""
        manager = SemaphoreManager(concurrency_limit=2)

        # Acquire both slots
        assert manager.acquire() is True
        assert manager.acquire() is True
        assert manager.get_active_count() == 2
        assert manager.get_available_count() == 0

        # Release one slot
        manager.release()
        assert manager.get_active_count() == 1
        assert manager.get_available_count() == 1

        # Release the other slot
        manager.release()
        assert manager.get_active_count() == 0
        assert manager.get_available_count() == 2

    def test_context_manager(self):
        """Test semaphore manager as context manager."""
        manager = SemaphoreManager(concurrency_limit=1)

        # Should work as context manager
        with manager:
            assert manager.get_active_count() == 1
            assert manager.get_available_count() == 0

        # Should be released after context
        assert manager.get_active_count() == 0
        assert manager.get_available_count() == 1

    def test_context_manager_exception(self):
        """Test semaphore manager context manager with exception."""
        manager = SemaphoreManager(concurrency_limit=1)

        # Should release even if exception occurs
        try:
            with manager:
                assert manager.get_active_count() == 1
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should be released after exception
        assert manager.get_active_count() == 0
        assert manager.get_available_count() == 1

    def test_thread_safety(self):
        """Test thread safety of semaphore manager."""
        manager = SemaphoreManager(concurrency_limit=2)
        results = []

        def worker(worker_id):
            if manager.acquire(timeout=1.0):
                results.append(f"worker_{worker_id}_acquired")
                time.sleep(0.1)  # Simulate work
                manager.release()
                results.append(f"worker_{worker_id}_released")
            else:
                results.append(f"worker_{worker_id}_timeout")

        # Create multiple threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have some successful acquisitions
        acquired_count = sum(1 for result in results if "acquired" in result)
        assert acquired_count == 5  # All should succeed with timeout

        # Should have some releases
        released_count = sum(1 for result in results if "released" in result)
        assert released_count == 5

    def test_concurrent_acquire_release(self):
        """Test concurrent acquire and release operations."""
        manager = SemaphoreManager(concurrency_limit=3)
        results = []

        def worker(worker_id):
            for _ in range(3):
                if manager.acquire(timeout=0.5):
                    results.append(f"worker_{worker_id}_acquired")
                    time.sleep(0.01)
                    manager.release()
                    results.append(f"worker_{worker_id}_released")
                else:
                    results.append(f"worker_{worker_id}_timeout")

        # Create multiple threads
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have some successful operations
        acquired_count = sum(1 for result in results if "acquired" in result)
        assert acquired_count > 0

        # Should have matching releases
        released_count = sum(1 for result in results if "released" in result)
        assert released_count == acquired_count

    def test_negative_concurrency_limit(self):
        """Test behavior with negative concurrency limit."""
        # Should handle negative limit gracefully
        manager = SemaphoreManager(concurrency_limit=-1)

        # Should still work (semaphore will have 0 capacity)
        assert manager.acquire(timeout=0.1) is False

    def test_zero_concurrency_limit(self):
        """Test behavior with zero concurrency limit."""
        manager = SemaphoreManager(concurrency_limit=0)

        # Should not be able to acquire
        assert manager.acquire(timeout=0.1) is False
        assert manager.get_active_count() == 0
        assert manager.get_available_count() == 0
