"""Tests for MediaTypeScorer strategy implementation.

This module tests the media type matching scoring logic with various
scenarios including TV/movie matches, mismatches, and edge cases.
"""

from __future__ import annotations

import pytest

from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher.models import ScoreResult
from anivault.services.metadata_enricher.scoring.media_type_scorer import (
    MediaTypeScorer,
)
from anivault.shared.errors import DomainError


class TestMediaTypeScorerInit:
    """Test suite for MediaTypeScorer initialization."""

    def test_default_weight(self) -> None:
        """Test MediaTypeScorer with default weight."""
        scorer = MediaTypeScorer()
        assert scorer.weight == 0.1

    def test_custom_weight(self) -> None:
        """Test MediaTypeScorer with custom weight."""
        scorer = MediaTypeScorer(weight=0.2)
        assert scorer.weight == 0.2

    def test_invalid_weight_below_range(self) -> None:
        """Test MediaTypeScorer with weight below valid range."""
        with pytest.raises(ValueError, match=r"weight must be between"):
            MediaTypeScorer(weight=-0.1)

    def test_invalid_weight_above_range(self) -> None:
        """Test MediaTypeScorer with weight above valid range."""
        with pytest.raises(ValueError, match=r"weight must be between"):
            MediaTypeScorer(weight=1.5)


class TestMediaTypeScorerMatching:
    """Test suite for media type matching logic."""

    def test_tv_show_with_episode_matches_tv(self) -> None:
        """Test TV show with episode info matches TMDB TV."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Attack on Titan", episode=1)
        tmdb_candidate = {"media_type": "tv", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert isinstance(result, ScoreResult)
        assert result.score == 1.0
        assert result.weight == 0.1
        assert result.component == "media_type_match"
        assert "Media type match: tv" in result.reason

    def test_tv_show_with_season_matches_tv(self) -> None:
        """Test TV show with season info matches TMDB TV."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Attack on Titan", season=1)
        tmdb_candidate = {"media_type": "tv", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0
        assert "Media type match: tv" in result.reason

    def test_tv_show_with_both_episode_and_season_matches_tv(self) -> None:
        """Test TV show with both episode and season matches TMDB TV."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Attack on Titan", episode=1, season=1)
        tmdb_candidate = {"media_type": "tv", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0

    def test_movie_without_episode_matches_movie(self) -> None:
        """Test movie without episode info matches TMDB movie."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Spirited Away")
        tmdb_candidate = {"media_type": "movie", "id": 129}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0
        assert "Media type match: movie" in result.reason

    def test_tv_show_with_episode_mismatches_movie(self) -> None:
        """Test TV show with episode mismatches TMDB movie."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Attack on Titan", episode=1)
        tmdb_candidate = {"media_type": "movie", "id": 129}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Media type mismatch" in result.reason
        assert "expected tv, got movie" in result.reason

    def test_movie_without_episode_mismatches_tv(self) -> None:
        """Test movie without episode mismatches TMDB TV."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Spirited Away")
        tmdb_candidate = {"media_type": "tv", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Media type mismatch" in result.reason
        assert "expected movie, got tv" in result.reason


class TestMediaTypeScorerMissingType:
    """Test suite for missing media type scenarios."""

    def test_missing_media_type_field(self) -> None:
        """Test when media_type field is missing."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"id": 123}  # No media_type

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Media type unavailable" in result.reason

    def test_empty_media_type_field(self) -> None:
        """Test when media_type field is empty."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"media_type": "", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Media type unavailable" in result.reason

    def test_none_media_type_field(self) -> None:
        """Test when media_type field is None."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"media_type": None, "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Media type unavailable" in result.reason

    def test_invalid_media_type_value(self) -> None:
        """Test when media_type has unknown value."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"media_type": "unknown_type", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Media type unavailable" in result.reason


class TestMediaTypeScorerCaseInsensitivity:
    """Test suite for case insensitivity."""

    def test_uppercase_tv(self) -> None:
        """Test uppercase TV media type."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Test", episode=1)
        tmdb_candidate = {"media_type": "TV", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0

    def test_uppercase_movie(self) -> None:
        """Test uppercase MOVIE media type."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"media_type": "MOVIE", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0

    def test_mixed_case(self) -> None:
        """Test mixed case media type."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Test", episode=1)
        tmdb_candidate = {"media_type": "Tv", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0


class TestMediaTypeScorerValidation:
    """Test suite for input validation."""

    def test_invalid_file_info_type(self) -> None:
        """Test invalid file_info type raises DomainError."""
        # Given
        scorer = MediaTypeScorer()
        file_info = {"title": "Test"}  # type: ignore[arg-type]  # Wrong type
        tmdb_candidate = {"media_type": "tv", "id": 123}

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            scorer.score(file_info, tmdb_candidate)  # type: ignore[arg-type]

        assert exc_info.value.code.value == "VALIDATION_ERROR"

    def test_invalid_tmdb_candidate_type(self) -> None:
        """Test invalid tmdb_candidate type raises DomainError."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Test")
        tmdb_candidate = "tv"  # type: ignore[arg-type]  # Wrong type

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            scorer.score(file_info, tmdb_candidate)  # type: ignore[arg-type]

        assert exc_info.value.code.value == "VALIDATION_ERROR"


class TestMediaTypeScorerEdgeCases:
    """Test suite for edge cases."""

    def test_non_string_media_type(self) -> None:
        """Test non-string media_type field."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"media_type": 123, "id": 123}  # type: ignore[dict-item]  # int

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Media type unavailable" in result.reason

    def test_score_result_structure(self) -> None:
        """Test ScoreResult has correct structure."""
        # Given
        scorer = MediaTypeScorer(weight=0.2)
        file_info = ParsingResult(title="Test", episode=1)
        tmdb_candidate = {"media_type": "tv", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert hasattr(result, "score")
        assert hasattr(result, "weight")
        assert hasattr(result, "reason")
        assert hasattr(result, "component")
        assert result.weight == 0.2

    def test_score_always_in_valid_range(self) -> None:
        """Test score is always in valid range."""
        # Given
        scorer = MediaTypeScorer()
        test_cases = [
            (ParsingResult(title="Test", episode=1), {"media_type": "tv"}),
            (ParsingResult(title="Test"), {"media_type": "movie"}),
            (ParsingResult(title="Test", episode=1), {"media_type": "movie"}),
            (ParsingResult(title="Test"), {"id": 123}),
        ]

        # When & Then
        for file_info, tmdb_candidate in test_cases:
            result = scorer.score(file_info, tmdb_candidate)
            assert 0.0 <= result.score <= 1.0

    def test_reason_contains_meaningful_info(self) -> None:
        """Test reason string contains meaningful information."""
        # Given
        scorer = MediaTypeScorer()
        file_info = ParsingResult(title="Test", episode=1)
        tmdb_candidate = {"media_type": "movie", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert "mismatch" in result.reason.lower()
        assert "tv" in result.reason.lower()
        assert "movie" in result.reason.lower()
