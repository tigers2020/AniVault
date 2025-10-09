"""Unit tests for DirectoryScanner."""

import os
import tempfile
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

import pytest

from anivault.core.pipeline.scanner import DirectoryScanner
from anivault.core.pipeline.utils import BoundedQueue, ScanStatistics
from anivault.shared.constants import FileSystem


class TestDirectoryScanner:
    """Test cases for DirectoryScanner class."""

    @pytest.fixture
    def scanner(self):
        """Create a DirectoryScanner instance for testing."""
        input_queue = BoundedQueue(maxsize=100)
        stats = ScanStatistics()

        return DirectoryScanner(
            root_path="/tmp",  # Will be overridden in tests
            extensions=FileSystem.SUPPORTED_VIDEO_EXTENSIONS,
            input_queue=input_queue,
            stats=stats,
            parallel=True,
            max_workers=2,
        )

    @pytest.fixture
    def temp_test_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as temp_path:
            test_dir = Path(temp_path)

            # Create test files
            (test_dir / "video1.mp4").write_bytes(b"fake video content")
            (test_dir / "video2.mkv").write_bytes(b"fake video content")
            (test_dir / "readme.txt").write_bytes(b"text file")

            # Create subdirectory
            subdir = test_dir / "subdir"
            subdir.mkdir()
            (subdir / "video3.avi").write_bytes(b"fake video content")
            (subdir / "video4.mp4").write_bytes(b"fake video content")

            yield test_dir

    def test_parallel_scan_directory_basic(self, temp_test_dir):
        """Test basic parallel directory scanning functionality."""
        # Given
        input_queue = BoundedQueue(maxsize=100)
        stats = ScanStatistics()

        scanner = DirectoryScanner(
            root_path=str(temp_test_dir),
            extensions=FileSystem.SUPPORTED_VIDEO_EXTENSIONS,
            input_queue=input_queue,
            stats=stats,
            parallel=True,
            max_workers=2,
        )

        # When
        files, dirs_scanned = scanner._parallel_scan_directory(temp_test_dir)

        # Then
        assert isinstance(files, list)
        assert isinstance(dirs_scanned, int)
        assert dirs_scanned >= 1  # At least the root directory

        # Should find video files but not text files
        video_files = [
            f for f in files if f.suffix in FileSystem.SUPPORTED_VIDEO_EXTENSIONS
        ]
        text_files = [f for f in files if f.suffix == ".txt"]

        assert len(video_files) == 4  # 2 in root + 2 in subdir
        assert len(text_files) == 0  # Should be filtered out

    def test_parallel_scan_directory_nonexistent(self):
        """Test scanning a non-existent directory."""
        # Given
        input_queue = BoundedQueue(maxsize=100)
        stats = ScanStatistics()

        scanner = DirectoryScanner(
            root_path="/tmp",
            extensions=FileSystem.SUPPORTED_VIDEO_EXTENSIONS,
            input_queue=input_queue,
            stats=stats,
            parallel=True,
            max_workers=2,
        )

        # When
        files, dirs_scanned = scanner._parallel_scan_directory(
            Path("/nonexistent/path")
        )

        # Then
        assert files == []
        assert dirs_scanned == 0

    def test_parallel_scan_directory_file_not_dir(self, temp_test_dir):
        """Test scanning a file instead of directory."""
        # Given
        input_queue = BoundedQueue(maxsize=100)
        stats = ScanStatistics()

        scanner = DirectoryScanner(
            root_path="/tmp",
            extensions=FileSystem.SUPPORTED_VIDEO_EXTENSIONS,
            input_queue=input_queue,
            stats=stats,
            parallel=True,
            max_workers=2,
        )

        # When
        files, dirs_scanned = scanner._parallel_scan_directory(
            temp_test_dir / "video1.mp4"
        )

        # Then
        assert files == []
        assert dirs_scanned == 0

    def test_parallel_scan_directory_with_stop_event(self, temp_test_dir):
        """Test that scanning respects stop event."""
        # Given
        input_queue = BoundedQueue(maxsize=100)
        stats = ScanStatistics()

        scanner = DirectoryScanner(
            root_path="/tmp",
            extensions=FileSystem.SUPPORTED_VIDEO_EXTENSIONS,
            input_queue=input_queue,
            stats=stats,
            parallel=True,
            max_workers=2,
        )
        scanner._stop_event.set()  # Set stop event

        # When
        files, dirs_scanned = scanner._parallel_scan_directory(temp_test_dir)

        # Then
        assert files == []
        # Even with stop event, the current directory is still counted
        assert dirs_scanned == 1

    def test_parallel_scan_directory_empty_directory(self):
        """Test scanning an empty directory."""
        # Given
        input_queue = BoundedQueue(maxsize=100)
        stats = ScanStatistics()

        scanner = DirectoryScanner(
            root_path="/tmp",
            extensions=FileSystem.SUPPORTED_VIDEO_EXTENSIONS,
            input_queue=input_queue,
            stats=stats,
            parallel=True,
            max_workers=2,
        )

        with tempfile.TemporaryDirectory() as temp_path:
            empty_dir = Path(temp_path)

            # When
            files, dirs_scanned = scanner._parallel_scan_directory(empty_dir)

            # Then
            assert files == []
            assert dirs_scanned == 1  # The directory itself was scanned

    def test_is_valid_directory(self, temp_test_dir):
        """Test directory validation helper method."""
        # Given
        input_queue = BoundedQueue(maxsize=100)
        stats = ScanStatistics()

        scanner = DirectoryScanner(
            root_path="/tmp",
            extensions=FileSystem.SUPPORTED_VIDEO_EXTENSIONS,
            input_queue=input_queue,
            stats=stats,
            parallel=True,
            max_workers=2,
        )

        # When & Then
        assert scanner._is_valid_directory(temp_test_dir) is True
        assert scanner._is_valid_directory(Path("/nonexistent")) is False
        assert scanner._is_valid_directory(temp_test_dir / "video1.mp4") is False

    def test_process_file_entry(self, temp_test_dir):
        """Test file entry processing helper method."""
        # Given
        input_queue = BoundedQueue(maxsize=100)
        stats = ScanStatistics()

        scanner = DirectoryScanner(
            root_path="/tmp",
            extensions=FileSystem.SUPPORTED_VIDEO_EXTENSIONS,
            input_queue=input_queue,
            stats=stats,
            parallel=True,
            max_workers=2,
        )

        # Create a mock DirEntry for video file
        video_file = temp_test_dir / "test_video.mp4"
        video_file.write_text("test content")

        with os.scandir(temp_test_dir) as entries:
            for entry in entries:
                if entry.name == "test_video.mp4":
                    # When
                    result = scanner._process_file_entry(entry)

                    # Then
                    assert result is not None
                    assert result.name == "test_video.mp4"
                    break

    def test_process_file_entry_non_video(self, temp_test_dir):
        """Test file entry processing with non-video file."""
        # Given
        input_queue = BoundedQueue(maxsize=100)
        stats = ScanStatistics()

        scanner = DirectoryScanner(
            root_path="/tmp",
            extensions=FileSystem.SUPPORTED_VIDEO_EXTENSIONS,
            input_queue=input_queue,
            stats=stats,
            parallel=True,
            max_workers=2,
        )

        # Create a text file
        text_file = temp_test_dir / "test.txt"
        text_file.write_text("test content")

        with os.scandir(temp_test_dir) as entries:
            for entry in entries:
                if entry.name == "test.txt":
                    # When
                    result = scanner._process_file_entry(entry)

                    # Then
                    assert result is None  # Should be filtered out
                    break
