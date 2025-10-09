"""Tests for CandidateFilterService."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from anivault.core.matching.services.filter_service import CandidateFilterService
from anivault.core.statistics import StatisticsCollector
from anivault.services.tmdb_models import ScoredSearchResult, TMDBSearchResult


class TestCandidateFilterService:
    """Test suite for CandidateFilterService."""

    @pytest.fixture
    def mock_statistics(self):
        """Create mock statistics collector."""
        return Mock(spec=StatisticsCollector)

    @pytest.fixture
    def service(self, mock_statistics):
        """Create CandidateFilterService instance."""
        return CandidateFilterService(statistics=mock_statistics)

    @pytest.fixture
    def sample_scored_candidates(self):
        """Sample scored candidates with different years."""
        return [
            ScoredSearchResult(
                id=1,
                name="Show 2013",
                media_type="tv",
                first_air_date="2013-04-07",
                popularity=100.0,
                vote_average=8.5,
                vote_count=5000,
                overview="2013",
                original_language="ja",
                genre_ids=[16],
                confidence_score=0.9,
            ),
            ScoredSearchResult(
                id=2,
                name="Show 2015",
                media_type="tv",
                first_air_date="2015-01-01",
                popularity=80.0,
                vote_average=8.0,
                vote_count=3000,
                overview="2015",
                original_language="ja",
                genre_ids=[16],
                confidence_score=0.8,
            ),
            ScoredSearchResult(
                id=3,
                name="Show 2025",
                media_type="tv",
                first_air_date="2025-01-01",
                popularity=60.0,
                vote_average=7.5,
                vote_count=1000,
                overview="Too far",
                original_language="ja",
                genre_ids=[16],
                confidence_score=0.7,
            ),
        ]

    @pytest.fixture
    def sample_tmdb_candidates(self):
        """Sample TMDB candidates for genre filtering."""
        return [
            TMDBSearchResult(
                id=1,
                name="Anime Show",
                media_type="tv",
                first_air_date="2013-04-07",
                popularity=100.0,
                vote_average=8.5,
                vote_count=5000,
                overview="Anime",
                original_language="ja",
                genre_ids=[16],  # Animation genre
            ),
            TMDBSearchResult(
                id=2,
                name="Drama Show",
                media_type="tv",
                first_air_date="2013-01-01",
                popularity=80.0,
                vote_average=8.0,
                vote_count=3000,
                overview="Drama",
                original_language="ko",
                genre_ids=[18],  # Drama genre
            ),
        ]

    # === Initialization Tests ===

    def test_service_initialization(self, mock_statistics):
        """Test service initialization."""
        service = CandidateFilterService(mock_statistics)
        assert service.statistics is mock_statistics

    # === Year Filter Tests ===

    def test_filter_by_year_with_hint(self, service, sample_scored_candidates):
        """Test year filtering with year hint."""
        filtered = service.filter_by_year(sample_scored_candidates, 2013)

        # Should keep 2013 and 2015 (within ±10 years)
        # Should filter out 2025 (12 years away)
        assert len(filtered) == 2
        assert filtered[0].id in [1, 2]
        assert filtered[1].id in [1, 2]

    def test_filter_by_year_no_hint_returns_all(
        self, service, sample_scored_candidates
    ):
        """Test filtering without year hint returns all candidates."""
        filtered = service.filter_by_year(sample_scored_candidates, None)

        assert len(filtered) == 3
        assert filtered == sample_scored_candidates

    def test_filter_by_year_empty_list(self, service):
        """Test filtering empty candidate list."""
        filtered = service.filter_by_year([], 2013)

        assert filtered == []

    def test_filter_by_year_boundary_10_years(self, service):
        """Test year filter at exactly 10 year boundary."""
        candidates = [
            ScoredSearchResult(
                id=1,
                name="Exactly 10 years",
                media_type="tv",
                first_air_date="2003-01-01",  # Exactly 10 years before 2013
                popularity=100.0,
                vote_average=8.0,
                vote_count=1000,
                overview="Test",
                original_language="ja",
                genre_ids=[],
                confidence_score=0.8,
            ),
            ScoredSearchResult(
                id=2,
                name="Over 10 years",
                media_type="tv",
                first_air_date="2002-12-31",  # Over 10 years
                popularity=100.0,
                vote_average=8.0,
                vote_count=1000,
                overview="Test",
                original_language="ja",
                genre_ids=[],
                confidence_score=0.8,
            ),
        ]

        filtered = service.filter_by_year(candidates, 2013)

        # Should keep exactly 10 years, filter out over 10
        assert len(filtered) == 1
        assert filtered[0].id == 1

    # === Genre Filter Tests ===

    def test_filter_by_genre_anime_only(self, service, sample_tmdb_candidates):
        """Test genre filtering keeps only anime candidates."""
        filtered = service.filter_by_genre(sample_tmdb_candidates)

        # Should keep only anime (genre_ids contains 16)
        assert len(filtered) == 1
        assert filtered[0].id == 1
        assert 16 in (filtered[0].genre_ids or [])

    def test_filter_by_genre_custom_ids(self, service):
        """Test genre filtering with custom genre IDs."""
        candidates = [
            TMDBSearchResult(
                id=1,
                name="Custom Genre",
                media_type="tv",
                first_air_date="2013-01-01",
                popularity=100.0,
                vote_average=8.0,
                vote_count=1000,
                overview="Test",
                original_language="ja",
                genre_ids=[99],  # Custom genre
            ),
        ]

        filtered = service.filter_by_genre(candidates, genre_ids=[99])

        assert len(filtered) == 1

    def test_filter_by_genre_empty_list(self, service):
        """Test genre filtering with empty candidate list."""
        filtered = service.filter_by_genre([])

        assert filtered == []

    def test_filter_by_genre_no_match(self, service, sample_tmdb_candidates):
        """Test genre filtering when no candidates match."""
        # Filter with non-existent genre ID
        filtered = service.filter_by_genre(sample_tmdb_candidates, genre_ids=[999])

        assert filtered == []

    # === Immutability Tests ===

    def test_filter_does_not_modify_input(self, service, sample_scored_candidates):
        """Test that filtering does not modify input list."""
        original_len = len(sample_scored_candidates)
        original_ids = [c.id for c in sample_scored_candidates]

        # Filter
        filtered = service.filter_by_year(sample_scored_candidates, 2013)

        # Original should be unchanged
        assert len(sample_scored_candidates) == original_len
        assert [c.id for c in sample_scored_candidates] == original_ids
        # Filtered is different
        assert filtered is not sample_scored_candidates
