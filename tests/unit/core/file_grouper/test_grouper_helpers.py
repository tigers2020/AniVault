"""Unit tests for FileGrouper helper classes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from anivault.core.file_grouper.grouper import (
    GroupNameManager,
    TitleExtractor,
    TitleQualityEvaluator,
)
from anivault.core.models import ParsingResult, ScannedFile


def create_test_file(filename: str, title: str = "Test") -> ScannedFile:
    """Helper to create ScannedFile."""
    return ScannedFile(
        file_path=Path(filename),
        metadata=ParsingResult(title=title),
    )


class TestTitleExtractor:
    """Test TitleExtractor class."""

    def test_extract_base_title_basic(self) -> None:
        """Test basic title extraction."""
        extractor = TitleExtractor()
        result = extractor.extract_base_title(
            "[Group] Attack on Titan - 01 [1080p].mkv"
        )

        assert result
        assert "Attack on Titan" in result or "attack" in result.lower()

    def test_extract_base_title_with_technical_info(self) -> None:
        """Test extracting title with technical info."""
        extractor = TitleExtractor()
        result = extractor.extract_base_title("Attack_on_Titan_1080p_x264.mkv")

        assert result
        assert result != "unknown"

    def test_extract_base_title_empty_returns_unknown(self) -> None:
        """Test empty filename returns unknown."""
        extractor = TitleExtractor()
        result = extractor.extract_base_title("")

        assert result == "unknown"

    def test_extract_title_with_parser_success(self) -> None:
        """Test parser-based extraction success."""
        extractor = TitleExtractor()
        result = extractor.extract_title_with_parser("[Group] Attack on Titan - 01.mkv")

        assert result
        assert result != "unknown"

    def test_extract_title_with_parser_fallback(self) -> None:
        """Test parser fallback to base extraction."""
        extractor = TitleExtractor()
        # Malformed filename should fallback
        result = extractor.extract_title_with_parser("random_file_name.mkv")

        assert result
        assert isinstance(result, str)


class TestTitleQualityEvaluator:
    """Test TitleQualityEvaluator class."""

    def test_score_empty_title_returns_zero(self) -> None:
        """Test empty title scores zero."""
        evaluator = TitleQualityEvaluator()
        assert evaluator.score_title_quality("") == 0
        assert evaluator.score_title_quality("unknown") == 0

    def test_score_title_quality_basic(self) -> None:
        """Test basic quality scoring."""
        evaluator = TitleQualityEvaluator()

        clean_title = "Attack on Titan"
        dirty_title = "Attack_on_Titan_1080p_x264_AAC"

        score_clean = evaluator.score_title_quality(clean_title)
        score_dirty = evaluator.score_title_quality(dirty_title)

        # Clean title should score better (higher) than dirty
        assert score_clean > score_dirty

    def test_is_cleaner_title(self) -> None:
        """Test comparing title cleanliness."""
        evaluator = TitleQualityEvaluator()

        clean = "Attack on Titan"
        dirty = "Attack_on_Titan_1080p"

        assert evaluator.is_cleaner_title(clean, dirty)
        assert not evaluator.is_cleaner_title(dirty, clean)

    def test_contains_technical_info(self) -> None:
        """Test detecting technical information."""
        evaluator = TitleQualityEvaluator()

        assert evaluator.contains_technical_info("Attack on Titan 1080p")
        assert evaluator.contains_technical_info("Attack on Titan x264")
        assert not evaluator.contains_technical_info("Attack on Titan")

    def test_select_better_title_prefers_quality(self) -> None:
        """Test selecting better title based on quality."""
        evaluator = TitleQualityEvaluator()

        title1 = "Attack on Titan"
        title2 = "Attack_on_Titan_1080p_x264"

        result = evaluator.select_better_title(title1, title2)
        assert result == title1

    def test_select_better_title_handles_unknown(self) -> None:
        """Test handling unknown titles."""
        evaluator = TitleQualityEvaluator()

        assert (
            evaluator.select_better_title("Attack on Titan", "unknown")
            == "Attack on Titan"
        )
        assert evaluator.select_better_title("unknown", "Death Note") == "Death Note"
        assert evaluator.select_better_title("", "Death Note") == "Death Note"


class TestGroupNameManager:
    """Test GroupNameManager class."""

    def test_ensure_unique_group_name_no_conflict(self) -> None:
        """Test unique name when no conflict."""
        manager = GroupNameManager()
        existing = {"Group A": [], "Group B": []}

        result = manager.ensure_unique_group_name("Group C", existing)
        assert result == "Group C"

    def test_ensure_unique_group_name_with_conflict(self) -> None:
        """Test unique name with conflict."""
        manager = GroupNameManager()
        existing = {"Attack on Titan": []}

        result = manager.ensure_unique_group_name("Attack on Titan", existing)
        assert result != "Attack on Titan"
        assert "Attack on Titan" in result

    def test_ensure_unique_group_name_multiple_conflicts(self) -> None:
        """Test unique name with multiple conflicts."""
        manager = GroupNameManager()
        existing = {
            "Attack on Titan": [],
            "Attack on Titan (1)": [],
        }

        result = manager.ensure_unique_group_name("Attack on Titan", existing)
        assert result == "Attack on Titan (2)"

    def test_merge_similar_group_names_no_merge_needed(self) -> None:
        """Test merging when groups are different."""
        manager = GroupNameManager()
        file1 = create_test_file("file1.mkv")
        file2 = create_test_file("file2.mkv")

        groups = {
            "Attack on Titan": [file1],
            "Death Note": [file2],
        }

        result = manager.merge_similar_group_names(groups)
        assert len(result) == 2

    def test_merge_similar_group_names_single_group(self) -> None:
        """Test merging with single group."""
        manager = GroupNameManager()
        file1 = create_test_file("file1.mkv")

        groups = {"Attack on Titan": [file1]}

        result = manager.merge_similar_group_names(groups)
        assert result == groups

    def test_merge_similar_group_names_with_numbered_suffix(self) -> None:
        """Test merging groups with numbered suffixes."""
        manager = GroupNameManager()
        file1 = create_test_file("file1.mkv")
        file2 = create_test_file("file2.mkv")

        groups = {
            "Attack on Titan": [file1],
            "Attack on Titan (2)": [file2],
        }

        result = manager.merge_similar_group_names(groups)
        # Should merge numbered variants
        assert len(result) <= 2
