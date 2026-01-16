"""Bounded queue for pipeline backpressure control.

This module provides BoundedQueue, a thread-safe queue wrapper
with size limits for implementing backpressure in the pipeline.

This is a queue.Queue-compatible wrapper used by pipeline components
for inter-component communication with backpressure control.
"""

from __future__ import annotations

import queue
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
        self._queue: queue.Queue[Any] = queue.Queue(maxsize=maxsize)
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
