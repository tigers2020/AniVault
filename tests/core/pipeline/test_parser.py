"""Unit tests for ParserWorker and ParserWorkerPool classes.

This module contains comprehensive tests for the parser worker threads
and worker pool that process files in the pipeline.
"""

import os
import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

from anivault.core.pipeline.parser import ParserWorker, ParserWorkerPool
from anivault.core.pipeline.utils import BoundedQueue, ParserStatistics


class TestParserWorker:
    """Test cases for ParserWorker class."""

    def test_init_with_valid_parameters(self) -> None:
        """Test ParserWorker initialization with valid parameters."""
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()
        worker_id = "test_worker"

        worker = ParserWorker(input_queue, output_queue, stats, cache, worker_id)

        assert worker.input_queue == input_queue
        assert worker.output_queue == output_queue
        assert worker.stats == stats
        assert worker.cache == cache
        assert worker.worker_id == worker_id
        assert not worker._stop_event.is_set()

    def test_init_without_worker_id(self) -> None:
        """Test ParserWorker initialization without worker_id."""
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        worker = ParserWorker(input_queue, output_queue, stats, cache)

        assert worker.worker_id.startswith("worker_")
        assert worker.worker_id != "worker_"

    def test_parse_file_success(self) -> None:
        """Test _parse_file method with successful file parsing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_video.mp4"
            test_file.touch()

            input_queue = Mock(spec=BoundedQueue)
            output_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ParserStatistics)
            cache = Mock()

            worker = ParserWorker(
                input_queue, output_queue, stats, cache, "test_worker"
            )

            result = worker._parse_file(test_file)

            assert result["file_path"] == str(test_file)
            assert result["file_name"] == "test_video.mp4"
            assert result["file_extension"] == ".mp4"
            assert result["file_size"] == 0
            assert result["worker_id"] == "test_worker"
            assert result["status"] == "success"
            assert "modified_time" in result
            assert "created_time" in result

    def test_parse_file_nonexistent(self) -> None:
        """Test _parse_file method with non-existent file."""
        nonexistent_file = Path("/nonexistent/file.mp4")

        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        worker = ParserWorker(input_queue, output_queue, stats, cache, "test_worker")

        result = worker._parse_file(nonexistent_file)

        assert result["file_path"] == str(nonexistent_file)
        assert result["file_name"] == "file.mp4"
        assert result["worker_id"] == "test_worker"
        assert result["status"] == "error"
        assert "error" in result

    def test_process_file_success(self) -> None:
        """Test _process_file method with successful processing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_video.mp4"
            test_file.touch()

            input_queue = Mock(spec=BoundedQueue)
            output_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ParserStatistics)
            cache = Mock()
            cache.get.return_value = None  # Cache miss
            cache.set.return_value = None

            worker = ParserWorker(
                input_queue, output_queue, stats, cache, "test_worker"
            )

            worker._process_file(test_file)

            # Verify statistics were updated
            stats.increment_items_processed.assert_called_once()
            stats.increment_successes.assert_called_once()
            stats.increment_failures.assert_not_called()

            # Verify output queue was called
            output_queue.put.assert_called_once()

            # Verify task was marked as done
            input_queue.task_done.assert_called_once()

            # Verify cache was called
            cache.get.assert_called_once_with(str(test_file))
            cache.set.assert_called_once()

    def test_process_file_with_cache_hit(self) -> None:
        """Test _process_file method with cache hit."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test_video.mp4"
            test_file.touch()

            # Mock cached result
            cached_result = {
                "file_path": str(test_file),
                "file_name": "test_video.mp4",
                "status": "success",
                "cached": True,
            }

            input_queue = Mock(spec=BoundedQueue)
            output_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ParserStatistics)
            cache = Mock()
            cache.get.return_value = cached_result  # Cache hit

            worker = ParserWorker(
                input_queue, output_queue, stats, cache, "test_worker"
            )

            worker._process_file(test_file)

            # Verify statistics were updated
            stats.increment_items_processed.assert_called_once()
            stats.increment_cache_hit.assert_called_once()
            stats.increment_cache_miss.assert_not_called()
            stats.increment_successes.assert_called_once()
            stats.increment_failures.assert_not_called()

            # Verify output queue was called with cached result
            output_queue.put.assert_called_once_with(cached_result)

            # Verify task was marked as done
            input_queue.task_done.assert_called_once()

            # Verify cache was called but set was not (since it was a hit)
            cache.get.assert_called_once_with(str(test_file))
            cache.set.assert_not_called()

    def test_process_file_failure(self) -> None:
        """Test _process_file method with processing failure."""
        with patch.object(
            ParserWorker, "_parse_file", side_effect=Exception("Parse error")
        ):
            input_queue = Mock(spec=BoundedQueue)
            output_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ParserStatistics)
            cache = Mock()
            cache.get.return_value = None  # Cache miss

            worker = ParserWorker(
                input_queue, output_queue, stats, cache, "test_worker"
            )

            worker._process_file(Path("/test/file.mp4"))

            # Verify statistics were updated
            stats.increment_items_processed.assert_called_once()
            stats.increment_failures.assert_called_once()
            stats.increment_successes.assert_not_called()

            # Verify output queue was not called
            output_queue.put.assert_not_called()

            # Verify task was marked as done
            input_queue.task_done.assert_called_once()

    def test_run_with_sentinel_value(self) -> None:
        """Test run method stops when sentinel value is received."""
        input_queue = Mock(spec=BoundedQueue)
        input_queue.get.side_effect = [Path("/test/file.mp4"), None]  # Sentinel value
        input_queue.task_done = Mock()  # Add task_done method
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)

        worker = ParserWorker(input_queue, output_queue, stats, "test_worker")

        # Start worker in a separate thread
        worker_thread = threading.Thread(target=worker.run)
        worker_thread.start()
        worker_thread.join(timeout=5.0)

        # Verify worker stopped gracefully
        assert not worker_thread.is_alive()

    def test_run_with_timeout(self) -> None:
        """Test run method handles timeout gracefully."""
        input_queue = Mock(spec=BoundedQueue)
        input_queue.get.side_effect = Exception("timeout")
        input_queue.task_done = Mock()  # Add task_done method
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)

        worker = ParserWorker(input_queue, output_queue, stats, "test_worker")

        # Start worker and stop it quickly
        worker_thread = threading.Thread(target=worker.run)
        worker_thread.start()
        time.sleep(0.1)
        worker.stop()
        worker_thread.join(timeout=1.0)

        # Verify worker stopped
        assert not worker_thread.is_alive()

    def test_stop_sets_stop_event(self) -> None:
        """Test stop method sets the stop event."""
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        worker = ParserWorker(input_queue, output_queue, stats, cache, "test_worker")

        assert not worker._stop_event.is_set()
        worker.stop()
        assert worker._stop_event.is_set()


class TestParserWorkerPool:
    """Test cases for ParserWorkerPool class."""

    def test_init_with_valid_parameters(self) -> None:
        """Test ParserWorkerPool initialization with valid parameters."""
        num_workers = 3
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)

        assert pool.num_workers == num_workers
        assert pool.input_queue == input_queue
        assert pool.output_queue == output_queue
        assert pool.stats == stats
        assert pool.cache == cache
        assert pool.workers == []
        assert not pool._started

    def test_start_creates_workers(self) -> None:
        """Test start method creates and starts worker threads."""
        print("Starting test_start_creates_workers")
        num_workers = 3
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)
        print("Created ParserWorkerPool")

        # Mock ParserWorker to avoid actual threading
        with patch("anivault.core.pipeline.parser.ParserWorker") as mock_worker_class:
            # Create different mock workers for each call
            mock_workers = []
            for i in range(num_workers):
                mock_worker = Mock(spec=ParserWorker)
                mock_worker.worker_id = f"worker_{i}"
                mock_worker.is_alive.return_value = True
                mock_workers.append(mock_worker)

            mock_worker_class.side_effect = mock_workers

            pool.start()
            print("Started pool")

            assert pool._started
            assert len(pool.workers) == num_workers
            print(f"Verified {num_workers} workers created")

            # Verify all workers are started
            for i, worker in enumerate(pool.workers):
                assert worker.worker_id == f"worker_{i}"
                assert worker.is_alive()
            print("Verified all workers are alive")
        print("test_start_creates_workers completed successfully")

    def test_start_already_started_raises_error(self) -> None:
        """Test start method raises error if already started."""
        print("Starting test_start_already_started_raises_error")
        num_workers = 2
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)
        print("Created ParserWorkerPool")

        # Mock ParserWorker to avoid actual threading
        with patch("anivault.core.pipeline.parser.ParserWorker") as mock_worker_class:
            mock_worker = Mock(spec=ParserWorker)
            mock_worker_class.return_value = mock_worker

            pool.start()
            print("Started pool once")

            with pytest.raises(RuntimeError, match="already been started"):
                pool.start()
            print("Verified error raised on second start")
        print("test_start_already_started_raises_error completed successfully")

    def test_join_not_started_raises_error(self) -> None:
        """Test join method raises error if not started."""
        num_workers = 2
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)

        with pytest.raises(RuntimeError, match="not been started"):
            pool.join()

    def test_join_waits_for_workers(self) -> None:
        """Test join method waits for all workers to complete."""
        print("Starting test_join_waits_for_workers")
        num_workers = 2
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)
        print("Created ParserWorkerPool")

        # Mock workers with proper join behavior
        worker1 = Mock(spec=ParserWorker)
        worker1.is_alive.return_value = False
        worker1.join.return_value = None

        worker2 = Mock(spec=ParserWorker)
        worker2.is_alive.return_value = False
        worker2.join.return_value = None

        pool.workers = [worker1, worker2]
        pool._started = True
        print("Mocked workers and set started=True")

        # Test join
        print("Calling join with timeout")
        pool.join(timeout=5.0)
        print("Join completed")

        # Verify workers were joined
        worker1.join.assert_called_once_with(timeout=5.0)
        worker2.join.assert_called_once_with(timeout=5.0)
        print("test_join_waits_for_workers completed successfully")

    def test_stop_stops_all_workers(self) -> None:
        """Test stop method stops all workers."""
        print("Starting test_stop_stops_all_workers")
        num_workers = 3
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)

        # Mock workers with stop method
        workers = []
        for i in range(num_workers):
            worker = Mock(spec=ParserWorker)
            worker._stop_event = Mock()
            worker._stop_event.is_set.return_value = True
            workers.append(worker)

        pool.workers = workers
        print("Mocked workers")

        # Stop all workers
        pool.stop()
        print("Called stop")

        # Verify all workers are stopped
        for i, worker in enumerate(pool.workers):
            print(f"Checking worker {i} stop event")
            worker.stop.assert_called_once()
        print("test_stop_stops_all_workers completed successfully")

    def test_is_alive_with_live_workers(self) -> None:
        """Test is_alive method with live workers."""
        print("Starting test_is_alive_with_live_workers")
        num_workers = 2
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)

        # Mock workers with is_alive behavior
        worker1 = Mock(spec=ParserWorker)
        worker1.is_alive.return_value = True

        worker2 = Mock(spec=ParserWorker)
        worker2.is_alive.return_value = True

        pool.workers = [worker1, worker2]
        print("Mocked workers as alive")

        assert pool.is_alive()
        print("Verified pool is alive")

        # Mock workers as stopped
        worker1.is_alive.return_value = False
        worker2.is_alive.return_value = False
        print("Mocked workers as stopped")

        assert not pool.is_alive()
        print("Verified pool is not alive")
        print("test_is_alive_with_live_workers completed successfully")

    def test_get_worker_count(self) -> None:
        """Test get_worker_count method."""
        print("Starting test_get_worker_count")
        num_workers = 4
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)

        assert pool.get_worker_count() == 0
        print("Verified initial worker count is 0")

        # Mock workers
        workers = [Mock(spec=ParserWorker) for _ in range(num_workers)]
        pool.workers = workers
        print(f"Mocked {num_workers} workers")

        assert pool.get_worker_count() == num_workers
        print("Verified worker count after start")
        print("test_get_worker_count completed successfully")

    def test_get_alive_worker_count(self) -> None:
        """Test get_alive_worker_count method."""
        print("Starting test_get_alive_worker_count")
        num_workers = 3
        input_queue = Mock(spec=BoundedQueue)
        output_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ParserStatistics)
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)

        assert pool.get_alive_worker_count() == 0
        print("Verified initial alive worker count is 0")

        # Mock workers as alive
        workers = []
        for i in range(num_workers):
            worker = Mock(spec=ParserWorker)
            worker.is_alive.return_value = True
            workers.append(worker)

        pool.workers = workers
        print("Mocked workers as alive")
        assert pool.get_alive_worker_count() == num_workers
        print("Verified alive worker count")

        # Mock workers as stopped
        for worker in pool.workers:
            worker.is_alive.return_value = False
        print("Mocked workers as stopped")
        assert pool.get_alive_worker_count() == 0
        print("Verified stopped worker count")
        print("test_get_alive_worker_count completed successfully")

    def test_get_pool_status(self) -> None:
        """Test get_pool_status method."""
        num_workers = 2
        input_queue = Mock(spec=BoundedQueue)
        input_queue.qsize.return_value = 5
        output_queue = Mock(spec=BoundedQueue)
        output_queue.qsize.return_value = 3
        stats = Mock(spec=ParserStatistics)
        stats.items_processed = 10
        stats.successes = 8
        stats.failures = 2
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)

        status = pool.get_pool_status()

        assert status["num_workers"] == num_workers
        assert status["started"] == False
        assert status["alive_workers"] == 0
        assert status["total_workers"] == 0
        assert status["input_queue_size"] == 5
        assert status["output_queue_size"] == 3
        assert status["items_processed"] == 10
        assert status["successes"] == 8
        assert status["failures"] == 2

    def test_integration_with_real_queues(self) -> None:
        """Test integration with real BoundedQueue instances."""
        print("Starting test_integration_with_real_queues")
        num_workers = 1  # Reduce to 1 worker to avoid complexity
        input_queue = BoundedQueue(maxsize=10)
        output_queue = BoundedQueue(maxsize=10)
        stats = ParserStatistics()
        cache = Mock()
        cache.get.return_value = None  # Always cache miss for integration test
        cache.set.return_value = None

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)
        print("Created pool with real queues")

        # Add some test files to input queue
        with tempfile.TemporaryDirectory() as temp_dir:
            test_files = []
            for i in range(2):  # Reduce to 2 files
                test_file = Path(temp_dir) / f"test_{i}.mp4"
                test_file.touch()
                test_files.append(test_file)
                input_queue.put(test_file)
                print(f"Added test file {i}")

            # Add sentinel value
            input_queue.put(None)
            print("Added sentinel value")

            # Start pool
            pool.start()
            print("Started pool")

            # Wait for processing with shorter timeout
            start_time = time.time()
            while stats.items_processed < 2 and time.time() - start_time < 2.0:
                time.sleep(0.1)
            print(f"Processing completed, items_processed: {stats.items_processed}")

            # Stop pool
            pool.stop()
            print("Stopped pool")
            pool.join(timeout=1.0)
            print("Joined pool")

            # Verify results
            assert stats.items_processed == 2
            assert stats.successes == 2
            assert stats.failures == 0
            print("Verified statistics")

            # Verify output queue has results
            results = []
            while not output_queue.empty():
                results.append(output_queue.get())

            assert len(results) == 2
            for result in results:
                assert result["status"] == "success"
                assert "file_path" in result
                assert "worker_id" in result
            print("Verified output results")
        print("test_integration_with_real_queues completed successfully")

    def test_error_handling_in_workers(self) -> None:
        """Test error handling when workers encounter errors."""
        print("Starting test_error_handling_in_workers")
        num_workers = 1
        input_queue = BoundedQueue(maxsize=10)
        output_queue = BoundedQueue(maxsize=10)
        stats = ParserStatistics()
        cache = Mock()

        pool = ParserWorkerPool(num_workers, input_queue, output_queue, stats, cache)
        print("Created pool")

        # Add a problematic file path
        input_queue.put(Path("/nonexistent/file.mp4"))
        input_queue.put(None)  # Sentinel value
        print("Added problematic file and sentinel")

        # Start pool
        pool.start()
        print("Started pool")

        # Wait for processing with shorter timeout
        start_time = time.time()
        while stats.items_processed < 1 and time.time() - start_time < 2.0:
            time.sleep(0.1)
        print(f"Processing completed, items_processed: {stats.items_processed}")

        # Stop pool
        pool.stop()
        print("Stopped pool")
        pool.join(timeout=1.0)
        print("Joined pool")

        # Verify error was handled
        assert stats.items_processed == 1
        assert stats.failures == 1
        assert stats.successes == 0
        print("Verified error handling")
        print("test_error_handling_in_workers completed successfully")
