"""Tests for ScoringEngine implementation.

This module tests the scoring engine that orchestrates multiple
scoring strategies with weight composition and evidence collection.
"""

from __future__ import annotations

import pytest

from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher.models import MatchEvidence, ScoreResult
from anivault.services.metadata_enricher.scoring.engine import ScoringEngine
from anivault.services.metadata_enricher.scoring.media_type_scorer import (
    MediaTypeScorer,
)
from anivault.services.metadata_enricher.scoring.title_scorer import TitleScorer
from anivault.services.metadata_enricher.scoring.year_scorer import YearScorer
from anivault.shared.errors import DomainError


class MockScorer:
    """Mock scorer for testing."""

    def __init__(
        self, weight: float = 0.5, score: float = 1.0, component: str = "mock"
    ) -> None:
        self.weight = weight
        self._score = score
        self._component = component

    def score(self, file_info: ParsingResult, tmdb_candidate: dict) -> ScoreResult:
        """Return mock score."""
        return ScoreResult(
            score=self._score,
            weight=self.weight,
            reason=f"Mock scorer: {self._component}",
            component=self._component,
        )


class TestScoringEngineInit:
    """Test suite for ScoringEngine initialization."""

    def test_init_with_valid_scorers(self) -> None:
        """Test initialization with valid scorers."""
        # Given
        scorers = [MockScorer(weight=0.6), MockScorer(weight=0.4)]

        # When
        engine = ScoringEngine(scorers)

        # Then
        assert len(engine.scorers) == 2
        assert engine.normalize_weights is False

    def test_init_with_empty_scorers_fails(self) -> None:
        """Test initialization with empty scorers list fails."""
        # When & Then
        with pytest.raises(ValueError, match=r"scorers list cannot be empty"):
            ScoringEngine([])

    def test_init_with_normalize_weights(self) -> None:
        """Test initialization with weight normalization."""
        # Given
        scorers = [MockScorer(weight=0.3), MockScorer(weight=0.3)]

        # When
        engine = ScoringEngine(scorers, normalize_weights=True)

        # Then
        # Weights should be normalized to sum to 1.0
        total_weight = sum(s.weight for s in engine.scorers)
        assert abs(total_weight - 1.0) < 1e-9

    def test_init_with_invalid_scorer_no_score_method(self) -> None:
        """Test initialization with scorer missing score method."""

        # Given
        class InvalidScorer:
            weight = 0.5

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            ScoringEngine([InvalidScorer()])  # type: ignore[list-item]

        assert exc_info.value.code.value == "VALIDATION_ERROR"
        assert "does not implement score method" in exc_info.value.message

    def test_init_with_invalid_scorer_no_weight(self) -> None:
        """Test initialization with scorer missing weight attribute."""

        # Given
        class InvalidScorer:
            def score(self, file_info, tmdb_candidate):
                pass

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            ScoringEngine([InvalidScorer()])  # type: ignore[list-item]

        assert exc_info.value.code.value == "VALIDATION_ERROR"
        assert "does not have weight attribute" in exc_info.value.message

    def test_init_with_invalid_weight_type(self) -> None:
        """Test initialization with non-numeric weight."""

        # Given
        class InvalidScorer:
            weight = "invalid"  # String instead of number

            def score(self, file_info, tmdb_candidate):
                pass

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            ScoringEngine([InvalidScorer()])  # type: ignore[list-item]

        assert exc_info.value.code.value == "VALIDATION_ERROR"
        assert "must be numeric" in exc_info.value.message

    def test_init_with_weight_out_of_range(self) -> None:
        """Test initialization with weight outside [0.0, 1.0]."""
        # Given
        scorers = [MockScorer(weight=1.5)]

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            ScoringEngine(scorers)

        assert exc_info.value.code.value == "VALIDATION_ERROR"
        assert "must be in [0.0, 1.0]" in exc_info.value.message


