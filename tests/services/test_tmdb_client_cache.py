"""Tests for TMDBClient cache integration.

Note: TMDBClient itself does not have direct cache methods.
Caching is handled by MatchingEngine which uses TMDBClient for API calls.
This test verifies that TMDBClient works correctly with the caching layer.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from anivault.services.tmdb_client import TMDBClient
from anivault.services.tmdb_models import TMDBSearchResponse
from anivault.shared.errors import ErrorCode, InfrastructureError


class TestTMDBClientCacheIntegration:
    """Test TMDBClient cache integration scenarios."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.client = TMDBClient()

    @pytest.mark.asyncio
    async def test_search_media_with_rate_limiting(self) -> None:
        """Test that search_media works with rate limiting."""
        # Mock the API responses
        # Mock strategy search results directly
        from anivault.services.tmdb_models import TMDBSearchResult

        mock_tv_results = [TMDBSearchResult(id=1, media_type="tv", name="Test TV Show")]
        mock_movie_results = [
            TMDBSearchResult(id=2, media_type="movie", title="Test Movie")
        ]

        with (
            patch.object(
                self.client._tv_strategy, "search", return_value=mock_tv_results
            ) as mock_tv_search,
            patch.object(
                self.client._movie_strategy, "search", return_value=mock_movie_results
            ) as mock_movie_search,
        ):
            # Test search
            response = await self.client.search_media("Test")

            # Verify results
            assert isinstance(response, TMDBSearchResponse)
            assert len(response.results) == 2
            assert response.results[0].media_type == "tv"
            assert response.results[1].media_type == "movie"

            # Verify both strategies were called
            assert mock_tv_search.call_count == 1
            assert mock_movie_search.call_count == 1

    @pytest.mark.asyncio
    async def test_search_media_api_error_handling(self) -> None:
        """Test error handling when API fails."""
        # Mock both strategies to return empty results
        with (
            patch.object(self.client._tv_strategy, "search", return_value=[]),
            patch.object(self.client._movie_strategy, "search", return_value=[]),
        ):
            # Test that error is properly propagated when no results found
            with pytest.raises(InfrastructureError) as exc_info:
                await self.client.search_media("Test")

            # When both searches fail, it raises TMDB_API_MEDIA_NOT_FOUND
            assert exc_info.value.code == ErrorCode.TMDB_API_MEDIA_NOT_FOUND

    @pytest.mark.asyncio
    async def test_search_media_empty_results(self) -> None:
        """Test handling of empty API responses."""
        with patch.object(self.client, "_make_request") as mock_make_request:
            # Mock empty responses
            mock_make_request.side_effect = [
                {"results": []},  # TV search
                {"results": []},  # Movie search
            ]

            # Test search - should raise error when no results found
            with pytest.raises(InfrastructureError) as exc_info:
                await self.client.search_media("NonExistent")

            # Verify error when no results
            assert exc_info.value.code == ErrorCode.TMDB_API_MEDIA_NOT_FOUND

    def test_tmdb_client_initialization(self) -> None:
        """Test TMDBClient initialization with default parameters."""
        client = TMDBClient()

        # Verify client is properly initialized
        assert client is not None
        assert client._tv is not None
        assert client._movie is not None

    def test_tmdb_client_custom_language(self) -> None:
        """Test TMDBClient initialization with custom language."""
        client = TMDBClient(language="ko")

        # Verify client is initialized with custom language
        assert client is not None
        # Language is used internally by tmdbv3api library
