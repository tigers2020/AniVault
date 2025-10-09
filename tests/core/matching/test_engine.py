"""Tests for MatchingEngine class."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from anivault.core.matching.cache_models import CachedSearchData
from anivault.core.matching.engine import MatchingEngine
from anivault.core.matching.models import MatchResult, NormalizedQuery
from anivault.core.statistics import StatisticsCollector
from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.services.tmdb_client import TMDBClient
from anivault.services.tmdb_models import ScoredSearchResult, TMDBSearchResult


@pytest.fixture
def mock_cache():
    """Create mock SQLiteCacheDB."""
    cache = Mock(spec=SQLiteCacheDB)
    cache.get_cache = Mock(return_value=None)  # Default: cache miss
    cache.set_cache = Mock()
    cache.get_stats = Mock(
        return_value={
            "total_entries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
    )
    return cache


@pytest.fixture
def mock_tmdb_client():
    """Create mock TMDBClient."""
    client = Mock(spec=TMDBClient)
    # Mock search_media to return response object with .results attribute
    empty_response = Mock()
    empty_response.results = []
    client.search_media = AsyncMock(return_value=empty_response)
    return client


@pytest.fixture
def mock_statistics():
    """Create mock StatisticsCollector."""
    stats = Mock(spec=StatisticsCollector)
    # Add metrics attribute
    stats.metrics = Mock()
    stats.metrics.cache_hits = 0
    stats.metrics.cache_misses = 0
    return stats


@pytest.fixture
def engine(mock_cache, mock_tmdb_client, mock_statistics):
    """Create MatchingEngine instance with mocks."""
    return MatchingEngine(
        cache=mock_cache,
        tmdb_client=mock_tmdb_client,
        statistics=mock_statistics,
    )


@pytest.fixture
def sample_anitopy_result():
    """Sample anitopy parsing result."""
    return {
        "anime_title": "Attack on Titan",
        "anime_season": "1",
        "episode_number": "1",
        "anime_year": "2013",
    }


@pytest.fixture
def sample_tmdb_result():
    """Sample TMDB search result."""
    return TMDBSearchResult(
        id=1429,
        name="Attack on Titan",
        first_air_date="2013-04-07",
        media_type="tv",
        popularity=100.5,
        vote_average=8.5,
        vote_count=5000,
        overview="Sample overview",
        original_language="ja",
        genre_ids=[16, 10765],
    )


class TestMatchingEngineInit:
    """Test MatchingEngine initialization."""

    def test_init_with_all_params(
        self,
        mock_cache,
        mock_tmdb_client,
        mock_statistics,
    ):
        """Test initialization with all parameters."""
        engine = MatchingEngine(
            cache=mock_cache,
            tmdb_client=mock_tmdb_client,
            statistics=mock_statistics,
        )

        assert engine.cache.backend is mock_cache  # Cache wrapped in adapter
        assert engine.tmdb_client is mock_tmdb_client
        assert engine.statistics is mock_statistics

    def test_init_creates_default_statistics(self, mock_cache, mock_tmdb_client):
        """Test initialization creates default statistics if not provided."""
        engine = MatchingEngine(
            cache=mock_cache,
            tmdb_client=mock_tmdb_client,
        )

        assert engine.cache.backend is mock_cache  # Cache wrapped in adapter
        assert engine.tmdb_client is mock_tmdb_client
        assert isinstance(engine.statistics, StatisticsCollector)


class TestFindMatchBasic:
    """Test find_match basic functionality."""

    @pytest.mark.asyncio
    async def test_find_match_with_no_results(
        self,
        engine,
        sample_anitopy_result,
    ):
        """Test find_match returns None when no TMDB results."""
        # TMDB returns empty list (already mocked)
        result = await engine.find_match(sample_anitopy_result)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_match_with_invalid_query(self, engine):
        """Test find_match returns None with invalid anitopy result."""
        invalid_result = {}  # Missing required fields

        result = await engine.find_match(invalid_result)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_match_successful_match(
        self,
        engine,
        mock_tmdb_client,
        sample_anitopy_result,
        sample_tmdb_result,
    ):
        """Test find_match returns MatchResult on successful match."""
        # Mock TMDB to return a matching result
        mock_response = Mock()
        mock_response.results = [sample_tmdb_result]
        mock_tmdb_client.search_media = AsyncMock(return_value=mock_response)

        result = await engine.find_match(sample_anitopy_result)

        # Should return a MatchResult
        assert result is not None
        assert isinstance(result, MatchResult)
        assert result.tmdb_id == 1429
        assert result.title == "Attack on Titan"
        assert result.media_type == "tv"

    @pytest.mark.asyncio
    async def test_find_match_uses_cache(
        self,
        engine,
        mock_cache,
        mock_tmdb_client,
        sample_anitopy_result,
        sample_tmdb_result,
    ):
        """Test find_match checks cache before TMDB search."""
        # Mock cache to return Pydantic model
        cached_data = CachedSearchData(
            results=[sample_tmdb_result],
            language="ko-KR",
        )
        mock_cache.get = Mock(return_value=cached_data)

        # Also mock TMDB in case cache miss
        mock_response = Mock()
        mock_response.results = [sample_tmdb_result]
        mock_tmdb_client.search_media = AsyncMock(return_value=mock_response)

        result = await engine.find_match(sample_anitopy_result)

        # Should use cached result (adapter calls backend.get)
        mock_cache.get.assert_called()
        assert result is not None


class TestFindMatchConfidence:
    """Test find_match confidence scoring."""

    @pytest.mark.asyncio
    async def test_find_match_low_confidence_returns_none(
        self,
        engine,
        mock_tmdb_client,
        sample_anitopy_result,
    ):
        """Test find_match returns None if confidence is too low."""
        # Create a result with very different title AND year (low confidence)
        poor_match = TMDBSearchResult(
            id=9999,
            name="Completely Different Show",
            first_air_date="2000-01-01",  # Different year (13 years away)
            media_type="movie",  # Different media type
            popularity=10.0,
            vote_average=5.0,
            vote_count=100,
            overview="Poor match",
            original_language="en",  # Different language
            genre_ids=[18],  # Drama (non-animation)
        )

        mock_response = Mock()
        mock_response.results = [poor_match]
        mock_tmdb_client.search_media = AsyncMock(return_value=mock_response)

        result = await engine.find_match(sample_anitopy_result)

        # Should return None due to low confidence
        assert result is None

    @pytest.mark.asyncio
    async def test_find_match_high_confidence_returns_match(
        self,
        engine,
        mock_tmdb_client,
        sample_anitopy_result,
        sample_tmdb_result,
    ):
        """Test find_match returns match if confidence is high enough."""
        mock_response = Mock()
        mock_response.results = [sample_tmdb_result]
        mock_tmdb_client.search_media = AsyncMock(return_value=mock_response)

        result = await engine.find_match(sample_anitopy_result)

        # Should return match with high confidence
        assert result is not None
        assert result.confidence_score > 0.0


class TestFindMatchYearFiltering:
    """Test find_match year-based filtering."""

    @pytest.mark.asyncio
    async def test_find_match_filters_by_year(
        self,
        engine,
        mock_tmdb_client,
        sample_anitopy_result,
    ):
        """Test find_match filters results by year."""
        # Create results with different years
        correct_year = TMDBSearchResult(
            id=1429,
            name="Attack on Titan",
            first_air_date="2013-04-07",
            media_type="tv",
            popularity=100.5,
            vote_average=8.5,
            vote_count=5000,
            overview="Correct year",
            original_language="ja",
            genre_ids=[16],
        )

        wrong_year = TMDBSearchResult(
            id=9999,
            name="Attack on Titan (2020)",
            first_air_date="2020-01-01",
            media_type="tv",
            popularity=50.0,
            vote_average=7.0,
            vote_count=1000,
            overview="Wrong year",
            original_language="ja",
            genre_ids=[16],
        )

        mock_response = Mock()
        mock_response.results = [wrong_year, correct_year]
        mock_tmdb_client.search_media = AsyncMock(return_value=mock_response)

        result = await engine.find_match(sample_anitopy_result)

        # Should prefer correct year match
        assert result is not None
        assert result.year == 2013


@pytest.mark.skip(reason="_search_tmdb moved to TMDBSearchService")
class TestSearchTMDB:
    """Test _search_tmdb method.

    Note: These tests are SKIPPED because _search_tmdb was moved to TMDBSearchService.
    See tests/core/matching/services/test_search_service.py for equivalent tests.
    """

    @pytest.mark.asyncio
    async def test_search_tmdb_cache_hit(self, engine, mock_cache):
        """Test _search_tmdb returns cached results if available."""
        normalized_query = NormalizedQuery(
            title="attack on titan",
            year=2013,
        )

        sample_result = TMDBSearchResult(
            id=1429,
            name="Attack on Titan",
            media_type="tv",
            first_air_date="2013-04-07",
            popularity=100.5,
            vote_average=8.5,
            vote_count=5000,
            overview="Cached",
            original_language="ja",
            genre_ids=[16],
        )
        cached_data = CachedSearchData(results=[sample_result], language="ko-KR")
        mock_cache.get = Mock(return_value=cached_data)

        results = await engine._search_tmdb(normalized_query)

        # Should return cached results (adapter calls backend.get)
        mock_cache.get.assert_called_once()
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_tmdb_cache_miss(
        self,
        engine,
        mock_cache,
        mock_tmdb_client,
        sample_tmdb_result,
    ):
        """Test _search_tmdb fetches from TMDB on cache miss."""
        normalized_query = NormalizedQuery(
            title="attack on titan",
            year=2013,
        )

        mock_cache.get = Mock(return_value=None)  # Cache miss
        mock_response = Mock()
        mock_response.results = [sample_tmdb_result]
        mock_tmdb_client.search_media = AsyncMock(return_value=mock_response)

        results = await engine._search_tmdb(normalized_query)

        # Should call TMDB and cache result
        mock_tmdb_client.search_media.assert_called_once()
        mock_cache.set_cache.assert_called_once()
        assert len(results) == 1


class TestGetCacheStats:
    """Test get_cache_stats method."""

    def test_get_cache_stats_success(self, engine, mock_cache):
        """Test get_cache_stats returns statistics."""
        mock_cache.get_cache_info = Mock(
            return_value={
                "total_files": 100,
                "cache_hits": 50,
                "cache_misses": 50,
            },
        )

        stats = engine.get_cache_stats()

        assert isinstance(stats, dict)
        assert "hit_ratio" in stats
        assert "total_requests" in stats
        assert "cache_items" in stats
        mock_cache.get_cache_info.assert_called_once()

    def test_get_cache_stats_handles_error(self, engine, mock_cache):
        """Test get_cache_stats handles exceptions gracefully."""
        mock_cache.get_cache_info = Mock(side_effect=OSError("DB error"))

        stats = engine.get_cache_stats()

        # Should return partial stats even on error
        assert isinstance(stats, dict)
        assert stats.get("cache_items") == 0  # Defaults to 0 on error


class TestFallbackStrategies:
    """Test find_match fallback strategies."""

    @pytest.mark.skip(
        reason="Fallback strategies only boost confidence, don't re-search"
    )
    @pytest.mark.asyncio
    async def test_find_match_uses_fallback_on_no_initial_match(
        self,
        engine,
        mock_tmdb_client,
        sample_anitopy_result,
        sample_tmdb_result,
    ):
        """Test find_match tries fallback strategies if initial search fails.

        Note: This test is SKIPPED because the current fallback strategy design
        only boosts confidence scores, it doesn't perform re-searching.
        Fallback re-search logic was removed in favor of confidence boosting strategies.
        """
        # First call returns empty, second returns result (fallback)
        empty_response = Mock()
        empty_response.results = []
        success_response = Mock()
        success_response.results = [sample_tmdb_result]
        mock_tmdb_client.search_media = AsyncMock(
            side_effect=[empty_response, success_response],
        )

        result = await engine.find_match(sample_anitopy_result)

        # Should succeed using fallback
        assert result is not None
        # Should have called search twice (initial + fallback)
        assert mock_tmdb_client.search_media.call_count >= 1
