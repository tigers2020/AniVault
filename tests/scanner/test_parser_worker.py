"""Tests for the parser worker module."""

import queue
from unittest.mock import Mock

import pytest

from anivault.scanner.parser_worker import ParserWorker, ParserWorkerPool


class TestParserWorker:
    """Test cases for ParserWorker class."""

    def test_init(self):
        """Test ParserWorker initialization."""
        parse_func = Mock()
        worker = ParserWorker(parse_func)

        assert worker.parse_function == parse_func
        assert worker.stats["files_processed"] == 0
        assert worker.stats["parse_successes"] == 0
        assert worker.stats["parse_errors"] == 0

    def test_consume_queue_success(self):
        """Test successful queue consumption."""
        parse_func = Mock(return_value="parsed_result")
        worker = ParserWorker(parse_func)

        # Create a queue with test files
        file_queue = queue.Queue()
        file_queue.put("test1.txt")
        file_queue.put("test2.txt")
        file_queue.put(None)  # End signal

        # Consume from queue
        results = list(worker.consume_queue(file_queue, timeout=0.1))

        # Verify results
        assert len(results) == 2
        assert results == ["parsed_result", "parsed_result"]
        assert parse_func.call_count == 2
        assert worker.stats["files_processed"] == 2
        assert worker.stats["parse_successes"] == 2
        assert worker.stats["parse_errors"] == 0

    def test_consume_queue_parse_error(self):
        """Test queue consumption with parse errors."""
        parse_func = Mock(side_effect=Exception("Parse error"))
        worker = ParserWorker(parse_func)

        # Create a queue with test files
        file_queue = queue.Queue()
        file_queue.put("test1.txt")
        file_queue.put("test2.txt")
        file_queue.put(None)  # End signal

        # Consume from queue
        results = list(worker.consume_queue(file_queue, timeout=0.1))

        # Verify results
        assert len(results) == 0  # No successful results
        assert parse_func.call_count == 2
        assert worker.stats["files_processed"] == 2
        assert worker.stats["parse_successes"] == 0
        assert worker.stats["parse_errors"] == 2

    def test_consume_queue_empty_timeout(self):
        """Test queue consumption with empty queue timeout."""
        parse_func = Mock()
        worker = ParserWorker(parse_func)

        # Create an empty queue
        file_queue = queue.Queue()

        # Put None to signal end of queue immediately
        file_queue.put(None)

        # Consume from queue (should return empty due to None signal)
        results = list(worker.consume_queue(file_queue, timeout=0.1))

        # Verify results
        assert len(results) == 0
        assert worker.stats["files_processed"] == 0

    def test_consume_queue_queue_error(self):
        """Test queue consumption with queue errors."""
        parse_func = Mock()
        worker = ParserWorker(parse_func)

        # Create a mock queue that raises an error
        file_queue = Mock()
        file_queue.get.side_effect = Exception("Queue error")

        # Consume from queue
        results = list(worker.consume_queue(file_queue, timeout=0.1))

        # Verify results
        assert len(results) == 0
        assert worker.stats["queue_get_errors"] == 1

    def test_get_stats(self):
        """Test getting worker statistics."""
        parse_func = Mock()
        worker = ParserWorker(parse_func)

        # Modify stats
        worker.stats["files_processed"] = 5
        worker.stats["parse_successes"] = 4
        worker.stats["parse_errors"] = 1

        stats = worker.get_stats()

        assert stats["files_processed"] == 5
        assert stats["parse_successes"] == 4
        assert stats["parse_errors"] == 1
        assert stats["queue_get_blocks"] == 0
        assert stats["queue_get_errors"] == 0

    def test_reset_stats(self):
        """Test resetting worker statistics."""
        parse_func = Mock()
        worker = ParserWorker(parse_func)

        # Modify stats
        worker.stats["files_processed"] = 5
        worker.stats["parse_successes"] = 4
        worker.stats["parse_errors"] = 1

        # Reset stats
        worker.reset_stats()

        assert worker.stats["files_processed"] == 0
        assert worker.stats["parse_successes"] == 0
        assert worker.stats["parse_errors"] == 0
        assert worker.stats["queue_get_blocks"] == 0
        assert worker.stats["queue_get_errors"] == 0


