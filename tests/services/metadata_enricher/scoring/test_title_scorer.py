"""Tests for TitleScorer strategy implementation.

This module tests the title similarity scoring logic using various
matching scenarios including exact matches, fuzzy matches, and edge cases.
"""

from __future__ import annotations

import pytest

from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher.models import ScoreResult
from anivault.services.metadata_enricher.scoring.title_scorer import TitleScorer
from anivault.shared.errors import DomainError


class TestTitleScorerInit:
    """Test suite for TitleScorer initialization."""

    def test_default_weight(self) -> None:
        """Test TitleScorer with default weight."""
        scorer = TitleScorer()
        assert scorer.weight == 0.6

    def test_custom_weight(self) -> None:
        """Test TitleScorer with custom weight."""
        scorer = TitleScorer(weight=0.8)
        assert scorer.weight == 0.8

    def test_invalid_weight_below_range(self) -> None:
        """Test TitleScorer with weight below valid range."""
        with pytest.raises(ValueError) as exc_info:
            TitleScorer(weight=-0.1)
        assert "weight must be between 0.0 and 1.0" in str(exc_info.value)

    def test_invalid_weight_above_range(self) -> None:
        """Test TitleScorer with weight above valid range."""
        with pytest.raises(ValueError) as exc_info:
            TitleScorer(weight=1.5)
        assert "weight must be between 0.0 and 1.0" in str(exc_info.value)


class TestTitleScorerScoring:
    """Test suite for TitleScorer scoring logic."""

    def test_exact_match(self) -> None:
        """Test exact title match returns 1.0."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="Attack on Titan")
        tmdb_candidate = {"title": "Attack on Titan", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert isinstance(result, ScoreResult)
        assert result.score == 1.0
        assert result.weight == 0.6
        assert result.component == "title_similarity"
        assert "Attack on Titan" in result.reason
        assert "Excellent match" in result.reason

    def test_case_insensitive_match(self) -> None:
        """Test case-insensitive match returns 0.95."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="attack on titan")
        tmdb_candidate = {"title": "Attack on Titan", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.95
        assert "Excellent match" in result.reason

    def test_substring_match(self) -> None:
        """Test substring match returns 0.8."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="Attack on Titan")
        tmdb_candidate = {"title": "Attack on Titan: Final Season", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.8
        assert "High similarity" in result.reason

    def test_fuzzy_match_high(self) -> None:
        """Test fuzzy match with high similarity."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="Death Note")
        tmdb_candidate = {"name": "Death Note", "id": 1535}  # TV show uses 'name'

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0  # Exact match
        assert "Excellent match" in result.reason

    def test_fuzzy_match_typo(self) -> None:
        """Test fuzzy match handles typos."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="Atack on Titan")  # Typo: 'Atack'
        tmdb_candidate = {"title": "Attack on Titan", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        # Should still get high score due to fuzzy matching
        assert result.score >= 0.8
        assert 0.0 <= result.score <= 1.0

    def test_low_similarity(self) -> None:
        """Test low similarity titles."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="Naruto")
        tmdb_candidate = {"title": "One Piece", "id": 37854}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score < 0.5
        assert "Low similarity" in result.reason


class TestTitleScorerValidation:
    """Test suite for TitleScorer input validation."""

    def test_empty_file_title_fails(self) -> None:
        """Test empty file title raises DomainError."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="")
        tmdb_candidate = {"title": "Attack on Titan", "id": 1429}

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            scorer.score(file_info, tmdb_candidate)

        assert exc_info.value.code.value == "VALIDATION_ERROR"
        assert "title cannot be empty" in str(exc_info.value).lower()

    def test_missing_tmdb_title_fails(self) -> None:
        """Test missing TMDB title raises DomainError."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="Attack on Titan")
        tmdb_candidate = {"id": 1429}  # Missing both 'title' and 'name'

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            scorer.score(file_info, tmdb_candidate)

        assert exc_info.value.code.value == "DATA_PROCESSING_ERROR"
        assert "missing title/name" in str(exc_info.value).lower()

    def test_invalid_file_info_type_fails(self) -> None:
        """Test invalid file_info type raises DomainError."""
        # Given
        scorer = TitleScorer()
        file_info = {"title": "Attack on Titan"}  # type: ignore  # Wrong type
        tmdb_candidate = {"title": "Attack on Titan", "id": 1429}

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            scorer.score(file_info, tmdb_candidate)  # type: ignore

        assert exc_info.value.code.value == "VALIDATION_ERROR"

    def test_invalid_tmdb_candidate_type_fails(self) -> None:
        """Test invalid tmdb_candidate type raises DomainError."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="Attack on Titan")
        tmdb_candidate = "Attack on Titan"  # type: ignore  # Wrong type

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            scorer.score(file_info, tmdb_candidate)  # type: ignore

        assert exc_info.value.code.value == "VALIDATION_ERROR"


class TestTitleScorerScoreResult:
    """Test suite for ScoreResult properties."""

    def test_score_result_structure(self) -> None:
        """Test ScoreResult has correct structure."""
        # Given
        scorer = TitleScorer(weight=0.7)
        file_info = ParsingResult(title="Test Title")
        tmdb_candidate = {"title": "Test Title", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert hasattr(result, "score")
        assert hasattr(result, "weight")
        assert hasattr(result, "reason")
        assert hasattr(result, "component")

    def test_score_in_valid_range(self) -> None:
        """Test score is always in valid range."""
        # Given
        scorer = TitleScorer()
        test_cases = [
            ("Attack on Titan", "Attack on Titan"),
            ("Naruto", "Naruto Shippuden"),
            ("One Piece", "Dragon Ball"),
            ("Death Note", "Death Note Relight"),
        ]

        # When & Then
        for file_title, tmdb_title in test_cases:
            file_info = ParsingResult(title=file_title)
            tmdb_candidate = {"title": tmdb_title, "id": 123}
            result = scorer.score(file_info, tmdb_candidate)

            assert (
                0.0 <= result.score <= 1.0
            ), f"Score out of range for '{file_title}' vs '{tmdb_title}'"

    def test_reason_contains_titles(self) -> None:
        """Test reason string contains both titles."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="Attack on Titan")
        tmdb_candidate = {"title": "Shingeki no Kyojin", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert "Attack on Titan" in result.reason
        assert "Shingeki no Kyojin" in result.reason
        assert "score:" in result.reason.lower()


class TestTitleScorerEdgeCases:
    """Test suite for edge cases."""

    def test_unicode_titles(self) -> None:
        """Test handling of Unicode characters in titles."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="進撃の巨人")
        tmdb_candidate = {"title": "進撃の巨人", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0  # Exact match

    def test_special_characters(self) -> None:
        """Test handling of special characters."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="Re:Zero - Starting Life in Another World")
        tmdb_candidate = {
            "title": "Re:Zero - Starting Life in Another World",
            "id": 63926,
        }

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0

    def test_very_long_titles(self) -> None:
        """Test handling of very long titles."""
        # Given
        scorer = TitleScorer()
        long_title = "A" * 200
        file_info = ParsingResult(title=long_title)
        tmdb_candidate = {"title": long_title, "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0

    def test_whitespace_handling(self) -> None:
        """Test handling of extra whitespace."""
        # Given
        scorer = TitleScorer()
        file_info = ParsingResult(title="  Attack on Titan  ")
        tmdb_candidate = {"title": "Attack on Titan", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0  # Should strip whitespace
