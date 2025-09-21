"""Tests for the file processing queue system."""

import os
import sys
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from core.file_processing_queue import (
    FileProcessingQueue,
    QueueConfig,
    QueueStatus,
    QueueStats
)


class TestFileProcessingQueue:
    """Test cases for FileProcessingQueue."""

    def test_queue_initialization(self):
        """Test queue initialization with default and custom config."""
        # Test with default config
        queue = FileProcessingQueue()
        assert queue.get_status() == QueueStatus.IDLE
        assert queue.is_empty()
        assert queue.queue_size() == 0

        # Test with custom config
        config = QueueConfig(max_queue_size=500, batch_size=5)
        queue = FileProcessingQueue(config=config, executor_type="process")
        assert queue.get_status() == QueueStatus.IDLE
        assert queue.config.max_queue_size == 500
        assert queue.config.batch_size == 5

    def test_add_items(self):
        """Test adding items to the queue."""
        queue = FileProcessingQueue()
        
        # Test adding single item
        items = ["item1", "item2", "item3"]
        added_count = queue.add_items(items)
        assert added_count == 3
        assert queue.queue_size() == 3
        
        # Test adding single item
        success = queue.add_item("item4")
        assert success is True
        assert queue.queue_size() == 4

    def test_add_items_when_full(self):
        """Test adding items when queue is full."""
        config = QueueConfig(max_queue_size=2)
        queue = FileProcessingQueue(config=config)
        
        # Fill queue
        items = ["item1", "item2"]
        added_count = queue.add_items(items)
        assert added_count == 2
        assert queue.queue_size() == 2
        
        # Try to add more items (should fail due to full queue)
        items = ["item3", "item4", "item5"]
        added_count = queue.add_items(items)
        assert added_count == 0  # No items added due to full queue
        assert queue.queue_size() == 2

    def test_add_items_when_stopped(self):
        """Test adding items when queue is stopped."""
        queue = FileProcessingQueue()
        queue.stop_processing()
        
        # Should raise RuntimeError when trying to add items to stopped queue
        with pytest.raises(RuntimeError):
            queue.add_items(["item1"])

    def test_thread_executor_processing(self):
        """Test processing with ThreadPoolExecutor."""
        queue = FileProcessingQueue(executor_type="thread", max_workers=2)
        
        # Mock worker function
        def worker_function(item):
            return f"processed_{item}"
        
        # Add items
        items = ["item1", "item2", "item3"]
        queue.add_items(items)
        
        # Start processing
        queue.start_processing(worker_function)
        
        # Check results
        stats = queue.get_stats()
        assert stats.total_items == 3
        assert stats.processed_items == 3
        assert stats.failed_items == 0
        assert queue.get_status() == QueueStatus.STOPPED

    def test_process_executor_processing(self):
        """Test processing with ProcessPoolExecutor."""
        # Skip if on Windows due to multiprocessing issues in tests
        if os.name == 'nt':
            pytest.skip("Skipping ProcessPoolExecutor test on Windows")
        
        queue = FileProcessingQueue(executor_type="process", max_workers=2)
        
        # Mock worker function (must be at module level for ProcessPoolExecutor)
        def worker_function(item):
            return f"processed_{item}"
        
        # Add items
        items = ["item1", "item2", "item3"]
        queue.add_items(items)
        
        # Start processing
        queue.start_processing(worker_function)
        
        # Check results
        stats = queue.get_stats()
        assert stats.total_items == 3
        assert stats.processed_items == 3
        assert stats.failed_items == 0
        assert queue.get_status() == QueueStatus.STOPPED

    def test_batch_processing(self):
        """Test batch processing functionality."""
        config = QueueConfig(batch_size=2, timeout_seconds=0.2)  # Very short timeout
        queue = FileProcessingQueue(config=config, executor_type="thread")

        # Mock worker function that processes batches
        def worker_function(batch):
            return [f"processed_{item}" for item in batch]

        # Add items
        items = ["item1", "item2", "item3", "item4", "item5"]
        queue.add_items(items)

        # Start batch processing
        queue.start_processing(worker_function, batch_processing=True)

        # Check results
        stats = queue.get_stats()
        assert stats.total_items == 5
        assert stats.processed_items == 5
        assert stats.failed_items == 0
        assert queue.get_status() == QueueStatus.STOPPED

    def test_progress_callback(self):
        """Test progress callback functionality."""
        callback_calls = []
        
        def progress_callback(processed, total, message):
            callback_calls.append((processed, total, message))
        
        config = QueueConfig(progress_callback=progress_callback)
        queue = FileProcessingQueue(config=config, executor_type="thread")
        
        # Mock worker function
        def worker_function(item):
            time.sleep(0.01)  # Small delay to ensure callback is called
            return f"processed_{item}"
        
        # Add items
        items = ["item1", "item2", "item3"]
        queue.add_items(items)
        
        # Start processing
        queue.start_processing(worker_function)
        
        # Check that callback was called
        assert len(callback_calls) > 0
        # Last callback should show completion
        assert callback_calls[-1][1] == 3  # total items

    def test_error_callback(self):
        """Test error callback functionality."""
        error_calls = []
        
        def error_callback(error, item):
            error_calls.append((error, item))
        
        config = QueueConfig(error_callback=error_callback)
        queue = FileProcessingQueue(config=config, executor_type="thread")
        
        # Mock worker function that raises an exception
        def worker_function(item):
            if item == "error_item":
                raise ValueError("Test error")
            return f"processed_{item}"
        
        # Add items including one that will cause an error
        items = ["item1", "error_item", "item2"]
        queue.add_items(items)
        
        # Start processing
        queue.start_processing(worker_function)
        
        # Check results
        stats = queue.get_stats()
        assert stats.total_items == 3
        assert stats.processed_items == 2  # Two successful items
        assert stats.failed_items == 1     # One failed item
        assert len(error_calls) == 1       # One error callback
        assert isinstance(error_calls[0][0], ValueError)

    def test_stop_processing(self):
        """Test stopping processing gracefully."""
        queue = FileProcessingQueue(executor_type="thread")
        
        # Mock worker function with delay
        def worker_function(item):
            time.sleep(0.1)  # Simulate work
            return f"processed_{item}"
        
        # Add items
        items = ["item1", "item2", "item3", "item4", "item5"]
        queue.add_items(items)
        
        # Start processing in a separate thread
        processing_thread = threading.Thread(
            target=queue.start_processing,
            args=(worker_function,)
        )
        processing_thread.start()
        
        # Wait a bit then stop
        time.sleep(0.05)
        queue.stop_processing(wait=True)
        
        # Wait for processing thread to finish
        processing_thread.join(timeout=2.0)
        
        # Check that processing was stopped
        assert queue.get_status() == QueueStatus.STOPPED

    def test_context_manager(self):
        """Test using queue as context manager."""
        with FileProcessingQueue(executor_type="thread") as queue:
            # Mock worker function
            def worker_function(item):
                return f"processed_{item}"
            
            # Add items
            items = ["item1", "item2"]
            queue.add_items(items)
            
            # Start processing
            queue.start_processing(worker_function)
            
            # Check results
            stats = queue.get_stats()
            assert stats.total_items == 2
            assert stats.processed_items == 2
        
        # Queue should be stopped after exiting context
        assert queue.get_status() == QueueStatus.STOPPED

    def test_queue_stats(self):
        """Test queue statistics calculation."""
        config = QueueConfig()
        queue = FileProcessingQueue(config=config, executor_type="thread")
        
        # Mock worker function
        def worker_function(item):
            return f"processed_{item}"
        
        # Add items
        items = ["item1", "item2", "item3"]
        queue.add_items(items)
        
        # Start processing
        queue.start_processing(worker_function)
        
        # Check statistics
        stats = queue.get_stats()
        assert stats.total_items == 3
        assert stats.processed_items == 3
        assert stats.failed_items == 0
        assert stats.success_rate == 100.0
        assert stats.processing_time > 0
        assert stats.items_per_second > 0

    def test_environment_variable_workers(self):
        """Test worker count from environment variables."""
        # This test would require setting environment variables
        # and is more of an integration test
        pass


# Module-level worker function for ProcessPoolExecutor tests
def _test_worker_function(item):
    """Test worker function for ProcessPoolExecutor."""
    return f"processed_{item}"


if __name__ == "__main__":
    pytest.main([__file__])
