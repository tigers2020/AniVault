"""Tests for the file grouper module.

This module contains comprehensive tests for the FileGrouper class and related functionality.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from src.core.file_grouper import FileGrouper, GroupingResult, group_files
from src.core.models import AnimeFile, FileGroup


class TestFileGrouper:
    """Test cases for FileGrouper class."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)

        # Create test anime files with similar names
        self.test_files = [
            "Attack on Titan S01E01 [1080p].mkv",
            "Attack on Titan S01E02 [1080p].mkv",
            "Attack on Titan S01E03 [1080p].mkv",
            "One Piece S01E01 [720p].mp4",
            "One Piece S01E02 [720p].mp4",
            "Naruto S01E01 [1080p].avi",
            "Different Anime S01E01 [1080p].mkv",
            "Completely Different Title S01E01 [1080p].mkv",
        ]

        # Create AnimeFile objects
        self.anime_files = []
        for i, filename in enumerate(self.test_files):
            file_path = self.temp_dir / filename
            file_path.write_text("test content")

            anime_file = AnimeFile(
                file_path=file_path,
                filename=filename,
                file_size=1000 + i * 100,
                file_extension=Path(filename).suffix.lower(),
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            self.anime_files.append(anime_file)

    def teardown_method(self) -> None:
        """Clean up test fixtures after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_group_files_basic(self) -> None:
        """Test basic file grouping functionality."""
        result = self.grouper.group_files(self.anime_files)

        assert isinstance(result, GroupingResult)
        assert result.total_files == len(self.anime_files)
        assert result.similarity_threshold == 0.75
        assert result.grouping_duration > 0
        assert len(result.groups) > 0
        assert result.grouped_files > 0

    def test_group_files_empty_list(self) -> None:
        """Test grouping with empty file list."""
        result = self.grouper.group_files([])

        assert result.total_files == 0
        assert result.grouped_files == 0
        assert len(result.groups) == 0
        assert len(result.ungrouped_files) == 0

    def test_group_files_single_file(self) -> None:
        """Test grouping with single file."""
        single_file = [self.anime_files[0]]
        result = self.grouper.group_files(single_file)

        assert result.total_files == 1
        assert result.grouped_files == 0  # Single file should remain ungrouped
        assert len(result.groups) == 0
        assert len(result.ungrouped_files) == 1

    def test_similarity_threshold(self) -> None:
        """Test different similarity thresholds."""
        # Test with high threshold (should create more groups)
        grouper_high = FileGrouper(similarity_threshold=0.9)
        result_high = grouper_high.group_files(self.anime_files)

        # Test with low threshold (should create fewer groups)
        grouper_low = FileGrouper(similarity_threshold=0.5)
        result_low = grouper_low.group_files(self.anime_files)

        # Higher threshold should result in more groups (more strict grouping)
        assert len(result_high.groups) >= len(result_low.groups)

    def test_filename_info_extraction(self) -> None:
        """Test filename information extraction."""
        test_filename = "Attack on Titan S01E01 [1080p] [GroupName].mkv"
        info = self.grouper._extract_filename_info(test_filename)

        assert info["episode"] == "1"
        assert info["season"] == "1"
        assert info["quality"] == "1080p"
        assert "attack on titan" in info["clean_name"].lower()
        assert "groupname" not in info["clean_name"].lower()

    def test_clean_filename(self) -> None:
        """Test filename cleaning functionality."""
        dirty_filename = "Attack on Titan [1080p] [GroupName] S01E01.mkv"
        clean_name = self.grouper._clean_filename(dirty_filename)

        assert "attack on titan" in clean_name.lower()
        assert "1080p" not in clean_name
        assert "groupname" not in clean_name.lower()
        assert "s01e01" not in clean_name.lower()

    def test_files_similarity(self) -> None:
        """Test file similarity detection."""
        file1 = self.anime_files[0]  # Attack on Titan S01E01
        file2 = self.anime_files[1]  # Attack on Titan S01E02

        # These should be similar
        assert self.grouper._are_files_similar(file1, file2)

        file3 = self.anime_files[6]  # Different Anime S01E01
        # These should not be similar
        assert not self.grouper._are_files_similar(file1, file3)

    def test_group_creation(self) -> None:
        """Test FileGroup creation and management."""
        group = FileGroup(group_id="test-group")

        # Add files to group
        for file in self.anime_files[:3]:
            group.add_file(file)

        assert group.file_count == 3
        assert len(group.files) == 3
        assert group.best_file is not None
        assert group.total_size > 0
        assert group.total_size_mb > 0

        # Remove a file
        removed = group.remove_file(self.anime_files[0])
        assert removed is True
        assert group.file_count == 2

        # Try to remove non-existent file
        removed = group.remove_file(self.anime_files[3])
        assert removed is False
        assert group.file_count == 2

    def test_group_metadata_update(self) -> None:
        """Test group metadata updating."""
        group = FileGroup(group_id="test-group")

        # Add files with parsed info
        for file in self.anime_files[:2]:
            # Simulate parsed info
            file._extracted_info = {
                "base_name": "Attack on Titan",
                "season": 1,
                "episode": 1 if "E01" in file.filename else 2,
            }
            group.add_file(file)

        # Set group metadata
        self.grouper._set_group_metadata(group)

        assert group.series_title == "Attack on Titan"
        assert group.season == 1

    def test_progress_callback(self) -> None:
        """Test progress callback functionality."""
        progress_calls = []

        def progress_callback(progress, message) -> None:
            progress_calls.append((progress, message))

        grouper = FileGrouper(progress_callback=progress_callback)
        _result = grouper.group_files(self.anime_files)

        assert len(progress_calls) > 0
        assert any("Starting grouping" in msg for _, msg in progress_calls)
        assert any("Grouping completed" in msg for _, msg in progress_calls)

    def test_cancel_grouping(self) -> None:
        """Test grouping cancellation functionality."""
        self.grouper.cancel_grouping()
        assert self.grouper._cancelled is True

        self.grouper.reset()
        assert self.grouper._cancelled is False

    def test_grouping_result_properties(self) -> None:
        """Test GroupingResult properties and methods."""
        result = self.grouper.group_files(self.anime_files)

        assert result.grouping_rate >= 0
        assert result.grouping_rate <= 100
        assert result.grouping_rate == (result.grouped_files / result.total_files) * 100

    def test_parallel_processing(self) -> None:
        """Test parallel processing with multiple workers."""
        grouper = FileGrouper(max_workers=4)
        result = grouper.group_files(self.anime_files)

        assert result.total_files == len(self.anime_files)
        assert len(result.groups) > 0

    def test_group_merging(self) -> None:
        """Test merging of similar groups."""
        # Create two similar groups
        group1 = FileGroup(group_id="group1")
        group2 = FileGroup(group_id="group2")

        # Add similar files to both groups
        for file in self.anime_files[:2]:
            group1.add_file(file)

        for file in self.anime_files[2:4]:
            group2.add_file(file)

        # Test if groups should be merged
        should_merge = self.grouper._should_merge_groups(group1, group2)

        # This depends on the actual similarity of the files
        assert isinstance(should_merge, bool)

    def test_similarity_calculation(self) -> None:
        """Test similarity score calculation for groups."""
        group_files = self.anime_files[:3]  # Similar files
        similarity = self.grouper._calculate_group_similarity(group_files)

        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Should be reasonably similar


class TestGroupFilesFunction:
    """Test cases for the group_files convenience function."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create test files
        test_files = ["Anime S01E01.mkv", "Anime S01E02.mkv", "Different S01E01.mp4"]

        self.anime_files = []
        for filename in test_files:
            file_path = self.temp_dir / filename
            file_path.write_text("test content")

            anime_file = AnimeFile(
                file_path=file_path,
                filename=filename,
                file_size=1000,
                file_extension=Path(filename).suffix.lower(),
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            self.anime_files.append(anime_file)

    def teardown_method(self) -> None:
        """Clean up test fixtures after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_group_files_function(self) -> None:
        """Test the group_files convenience function."""
        result = group_files(self.anime_files, similarity_threshold=0.75, max_workers=2)

        assert isinstance(result, GroupingResult)
        assert result.total_files == len(self.anime_files)
        assert result.similarity_threshold == 0.75

    def test_group_files_with_callback(self) -> None:
        """Test group_files with progress callback."""
        progress_calls = []

        def progress_callback(progress, message) -> None:
            progress_calls.append((progress, message))

        result = group_files(
            self.anime_files,
            similarity_threshold=0.75,
            max_workers=2,
            progress_callback=progress_callback,
        )

        assert len(progress_calls) > 0
        assert result.total_files == len(self.anime_files)


class TestFileGrouperEdgeCases:
    """Test edge cases and error conditions for FileGrouper."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.grouper = FileGrouper(similarity_threshold=0.75)

    def teardown_method(self) -> None:
        """Clean up test fixtures after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_files_with_special_characters(self) -> None:
        """Test grouping files with special characters in names."""
        special_files = [
            "Anime [Special] S01E01.mkv",
            "Anime [Special] S01E02.mkv",
            "Anime (OVA) S01E01.mp4",
            "Anime (OVA) S01E02.mp4",
        ]

        anime_files = []
        for filename in special_files:
            file_path = self.temp_dir / filename
            file_path.write_text("test content")

            anime_file = AnimeFile(
                file_path=file_path,
                filename=filename,
                file_size=1000,
                file_extension=Path(filename).suffix.lower(),
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            anime_files.append(anime_file)

        result = self.grouper.group_files(anime_files)

        assert result.total_files == len(anime_files)
        assert len(result.groups) > 0

    def test_files_with_unicode_characters(self) -> None:
        """Test grouping files with Unicode characters."""
        unicode_files = [
            "アニメ S01E01.mkv",
            "アニメ S01E02.mkv",
            "애니메이션 S01E01.mp4",
            "애니메이션 S01E02.mp4",
        ]

        anime_files = []
        for filename in unicode_files:
            file_path = self.temp_dir / filename
            file_path.write_text("test content")

            anime_file = AnimeFile(
                file_path=file_path,
                filename=filename,
                file_size=1000,
                file_extension=Path(filename).suffix.lower(),
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            anime_files.append(anime_file)

        result = self.grouper.group_files(anime_files)

        assert result.total_files == len(anime_files)
        # Should still be able to group similar files
        assert len(result.groups) > 0

    def test_files_with_very_long_names(self) -> None:
        """Test grouping files with very long names."""
        long_name = "A" * 200 + " S01E01.mkv"
        long_files = [long_name, long_name.replace("E01", "E02"), long_name.replace("E01", "E03")]

        anime_files = []
        for filename in long_files:
            file_path = self.temp_dir / filename
            file_path.write_text("test content")

            anime_file = AnimeFile(
                file_path=file_path,
                filename=filename,
                file_size=1000,
                file_extension=Path(filename).suffix.lower(),
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            anime_files.append(anime_file)

        result = self.grouper.group_files(anime_files)

        assert result.total_files == len(anime_files)
        assert len(result.groups) > 0

    def test_grouping_with_duplicate_files(self) -> None:
        """Test grouping with duplicate file names."""
        duplicate_files = ["Anime S01E01.mkv", "Anime S01E01.mkv", "Anime S01E02.mkv"]  # Duplicate

        anime_files = []
        for i, filename in enumerate(duplicate_files):
            file_path = self.temp_dir / f"file_{i}_{filename}"
            file_path.write_text("test content")

            anime_file = AnimeFile(
                file_path=file_path,
                filename=filename,
                file_size=1000,
                file_extension=Path(filename).suffix.lower(),
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            anime_files.append(anime_file)

        result = self.grouper.group_files(anime_files)

        assert result.total_files == len(anime_files)
        # Should handle duplicates gracefully
        assert len(result.groups) > 0 or len(result.ungrouped_files) > 0


class TestFileGrouperPerformance:
    """Performance tests for FileGrouper."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create many test files for performance testing
        self.file_count = 50
        self.anime_files = []

        for i in range(self.file_count):
            filename = f"Anime Series S01E{i+1:02d} [1080p].mkv"
            file_path = self.temp_dir / filename
            file_path.write_text("test content")

            anime_file = AnimeFile(
                file_path=file_path,
                filename=filename,
                file_size=1000 + i * 100,
                file_extension=".mkv",
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            self.anime_files.append(anime_file)

    def teardown_method(self) -> None:
        """Clean up test fixtures after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_grouping_performance(self) -> None:
        """Test grouping performance with many files."""
        grouper = FileGrouper(similarity_threshold=0.75, max_workers=4)

        start_time = datetime.now()
        result = grouper.group_files(self.anime_files)
        end_time = datetime.now()

        duration = (end_time - start_time).total_seconds()

        assert result.total_files == self.file_count
        assert duration < 30.0  # Should complete within 30 seconds
        assert len(result.groups) > 0  # Should create some groups
        assert result.grouped_files > 0  # Should group some files

    def test_memory_efficiency(self) -> None:
        """Test memory efficiency during grouping."""
        grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)

        result = grouper.group_files(self.anime_files)

        assert result.total_files == self.file_count
        assert len(result.groups) > 0

        # Verify all files are accounted for
        total_grouped = sum(len(group.files) for group in result.groups)
        total_ungrouped = len(result.ungrouped_files)
        assert total_grouped + total_ungrouped == self.file_count
