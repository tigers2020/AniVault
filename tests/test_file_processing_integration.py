"""
Integration tests for file scanning and grouping functionality.

This module contains comprehensive integration tests that test the complete
file processing pipeline from scanning to grouping.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.core.file_grouper import FileGrouper
from src.core.file_scanner import FileScanner
from src.core.performance_optimizer import OptimizedFileProcessor


class TestFileProcessingIntegration:
    """Integration tests for the complete file processing pipeline."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create a realistic test directory structure with various anime files
        self.test_structure = {
            "Attack on Titan": [
                "Attack on Titan S01E01 [1080p] [GroupA].mkv",
                "Attack on Titan S01E02 [1080p] [GroupA].mkv",
                "Attack on Titan S01E03 [1080p] [GroupA].mkv",
                "Attack on Titan S02E01 [1080p] [GroupB].mkv",
                "Attack on Titan S02E02 [1080p] [GroupB].mkv",
            ],
            "One Piece": [
                "One Piece S01E001 [720p] [GroupC].mp4",
                "One Piece S01E002 [720p] [GroupC].mp4",
                "One Piece S01E003 [720p] [GroupC].mp4",
            ],
            "Naruto": [
                "Naruto S01E01 [1080p] [GroupD].avi",
                "Naruto S01E02 [1080p] [GroupD].avi",
            ],
            "Movies": [
                "Your Name [1080p] [GroupE].mkv",
                "Spirited Away [1080p] [GroupF].mp4",
            ],
            "Different Quality": [
                "Attack on Titan S01E01 [720p] [GroupA].mkv",  # Different quality
                "One Piece S01E001 [1080p] [GroupC].mp4",  # Different quality
            ],
        }

        # Create the directory structure
        for series, files in self.test_structure.items():
            series_dir = self.temp_dir / series
            series_dir.mkdir(exist_ok=True)

            for filename in files:
                file_path = series_dir / filename
                file_path.write_text(f"Test content for {filename}")

    def teardown_method(self) -> None:
        """Clean up test fixtures after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_complete_processing_pipeline(self) -> None:
        """Test the complete file processing pipeline from scan to group."""
        # Step 1: Scan directory
        scanner = FileScanner(max_workers=4)
        scan_result = scanner.scan_directory(self.temp_dir, recursive=True)

        assert scan_result.supported_files > 0
        assert len(scan_result.files) > 0
        assert len(scan_result.errors) == 0

        # Step 2: Group files
        grouper = FileGrouper(similarity_threshold=0.75, max_workers=4)
        grouping_result = grouper.group_files(scan_result.files)

        assert grouping_result.total_files == scan_result.supported_files
        assert len(grouping_result.groups) > 0
        assert grouping_result.grouped_files > 0

        # Step 3: Verify grouping quality
        self._verify_grouping_quality(grouping_result)

    def test_processing_with_progress_callbacks(self) -> None:
        """Test processing with progress callbacks."""
        scan_progress = []
        group_progress = []

        def scan_callback(progress, message):
            scan_progress.append((progress, message))

        def group_callback(progress, message):
            group_progress.append((progress, message))

        # Scan with callback
        scanner = FileScanner(max_workers=2, progress_callback=scan_callback)
        scan_result = scanner.scan_directory(self.temp_dir, recursive=True)

        # Group with callback
        grouper = FileGrouper(max_workers=2, progress_callback=group_callback)
        grouping_result = grouper.group_files(scan_result.files)

        # Verify callbacks were called
        assert len(scan_progress) > 0
        assert len(group_progress) > 0

        # Verify results
        assert scan_result.supported_files > 0
        assert len(grouping_result.groups) > 0

    def test_processing_different_similarity_thresholds(self) -> None:
        """Test processing with different similarity thresholds."""
        # Scan files first
        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(self.temp_dir, recursive=True)

        # Test with high similarity threshold (strict grouping)
        grouper_strict = FileGrouper(similarity_threshold=0.9, max_workers=2)
        strict_result = grouper_strict.group_files(scan_result.files)

        # Test with low similarity threshold (loose grouping)
        grouper_loose = FileGrouper(similarity_threshold=0.5, max_workers=2)
        loose_result = grouper_loose.group_files(scan_result.files)

        # Strict grouping should create more groups
        assert len(strict_result.groups) >= len(loose_result.groups)

        # Both should group some files
        assert strict_result.grouped_files > 0
        assert loose_result.grouped_files > 0

    def test_processing_with_mixed_file_types(self) -> None:
        """Test processing with mixed file types and qualities."""
        # Add some additional files with different characteristics
        mixed_files = [
            "Attack on Titan S01E01 [480p] [OldGroup].avi",
            "Attack on Titan S01E01 [2160p] [NewGroup].mkv",
            "One Piece Movie [1080p] [GroupG].mp4",
            "Special Episode [720p] [GroupH].mkv",
        ]

        for filename in mixed_files:
            file_path = self.temp_dir / filename
            file_path.write_text(f"Test content for {filename}")

        # Process the mixed files
        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(self.temp_dir, recursive=True)

        grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)
        grouping_result = grouper.group_files(scan_result.files)

        # Should handle mixed files gracefully
        assert scan_result.supported_files > 0
        assert len(grouping_result.groups) > 0

        # Verify that similar files are grouped together
        self._verify_grouping_quality(grouping_result)

    def test_processing_performance(self) -> None:
        """Test processing performance with realistic data."""
        # Create more files for performance testing
        self._create_performance_test_files(100)

        scanner = FileScanner(max_workers=4)
        grouper = FileGrouper(similarity_threshold=0.75, max_workers=4)

        # Measure scan performance
        scan_start = datetime.now()
        scan_result = scanner.scan_directory(self.temp_dir, recursive=True)
        scan_duration = (datetime.now() - scan_start).total_seconds()

        # Measure grouping performance
        group_start = datetime.now()
        grouping_result = grouper.group_files(scan_result.files)
        group_duration = (datetime.now() - group_start).total_seconds()

        # Performance assertions
        assert scan_duration < 10.0  # Should scan within 10 seconds
        assert group_duration < 30.0  # Should group within 30 seconds
        assert scan_result.files_per_second > 5  # Should process at least 5 files/sec
        assert len(grouping_result.groups) > 0

    def test_optimized_processor(self) -> None:
        """Test the optimized file processor."""
        processor = OptimizedFileProcessor(similarity_threshold=0.75, max_workers=2, batch_size=10)

        scan_result, grouping_result = processor.process_directory(self.temp_dir)

        assert scan_result.supported_files > 0
        assert len(grouping_result.groups) > 0
        assert grouping_result.grouped_files > 0

    def test_processing_with_errors(self) -> None:
        """Test processing with various error conditions."""
        # Create a file that will cause an error (very long name)
        long_name = "A" * 300 + ".mkv"
        long_file = self.temp_dir / long_name
        long_file.write_text("test")

        # Create a file with invalid characters
        invalid_file = self.temp_dir / "invalid<>file.mkv"
        invalid_file.write_text("test")

        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(self.temp_dir, recursive=True)

        # Should still process other files
        assert scan_result.supported_files > 0

        grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)
        grouping_result = grouper.group_files(scan_result.files)

        # Should still group files
        assert len(grouping_result.groups) > 0

    def _verify_grouping_quality(self, grouping_result: GroupingResult):
        """Verify the quality of file grouping."""
        # Check that files are properly grouped
        total_grouped_files = sum(len(group.files) for group in grouping_result.groups)
        total_files = total_grouped_files + len(grouping_result.ungrouped_files)

        assert total_files == grouping_result.total_files

        # Check that groups have reasonable similarity scores
        for group in grouping_result.groups:
            assert group.similarity_score >= 0.0
            assert group.similarity_score <= 1.0
            assert len(group.files) > 1  # Groups should have multiple files
            assert group.best_file is not None  # Should have a best file

        # Check that similar series are grouped together
        series_groups = {}
        for group in grouping_result.groups:
            if group.series_title:
                if group.series_title not in series_groups:
                    series_groups[group.series_title] = []
                series_groups[group.series_title].append(group)

        # Each series should ideally have one group (or a few related groups)
        for series, groups in series_groups.items():
            assert len(groups) <= 3  # Should not have too many groups per series

    def _create_performance_test_files(self, count: int):
        """Create additional test files for performance testing."""
        for i in range(count):
            series_num = (i % 5) + 1
            episode_num = (i % 20) + 1
            quality = ["720p", "1080p", "480p"][i % 3]

            filename = (
                f"Test Series {series_num} S01E{episode_num:02d} [{quality}] [Group{i%3}].mkv"
            )
            file_path = self.temp_dir / filename
            file_path.write_text(f"Test content for {filename}")


class TestFileProcessingEdgeCases:
    """Test edge cases and error conditions for file processing."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self) -> None:
        """Clean up test fixtures after each test method."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_empty_directory(self) -> None:
        """Test processing an empty directory."""
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()

        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(empty_dir, recursive=True)

        assert scan_result.total_files_found == 0
        assert scan_result.supported_files == 0
        assert len(scan_result.files) == 0

        grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)
        grouping_result = grouper.group_files(scan_result.files)

        assert grouping_result.total_files == 0
        assert len(grouping_result.groups) == 0

    def test_directory_with_only_non_video_files(self) -> None:
        """Test processing a directory with only non-video files."""
        # Create only non-video files
        non_video_files = ["document.txt", "image.jpg", "data.json"]
        for filename in non_video_files:
            file_path = self.temp_dir / filename
            file_path.write_text("test content")

        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(self.temp_dir, recursive=True)

        assert scan_result.total_files_found == len(non_video_files)
        assert scan_result.supported_files == 0
        assert len(scan_result.files) == 0

        grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)
        grouping_result = grouper.group_files(scan_result.files)

        assert grouping_result.total_files == 0
        assert len(grouping_result.groups) == 0

    def test_processing_with_symlinks(self) -> None:
        """Test processing with symbolic links."""
        # Create a regular file
        original_file = self.temp_dir / "original.mkv"
        original_file.write_text("test content")

        # Create a symlink (skip on Windows if not supported)
        try:
            symlink = self.temp_dir / "symlink.mkv"
            symlink.symlink_to(original_file)

            scanner = FileScanner(max_workers=2)
            scan_result = scanner.scan_directory(
                self.temp_dir, recursive=True, follow_symlinks=True
            )

            # Should find both the original and symlink
            assert scan_result.supported_files >= 1

            grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)
            grouping_result = grouper.group_files(scan_result.files)

            assert len(grouping_result.groups) > 0

        except (OSError, NotImplementedError):
            # Symlinks not supported on this platform
            pytest.skip("Symbolic links not supported on this platform")

    def test_processing_with_permission_errors(self) -> None:
        """Test processing with permission errors."""
        # Create a file
        test_file = self.temp_dir / "test.mkv"
        test_file.write_text("test content")

        # Create a subdirectory that we can't access (simulate permission error)
        restricted_dir = self.temp_dir / "restricted"
        restricted_dir.mkdir()

        # On Unix systems, we can change permissions
        if os.name != "nt":  # Not Windows
            try:
                os.chmod(restricted_dir, 0o000)  # No permissions

                scanner = FileScanner(max_workers=2)
                scan_result = scanner.scan_directory(self.temp_dir, recursive=True)

                # Should still process accessible files
                assert scan_result.supported_files >= 1

            finally:
                # Restore permissions for cleanup
                os.chmod(restricted_dir, 0o755)

    def test_processing_with_very_large_files(self) -> None:
        """Test processing with very large files."""
        # Create a large file (simulate with a smaller file for testing)
        large_file = self.temp_dir / "large_file.mkv"
        large_file.write_text("x" * 10000)  # 10KB file

        scanner = FileScanner(max_workers=2)
        scan_result = scanner.scan_directory(self.temp_dir, recursive=True)

        assert scan_result.supported_files == 1
        assert len(scan_result.files) == 1
        assert scan_result.files[0].file_size > 0

        grouper = FileGrouper(similarity_threshold=0.75, max_workers=2)
        grouping_result = grouper.group_files(scan_result.files)

        # Single file should be ungrouped
        assert len(grouping_result.groups) == 0
        assert len(grouping_result.ungrouped_files) == 1
