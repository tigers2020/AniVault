"""Tests for file grouper module."""

import pytest
from pathlib import Path

from anivault.core.file_grouper import FileGrouper, group_similar_files
from anivault.core.models import ScannedFile, ParsingResult


class TestFileGrouper:
    """Test cases for FileGrouper class."""

    def test_group_files_empty_list(self):
        """Test grouping with empty file list."""
        grouper = FileGrouper()
        result = grouper.group_files([])
        assert result == {}

    def test_group_files_single_file(self):
        """Test grouping with single file."""
        grouper = FileGrouper()
        file = ScannedFile(
            file_path=Path("test.mkv"),
            metadata=ParsingResult(title="Test Anime", season=1, episode=1)
        )
        result = grouper.group_files([file])
        assert len(result) == 1
        assert "test" in result  # Based on filename, not metadata title

    def test_group_files_similar_names(self):
        """Test grouping files with similar names."""
        grouper = FileGrouper(similarity_threshold=0.5)
        files = [
            ScannedFile(
                file_path=Path("Attack on Titan S01E01.mkv"),
                metadata=ParsingResult(title="Attack on Titan", season=1, episode=1)
            ),
            ScannedFile(
                file_path=Path("Attack on Titan S01E02.mkv"),
                metadata=ParsingResult(title="Attack on Titan", season=1, episode=2)
            ),
            ScannedFile(
                file_path=Path("One Piece S01E01.mkv"),
                metadata=ParsingResult(title="One Piece", season=1, episode=1)
            ),
        ]
        result = grouper.group_files(files)
        assert len(result) == 2  # Should group Attack on Titan files together

    def test_extract_base_title(self):
        """Test base title extraction."""
        grouper = FileGrouper()
        
        # Test with resolution patterns
        title = grouper._extract_base_title("[SubsPlease] Attack on Titan - 01 (1080p).mkv")
        assert "Attack on Titan" in title
        
        # Test with episode patterns
        title = grouper._extract_base_title("Attack on Titan S01E01.mkv")
        assert "Attack on Titan" in title

    def test_calculate_similarity(self):
        """Test similarity calculation."""
        grouper = FileGrouper()
        
        # High similarity
        similarity = grouper._calculate_similarity("Attack on Titan", "Attack on Titan")
        assert similarity == 1.0
        
        # Medium similarity
        similarity = grouper._calculate_similarity("Attack on Titan", "Attack Titan")
        assert similarity > 0.5
        
        # Low similarity
        similarity = grouper._calculate_similarity("Attack on Titan", "One Piece")
        assert similarity < 0.5

    def test_convenience_function(self):
        """Test convenience function."""
        files = [
            ScannedFile(
                file_path=Path("test1.mkv"),
                metadata=ParsingResult(title="Test", season=1, episode=1)
            )
        ]
        result = group_similar_files(files)
        assert len(result) == 1
