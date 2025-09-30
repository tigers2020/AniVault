"""
Tests for BoundedQueue implementation.
"""

import pytest
import threading
import time
from typing import List
from src.anivault.core.bounded_queue import BoundedQueue, QueueStats


class TestBoundedQueue:
    """Test cases for BoundedQueue."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.queue = BoundedQueue(capacity=5)

    def teardown_method(self) -> None:
        """Clean up after tests."""
        if hasattr(self, "queue"):
            self.queue.clear()

    def test_initialization(self) -> None:
        """Test queue initialization."""
        assert self.queue.capacity() == 5
        assert self.queue.size() == 0
        assert self.queue.is_empty()
        assert not self.queue.is_full()

    def test_put_and_get_basic(self) -> None:
        """Test basic put and get operations."""
        # Test put
        assert self.queue.put("item1") is True
        assert self.queue.size() == 1
        assert not self.queue.is_empty()

        # Test get
        item = self.queue.get()
        assert item == "item1"
        assert self.queue.size() == 0
        assert self.queue.is_empty()

    def test_put_nowait_and_get_nowait(self) -> None:
        """Test non-blocking operations."""
        # Test put_nowait
        assert self.queue.put_nowait("item1") is True
        assert self.queue.size() == 1

        # Test get_nowait
        item = self.queue.get_nowait()
        assert item == "item1"
        assert self.queue.size() == 0

    def test_capacity_limit(self) -> None:
        """Test capacity limits."""
        # Fill queue to capacity
        for i in range(5):
            assert self.queue.put_nowait(f"item{i}") is True

        assert self.queue.is_full()
        assert self.queue.size() == 5

        # Try to add one more item
        assert self.queue.put_nowait("overflow") is False
        assert self.queue.size() == 5

    def test_empty_queue_operations(self) -> None:
        """Test operations on empty queue."""
        # get_nowait on empty queue
        assert self.queue.get_nowait() is None

        # peek on empty queue
        assert self.queue.peek() is None

    def test_peek_operation(self) -> None:
        """Test peek operation."""
        self.queue.put("item1")
        self.queue.put("item2")

        # Peek should return first item without removing it
        assert self.queue.peek() == "item1"
        assert self.queue.size() == 2

        # Get should return the same item and remove it
        item = self.queue.get()
        assert item == "item1"
        assert self.queue.size() == 1

    def test_clear_operation(self) -> None:
        """Test clear operation."""
        # Add some items
        for i in range(3):
            self.queue.put_nowait(f"item{i}")

        assert self.queue.size() == 3

        # Clear queue
        self.queue.clear()
        assert self.queue.size() == 0
        assert self.queue.is_empty()

    def test_statistics(self) -> None:
        """Test queue statistics."""
        # Add and remove items
        for i in range(3):
            self.queue.put_nowait(f"item{i}")

        for i in range(2):
            self.queue.get_nowait()

        stats = self.queue.get_stats()
        assert stats.size == 1
        assert stats.capacity == 5
        assert stats.total_added == 3
        assert stats.total_removed == 2
        assert stats.max_size_reached == 3

    def test_to_list(self) -> None:
        """Test converting queue to list."""
        items = ["item1", "item2", "item3"]
        for item in items:
            self.queue.put_nowait(item)

        queue_list = self.queue.to_list()
        assert queue_list == items

    def test_iterator(self) -> None:
        """Test queue iteration."""
        items = ["item1", "item2", "item3"]
        for item in items:
            self.queue.put_nowait(item)

        # Test iteration
        for i, item in enumerate(self.queue):
            assert item == items[i]

    def test_boolean_conversion(self) -> None:
        """Test boolean conversion."""
        assert not bool(self.queue)  # Empty queue is falsy

        self.queue.put_nowait("item")
        assert bool(self.queue)  # Non-empty queue is truthy

    def test_string_representation(self) -> None:
        """Test string representation."""
        repr_str = repr(self.queue)
        assert "BoundedQueue" in repr_str
        assert "size=0" in repr_str
        assert "capacity=5" in repr_str

    def test_len_function(self) -> None:
        """Test len function."""
        assert len(self.queue) == 0

        self.queue.put_nowait("item")
        assert len(self.queue) == 1

    def test_none_value_handling(self) -> None:
        """Test handling of None values."""
        with pytest.raises(ValueError):
            self.queue.put(None)

        with pytest.raises(ValueError):
            self.queue.put_nowait(None)

    def test_timeout_operations(self) -> None:
        """Test timeout operations."""
        # Test put with timeout on full queue
        # Fill queue to capacity
        for i in range(5):
            self.queue.put_nowait(f"item{i}")

        # Try to put with short timeout
        start_time = time.time()
        result = self.queue.put("timeout_item", timeout=0.1)
        elapsed = time.time() - start_time

        assert result is False
        assert elapsed >= 0.1

        # Test get with timeout on empty queue
        self.queue.clear()
        start_time = time.time()
        result = self.queue.get(timeout=0.1)
        elapsed = time.time() - start_time

        assert result is None
        assert elapsed >= 0.1

    def test_thread_safety(self) -> None:
        """Test thread safety with multiple threads."""
        results: list[str] = []
        errors: list[Exception] = []

        def producer():
            """Producer thread."""
            try:
                for i in range(10):
                    self.queue.put(f"item{i}")
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        def consumer():
            """Consumer thread."""
            try:
                for _ in range(10):
                    item = self.queue.get()
                    if item:
                        results.append(item)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        # Start threads
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)

        producer_thread.start()
        consumer_thread.start()

        # Wait for completion
        producer_thread.join()
        consumer_thread.join()

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        assert all(f"item{i}" in results for i in range(10))

    def test_blocking_behavior_configuration(self) -> None:
        """Test different blocking behavior configurations."""
        # Test non-blocking queue
        non_blocking_queue = BoundedQueue(
            capacity=2, block_on_full=False, block_on_empty=False
        )

        # Fill to capacity
        assert non_blocking_queue.put_nowait("item1") is True
        assert non_blocking_queue.put_nowait("item2") is True

        # Try to add more - should fail immediately
        assert non_blocking_queue.put("item3") is False

        # Try to get from empty queue - should return None immediately
        non_blocking_queue.clear()
        assert non_blocking_queue.get() is None

    def test_large_capacity(self) -> None:
        """Test queue with large capacity."""
        large_queue = BoundedQueue(capacity=10000)

        # Add many items
        for i in range(1000):
            assert large_queue.put_nowait(f"item{i}") is True

        assert large_queue.size() == 1000
        assert not large_queue.is_full()

        # Remove all items
        for i in range(1000):
            item = large_queue.get_nowait()
            assert item == f"item{i}"

        assert large_queue.is_empty()

    def test_concurrent_access(self) -> None:
        """Test concurrent access from multiple threads."""
        num_threads = 5
        items_per_thread = 20
        all_results: list[str] = []

        def worker(thread_id: int):
            """Worker thread."""
            for i in range(items_per_thread):
                item = f"thread{thread_id}_item{i}"
                self.queue.put(item)
                time.sleep(0.001)

        def collector():
            """Collector thread."""
            for _ in range(num_threads * items_per_thread):
                item = self.queue.get()
                if item:
                    all_results.append(item)
                time.sleep(0.001)

        # Start worker threads
        worker_threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(num_threads)
        ]

        # Start collector thread
        collector_thread = threading.Thread(target=collector)

        # Start all threads
        for thread in worker_threads:
            thread.start()
        collector_thread.start()

        # Wait for completion
        for thread in worker_threads:
            thread.join()
        collector_thread.join()

        # Verify all items were processed
        assert len(all_results) == num_threads * items_per_thread
        assert self.queue.is_empty()
