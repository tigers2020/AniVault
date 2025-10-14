"""Unit tests for TitleSimilarityMatcher."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from anivault.core.file_grouper.matchers.title_matcher import TitleSimilarityMatcher
from anivault.core.file_grouper.models import Group
from anivault.core.models import ParsingResult, ScannedFile

if TYPE_CHECKING:
    from anivault.core.file_grouper.grouper import (
        TitleExtractor,
        TitleQualityEvaluator,
    )


def create_test_file(filename: str, title: str | None = None) -> ScannedFile:
    """Helper to create ScannedFile with metadata."""
    return ScannedFile(
        file_path=Path(filename),
        metadata=ParsingResult(title=title or "Test Anime"),
    )


class TestInitialization:
    """Test TitleSimilarityMatcher initialization."""

    def test_init_with_valid_threshold(self) -> None:
        """Test initialization with valid threshold."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=0.85)

        assert matcher.component_name == "title"
        assert matcher.threshold == 0.85
        assert matcher.title_extractor is extractor
        assert matcher.quality_evaluator is evaluator

    def test_init_with_threshold_zero(self) -> None:
        """Test initialization with threshold 0.0."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=0.0)

        assert matcher.threshold == 0.0

    def test_init_with_threshold_one(self) -> None:
        """Test initialization with threshold 1.0."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=1.0)

        assert matcher.threshold == 1.0

    def test_init_with_invalid_threshold_negative(self) -> None:
        """Test initialization with negative threshold raises ValueError."""
        extractor = MagicMock()
        evaluator = MagicMock()

        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 1.0"):
            TitleSimilarityMatcher(extractor, evaluator, threshold=-0.1)

    def test_init_with_invalid_threshold_over_one(self) -> None:
        """Test initialization with threshold > 1.0 raises ValueError."""
        extractor = MagicMock()
        evaluator = MagicMock()

        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 1.0"):
            TitleSimilarityMatcher(extractor, evaluator, threshold=1.5)


