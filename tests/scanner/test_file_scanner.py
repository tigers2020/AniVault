"""Tests for the file scanner module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from anivault.scanner.file_scanner import (
    get_media_files_count,
    scan_directory,
    scan_directory_paths,
    scan_directory_with_stats,
)


class TestFileScanner:
    """Test cases for the file scanner functionality."""

    def test_scan_directory_basic(self):
        """Test basic directory scanning functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "video1.mkv").touch()
            (temp_path / "video2.mp4").touch()
            (temp_path / "document.txt").touch()

            # Create subdirectory with more files
            subdir = temp_path / "subdir"
            subdir.mkdir()
            (subdir / "video3.avi").touch()
            (subdir / "video4.mov").touch()
            (subdir / "readme.txt").touch()

            # Scan directory
            files = list(scan_directory(temp_path))

            # Should find 4 media files
            assert len(files) == 4

            # Check that all found files are media files
            media_extensions = {".mkv", ".mp4", ".avi", ".mov"}
            for file_entry in files:
                assert any(
                    file_entry.name.lower().endswith(ext) for ext in media_extensions
                )

    def test_scan_directory_with_nested_structure(self):
        """Test scanning with deeply nested directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested structure
            level1 = temp_path / "level1"
            level1.mkdir()
            (level1 / "file1.mkv").touch()

            level2 = level1 / "level2"
            level2.mkdir()
            (level2 / "file2.mp4").touch()

            level3 = level2 / "level3"
            level3.mkdir()
            (level3 / "file3.avi").touch()

            # Scan directory
            files = list(scan_directory(temp_path))

            # Should find 3 media files
            assert len(files) == 3

    def test_scan_directory_permission_error(self):
        """Test handling of permission errors during scanning."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a file
            (temp_path / "video.mkv").touch()

            # Mock os.scandir to raise PermissionError
            with patch("os.scandir", side_effect=PermissionError("Access denied")):
                files = list(scan_directory(temp_path))

                # Should return empty list due to permission error
                assert len(files) == 0

    def test_scan_directory_nonexistent_path(self):
        """Test scanning a non-existent directory."""
        files = list(scan_directory("/nonexistent/path"))
        assert len(files) == 0

    def test_scan_directory_file_instead_of_directory(self):
        """Test scanning a file instead of a directory."""
        with tempfile.NamedTemporaryFile() as temp_file:
            files = list(scan_directory(temp_file.name))
            assert len(files) == 0

    def test_scan_directory_with_stats(self):
        """Test scanning with statistics."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test structure
            (temp_path / "video1.mkv").touch()
            (temp_path / "video2.mp4").touch()
            (temp_path / "document.txt").touch()

            subdir = temp_path / "subdir"
            subdir.mkdir()
            (subdir / "video3.avi").touch()

            # Scan with stats
            files, stats = scan_directory_with_stats(temp_path)
            file_list = list(files)

            # Check results
            assert len(file_list) == 3
            assert stats["files_found"] == 3
            assert stats["directories_scanned"] >= 2  # At least root and subdir
            assert stats["permission_errors"] == 0
            assert stats["other_errors"] == 0

    def test_get_media_files_count(self):
        """Test counting media files without processing them."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "video1.mkv").touch()
            (temp_path / "video2.mp4").touch()
            (temp_path / "document.txt").touch()

            subdir = temp_path / "subdir"
            subdir.mkdir()
            (subdir / "video3.avi").touch()
            (subdir / "video4.mov").touch()

            # Count files
            count = get_media_files_count(temp_path)
            assert count == 4

    def test_media_file_filtering(self):
        """Test that only media files are included in results."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create various file types
            media_files = [
                "video.mkv",
                "movie.mp4",
                "anime.avi",
                "film.mov",
                "show.wmv",
                "episode.flv",
                "content.m4v",
                "stream.webm",
            ]

            non_media_files = [
                "document.txt",
                "image.jpg",
                "audio.mp3",
                "archive.zip",
                "script.py",
                "config.json",
            ]

            # Create all files
            for filename in media_files + non_media_files:
                (temp_path / filename).touch()

            # Scan directory
            files = list(scan_directory(temp_path))

            # Should only find media files
            assert len(files) == len(media_files)

            found_names = {f.name for f in files}
            expected_names = set(media_files)
            assert found_names == expected_names

    def test_case_insensitive_extension_matching(self):
        """Test that extension matching is case-insensitive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create files with different case extensions
            (temp_path / "video1.MKV").touch()
            (temp_path / "video2.Mp4").touch()
            (temp_path / "video3.AVI").touch()
            (temp_path / "video4.mOv").touch()

            # Scan directory
            files = list(scan_directory(temp_path))

            # Should find all files regardless of case
            assert len(files) == 4

    def test_empty_directory(self):
        """Test scanning an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            files = list(scan_directory(temp_dir))
            assert len(files) == 0

    def test_directory_with_only_non_media_files(self):
        """Test scanning a directory with only non-media files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create only non-media files
            (temp_path / "readme.txt").touch()
            (temp_path / "config.json").touch()
            (temp_path / "image.jpg").touch()

            # Scan directory
            files = list(scan_directory(temp_path))

            # Should find no media files
            assert len(files) == 0

    def test_scan_directory_paths_basic(self):
        """Test basic directory path scanning functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "video1.mkv").touch()
            (temp_path / "video2.mp4").touch()
            (temp_path / "document.txt").touch()

            # Scan directory paths
            file_paths = list(scan_directory_paths(temp_path))

            # Should find 2 media files
            assert len(file_paths) == 2

            # Check that all paths are strings
            for path in file_paths:
                assert isinstance(path, str)
                assert any(
                    filename in path for filename in ["video1.mkv", "video2.mp4"]
                )

    def test_scan_directory_paths_vs_scan_directory(self):
        """Test that scan_directory_paths yields same files as scan_directory but as strings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "video1.mkv").touch()
            (temp_path / "video2.mp4").touch()
            (temp_path / "document.txt").touch()

            # Get results from both functions
            dir_entries = list(scan_directory(temp_path))
            file_paths = list(scan_directory_paths(temp_path))

            # Should find same number of files
            assert len(dir_entries) == len(file_paths) == 2

            # Check that paths match
            dir_entry_paths = {entry.path for entry in dir_entries}
            assert set(file_paths) == dir_entry_paths

    @pytest.mark.slow
    def test_large_directory_structure(self):
        """Test scanning a large directory structure (slow test)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a larger structure
            for i in range(100):
                subdir = temp_path / f"dir_{i}"
                subdir.mkdir()

                # Create some media files in each subdirectory
                for j in range(5):
                    (subdir / f"video_{i}_{j}.mkv").touch()
                    (subdir / f"document_{i}_{j}.txt").touch()

            # Scan directory
            files = list(scan_directory(temp_path))

            # Should find 500 media files (100 dirs * 5 files each)
            assert len(files) == 500
