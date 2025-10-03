"""Tests for refactored ResultCollector with SRP and structured error handling."""

import logging
import queue
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.core.pipeline.collector import (
    SENTINEL,
    ResultCollector,
    ResultCollectorPool,
)
from anivault.core.pipeline.utils import BoundedQueue
from anivault.shared.errors import ErrorCode, InfrastructureError


class TestResultCollectorRefactored(unittest.TestCase):
    """Test refactored ResultCollector with structured error handling."""

    def setup_method(self, method) -> None:
        """Set up test fixtures."""
        self.output_queue = BoundedQueue(maxsize=10)
        self.collector = ResultCollector(
            output_queue=self.output_queue, collector_id="test_collector"
        )

    def test_get_item_from_queue_success(self) -> None:
        """Test successful item retrieval from queue."""
        # Given
        test_item = {"status": "success", "data": "test"}
        self.output_queue.put(test_item)

        # When
        item = self.collector._get_item_from_queue(1.0)

        # Then
        assert item == test_item
        self.output_queue.task_done()

    def test_get_item_from_queue_empty(self) -> None:
        """Test item retrieval when queue is empty."""
        # When
        item = self.collector._get_item_from_queue(0.01)

        # Then
        assert item is None

    def test_handle_idle_state(self) -> None:
        """Test idle state handling."""
        # When
        new_idle_count = self.collector._handle_idle_state(5, 10, 0.01)

        # Then
        assert new_idle_count == 6

    def test_handle_sentinel_true(self) -> None:
        """Test sentinel handling when sentinel is received."""
        # When
        result = self.collector._handle_sentinel(SENTINEL)

        # Then
        assert result is True

    def test_handle_sentinel_false(self) -> None:
        """Test sentinel handling when normal item is received."""
        # Given
        normal_item = {"status": "success", "data": "test"}

        # When
        result = self.collector._handle_sentinel(normal_item)

        # Then
        assert result is False

    def test_store_result_with_error_handling_success(self) -> None:
        """Test successful result storage with error handling."""
        # Given
        test_result = {"status": "success", "data": "test"}

        # When
        self.collector._store_result_with_error_handling(test_result)

        # Then
        assert len(self.collector._results) == 1
        assert self.collector._results[0] == test_result

    def test_store_result_with_error_handling_failure(self) -> None:
        """Test result storage failure with structured error handling."""
        # Given
        test_result = {"status": "success", "data": "test"}

        # Mock _store_result to raise an exception
        with patch.object(
            self.collector, "_store_result", side_effect=Exception("Storage error")
        ):
            # When & Then
            with pytest.raises(InfrastructureError) as exc_info:
                self.collector._store_result_with_error_handling(test_result)

            assert exc_info.value.code == ErrorCode.COLLECTOR_ERROR
            assert "Failed to store result" in exc_info.value.message
            assert exc_info.value.context.operation == "store_result"

    def test_handle_queue_error_non_critical(self) -> None:
        """Test handling of non-critical queue errors."""
        # Given
        from anivault.shared.errors import ErrorContext

        context = ErrorContext(operation="test_operation")
        non_critical_error = ValueError("Non-critical error")

        # When - should not raise
        self.collector._handle_queue_error(non_critical_error, context)

        # Then - no exception should be raised

    def test_handle_queue_error_critical(self) -> None:
        """Test handling of critical queue errors."""
        # Given
        from anivault.shared.errors import ErrorContext

        context = ErrorContext(operation="test_operation")
        critical_error = OSError("Critical error")

        # When & Then
        with pytest.raises(InfrastructureError) as exc_info:
            self.collector._handle_queue_error(critical_error, context)

        assert exc_info.value.code == ErrorCode.QUEUE_OPERATION_ERROR
        assert "Critical queue error" in exc_info.value.message

    def test_poll_once_success(self) -> None:
        """Test successful poll_once operation."""
        # Given
        test_result = {"status": "success", "data": "test"}
        self.output_queue.put(test_result)

        # When
        result = self.collector.poll_once(1.0)

        # Then
        assert result is True
        assert len(self.collector._results) == 1
        assert self.collector._results[0] == test_result
        # task_done() is called inside _store_result_with_error_handling

    def test_poll_once_empty_queue(self) -> None:
        """Test poll_once when queue is empty."""
        # When
        result = self.collector.poll_once(0.01)

        # Then
        assert result is False
        assert len(self.collector._results) == 0

    def test_poll_once_sentinel(self) -> None:
        """Test poll_once when sentinel is received."""
        # Given
        self.output_queue.put(SENTINEL)

        # When
        result = self.collector.poll_once(1.0)

        # Then
        assert result is False
        # Give a moment for stop() to be processed
        import time

        time.sleep(0.01)
        assert self.collector.is_stopped()

    def test_poll_once_failure(self) -> None:
        """Test poll_once failure with structured error handling."""
        # Given - mock queue to raise exception
        mock_queue = Mock(spec=BoundedQueue)
        mock_queue.get.side_effect = RuntimeError("Queue error")
        self.collector.output_queue = mock_queue

        # When & Then
        with pytest.raises(InfrastructureError) as exc_info:
            self.collector.poll_once(1.0)

        assert exc_info.value.code == ErrorCode.COLLECTOR_ERROR
        assert "Poll once failed" in exc_info.value.message

    def test_run_success_with_results(self) -> None:
        """Test successful run with multiple results."""
        # Given
        test_results = [
            {"status": "success", "data": "test1"},
            {"status": "success", "data": "test2"},
            SENTINEL,
        ]

        for result in test_results:
            self.output_queue.put(result)

        # When
        self.collector.run(max_idle_loops=5, get_timeout=1.0)

        # Then
        assert len(self.collector._results) == 2
        assert self.collector._results[0]["data"] == "test1"
        assert self.collector._results[1]["data"] == "test2"
        assert self.collector.is_stopped()

        # Clean up
        for _ in range(3):
            try:
                self.output_queue.task_done()
            except ValueError:
                break

    def test_run_with_idle_timeout(self) -> None:
        """Test run with idle timeout."""
        # When - run with very low idle timeout
        self.collector.run(max_idle_loops=2, idle_sleep=0.01, get_timeout=0.01)

        # Then
        assert self.collector.is_stopped()

    def test_run_failure_with_error_handling(self) -> None:
        """Test run failure with structured error handling."""
        # Given - mock queue to raise critical error
        mock_queue = Mock(spec=BoundedQueue)
        mock_queue.get.side_effect = OSError("Critical queue error")
        self.collector.output_queue = mock_queue

        # When & Then
        with pytest.raises(InfrastructureError) as exc_info:
            self.collector.run(max_idle_loops=1, get_timeout=0.01)

        assert exc_info.value.code == ErrorCode.COLLECTOR_ERROR
        assert "Collector run failed" in exc_info.value.message

    def test_run_with_mixed_results_and_errors(self) -> None:
        """Test run with mixed successful results and recoverable errors."""
        # Given
        test_result = {"status": "success", "data": "test"}
        self.output_queue.put(test_result)

        # Mock queue to raise non-critical error after first item
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return test_result
            elif call_count == 2:
                raise ValueError("Non-critical error")
            else:
                return SENTINEL

        self.output_queue.get = mock_get

        # When
        self.collector.run(max_idle_loops=3, get_timeout=1.0)

        # Then
        assert len(self.collector._results) == 1
        assert self.collector._results[0]["data"] == "test"
        assert self.collector.is_stopped()

    def test_existing_functionality_preserved(self) -> None:
        """Test that existing functionality is preserved after refactoring."""
        # Test get_results
        test_result = {"status": "success", "data": "test"}
        self.collector._store_result(test_result)
        results = self.collector.get_results()
        assert results == [test_result]

        # Test get_result_count
        assert self.collector.get_result_count() == 1

        # Test get_successful_results
        successful = self.collector.get_successful_results()
        assert len(successful) == 1

        # Test get_failed_results
        failed_result = {"status": "error", "data": "failed"}
        self.collector._store_result(failed_result)
        failed = self.collector.get_failed_results()
        assert len(failed) == 1

        # Test clear_results
        self.collector.clear_results()
        assert self.collector.get_result_count() == 0


