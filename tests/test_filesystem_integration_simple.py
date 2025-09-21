"""Simplified filesystem integration tests."""

import tempfile
import threading
import time
from pathlib import Path

import pytest

from src.core.file_grouper import FileGrouper
from src.core.file_mover import FileMover
from src.core.file_scanner import FileScanner


class TestFileSystemIntegrationSimple:
    """Simplified integration tests for filesystem operations."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        base_dir = Path(tempfile.mkdtemp())
        source_dir = base_dir / "source"
        target_dir = base_dir / "target"

        source_dir.mkdir(parents=True)
        target_dir.mkdir(parents=True)

        yield source_dir, target_dir

        # Clean up
        import shutil

        shutil.rmtree(base_dir, ignore_errors=True)

    def test_file_scanner_basic_scanning(self, temp_dirs) -> None:
        """Test basic file scanning functionality."""
        source_dir, _ = temp_dirs

        # Create test files
        test_files = [
            "Attack on Titan S01E01 [1080p].mkv",
            "Attack on Titan S01E02 [1080p].mkv",
            "One Piece S01E001 [720p].mp4",
        ]

        for filename in test_files:
            file_path = source_dir / filename
            file_path.write_text(f"Test content for {filename}")

        # Test file scanner
        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(source_dir, recursive=True)

        assert scan_result.total_files_found > 0
        assert scan_result.supported_files > 0
        assert len(scan_result.files) > 0
        assert len(scan_result.errors) == 0

        # Verify file data
        for file in scan_result.files:
            assert file.file_path.exists()
            assert file.file_size > 0
            assert file.filename in test_files

    def test_file_grouper_basic_grouping(self, temp_dirs) -> None:
        """Test basic file grouping functionality."""
        source_dir, _ = temp_dirs

        # Create test files
        test_files = [
            "Attack on Titan S01E01 [1080p] [GroupA].mkv",
            "Attack on Titan S01E02 [1080p] [GroupA].mkv",
            "Attack on Titan S01E03 [1080p] [GroupA].mkv",
            "One Piece S01E001 [720p] [GroupB].mp4",
            "One Piece S01E002 [720p] [GroupB].mp4",
            "Naruto S01E01 [1080p] [GroupC].avi",
        ]

        for filename in test_files:
            file_path = source_dir / filename
            file_path.write_text(f"Content for {filename}")

        # Scan files first
        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(source_dir, recursive=True)

        # Group files
        grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)
        grouping_result = grouper.group_files(scan_result.files)

        assert len(grouping_result.groups) > 0
        assert grouping_result.grouped_files > 0
        assert len(grouping_result.ungrouped_files) >= 0

        # Verify grouping makes sense
        for group in grouping_result.groups:
            assert len(group.files) > 0
            # All files in a group should have similar names
            first_name = group.files[0].filename
            for file in group.files[1:]:
                # Basic similarity check (files should share common words)
                common_words = set(first_name.lower().split()) & set(file.filename.lower().split())
                assert len(common_words) > 0

    def test_file_mover_basic_moving(self, temp_dirs) -> None:
        """Test basic file moving functionality."""
        source_dir, target_dir = temp_dirs

        # Create test files
        test_files = [
            "Attack on Titan S01E01 [1080p].mkv",
            "Attack on Titan S01E02 [1080p].mkv",
            "One Piece S01E001 [720p].mp4",
        ]

        for filename in test_files:
            file_path = source_dir / filename
            file_path.write_text(f"Test content for {filename}")

        # Test file mover
        mover = FileMover()

        # Move files one by one
        for filename in test_files:
            source_path = source_dir / filename
            target_path = target_dir / filename

            result = mover.move_file(source_path, target_path)

            # Verify move result
            assert result.success
            assert target_path.exists()
            assert not source_path.exists()
            assert result.file_size > 0

    def test_file_mover_with_directories(self, temp_dirs) -> None:
        """Test file mover with directory creation."""
        source_dir, target_dir = temp_dirs

        # Create test file
        test_file = source_dir / "test.mkv"
        test_file.write_text("Test content")

        # Create subdirectory structure
        target_subdir = target_dir / "anime" / "Attack on Titan" / "Season 1"
        target_path = target_subdir / "test.mkv"

        mover = FileMover()
        result = mover.move_file(test_file, target_path, create_dirs=True)

        # Verify move result
        assert result.success
        assert target_path.exists()
        assert not test_file.exists()
        assert target_subdir.exists()

    def test_file_mover_error_handling(self, temp_dirs) -> None:
        """Test file mover error handling."""
        source_dir, target_dir = temp_dirs

        # Test moving non-existent file
        non_existent_file = source_dir / "non_existent.mkv"
        target_path = target_dir / "non_existent.mkv"

        mover = FileMover()
        result = mover.move_file(non_existent_file, target_path)

        # Should fail gracefully
        assert not result.success
        assert (
            "not found" in result.error_message.lower()
            or "does not exist" in result.error_message.lower()
        )

    def test_file_mover_concurrent_operations(self, temp_dirs) -> None:
        """Test file mover with concurrent operations."""
        source_dir, target_dir = temp_dirs

        # Create test files
        test_files = [f"anime_{i}.mkv" for i in range(5)]
        for filename in test_files:
            file_path = source_dir / filename
            file_path.write_text(f"Content for {filename}")

        results = []

        def move_worker(filename: str) -> None:
            """Worker function for concurrent move operations."""
            try:
                mover = FileMover()
                source_path = source_dir / filename
                target_path = target_dir / filename

                result = mover.move_file(source_path, target_path)
                results.append((filename, result.success))

            except Exception as e:
                results.append((filename, str(e)))

        # Start multiple threads
        threads = []
        for filename in test_files:
            thread = threading.Thread(target=move_worker, args=(filename,))
            thread.start()
            threads.append(thread)
            time.sleep(0.01)  # Small delay to stagger operations

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)

        # Verify results
        assert len(results) == len(test_files)

        # Most operations should succeed
        success_count = sum(1 for _, success in results if success is True)
        assert success_count >= len(test_files) * 0.8  # At least 80% success rate

    def test_file_scanner_with_different_extensions(self, temp_dirs) -> None:
        """Test file scanner with different file extensions."""
        source_dir, _ = temp_dirs

        # Create test files with different extensions
        test_files = [
            "anime1.mkv",
            "anime2.mp4",
            "anime3.avi",
            "anime4.mov",
            "anime5.wmv",
            "document.txt",  # Should be ignored
            "image.jpg",  # Should be ignored
        ]

        for filename in test_files:
            file_path = source_dir / filename
            file_path.write_text(f"Content for {filename}")

        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(source_dir, recursive=True)

        # Should find video files but ignore non-video files
        assert scan_result.total_files_found >= 5  # At least the video files
        assert scan_result.supported_files >= 5

        # Check that video files are found
        found_filenames = [file.filename for file in scan_result.files]
        for ext in [".mkv", ".mp4", ".avi", ".mov", ".wmv"]:
            assert any(filename.endswith(ext) for filename in found_filenames)

    def test_file_scanner_recursive_scanning(self, temp_dirs) -> None:
        """Test file scanner with recursive directory scanning."""
        source_dir, _ = temp_dirs

        # Create nested directory structure
        subdir1 = source_dir / "Season1"
        subdir2 = source_dir / "Season2"
        subdir3 = source_dir / "Extras"

        subdir1.mkdir()
        subdir2.mkdir()
        subdir3.mkdir()

        # Create files in different directories
        test_files = [
            (subdir1 / "episode1.mkv", "Episode 1 content"),
            (subdir1 / "episode2.mkv", "Episode 2 content"),
            (subdir2 / "episode1.mkv", "Season 2 Episode 1 content"),
            (subdir2 / "episode2.mkv", "Season 2 Episode 2 content"),
            (subdir3 / "special.mkv", "Special episode content"),
        ]

        for file_path, content in test_files:
            file_path.write_text(content)

        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(source_dir, recursive=True)

        # Should find all files in subdirectories
        assert scan_result.total_files_found >= 5
        assert scan_result.supported_files >= 5

        # Check that files from all subdirectories are found
        found_paths = [str(file.file_path) for file in scan_result.files]
        for file_path, _ in test_files:
            assert str(file_path) in found_paths
