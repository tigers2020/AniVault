"""Unit tests for TitleSimilarityMatcher."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from anivault.core.file_grouper.matchers.title_matcher import TitleSimilarityMatcher
from anivault.core.file_grouper.models import Group
from anivault.core.models import ScannedFile
from anivault.core.parser.models import ParsingResult

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_title_extractor() -> Mock:
    """Create a mock TitleExtractor."""
    extractor = Mock()
    extractor.extract_base_title = Mock(
        side_effect=lambda name: name.replace("_", " ").replace(".mkv", "")
    )
    return extractor


@pytest.fixture
def mock_quality_evaluator() -> Mock:
    """Create a mock TitleQualityEvaluator."""
    evaluator = Mock()
    # Default: return first title (can be overridden in tests)
    evaluator.select_better_title = Mock(side_effect=lambda t1, t2: t1)
    return evaluator


@pytest.fixture
def sample_files_similar_titles() -> list[ScannedFile]:
    """Create sample files with similar titles."""
    return [
        ScannedFile(
            file_path=Path("/test/attack_on_titan_01.mkv"),
            metadata=ParsingResult(title="Attack on Titan", episode=1),
            file_size=500 * 1024 * 1024,
        ),
        ScannedFile(
            file_path=Path("/test/attack_on_titan_02.mkv"),
            metadata=ParsingResult(title="Attack on Titan", episode=2),
            file_size=480 * 1024 * 1024,
        ),
        ScannedFile(
            file_path=Path("/test/shingeki_no_kyojin_01.mkv"),
            metadata=ParsingResult(title="Shingeki no Kyojin", episode=1),
            file_size=450 * 1024 * 1024,
        ),
    ]


@pytest.fixture
def sample_files_dissimilar_titles() -> list[ScannedFile]:
    """Create sample files with completely different titles."""
    return [
        ScannedFile(
            file_path=Path("/test/bleach_01.mkv"),
            metadata=ParsingResult(title="Bleach", episode=1),
            file_size=500 * 1024 * 1024,
        ),
        ScannedFile(
            file_path=Path("/test/naruto_01.mkv"),
            metadata=ParsingResult(title="Naruto", episode=1),
            file_size=480 * 1024 * 1024,
        ),
    ]


class TestTitleSimilarityMatcherInit:
    """Test cases for TitleSimilarityMatcher initialization."""

    def test_init_default_threshold(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test initialization with default threshold."""
        matcher = TitleSimilarityMatcher(
            mock_title_extractor,
            mock_quality_evaluator,
        )

        assert matcher.component_name == "title"
        assert matcher.threshold == 0.85
        assert matcher.title_extractor == mock_title_extractor
        assert matcher.quality_evaluator == mock_quality_evaluator

    def test_init_custom_threshold(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test initialization with custom threshold."""
        matcher = TitleSimilarityMatcher(
            mock_title_extractor,
            mock_quality_evaluator,
            threshold=0.9,
        )

        assert matcher.threshold == 0.9

    def test_init_invalid_threshold_too_low(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test that threshold below 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 1.0"):
            TitleSimilarityMatcher(
                mock_title_extractor,
                mock_quality_evaluator,
                threshold=-0.1,
            )

    def test_init_invalid_threshold_too_high(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test that threshold above 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Threshold must be between 0.0 and 1.0"):
            TitleSimilarityMatcher(
                mock_title_extractor,
                mock_quality_evaluator,
                threshold=1.1,
            )


class TestTitleExtraction:
    """Test cases for title extraction logic."""

    def test_extract_from_metadata(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test that title is extracted from metadata when available."""
        matcher = TitleSimilarityMatcher(mock_title_extractor, mock_quality_evaluator)

        file = ScannedFile(
            file_path=Path("/test/attack_01.mkv"),
            metadata=ParsingResult(title="Attack on Titan", episode=1),
            file_size=500 * 1024 * 1024,
        )

        title = matcher._extract_title_from_file(file)
        assert title == "Attack on Titan"
        # Should NOT call extractor when metadata exists
        mock_title_extractor.extract_base_title.assert_not_called()

    def test_extract_fallback_to_extractor(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test fallback to title_extractor when metadata is missing."""
        matcher = TitleSimilarityMatcher(mock_title_extractor, mock_quality_evaluator)

        file = ScannedFile(
            file_path=Path("/test/attack_01.mkv"),
            metadata=ParsingResult(title="", episode=1),  # Empty title
            file_size=500 * 1024 * 1024,
        )

        title = matcher._extract_title_from_file(file)
        # Should call extractor
        mock_title_extractor.extract_base_title.assert_called_once_with("attack_01.mkv")
        assert title == "attack 01"  # Mock returns name with spaces


class TestSimilarityCalculation:
    """Test cases for similarity calculation."""

    def test_calculate_identical_titles(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test similarity score for identical titles."""
        matcher = TitleSimilarityMatcher(mock_title_extractor, mock_quality_evaluator)

        score = matcher._calculate_similarity("Attack on Titan", "Attack on Titan")
        assert score == 1.0

    def test_calculate_similar_titles(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test similarity score for similar titles."""
        matcher = TitleSimilarityMatcher(mock_title_extractor, mock_quality_evaluator)

        score = matcher._calculate_similarity("Attack on Titan", "Attack on Titan S01")
        assert 0.8 < score < 1.0  # Should be high similarity

    def test_calculate_dissimilar_titles(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test similarity score for completely different titles."""
        matcher = TitleSimilarityMatcher(mock_title_extractor, mock_quality_evaluator)

        score = matcher._calculate_similarity("Attack on Titan", "Bleach")
        assert score < 0.5  # Should be low similarity

    def test_calculate_case_insensitive(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test that similarity calculation is case-insensitive."""
        matcher = TitleSimilarityMatcher(mock_title_extractor, mock_quality_evaluator)

        score1 = matcher._calculate_similarity("ATTACK ON TITAN", "attack on titan")
        score2 = matcher._calculate_similarity("Attack On Titan", "Attack On Titan")

        assert score1 == score2 == 1.0


class TestMatchMethod:
    """Test cases for match() method."""

    def test_match_empty_input(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test that empty input returns empty list."""
        matcher = TitleSimilarityMatcher(mock_title_extractor, mock_quality_evaluator)

        result = matcher.match([])
        assert result == []
        assert isinstance(result, list)

    def test_match_single_file(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test matching with single file."""
        matcher = TitleSimilarityMatcher(mock_title_extractor, mock_quality_evaluator)

        files = [
            ScannedFile(
                file_path=Path("/test/attack_01.mkv"),
                metadata=ParsingResult(title="Attack on Titan", episode=1),
                file_size=500 * 1024 * 1024,
            )
        ]

        result = matcher.match(files)
        assert len(result) == 1
        assert isinstance(result[0], Group)
        assert result[0].title == "Attack on Titan"
        assert result[0].files == files

    def test_match_identical_titles(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test matching files with identical titles."""
        matcher = TitleSimilarityMatcher(mock_title_extractor, mock_quality_evaluator)

        files = [
            ScannedFile(
                file_path=Path(f"/test/attack_{i:02d}.mkv"),
                metadata=ParsingResult(title="Attack on Titan", episode=i),
                file_size=500 * 1024 * 1024,
            )
            for i in range(1, 4)
        ]

        result = matcher.match(files)
        assert len(result) == 1
        assert isinstance(result[0], Group)
        assert result[0].title == "Attack on Titan"
        assert len(result[0].files) == 3

    def test_match_similar_titles_above_threshold(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
        sample_files_similar_titles: list[ScannedFile],
    ) -> None:
        """Test matching files with similar titles above threshold."""
        # Configure quality evaluator to return first title
        mock_quality_evaluator.select_better_title = Mock(side_effect=lambda t1, t2: t1)

        matcher = TitleSimilarityMatcher(
            mock_title_extractor,
            mock_quality_evaluator,
            threshold=0.5,  # Low threshold to group similar titles
        )

        result = matcher.match(sample_files_similar_titles)

        # Files should be grouped (Attack on Titan has high similarity with itself)
        assert len(result) >= 1
        assert all(isinstance(g, Group) for g in result)
        # At least 2 files should be grouped
        max_group_size = max(len(g.files) for g in result)
        assert max_group_size >= 2

    def test_match_dissimilar_titles(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
        sample_files_dissimilar_titles: list[ScannedFile],
    ) -> None:
        """Test matching files with completely different titles."""
        matcher = TitleSimilarityMatcher(
            mock_title_extractor,
            mock_quality_evaluator,
            threshold=0.85,
        )

        result = matcher.match(sample_files_dissimilar_titles)

        # Should create separate groups for each title
        assert len(result) == 2
        assert all(isinstance(g, Group) for g in result)
        assert all(len(g.files) == 1 for g in result)

    def test_match_threshold_boundary(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test matching at threshold boundary."""
        matcher = TitleSimilarityMatcher(
            mock_title_extractor,
            mock_quality_evaluator,
            threshold=0.9,  # High threshold
        )

        files = [
            ScannedFile(
                file_path=Path("/test/attack_01.mkv"),
                metadata=ParsingResult(title="Attack on Titan", episode=1),
                file_size=500 * 1024 * 1024,
            ),
            ScannedFile(
                file_path=Path("/test/attack_02.mkv"),
                metadata=ParsingResult(title="Attack on Titan Season 1", episode=2),
                file_size=480 * 1024 * 1024,
            ),
        ]

        result = matcher.match(files)

        # With high threshold, might create separate groups
        # (depends on exact similarity score)
        assert len(result) >= 1

    def test_match_with_quality_evaluation(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test that quality evaluator is used for group naming."""
        # Configure quality evaluator to prefer longer titles
        mock_quality_evaluator.select_better_title = Mock(
            side_effect=lambda t1, t2: t2 if len(t2) > len(t1) else t1
        )

        matcher = TitleSimilarityMatcher(
            mock_title_extractor,
            mock_quality_evaluator,
            threshold=0.85,
        )

        files = [
            ScannedFile(
                file_path=Path("/test/attack_01.mkv"),
                metadata=ParsingResult(title="Attack on Titan", episode=1),
                file_size=500 * 1024 * 1024,
            ),
            ScannedFile(
                file_path=Path("/test/attack_02.mkv"),
                metadata=ParsingResult(title="Attack on Titan S01", episode=2),
                file_size=480 * 1024 * 1024,
            ),
        ]

        result = matcher.match(files)

        # Quality evaluator should have been called (titles are similar enough to group)
        assert mock_quality_evaluator.select_better_title.called
        # Should have 1 group (both files grouped together)
        assert len(result) == 1

    def test_match_files_without_metadata(
        self,
        mock_title_extractor: Mock,
        mock_quality_evaluator: Mock,
    ) -> None:
        """Test matching files that rely on title extractor."""
        matcher = TitleSimilarityMatcher(mock_title_extractor, mock_quality_evaluator)

        files = [
            ScannedFile(
                file_path=Path("/test/attack_01.mkv"),
                metadata=ParsingResult(title="", episode=1),  # Empty title
                file_size=500 * 1024 * 1024,
            ),
            ScannedFile(
                file_path=Path("/test/attack_02.mkv"),
                metadata=ParsingResult(title="", episode=2),  # Empty title
                file_size=480 * 1024 * 1024,
            ),
        ]

        result = matcher.match(files)

        # Should use extractor and group similar filenames
        assert mock_title_extractor.extract_base_title.called
        assert len(result) >= 1
        assert all(isinstance(g, Group) for g in result)
