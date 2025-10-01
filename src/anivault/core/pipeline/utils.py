"""Pipeline utilities for AniVault.

This module provides core utilities for the file processing pipeline:
- BoundedQueue: Thread-safe queue with size limits for backpressure
- Statistics classes: For collecting pipeline metrics
"""

from __future__ import annotations

import queue
import threading
from typing import Any


class BoundedQueue:
    """Thread-safe queue with size limits for backpressure control.

    This class wraps Python's queue.Queue to provide a bounded queue
    that blocks when full, implementing backpressure in the pipeline.

    Args:
        maxsize: Maximum number of items the queue can hold.
                0 means unlimited size.
    """

    def __init__(self, maxsize: int = 0) -> None:
        """Initialize the bounded queue.

        Args:
            maxsize: Maximum number of items the queue can hold.
                    0 means unlimited size.
        """
        self._queue = queue.Queue(maxsize=maxsize)
        self._maxsize = maxsize

    def put(
        self,
        item: Any,
        block: bool = True,
        timeout: float | None = None,
    ) -> None:
        """Put an item into the queue.

        Args:
            item: The item to put into the queue.
            block: If True, block until a slot is available.
            timeout: Maximum time to wait if blocking.

        Raises:
            queue.Full: If the queue is full and block is False.
        """
        self._queue.put(item, block=block, timeout=timeout)

    def get(self, block: bool = True, timeout: float | None = None) -> Any:
        """Get an item from the queue.

        Args:
            block: If True, block until an item is available.
            timeout: Maximum time to wait if blocking.

        Returns:
            The item from the queue.

        Raises:
            queue.Empty: If the queue is empty and block is False.
        """
        return self._queue.get(block=block, timeout=timeout)

    def qsize(self) -> int:
        """Return the approximate size of the queue.

        Returns:
            The approximate number of items in the queue.
        """
        return self._queue.qsize()

    def empty(self) -> bool:
        """Return True if the queue is empty.

        Returns:
            True if the queue is empty, False otherwise.
        """
        return self._queue.empty()

    def full(self) -> bool:
        """Return True if the queue is full.

        Returns:
            True if the queue is full, False otherwise.
        """
        return self._queue.full()

    def task_done(self) -> None:
        """Indicate that a formerly enqueued task is complete.

        Used by queue consumer threads. For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.
        """
        self._queue.task_done()

    @property
    def maxsize(self) -> int:
        """Get the maximum size of the queue.

        Returns:
            The maximum number of items the queue can hold.
        """
        return self._maxsize


class ScanStatistics:
    """Statistics collector for directory scanning operations.

    This class provides thread-safe counters for tracking scanning metrics.
    """

    def __init__(self) -> None:
        """Initialize the scan statistics with zero counters."""
        self._lock = threading.Lock()
        self._files_scanned = 0
        self._directories_scanned = 0

    def increment_files_scanned(self) -> None:
        """Increment the files scanned counter."""
        with self._lock:
            self._files_scanned += 1

    def increment_directories_scanned(self) -> None:
        """Increment the directories scanned counter."""
        with self._lock:
            self._directories_scanned += 1

    @property
    def files_scanned(self) -> int:
        """Get the number of files scanned."""
        with self._lock:
            return self._files_scanned

    @property
    def directories_scanned(self) -> int:
        """Get the number of directories scanned."""
        with self._lock:
            return self._directories_scanned


class QueueStatistics:
    """Statistics collector for queue operations.

    This class provides thread-safe counters for tracking queue metrics.
    """

    def __init__(self) -> None:
        """Initialize the queue statistics with zero counters."""
        self._lock = threading.Lock()
        self._items_put = 0
        self._items_got = 0
        self._max_size = 0

    def increment_items_put(self) -> None:
        """Increment the items put counter."""
        with self._lock:
            self._items_put += 1

    def increment_items_got(self) -> None:
        """Increment the items got counter."""
        with self._lock:
            self._items_got += 1

    def update_max_size(self, size: int) -> None:
        """Update the maximum size observed.

        Args:
            size: The current size of the queue.
        """
        with self._lock:
            self._max_size = max(size, self._max_size)

    @property
    def items_put(self) -> int:
        """Get the number of items put into the queue."""
        with self._lock:
            return self._items_put

    @property
    def items_got(self) -> int:
        """Get the number of items got from the queue."""
        with self._lock:
            return self._items_got

    @property
    def max_size(self) -> int:
        """Get the maximum size observed."""
        with self._lock:
            return self._max_size


class ParserStatistics:
    """Statistics collector for parser operations.

    This class provides thread-safe counters for tracking parser metrics.
    """

    def __init__(self) -> None:
        """Initialize the parser statistics with zero counters."""
        self._lock = threading.Lock()
        self._items_processed = 0
        self._successes = 0
        self._failures = 0
        self._cache_hits = 0
        self._cache_misses = 0

    def increment_items_processed(self) -> None:
        """Increment the items processed counter."""
        with self._lock:
            self._items_processed += 1

    def increment_successes(self) -> None:
        """Increment the successes counter."""
        with self._lock:
            self._successes += 1

    def increment_failures(self) -> None:
        """Increment the failures counter."""
        with self._lock:
            self._failures += 1

    def increment_cache_hit(self) -> None:
        """Increment the cache hits counter."""
        with self._lock:
            self._cache_hits += 1

    def increment_cache_miss(self) -> None:
        """Increment the cache misses counter."""
        with self._lock:
            self._cache_misses += 1

    @property
    def items_processed(self) -> int:
        """Get the number of items processed."""
        with self._lock:
            return self._items_processed

    @property
    def successes(self) -> int:
        """Get the number of successful operations."""
        with self._lock:
            return self._successes

    @property
    def failures(self) -> int:
        """Get the number of failed operations."""
        with self._lock:
            return self._failures

    @property
    def cache_hits(self) -> int:
        """Get the number of cache hits."""
        with self._lock:
            return self._cache_hits

    @property
    def cache_misses(self) -> int:
        """Get the number of cache misses."""
        with self._lock:
            return self._cache_misses
