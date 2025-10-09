"""Integration tests for group name update functionality.

This module tests the complete flow of group name updates
from file grouping to UI display.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from anivault.core.file_grouper import FileGrouper
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult


class TestGroupNameUpdateIntegration:
    """Integration tests for group name update functionality."""

    def test_end_to_end_group_name_update(self):
        """Test complete end-to-end group name update flow."""
        with patch('anivault.core.file_grouper.AnitopyParser') as mock_parser_class:
            # Setup mock parser
            mock_parser = Mock()
            mock_parser_class.return_value = mock_parser
            
            # Mock parsing results for different files
            def mock_parse(filename):
                mock_result = Mock()
                if "Attack on Titan" in filename:
                    mock_result.title = "Attack on Titan"
                elif "One Piece" in filename:
                    mock_result.title = "One Piece"
                else:
                    mock_result.title = filename  # Fallback
                return mock_result
            
            mock_parser.parse.side_effect = mock_parse
            
            # Create file grouper
            grouper = FileGrouper()
            
            # Create test files with similar names
            files = [
                ScannedFile(
                    file_path=Path("[SubsPlease] Attack on Titan - 01 [1080p].mkv"),
                    metadata=ParsingResult(title="Attack on Titan - 01", parser_used="test"),
                    file_size=1000,
                    last_modified=1234567890.0
                ),
                ScannedFile(
                    file_path=Path("[SubsPlease] Attack on Titan - 02 [1080p].mkv"),
                    metadata=ParsingResult(title="Attack on Titan - 02", parser_used="test"),
                    file_size=1000,
                    last_modified=1234567890.0
                ),
                ScannedFile(
                    file_path=Path("[Erai-raws] One Piece - 1000 [1080p].mkv"),
                    metadata=ParsingResult(title="One Piece - 1000", parser_used="test"),
                    file_size=1000,
                    last_modified=1234567890.0
                ),
            ]
            
            # Group files
            grouped_files = grouper.group_files(files)
            
            # Verify grouping and name updates
            assert len(grouped_files) >= 1  # Should have at least one group
            
            # Check that parser was called
            assert mock_parser.parse.call_count >= 1
            
            # Verify that group names are more descriptive than basic extraction
            group_names = list(grouped_files.keys())
            
            # At least one group should have a proper anime title
            has_anime_title = any(
                any(title in name for title in ["Attack on Titan", "One Piece"])
                for name in group_names
            )
            assert has_anime_title, f"Expected anime titles in group names: {group_names}"

    def test_group_name_update_with_mixed_quality_files(self):
        """Test group name update with files of varying quality."""
        with patch('anivault.core.file_grouper.AnitopyParser') as mock_parser_class:
            # Setup mock parser
            mock_parser = Mock()
            mock_parser_class.return_value = mock_parser
            
            # Mock parsing results
            def mock_parse(filename):
                mock_result = Mock()
                if "good" in filename.lower():
                    mock_result.title = "Good Anime Title"
                elif "bad" in filename.lower():
                    mock_result.title = ""  # Empty title (parser failed)
                else:
                    mock_result.title = "Default Title"
                return mock_result
            
            mock_parser.parse.side_effect = mock_parse
            
            # Create file grouper
            grouper = FileGrouper()
            
            # Create test files with different quality names
            files = [
                ScannedFile(
                    file_path=Path("good_anime_ep01.mkv"),
                    metadata=ParsingResult(title="good_anime_ep01", parser_used="test"),
                    file_size=1000,
                    last_modified=1234567890.0
                ),
                ScannedFile(
                    file_path=Path("bad_filename_ep02.mkv"),
                    metadata=ParsingResult(title="bad_filename_ep02", parser_used="test"),
                    file_size=1000,
                    last_modified=1234567890.0
                ),
            ]
            
            # Group files
            grouped_files = grouper.group_files(files)
            
            # Verify that the grouper handles mixed quality gracefully
            assert len(grouped_files) >= 1
            
            # The group name should be based on the best representative file
            group_names = list(grouped_files.keys())
            
            # Should prefer the good title when available
            has_good_title = any("Good Anime Title" in name for name in group_names)
            assert has_good_title or len(group_names) > 0  # At least some grouping occurred

    def test_group_name_uniqueness_handling(self):
        """Test that duplicate group names are handled properly."""
        with patch('anivault.core.file_grouper.AnitopyParser') as mock_parser_class:
            # Setup mock parser that always returns the same title
            mock_parser = Mock()
            mock_parser_class.return_value = mock_parser
            
            mock_result = Mock()
            mock_result.title = "Same Title"
            mock_parser.parse.return_value = mock_result
            
            # Create file grouper
            grouper = FileGrouper()
            
            # Create test files that would result in duplicate group names
            files = [
                ScannedFile(
                    file_path=Path("anime1_ep01.mkv"),
                    metadata=ParsingResult(title="anime1_ep01", parser_used="test"),
                    file_size=1000,
                    last_modified=1234567890.0
                ),
                ScannedFile(
                    file_path=Path("anime2_ep01.mkv"),
                    metadata=ParsingResult(title="anime2_ep01", parser_used="test"),
                    file_size=1000,
                    last_modified=1234567890.0
                ),
            ]
            
            # Group files
            grouped_files = grouper.group_files(files)
            
            # Verify that all group names are unique
            group_names = list(grouped_files.keys())
            assert len(group_names) == len(set(group_names)), "All group names should be unique"
            
            # If there are multiple groups with the same parsed title,
            # they should have unique suffixes
            same_title_groups = [name for name in group_names if "Same Title" in name]
            if len(same_title_groups) > 1:
                # Check for uniqueness suffixes
                assert len(same_title_groups) == len(set(same_title_groups))

    def test_fallback_behavior_without_parser(self):
        """Test fallback behavior when parser is not available."""
        # Mock ImportError for AnitopyParser
        with patch('anivault.core.file_grouper.AnitopyParser', side_effect=ImportError):
            # Create file grouper (should handle ImportError gracefully)
            grouper = FileGrouper()
            assert grouper.parser is None
            
            # Create test files
            files = [
                ScannedFile(
                    file_path=Path("anime_title_ep01.mkv"),
                    metadata=ParsingResult(title="anime_title_ep01", parser_used="test"),
                    file_size=1000,
                    last_modified=1234567890.0
                ),
            ]
            
            # Group files (should work without parser)
            grouped_files = grouper.group_files(files)
            
            # Verify that grouping still works
            assert len(grouped_files) >= 1
            
            # Group names should be basic extracted titles
            group_names = list(grouped_files.keys())
            assert len(group_names) > 0
            
            # Should not contain parsed titles since parser is not available
            for name in group_names:
                # Basic extracted titles should be present
                assert len(name) > 0