class TestScoringEngineCalculateScore:
    """Test suite for score calculation logic."""

    def test_calculate_score_with_perfect_match(self) -> None:
        """Test score calculation with all scorers returning 1.0."""
        # Given
        engine = ScoringEngine(
            [MockScorer(weight=0.6, score=1.0), MockScorer(weight=0.4, score=1.0)]
        )
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"title": "Test", "id": 123}

        # When
        score, evidence = engine.calculate_score(file_info, tmdb_candidate)

        # Then
        assert score == 1.0
        assert isinstance(evidence, MatchEvidence)
        assert len(evidence.component_scores) == 2
        assert evidence.total_score == 1.0

    def test_calculate_score_with_partial_match(self) -> None:
        """Test score calculation with mixed scorer results."""
        # Given
        engine = ScoringEngine(
            [
                MockScorer(weight=0.6, score=0.8),  # 0.6 * 0.8 = 0.48
                MockScorer(weight=0.4, score=0.5),  # 0.4 * 0.5 = 0.20
            ]
        )
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"title": "Test", "id": 123}

        # When
        score, evidence = engine.calculate_score(file_info, tmdb_candidate)

        # Then
        # Total: 0.48 + 0.20 = 0.68
        assert abs(score - 0.68) < 1e-9
        assert len(evidence.component_scores) == 2

    def test_calculate_score_with_zero_match(self) -> None:
        """Test score calculation with all scorers returning 0.0."""
        # Given
        engine = ScoringEngine(
            [MockScorer(weight=0.6, score=0.0), MockScorer(weight=0.4, score=0.0)]
        )
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"title": "Different", "id": 123}

        # When
        score, evidence = engine.calculate_score(file_info, tmdb_candidate)

        # Then
        assert score == 0.0

    def test_calculate_score_clamps_above_one(self) -> None:
        """Test score is clamped to 1.0 if sum exceeds."""
        # Given (weights sum > 1.0, but individual scorers are valid)
        scorers = [
            MockScorer(weight=0.8, score=1.0),
            MockScorer(weight=0.8, score=1.0),
        ]
        engine = ScoringEngine(scorers)  # No normalization
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"title": "Test", "id": 123}

        # When
        score, evidence = engine.calculate_score(file_info, tmdb_candidate)

        # Then
        # Sum would be 0.8 + 0.8 = 1.6, but clamped to 1.0
        assert score == 1.0

    def test_calculate_score_with_real_scorers(self) -> None:
        """Test score calculation with real scorer implementations."""
        # Given
        engine = ScoringEngine(
            [
                TitleScorer(weight=0.6),
                YearScorer(weight=0.2),
                MediaTypeScorer(weight=0.2),
            ]
        )
        file_info = ParsingResult(title="Attack on Titan", episode=1, year=2013)
        tmdb_candidate = {
            "title": "Attack on Titan",
            "first_air_date": "2013-04-07",
            "media_type": "tv",
            "id": 1429,
        }

        # When
        score, evidence = engine.calculate_score(file_info, tmdb_candidate)

        # Then
        assert 0.0 <= score <= 1.0
        assert len(evidence.component_scores) == 3
        assert evidence.file_title == "Attack on Titan"
        assert evidence.tmdb_id == 1429


class TestScoringEngineValidation:
    """Test suite for input validation."""

    def test_calculate_score_with_invalid_file_info_type(self) -> None:
        """Test invalid file_info type raises DomainError."""
        # Given
        engine = ScoringEngine([MockScorer()])
        file_info = {"title": "Test"}  # type: ignore[arg-type]  # Wrong type
        tmdb_candidate = {"title": "Test", "id": 123}

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            engine.calculate_score(file_info, tmdb_candidate)  # type: ignore[arg-type]

        assert exc_info.value.code.value == "VALIDATION_ERROR"

    def test_calculate_score_with_invalid_tmdb_candidate_type(self) -> None:
        """Test invalid tmdb_candidate type raises DomainError."""
        # Given
        engine = ScoringEngine([MockScorer()])
        file_info = ParsingResult(title="Test")
        tmdb_candidate = "invalid"  # type: ignore[arg-type]  # Wrong type

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            engine.calculate_score(file_info, tmdb_candidate)  # type: ignore[arg-type]

        assert exc_info.value.code.value == "VALIDATION_ERROR"


