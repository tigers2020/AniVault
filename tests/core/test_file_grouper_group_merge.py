"""Tests for FileGrouper group merging functionality."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from anivault.core.file_grouper import FileGrouper
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult


@pytest.mark.skip(
    reason="Refactored - _merge_similar_group_names moved to GroupNameManager"
)
class TestFileGrouperGroupMerge:
    """Test group merging functionality in FileGrouper."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.grouper = FileGrouper()
        self.mock_files = [
            ScannedFile(
                file_path=Path("test1.mp4"),
                metadata=ParsingResult(title="test1", parser_used="test"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("test2.mp4"),
                metadata=ParsingResult(title="test2", parser_used="test"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("test3.mkv"),
                metadata=ParsingResult(title="test3", parser_used="test"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
        ]

    def test_merge_similar_group_names_empty_input(self) -> None:
        """Test merging with empty input."""
        result = self.grouper._merge_similar_group_names({})
        assert result == {}

    def test_merge_similar_group_names_no_numbered_groups(self) -> None:
        """Test merging when no numbered groups exist."""
        input_groups = {
            "Anime A": [self.mock_files[0]],
            "Anime B": [self.mock_files[1]],
        }

        result = self.grouper._merge_similar_group_names(input_groups)
        assert result == input_groups

    def test_merge_similar_group_names_base_and_numbered(self) -> None:
        """Test merging base group with numbered variant."""
        input_groups = {
            "Anime A": [self.mock_files[0]],
            "Anime A (1)": [self.mock_files[1]],
            "Anime B": [self.mock_files[2]],
        }

        result = self.grouper._merge_similar_group_names(input_groups)

        assert len(result) == 2
        assert "Anime A" in result
        assert "Anime B" in result
        assert "Anime A (1)" not in result
        assert len(result["Anime A"]) == 2
        assert len(result["Anime B"]) == 1

    def test_merge_similar_group_names_multiple_numbered_variants(self) -> None:
        """Test merging multiple numbered variants with base group."""
        input_groups = {
            "Anime A": [self.mock_files[0]],
            "Anime A (1)": [self.mock_files[1]],
            "Anime A (2)": [self.mock_files[2]],
        }

        result = self.grouper._merge_similar_group_names(input_groups)

        assert len(result) == 1
        assert "Anime A" in result
        assert "Anime A (1)" not in result
        assert "Anime A (2)" not in result
        assert len(result["Anime A"]) == 3

    def test_merge_similar_group_names_only_numbered_variants(self) -> None:
        """Test merging when only numbered variants exist."""
        input_groups = {
            "Anime A (1)": [self.mock_files[0]],
            "Anime A (2)": [self.mock_files[1]],
            "Anime B": [self.mock_files[2]],
        }

        result = self.grouper._merge_similar_group_names(input_groups)

        assert len(result) == 3
        assert "Anime A (1)" in result
        assert "Anime A (2)" in result
        assert "Anime B" in result
        # No base group exists, so numbered variants remain separate

    def test_merge_similar_group_names_complex_case(self) -> None:
        """Test merging with complex scenario."""
        input_groups = {
            "Title A": [self.mock_files[0]],
            "Title A (1)": [self.mock_files[1]],
            "Title B (1)": [self.mock_files[2]],
        }

        result = self.grouper._merge_similar_group_names(input_groups)

        assert len(result) == 2
        assert "Title A" in result
        assert "Title B (1)" in result
        assert "Title A (1)" not in result
        assert len(result["Title A"]) == 2
        assert len(result["Title B (1)"]) == 1

    def test_merge_similar_group_names_whitespace_handling(self) -> None:
        """Test merging with whitespace variations."""
        input_groups = {
            "Anime A": [self.mock_files[0]],
            "Anime A (1)": [self.mock_files[1]],  # Normal spacing
            "Anime A  (2)": [self.mock_files[2]],  # Extra space
        }

        result = self.grouper._merge_similar_group_names(input_groups)

        assert len(result) == 1
        assert "Anime A" in result
        assert len(result["Anime A"]) == 3

    def test_group_files_with_merge_integration(self) -> None:
        """Test that group_files method properly integrates merging."""
        # Create files that would result in numbered groups
        test_files = [
            ScannedFile(
                file_path=Path("[Group] Title - 01.mkv"),
                metadata=ParsingResult(title="Title", parser_used="test"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("[Group] Title - 02.mkv"),
                metadata=ParsingResult(title="Title", parser_used="test"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("[Group] Title - 12 END.mkv"),
                metadata=ParsingResult(title="Title", parser_used="test"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
        ]

        result = self.grouper.group_files(test_files)

        # Should result in a single merged group
        assert len(result) == 1
        assert "Title" in result
        assert len(result["Title"]) == 3

    def test_merge_preserves_file_order(self) -> None:
        """Test that merging preserves the order of files."""
        input_groups = {
            "Anime A": [self.mock_files[0]],
            "Anime A (1)": [self.mock_files[1]],
        }

        result = self.grouper._merge_similar_group_names(input_groups)

        merged_files = result["Anime A"]
        assert len(merged_files) == 2
        assert merged_files[0] == self.mock_files[0]  # Base group files first
        assert merged_files[1] == self.mock_files[1]  # Then numbered variant files