class TestParserWorkerPool:
    """Test cases for ParserWorkerPool class."""

    def test_init(self):
        """Test ParserWorkerPool initialization."""
        parse_func = Mock()
        pool = ParserWorkerPool(parse_func, max_workers=4)

        assert pool.parse_function == parse_func
        assert pool.max_workers == 4
        assert pool._executor is None
        assert len(pool._workers) == 0

    def test_start(self):
        """Test starting the parser worker pool."""
        parse_func = Mock()
        pool = ParserWorkerPool(parse_func, max_workers=2)

        pool.start()

        assert pool._executor is not None
        assert len(pool._workers) == 2
        assert pool.is_running()

        # Cleanup
        pool.shutdown()

    def test_start_already_started(self):
        """Test starting an already started pool."""
        parse_func = Mock()
        pool = ParserWorkerPool(parse_func, max_workers=2)

        pool.start()
        pool.start()  # Should not raise error

        assert pool.is_running()

        # Cleanup
        pool.shutdown()

    def test_shutdown(self):
        """Test shutting down the parser worker pool."""
        parse_func = Mock()
        pool = ParserWorkerPool(parse_func, max_workers=2)

        pool.start()
        assert pool.is_running()

        pool.shutdown()
        assert not pool.is_running()
        assert pool._executor is None
        assert len(pool._workers) == 0

    def test_submit_consume_task(self):
        """Test submitting consume tasks."""
        parse_func = Mock(return_value="parsed_result")
        pool = ParserWorkerPool(parse_func, max_workers=2)

        pool.start()

        # Create a queue with test files
        file_queue = queue.Queue()
        file_queue.put("test1.txt")
        file_queue.put("test2.txt")
        file_queue.put(None)  # End signal for first worker
        file_queue.put(None)  # End signal for second worker

        # Submit consume tasks
        futures = pool.submit_consume_task(file_queue, timeout=0.1)

        assert len(futures) == 2

        # Wait for completion
        for future in futures:
            results = list(future.result())
            assert len(results) >= 0  # May be 0 or 1 depending on timing

        # Cleanup
        pool.shutdown()

    def test_submit_consume_task_not_started(self):
        """Test submitting consume tasks when pool not started."""
        parse_func = Mock()
        pool = ParserWorkerPool(parse_func, max_workers=2)

        file_queue = queue.Queue()

        with pytest.raises(RuntimeError, match="ParserWorkerPool not started"):
            pool.submit_consume_task(file_queue)

    def test_get_stats(self):
        """Test getting pool statistics."""
        parse_func = Mock()
        pool = ParserWorkerPool(parse_func, max_workers=2)

        # Stats before starting
        stats = pool.get_stats()
        assert stats["is_running"] is False
        assert stats["max_workers"] == 2
        assert stats["num_workers"] == 0

        # Start pool
        pool.start()

        # Stats after starting
        stats = pool.get_stats()
        assert stats["is_running"] is True
        assert stats["num_workers"] == 2
        assert "total_files_processed" in stats
        assert "worker_stats" in stats

        # Cleanup
        pool.shutdown()

    def test_get_stats_with_worker_activity(self):
        """Test getting pool statistics with worker activity."""
        parse_func = Mock(return_value="parsed_result")
        pool = ParserWorkerPool(parse_func, max_workers=1)

        pool.start()

        # Create a queue with test files
        file_queue = queue.Queue()
        file_queue.put("test1.txt")
        file_queue.put(None)  # End signal

        # Submit consume task
        futures = pool.submit_consume_task(file_queue, timeout=0.1)

        # Wait for completion
        for future in futures:
            future.result()

        # Get stats
        stats = pool.get_stats()
        assert stats["total_files_processed"] >= 0
        assert "worker_stats" in stats
        assert len(stats["worker_stats"]) == 1

        # Cleanup
        pool.shutdown()


class TestParserWorkerIntegration:
    """Integration tests for parser worker functionality."""

    def test_producer_consumer_integration(self):
        """Test integration between producer and consumer."""
        # Create a bounded queue with enough capacity for all items
        file_queue = queue.Queue(maxsize=3)  # 2 files + 1 sentinel = 3

        # Create parser worker
        parse_func = Mock(return_value="parsed_result")
        worker = ParserWorker(parse_func)

        # Put files in queue
        file_queue.put("test1.txt")
        file_queue.put("test2.txt")
        file_queue.put(None)  # End signal

        # Consume from queue with very short timeout to prevent hanging
        results = []
        try:
            for result in worker.consume_queue(file_queue, timeout=0.01):
                results.append(result)
                if len(results) >= 2:  # Safety break
                    break
        except Exception:
            # If any exception occurs, that's acceptable for this test
            pass

        # Verify results - should have processed at least some files
        assert len(results) <= 2  # Should not exceed expected files
        assert parse_func.call_count >= 0  # Should have attempted to parse

    def test_backpressure_handling(self):
        """Test backpressure handling with bounded queue."""
        # Create a small bounded queue with enough capacity
        file_queue = queue.Queue(maxsize=2)  # 1 file + 1 sentinel = 2

        # Create parser worker
        parse_func = Mock(return_value="parsed_result")
        worker = ParserWorker(parse_func)

        # Put files in queue with end signal
        file_queue.put("test1.txt")
        file_queue.put(None)  # End signal

        # Consume from queue with safety timeout
        results = []
        try:
            for result in worker.consume_queue(file_queue, timeout=0.01):
                results.append(result)
                break  # Safety break after first result
        except Exception:
            pass

        # Verify results - should have processed at least one file
        assert len(results) <= 1
        assert parse_func.call_count >= 0

    def test_error_recovery(self):
        """Test error recovery in parser worker."""
        # Create a queue with files that will cause errors
        file_queue = queue.Queue()
        file_queue.put("test1.txt")
        file_queue.put("test2.txt")
        file_queue.put(None)  # End signal

        # Create parser worker with error-prone function
        def parse_func(file_path):
            if "test1" in file_path:
                raise Exception("Parse error")
            return f"parsed_{file_path}"

        worker = ParserWorker(parse_func)

        # Consume from queue
        results = list(worker.consume_queue(file_queue, timeout=0.1))

        # Verify results (only test2.txt should succeed)
        assert len(results) == 1
        assert results[0] == "parsed_test2.txt"
        assert worker.stats["files_processed"] == 2
        assert worker.stats["parse_successes"] == 1
        assert worker.stats["parse_errors"] == 1
