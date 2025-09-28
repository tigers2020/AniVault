"""Tests for matching engine."""

from unittest.mock import Mock

import pytest

from anivault.services.matching_engine import MatchingConfig, MatchingEngine
from anivault.services.tmdb_client import TMDBClient


class TestMatchingEngine:
    """Test cases for MatchingEngine."""

    @pytest.fixture
    def mock_tmdb_client(self):
        """Create a mock TMDB client."""
        client = Mock(spec=TMDBClient)
        return client

    @pytest.fixture
    def matching_engine(self, mock_tmdb_client):
        """Create a matching engine with mock client."""
        config = MatchingConfig(
            min_confidence=0.7,
            max_fallback_attempts=2,
            use_language_hints=True,
            use_year_hints=True,
            enable_query_variants=True,
            cache_results=True,
        )
        return MatchingEngine(mock_tmdb_client, config)

    def test_match_anime_success(self, matching_engine, mock_tmdb_client):
        """Test successful anime matching."""
        # Mock TMDB response
        mock_tmdb_client.search_tv.return_value = [
            {
                "id": 12345,
                "name": "Attack on Titan",
                "original_name": "進撃の巨人",
                "overview": "Humanity fights against Titans",
                "first_air_date": "2013-04-07",
                "popularity": 100.0,
                "vote_average": 8.5,
                "vote_count": 1000,
            },
        ]

        result = matching_engine.match_anime("Attack on Titan", 2013, "en-US")

        assert result.tmdb_id == 12345
        assert result.title == "Attack on Titan"
        assert result.confidence > 0.0
        assert result.match_type in ["exact", "high", "medium", "low"]

    def test_match_anime_no_results(self, matching_engine, mock_tmdb_client):
        """Test matching with no TMDB results."""
        mock_tmdb_client.search_tv.return_value = []

        result = matching_engine.match_anime("Unknown Anime", None, "en-US")

        assert result.tmdb_id is None
        assert result.confidence == 0.0
        assert result.match_type == "none"

    def test_match_anime_fallback_strategies(self, matching_engine, mock_tmdb_client):
        """Test fallback matching strategies."""
        # Mock successful response for fallback
        mock_tmdb_client.search_tv.return_value = [
            {
                "id": 12345,
                "name": "Attack on Titan",
                "original_name": "進撃の巨人",
                "overview": "Humanity fights against Titans",
                "first_air_date": "2013-04-07",
                "popularity": 100.0,
                "vote_average": 8.5,
                "vote_count": 1000,
            },
        ]

        result = matching_engine.match_anime("Attack on Titan (TV)", 2013, "en-US")

        assert result.tmdb_id == 12345
        assert result.fallback_attempts >= 0

    def test_calculate_confidence(self, matching_engine):
        """Test confidence calculation."""
        # Test exact match
        confidence = matching_engine._calculate_confidence(
            "Attack on Titan",
            "Attack on Titan",
            "進撃の巨人",
            "Attack on Titan",
            2013,
            "2013-04-07",
        )
        assert confidence > 0.7

        # Test partial match
        confidence = matching_engine._calculate_confidence(
            "Attack",
            "Attack on Titan",
            "進撃の巨人",
            "Attack on Titan",
            2013,
            "2013-04-07",
        )
        assert 0.0 < confidence < 1.0

    def test_determine_match_type(self, matching_engine):
        """Test match type determination."""
        assert matching_engine._determine_match_type(0.95) == "exact"
        assert matching_engine._determine_match_type(0.90) == "high"
        assert matching_engine._determine_match_type(0.75) == "medium"
        assert matching_engine._determine_match_type(0.50) == "low"
        assert matching_engine._determine_match_type(0.30) == "none"

    def test_get_stats(self, matching_engine):
        """Test statistics retrieval."""
        stats = matching_engine.get_stats()

        assert "total_queries" in stats
        assert "cache_hits" in stats
        assert "successful_matches" in stats
        assert "success_rate" in stats

    def test_clear_cache(self, matching_engine):
        """Test cache clearing."""
        # Add some data to cache
        matching_engine.cache["test_key"] = Mock()

        matching_engine.clear_cache()
        assert len(matching_engine.cache) == 0

    def test_evaluate_match(self, matching_engine):
        """Test match evaluation."""
        result_data = {
            "id": 12345,
            "name": "Attack on Titan",
            "original_name": "進撃の巨人",
            "overview": "Humanity fights against Titans",
            "first_air_date": "2013-04-07",
            "popularity": 100.0,
            "vote_average": 8.5,
            "vote_count": 1000,
        }

        result = matching_engine._evaluate_match(
            "Attack on Titan",
            result_data,
            "Attack on Titan",
            2013,
            "en-US",
        )

        assert result.tmdb_id == 12345
        assert result.title == "Attack on Titan"
        assert result.confidence > 0.0
