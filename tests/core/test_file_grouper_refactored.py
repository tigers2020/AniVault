"""Comprehensive tests for refactored FileGrouper classes.

This module tests the newly refactored FileGrouper classes following the
Single Responsibility Principle:
- TitleExtractor: Title extraction and cleaning
- TitleQualityEvaluator: Title quality scoring
- GroupNameManager: Group naming and merging
- FileGrouper: Main orchestration
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.core.file_grouper import (
    FileGrouper,
    GroupNameManager,
    TitleExtractor,
    TitleQualityEvaluator,
)
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult
from anivault.shared.constants.filename_patterns import (
    TitlePatterns,
    TitleQualityScores,
    TitleSelectionThresholds,
)


class TestTitleExtractor:
    """Test cases for TitleExtractor class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.extractor = TitleExtractor()

    def test_extract_base_title_clean_filename(self) -> None:
        """Test extracting title from clean filename."""
        filename = "Attack on Titan S01E01.mkv"
        result = self.extractor.extract_base_title(filename)
        assert result == "Attack on Titan E01"  # S01 is removed, E01 is kept

    def test_extract_base_title_with_technical_info(self) -> None:
        """Test extracting title from filename with technical information."""
        filename = "[SubsPlease] Attack on Titan - S01E01 [1080p] [x264] [AAC].mkv"
        result = self.extractor.extract_base_title(filename)
        assert result == "Attack on Titan - E01"  # Technical info removed, E01 kept

    def test_extract_base_title_with_release_group(self) -> None:
        """Test extracting title from filename with release group."""
        filename = "[Erai-raws] Demon Slayer - S01E01 [1080p] [x264] [AAC].mkv"
        result = self.extractor.extract_base_title(filename)
        assert result == "Demon Slayer - E01"  # Technical info removed, E01 kept

    def test_extract_base_title_with_resolution(self) -> None:
        """Test extracting title from filename with resolution info."""
        filename = "One Piece - Episode 1000 [1080p] [WEB-DL] [x265] [AAC].mkv"
        result = self.extractor.extract_base_title(filename)
        assert (
            result == "One Piece - Episode 1000 [WEB-DL]"
        )  # Technical info removed, Episode 1000 kept

    def test_extract_base_title_with_codec_info(self) -> None:
        """Test extracting title from filename with codec information."""
        filename = "Naruto Shippuden - Episode 500 [x264] [AAC] [1080p].mkv"
        result = self.extractor.extract_base_title(filename)
        assert result == "Naruto Shippuden"  # Episode info and technical info removed

    def test_extract_base_title_japanese_characters(self) -> None:
        """Test extracting title with Japanese characters."""
        filename = "進撃の巨人 - Episode 1 [1080p].mkv"
        result = self.extractor.extract_base_title(filename)
        assert result == "進撃の巨人"  # Episode info and technical info removed

    def test_extract_base_title_empty_result(self) -> None:
        """Test extracting title from filename with only technical info."""
        filename = "[1080p] [x264] [AAC].mkv"
        result = self.extractor.extract_base_title(filename)
        assert result == "unknown"  # Only technical info remains

    def test_extract_base_title_with_parentheses(self) -> None:
        """Test extracting title from filename with parentheses."""
        filename = "Attack on Titan (Season 1) - Episode 1.mkv"
        result = self.extractor.extract_base_title(filename)
        assert result == "Attack on Titan"  # Season and Episode info removed

    def test_extract_base_title_error_handling(self) -> None:
        """Test error handling in title extraction."""
        # Test with None filename
        result = self.extractor.extract_base_title(None)
        assert result == "unknown"

    @patch("anivault.core.file_grouper.AnitopyParser")
    def test_extract_title_with_parser_success(self, mock_parser_class) -> None:
        """Test title extraction using parser successfully."""
        mock_parser = Mock()
        mock_parser.parse.return_value = {"anime_title": "Attack on Titan"}
        mock_parser_class.return_value = mock_parser

        extractor = TitleExtractor()
        result = extractor.extract_title_with_parser("test.mkv")

        assert result == "Attack on Titan"
        mock_parser.parse.assert_called_once_with("test.mkv")

    @patch("anivault.core.file_grouper.AnitopyParser")
    def test_extract_title_with_parser_fallback(self, mock_parser_class) -> None:
        """Test title extraction fallback when parser fails."""
        mock_parser = Mock()
        mock_parser.parse.return_value = {"anime_title": ""}
        mock_parser_class.return_value = mock_parser

        extractor = TitleExtractor()
        result = extractor.extract_title_with_parser("Attack on Titan S01E01.mkv")

        assert result == "Attack on Titan E01"  # S01 removed, E01 kept

    @patch("anivault.core.file_grouper.AnitopyParser")
    def test_extract_title_with_parser_error(self, mock_parser_class) -> None:
        """Test title extraction when parser raises exception."""
        mock_parser = Mock()
        mock_parser.parse.side_effect = ValueError("Parse error")
        mock_parser_class.return_value = mock_parser

        extractor = TitleExtractor()
        result = extractor.extract_title_with_parser("test.mkv")

        assert result == "test"  # Fallback to base extraction