class TestScoringEngineWeightNormalization:
    """Test suite for weight normalization."""

    def test_normalize_weights_with_non_unit_sum(self) -> None:
        """Test weight normalization when sum is not 1.0."""
        # Given
        scorers = [
            MockScorer(weight=0.3),  # 30%
            MockScorer(weight=0.5),  # 50%
        ]  # Sum: 0.8

        # When
        engine = ScoringEngine(scorers, normalize_weights=True)

        # Then
        # Weights should be normalized: 0.3/0.8=0.375, 0.5/0.8=0.625
        assert abs(engine.scorers[0].weight - 0.375) < 1e-9
        assert abs(engine.scorers[1].weight - 0.625) < 1e-9
        total_weight = sum(s.weight for s in engine.scorers)
        assert abs(total_weight - 1.0) < 1e-9

    def test_normalize_weights_with_all_zero(self) -> None:
        """Test weight normalization when all weights are 0.0."""
        # Given
        scorers = [MockScorer(weight=0.0), MockScorer(weight=0.0)]

        # When
        engine = ScoringEngine(scorers, normalize_weights=True)

        # Then
        # Equal weights should be assigned: 0.5 each
        assert abs(engine.scorers[0].weight - 0.5) < 1e-9
        assert abs(engine.scorers[1].weight - 0.5) < 1e-9


class TestScoringEngineErrorHandling:
    """Test suite for error handling."""

    def test_scorer_exception_is_logged_and_skipped(self) -> None:
        """Test that scorer exceptions are logged and skipped gracefully."""

        # Given
        class FailingScorer:
            weight = 0.5

            def score(self, file_info, tmdb_candidate):
                raise RuntimeError("Test error")

        engine = ScoringEngine([FailingScorer(), MockScorer(weight=0.5)])  # type: ignore[list-item]
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"title": "Test", "id": 123}

        # When
        score, evidence = engine.calculate_score(file_info, tmdb_candidate)

        # Then
        # Failing scorer should be skipped, only MockScorer contributes
        # MockScorer: 1.0 * 0.5 = 0.5
        assert score == 0.5
        assert len(evidence.component_scores) == 2  # Both scorers logged
        # First one failed (zero score), second succeeded
        assert evidence.component_scores[0].score == 0.0
        assert evidence.component_scores[1].score == 1.0


class TestScoringEngineEvidence:
    """Test suite for evidence building."""

    def test_evidence_contains_all_component_scores(self) -> None:
        """Test evidence contains results from all scorers."""
        # Given
        engine = ScoringEngine(
            [
                MockScorer(weight=0.5, component="scorer1"),
                MockScorer(weight=0.5, component="scorer2"),
            ]
        )
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"title": "Test", "id": 123}

        # When
        _, evidence = engine.calculate_score(file_info, tmdb_candidate)

        # Then
        assert len(evidence.component_scores) == 2
        components = [s.component for s in evidence.component_scores]
        assert "scorer1" in components
        assert "scorer2" in components

    def test_evidence_extracts_tmdb_fields(self) -> None:
        """Test evidence correctly extracts TMDB fields."""
        # Given
        engine = ScoringEngine([MockScorer()])
        file_info = ParsingResult(title="File Title")
        tmdb_candidate = {
            "title": "TMDB Title",
            "id": 999,
            "media_type": "tv",
        }

        # When
        _, evidence = engine.calculate_score(file_info, tmdb_candidate)

        # Then
        assert evidence.file_title == "File Title"
        assert evidence.matched_title == "TMDB Title"
        assert evidence.tmdb_id == 999
        assert evidence.media_type == "tv"

    def test_evidence_handles_missing_tmdb_fields(self) -> None:
        """Test evidence handles missing TMDB fields gracefully."""
        # Given
        engine = ScoringEngine([MockScorer()])
        file_info = ParsingResult(title="File Title")
        tmdb_candidate = {}  # Empty dict

        # When
        _, evidence = engine.calculate_score(file_info, tmdb_candidate)

        # Then
        assert evidence.tmdb_id == 1  # Default (MatchEvidence requires > 0)
        assert evidence.media_type == "movie"  # Default
        assert evidence.matched_title == "Unknown"  # Default