class TestResultCollectorPoolRefactored(unittest.TestCase):
    """Test ResultCollectorPool with refactored collectors."""

    def setup_method(self, method) -> None:
        """Set up test fixtures."""
        self.output_queue = BoundedQueue(maxsize=10)
        self.pool = ResultCollectorPool(
            output_queue=self.output_queue,
            num_collectors=2,
            collector_id_prefix="test_collector",
        )

    def teardown_method(self, method) -> None:
        """Clean up after each test."""
        if hasattr(self, "pool") and self.pool._started:
            try:
                self.pool.stop()
                # Wait for collectors to stop
                import time

                for _ in range(10):
                    if not self.pool.is_alive():
                        break
                    time.sleep(0.1)
            except Exception:
                pass  # Ignore cleanup errors

    def test_pool_initialization(self) -> None:
        """Test pool initialization."""
        assert self.pool.num_collectors == 2
        assert self.pool.collector_id_prefix == "test_collector"
        assert not self.pool._started
        assert len(self.pool.collectors) == 0

    def test_start_collectors(self) -> None:
        """Test starting collector pool."""
        try:
            # When
            self.pool.start()

            # Then
            assert self.pool._started
            assert len(self.pool.collectors) == 2
            assert self.pool.get_collector_count() == 2
        finally:
            # Clean up
            if self.pool._started:
                self.pool.stop()
                import time

                for _ in range(10):
                    if not self.pool.is_alive():
                        break
                    time.sleep(0.1)

    def test_start_already_started_pool(self) -> None:
        """Test starting already started pool raises error."""
        try:
            # Given
            self.pool.start()

            # When & Then
            with pytest.raises(
                RuntimeError, match="Collector pool has already been started"
            ):
                self.pool.start()
        finally:
            # Clean up
            if self.pool._started:
                self.pool.stop()
                import time

                for _ in range(10):
                    if not self.pool.is_alive():
                        break
                    time.sleep(0.1)

    def test_stop_collectors(self) -> None:
        """Test stopping collector pool."""
        try:
            # Given
            self.pool.start()

            # When
            self.pool.stop()

            # Then
            assert not self.pool._started
        finally:
            # Clean up
            if self.pool._started:
                self.pool.stop()
                import time

                for _ in range(10):
                    if not self.pool.is_alive():
                        break
                    time.sleep(0.1)

    def test_get_pool_summary(self) -> None:
        """Test getting pool summary information."""
        try:
            # Given
            self.pool.start()

            # When
            summary = self.pool.get_pool_summary()

            # Then
            assert summary["num_collectors"] == 2
            assert summary["started"] is True
            assert summary["total_collectors"] == 2
        finally:
            # Clean up
            if self.pool._started:
                self.pool.stop()
                import time

                for _ in range(10):
                    if not self.pool.is_alive():
                        break
                    time.sleep(0.1)


if __name__ == "__main__":
    unittest.main()
