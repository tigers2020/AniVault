"""Tests for the ScanParsePool and extension filter modules."""

import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from anivault.scanner.extension_filter import (
    create_custom_extension_filter,
    create_media_extension_filter,
    get_default_media_filter,
    is_media_file,
    validate_extension_filter,
)
from anivault.scanner.scan_parse_pool import ScanParsePool


class TestExtensionFilter:
    """Test cases for extension filter functionality."""

    def test_create_media_extension_filter_basic(self):
        """Test basic media extension filter creation."""
        extensions = [".mkv", ".mp4", ".avi"]
        filter_func = create_media_extension_filter(extensions)

        # Test valid extensions
        assert filter_func("/path/to/movie.mkv") is True
        assert filter_func("/path/to/video.mp4") is True
        assert filter_func("/path/to/film.avi") is True

        # Test invalid extensions
        assert filter_func("/path/to/document.txt") is False
        assert filter_func("/path/to/image.jpg") is False
        assert filter_func("/path/to/no_extension") is False

    def test_create_media_extension_filter_case_sensitive(self):
        """Test case-sensitive extension filtering."""
        extensions = [".MKV", ".MP4"]
        filter_func = create_media_extension_filter(extensions, case_sensitive=True)

        # Test exact case match
        assert filter_func("/path/to/movie.MKV") is True
        assert filter_func("/path/to/video.MP4") is True

        # Test case mismatch
        assert filter_func("/path/to/movie.mkv") is False
        assert filter_func("/path/to/video.mp4") is False

    def test_create_media_extension_filter_case_insensitive(self):
        """Test case-insensitive extension filtering (default)."""
        extensions = [".MKV", ".MP4"]
        filter_func = create_media_extension_filter(extensions, case_sensitive=False)

        # Test various cases
        assert filter_func("/path/to/movie.mkv") is True
        assert filter_func("/path/to/video.MP4") is True
        assert filter_func("/path/to/film.Mkv") is True
        assert filter_func("/path/to/show.mp4") is True

    def test_get_default_media_filter(self):
        """Test default media filter using APP_CONFIG."""
        filter_func = get_default_media_filter()

        # Test with default extensions (should match APP_CONFIG.media_extensions)
        assert filter_func("/path/to/movie.mkv") is True
        assert filter_func("/path/to/video.mp4") is True
        assert filter_func("/path/to/film.avi") is True

        # Test with non-media extensions
        assert filter_func("/path/to/document.txt") is False
        assert filter_func("/path/to/image.jpg") is False

    def test_create_custom_extension_filter_with_patterns(self):
        """Test custom extension filter with inclusion/exclusion patterns."""
        filter_func = create_custom_extension_filter(
            extensions=[".mkv", ".mp4"],
            include_patterns=["*.sample.mkv"],
            exclude_patterns=["*.tmp"],
        )

        # Test normal extensions
        assert filter_func("/path/to/movie.mkv") is True
        assert filter_func("/path/to/video.mp4") is True

        # Test inclusion pattern
        assert filter_func("/path/to/sample.sample.mkv") is True
        assert filter_func("/path/to/trailer.sample.mkv") is True

        # Test exclusion pattern
        assert filter_func("/path/to/movie.tmp") is False
        assert filter_func("/path/to/video.tmp") is False

        # Test non-media files
        assert filter_func("/path/to/document.txt") is False

    def test_is_media_file_convenience_function(self):
        """Test the convenience is_media_file function."""
        # Test media files
        assert is_media_file("/path/to/movie.mkv") is True
        assert is_media_file("/path/to/video.mp4") is True
        assert is_media_file("/path/to/film.avi") is True

        # Test non-media files
        assert is_media_file("/path/to/document.txt") is False
        assert is_media_file("/path/to/image.jpg") is False

    def test_validate_extension_filter(self):
        """Test extension filter validation utility."""
        filter_func = create_media_extension_filter([".mkv", ".mp4"])

        test_files = [
            "/path/to/movie.mkv",
            "/path/to/video.mp4",
            "/path/to/document.txt",
            "/path/to/image.jpg",
        ]

        results = validate_extension_filter(filter_func, test_files)

        expected = {
            "/path/to/movie.mkv": True,
            "/path/to/video.mp4": True,
            "/path/to/document.txt": False,
            "/path/to/image.jpg": False,
        }

        assert results == expected

    def test_extension_filter_error_handling(self):
        """Test extension filter error handling."""
        filter_func = create_media_extension_filter([".mkv"])

        # Test with invalid paths
        assert filter_func("") is False
        assert filter_func(None) is False  # Should handle gracefully

        # Test with paths that might cause issues
        assert filter_func("/path/with/weird/chars/!@#$%.mkv") is True

    def test_empty_extensions_list(self):
        """Test filter with empty extensions list."""
        filter_func = create_media_extension_filter([])

        # Should reject all files
        assert filter_func("/path/to/movie.mkv") is False
        assert filter_func("/path/to/video.mp4") is False


