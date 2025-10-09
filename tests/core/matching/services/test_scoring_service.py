"""Tests for CandidateScoringService."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from anivault.core.matching.models import NormalizedQuery
from anivault.core.matching.services.scoring_service import CandidateScoringService
from anivault.core.statistics import StatisticsCollector
from anivault.services.tmdb_models import ScoredSearchResult, TMDBSearchResult


class TestCandidateScoringService:
    """Test suite for CandidateScoringService."""

    @pytest.fixture
    def mock_statistics(self):
        """Create mock statistics collector."""
        stats = Mock(spec=StatisticsCollector)
        return stats

    @pytest.fixture
    def service(self, mock_statistics):
        """Create CandidateScoringService instance."""
        return CandidateScoringService(statistics=mock_statistics)

    @pytest.fixture
    def sample_query(self):
        """Sample normalized query."""
        return NormalizedQuery(title="attack on titan", year=2013)

    @pytest.fixture
    def sample_candidates(self):
        """Sample TMDB search results."""
        return [
            TMDBSearchResult(
                id=1429,
                name="Attack on Titan",
                first_air_date="2013-04-07",
                media_type="tv",
                popularity=100.5,
                vote_average=8.5,
                vote_count=5000,
                overview="Perfect match",
                original_language="ja",
                genre_ids=[16],
            ),
            TMDBSearchResult(
                id=9999,
                name="Different Show",
                first_air_date="2015-01-01",
                media_type="tv",
                popularity=50.0,
                vote_average=7.0,
                vote_count=1000,
                overview="Poor match",
                original_language="en",
                genre_ids=[18],
            ),
        ]

    # === Initialization Tests ===

    def test_service_initialization(self, mock_statistics):
        """Test service initialization."""
        service = CandidateScoringService(mock_statistics)

        assert service.statistics is mock_statistics

    # === Scoring Tests ===

    def test_score_candidates_success(self, service, sample_candidates, sample_query):
        """Test successful scoring of candidates."""
        scored = service.score_candidates(sample_candidates, sample_query)

        assert len(scored) == 2
        assert all(isinstance(r, ScoredSearchResult) for r in scored)
        assert all(hasattr(r, "confidence_score") for r in scored)
        # First should have higher confidence (better match)
        assert scored[0].confidence_score >= scored[1].confidence_score

    def test_score_candidates_sorted_by_confidence(
        self, service, sample_candidates, sample_query
    ):
        """Test candidates are sorted by confidence score (descending)."""
        scored = service.score_candidates(sample_candidates, sample_query)

        # Verify sorted order
        for i in range(len(scored) - 1):
            assert scored[i].confidence_score >= scored[i + 1].confidence_score

    def test_score_candidates_popularity_tiebreaker(self, service, sample_query):
        """Test popularity is used as tie-breaker for equal confidence."""
        # Create candidates with potentially equal confidence
        candidates = [
            TMDBSearchResult(
                id=1,
                name="Show A",
                media_type="tv",
                first_air_date="2013-01-01",
                popularity=50.0,  # Lower popularity
                vote_average=7.0,
                vote_count=100,
                overview="Test",
                original_language="ja",
                genre_ids=[],
            ),
            TMDBSearchResult(
                id=2,
                name="Show B",
                media_type="tv",
                first_air_date="2013-01-01",
                popularity=100.0,  # Higher popularity
                vote_average=7.0,
                vote_count=100,
                overview="Test",
                original_language="ja",
                genre_ids=[],
            ),
        ]

        scored = service.score_candidates(candidates, sample_query)

        # If confidence is equal, higher popularity should come first
        if scored[0].confidence_score == scored[1].confidence_score:
            assert scored[0].popularity >= scored[1].popularity

    # === Exception Handling Tests ===

    def test_score_candidates_exception_assigns_zero_score(self, service, sample_query):
        """Test scoring exception assigns 0.0 confidence."""
        # Create candidate that will cause scoring error
        invalid_candidate = TMDBSearchResult(
            id=999,
            name="Invalid",
            media_type="tv",
            first_air_date="invalid-date",  # Invalid date format
            popularity=10.0,
            vote_average=5.0,
            vote_count=10,
            overview="Test",
            original_language="ja",
            genre_ids=[],
        )

        # Mock calculate_confidence_score to raise exception
        with patch(
            "anivault.core.matching.services.scoring_service.calculate_confidence_score",
            side_effect=Exception("Scoring error"),
        ):
            scored = service.score_candidates([invalid_candidate], sample_query)

        # Should return candidate with 0.0 score
        assert len(scored) == 1
        assert scored[0].confidence_score == 0.0

    # === Edge Cases ===

    def test_score_empty_candidate_list(self, service, sample_query):
        """Test scoring empty candidate list."""
        scored = service.score_candidates([], sample_query)

        assert scored == []

    def test_score_single_candidate(self, service, sample_candidates, sample_query):
        """Test scoring single candidate."""
        scored = service.score_candidates([sample_candidates[0]], sample_query)

        assert len(scored) == 1
        assert isinstance(scored[0], ScoredSearchResult)

    # === Confidence Level Tests ===

    def test_get_confidence_level_high(self, service):
        """Test high confidence level."""
        level = service.get_confidence_level(0.95)
        assert level == "high"

    def test_get_confidence_level_medium(self, service):
        """Test medium confidence level."""
        level = service.get_confidence_level(0.75)
        assert level == "medium"

    def test_get_confidence_level_low(self, service):
        """Test low confidence level (0.2 ≤ score < 0.5)."""
        level = service.get_confidence_level(0.35)
        assert level == "low"

    def test_get_confidence_level_very_low(self, service):
        """Test very low confidence level (score < 0.2)."""
        level = service.get_confidence_level(0.1)
        assert level == "very_low"

    def test_get_confidence_level_boundary_values(self, service):
        """Test boundary values for confidence levels."""
        # Test exact threshold values
        from anivault.shared.constants import ConfidenceThresholds

        # Exactly at HIGH threshold
        assert service.get_confidence_level(ConfidenceThresholds.HIGH) == "high"

        # Just below HIGH threshold
        assert (
            service.get_confidence_level(ConfidenceThresholds.HIGH - 0.01) == "medium"
        )

        # Exactly at MEDIUM threshold
        assert service.get_confidence_level(ConfidenceThresholds.MEDIUM) == "medium"

        # Just below MEDIUM threshold
        assert service.get_confidence_level(ConfidenceThresholds.MEDIUM - 0.01) == "low"
