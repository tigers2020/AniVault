"""Integration tests for the complete pipeline."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from anivault.core.pipeline.main import run_pipeline


class TestPipelineIntegration:
    """Integration test cases for the complete pipeline."""

    @pytest.fixture
    def temp_test_dir(self, tmp_path):
        """Create a temporary directory with test files."""
        # Create test directory structure
        test_dir = tmp_path / "test_anime"
        test_dir.mkdir()

        # Create test video files
        video_files = [
            "anime_s01e01.mp4",
            "anime_s01e02.mkv",
            "anime_s01e03.avi",
        ]

        for filename in video_files:
            file_path = test_dir / filename
            file_path.write_bytes(b"fake video content")

        # Create a non-video file (should be ignored)
        (test_dir / "readme.txt").write_text("test readme")

        return test_dir

    def test_pipeline_with_mock_components(self, temp_test_dir) -> None:
        """Test pipeline orchestration with mocked components."""
        # Given
        root_path = str(temp_test_dir)
        extensions = [".mp4", ".mkv", ".avi"]
        num_workers = 2

        # Mock all components to avoid actual threading
        with (
            patch("anivault.core.pipeline.main.DirectoryScanner") as MockScanner,
            patch("anivault.core.pipeline.main.ParserWorkerPool") as MockParserPool,
            patch("anivault.core.pipeline.main.ResultCollector") as MockCollector,
            patch("anivault.core.pipeline.main.BoundedQueue") as MockQueue,
        ):

            # Setup mock scanner
            mock_scanner = Mock()
            mock_scanner.is_alive.return_value = False
            MockScanner.return_value = mock_scanner

            # Setup mock parser pool
            mock_parser_pool = Mock()
            mock_parser_pool.is_alive.return_value = False
            MockParserPool.return_value = mock_parser_pool

            # Setup mock collector with results
            mock_collector = Mock()
            mock_collector.is_alive.return_value = False
            mock_collector.get_result_count.return_value = 3
            mock_collector.get_results.return_value = [
                {
                    "file_path": str(temp_test_dir / "anime_s01e01.mp4"),
                    "status": "success",
                },
                {
                    "file_path": str(temp_test_dir / "anime_s01e02.mkv"),
                    "status": "success",
                },
                {
                    "file_path": str(temp_test_dir / "anime_s01e03.avi"),
                    "status": "success",
                },
            ]
            MockCollector.return_value = mock_collector

            # Setup mock queues
            mock_file_queue = Mock()
            mock_result_queue = Mock()
            MockQueue.side_effect = [mock_file_queue, mock_result_queue]

            # When
            results = run_pipeline(root_path, extensions, num_workers)

            # Then - Verify component creation
            MockScanner.assert_called_once()
            MockParserPool.assert_called_once()
            MockCollector.assert_called_once()

            # Verify lifecycle calls
            mock_scanner.start.assert_called_once()
            mock_scanner.join.assert_called_once()

            mock_parser_pool.start.assert_called_once()
            mock_parser_pool.join.assert_called_once()

            mock_collector.start.assert_called_once()
            mock_collector.join.assert_called_once()

            # Verify sentinel values were sent
            assert (
                mock_file_queue.put.call_count == num_workers
            )  # Sentinel for each worker
            assert mock_result_queue.put.call_count == 1  # Sentinel for collector

            # Verify results
            assert len(results) == 3
            assert all(r["status"] == "success" for r in results)

    def test_pipeline_error_handling(self, temp_test_dir) -> None:
        """Test pipeline error handling and graceful shutdown."""
        # Given
        root_path = str(temp_test_dir)
        extensions = [".mp4"]

        with (
            patch("anivault.core.pipeline.main.DirectoryScanner") as MockScanner,
            patch("anivault.core.pipeline.main.ParserWorkerPool") as MockParserPool,
            patch("anivault.core.pipeline.main.ResultCollector") as MockCollector,
        ):

            # Setup mock scanner to raise an error
            mock_scanner = Mock()
            mock_scanner.start.side_effect = RuntimeError("Scanner error")
            mock_scanner.is_alive.return_value = True
            MockScanner.return_value = mock_scanner

            mock_parser_pool = Mock()
            mock_parser_pool.is_alive.return_value = True
            MockParserPool.return_value = mock_parser_pool

            mock_collector = Mock()
            mock_collector.is_alive.return_value = True
            MockCollector.return_value = mock_collector

            # When/Then
            with pytest.raises(RuntimeError, match="Scanner error"):
                run_pipeline(root_path, extensions)

            # Verify cleanup was attempted
            mock_scanner.stop.assert_called()
            mock_parser_pool.stop.assert_called()
            mock_collector.stop.assert_called()

    def test_pipeline_with_empty_directory(self, tmp_path) -> None:
        """Test pipeline with empty directory."""
        # Given
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with (
            patch("anivault.core.pipeline.main.DirectoryScanner") as MockScanner,
            patch("anivault.core.pipeline.main.ParserWorkerPool") as MockParserPool,
            patch("anivault.core.pipeline.main.ResultCollector") as MockCollector,
        ):

            mock_scanner = Mock()
            mock_scanner.is_alive.return_value = False
            MockScanner.return_value = mock_scanner

            mock_parser_pool = Mock()
            mock_parser_pool.is_alive.return_value = False
            MockParserPool.return_value = mock_parser_pool

            mock_collector = Mock()
            mock_collector.is_alive.return_value = False
            mock_collector.get_result_count.return_value = 0
            mock_collector.get_results.return_value = []
            MockCollector.return_value = mock_collector

            # When
            results = run_pipeline(str(empty_dir), [".mp4"])

            # Then
            assert len(results) == 0
            mock_scanner.start.assert_called_once()
            mock_scanner.join.assert_called_once()

    def test_pipeline_respects_extensions_filter(self, tmp_path) -> None:
        """Test that pipeline only processes specified extensions."""
        # Given
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        # Create files with different extensions
        (test_dir / "video.mp4").write_bytes(b"mp4")
        (test_dir / "video.mkv").write_bytes(b"mkv")
        (test_dir / "video.avi").write_bytes(b"avi")
        (test_dir / "doc.txt").write_bytes(b"txt")

        with (
            patch("anivault.core.pipeline.main.DirectoryScanner") as MockScanner,
            patch("anivault.core.pipeline.main.ParserWorkerPool") as MockParserPool,
            patch("anivault.core.pipeline.main.ResultCollector") as MockCollector,
        ):

            # Setup mocks
            mock_scanner = Mock()
            mock_scanner.is_alive.return_value = False
            MockScanner.return_value = mock_scanner

            mock_parser_pool = Mock()
            mock_parser_pool.is_alive.return_value = False
            MockParserPool.return_value = mock_parser_pool

            mock_collector = Mock()
            mock_collector.is_alive.return_value = False
            mock_collector.get_results.return_value = []
            MockCollector.return_value = mock_collector

            # When - only process .mp4 files
            run_pipeline(str(test_dir), [".mp4"])

            # Then - verify scanner was called with correct extensions
            scanner_call_args = MockScanner.call_args
            assert ".mp4" in scanner_call_args.kwargs["extensions"]
            assert ".txt" not in scanner_call_args.kwargs["extensions"]