class TestScanParsePool:
    """Test cases for ScanParsePool functionality."""

    def test_scan_parse_pool_initialization(self):
        """Test ScanParsePool initialization."""
        pool = ScanParsePool(max_workers=4)

        assert pool.max_workers == 4
        assert pool.extension_filter is not None
        assert pool.parse_function is None
        assert pool.is_running() is False

    def test_scan_parse_pool_context_manager(self):
        """Test ScanParsePool as context manager."""
        with ScanParsePool(max_workers=2) as pool:
            assert pool.is_running() is True
        assert pool.is_running() is False

    def test_scan_parse_pool_manual_start_shutdown(self):
        """Test manual start and shutdown of thread pool."""
        pool = ScanParsePool(max_workers=2)

        # Test start
        pool.start()
        assert pool.is_running() is True

        # Test shutdown
        pool.shutdown()
        assert pool.is_running() is False

    def test_scan_parse_pool_double_start(self):
        """Test that starting an already running pool handles gracefully."""
        pool = ScanParsePool(max_workers=2)
        pool.start()

        # Should handle double start gracefully
        pool.start()  # Should not raise exception
        assert pool.is_running() is True

    def test_scan_parse_pool_custom_extension_filter(self):
        """Test ScanParsePool with custom extension filter."""
        custom_filter = create_media_extension_filter([".mkv"])
        pool = ScanParsePool(extension_filter=custom_filter)

        assert pool.extension_filter == custom_filter

    def test_scan_parse_pool_custom_parse_function(self):
        """Test ScanParsePool with custom parse function."""

        def mock_parse(file_path):
            return f"parsed_{file_path}"

        pool = ScanParsePool(parse_function=mock_parse)
        assert pool.parse_function == mock_parse

    def test_submit_scan_task_basic(self):
        """Test basic directory scanning task submission."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "video1.mkv").touch()
            (temp_path / "video2.mp4").touch()
            (temp_path / "document.txt").touch()

            with ScanParsePool(max_workers=2) as pool:
                future = pool.submit_scan_task(temp_path)
                file_paths = future.result()

                # Should find 2 media files (mkv and mp4)
                assert len(file_paths) == 2
                assert any("video1.mkv" in path for path in file_paths)
                assert any("video2.mp4" in path for path in file_paths)
                assert not any("document.txt" in path for path in file_paths)

    def test_submit_scan_task_empty_directory(self):
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with ScanParsePool(max_workers=2) as pool:
                future = pool.submit_scan_task(temp_dir)
                file_paths = future.result()

                assert len(file_paths) == 0

    def test_submit_parse_task(self):
        """Test file parsing task submission."""

        def mock_parse(file_path):
            return f"parsed_{Path(file_path).name}"

        with ScanParsePool(parse_function=mock_parse, max_workers=2) as pool:
            future = pool.submit_parse_task("/path/to/movie.mkv")
            result = future.result()

            assert result == "parsed_movie.mkv"

    def test_submit_parse_task_no_parse_function(self):
        """Test that submitting parse task without parse function raises error."""
        with ScanParsePool(max_workers=2) as pool:
            with pytest.raises(RuntimeError, match="Parse function not set"):
                pool.submit_parse_task("/path/to/movie.mkv")

    def test_submit_task_not_running(self):
        """Test that submitting tasks to non-running pool raises error."""
        pool = ScanParsePool(max_workers=2)

        with pytest.raises(RuntimeError, match="ThreadPoolExecutor not started"):
            pool.submit_scan_task("/some/path")

    def test_process_directory_without_parsing(self):
        """Test directory processing without parse function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "video1.mkv").touch()
            (temp_path / "video2.mp4").touch()
            (temp_path / "document.txt").touch()

            with ScanParsePool(max_workers=2) as pool:
                results = list(pool.process_directory(temp_path))

                # Should yield file paths directly
                assert len(results) == 2
                assert any("video1.mkv" in result for result in results)
                assert any("video2.mp4" in result for result in results)

    def test_process_directory_with_parsing(self):
        """Test directory processing with parse function."""

        def mock_parse(file_path):
            return f"parsed_{Path(file_path).name}"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "video1.mkv").touch()
            (temp_path / "video2.mp4").touch()
            (temp_path / "document.txt").touch()

            with ScanParsePool(parse_function=mock_parse, max_workers=2) as pool:
                results = list(pool.process_directory(temp_path))

                # Should yield parsed results
                assert len(results) == 2
                assert any("parsed_video1.mkv" in result for result in results)
                assert any("parsed_video2.mp4" in result for result in results)

    def test_process_directory_nested_structure(self):
        """Test processing directory with nested structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested structure
            (temp_path / "video1.mkv").touch()
            subdir = temp_path / "subdir"
            subdir.mkdir()
            (subdir / "video2.mp4").touch()
            (subdir / "document.txt").touch()

            with ScanParsePool(max_workers=2) as pool:
                results = list(pool.process_directory(temp_path))

                # Should find files in both root and subdirectory
                assert len(results) == 2
                assert any("video1.mkv" in result for result in results)
                assert any("video2.mp4" in result for result in results)

    def test_process_directory_not_running(self):
        """Test that processing directory with non-running pool raises error."""
        pool = ScanParsePool(max_workers=2)

        with pytest.raises(RuntimeError, match="ThreadPoolExecutor not started"):
            list(pool.process_directory("/some/path"))

    def test_get_stats(self):
        """Test getting thread pool statistics."""
        pool = ScanParsePool(max_workers=4, parse_function=lambda x: x)

        stats = pool.get_stats()

        assert stats["is_running"] is False
        assert stats["max_workers"] == 4
        assert stats["has_extension_filter"] is True
        assert stats["has_parse_function"] is True

    def test_get_stats_running(self):
        """Test getting statistics from running pool."""
        with ScanParsePool(max_workers=2) as pool:
            stats = pool.get_stats()

            assert stats["is_running"] is True
            assert stats["max_workers"] == 2

    def test_parse_function_error_handling(self):
        """Test error handling in parse function."""

        def failing_parse(file_path):
            raise ValueError(f"Parse error for {file_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "video.mkv").touch()

            with ScanParsePool(parse_function=failing_parse, max_workers=2) as pool:
                # Should handle parse errors gracefully
                results = list(pool.process_directory(temp_path))
                # Should yield empty results due to parse error
                assert len(results) == 0

    def test_scan_task_error_handling(self):
        """Test error handling in scan tasks."""
        with ScanParsePool(max_workers=2) as pool:
            # Test with non-existent directory
            future = pool.submit_scan_task("/nonexistent/path")
            file_paths = future.result()

            # Should return empty list for non-existent directory
            assert len(file_paths) == 0

    @pytest.mark.slow
    def test_concurrent_processing(self):
        """Test concurrent processing with multiple tasks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create multiple subdirectories with files
            for i in range(5):
                subdir = temp_path / f"dir_{i}"
                subdir.mkdir()
                (subdir / f"video_{i}.mkv").touch()
                (subdir / f"document_{i}.txt").touch()

            def mock_parse(file_path):
                # Simulate some processing time
                time.sleep(0.01)
                return f"parsed_{Path(file_path).name}"

            with ScanParsePool(parse_function=mock_parse, max_workers=3) as pool:
                results = list(pool.process_directory(temp_path))

                # Should find 5 video files
                assert len(results) == 5
                assert all("parsed_video_" in result for result in results)

    def test_extension_filter_integration(self):
        """Test integration between ScanParsePool and extension filters."""
        # Create a custom filter that only accepts .mkv files
        custom_filter = create_media_extension_filter([".mkv"])

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different extensions
            (temp_path / "movie.mkv").touch()
            (temp_path / "video.mp4").touch()
            (temp_path / "film.avi").touch()
            (temp_path / "document.txt").touch()

            with ScanParsePool(extension_filter=custom_filter, max_workers=2) as pool:
                results = list(pool.process_directory(temp_path))

                # Should only find .mkv file
                assert len(results) == 1
                assert "movie.mkv" in results[0]

    def test_thread_pool_executor_integration(self):
        """Test that ScanParsePool properly integrates with ThreadPoolExecutor."""
        with ScanParsePool(max_workers=2) as pool:
            # Verify that the internal executor is properly configured
            assert pool._executor is not None
            assert isinstance(pool._executor, ThreadPoolExecutor)
            assert pool._executor._max_workers == 2
