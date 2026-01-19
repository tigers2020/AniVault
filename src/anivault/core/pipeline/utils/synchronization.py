"""Thread-safe synchronization utilities for pipeline components.

This module provides common synchronization patterns and utilities
for thread-safe operations in the pipeline components.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Any, Callable, TypeVar
from collections.abc import Iterator

T = TypeVar("T")


class ThreadSafeStatsUpdater:
    """Thread-safe statistics updater for pipeline components.

    Provides a standardized way to update statistics in a thread-safe manner
    across different pipeline components.

    Example:
        >>> stats = ScanStatistics()
        >>> updater = ThreadSafeStatsUpdater(stats, threading.Lock())
        >>> updater.increment_files(count=10)
        >>> updater.increment_directories(count=5)
    """

    def __init__(self, stats: Any, lock: threading.Lock | threading.RLock) -> None:
        """Initialize the thread-safe stats updater.

        Args:
            stats: Statistics object to update.
            lock: Lock to use for thread synchronization.
        """
        self.stats = stats
        self._lock = lock

    def increment_files(self, count: int = 1) -> None:
        """Increment file count in a thread-safe manner.

        Args:
            count: Number of files to increment by. Default is 1.
        """
        with self._lock:
            for _ in range(count):
                if hasattr(self.stats, "increment_files_scanned"):
                    self.stats.increment_files_scanned()
                elif hasattr(self.stats, "increment_files"):
                    self.stats.increment_files()
                else:
                    message = "Stats object " f"{type(self.stats)} does not have increment_files_scanned or increment_files method"
                    raise AttributeError(message)

    def increment_directories(self, count: int = 1) -> None:
        """Increment directory count in a thread-safe manner.

        Args:
            count: Number of directories to increment by. Default is 1.
        """
        with self._lock:
            for _ in range(count):
                if hasattr(self.stats, "increment_directories_scanned"):
                    self.stats.increment_directories_scanned()
                elif hasattr(self.stats, "increment_directories"):
                    self.stats.increment_directories()
                else:
                    message = "Stats object " f"{type(self.stats)} does not have increment_directories_scanned " "or increment_directories method"
                    raise AttributeError(message)

    def update_files_and_directories(
        self,
        files_count: int,
        directories_count: int,
    ) -> None:
        """Update both file and directory counts in a thread-safe manner.

        Args:
            files_count: Number of files to increment by.
            directories_count: Number of directories to increment by.
        """
        with self._lock:
            self.increment_files(files_count)
            self.increment_directories(directories_count)


@contextmanager
def thread_safe_operation(
    lock: threading.Lock | threading.RLock,
) -> Iterator[None]:
    """Context manager for thread-safe operations.

    Provides a clean way to execute code blocks with lock protection.

    Args:
        lock: Lock to use for synchronization.

    Example:
        >>> with thread_safe_operation(my_lock):
        ...     # Thread-safe code here
        ...     shared_resource.modify()
    """
    with lock:
        yield


def synchronized(
    lock: threading.Lock | threading.RLock,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for thread-safe method execution.

    Args:
        lock: Lock to use for synchronization.

    Returns:
        Decorator function.

    Example:
        >>> class MyClass:
        ...     _lock = threading.Lock()
        ...
        ...     @synchronized(_lock)
        ...     def my_method(self):
        ...         # Thread-safe method
        ...         pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with lock:
                return func(*args, **kwargs)

        return wrapper

    return decorator
