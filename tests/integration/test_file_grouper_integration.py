"""Integration tests for FileGrouper classes.

This module contains integration tests that verify the FileGrouper classes
work correctly together and with the broader AniVault system.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.core.file_grouper import FileGrouper
from anivault.core.models import ScannedFile
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.shared.constants import BusinessRules


class TestFileGrouperIntegration:
    """Integration tests for FileGrouper with real file system."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.grouper = FileGrouper()
        self.parser = AnitopyParser()

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_scanned_file(self, filename: str, index: int) -> ScannedFile:
        """Helper to create ScannedFile with proper metadata."""
        file_path = Path(self.temp_dir) / filename
        metadata = self.parser.parse(filename)

        return ScannedFile(
            file_path=file_path,
            metadata=metadata,
            file_size=1000000000 + index * 1000000,
            last_modified=1234567890.0 + index,
        )

    def test_real_file_scanning_integration(self) -> None:
        """Test integration with real file scanning."""
        # Create test files
        test_files = [
            "Attack on Titan S01E01.mkv",
            "Attack on Titan S01E02.mkv",
            "Demon Slayer S01E01.mkv",
            "Demon Slayer S01E02.mkv",
            "One Piece Episode 1000.mkv",
            "Naruto Shippuden Episode 500.mkv",
        ]

        scanned_files = []
        for i, filename in enumerate(test_files):
            file_path = Path(self.temp_dir) / filename
            file_path.write_bytes(b"fake video content")
            scanned_files.append(self._create_scanned_file(filename, i))

        # Group files
        result = self.grouper.group_files(scanned_files)

        # Verify results
        assert len(result) >= 4  # Should have at least 4 groups
        total_files = sum(len(group_files) for group_files in result.values())
        assert total_files == len(test_files)

        # Check that files are properly grouped
        for group_name, group_files in result.items():
            assert len(group_files) >= 1
            for file in group_files:
                assert file.file_path.exists()

    def test_subtitle_file_integration(self) -> None:
        """Test integration with subtitle files."""
        # Create test files including subtitles
        test_files = [
            "Attack on Titan S01E01.mkv",
            "Attack on Titan S01E01.srt",
            "Attack on Titan S01E01.ass",
            "Attack on Titan S01E02.mkv",
            "Attack on Titan S01E02.srt",
        ]

        scanned_files = []
        for i, filename in enumerate(test_files):
            file_path = Path(self.temp_dir) / filename
            if filename.endswith(".srt"):
                file_path.write_text("1\n00:00:00,000 --> 00:00:05,000\nSubtitle text")
            elif filename.endswith(".ass"):
                file_path.write_text("[Script Info]\nTitle: Test\n\n[V4+ Styles]")
            else:
                file_path.write_bytes(b"fake video content")

            scanned_files.append(self._create_scanned_file(filename, i))

        # Group files
        result = self.grouper.group_files(scanned_files)

        # Verify results
        assert len(result) >= 1
        total_files = sum(len(group_files) for group_files in result.values())
        assert total_files == len(test_files)

        # Check that video and subtitle files are grouped together
        for group_name, group_files in result.items():
            if "Attack on Titan" in group_name:
                # Should have both video and subtitle files
                video_files = [
                    f
                    for f in group_files
                    if f.file_path.suffix in [".mkv", ".mp4", ".avi"]
                ]
                subtitle_files = [
                    f for f in group_files if f.file_path.suffix in [".srt", ".ass"]
                ]
                assert len(video_files) >= 1
                assert len(subtitle_files) >= 1

    def test_japanese_filename_integration(self) -> None:
        """Test integration with Japanese filenames."""
        # Create test files with Japanese names
        test_files = [
            "進撃の巨人 S01E01.mkv",
            "進撃の巨人 S01E02.mkv",
            "鬼滅の刃 S01E01.mkv",
            "鬼滅の刃 S01E02.mkv",
        ]

        scanned_files = []
        for i, filename in enumerate(test_files):
            file_path = Path(self.temp_dir) / filename
            file_path.write_bytes(b"fake video content")

            scanned_files.append(self._create_scanned_file(filename, i))

        # Group files
        result = self.grouper.group_files(scanned_files)

        # Verify results
        assert len(result) >= 2  # Should have at least 2 groups
        total_files = sum(len(group_files) for group_files in result.values())
        assert total_files == len(test_files)

        # Check that Japanese characters are preserved
        for group_name, group_files in result.items():
            assert len(group_files) >= 1
            # Group names should contain Japanese characters
            has_japanese = any(ord(char) >= 0x3040 for char in group_name)
            if has_japanese:
                assert "進撃" in group_name or "鬼滅" in group_name

    def test_technical_info_removal_integration(self) -> None:
        """Test integration with files containing technical information."""
        # Create test files with various technical info
        test_files = [
            "[SubsPlease] Attack on Titan - S01E01 [1080p] [x264] [AAC].mkv",
            "[Erai-raws] Attack on Titan - S01E02 [1080p] [x265] [AAC].mkv",
            "Attack on Titan - S01E03 [1080p] [WEB-DL] [x264] [AAC].mkv",
            "[HorribleSubs] Demon Slayer - S01E01 [1080p] [x264] [AAC].mkv",
        ]

        scanned_files = []
        for i, filename in enumerate(test_files):
            file_path = Path(self.temp_dir) / filename
            file_path.write_bytes(b"fake video content")

            scanned_files.append(self._create_scanned_file(filename, i))

        # Group files
        result = self.grouper.group_files(scanned_files)

        # Verify results
        assert len(result) >= 2  # Should have at least 2 groups
        total_files = sum(len(group_files) for group_files in result.values())
        assert total_files == len(test_files)

        # Check that technical info is removed from group names
        for group_name, group_files in result.items():
            assert "[" not in group_name  # No brackets in group names
            assert "1080p" not in group_name  # No resolution info
            assert "x264" not in group_name  # No codec info
            assert "AAC" not in group_name  # No audio codec info

    def test_error_handling_integration(self) -> None:
        """Test error handling integration."""
        # Create test files with problematic names
        test_files = [
            "",  # Empty filename
            "   ",  # Whitespace only
            "file_without_extension",  # No extension
            "file.with.multiple.extensions.mkv",  # Multiple extensions
        ]

        scanned_files = []
        for i, filename in enumerate(test_files):
            if filename.strip():  # Skip empty filenames
                file_path = Path(self.temp_dir) / filename
                file_path.write_bytes(b"fake content")
                scanned_files.append(self._create_scanned_file(filename, i))

        # Should not raise exceptions
        result = self.grouper.group_files(scanned_files)

        # Should handle gracefully
        assert isinstance(result, dict)
        total_files = sum(len(group_files) for group_files in result.values())
        assert total_files == len(scanned_files)

    def test_large_dataset_integration(self) -> None:
        """Test integration with large dataset."""
        # Create many test files
        num_files = 100
        test_files = []

        for i in range(num_files):
            anime_index = i % 10
            episode = (i // 10) + 1
            filename = f"Anime_{anime_index:02d}_Episode_{episode:03d}.mkv"
            test_files.append(filename)

        scanned_files = []
        for i, filename in enumerate(test_files):
            file_path = Path(self.temp_dir) / filename
            file_path.write_bytes(b"fake video content")

            scanned_files.append(self._create_scanned_file(filename, i))

        # Group files
        result = self.grouper.group_files(scanned_files)

        # Verify results
        assert len(result) >= 1  # Should have at least 1 group
        total_files = sum(len(group_files) for group_files in result.values())
        assert total_files == num_files

        # Check that files are properly distributed
        for group_name, group_files in result.items():
            assert len(group_files) >= 1
            # Files should be grouped correctly

    def test_parser_integration(self) -> None:
        """Test integration with AnitopyParser."""
        # Create test files that should benefit from parser
        test_files = [
            "[SubsPlease] Attack on Titan - S01E01 [1080p] [x264] [AAC].mkv",
            "[Erai-raws] Attack on Titan - S01E02 [1080p] [x265] [AAC].mkv",
        ]

        scanned_files = []
        for i, filename in enumerate(test_files):
            file_path = Path(self.temp_dir) / filename
            file_path.write_bytes(b"fake video content")

            scanned_files.append(self._create_scanned_file(filename, i))

        # Mock the parser to return consistent results
        with patch("anivault.core.file_grouper.AnitopyParser") as mock_parser_class:
            mock_parser = Mock()
            mock_parser.parse.return_value = {"anime_title": "Attack on Titan"}
            mock_parser_class.return_value = mock_parser

            # Group files
            result = self.grouper.group_files(scanned_files)

            # Verify results
            assert len(result) >= 1
            total_files = sum(len(group_files) for group_files in result.values())
            assert total_files == len(test_files)

            # Parser should have been called
            assert mock_parser.parse.call_count >= 1

    def test_business_rules_integration(self) -> None:
        """Test integration with business rules."""
        # Test with different similarity thresholds
        thresholds = [0.5, 0.7, 0.9]

        test_files = [
            "Attack on Titan S01E01.mkv",
            "Attack on Titan S01E02.mkv",
            "Demon Slayer S01E01.mkv",
        ]

        scanned_files = []
        for i, filename in enumerate(test_files):
            file_path = Path(self.temp_dir) / filename
            file_path.write_bytes(b"fake video content")

            scanned_files.append(self._create_scanned_file(filename, i))

        results = []
        for threshold in thresholds:
            grouper = FileGrouper(similarity_threshold=threshold)
            result = grouper.group_files(scanned_files)
            results.append(result)

        # All results should be valid
        for result in results:
            assert isinstance(result, dict)
            total_files = sum(len(group_files) for group_files in result.values())
            assert total_files == len(test_files)

        # Results might differ based on threshold
        print(f"Results with different thresholds:")
        for i, (threshold, result) in enumerate(zip(thresholds, results)):
            print(f"  Threshold {threshold}: {len(result)} groups")

    def test_file_path_encoding_integration(self) -> None:
        """Test integration with different file path encodings."""
        # Create test files with various encodings
        test_files = [
            "Attack on Titan S01E01.mkv",  # ASCII
            "進撃の巨人 S01E01.mkv",  # Japanese
            "Attack on Titan - Saison 1 Episode 1.mkv",  # French
            "Attack on Titan - Staffel 1 Episode 1.mkv",  # German
        ]

        scanned_files = []
        for i, filename in enumerate(test_files):
            file_path = Path(self.temp_dir) / filename
            file_path.write_bytes(b"fake video content")

            scanned_files.append(self._create_scanned_file(filename, i))

        # Group files
        result = self.grouper.group_files(scanned_files)

        # Verify results
        assert len(result) >= 1
        total_files = sum(len(group_files) for group_files in result.values())
        assert total_files == len(test_files)

        # Check that different encodings are handled properly
        for group_name, group_files in result.items():
            assert len(group_files) >= 1
            # Group names should be valid strings
            assert isinstance(group_name, str)
            assert len(group_name) > 0