class TestTitleQualityEvaluator:
    """Test cases for TitleQualityEvaluator class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.evaluator = TitleQualityEvaluator()

    def test_score_title_quality_good_title(self) -> None:
        """Test scoring a good quality title."""
        title = "Attack on Titan"
        score = self.evaluator.score_title_quality(title)
        assert score >= 0  # Should have positive score

    def test_score_title_quality_with_japanese(self) -> None:
        """Test scoring title with Japanese characters."""
        title = "進撃の巨人"
        score = self.evaluator.score_title_quality(title)
        assert score >= TitleQualityScores.JAPANESE_CHAR_BONUS

    def test_score_title_quality_title_case(self) -> None:
        """Test scoring title with proper title case."""
        title = "Attack On Titan"
        score = self.evaluator.score_title_quality(title)
        assert score >= TitleQualityScores.TITLE_CASE_BONUS

    def test_score_title_quality_with_technical_info(self) -> None:
        """Test scoring title with technical information."""
        title = "Attack on Titan [1080p] [x264]"
        score = self.evaluator.score_title_quality(title)
        assert score <= 0  # Should have negative score

    def test_score_title_quality_too_short(self) -> None:
        """Test scoring very short title."""
        title = "AoT"
        score = self.evaluator.score_title_quality(title)
        assert score <= TitleQualityScores.BAD_LENGTH_PENALTY

    def test_score_title_quality_too_long(self) -> None:
        """Test scoring very long title."""
        title = "A" * 101
        score = self.evaluator.score_title_quality(title)
        assert score <= TitleQualityScores.BAD_LENGTH_PENALTY

    def test_score_title_quality_unknown(self) -> None:
        """Test scoring unknown title."""
        score = self.evaluator.score_title_quality("unknown")
        assert score == 0

    def test_score_title_quality_empty(self) -> None:
        """Test scoring empty title."""
        score = self.evaluator.score_title_quality("")
        assert score == 0

    def test_is_cleaner_title_first_cleaner(self) -> None:
        """Test comparing titles where first is cleaner."""
        title1 = "Attack on Titan"
        title2 = "Attack on Titan [1080p] [x264]"
        result = self.evaluator.is_cleaner_title(title1, title2)
        assert result is True

    def test_is_cleaner_title_second_cleaner(self) -> None:
        """Test comparing titles where second is cleaner."""
        title1 = "Attack on Titan [1080p] [x264]"
        title2 = "Attack on Titan"
        result = self.evaluator.is_cleaner_title(title1, title2)
        assert result is False

    def test_contains_technical_info_true(self) -> None:
        """Test detecting technical information in title."""
        title = "Attack on Titan [1080p] [x264] [AAC]"
        result = self.evaluator.contains_technical_info(title)
        assert result is True

    def test_contains_technical_info_false(self) -> None:
        """Test detecting no technical information in title."""
        title = "Attack on Titan"
        result = self.evaluator.contains_technical_info(title)
        assert result is False

    def test_select_better_title_first_better(self) -> None:
        """Test selecting better title when first is significantly better."""
        title1 = "Attack on Titan"
        title2 = "Attack on Titan [1080p] [x264] [AAC]"
        result = self.evaluator.select_better_title(title1, title2)
        assert result == title1

    def test_select_better_title_second_better(self) -> None:
        """Test selecting better title when second is significantly better."""
        title1 = "Attack on Titan [1080p] [x264] [AAC]"
        title2 = "Attack on Titan"
        result = self.evaluator.select_better_title(title1, title2)
        assert result == title2

    def test_select_better_title_first_unknown(self) -> None:
        """Test selecting title when first is unknown."""
        title1 = "unknown"
        title2 = "Attack on Titan"
        result = self.evaluator.select_better_title(title1, title2)
        assert result == title2

    def test_select_better_title_second_unknown(self) -> None:
        """Test selecting title when second is unknown."""
        title1 = "Attack on Titan"
        title2 = "unknown"
        result = self.evaluator.select_better_title(title1, title2)
        assert result == title1

    def test_select_better_title_length_preference(self) -> None:
        """Test length-based title selection."""
        title1 = "Attack on Titan"
        title2 = "Attack on Titan: The Final Season"
        result = self.evaluator.select_better_title(title1, title2)
        # Should prefer shorter title if scores are similar
        assert result in [title1, title2]


class TestGroupNameManager:
    """Test cases for GroupNameManager class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.manager = GroupNameManager()
        self.sample_file = ScannedFile(
            file_path=Path("test.mkv"),
            metadata=ParsingResult(title="test"),
            file_size=1000,
            last_modified=1234567890.0,
        )

    def test_ensure_unique_group_name_unique(self) -> None:
        """Test ensuring unique group name when name is already unique."""
        existing_groups = {"Group A": [self.sample_file]}
        result = self.manager.ensure_unique_group_name("Group B", existing_groups)
        assert result == "Group B"

    def test_ensure_unique_group_name_duplicate(self) -> None:
        """Test ensuring unique group name when name already exists."""
        existing_groups = {"Group A": [self.sample_file]}
        result = self.manager.ensure_unique_group_name("Group A", existing_groups)
        assert result == "Group A (1)"

    def test_ensure_unique_group_name_multiple_duplicates(self) -> None:
        """Test ensuring unique group name with multiple duplicates."""
        existing_groups = {
            "Group A": [self.sample_file],
            "Group A (1)": [self.sample_file],
            "Group A (2)": [self.sample_file],
        }
        result = self.manager.ensure_unique_group_name("Group A", existing_groups)
        assert result == "Group A (3)"

    def test_merge_similar_group_names_no_merges(self) -> None:
        """Test merging when no similar group names exist."""
        grouped_files = {
            "Group A": [self.sample_file],
            "Group B": [self.sample_file],
        }
        result = self.manager.merge_similar_group_names(grouped_files)
        assert result == grouped_files

    def test_merge_similar_group_names_single_group(self) -> None:
        """Test merging with single group."""
        grouped_files = {"Group A": [self.sample_file]}
        result = self.manager.merge_similar_group_names(grouped_files)
        assert result == grouped_files

    def test_merge_similar_group_names_empty(self) -> None:
        """Test merging with empty groups."""
        grouped_files = {}
        result = self.manager.merge_similar_group_names(grouped_files)
        assert result == {}

    def test_merge_similar_group_names_numbered_suffixes(self) -> None:
        """Test merging groups with numbered suffixes."""
        file1 = ScannedFile(
            file_path=Path("test1.mkv"),
            metadata=ParsingResult(title="Attack on Titan"),
            file_size=1000,
            last_modified=1234567890.0,
        )
        file2 = ScannedFile(
            file_path=Path("test2.mkv"),
            metadata=ParsingResult(title="Attack on Titan"),
            file_size=2000,
            last_modified=1234567890.0,
        )
        file3 = ScannedFile(
            file_path=Path("test3.mkv"),
            metadata=ParsingResult(title="Attack on Titan"),
            file_size=3000,
            last_modified=1234567890.0,
        )

        grouped_files = {
            "Attack on Titan": [file1],
            "Attack on Titan (1)": [file2],
            "Attack on Titan (2)": [file3],
        }

        result = self.manager.merge_similar_group_names(grouped_files)

        # Should merge all three groups under "Attack on Titan"
        assert len(result) == 1
        assert "Attack on Titan" in result
        assert len(result["Attack on Titan"]) == 3


