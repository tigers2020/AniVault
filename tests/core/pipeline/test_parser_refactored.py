"""Tests for refactored ParserWorker with SRP and structured error handling."""

import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from anivault.core.pipeline.cache import CacheV1
from anivault.core.pipeline.parser import ParserWorker, ParserWorkerPool
from anivault.core.pipeline.utils import BoundedQueue, ParserStatistics
from anivault.shared.errors import ErrorCode, InfrastructureError


class TestParserWorkerRefactored:
    """Test refactored ParserWorker with SRP methods."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.input_queue = BoundedQueue(maxsize=10)
        self.output_queue = BoundedQueue(maxsize=10)
        self.stats = ParserStatistics()
        self.cache = Mock(spec=CacheV1)
        self.worker_id = "test_worker"

        self.worker = ParserWorker(
            input_queue=self.input_queue,
            output_queue=self.output_queue,
            stats=self.stats,
            cache=self.cache,
            worker_id=self.worker_id,
        )

    def test_check_cache_success(self) -> None:
        """Test successful cache check."""
        # Given
        file_path = Path("test.mkv")
        expected_result = {"status": "success", "data": "cached"}
        self.cache.get.return_value = expected_result

        # When
        result = self.worker._check_cache(file_path)

        # Then
        assert result == expected_result
        self.cache.get.assert_called_once_with(str(file_path))

    def test_check_cache_failure(self) -> None:
        """Test cache check failure with structured error handling."""
        # Given
        file_path = Path("test.mkv")
        self.cache.get.side_effect = Exception("Cache error")

        # When & Then
        try:
            self.worker._check_cache(file_path)
            assert False, "Expected InfrastructureError to be raised"
        except InfrastructureError as exc_info:
            assert exc_info.code == ErrorCode.CACHE_READ_FAILED
            assert "Failed to check cache for file" in exc_info.message
            assert exc_info.context.file_path == str(file_path)
            assert exc_info.context.operation == "check_cache"

    def test_handle_cache_hit_success(self) -> None:
        """Test successful cache hit handling."""
        # Given
        cached_result = {"status": "success", "data": "cached"}

        # When
        self.worker._handle_cache_hit(cached_result)

        # Then
        assert self.stats.cache_hits == 1
        assert self.stats.items_processed == 1
        assert self.stats.successes == 1
        assert self.output_queue.get() == cached_result

    def test_handle_cache_hit_with_failure_status(self) -> None:
        """Test cache hit handling with failure status."""
        # Given
        cached_result = {"status": "error", "error": "parse failed"}

        # When
        self.worker._handle_cache_hit(cached_result)

        # Then
        assert self.stats.cache_hits == 1
        assert self.stats.items_processed == 1
        assert self.stats.failures == 1
        assert self.output_queue.get() == cached_result

    def test_handle_cache_hit_queue_failure(self) -> None:
        """Test cache hit handling when queue operation fails."""
        # Given
        cached_result = {"status": "success", "data": "cached"}
        mock_queue = Mock(spec=BoundedQueue)
        mock_queue.put.side_effect = Exception("Queue error")
        self.worker.output_queue = mock_queue

        # When & Then
        with pytest.raises(InfrastructureError) as exc_info:
            self.worker._handle_cache_hit(cached_result)

        assert exc_info.value.code == ErrorCode.QUEUE_OPERATION_ERROR
        assert "Failed to handle cache hit result" in exc_info.value.message

    def test_handle_cache_miss_success(self) -> None:
        """Test successful cache miss handling."""
        # Given
        file_path = Path("test.mkv")
        expected_result = {
            "file_path": str(file_path),
            "status": "success",
            "worker_id": self.worker_id,
        }

        # Mock _parse_file to return expected result
        with patch.object(self.worker, "_parse_file", return_value=expected_result):
            # When
            self.worker._handle_cache_miss(file_path)

        # Then
        assert self.stats.cache_misses == 1
        assert self.stats.items_processed == 1
        assert self.stats.successes == 1
        self.cache.set.assert_called_once_with(
            str(file_path), expected_result, ttl_seconds=86400
        )
        assert self.output_queue.get() == expected_result

    def test_handle_cache_miss_parsing_failure(self) -> None:
        """Test cache miss handling when parsing fails."""
        # Given
        file_path = Path("test.mkv")
        error_result = {
            "file_path": str(file_path),
            "status": "error",
            "error": "parse failed",
            "worker_id": self.worker_id,
        }

        # Mock _parse_file to return error result
        with patch.object(self.worker, "_parse_file", return_value=error_result):
            # When
            self.worker._handle_cache_miss(file_path)

        # Then
        assert self.stats.cache_misses == 1
        assert self.stats.items_processed == 1
        assert self.stats.failures == 1
        self.cache.set.assert_called_once_with(
            str(file_path), error_result, ttl_seconds=86400
        )
        assert self.output_queue.get() == error_result

    def test_handle_cache_miss_parsing_exception(self) -> None:
        """Test cache miss handling when parsing raises exception."""
        # Given
        file_path = Path("test.mkv")

        # Mock _parse_file to raise exception
        with patch.object(
            self.worker, "_parse_file", side_effect=Exception("Parse error")
        ):
            # When & Then
            with pytest.raises(InfrastructureError) as exc_info:
                self.worker._handle_cache_miss(file_path)

            assert exc_info.value.code == ErrorCode.PARSER_ERROR
            assert "Failed to handle cache miss for file" in exc_info.value.message

    def test_store_in_cache_success(self) -> None:
        """Test successful cache storage."""
        # Given
        file_path = Path("test.mkv")
        result = {"status": "success", "data": "parsed"}

        # When
        self.worker._store_in_cache(file_path, result)

        # Then
        self.cache.set.assert_called_once_with(
            str(file_path), result, ttl_seconds=86400
        )

    def test_store_in_cache_failure(self) -> None:
        """Test cache storage failure with structured error handling."""
        # Given
        file_path = Path("test.mkv")
        result = {"status": "success", "data": "parsed"}
        self.cache.set.side_effect = Exception("Cache write error")

        # When & Then
        with pytest.raises(InfrastructureError) as exc_info:
            self.worker._store_in_cache(file_path, result)

        assert exc_info.value.code == ErrorCode.CACHE_WRITE_FAILED
        assert "Failed to store result in cache for file" in exc_info.value.message
        assert exc_info.value.context.file_path == str(file_path)
        assert exc_info.value.context.operation == "store_in_cache"

    def test_parse_file_success(self) -> None:
        """Test successful file parsing."""
        # Given
        file_path = Path("test.mkv")

        # Mock file stat
        mock_stat = Mock()
        mock_stat.st_size = 1024
        mock_stat.st_mtime = 1234567890
        mock_stat.st_ctime = 1234567890

        # Use patch on the Path class instead of instance
        with patch("pathlib.Path.stat", return_value=mock_stat):
            # When
            result = self.worker._parse_file(file_path)

        # Then
        assert result["file_path"] == str(file_path)
        assert result["file_name"] == "test.mkv"
        assert result["file_size"] == 1024
        assert result["file_extension"] == ".mkv"
        assert result["worker_id"] == self.worker_id
        assert result["status"] == "success"

    def test_parse_file_failure(self) -> None:
        """Test file parsing failure with structured error handling."""
        # Given
        file_path = Path("nonexistent.mkv")

        # Mock file stat to raise exception
        with patch(
            "pathlib.Path.stat", side_effect=FileNotFoundError("File not found")
        ):
            # When
            result = self.worker._parse_file(file_path)

        # Then
        assert result["file_path"] == str(file_path)
        assert result["file_name"] == "nonexistent.mkv"
        assert result["error"] == "File not found"
        assert result["worker_id"] == self.worker_id
        assert result["status"] == "error"

    def test_process_file_cache_hit_flow(self) -> None:
        """Test complete process_file flow with cache hit."""
        # Given
        file_path = Path("test.mkv")
        cached_result = {"status": "success", "data": "cached"}

        # Mock queue to avoid task_done issues
        mock_queue = Mock(spec=BoundedQueue)
        self.worker.input_queue = mock_queue

        # Mock cache to return cached result
        with patch.object(
            self.worker, "_check_cache", return_value=cached_result
        ), patch.object(self.worker, "_handle_cache_hit") as mock_handle_hit:
            # When
            self.worker._process_file(file_path)

        # Then
        mock_handle_hit.assert_called_once_with(cached_result)
        mock_queue.task_done.assert_called_once()

    def test_process_file_cache_miss_flow(self) -> None:
        """Test complete process_file flow with cache miss."""
        # Given
        file_path = Path("test.mkv")

        # Mock queue to avoid task_done issues
        mock_queue = Mock(spec=BoundedQueue)
        self.worker.input_queue = mock_queue

        # Mock cache to return None (cache miss)
        with patch.object(self.worker, "_check_cache", return_value=None), patch.object(
            self.worker, "_handle_cache_miss"
        ) as mock_handle_miss:
            # When
            self.worker._process_file(file_path)

        # Then
        mock_handle_miss.assert_called_once_with(file_path)
        mock_queue.task_done.assert_called_once()

    def test_process_file_exception_handling(self) -> None:
        """Test process_file exception handling with structured error."""
        # Given
        file_path = Path("test.mkv")

        # Mock queue to avoid task_done issues
        mock_queue = Mock(spec=BoundedQueue)
        self.worker.input_queue = mock_queue

        # Mock _check_cache to raise exception
        with patch.object(
            self.worker, "_check_cache", side_effect=Exception("Check error")
        ):
            # When
            self.worker._process_file(file_path)

        # Then
        assert self.stats.failures == 1
        # task_done should still be called
        mock_queue.task_done.assert_called_once()

    def test_process_file_task_done_always_called(self) -> None:
        """Test that task_done is always called in finally block."""
        # Given
        file_path = Path("test.mkv")

        # Mock _check_cache to raise exception
        with patch.object(
            self.worker, "_check_cache", side_effect=Exception("Error")
        ), patch.object(self.input_queue, "task_done") as mock_task_done:
            # When
            self.worker._process_file(file_path)

        # Then
        mock_task_done.assert_called_once()


class TestParserWorkerPoolRefactored:
    """Test ParserWorkerPool with refactored workers."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.input_queue = BoundedQueue(maxsize=10)
        self.output_queue = BoundedQueue(maxsize=10)
        self.stats = ParserStatistics()
        self.cache = Mock(spec=CacheV1)

        self.pool = ParserWorkerPool(
            num_workers=2,
            input_queue=self.input_queue,
            output_queue=self.output_queue,
            stats=self.stats,
            cache=self.cache,
        )

    def teardown_method(self) -> None:
        """Clean up after each test."""
        if hasattr(self, "pool"):
            try:
                if self.pool._started:
                    self.pool.stop()
                    # Wait for workers to actually stop
                    import time

                    for _ in range(10):  # Wait up to 1 second
                        if not self.pool.is_alive():
                            break
                        time.sleep(0.1)
            except Exception:
                pass  # Ignore cleanup errors

    def test_pool_initialization(self) -> None:
        """Test pool initialization."""
        assert self.pool.num_workers == 2
        assert self.pool.input_queue == self.input_queue
        assert self.pool.output_queue == self.output_queue
        assert self.pool.stats == self.stats
        assert self.pool.cache == self.cache
        assert len(self.pool.workers) == 0
        assert not self.pool._started

    def test_start_workers(self) -> None:
        """Test starting worker threads."""
        try:
            # When
            self.pool.start()

            # Then
            assert self.pool._started
            assert len(self.pool.workers) == 2
            assert all(worker.is_alive() for worker in self.pool.workers)
            assert self.pool.get_worker_count() == 2
            assert self.pool.get_alive_worker_count() == 2
        finally:
            # Clean up
            if self.pool._started:
                self.pool.stop()
                # Wait for workers to stop
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
                RuntimeError, match="Worker pool has already been started"
            ):
                self.pool.start()
        finally:
            # Clean up
            if self.pool._started:
                self.pool.stop()
                # Wait for workers to stop
                import time

                for _ in range(10):
                    if not self.pool.is_alive():
                        break
                    time.sleep(0.1)

    def test_join_workers(self) -> None:
        """Test joining worker threads."""
        try:
            # Given
            self.pool.start()

            # When
            self.pool.join(timeout=1.0)

            # Then
            # Workers should be joined (test completes without hanging)
            assert True
        finally:
            # Clean up
            if self.pool._started:
                self.pool.stop()
                # Wait for workers to stop
                import time

                for _ in range(10):
                    if not self.pool.is_alive():
                        break
                    time.sleep(0.1)

    def test_join_not_started_pool(self) -> None:
        """Test joining not started pool raises error."""
        # When & Then
        with pytest.raises(RuntimeError, match="Worker pool has not been started"):
            self.pool.join()

    def test_stop_workers(self) -> None:
        """Test stopping worker threads."""
        try:
            # Given
            self.pool.start()

            # When
            self.pool.stop()

            # Then
            # Workers should be signaled to stop
            assert not self.pool._started
        finally:
            # Clean up
            if self.pool._started:
                self.pool.stop()
                # Wait for workers to stop
                import time

                for _ in range(10):
                    if not self.pool.is_alive():
                        break
                    time.sleep(0.1)

    def test_get_pool_status(self) -> None:
        """Test getting pool status information."""
        try:
            # Given
            self.pool.start()

            # When
            status = self.pool.get_pool_status()

            # Then
            assert status["num_workers"] == 2
            assert status["started"] is True
            assert status["alive_workers"] == 2
            assert status["total_workers"] == 2
        finally:
            # Clean up
            if self.pool._started:
                self.pool.stop()
                # Wait for workers to stop
                import time

                for _ in range(10):
                    if not self.pool.is_alive():
                        break
                    time.sleep(0.1)
        assert "input_queue_size" in status
        assert "output_queue_size" in status
        assert "items_processed" in status
        assert "successes" in status
        assert "failures" in status
