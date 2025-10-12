"""Tests for scoring models (ScoreResult, MatchEvidence).

This module tests the data validation and behavior of scoring models
used in the metadata enrichment matching algorithm.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from anivault.services.metadata_enricher.models import MatchEvidence, ScoreResult


class TestScoreResult:
    """Test suite for ScoreResult dataclass."""

    def test_valid_score_result(self) -> None:
        """Test creating valid ScoreResult."""
        # Given
        score = 0.85
        weight = 0.6
        reason = "High title similarity"
        component = "title_scorer"

        # When
        result = ScoreResult(
            score=score, weight=weight, reason=reason, component=component
        )

        # Then
        assert result.score == score
        assert result.weight == weight
        assert result.reason == reason
        assert result.component == component

    def test_score_at_boundaries(self) -> None:
        """Test ScoreResult at boundary values."""
        # Test minimum valid values
        result_min = ScoreResult(score=0.0, weight=0.0, reason="Min", component="test")
        assert result_min.score == 0.0
        assert result_min.weight == 0.0

        # Test maximum valid values
        result_max = ScoreResult(score=1.0, weight=1.0, reason="Max", component="test")
        assert result_max.score == 1.0
        assert result_max.weight == 1.0

    def test_score_below_range_fails(self) -> None:
        """Test ScoreResult with score below valid range."""
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            ScoreResult(score=-0.1, weight=0.5, reason="Invalid", component="test")

        # Verify error message
        assert "score" in str(exc_info.value).lower()

    def test_score_above_range_fails(self) -> None:
        """Test ScoreResult with score above valid range."""
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            ScoreResult(score=1.5, weight=0.5, reason="Invalid", component="test")

        # Verify error message
        assert "score" in str(exc_info.value).lower()

    def test_weight_below_range_fails(self) -> None:
        """Test ScoreResult with weight below valid range."""
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            ScoreResult(score=0.5, weight=-0.1, reason="Invalid", component="test")

        # Verify error message
        assert "weight" in str(exc_info.value).lower()

    def test_weight_above_range_fails(self) -> None:
        """Test ScoreResult with weight above valid range."""
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            ScoreResult(score=0.5, weight=1.5, reason="Invalid", component="test")

        # Verify error message
        assert "weight" in str(exc_info.value).lower()

    def test_empty_reason_fails(self) -> None:
        """Test ScoreResult with empty reason string."""
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            ScoreResult(score=0.5, weight=0.5, reason="", component="test")

        # Verify error message
        assert "reason" in str(exc_info.value).lower()

    def test_empty_component_fails(self) -> None:
        """Test ScoreResult with empty component string."""
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            ScoreResult(score=0.5, weight=0.5, reason="Valid", component="")

        # Verify error message
        assert "component" in str(exc_info.value).lower()


class TestMatchEvidence:
    """Test suite for MatchEvidence dataclass."""

    def test_valid_match_evidence(self) -> None:
        """Test creating valid MatchEvidence."""
        # Given
        component_scores = [
            ScoreResult(
                score=0.85,
                weight=0.6,
                reason="High title similarity",
                component="title",
            ),
            ScoreResult(
                score=0.20,
                weight=0.2,
                reason="Episode info present",
                component="episode",
            ),
        ]

        # When
        evidence = MatchEvidence(
            total_score=0.87,
            component_scores=component_scores,
            file_title="Attack on Titan S01E01",
            matched_title="Shingeki no Kyojin",
            tmdb_id=1429,
            media_type="tv",
        )

        # Then
        assert evidence.total_score == 0.87
        assert len(evidence.component_scores) == 2
        assert evidence.file_title == "Attack on Titan S01E01"
        assert evidence.matched_title == "Shingeki no Kyojin"
        assert evidence.tmdb_id == 1429
        assert evidence.media_type == "tv"

    def test_total_score_below_range_fails(self) -> None:
        """Test MatchEvidence with total_score below valid range."""
        # Given
        component_scores = [
            ScoreResult(score=0.5, weight=0.6, reason="Test", component="title")
        ]

        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            MatchEvidence(
                total_score=-0.1,
                component_scores=component_scores,
                file_title="Test",
                matched_title="Test Match",
                tmdb_id=123,
                media_type="tv",
            )

        # Verify error message
        assert "total_score" in str(exc_info.value).lower()

    def test_total_score_above_range_fails(self) -> None:
        """Test MatchEvidence with total_score above valid range."""
        # Given
        component_scores = [
            ScoreResult(score=0.5, weight=0.6, reason="Test", component="title")
        ]

        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            MatchEvidence(
                total_score=1.5,
                component_scores=component_scores,
                file_title="Test",
                matched_title="Test Match",
                tmdb_id=123,
                media_type="tv",
            )

        # Verify error message
        assert "total_score" in str(exc_info.value).lower()

    def test_empty_component_scores_fails(self) -> None:
        """Test MatchEvidence with empty component_scores list."""
        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            MatchEvidence(
                total_score=0.5,
                component_scores=[],  # Empty list
                file_title="Test",
                matched_title="Test Match",
                tmdb_id=123,
                media_type="tv",
            )

        # Verify error message
        assert "component_scores" in str(exc_info.value).lower()

    def test_invalid_media_type_fails(self) -> None:
        """Test MatchEvidence with invalid media_type."""
        # Given
        component_scores = [
            ScoreResult(score=0.5, weight=0.6, reason="Test", component="title")
        ]

        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            MatchEvidence(
                total_score=0.5,
                component_scores=component_scores,
                file_title="Test",
                matched_title="Test Match",
                tmdb_id=123,
                media_type="invalid",  # Must be "tv" or "movie"
            )

        # Verify error message
        assert "media_type" in str(exc_info.value).lower()

    def test_invalid_tmdb_id_fails(self) -> None:
        """Test MatchEvidence with invalid tmdb_id."""
        # Given
        component_scores = [
            ScoreResult(score=0.5, weight=0.6, reason="Test", component="title")
        ]

        # When & Then
        with pytest.raises(ValidationError) as exc_info:
            MatchEvidence(
                total_score=0.5,
                component_scores=component_scores,
                file_title="Test",
                matched_title="Test Match",
                tmdb_id=0,  # Must be > 0
                media_type="tv",
            )

        # Verify error message
        assert "tmdb_id" in str(exc_info.value).lower()

    def test_get_summary(self) -> None:
        """Test get_summary() returns formatted string."""
        # Given
        component_scores = [
            ScoreResult(
                score=0.85,
                weight=0.6,
                reason="High title similarity",
                component="title",
            ),
            ScoreResult(
                score=0.20,
                weight=0.2,
                reason="Episode info present",
                component="episode",
            ),
        ]

        evidence = MatchEvidence(
            total_score=0.87,
            component_scores=component_scores,
            file_title="Test",
            matched_title="Test Match",
            tmdb_id=123,
            media_type="tv",
        )

        # When
        summary = evidence.get_summary()

        # Then
        assert "Match Score: 0.87" in summary
        assert "title:" in summary
        assert "episode:" in summary
        assert "weight: 60%" in summary
        assert "weight: 20%" in summary