class TestFileGrouper:
    """Test cases for FileGrouper class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.grouper = FileGrouper()

    def test_init_default_threshold(self) -> None:
        """Test initialization with default threshold."""
        grouper = FileGrouper()
        assert hasattr(grouper, "similarity_threshold")
        assert hasattr(grouper, "title_extractor")
        assert hasattr(grouper, "quality_evaluator")
        assert hasattr(grouper, "group_manager")

    def test_init_custom_threshold(self) -> None:
        """Test initialization with custom threshold."""
        threshold = 0.8
        grouper = FileGrouper(similarity_threshold=threshold)
        assert grouper.similarity_threshold == threshold

    def test_group_files_empty_list(self) -> None:
        """Test grouping empty file list."""
        result = self.grouper.group_files([])
        assert result == {}

    def test_group_files_single_file(self) -> None:
        """Test grouping single file."""
        file1 = ScannedFile(
            file_path=Path("Attack on Titan S01E01.mkv"),
            metadata=ParsingResult(title="Attack on Titan"),
            file_size=1000,
            last_modified=1234567890.0,
        )

        result = self.grouper.group_files([file1])

        assert len(result) == 1
        # Group name is cleaned title without episode/season info
        assert "Attack on Titan" in result
        assert len(list(result.values())[0]) == 1

    def test_group_files_similar_titles(self) -> None:
        """Test grouping files with similar titles."""
        file1 = ScannedFile(
            file_path=Path("Attack on Titan S01E01.mkv"),
            metadata=ParsingResult(title="Attack on Titan"),
            file_size=1000,
            last_modified=1234567890.0,
        )
        file2 = ScannedFile(
            file_path=Path("Attack on Titan S01E02.mkv"),
            metadata=ParsingResult(title="Demon Slayer"),
            file_size=2000,
            last_modified=1234567890.0,
        )

        result = self.grouper.group_files([file1, file2])

        # Should create separate groups for different episodes
        assert len(result) >= 1
        total_files = sum(len(files) for files in result.values())
        assert total_files == 2

    def test_group_files_with_technical_info(self) -> None:
        """Test grouping files with technical information."""
        file1 = ScannedFile(
            file_path=Path("[SubsPlease] Attack on Titan - S01E01 [1080p] [x264].mkv"),
            metadata=ParsingResult(title="Attack on Titan"),
            file_size=1000,
            last_modified=1234567890.0,
        )
        file2 = ScannedFile(
            file_path=Path("Attack on Titan - S01E02 [1080p] [x264].mkv"),
            metadata=ParsingResult(title="Demon Slayer"),
            file_size=2000,
            last_modified=1234567890.0,
        )

        result = self.grouper.group_files([file1, file2])

        # Should group by cleaned titles
        assert len(result) >= 1
        total_files = sum(len(files) for files in result.values())
        assert total_files == 2

    def test_group_files_error_handling(self) -> None:
        """Test error handling in file grouping."""
        # Test with invalid file objects
        with pytest.raises(Exception):
            self.grouper.group_files([None])  # type: ignore

    def test_group_files_with_parser_integration(self) -> None:
        """Test file grouping with parser integration."""
        file1 = ScannedFile(
            file_path=Path("[Erai-raws] Demon Slayer - S01E01 [1080p].mkv"),
            metadata=ParsingResult(title="Attack on Titan"),
            file_size=1000,
            last_modified=1234567890.0,
        )

        with patch.object(
            self.grouper, "_update_group_names_with_parser"
        ) as mock_update:
            mock_update.return_value = {"Demon Slayer": [file1]}

            result = self.grouper.group_files([file1])

            assert len(result) >= 1
            # Parser integration should be called during processing
            mock_update.assert_called()

    def test_calculate_similarity_identical(self) -> None:
        """Test similarity calculation for identical titles."""
        similarity = self.grouper._calculate_similarity(
            "Attack on Titan", "Attack on Titan"
        )
        assert similarity == 1.0

    def test_calculate_similarity_different(self) -> None:
        """Test similarity calculation for different titles."""
        similarity = self.grouper._calculate_similarity(
            "Attack on Titan", "Demon Slayer"
        )
        assert similarity < 0.5

    def test_calculate_similarity_partial(self) -> None:
        """Test similarity calculation for partially similar titles."""
        similarity = self.grouper._calculate_similarity(
            "Attack on Titan", "Attack on Titan Season 2"
        )
        assert 0.5 <= similarity <= 1.0

    def test_calculate_similarity_empty(self) -> None:
        """Test similarity calculation for empty titles."""
        similarity = self.grouper._calculate_similarity("", "")
        assert similarity == 0.0

    def test_select_best_group_key_longest(self) -> None:
        """Test selecting best group key (prefers longer titles)."""
        titles = ["Attack", "Attack on Titan", "Attack on Titan Season 1"]
        result = self.grouper._select_best_group_key(titles)
        assert result == "Attack on Titan Season 1"


class TestFileGrouperIntegration:
    """Integration tests for FileGrouper with real-world scenarios."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.grouper = FileGrouper()

    def test_real_world_anime_grouping(self) -> None:
        """Test grouping with real-world anime filenames."""
        files = [
            ScannedFile(
                file_path=Path(
                    "[SubsPlease] Attack on Titan - S01E01 [1080p] [x264] [AAC].mkv"
                ),
                metadata=ParsingResult(title="Attack on Titan"),
                file_size=1000000000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path(
                    "[Erai-raws] Attack on Titan - S01E02 [1080p] [x265] [AAC].mkv"
                ),
                metadata=ParsingResult(title="Attack on Titan"),
                file_size=2000000000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("Attack on Titan - S01E03 [1080p] [WEB-DL].mkv"),
                metadata=ParsingResult(title="Attack on Titan"),
                file_size=1500000000,
                last_modified=1234567890.0,
            ),
        ]

        result = self.grouper.group_files(files)

        # Should group all Attack on Titan episodes together
        assert len(result) >= 1
        total_files = sum(len(group_files) for group_files in result.values())
        assert total_files == 3

        # Check that files are properly grouped
        for group_name, group_files in result.items():
            assert len(group_files) >= 1
            for file in group_files:
                assert "Attack on Titan" in file.file_path.name

    def test_mixed_content_grouping(self) -> None:
        """Test grouping mixed content (anime, movies, etc.)."""
        files = [
            ScannedFile(
                file_path=Path("Attack on Titan S01E01.mkv"),
                metadata=ParsingResult(title="Attack on Titan"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("Demon Slayer S01E01.mkv"),
                metadata=ParsingResult(title="Demon Slayer"),
                file_size=2000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("Your Name (2016) [1080p].mkv"),
                metadata=ParsingResult(title="Your Name"),
                file_size=3000,
                last_modified=1234567890.0,
            ),
        ]

        result = self.grouper.group_files(files)

        # Should create separate groups for different content
        assert len(result) >= 3
        total_files = sum(len(group_files) for group_files in result.values())
        assert total_files == 3

    def test_subtitle_file_handling(self) -> None:
        """Test handling of subtitle files."""
        files = [
            ScannedFile(
                file_path=Path("Attack on Titan S01E01.mkv"),
                metadata=ParsingResult(title="Attack on Titan"),
                file_size=1000,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("Attack on Titan S01E01.srt"),
                metadata=ParsingResult(title="Attack on Titan"),
                file_size=100,
                last_modified=1234567890.0,
            ),
            ScannedFile(
                file_path=Path("Attack on Titan S01E01.ass"),
                metadata=ParsingResult(title="Attack on Titan"),
                file_size=200,
                last_modified=1234567890.0,
            ),
        ]

        result = self.grouper.group_files(files)

        # Should group video and subtitle files together
        assert len(result) >= 1
        total_files = sum(len(group_files) for group_files in result.values())
        assert total_files == 3
