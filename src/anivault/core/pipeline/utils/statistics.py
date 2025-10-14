"""Statistics collectors for pipeline operations.

This module provides thread-safe statistics collectors for tracking
metrics across different pipeline components:
- ScanStatistics: Directory scanning metrics
- QueueStatistics: Inter-component queue metrics
- ParserStatistics: File parsing metrics
"""

from __future__ import annotations

import threading


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
