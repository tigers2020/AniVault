"""Semaphore Manager for concurrency control.

This module provides a semaphore manager to limit the number of concurrent
requests sent to external APIs, preventing overwhelming the API and helping
manage application resources.
"""

from __future__ import annotations

import threading

from typing_extensions import Self


class SemaphoreManager:
    """Semaphore manager for controlling concurrent API requests.

    This class provides a thread-safe way to limit the number of concurrent
    requests to external APIs. It uses a semaphore to control access and
    can be used as a context manager for automatic resource management.

    Args:
        concurrency_limit: Maximum number of concurrent requests allowed (default: 4)
    """

    def __init__(self, concurrency_limit: int = 4):
        """Initialize the semaphore manager.

        Args:
            concurrency_limit: Maximum number of concurrent requests allowed
        """
        self.concurrency_limit = concurrency_limit
        self._semaphore = threading.Semaphore(concurrency_limit)
        self._lock = threading.Lock()
        self._active_count = 0

    def acquire(self, timeout: float | None = 30.0) -> bool:
        """Acquire the semaphore with optional timeout.

        This method attempts to acquire the semaphore, blocking until
        it becomes available or the timeout expires.

        Args:
            timeout: Maximum time to wait for semaphore acquisition in seconds.
                    If None, blocks indefinitely. Default: 30.0 seconds.

        Returns:
            True if semaphore was acquired successfully, False if timeout occurred
        """
        acquired = self._semaphore.acquire(timeout=timeout)

        if acquired:
            with self._lock:
                self._active_count += 1

        return acquired

    def release(self) -> None:
        """Release the semaphore.

        This method releases a previously acquired semaphore, making it
        available for other threads to acquire.
        """
        with self._lock:
            if self._active_count > 0:
                self._active_count -= 1

        self._semaphore.release()

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            Self for use in context manager
        """
        if not self.acquire():
            raise RuntimeError("Failed to acquire semaphore within timeout")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        self.release()

    def get_active_count(self) -> int:
        """Get the current number of active requests.

        Returns:
            Number of currently active requests
        """
        with self._lock:
            return self._active_count

    def get_available_count(self) -> int:
        """Get the number of available semaphore slots.

        Returns:
            Number of available semaphore slots
        """
        return self._semaphore._value
