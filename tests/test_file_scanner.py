"""
Tests for the file scanner module.

This module contains comprehensive tests for the FileScanner class and related functionality.
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.core.file_scanner import FileScanner, ScanResult, scan_directory
from src.core.models import AnimeFile


class TestFileScanner:
    """Test cases for FileScanner class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.scanner = FileScanner(max_workers=2)

        # Create test files with various extensions
        self.test_files = [
            "anime_episode_01.mkv",
            "anime_episode_02.mp4",
            "anime_episode_03.avi",
            "document.txt",
            "image.jpg",
            "subdirectory/anime_episode_04.mkv",
            "subdirectory/anime_episode_05.mp4",
            "nested/deep/anime_episode_06.avi",
        ]

        # Create test directory structure
        for file_path in self.test_files:
            full_path = self.temp_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text("test content")

    def teardown_method(self) -> None:
        """Clean up test fixtures after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_scan_directory_basic(self) -> None:
        """Test basic directory scanning functionality."""
        result = self.scanner.scan_directory(self.temp_dir, recursive=True)

        assert isinstance(result, ScanResult)
        assert result.total_files_found == len(self.test_files)
        assert result.supported_files == 6  # Only video files
        assert result.scan_duration > 0
        assert len(result.files) == 6
        assert len(result.errors) == 0

    def test_scan_directory_non_recursive(self) -> None:
        """Test non-recursive directory scanning."""
        result = self.scanner.scan_directory(self.temp_dir, recursive=False)

        # Should only find files in the root directory
        assert result.total_files_found == 5  # 3 video + 2 non-video files
        assert result.supported_files == 3  # Only video files
        assert len(result.files) == 3

    def test_scan_directory_nonexistent(self) -> None:
        """Test scanning a non-existent directory."""
        nonexistent_dir = self.temp_dir / "nonexistent"
        result = self.scanner.scan_directory(nonexistent_dir)

        assert len(result.files) == 0
        assert len(result.errors) > 0
        assert "does not exist" in result.errors[0]

    def test_scan_directory_file_not_directory(self) -> None:
        """Test scanning a file instead of a directory."""
        test_file = self.temp_dir / "test_file.txt"
        test_file.write_text("test")

        result = self.scanner.scan_directory(test_file)

        assert len(result.files) == 0
        assert len(result.errors) > 0
        assert "not a directory" in result.errors[0]

    def test_supported_extensions(self) -> None:
        """Test supported file extensions."""
        extensions = FileScanner.get_supported_extensions()

        assert ".mkv" in extensions
        assert ".mp4" in extensions
        assert ".avi" in extensions
        assert ".txt" not in extensions
        assert ".jpg" not in extensions

    def test_add_remove_supported_extension(self) -> None:
        """Test adding and removing supported extensions."""
        # Add new extension
        FileScanner.add_supported_extension(".test")
        assert ".test" in FileScanner.get_supported_extensions()

        # Remove extension
        FileScanner.remove_supported_extension(".test")
        assert ".test" not in FileScanner.get_supported_extensions()

    def test_anime_file_creation(self) -> None:
        """Test AnimeFile object creation from file paths."""
        test_file = self.temp_dir / "test_anime.mkv"
        test_file.write_text("test content")

        anime_file = self.scanner._create_anime_file(test_file)

        assert isinstance(anime_file, AnimeFile)
        assert anime_file.file_path == test_file
        assert anime_file.filename == "test_anime.mkv"
        assert anime_file.file_extension == ".mkv"
        assert anime_file.file_size > 0
        assert isinstance(anime_file.created_at, datetime)
        assert isinstance(anime_file.modified_at, datetime)

    def test_anime_file_creation_nonexistent(self) -> None:
        """Test AnimeFile creation with non-existent file."""
        nonexistent_file = self.temp_dir / "nonexistent.mkv"

        with pytest.raises(Exception):
            self.scanner._create_anime_file(nonexistent_file)

    def test_progress_callback(self) -> None:
        """Test progress callback functionality."""
        progress_calls = []

        def progress_callback(progress, message):
            progress_calls.append((progress, message))

        scanner = FileScanner(progress_callback=progress_callback)
        result = scanner.scan_directory(self.temp_dir, recursive=True)

        assert len(progress_calls) > 0
        assert any("Found" in msg for _, msg in progress_calls)
        assert any("Scan completed" in msg for _, msg in progress_calls)

    def test_cancel_scan(self) -> None:
        """Test scan cancellation functionality."""
        self.scanner.cancel_scan()
        assert self.scanner._cancelled is True

        self.scanner.reset()
        assert self.scanner._cancelled is False

    def test_scan_result_properties(self) -> None:
        """Test ScanResult properties and methods."""
        result = self.scanner.scan_directory(self.temp_dir, recursive=True)

        assert result.success_rate > 0
        assert result.success_rate <= 100

    def test_scan_with_symlinks(self) -> None:
        """Test scanning with symbolic links."""
        # Create a symlink (skip on Windows if not supported)
        try:
            symlink_target = self.temp_dir / "symlink_target.mkv"
            symlink_target.write_text("test")

            symlink = self.temp_dir / "symlink.mkv"
            symlink.symlink_to(symlink_target)

            result = self.scanner.scan_directory(
                self.temp_dir, recursive=True, follow_symlinks=True
            )

            # Should find the symlinked file
            assert result.supported_files >= 6  # Original files + symlink
        except (OSError, NotImplementedError):
            # Symlinks not supported on this platform
            pytest.skip("Symbolic links not supported on this platform")

    def test_scan_permission_error(self) -> None:
        """Test handling of permission errors."""
        # Create a directory that we can't read (simulate permission error)
        restricted_dir = self.temp_dir / "restricted"
        restricted_dir.mkdir()

        # On Unix systems, we can change permissions
        if os.name != "nt":  # Not Windows
            try:
                os.chmod(restricted_dir, 0o000)  # No permissions

                result = self.scanner.scan_directory(self.temp_dir, recursive=True)

                # Should still process other files
                assert result.supported_files > 0
            finally:
                # Restore permissions for cleanup
                os.chmod(restricted_dir, 0o755)

    def test_parallel_processing(self) -> None:
        """Test parallel processing with multiple workers."""
        scanner = FileScanner(max_workers=4)
        result = scanner.scan_directory(self.temp_dir, recursive=True)

        assert result.supported_files == 6
        assert len(result.files) == 6

    def test_empty_directory(self) -> None:
        """Test scanning an empty directory."""
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()

        result = self.scanner.scan_directory(empty_dir)

        assert result.total_files_found == 0
        assert result.supported_files == 0
        assert len(result.files) == 0
        assert len(result.errors) == 0


class TestScanDirectoryFunction:
    """Test cases for the scan_directory convenience function."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create test files
        test_files = ["test1.mkv", "test2.mp4", "test3.avi"]
        for file_name in test_files:
            (self.temp_dir / file_name).write_text("test content")

    def teardown_method(self) -> None:
        """Clean up test fixtures after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_scan_directory_function(self) -> None:
        """Test the scan_directory convenience function."""
        result = scan_directory(self.temp_dir, recursive=True, max_workers=2)

        assert isinstance(result, ScanResult)
        assert result.supported_files == 3
        assert len(result.files) == 3

    def test_scan_directory_with_callback(self) -> None:
        """Test scan_directory with progress callback."""
        progress_calls = []

        def progress_callback(progress, message):
            progress_calls.append((progress, message))

        result = scan_directory(
            self.temp_dir, recursive=True, max_workers=2, progress_callback=progress_callback
        )

        assert len(progress_calls) > 0
        assert result.supported_files == 3


class TestFileScannerPerformance:
    """Performance tests for FileScanner."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create many test files for performance testing
        self.file_count = 100
        for i in range(self.file_count):
            file_name = f"anime_episode_{i:03d}.mkv"
            (self.temp_dir / file_name).write_text("test content")

    def teardown_method(self) -> None:
        """Clean up test fixtures after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_scan_performance(self) -> None:
        """Test scanning performance with many files."""
        scanner = FileScanner(max_workers=4)

        start_time = datetime.now()
        result = scanner.scan_directory(self.temp_dir, recursive=True)
        end_time = datetime.now()

        duration = (end_time - start_time).total_seconds()

        assert result.supported_files == self.file_count
        assert duration < 10.0  # Should complete within 10 seconds
        assert result.files_per_second > 10  # Should process at least 10 files per second

    def test_memory_usage(self) -> None:
        """Test memory usage during scanning."""
        scanner = FileScanner(max_workers=2)

        # This is a basic test - in a real scenario, you'd use memory profiling
        result = scanner.scan_directory(self.temp_dir, recursive=True)

        assert result.supported_files == self.file_count
        assert len(result.files) == self.file_count

        # Verify all files were created correctly
        for anime_file in result.files:
            assert anime_file.file_size > 0
            assert anime_file.file_extension == ".mkv"
