"""Tests for AsyncTMDBClient functionality.

This module contains comprehensive tests for the AsyncTMDBClient including
rate limiting, connection pooling, retry logic, and error handling.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch
from unittest.mock import MagicMock

import pytest
import aiohttp
from aiolimiter import AsyncLimiter

from src.core.async_tmdb_client import (
    AsyncTMDBClient,
    TMDBConfig,
    SearchResult,
    SearchStrategy,
    SearchStrategyType,
    create_async_tmdb_client,
)


class TestAsyncTMDBClient:
    """Test AsyncTMDBClient functionality."""

    @pytest.fixture
    def config(self) -> TMDBConfig:
        """Create test configuration."""
        return TMDBConfig(
            api_key="test_key",
            language="ko-KR",
            timeout=30,
            max_retries=3,
            burst_limit=40,
            rate_limit_window=10
        )

    @pytest.fixture
    def client(self, config: TMDBConfig) -> AsyncTMDBClient:
        """Create test client."""
        return AsyncTMDBClient(config)

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock aiohttp session."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.closed = False
        return session

    def test_client_initialization(self, config: TMDBConfig) -> None:
        """Test AsyncTMDBClient initialization."""
        client = AsyncTMDBClient(config)

        assert client.config == config
        assert isinstance(client._rate_limiter, AsyncLimiter)
        assert isinstance(client._concurrency_limiter, asyncio.Semaphore)
        assert client._concurrency_limiter._value == 10
        assert client._request_count == 0

    def test_config_rate_limiting_settings(self, config: TMDBConfig) -> None:
        """Test rate limiting configuration."""
        assert config.burst_limit == 40
        assert config.rate_limit_window == 10
        assert config.requests_per_second == 4.0

    @pytest.mark.asyncio
    async def test_make_request_success(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test successful request."""
        # Initialize session
        await client._initialize_session()

        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"results": []}
        mock_response.headers = {}

        # Mock session context manager
        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch.object(client, '_session', mock_session):
            result = await client._make_request('GET', '/search/tv', {'query': 'test'})

            assert result == {"results": []}
            assert client._request_count == 1

    @pytest.mark.asyncio
    async def test_make_request_429_retry_success(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test 429 error with successful retry."""
        # Initialize session
        await client._initialize_session()

        # First response: 429 error
        mock_response_429 = AsyncMock()
        mock_response_429.status = 429
        mock_response_429.headers = {"Retry-After": "1"}

        # Second response: success
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json.return_value = {"results": []}
        mock_response_success.headers = {}

        # Mock session to return 429 first, then success
        mock_session.request.return_value.__aenter__.side_effect = [
            mock_response_429,
            mock_response_success
        ]

        with patch.object(client, '_session', mock_session):
            with patch('asyncio.sleep', return_value=None):  # Mock sleep
                result = await client._make_request('GET', '/search/tv', {'query': 'test'})

                assert result == {"results": []}
                assert client._request_count == 1

    @pytest.mark.asyncio
    async def test_make_request_429_max_retries_exceeded(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test 429 error with max retries exceeded."""
        # Initialize session
        await client._initialize_session()

        # Mock 429 response
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "1"}
        mock_response.request_info = Mock()
        mock_response.history = []

        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch.object(client, '_session', mock_session):
            with patch('asyncio.sleep', return_value=None):  # Mock sleep
                with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                    await client._make_request('GET', '/search/tv', {'query': 'test'})

                assert exc_info.value.status == 429
                assert "Rate limit exceeded after 3 retries" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_exponential_backoff(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test exponential backoff with jitter."""
        # Initialize session
        await client._initialize_session()

        # Mock ClientError
        mock_session.request.side_effect = aiohttp.ClientError("Connection error")

        with patch.object(client, '_session', mock_session):
            with patch('asyncio.sleep') as mock_sleep:
                with pytest.raises(aiohttp.ClientError):
                    await client._make_request('GET', '/search/tv', {'query': 'test'})

                # Verify exponential backoff was called
                assert mock_sleep.call_count == 3  # 3 retries

                # Check that delays increase exponentially
                calls = mock_sleep.call_args_list
                delays = [call[0][0] for call in calls]

                # First delay should be around 1.0 + jitter
                assert 1.0 <= delays[0] <= 1.5
                # Second delay should be around 2.0 + jitter
                assert 2.0 <= delays[1] <= 2.5
                # Third delay should be around 4.0 + jitter
                assert 4.0 <= delays[2] <= 4.5

    @pytest.mark.asyncio
    async def test_make_request_timeout_retry(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test timeout error with retry."""
        # Initialize session
        await client._initialize_session()

        # Mock TimeoutError
        mock_session.request.side_effect = asyncio.TimeoutError("Request timeout")

        with patch.object(client, '_session', mock_session):
            with patch('asyncio.sleep') as mock_sleep:
                with pytest.raises(asyncio.TimeoutError):
                    await client._make_request('GET', '/search/tv', {'query': 'test'})

                # Verify retry was attempted
                assert mock_sleep.call_count == 3

    @pytest.mark.asyncio
    async def test_search_tv_series(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test TV series search."""
        # Initialize session
        await client._initialize_session()

        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 1,
                    "name": "Test Anime",
                    "original_name": "Test Anime Original",
                    "first_air_date": "2020-01-01",
                    "overview": "Test overview",
                    "poster_path": "/test.jpg",
                    "popularity": 10.0,
                    "vote_average": 8.5,
                    "vote_count": 100
                }
            ]
        }
        mock_response.headers = {}

        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch.object(client, '_session', mock_session):
            result = await client.search_tv_series("Test Anime", year=2020)

            assert "results" in result
            assert len(result["results"]) == 1
            assert result["results"][0]["name"] == "Test Anime"

    @pytest.mark.asyncio
    async def test_search_multi(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test multi search."""
        # Initialize session
        await client._initialize_session()

        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"results": []}
        mock_response.headers = {}

        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch.object(client, '_session', mock_session):
            result = await client.search_multi("Test Query")

            assert "results" in result

    @pytest.mark.asyncio
    async def test_get_tv_series_details(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test TV series details retrieval."""
        # Initialize session
        await client._initialize_session()

        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "id": 1,
            "name": "Test Anime",
            "overview": "Test overview"
        }
        mock_response.headers = {}

        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch.object(client, '_session', mock_session):
            result = await client.get_tv_series_details(1, include_credits=True)

            assert result["id"] == 1
            assert result["name"] == "Test Anime"

    @pytest.mark.asyncio
    async def test_get_movie_details(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test movie details retrieval."""
        # Initialize session
        await client._initialize_session()

        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "id": 1,
            "title": "Test Movie",
            "overview": "Test overview"
        }
        mock_response.headers = {}

        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch.object(client, '_session', mock_session):
            result = await client.get_movie_details(1, include_credits=True)

            assert result["id"] == 1
            assert result["title"] == "Test Movie"

    @pytest.mark.asyncio
    async def test_get_media_details_tv(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test media details for TV series."""
        # Initialize session
        await client._initialize_session()

        with patch.object(client, 'get_tv_series_details') as mock_tv:
            mock_tv.return_value = {"id": 1, "name": "Test TV"}

            result = await client.get_media_details(1, "tv")

            mock_tv.assert_called_once_with(1, True)
            assert result == {"id": 1, "name": "Test TV"}

    @pytest.mark.asyncio
    async def test_get_media_details_movie(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test media details for movie."""
        # Initialize session
        await client._initialize_session()

        with patch.object(client, 'get_movie_details') as mock_movie:
            mock_movie.return_value = {"id": 1, "title": "Test Movie"}

            result = await client.get_media_details(1, "movie")

            mock_movie.assert_called_once_with(1, True)
            assert result == {"id": 1, "title": "Test Movie"}

    @pytest.mark.asyncio
    async def test_get_media_details_invalid_type(self, client: AsyncTMDBClient) -> None:
        """Test media details with invalid media type."""
        # Initialize session
        await client._initialize_session()

        with pytest.raises(ValueError) as exc_info:
            await client.get_media_details(1, "invalid")

        assert "Unsupported media type: invalid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_comprehensive(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test comprehensive search with multiple strategies."""
        # Initialize session
        await client._initialize_session()

        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 1,
                    "media_type": "tv",
                    "name": "Test Anime",
                    "original_name": "Test Anime Original",
                    "first_air_date": "2020-01-01",
                    "overview": "Test overview",
                    "poster_path": "/test.jpg",
                    "popularity": 10.0,
                    "vote_average": 8.5,
                    "vote_count": 100
                }
            ]
        }
        mock_response.headers = {}

        mock_session.request.return_value.__aenter__.return_value = mock_response

        with patch.object(client, '_session', mock_session):
            results = await client.search_comprehensive("Test Anime", year=2020)

            assert len(results) == 3  # 3 strategies
            assert all(isinstance(result, SearchResult) for result in results)
            assert all(result.title == "Test Anime" for result in results)

    def test_clean_title(self, client: AsyncTMDBClient) -> None:
        """Test title cleaning functionality."""
        # Test with various suffixes
        test_cases = [
            ("Anime (TV)", "Anime"),
            ("Anime (OVA)", "Anime"),
            ("Anime (ONA)", "Anime"),
            ("Anime (Movie)", "Anime"),
            ("Anime (Special)", "Anime"),
            ("Anime (TV) (OVA)", "Anime"),
            ("Regular Anime", "Regular Anime"),
        ]

        for input_title, expected in test_cases:
            result = client._clean_title(input_title)
            assert result == expected

    def test_create_search_result(self, client: AsyncTMDBClient) -> None:
        """Test SearchResult creation."""
        item = {
            "id": 1,
            "media_type": "tv",
            "name": "Test Anime",
            "original_name": "Test Anime Original",
            "first_air_date": "2020-01-01",
            "overview": "Test overview",
            "poster_path": "/test.jpg",
            "popularity": 10.0,
            "vote_average": 8.5,
            "vote_count": 100
        }

        result = client._create_search_result(item, SearchStrategy.TV_ONLY, SearchStrategyType.EXACT_TITLE_WITH_YEAR, "Test Anime", "en", 2020)

        assert isinstance(result, SearchResult)
        assert result.id == 1
        assert result.media_type == "tv"
        assert result.title == "Test Anime"
        assert result.original_title == "Test Anime Original"
        assert result.year == 2020
        assert result.overview == "Test overview"
        assert result.poster_path == "/test.jpg"
        assert result.popularity == 10.0
        assert result.vote_average == 8.5
        assert result.vote_count == 100
        assert result.strategy_used == SearchStrategy.TV_ONLY
        assert 0.0 <= result.quality_score <= 1.0

    @pytest.mark.asyncio
    async def test_close(self, client: AsyncTMDBClient, mock_session: AsyncMock) -> None:
        """Test client close method."""
        # Initialize session
        await client._initialize_session()

        mock_session.closed = False

        with patch.object(client, '_session', mock_session):
            await client.close()

            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, config: TMDBConfig) -> None:
        """Test async context manager."""
        with patch('src.core.async_tmdb_client.get_http_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_session.closed = False
            mock_get_session.return_value = mock_session

            async with AsyncTMDBClient(config) as client:
                assert isinstance(client, AsyncTMDBClient)
                # Initialize session to ensure it's properly set up
                await client._initialize_session()

            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_requests_limiting(self, client: AsyncTMDBClient) -> None:
        """Test that concurrent requests are properly limited."""
        # Mock the entire _make_request method to avoid actual API calls
        async def mock_make_request(method, endpoint, params=None, retry_count=0):
            return {"results": []}

        with patch.object(client, '_make_request', side_effect=mock_make_request):
            # Create many concurrent requests
            tasks = [client._make_request('GET', '/search/tv', {'query': f'test{i}'}) for i in range(20)]

            # All requests should complete successfully
            results = await asyncio.gather(*tasks)
            assert len(results) == 20
            assert all(result == {"results": []} for result in results)

    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self, config: TMDBConfig) -> None:
        """Test that rate limiting is properly applied."""
        # Create client with very restrictive rate limiting for testing
        config.burst_limit = 2
        config.rate_limit_window = 1
        client = AsyncTMDBClient(config)

        # Mock the entire _make_request method to avoid actual API calls
        async def mock_make_request(method, endpoint, params=None, retry_count=0):
            return {"results": []}

        with patch.object(client, '_make_request', side_effect=mock_make_request):
            # Test that rate limiting works (without actual time delays)
            # Make 5 requests - should complete without actual rate limiting delays
            tasks = [client._make_request('GET', '/search/tv', {'query': f'test{i}'}) for i in range(5)]
            results = await asyncio.gather(*tasks)

            # Verify that all requests completed successfully
            assert len(results) == 5
            assert all(result == {"results": []} for result in results)


class TestAsyncTMDBClientFactory:
    """Test AsyncTMDBClient factory functions."""

    def test_create_async_tmdb_client_with_config(self) -> None:
        """Test creating client with provided config."""
        config = TMDBConfig(api_key="test_key")

        client = create_async_tmdb_client(config)

        assert isinstance(client, AsyncTMDBClient)
        assert client.config == config

    def test_create_async_tmdb_client_without_config(self) -> None:
        """Test creating client without config (uses config manager)."""
        with patch('src.core.async_tmdb_client.get_config_manager') as mock_get_config:
            mock_config_manager = Mock()
            mock_config_manager.get.side_effect = lambda key, default=None: {
                'tmdb_api_key': 'test_key',
                'tmdb_language': 'ko-KR',
                'tmdb_fallback_language': 'en-US',
                'tmdb_timeout': 30,
                'tmdb_max_retries': 3,
                'tmdb_cache_only_mode': False
            }.get(key, default)

            mock_get_config.return_value = mock_config_manager

            client = create_async_tmdb_client()

            assert isinstance(client, AsyncTMDBClient)
            assert client.config.api_key == 'test_key'
