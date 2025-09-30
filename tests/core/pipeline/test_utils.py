"""Unit tests for pipeline utilities.

This module contains comprehensive tests for:
- BoundedQueue: Thread-safe queue with size limits
- Statistics classes: Thread-safe counters for pipeline metrics
"""

import pytest
import threading
import time
import queue
from unittest.mock import patch

from anivault.core.pipeline.utils import (
    BoundedQueue,
    ScanStatistics,
    QueueStatistics,
    ParserStatistics,
)


class TestBoundedQueue:
    """Test cases for BoundedQueue class."""

    def test_init_with_maxsize(self) -> None:
        """Test BoundedQueue initialization with maxsize."""
        queue = BoundedQueue(maxsize=5)
        assert queue.maxsize == 5
        assert queue.empty()
        assert not queue.full()

    def test_init_unlimited_size(self) -> None:
        """Test BoundedQueue initialization with unlimited size."""
        queue = BoundedQueue(maxsize=0)
        assert queue.maxsize == 0
        assert queue.empty()
        assert not queue.full()

    def test_put_and_get_single_item(self) -> None:
        """Test basic put and get operations."""
        queue = BoundedQueue(maxsize=1)
        test_item = "test_item"

        queue.put(test_item)
        assert not queue.empty()
        assert queue.full()

        retrieved_item = queue.get()
        assert retrieved_item == test_item
        assert queue.empty()
        assert not queue.full()

    def test_put_and_get_multiple_items(self) -> None:
        """Test put and get operations with multiple items."""
        queue = BoundedQueue(maxsize=3)
        test_items = ["item1", "item2", "item3"]

        # Put all items
        for item in test_items:
            queue.put(item)

        assert queue.qsize() == 3
        assert queue.full()

        # Get all items in order
        retrieved_items = []
        for _ in range(3):
            retrieved_items.append(queue.get())

        assert retrieved_items == test_items
        assert queue.empty()

    def test_put_blocking_behavior(self) -> None:
        """Test that put blocks when queue is full."""
        bounded_queue = BoundedQueue(maxsize=1)

        # Fill the queue
        bounded_queue.put("first_item")
        assert bounded_queue.full()

        # This should block (we'll use a timeout to test)
        start_time = time.time()
        with pytest.raises(queue.Full):
            bounded_queue.put("second_item", block=True, timeout=0.1)

        # Should have blocked for at least the timeout period
        assert time.time() - start_time >= 0.1

    def test_get_blocking_behavior(self) -> None:
        """Test that get blocks when queue is empty."""
        bounded_queue = BoundedQueue(maxsize=1)

        # This should block (we'll use a timeout to test)
        start_time = time.time()
        with pytest.raises(queue.Empty):
            bounded_queue.get(block=True, timeout=0.1)

        # Should have blocked for at least the timeout period
        assert time.time() - start_time >= 0.1

    def test_put_non_blocking(self) -> None:
        """Test put with non-blocking behavior."""
        bounded_queue = BoundedQueue(maxsize=1)

        # Fill the queue
        bounded_queue.put("first_item")

        # This should raise Full immediately
        with pytest.raises(queue.Full):
            bounded_queue.put("second_item", block=False)

    def test_get_non_blocking(self) -> None:
        """Test get with non-blocking behavior."""
        bounded_queue = BoundedQueue(maxsize=1)

        # This should raise Empty immediately
        with pytest.raises(queue.Empty):
            bounded_queue.get(block=False)

    def test_thread_safety(self) -> None:
        """Test thread safety of BoundedQueue operations."""
        queue = BoundedQueue(maxsize=10)
        results = []
        errors = []

        def producer():
            """Produce items to the queue."""
            try:
                for i in range(5):
                    queue.put(f"item_{i}")
                    time.sleep(0.01)  # Small delay to simulate work
            except Exception as e:
                errors.append(e)

        def consumer():
            """Consume items from the queue."""
            try:
                for _ in range(5):
                    item = queue.get()
                    results.append(item)
                    time.sleep(0.01)  # Small delay to simulate work
            except Exception as e:
                errors.append(e)

        # Start producer and consumer threads
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)

        producer_thread.start()
        consumer_thread.start()

        producer_thread.join()
        consumer_thread.join()

        # Verify no errors occurred
        assert not errors, f"Errors occurred: {errors}"

        # Verify all items were processed
        assert len(results) == 5
        assert set(results) == {f"item_{i}" for i in range(5)}


class TestScanStatistics:
    """Test cases for ScanStatistics class."""

    def test_init(self) -> None:
        """Test ScanStatistics initialization."""
        stats = ScanStatistics()
        assert stats.files_scanned == 0
        assert stats.directories_scanned == 0

    def test_increment_files_scanned(self) -> None:
        """Test incrementing files scanned counter."""
        stats = ScanStatistics()

        stats.increment_files_scanned()
        assert stats.files_scanned == 1

        stats.increment_files_scanned()
        assert stats.files_scanned == 2

    def test_increment_directories_scanned(self) -> None:
        """Test incrementing directories scanned counter."""
        stats = ScanStatistics()

        stats.increment_directories_scanned()
        assert stats.directories_scanned == 1

        stats.increment_directories_scanned()
        assert stats.directories_scanned == 2

    def test_thread_safety(self) -> None:
        """Test thread safety of ScanStatistics."""
        stats = ScanStatistics()
        errors = []

        def increment_files():
            """Increment files counter in a loop."""
            try:
                for _ in range(100):
                    stats.increment_files_scanned()
            except Exception as e:
                errors.append(e)

        def increment_directories():
            """Increment directories counter in a loop."""
            try:
                for _ in range(100):
                    stats.increment_directories_scanned()
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=increment_files))
            threads.append(threading.Thread(target=increment_directories))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert not errors, f"Errors occurred: {errors}"

        # Verify final counts
        assert stats.files_scanned == 500  # 5 threads * 100 increments
        assert stats.directories_scanned == 500  # 5 threads * 100 increments


