"""Unit tests for DirectoryScanner class.

This module contains comprehensive tests for the directory scanner
that acts as a producer in the file processing pipeline.
"""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from anivault.core.pipeline.scanner import DirectoryScanner
from anivault.core.pipeline.utils import BoundedQueue, ScanStatistics
from anivault.core.filter import FilterEngine
from anivault.config import FilterConfig


class TestDirectoryScanner:
    """Test cases for DirectoryScanner class."""

    def test_init_with_valid_parameters(self) -> None:
        """Test DirectoryScanner initialization with valid parameters."""
        root_path = Path("/test/path")
        extensions = [".mp4", ".mkv", ".avi"]
        input_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ScanStatistics)

        scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

        assert scanner.root_path == root_path
        assert scanner.extensions == {".mp4", ".mkv", ".avi"}
        assert scanner.input_queue == input_queue
        assert scanner.stats == stats

    def test_init_normalizes_extensions(self) -> None:
        """Test that extensions are normalized to lowercase."""
        root_path = Path("/test/path")
        extensions = [".MP4", ".Mkv", ".AVI"]
        input_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ScanStatistics)

        scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

        assert scanner.extensions == {".mp4", ".mkv", ".avi"}

    def test_scan_files_empty_directory(self) -> None:
        """Test scan_files with an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)
            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

            files = list(scanner.scan_files())
            assert len(files) == 0

    def test_scan_files_matching_extensions(self) -> None:
        """Test scan_files finds files with matching extensions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create test files
            (root_path / "video1.mp4").touch()
            (root_path / "video2.mkv").touch()
            (root_path / "video3.avi").touch()
            (root_path / "document.txt").touch()  # Should be ignored
            (root_path / "image.jpg").touch()  # Should be ignored

            extensions = [".mp4", ".mkv", ".avi"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

            files = list(scanner.scan_files())
            assert len(files) == 3

            # Check that all files are absolute paths
            for file_path in files:
                assert file_path.is_absolute()

            # Check that we got the expected files
            file_names = {f.name for f in files}
            assert file_names == {"video1.mp4", "video2.mkv", "video3.avi"}

    def test_scan_files_with_subdirectories(self) -> None:
        """Test scan_files with files in subdirectories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create subdirectories and files
            subdir1 = root_path / "season1"
            subdir2 = root_path / "season2"
            subdir1.mkdir()
            subdir2.mkdir()

            (subdir1 / "episode1.mp4").touch()
            (subdir1 / "episode2.mp4").touch()
            (subdir2 / "episode1.mkv").touch()
            (subdir2 / "episode2.mkv").touch()
            (root_path / "intro.mp4").touch()

            extensions = [".mp4", ".mkv"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

            files = list(scanner.scan_files())
            assert len(files) == 5

            # Check that we got files from all directories
            file_names = {f.name for f in files}
            expected_names = {
                "episode1.mp4",
                "episode2.mp4",
                "episode1.mkv",
                "episode2.mkv",
                "intro.mp4",
            }
            assert file_names == expected_names

    def test_scan_files_case_insensitive_extensions(self) -> None:
        """Test scan_files is case insensitive for extensions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create test files with different case extensions
            (root_path / "video1.MP4").touch()
            (root_path / "video2.Mkv").touch()
            (root_path / "video3.avi").touch()

            extensions = [".mp4", ".mkv"]  # Lowercase
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

            files = list(scanner.scan_files())
            assert len(files) == 2

            file_names = {f.name for f in files}
            assert file_names == {"video1.MP4", "video2.Mkv"}

    def test_scan_files_nonexistent_directory(self) -> None:
        """Test scan_files with non-existent directory."""
        root_path = Path("/nonexistent/directory")
        extensions = [".mp4"]
        input_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ScanStatistics)

        scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

        files = list(scanner.scan_files())
        assert len(files) == 0

    def test_scan_files_file_as_root(self) -> None:
        """Test scan_files when root_path is a file, not a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)
            test_file = root_path / "test.mp4"
            test_file.touch()

            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            # Use the file as root_path instead of directory
            scanner = DirectoryScanner(test_file, extensions, input_queue, stats)

            files = list(scanner.scan_files())
            assert len(files) == 0  # Should not find anything

    def test_run_successful_scan(self) -> None:
        """Test run method with successful scan."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create test files
            (root_path / "video1.mp4").touch()
            (root_path / "video2.mkv").touch()
            (root_path / "document.txt").touch()  # Should be ignored

            extensions = [".mp4", ".mkv"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(root_path, extensions, input_queue, stats)
            scanner.run()

            # Verify that put was called for each matching file + sentinel
            assert input_queue.put.call_count == 3  # 2 files + 1 sentinel

            # Verify that statistics were updated
            assert stats.increment_files_scanned.call_count == 2
            assert stats.increment_directories_scanned.call_count == 1

    def test_run_nonexistent_directory(self) -> None:
        """Test run method with non-existent directory."""
        root_path = Path("/nonexistent/directory")
        extensions = [".mp4"]
        input_queue = Mock(spec=BoundedQueue)
        stats = Mock(spec=ScanStatistics)

        scanner = DirectoryScanner(root_path, extensions, input_queue, stats)
        scanner.run()

        # Should only put sentinel (directory doesn't exist)
        assert input_queue.put.call_count == 1  # Only sentinel

    def test_run_file_as_root(self) -> None:
        """Test run method when root_path is a file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)
            test_file = root_path / "test.mp4"
            test_file.touch()

            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(test_file, extensions, input_queue, stats)
            scanner.run()

            # Should only put sentinel (file, not directory)
            assert input_queue.put.call_count == 1  # Only sentinel

    def test_run_queue_error_handling(self) -> None:
        """Test run method handles queue errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)
            (root_path / "video1.mp4").touch()

            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            input_queue.put.side_effect = Exception("Queue error")
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

            # Should not raise exception
            scanner.run()

            # Should put the file + sentinel (even though both fail)
            assert input_queue.put.call_count == 2  # 1 file + 1 sentinel attempt

    def test_run_queue_put_error_handling(self) -> None:
        """Test run method handles queue put errors gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)
            (root_path / "test.mp4").touch()

            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            input_queue.put.side_effect = Exception("Queue error")
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

            # Should not raise exception
            scanner.run()

    def test_get_scan_summary(self) -> None:
        """Test get_scan_summary method."""
        root_path = Path("/test/path")
        extensions = [".mp4", ".mkv"]
        input_queue = Mock(spec=BoundedQueue)
        input_queue.qsize.return_value = 5
        input_queue.maxsize = 100
        stats = Mock(spec=ScanStatistics)
        stats.files_scanned = 10
        stats.directories_scanned = 3

        scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

        summary = scanner.get_scan_summary()

        assert summary["root_path"] == str(root_path)
        assert set(summary["extensions"]) == {".mp4", ".mkv"}
        assert summary["files_scanned"] == 10
        assert summary["directories_scanned"] == 3
        assert summary["queue_size"] == 5
        assert summary["queue_maxsize"] == 100

    def test_scan_files_updates_directory_stats(self) -> None:
        """Test that scan_files updates directory statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create subdirectories
            subdir1 = root_path / "season1"
            subdir2 = root_path / "season2"
            subdir1.mkdir()
            subdir2.mkdir()

            (subdir1 / "episode1.mp4").touch()
            (subdir2 / "episode1.mp4").touch()

            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

            # Call scan_files to trigger directory counting
            list(scanner.scan_files())

            # Should have counted 3 directories (root + 2 subdirs)
            assert stats.increment_directories_scanned.call_count == 3

    def test_scan_files_with_symlinks(self) -> None:
        """Test scan_files handles symlinks correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create a real file
            real_file = root_path / "real_video.mp4"
            real_file.touch()

            # Create a symlink (if supported on the platform)
            try:
                symlink_file = root_path / "symlink_video.mp4"
                symlink_file.symlink_to(real_file)

                extensions = [".mp4"]
                input_queue = Mock(spec=BoundedQueue)
                stats = Mock(spec=ScanStatistics)

                scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

                files = list(scanner.scan_files())

                # Should find both the real file and the symlink
                assert len(files) == 2

                file_names = {f.name for f in files}
                assert file_names == {"real_video.mp4", "symlink_video.mp4"}

            except OSError:
                # Symlinks not supported on this platform, skip test
                pytest.skip("Symlinks not supported on this platform")

    def test_scan_files_with_hidden_files(self) -> None:
        """Test scan_files includes hidden files if they match extensions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create hidden files
            (root_path / ".hidden_video.mp4").touch()
            (root_path / "normal_video.mp4").touch()

            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(root_path, extensions, input_queue, stats)

            files = list(scanner.scan_files())

            # Should find both hidden and normal files
            assert len(files) == 2

            file_names = {f.name for f in files}
            assert file_names == {".hidden_video.mp4", "normal_video.mp4"}


