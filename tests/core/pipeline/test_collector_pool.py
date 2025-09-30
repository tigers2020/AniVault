"""Tests for ResultCollectorPool class."""

import pytest
from unittest.mock import Mock, patch
from anivault.core.pipeline.collector import ResultCollectorPool, ResultCollector


class FakeQueue:
    """Fake queue for testing without actual threading."""

    def __init__(self, values=None):
        self._values = list(values) if values else []
        self._put_items = []

    def get(self, timeout=None):
        if not self._values:
            raise Exception("Queue empty")  # Simulate queue.Empty
        return self._values.pop(0)

    def put(self, item, timeout=None):
        self._put_items.append(item)

    def task_done(self):
        pass

    def qsize(self):
        return len(self._values)

    def empty(self):
        return not self._values


class TestResultCollectorPool:
    """Test cases for ResultCollectorPool class."""

    def test_init(self) -> None:
        """Test pool initialization."""
        # Given
        fake_queue = FakeQueue()

        # When
        pool = ResultCollectorPool(
            fake_queue, num_collectors=3, collector_id_prefix="test"
        )

        # Then
        assert pool.output_queue == fake_queue
        assert pool.num_collectors == 3
        assert pool.collector_id_prefix == "test"
        assert len(pool.collectors) == 0
        assert not pool._started

    def test_init_with_defaults(self) -> None:
        """Test pool initialization with default values."""
        # Given
        fake_queue = FakeQueue()

        # When
        pool = ResultCollectorPool(fake_queue)

        # Then
        assert pool.num_collectors == 1
        assert pool.collector_id_prefix == "collector"
        assert len(pool.collectors) == 0
        assert not pool._started

    def test_start_creates_collectors(self) -> None:
        """Test start method creates and starts collectors."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=2)

        # When
        with patch("anivault.core.pipeline.collector.ResultCollector") as MockCollector:
            mock_collector1 = Mock()
            mock_collector2 = Mock()
            MockCollector.side_effect = [mock_collector1, mock_collector2]

            pool.start()

        # Then
        assert pool._started
        assert len(pool.collectors) == 2
        MockCollector.assert_called()
        mock_collector1.start.assert_called_once()
        mock_collector2.start.assert_called_once()

    def test_start_raises_error_if_already_started(self) -> None:
        """Test start raises error if pool is already started."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue)
        pool._started = True

        # When/Then
        with pytest.raises(
            RuntimeError, match="Collector pool has already been started"
        ):
            pool.start()

    def test_join_raises_error_if_not_started(self) -> None:
        """Test join raises error if pool is not started."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue)

        # When/Then
        with pytest.raises(RuntimeError, match="Collector pool has not been started"):
            pool.join()

    def test_join_calls_join_on_all_collectors(self) -> None:
        """Test join calls join on all collectors."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=2)

        mock_collector1 = Mock()
        mock_collector2 = Mock()
        pool.collectors = [mock_collector1, mock_collector2]
        pool._started = True

        # When
        pool.join(timeout=5.0)

        # Then
        mock_collector1.join.assert_called_once_with(timeout=5.0)
        mock_collector2.join.assert_called_once_with(timeout=5.0)

    def test_stop_calls_stop_on_all_collectors(self) -> None:
        """Test stop calls stop on all collectors."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=2)

        mock_collector1 = Mock()
        mock_collector2 = Mock()
        pool.collectors = [mock_collector1, mock_collector2]

        # When
        pool.stop()

        # Then
        mock_collector1.stop.assert_called_once()
        mock_collector2.stop.assert_called_once()

    def test_is_alive_returns_true_if_any_collector_alive(self) -> None:
        """Test is_alive returns True if any collector is alive."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=2)

        mock_collector1 = Mock()
        mock_collector1.is_alive.return_value = True
        mock_collector2 = Mock()
        mock_collector2.is_alive.return_value = False
        pool.collectors = [mock_collector1, mock_collector2]

        # When
        result = pool.is_alive()

        # Then
        assert result is True

    def test_is_alive_returns_false_if_no_collector_alive(self) -> None:
        """Test is_alive returns False if no collector is alive."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=2)

        mock_collector1 = Mock()
        mock_collector1.is_alive.return_value = False
        mock_collector2 = Mock()
        mock_collector2.is_alive.return_value = False
        pool.collectors = [mock_collector1, mock_collector2]

        # When
        result = pool.is_alive()

        # Then
        assert result is False

    def test_get_collector_count(self) -> None:
        """Test get_collector_count returns correct count."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=3)
        pool.collectors = [Mock(), Mock(), Mock()]

        # When
        count = pool.get_collector_count()

        # Then
        assert count == 3

    def test_get_alive_collector_count(self) -> None:
        """Test get_alive_collector_count returns correct count."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=3)

        mock_collector1 = Mock()
        mock_collector1.is_alive.return_value = True
        mock_collector2 = Mock()
        mock_collector2.is_alive.return_value = False
        mock_collector3 = Mock()
        mock_collector3.is_alive.return_value = True

        pool.collectors = [mock_collector1, mock_collector2, mock_collector3]

        # When
        count = pool.get_alive_collector_count()

        # Then
        assert count == 2

    def test_get_all_results_combines_results_from_all_collectors(self) -> None:
        """Test get_all_results combines results from all collectors."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=2)

        mock_collector1 = Mock()
        mock_collector1.get_results.return_value = [{"id": 1}, {"id": 2}]
        mock_collector2 = Mock()
        mock_collector2.get_results.return_value = [{"id": 3}, {"id": 4}]

        pool.collectors = [mock_collector1, mock_collector2]

        # When
        results = pool.get_all_results()

        # Then
        assert len(results) == 4
        assert results == [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]

    def test_get_total_result_count(self) -> None:
        """Test get_total_result_count returns sum of all collector counts."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=2)

        mock_collector1 = Mock()
        mock_collector1.get_result_count.return_value = 3
        mock_collector2 = Mock()
        mock_collector2.get_result_count.return_value = 2

        pool.collectors = [mock_collector1, mock_collector2]

        # When
        count = pool.get_total_result_count()

        # Then
        assert count == 5

    def test_get_pool_summary(self) -> None:
        """Test get_pool_summary returns correct summary."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=2)
        pool._started = True

        # Mock collectors with results
        mock_collector1 = Mock()
        mock_collector1.get_results.return_value = [
            {
                "status": "success",
                "file_size": 1000,
                "file_extension": ".mp4",
                "worker_id": "w1",
            },
            {"status": "error", "file_size": 0, "worker_id": "w1"},
        ]
        mock_collector1.is_alive.return_value = True

        mock_collector2 = Mock()
        mock_collector2.get_results.return_value = [
            {
                "status": "success",
                "file_size": 2000,
                "file_extension": ".mkv",
                "worker_id": "w2",
            }
        ]
        mock_collector2.is_alive.return_value = False

        pool.collectors = [mock_collector1, mock_collector2]

        # When
        summary = pool.get_pool_summary()

        # Then
        assert summary["num_collectors"] == 2
        assert summary["started"] is True
        assert summary["alive_collectors"] == 1
        assert summary["total_collectors"] == 2
        assert summary["total_results"] == 3
        assert summary["successful_results"] == 2
        assert summary["failed_results"] == 1
        assert abs(summary["success_rate"] - 200 / 3) < 0.001  # 2/3 * 100 = 66.666...
        assert summary["total_file_size"] == 3000
        assert summary["average_file_size"] == 1500.0
        assert set(summary["file_extensions"]) == {".mp4", ".mkv"}
        assert set(summary["worker_ids"]) == {"w1", "w2"}

    def test_clear_all_results_calls_clear_on_all_collectors(self) -> None:
        """Test clear_all_results calls clear on all collectors."""
        # Given
        fake_queue = FakeQueue()
        pool = ResultCollectorPool(fake_queue, num_collectors=2)

        mock_collector1 = Mock()
        mock_collector2 = Mock()
        pool.collectors = [mock_collector1, mock_collector2]

        # When
        pool.clear_all_results()

        # Then
        mock_collector1.clear_results.assert_called_once()
        mock_collector2.clear_results.assert_called_once()
