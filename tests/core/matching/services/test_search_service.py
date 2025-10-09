"""Tests for TMDBSearchService."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from anivault.core.matching.models import NormalizedQuery
from anivault.core.matching.services.search_service import TMDBSearchService
from anivault.core.statistics import StatisticsCollector
from anivault.services.tmdb_models import TMDBSearchResponse, TMDBSearchResult


class TestTMDBSearchService:
    """Test suite for TMDBSearchService."""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache adapter."""
        cache = Mock()
        cache.language = "ko-KR"
        cache.get = Mock(return_value=None)  # Default: cache miss
        cache.set = Mock()
        cache.delete = Mock()
        return cache

    @pytest.fixture
    def mock_tmdb_client(self):
        """Create mock TMDB client."""
        client = Mock()
        # Default: return empty response
        empty_response = TMDBSearchResponse(results=[])
        client.search_media = AsyncMock(return_value=empty_response)
        return client

    @pytest.fixture
    def mock_statistics(self):
        """Create mock statistics collector."""
        stats = Mock(spec=StatisticsCollector)
        stats.record_cache_hit = Mock()
        stats.record_cache_miss = Mock()
        stats.record_api_call = Mock()
        return stats

    @pytest.fixture
    def service(self, mock_tmdb_client, mock_cache, mock_statistics):
        """Create TMDBSearchService instance."""
        return TMDBSearchService(
            tmdb_client=mock_tmdb_client,
            cache=mock_cache,
            statistics=mock_statistics,
        )

    @pytest.fixture
    def sample_query(self):
        """Sample normalized query."""
        return NormalizedQuery(title="attack on titan", year=2013)

    @pytest.fixture
    def sample_result(self):
        """Sample TMDB search result."""
        return TMDBSearchResult(
            id=1429,
            name="Attack on Titan",
            first_air_date="2013-04-07",
            media_type="tv",
            popularity=100.5,
            vote_average=8.5,
            vote_count=5000,
            overview="Test",
            original_language="ja",
            genre_ids=[16],
        )

    # === Initialization Tests ===

    def test_service_initialization(
        self, mock_tmdb_client, mock_cache, mock_statistics
    ):
        """Test service initialization with dependencies."""
        service = TMDBSearchService(mock_tmdb_client, mock_cache, mock_statistics)

        assert service.tmdb_client is mock_tmdb_client
        assert service.cache is mock_cache
        assert service.statistics is mock_statistics

    # === Cache Hit Tests ===

    @pytest.mark.asyncio
    async def test_search_cache_hit_returns_cached_results(
        self, service, mock_cache, sample_query, sample_result
    ):
        """Test search returns cached results on cache hit."""
        # Setup: mock cache hit
        cached_data = {"results": [sample_result.model_dump()]}
        mock_cache.get = Mock(return_value=cached_data)

        # Execute
        results = await service.search(sample_query)

        # Verify
        assert len(results) == 1
        assert isinstance(results[0], TMDBSearchResult)
        assert results[0].id == 1429
        mock_cache.get.assert_called_once_with(
            "attack on titan", "search"
        )
        service.statistics.record_cache_hit.assert_called_once_with("search")

    @pytest.mark.asyncio
    async def test_search_cache_hit_skips_tmdb_api_call(
        self, service, mock_cache, mock_tmdb_client, sample_query, sample_result
    ):
        """Test cache hit prevents unnecessary TMDB API calls."""
        # Setup: mock cache hit
        cached_data = {"results": [sample_result.model_dump()]}
        mock_cache.get = Mock(return_value=cached_data)

        # Execute
        await service.search(sample_query)

        # Verify: TMDB client should NOT be called
        mock_tmdb_client.search_media.assert_not_called()

    # === Cache Miss Tests ===

    @pytest.mark.asyncio
    async def test_search_cache_miss_calls_tmdb_api(
        self, service, mock_cache, mock_tmdb_client, sample_query, sample_result
    ):
        """Test cache miss triggers TMDB API call."""
        # Setup: mock cache miss and TMDB response
        mock_cache.get = Mock(return_value=None)
        mock_response = TMDBSearchResponse(results=[sample_result])
        mock_tmdb_client.search_media = AsyncMock(return_value=mock_response)

        # Execute
        results = await service.search(sample_query)

        # Verify
        assert len(results) == 1
        assert results[0].id == 1429
        mock_tmdb_client.search_media.assert_called_once_with("attack on titan")
        service.statistics.record_cache_miss.assert_called_once_with("search")
        service.statistics.record_api_call.assert_called_with(
            "tmdb_search", success=True
        )

    @pytest.mark.asyncio
    async def test_search_cache_miss_stores_results(
        self, service, mock_cache, mock_tmdb_client, sample_query, sample_result
    ):
        """Test cache miss stores results in cache."""
        # Setup
        mock_cache.get = Mock(return_value=None)
        mock_response = TMDBSearchResponse(results=[sample_result])
        mock_tmdb_client.search_media = AsyncMock(return_value=mock_response)

        # Execute
        await service.search(sample_query)

        # Verify cache set was called
        mock_cache.set.assert_called_once()
        call_args = mock_cache.set.call_args
        assert call_args[1]["key"] == "attack on titan"
        assert "results" in call_args[1]["data"]
        assert call_args[1]["cache_type"] == "search"

    # === Invalid Cache Tests ===

    @pytest.mark.asyncio
    async def test_search_invalid_cache_structure_fallback_to_api(
        self, service, mock_cache, mock_tmdb_client, sample_query, sample_result
    ):
        """Test invalid cache structure triggers API fallback."""
        # Setup: invalid cache data (missing 'results')
        mock_cache.get = Mock(return_value={"invalid": "structure"})
        mock_response = TMDBSearchResponse(results=[sample_result])
        mock_tmdb_client.search_media = AsyncMock(return_value=mock_response)

        # Execute
        results = await service.search(sample_query)

        # Verify: should call TMDB API and delete invalid cache
        assert len(results) == 1
        mock_cache.delete.assert_called_with("attack on titan", "search")
        mock_tmdb_client.search_media.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_invalid_cached_results_type(
        self, service, mock_cache, sample_query
    ):
        """Test invalid cached results type (not list) invalidates cache."""
        # Setup: cached results is not a list
        mock_cache.get = Mock(return_value={"results": "not a list"})

        # Execute
        results = await service.search(sample_query)

        # Verify: cache should be invalidated
        mock_cache.delete.assert_called_with("attack on titan", "search")
        assert results == []  # Falls back to API (which returns [])

    @pytest.mark.asyncio
    async def test_search_pydantic_validation_failure_invalidates_cache(
        self, service, mock_cache, sample_query
    ):
        """Test Pydantic validation failure invalidates cache."""
        # Setup: cached data with invalid structure
        mock_cache.get = Mock(
            return_value={"results": [{"id": "invalid_id_type"}]}  # Missing fields
        )

        # Execute
        results = await service.search(sample_query)

        # Verify: invalid cache should be deleted
        mock_cache.delete.assert_called_with("attack on titan", "search")
        assert results == []

    # === Error Handling Tests ===

    @pytest.mark.asyncio
    async def test_search_tmdb_api_exception_returns_empty_list(
        self, service, mock_cache, mock_tmdb_client, sample_query
    ):
        """Test TMDB API exception returns empty list (graceful degradation)."""
        # Setup: TMDB client raises exception
        mock_cache.get = Mock(return_value=None)  # Cache miss
        mock_tmdb_client.search_media = AsyncMock(
            side_effect=Exception("TMDB API error")
        )

        # Execute
        results = await service.search(sample_query)

        # Verify: should return empty list, not raise
        assert results == []
        service.statistics.record_api_call.assert_called_with(
            "tmdb_search", success=False, error="Exception"
        )

    @pytest.mark.asyncio
    async def test_search_empty_results_from_tmdb(
        self, service, mock_cache, mock_tmdb_client, sample_query
    ):
        """Test empty results from TMDB API."""
        # Setup
        mock_cache.get = Mock(return_value=None)
        empty_response = TMDBSearchResponse(results=[])
        mock_tmdb_client.search_media = AsyncMock(return_value=empty_response)

        # Execute
        results = await service.search(sample_query)

        # Verify
        assert results == []
        mock_cache.set.assert_called_once()  # Still caches empty results

    # === Multiple Results Tests ===

    @pytest.mark.asyncio
    async def test_search_multiple_results(
        self, service, mock_cache, mock_tmdb_client, sample_query
    ):
        """Test search with multiple TMDB results."""
        # Setup: multiple results
        mock_cache.get = Mock(return_value=None)
        results_list = [
            TMDBSearchResult(
                id=1429,
                name="Attack on Titan",
                media_type="tv",
                first_air_date="2013-04-07",
                popularity=100.5,
                vote_average=8.5,
                vote_count=5000,
                overview="TV Show",
                original_language="ja",
                genre_ids=[16],
            ),
            TMDBSearchResult(
                id=99999,
                name="Attack on Titan (Movie)",
                media_type="movie",
                release_date="2015-11-25",
                popularity=50.0,
                vote_average=7.0,
                vote_count=1000,
                overview="Movie",
                original_language="ja",
                genre_ids=[16],
            ),
        ]
        mock_response = TMDBSearchResponse(results=results_list)
        mock_tmdb_client.search_media = AsyncMock(return_value=mock_response)

        # Execute
        results = await service.search(sample_query)

        # Verify
        assert len(results) == 2
        assert results[0].media_type == "tv"
        assert results[1].media_type == "movie"