class TestDirectoryScannerStreamingAPI:
    """Test cases for DirectoryScanner streaming API (scan method)."""

    def test_scan_returns_batches(self) -> None:
        """Test that scan() returns batches of files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create test files
            for i in range(15):
                (root_path / f"video{i}.mp4").touch()

            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            # Create scanner with small batch size
            scanner = DirectoryScanner(
                root_path, extensions, input_queue, stats, batch_size=5
            )

            # Collect all batches
            batches = list(scanner.scan())

            # Should have 3 batches (5 + 5 + 5)
            assert len(batches) == 3
            assert all(isinstance(batch, list) for batch in batches)
            assert all(len(batch) == 5 for batch in batches)

    def test_scan_with_partial_batch(self) -> None:
        """Test that scan() handles partial last batch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create test files
            for i in range(12):
                (root_path / f"video{i}.mp4").touch()

            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            # Create scanner with batch size of 5
            scanner = DirectoryScanner(
                root_path, extensions, input_queue, stats, batch_size=5
            )

            # Collect all batches
            batches = list(scanner.scan())

            # Should have 3 batches (5 + 5 + 2)
            assert len(batches) == 3
            assert len(batches[0]) == 5
            assert len(batches[1]) == 5
            assert len(batches[2]) == 2  # Partial batch

    def test_scan_with_backpressure(self) -> None:
        """Test scan_with_backpressure() respects queue limits."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create test files
            for i in range(20):
                (root_path / f"video{i}.mp4").touch()

            extensions = [".mp4"]
            input_queue = BoundedQueue(maxsize=5)  # Real queue
            output_queue = BoundedQueue(maxsize=3)  # Small queue for backpressure
            stats = ScanStatistics()

            # Create scanner with small batch size
            scanner = DirectoryScanner(
                root_path, extensions, input_queue, stats, batch_size=3
            )

            # Collect batches with backpressure
            batches = []
            for batch in scanner.scan_with_backpressure(output_queue):
                batches.append(batch)
                # Stop after a few batches
                if len(batches) >= 5:
                    break

            # Should have collected 5 batches
            assert len(batches) == 5
            assert all(isinstance(batch, list) for batch in batches)

    def test_scan_with_filtering(self) -> None:
        """Test scan() with FilterEngine integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)

            # Create test files with different sizes
            for i in range(10):
                file_path = root_path / f"video{i}.mp4"
                with open(file_path, "wb") as f:
                    # Create files with varying sizes (some small, some large)
                    f.write(b"x" * (i * 1024 * 1024))  # i MB

            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            # Create filter config that only allows files >= 3MB
            filter_config = FilterConfig()
            filter_config.min_file_size_mb = 3
            filter_config.excluded_filename_patterns = []
            filter_engine = FilterEngine(filter_config)

            # Create scanner with filtering
            scanner = DirectoryScanner(
                root_path,
                extensions,
                input_queue,
                stats,
                filter_engine=filter_engine,
                batch_size=5,
            )

            # Collect all files
            all_files = []
            for batch in scanner.scan():
                all_files.extend(batch)

            # Should only have files >= 3MB (video3 through video9)
            assert len(all_files) == 7  # Files 3-9
            assert all("video" in str(f.name) for f in all_files)

    def test_scan_empty_directory(self) -> None:
        """Test scan() with empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)
            extensions = [".mp4"]
            input_queue = Mock(spec=BoundedQueue)
            stats = Mock(spec=ScanStatistics)

            scanner = DirectoryScanner(
                root_path, extensions, input_queue, stats, batch_size=5
            )

            batches = list(scanner.scan())

            # Should have no batches
            assert len(batches) == 0