class TestQueueStatistics:
    """Test cases for QueueStatistics class."""

    def test_init(self) -> None:
        """Test QueueStatistics initialization."""
        stats = QueueStatistics()
        assert stats.items_put == 0
        assert stats.items_got == 0
        assert stats.max_size == 0

    def test_increment_items_put(self) -> None:
        """Test incrementing items put counter."""
        stats = QueueStatistics()

        stats.increment_items_put()
        assert stats.items_put == 1

        stats.increment_items_put()
        assert stats.items_put == 2

    def test_increment_items_got(self) -> None:
        """Test incrementing items got counter."""
        stats = QueueStatistics()

        stats.increment_items_got()
        assert stats.items_got == 1

        stats.increment_items_got()
        assert stats.items_got == 2

    def test_update_max_size(self) -> None:
        """Test updating maximum size."""
        stats = QueueStatistics()

        stats.update_max_size(5)
        assert stats.max_size == 5

        stats.update_max_size(3)  # Should not update (3 < 5)
        assert stats.max_size == 5

        stats.update_max_size(10)  # Should update (10 > 5)
        assert stats.max_size == 10

    def test_thread_safety(self) -> None:
        """Test thread safety of QueueStatistics."""
        stats = QueueStatistics()
        errors = []

        def increment_puts():
            """Increment items put counter in a loop."""
            try:
                for _ in range(100):
                    stats.increment_items_put()
            except Exception as e:
                errors.append(e)

        def increment_gets():
            """Increment items got counter in a loop."""
            try:
                for _ in range(100):
                    stats.increment_items_got()
            except Exception as e:
                errors.append(e)

        def update_sizes():
            """Update max size in a loop."""
            try:
                for i in range(100):
                    stats.update_max_size(i)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=increment_puts))
            threads.append(threading.Thread(target=increment_gets))
            threads.append(threading.Thread(target=update_sizes))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert not errors, f"Errors occurred: {errors}"

        # Verify final counts
        assert stats.items_put == 300  # 3 threads * 100 increments
        assert stats.items_got == 300  # 3 threads * 100 increments
        assert stats.max_size >= 99  # At least one thread should have set this


class TestParserStatistics:
    """Test cases for ParserStatistics class."""

    def test_init(self) -> None:
        """Test ParserStatistics initialization."""
        stats = ParserStatistics()
        assert stats.items_processed == 0
        assert stats.successes == 0
        assert stats.failures == 0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0

    def test_increment_items_processed(self) -> None:
        """Test incrementing items processed counter."""
        stats = ParserStatistics()

        stats.increment_items_processed()
        assert stats.items_processed == 1

        stats.increment_items_processed()
        assert stats.items_processed == 2

    def test_increment_successes(self) -> None:
        """Test incrementing successes counter."""
        stats = ParserStatistics()

        stats.increment_successes()
        assert stats.successes == 1

        stats.increment_successes()
        assert stats.successes == 2

    def test_increment_failures(self) -> None:
        """Test incrementing failures counter."""
        stats = ParserStatistics()

        stats.increment_failures()
        assert stats.failures == 1

        stats.increment_failures()
        assert stats.failures == 2

    def test_increment_cache_hit(self) -> None:
        """Test incrementing cache hits counter."""
        stats = ParserStatistics()

        stats.increment_cache_hit()
        assert stats.cache_hits == 1

        stats.increment_cache_hit()
        assert stats.cache_hits == 2

    def test_increment_cache_miss(self) -> None:
        """Test incrementing cache misses counter."""
        stats = ParserStatistics()

        stats.increment_cache_miss()
        assert stats.cache_misses == 1

        stats.increment_cache_miss()
        assert stats.cache_misses == 2

    def test_thread_safety(self) -> None:
        """Test thread safety of ParserStatistics."""
        stats = ParserStatistics()
        errors = []

        def increment_processed():
            """Increment items processed counter in a loop."""
            try:
                for _ in range(50):
                    stats.increment_items_processed()
            except Exception as e:
                errors.append(e)

        def increment_successes():
            """Increment successes counter in a loop."""
            try:
                for _ in range(50):
                    stats.increment_successes()
            except Exception as e:
                errors.append(e)

        def increment_failures():
            """Increment failures counter in a loop."""
            try:
                for _ in range(50):
                    stats.increment_failures()
            except Exception as e:
                errors.append(e)

        def increment_cache_hits():
            """Increment cache hits counter in a loop."""
            try:
                for _ in range(50):
                    stats.increment_cache_hit()
            except Exception as e:
                errors.append(e)

        def increment_cache_misses():
            """Increment cache misses counter in a loop."""
            try:
                for _ in range(50):
                    stats.increment_cache_miss()
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for _ in range(2):
            threads.append(threading.Thread(target=increment_processed))
            threads.append(threading.Thread(target=increment_successes))
            threads.append(threading.Thread(target=increment_failures))
            threads.append(threading.Thread(target=increment_cache_hits))
            threads.append(threading.Thread(target=increment_cache_misses))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert not errors, f"Errors occurred: {errors}"

        # Verify final counts
        assert stats.items_processed == 100  # 2 threads * 50 increments
        assert stats.successes == 100  # 2 threads * 50 increments
        assert stats.failures == 100  # 2 threads * 50 increments
        assert stats.cache_hits == 100  # 2 threads * 50 increments
        assert stats.cache_misses == 100  # 2 threads * 50 increments
