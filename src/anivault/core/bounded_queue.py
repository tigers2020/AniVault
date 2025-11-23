"""
BoundedQueue - Thread-safe bounded queue implementation.

A thread-safe bounded queue that provides efficient FIFO operations
with configurable capacity limits and blocking behavior.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


@dataclass
class QueueStats:
    """Statistics for queue operations."""

    size: int
    capacity: int
    total_added: int
    total_removed: int
    current_waiting: int
    max_size_reached: int


class BoundedQueue:
    """
    Thread-safe bounded queue with blocking operations.

    Features:
    - Thread-safe operations using locks
    - Configurable capacity limits
    - Blocking and non-blocking operations
    - Statistics tracking
    - Timeout support for operations

    Args:
        capacity: Maximum number of items the queue can hold
        block_on_full: Whether to block when queue is full
        block_on_empty: Whether to block when queue is empty
    """

    def __init__(
        self,
        capacity: int = 1000,
        *,
        block_on_full: bool = True,
        block_on_empty: bool = True,
    ) -> None:
        if capacity <= 0:
            msg = "Capacity must be positive"
            raise ValueError(msg)

        self._capacity = capacity
        self._block_on_full = block_on_full
        self._block_on_empty = block_on_empty

        # Thread synchronization
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)

        # Internal storage
        self._queue: deque[Any] = deque()

        # Statistics
        self._total_added = 0
        self._total_removed = 0
        self._max_size_reached = 0
        self._current_waiting = 0

    def put(self, item: Any, timeout: float | None = None) -> bool:
        """
        Add an item to the queue.

        Args:
            item: Item to add to the queue
            timeout: Maximum time to wait (None for no timeout)

        Returns:
            True if item was added, False if timeout occurred

        Raises:
            ValueError: If item is None
        """
        if item is None:
            msg = "Cannot add None to queue"
            raise ValueError(msg)

        with self._not_full:
            if timeout is None:
                # Block indefinitely until space is available
                while len(self._queue) >= self._capacity:
                    if not self._block_on_full:
                        return False
                    self._not_full.wait()
            else:
                # Block with timeout
                end_time = time.time() + timeout
                while len(self._queue) >= self._capacity:
                    if not self._block_on_full:
                        return False
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return False
                    self._not_full.wait(remaining)

            # Add item
            self._queue.append(item)
            self._total_added += 1
            self._max_size_reached = max(self._max_size_reached, len(self._queue))

            # Notify waiting consumers
            self._not_empty.notify()
            return True

    def get(self, timeout: float | None = None) -> Any | None:
        """
        Remove and return an item from the queue.

        Args:
            timeout: Maximum time to wait (None for no timeout)

        Returns:
            Item from queue, or None if timeout occurred
        """
        with self._not_empty:
            if timeout is None:
                # Block indefinitely until item is available
                while len(self._queue) == 0:
                    if not self._block_on_empty:
                        return None
                    self._not_empty.wait()
            else:
                # Block with timeout
                end_time = time.time() + timeout
                while len(self._queue) == 0:
                    if not self._block_on_empty:
                        return None
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return None
                    self._not_empty.wait(remaining)

            # Remove item
            if len(self._queue) > 0:
                item = self._queue.popleft()
                self._total_removed += 1

                # Notify waiting producers
                self._not_full.notify()
                return item
            return None

    def put_nowait(self, item: Any) -> bool:
        """
        Add an item to the queue without blocking.

        Args:
            item: Item to add to the queue

        Returns:
            True if item was added, False if queue is full
        """
        if item is None:
            msg = "Cannot add None to queue"
            raise ValueError(msg)

        with self._lock:
            if len(self._queue) >= self._capacity:
                return False

            self._queue.append(item)
            self._total_added += 1
            self._max_size_reached = max(self._max_size_reached, len(self._queue))
            self._not_empty.notify()
            return True

    def get_nowait(self) -> Any | None:
        """
        Remove and return an item from the queue without blocking.

        Returns:
            Item from queue, or None if queue is empty
        """
        with self._lock:
            if len(self._queue) == 0:
                return None

            item = self._queue.popleft()
            self._total_removed += 1
            self._not_full.notify()
            return item

    def peek(self) -> Any | None:
        """
        Return the next item without removing it.

        Returns:
            Next item in queue, or None if empty
        """
        with self._lock:
            if len(self._queue) == 0:
                return None
            return self._queue[0]

    def clear(self) -> None:
        """Remove all items from the queue."""
        with self._lock:
            self._queue.clear()
            self._not_full.notify_all()

    def size(self) -> int:
        """Return the current number of items in the queue."""
        with self._lock:
            return len(self._queue)

    def capacity(self) -> int:
        """Return the maximum capacity of the queue."""
        return self._capacity

    def is_empty(self) -> bool:
        """Return True if the queue is empty."""
        with self._lock:
            return len(self._queue) == 0

    def is_full(self) -> bool:
        """Return True if the queue is at capacity."""
        with self._lock:
            return len(self._queue) >= self._capacity

    def get_stats(self) -> QueueStats:
        """Return current queue statistics."""
        with self._lock:
            return QueueStats(
                size=len(self._queue),
                capacity=self._capacity,
                total_added=self._total_added,
                total_removed=self._total_removed,
                current_waiting=self._current_waiting,
                max_size_reached=self._max_size_reached,
            )

    def to_list(self) -> list[Any]:
        """Return a copy of the queue as a list."""
        with self._lock:
            return list(self._queue)

    def __len__(self) -> int:
        """Return the current number of items in the queue."""
        return self.size()

    def __bool__(self) -> bool:
        """Return True if the queue is not empty."""
        return not self.is_empty()

    def __iter__(self) -> Iterator[Any]:
        """Return an iterator over the queue items."""
        with self._lock:
            return iter(list(self._queue))

    def __repr__(self) -> str:
        """Return a string representation of the queue."""
        return f"BoundedQueue(size={self.size()}, capacity={self._capacity})"
