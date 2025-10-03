"""Tests for the matching engine module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from anivault.core.matching.engine import MatchingEngine
from anivault.services.cache_v2 import JSONCacheV2
from anivault.services.tmdb_client import TMDBClient


class TestMatchingEngine:
    """Test the MatchingEngine class."""

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache instance."""
        cache = MagicMock(spec=JSONCacheV2)
        cache.get.return_value = None  # Cache miss by default
        cache.set.return_value = None
        return cache

    @pytest.fixture
    def mock_tmdb_client(self):
        """Create a mock TMDB client instance."""
        client = MagicMock(spec=TMDBClient)
        client.search_media = AsyncMock(return_value=[])
        return client

    @pytest.fixture
    def matching_engine(self, mock_cache, mock_tmdb_client):
        """Create a MatchingEngine instance with mocked dependencies."""
        return MatchingEngine(cache=mock_cache, tmdb_client=mock_tmdb_client)

    def test_initialization(self, mock_cache, mock_tmdb_client):
        """Test MatchingEngine initialization."""
        engine = MatchingEngine(cache=mock_cache, tmdb_client=mock_tmdb_client)

        assert engine.cache is mock_cache
        assert engine.tmdb_client is mock_tmdb_client

    @pytest.mark.asyncio
    async def test_search_tmdb_cache_hit(self, matching_engine, mock_cache):
        """Test TMDB search with cache hit."""
        # Setup
        normalized_query = {"title": "Attack on Titan"}
        cached_results = [
            {"id": 1, "title": "Attack on Titan", "media_type": "tv"},
            {"id": 2, "title": "Attack on Titan", "media_type": "movie"},
        ]
        mock_cache.get.return_value = cached_results

        # Execute
        result = await matching_engine._search_tmdb(normalized_query)

        # Verify
        assert result == cached_results
        mock_cache.get.assert_called_once_with("Attack on Titan", "search")
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_tmdb_cache_miss(
        self, matching_engine, mock_cache, mock_tmdb_client
    ):
        """Test TMDB search with cache miss."""
        # Setup
        normalized_query = {"title": "Attack on Titan"}
        tmdb_results = [
            {"id": 1, "title": "Attack on Titan", "media_type": "tv"},
            {"id": 2, "title": "Attack on Titan", "media_type": "movie"},
        ]
        mock_cache.get.return_value = None  # Cache miss
        mock_tmdb_client.search_media.return_value = tmdb_results

        # Execute
        result = await matching_engine._search_tmdb(normalized_query)

        # Verify
        assert result == tmdb_results
        mock_cache.get.assert_called_once_with("Attack on Titan", "search")
        mock_cache.set.assert_called_once()
        mock_tmdb_client.search_media.assert_called_once_with("Attack on Titan")

    @pytest.mark.asyncio
    async def test_search_tmdb_empty_title(self, matching_engine, mock_cache):
        """Test TMDB search with empty title."""
        # Setup
        normalized_query = {"title": ""}

        # Execute
        result = await matching_engine._search_tmdb(normalized_query)

        # Verify
        assert result == []
        mock_cache.get.assert_not_called()
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_tmdb_api_error(
        self, matching_engine, mock_cache, mock_tmdb_client
    ):
        """Test TMDB search with API error."""
        # Setup
        normalized_query = {"title": "Attack on Titan"}
        mock_cache.get.return_value = None  # Cache miss
        mock_tmdb_client.search_media.side_effect = Exception("API Error")

        # Execute
        result = await matching_engine._search_tmdb(normalized_query)

        # Verify
        assert result == []
        mock_cache.get.assert_called_once_with("Attack on Titan", "search")
        mock_cache.set.assert_not_called()

    def test_calculate_confidence_scores(self, matching_engine):
        """Test confidence score calculation."""
        # Setup
        candidates = [
            {
                "id": 1,
                "title": "Attack on Titan",
                "media_type": "tv",
                "release_date": "2013-04-07",
                "popularity": 85.2,
            },
            {
                "id": 2,
                "title": "Attack on Titan: The Final Season",
                "media_type": "tv",
                "release_date": "2020-12-07",
                "popularity": 75.0,
            },
            {
                "id": 3,
                "title": "One Piece",
                "media_type": "tv",
                "release_date": "1999-10-20",
                "popularity": 90.0,
            },
        ]
        normalized_query = {"title": "Attack on Titan", "year": 2013, "language": "en"}

        # Execute
        result = matching_engine._calculate_confidence_scores(
            candidates, normalized_query
        )

        # Verify
        assert len(result) == 3
        assert all("confidence_score" in candidate for candidate in result)

        # Should be sorted by confidence score (highest first)
        assert result[0]["confidence_score"] >= result[1]["confidence_score"]
        assert result[1]["confidence_score"] >= result[2]["confidence_score"]

        # First candidate should have highest confidence (exact match)
        assert result[0]["title"] == "Attack on Titan"
        assert result[0]["confidence_score"] > 0.8  # Should be high confidence

    def test_get_confidence_level(self, matching_engine):
        """Test confidence level determination."""
        # Test high confidence
        assert matching_engine._get_confidence_level(0.9) == "high"
        assert matching_engine._get_confidence_level(0.8) == "high"

        # Test medium confidence
        assert matching_engine._get_confidence_level(0.7) == "medium"
        assert matching_engine._get_confidence_level(0.6) == "medium"

        # Test low confidence
        assert matching_engine._get_confidence_level(0.5) == "low"
        assert matching_engine._get_confidence_level(0.4) == "low"

        # Test very low confidence
        assert matching_engine._get_confidence_level(0.3) == "very_low"
        assert matching_engine._get_confidence_level(0.0) == "very_low"

    def test_score_candidates_empty_title(self, matching_engine):
        """Test candidate scoring with empty title."""
        # Setup
        candidates = [{"id": 1, "title": "Attack on Titan"}]
        normalized_title = ""

        # Execute
        result = matching_engine._score_candidates(candidates, normalized_title)

        # Verify
        assert result == candidates  # Should return as-is

    def test_score_candidates_no_title(self, matching_engine):
        """Test candidate scoring with candidates that have no title."""
        # Setup
        candidates = [
            {"id": 1, "title": "Attack on Titan"},
            {"id": 2},  # No title
            {"id": 3, "title": ""},  # Empty title
        ]
        normalized_title = "Attack on Titan"

        # Execute
        result = matching_engine._score_candidates(candidates, normalized_title)

        # Verify
        assert len(result) == 1  # Only the first candidate should be included
        assert result[0]["id"] == 1

    def test_filter_and_sort_by_year(self, matching_engine):
        """Test year-based filtering and sorting."""
        # Setup
        candidates = [
            {
                "id": 1,
                "title": "Attack on Titan",
                "first_air_date": "2013-04-07",
                "title_score": 100,
            },
            {
                "id": 2,
                "title": "Attack on Titan S2",
                "first_air_date": "2017-04-01",
                "title_score": 95,
            },
            {
                "id": 3,
                "title": "Attack on Titan S3",
                "first_air_date": "2018-07-23",
                "title_score": 90,
            },
        ]
        year_hint = "2013"

        # Execute
        result = matching_engine._filter_and_sort_by_year(candidates, year_hint)

        # Verify
        assert len(result) == 3
        assert all("year_score" in candidate for candidate in result)
        assert all("year_diff" in candidate for candidate in result)

        # Should be sorted by year score (highest first)
        assert result[0]["year_score"] >= result[1]["year_score"]
        assert result[1]["year_score"] >= result[2]["year_score"]

        # First candidate should have best year match
        assert result[0]["id"] == 1  # 2013
        assert result[0]["year_score"] == 100
        assert result[0]["year_diff"] == 0

    def test_filter_and_sort_by_year_no_hint(self, matching_engine):
        """Test year filtering with no year hint."""
        # Setup
        candidates = [{"id": 1, "title": "Attack on Titan", "title_score": 100}]

        # Execute
        result = matching_engine._filter_and_sort_by_year(candidates, None)

        # Verify
        assert result == candidates  # Should return as-is

    def test_filter_and_sort_by_year_invalid_hint(self, matching_engine):
        """Test year filtering with invalid year hint."""
        # Setup
        candidates = [{"id": 1, "title": "Attack on Titan", "title_score": 100}]

        # Execute
        result = matching_engine._filter_and_sort_by_year(candidates, "invalid")

        # Verify
        assert result == candidates  # Should return as-is

    def test_filter_and_sort_by_year_no_year_in_candidate(self, matching_engine):
        """Test year filtering with candidates that have no year."""
        # Setup
        candidates = [
            {"id": 1, "title": "Attack on Titan", "title_score": 100},
            {"id": 2, "title": "No Year", "title_score": 90},
        ]
        year_hint = "2013"

        # Execute
        result = matching_engine._filter_and_sort_by_year(candidates, year_hint)

        # Verify
        assert len(result) == 2  # Both candidates should be included with low priority
        # Should be sorted by title score (highest first)
        assert result[0]["id"] == 1  # Attack on Titan (title_score: 100)
        assert result[1]["id"] == 2  # No Year (title_score: 90)

    @pytest.mark.asyncio
    async def test_find_match_success(
        self, matching_engine, mock_cache, mock_tmdb_client
    ):
        """Test successful match finding."""
        # Setup
        anitopy_result = {
            "anime_title": "Attack on Titan",
            "episode_number": "01",
            "release_group": "HorribleSubs",
            "anime_year": 2013,
        }

        tmdb_results = [
            {
                "id": 1,
                "title": "Attack on Titan",
                "media_type": "tv",
                "release_date": "2013-04-07",
                "popularity": 85.2,
            },
            {
                "id": 2,
                "title": "Attack on Titan: The Final Season",
                "media_type": "tv",
                "release_date": "2020-12-07",
                "popularity": 75.0,
            },
        ]

        mock_cache.get.return_value = None  # Cache miss
        mock_tmdb_client.search_media.return_value = tmdb_results

        # Execute
        result = await matching_engine.find_match(anitopy_result)

        # Verify
        assert result is not None
        assert result["id"] == 1
        assert result["title"] == "Attack on Titan"
        assert "confidence_score" in result
        assert "matching_metadata" in result
        assert result["matching_metadata"]["original_title"] == "Attack on Titan"
        assert result["matching_metadata"]["total_candidates"] == 2
        assert result["matching_metadata"]["confidence_score"] > 0.0

    @pytest.mark.asyncio
    async def test_find_match_no_candidates(
        self, matching_engine, mock_cache, mock_tmdb_client
    ):
        """Test match finding with no candidates."""
        # Setup
        anitopy_result = {"anime_title": "Unknown Anime"}
        mock_cache.get.return_value = None  # Cache miss
        mock_tmdb_client.search_media.return_value = []

        # Execute
        result = await matching_engine.find_match(anitopy_result)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_find_match_normalization_failure(self, matching_engine):
        """Test match finding with normalization failure."""
        # Setup
        anitopy_result = {}  # Empty result

        # Execute
        result = await matching_engine.find_match(anitopy_result)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_find_match_exception(self, matching_engine, mock_cache):
        """Test match finding with exception."""
        # Setup
        anitopy_result = {"anime_title": "Attack on Titan"}
        mock_cache.get.side_effect = Exception("Cache error")

        # Execute
        result = await matching_engine.find_match(anitopy_result)

        # Verify
        assert result is None

    def test_apply_genre_filter_with_animation(self, matching_engine):
        """Test genre filter with animation candidates."""
        # Setup
        candidates = [
            {
                "id": 1,
                "title": "Attack on Titan",
                "confidence_score": 0.6,
                "genre_ids": [16, 28, 12],  # Animation, Action, Adventure
            },
            {
                "id": 2,
                "title": "The Matrix",
                "confidence_score": 0.7,
                "genre_ids": [28, 878],  # Action, Sci-Fi
            },
            {
                "id": 3,
                "title": "Spirited Away",
                "confidence_score": 0.5,
                "genre_ids": [16, 12, 14],  # Animation, Adventure, Fantasy
            },
        ]

        # Execute
        result = matching_engine._apply_genre_filter(candidates)

        # Verify
        assert len(result) == 3

        # Check that animation candidates got boosted
        attack_on_titan = next(c for c in result if c["id"] == 1)
        matrix = next(c for c in result if c["id"] == 2)
        spirited_away = next(c for c in result if c["id"] == 3)

        # Animation candidates should have higher confidence
        assert attack_on_titan["confidence_score"] == 0.7  # 0.6 + 0.1
        assert spirited_away["confidence_score"] == 0.6  # 0.5 + 0.1
        assert matrix["confidence_score"] == 0.7  # No boost

        # Results should be sorted by confidence (highest first)
        assert result[0]["confidence_score"] >= result[1]["confidence_score"]
        assert result[1]["confidence_score"] >= result[2]["confidence_score"]

    def test_apply_genre_filter_without_animation(self, matching_engine):
        """Test genre filter with no animation candidates."""
        # Setup
        candidates = [
            {
                "id": 1,
                "title": "The Matrix",
                "confidence_score": 0.7,
                "genre_ids": [28, 878],  # Action, Sci-Fi
            },
            {
                "id": 2,
                "title": "Inception",
                "confidence_score": 0.6,
                "genre_ids": [28, 878, 53],  # Action, Sci-Fi, Thriller
            },
        ]

        # Execute
        result = matching_engine._apply_genre_filter(candidates)

        # Verify
        assert len(result) == 2
        assert result[0]["confidence_score"] == 0.7  # No change
        assert result[1]["confidence_score"] == 0.6  # No change

    def test_apply_genre_filter_empty_candidates(self, matching_engine):
        """Test genre filter with empty candidates list."""
        # Execute
        result = matching_engine._apply_genre_filter([])

        # Verify
        assert result == []

    def test_apply_genre_filter_nested_tmdb_data(self, matching_engine):
        """Test genre filter with genre_ids in nested tmdb_data."""
        # Setup
        candidates = [
            {
                "id": 1,
                "title": "Attack on Titan",
                "confidence_score": 0.6,
                "tmdb_data": {
                    "genre_ids": [16, 28, 12],  # Animation, Action, Adventure
                },
            },
        ]

        # Execute
        result = matching_engine._apply_genre_filter(candidates)

        # Verify
        assert len(result) == 1
        assert result[0]["confidence_score"] == 0.7  # 0.6 + 0.1

    def test_apply_partial_substring_match_success(self, matching_engine):
        """Test partial substring matching with successful match."""
        # Setup
        candidates = [
            {
                "id": 1,
                "title": "Kimetsu no Yaiba",
                "confidence_score": 0.3,
            },
            {
                "id": 2,
                "title": "Attack on Titan",
                "confidence_score": 0.4,
            },
        ]
        normalized_query = {"title": "KNY"}

        # Execute
        result = matching_engine._apply_partial_substring_match(
            candidates, normalized_query
        )

        # Verify
        assert len(result) == 2

        # KNY should match "Kimetsu no Yaiba" better
        kimetsu = next(c for c in result if c["id"] == 1)
        attack = next(c for c in result if c["id"] == 2)

        assert kimetsu["partial_match_score"] > 0
        assert kimetsu["used_partial_matching"] is True
        assert kimetsu["confidence_score"] > 0.3  # Should be improved

        # Results should be sorted by confidence
        assert result[0]["confidence_score"] >= result[1]["confidence_score"]

    def test_apply_partial_substring_match_no_improvement(self, matching_engine):
        """Test partial substring matching with no improvement."""
        # Setup
        candidates = [
            {
                "id": 1,
                "title": "Attack on Titan",
                "confidence_score": 0.8,
            },
        ]
        normalized_query = {"title": "xyz"}  # Very different title

        # Execute
        result = matching_engine._apply_partial_substring_match(
            candidates, normalized_query
        )

        # Verify
        assert len(result) == 1
        assert result[0]["confidence_score"] == 0.8  # No change
        assert result[0]["used_partial_matching"] is False

    def test_apply_partial_substring_match_empty_candidates(self, matching_engine):
        """Test partial substring matching with empty candidates list."""
        # Execute
        result = matching_engine._apply_partial_substring_match([], {"title": "Test"})

        # Verify
        assert result == []

    def test_apply_partial_substring_match_no_title(self, matching_engine):
        """Test partial substring matching with no title in query."""
        # Setup
        candidates = [{"id": 1, "title": "Test", "confidence_score": 0.5}]
        normalized_query = {}

        # Execute
        result = matching_engine._apply_partial_substring_match(
            candidates, normalized_query
        )

        # Verify
        assert result == candidates  # Should return unchanged

    def test_apply_fallback_strategies_high_confidence_after_genre(
        self, matching_engine
    ):
        """Test fallback strategies when genre filtering produces high confidence."""
        # Setup
        candidates = [
            {
                "id": 1,
                "title": "My Neighbor Totoro",
                "confidence_score": 0.6,
                "genre_ids": [16, 12, 14],  # Animation
            },
            {
                "id": 2,
                "title": "The Matrix",
                "confidence_score": 0.7,
                "genre_ids": [28, 878],  # Not animation
            },
        ]
        normalized_query = {"title": "Totoro"}

        # Execute
        result = matching_engine._apply_fallback_strategies(
            candidates, normalized_query
        )

        # Verify
        assert len(result) == 2
        # My Neighbor Totoro should be first (boosted by genre + partial matching)
        assert result[0]["id"] == 1
        assert result[0]["confidence_score"] > 0.6  # Should be higher than original
        assert result[0]["confidence_score"] >= 0.7  # Should be at least genre boost

    def test_apply_fallback_strategies_low_confidence_after_genre(
        self, matching_engine
    ):
        """Test fallback strategies when genre filtering doesn't improve confidence enough."""
        # Setup
        candidates = [
            {
                "id": 1,
                "title": "Attack on Titan",
                "confidence_score": 0.3,
                "genre_ids": [16, 28, 12],  # Animation
            },
        ]
        normalized_query = {"title": "AOT"}

        # Execute
        result = matching_engine._apply_fallback_strategies(
            candidates, normalized_query
        )

        # Verify
        assert len(result) == 1
        # Should have applied partial matching
        assert result[0]["partial_match_score"] > 0
        assert result[0]["used_partial_matching"] is True

    def test_apply_fallback_strategies_empty_candidates(self, matching_engine):
        """Test fallback strategies with empty candidates list."""
        # Execute
        result = matching_engine._apply_fallback_strategies([], {"title": "Test"})

        # Verify
        assert result == []
