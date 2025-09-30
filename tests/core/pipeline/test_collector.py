"""Tests for the ResultCollector class."""

import queue
from pathlib import Path
from unittest.mock import Mock

import pytest

from anivault.core.pipeline.collector import ResultCollector
from anivault.core.pipeline.utils import BoundedQueue


class FakeQueue:
    """Fake queue for testing - no blocking, deterministic behavior."""

    def __init__(self, values=None):
        self._values = list(values) if values else []
        self._put_items = []

    def get(self, timeout=None):
        if not self._values:
            raise queue.Empty  # 표준 예외 타입 사용
        return self._values.pop(0)

    def put(self, item, timeout=None):
        self._put_items.append(item)
        return None

    def task_done(self):
        return None

    def qsize(self):
        return len(self._values)

    def empty(self):
        return not self._values


class TestResultCollector:
    """Test cases for ResultCollector class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.fake_queue = FakeQueue()
        self.collector = ResultCollector(
            output_queue=self.fake_queue, collector_id="test_collector"
        )

    def teardown_method(self) -> None:
        """Clean up after each test."""
        # No cleanup needed since we don't use real threads

    def test_init(self) -> None:
        """Test ResultCollector initialization."""
        assert self.collector.output_queue == self.fake_queue
        assert self.collector.collector_id == "test_collector"
        assert self.collector.get_result_count() == 0
        assert not self.collector.is_stopped()

    def test_init_with_default_id(self) -> None:
        """Test ResultCollector initialization with default ID."""
        collector = ResultCollector(output_queue=self.fake_queue)
        assert collector.collector_id.startswith("collector_")
        assert collector.get_result_count() == 0

    def test_store_and_get_results(self) -> None:
        """Test storing and retrieving results."""
        # Given
        result1 = {
            "file_path": "/path/to/file1.mp4",
            "file_name": "file1.mp4",
            "file_size": 1000,
            "status": "success",
            "worker_id": "worker_1",
        }
        result2 = {
            "file_path": "/path/to/file2.mkv",
            "file_name": "file2.mkv",
            "file_size": 2000,
            "status": "error",
            "worker_id": "worker_2",
        }

        # When
        self.collector._store_result(result1)
        self.collector._store_result(result2)

        # Then
        results = self.collector.get_results()
        assert len(results) == 2
        assert results[0] == result1
        assert results[1] == result2

    def test_get_result_count(self) -> None:
        """Test getting result count."""
        # Given
        result = {"file_path": "/test.mp4", "status": "success"}

        # When
        assert self.collector.get_result_count() == 0
        self.collector._store_result(result)
        assert self.collector.get_result_count() == 1

    def test_get_successful_results(self) -> None:
        """Test getting only successful results."""
        # Given
        success_result = {"file_path": "/success.mp4", "status": "success"}
        error_result = {"file_path": "/error.mp4", "status": "error"}

        # When
        self.collector._store_result(success_result)
        self.collector._store_result(error_result)

        # Then
        successful = self.collector.get_successful_results()
        assert len(successful) == 1
        assert successful[0] == success_result

    def test_get_failed_results(self) -> None:
        """Test getting only failed results."""
        # Given
        success_result = {"file_path": "/success.mp4", "status": "success"}
        error_result = {"file_path": "/error.mp4", "status": "error"}

        # When
        self.collector._store_result(success_result)
        self.collector._store_result(error_result)

        # Then
        failed = self.collector.get_failed_results()
        assert len(failed) == 1
        assert failed[0] == error_result

    def test_get_results_by_extension(self) -> None:
        """Test filtering results by file extension."""
        # Given
        mp4_result = {
            "file_path": "/test.mp4",
            "file_extension": ".mp4",
            "status": "success",
        }
        mkv_result = {
            "file_path": "/test.mkv",
            "file_extension": ".mkv",
            "status": "success",
        }

        # When
        self.collector._store_result(mp4_result)
        self.collector._store_result(mkv_result)

        # Then
        mp4_results = self.collector.get_results_by_extension(".mp4")
        mkv_results = self.collector.get_results_by_extension(".mkv")

        assert len(mp4_results) == 1
        assert len(mkv_results) == 1
        assert mp4_results[0] == mp4_result
        assert mkv_results[0] == mkv_result

    def test_get_results_by_worker(self) -> None:
        """Test filtering results by worker ID."""
        # Given
        worker1_result = {
            "file_path": "/test1.mp4",
            "worker_id": "worker_1",
            "status": "success",
        }
        worker2_result = {
            "file_path": "/test2.mp4",
            "worker_id": "worker_2",
            "status": "success",
        }

        # When
        self.collector._store_result(worker1_result)
        self.collector._store_result(worker2_result)

        # Then
        worker1_results = self.collector.get_results_by_worker("worker_1")
        worker2_results = self.collector.get_results_by_worker("worker_2")

        assert len(worker1_results) == 1
        assert len(worker2_results) == 1
        assert worker1_results[0] == worker1_result
        assert worker2_results[0] == worker2_result

    def test_get_total_file_size(self) -> None:
        """Test getting total file size."""
        # Given
        result1 = {"file_size": 1000, "status": "success"}
        result2 = {"file_size": 2000, "status": "success"}
        result3 = {"file_size": 500, "status": "error"}  # Should not be counted

        # When
        self.collector._store_result(result1)
        self.collector._store_result(result2)
        self.collector._store_result(result3)

        # Then
        total_size = self.collector.get_total_file_size()
        assert total_size == 3000  # Only successful results

    def test_get_average_file_size(self) -> None:
        """Test getting average file size."""
        # Given
        result1 = {"file_size": 1000, "status": "success"}
        result2 = {"file_size": 2000, "status": "success"}
        result3 = {"file_size": 500, "status": "error"}  # Should not be counted

        # When
        self.collector._store_result(result1)
        self.collector._store_result(result2)
        self.collector._store_result(result3)

        # Then
        avg_size = self.collector.get_average_file_size()
        assert avg_size == 1500.0  # (1000 + 2000) / 2

    def test_get_average_file_size_no_results(self) -> None:
        """Test getting average file size with no results."""
        avg_size = self.collector.get_average_file_size()
        assert avg_size == 0.0

    def test_get_file_extensions(self) -> None:
        """Test getting unique file extensions."""
        # Given
        result1 = {"file_extension": ".mp4", "status": "success"}
        result2 = {"file_extension": ".mkv", "status": "success"}
        result3 = {"file_extension": ".mp4", "status": "success"}  # Duplicate
        result4 = {"file_extension": ".avi", "status": "error"}  # Should not be counted

        # When
        self.collector._store_result(result1)
        self.collector._store_result(result2)
        self.collector._store_result(result3)
        self.collector._store_result(result4)

        # Then
        extensions = self.collector.get_file_extensions()
        assert len(extensions) == 2
        assert ".mp4" in extensions
        assert ".mkv" in extensions
        assert extensions == sorted(extensions)  # Should be sorted

    def test_get_worker_ids(self) -> None:
        """Test getting unique worker IDs."""
        # Given
        result1 = {"worker_id": "worker_1", "status": "success"}
        result2 = {"worker_id": "worker_2", "status": "success"}
        result3 = {"worker_id": "worker_1", "status": "success"}  # Duplicate

        # When
        self.collector._store_result(result1)
        self.collector._store_result(result2)
        self.collector._store_result(result3)

        # Then
        worker_ids = self.collector.get_worker_ids()
        assert len(worker_ids) == 2
        assert "worker_1" in worker_ids
        assert "worker_2" in worker_ids
        assert worker_ids == sorted(worker_ids)  # Should be sorted

    def test_get_summary(self) -> None:
        """Test getting summary statistics."""
        # Given
        result1 = {
            "file_path": "/test1.mp4",
            "file_size": 1000,
            "file_extension": ".mp4",
            "worker_id": "worker_1",
            "status": "success",
        }
        result2 = {
            "file_path": "/test2.mkv",
            "file_size": 2000,
            "file_extension": ".mkv",
            "worker_id": "worker_2",
            "status": "success",
        }
        result3 = {
            "file_path": "/test3.avi",
            "file_size": 500,
            "file_extension": ".avi",
            "worker_id": "worker_1",
            "status": "error",
        }

        # When
        self.collector._store_result(result1)
        self.collector._store_result(result2)
        self.collector._store_result(result3)

        # Then
        summary = self.collector.get_summary()
        assert summary["total_results"] == 3
        assert summary["successful_results"] == 2
        assert summary["failed_results"] == 1
        assert abs(summary["success_rate"] - 200 / 3) < 0.001  # 2/3 * 100 = 66.666...
        assert summary["total_file_size"] == 3000  # Only successful results
        assert summary["average_file_size"] == 1500.0  # 3000 / 2
        assert set(summary["file_extensions"]) == {".mp4", ".mkv"}
        assert set(summary["worker_ids"]) == {"worker_1", "worker_2"}

    def test_clear_results(self) -> None:
        """Test clearing all results."""
        # Given
        result = {"file_path": "/test.mp4", "status": "success"}
        self.collector._store_result(result)
        assert self.collector.get_result_count() == 1

        # When
        self.collector.clear_results()

        # Then
        assert self.collector.get_result_count() == 0
        assert self.collector.get_results() == []

    def test_stop(self) -> None:
        """Test stopping the collector."""
        # When
        self.collector.stop()

        # Then
        assert self.collector.is_stopped()

    def test_thread_safety_simulation(self) -> None:
        """Test thread safety simulation without actual threads."""
        # Given
        num_threads = 5
        results_per_thread = 10

        # When - simulate concurrent access without actual threads
        for thread_id in range(num_threads):
            for i in range(results_per_thread):
                result = {
                    "file_path": f"/test_{thread_id}_{i}.mp4",
                    "status": "success",
                    "worker_id": f"worker_{thread_id}",
                }
                self.collector._store_result(result)

        # Then
        assert self.collector.get_result_count() == num_threads * results_per_thread

    def test_run_loop_without_real_thread(self) -> None:
        """Test run method directly without actual threading."""
        # Given
        fake_queue = FakeQueue(
            [
                {"file_path": "/test1.mp4", "status": "success"},
                None,  # sentinel
            ]
        )
        collector = ResultCollector(output_queue=fake_queue, collector_id="c0")

        # When - run 메서드를 직접 호출 (동기 실행)
        collector.run()

        # Then
        assert collector.get_result_count() == 1
        results = collector.get_results()
        assert results[0]["file_path"] == "/test1.mp4"
        assert results[0]["status"] == "success"

    def test_run_handles_queue_empty_exception(self) -> None:
        """Test run method handles queue.Empty exception properly."""
        # Given
        fake_queue = FakeQueue([])  # 빈 큐
        collector = ResultCollector(output_queue=fake_queue)

        # When - run 메서드를 직접 호출 (max_idle_loops=1로 빠른 종료)
        collector.run(max_idle_loops=1)

        # Then - 예외가 발생해도 정상적으로 종료
        assert collector.get_result_count() == 0

    def test_run_with_multiple_results_and_sentinel(self) -> None:
        """Test run method with multiple results and sentinel."""
        # Given
        fake_queue = FakeQueue(
            [
                {"file_path": "/test1.mp4", "status": "success"},
                {"file_path": "/test2.mkv", "status": "success"},
                {"file_path": "/test3.avi", "status": "error"},
                None,  # sentinel
            ]
        )
        collector = ResultCollector(output_queue=fake_queue)

        # When
        collector.run()

        # Then
        assert collector.get_result_count() == 3
        results = collector.get_results()
        assert len(results) == 3
        assert results[0]["file_path"] == "/test1.mp4"
        assert results[1]["file_path"] == "/test2.mkv"
        assert results[2]["file_path"] == "/test3.avi"

    def test_run_directly_without_start(self) -> None:
        """Test run method directly without start method."""
        # Given
        fake_queue = FakeQueue([None])  # 즉시 종료
        collector = ResultCollector(output_queue=fake_queue)

        # When - run을 직접 호출
        collector.run()

        # Then
        assert collector.get_result_count() == 0  # 센티넬만 처리됨

    def test_poll_once_with_results(self) -> None:
        """Test poll_once method with available results."""
        # Given
        fake_queue = FakeQueue(
            [
                {"file_path": "/test1.mp4", "status": "success"},
                {"file_path": "/test2.mkv", "status": "success"},
                None,  # sentinel
            ]
        )
        collector = ResultCollector(output_queue=fake_queue)

        # When
        result1 = collector.poll_once()
        result2 = collector.poll_once()
        result3 = collector.poll_once()

        # Then
        assert result1 is True
        assert result2 is True
        assert result3 is False  # sentinel received
        assert collector.get_result_count() == 2
        assert collector.is_stopped()  # sentinel으로 인해 stop됨

    def test_poll_once_with_empty_queue(self) -> None:
        """Test poll_once method with empty queue."""
        # Given
        fake_queue = FakeQueue([])  # 빈 큐
        collector = ResultCollector(output_queue=fake_queue)

        # When
        result = collector.poll_once()

        # Then
        assert result is False
        assert collector.get_result_count() == 0
        assert not collector.is_stopped()

    def test_run_with_max_idle_loops(self) -> None:
        """Test run method with custom max_idle_loops."""
        # Given
        fake_queue = FakeQueue([])  # 빈 큐
        collector = ResultCollector(output_queue=fake_queue)

        # When - max_idle_loops=2로 설정
        collector.run(max_idle_loops=2)

        # Then - 2번의 idle 후 종료
        assert collector.get_result_count() == 0
        assert collector.is_stopped()  # run()이 끝나면 stop()이 호출됨