class TestTitleExtraction:
    """Test title extraction from files."""

    def test_extract_from_metadata(self) -> None:
        """Test extracting title from metadata."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        file = create_test_file("attack_01.mkv", title="Attack on Titan")

        result = matcher._extract_title_from_file(file)
        assert result == "Attack on Titan"
        extractor.extract_base_title.assert_not_called()

    def test_extract_fallback_to_filename(self) -> None:
        """Test fallback to filename extraction when metadata missing."""
        extractor = MagicMock()
        extractor.extract_base_title.return_value = "Extracted Title"
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        # Create file with empty metadata (no title attribute)
        file = ScannedFile(
            file_path=Path("attack_01.mkv"),
            metadata=ParsingResult(title=None),
        )

        result = matcher._extract_title_from_file(file)
        assert result == "Extracted Title"
        extractor.extract_base_title.assert_called_once_with("attack_01.mkv")

    def test_extract_fallback_when_title_equals_filename(self) -> None:
        """Test fallback when parsed title equals filename."""
        extractor = MagicMock()
        extractor.extract_base_title.return_value = "Cleaned Title"
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        # When metadata.title == filename, fallback to extraction
        file = ScannedFile(
            file_path=Path("attack_01.mkv"),
            metadata=ParsingResult(title="attack_01.mkv"),
        )

        result = matcher._extract_title_from_file(file)
        assert result == "Cleaned Title"
        extractor.extract_base_title.assert_called_once()


class TestSimilarityCalculation:
    """Test similarity calculation between titles."""

    def test_calculate_identical_titles(self) -> None:
        """Test similarity between identical titles."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        result = matcher._calculate_similarity("Attack on Titan", "Attack on Titan")
        assert result == 1.0

    def test_calculate_case_insensitive(self) -> None:
        """Test similarity is case-insensitive."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        result = matcher._calculate_similarity("Attack on Titan", "ATTACK ON TITAN")
        assert result == 1.0

    def test_calculate_different_titles(self) -> None:
        """Test similarity between completely different titles."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        result = matcher._calculate_similarity("Attack on Titan", "Death Note")
        assert result < 0.5  # Should be very low

    def test_calculate_similar_titles(self) -> None:
        """Test similarity between similar titles."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        result = matcher._calculate_similarity("Attack on Titan", "Attack on Titan S2")
        assert 0.8 < result < 1.0  # Should be high but not perfect


class TestMatching:
    """Test file grouping by title similarity."""

    def test_match_empty_list(self) -> None:
        """Test matching empty file list returns empty."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        result = matcher.match([])
        assert result == []

    def test_match_single_file(self) -> None:
        """Test matching single file creates one group."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=0.85)

        file = create_test_file("attack_01.mkv", title="Attack on Titan")

        result = matcher.match([file])
        assert len(result) == 1
        assert result[0].title == "Attack on Titan"
        assert result[0].files == [file]

    def test_match_identical_titles(self) -> None:
        """Test matching files with identical titles groups them."""
        extractor = MagicMock()
        evaluator = MagicMock()
        evaluator.select_better_title.side_effect = lambda t1, t2: t1
        matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=0.85)

        file1 = create_test_file("attack_01.mkv", title="Attack on Titan")
        file2 = create_test_file("attack_02.mkv", title="Attack on Titan")

        result = matcher.match([file1, file2])
        assert len(result) == 1
        assert result[0].title == "Attack on Titan"
        assert len(result[0].files) == 2
        assert file1 in result[0].files and file2 in result[0].files

    def test_match_different_titles(self) -> None:
        """Test matching files with different titles creates separate groups."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=0.85)

        file1 = create_test_file("attack_01.mkv", title="Attack on Titan")
        file2 = create_test_file("death_note_01.mkv", title="Death Note")

        result = matcher.match([file1, file2])
        assert len(result) == 2

        titles = {group.title for group in result}
        assert titles == {"Attack on Titan", "Death Note"}

    def test_match_similar_titles_above_threshold(self) -> None:
        """Test matching files with similar titles above threshold groups them."""
        extractor = MagicMock()
        evaluator = MagicMock()
        evaluator.select_better_title.side_effect = lambda t1, t2: t1
        matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=0.85)

        file1 = create_test_file("attack_01.mkv", title="Attack on Titan")
        file2 = create_test_file("attack_02.mkv", title="Attack on Titan S2")

        result = matcher.match([file1, file2])
        # Should group together if similarity >= 0.85
        assert len(result) == 1
        assert len(result[0].files) == 2

    def test_match_title_quality_selection(self) -> None:
        """Test that better quality title is selected as group name."""
        extractor = MagicMock()
        evaluator = MagicMock()
        # Return the second title as better
        evaluator.select_better_title.return_value = "Attack on Titan S2"
        matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=0.85)

        # Use nearly identical titles (high similarity)
        file1 = create_test_file("attack_01.mkv", title="Attack on Titan")
        file2 = create_test_file("attack_02.mkv", title="Attack on Titan S2")

        result = matcher.match([file1, file2])
        assert len(result) == 1
        assert result[0].title == "Attack on Titan S2"

    def test_match_files_without_titles_skipped(self) -> None:
        """Test files without extractable titles are skipped."""
        extractor = MagicMock()
        extractor.extract_base_title.return_value = None
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        # File with no metadata and extractor returns None
        file = ScannedFile(
            file_path=Path("unknown.mkv"),
            metadata=ParsingResult(title=None),
        )

        result = matcher.match([file])
        assert result == []

    def test_match_multiple_groups(self) -> None:
        """Test matching creates multiple groups correctly."""
        extractor = MagicMock()
        evaluator = MagicMock()
        evaluator.select_better_title.side_effect = lambda t1, t2: t1
        matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=0.85)

        file1 = create_test_file("attack_01.mkv", title="Attack on Titan")
        file2 = create_test_file("attack_02.mkv", title="Attack on Titan")
        file3 = create_test_file("death_01.mkv", title="Death Note")
        file4 = create_test_file("death_02.mkv", title="Death Note")

        result = matcher.match([file1, file2, file3, file4])
        assert len(result) == 2

        # Check each group has 2 files
        for group in result:
            assert len(group.files) == 2

    def test_match_returns_group_objects(self) -> None:
        """Test match returns proper Group objects."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        file = create_test_file("attack_01.mkv", title="Attack on Titan")

        result = matcher.match([file])
        assert len(result) == 1
        assert isinstance(result[0], Group)
        assert hasattr(result[0], "title")
        assert hasattr(result[0], "files")


class TestComponentInterface:
    """Test BaseMatcher protocol compliance."""

    def test_has_component_name(self) -> None:
        """Test matcher has component_name attribute."""
        extractor = MagicMock()
        evaluator = MagicMock()
        matcher = TitleSimilarityMatcher(extractor, evaluator)

        assert hasattr(matcher, "component_name")
        assert matcher.component_name == "title"

    def test_match_signature(self) -> None:
        """Test match method has correct signature."""
        from inspect import signature

        sig = signature(TitleSimilarityMatcher.match)
        params = list(sig.parameters.keys())

        assert "files" in params
        assert sig.return_annotation == "list[Group]"
