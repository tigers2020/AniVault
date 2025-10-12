"""Tests for TMDBFetcher module.

This module tests the TMDBFetcher class which encapsulates TMDB API interactions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from anivault.services.metadata_enricher.fetcher import TMDBFetcher
from anivault.services.tmdb_client import TMDBClient
from anivault.services.tmdb_models import (
    TMDBMediaDetails,
    TMDBSearchResponse,
    TMDBSearchResult,
)
from anivault.shared.errors import DomainError, ErrorCode, InfrastructureError


@pytest.fixture
def mock_tmdb_client() -> Mock:
    """Create a mock TMDB client."""
    client = Mock(spec=TMDBClient)
    client.search_media = AsyncMock()
    client.get_media_details = AsyncMock()
    return client


@pytest.fixture
def fetcher(mock_tmdb_client: Mock) -> TMDBFetcher:
    """Create a TMDBFetcher instance with mock client."""
    return TMDBFetcher(mock_tmdb_client)


class TestTMDBFetcherInit:
    """Tests for TMDBFetcher initialization."""

    def test_init_with_valid_client(self, mock_tmdb_client: Mock) -> None:
        """Test initialization with valid TMDB client."""
        fetcher = TMDBFetcher(mock_tmdb_client)
        assert fetcher.tmdb_client is mock_tmdb_client

    def test_init_with_none_client_raises_error(self) -> None:
        """Test initialization with None client raises ValueError."""
        with pytest.raises(ValueError, match="TMDB client cannot be None"):
            TMDBFetcher(None)  # type: ignore[arg-type]


class TestTMDBFetcherSearch:
    """Tests for TMDBFetcher.search() method."""

    @pytest.mark.asyncio
    async def test_search_success(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test successful search returns list of dicts."""
        # Given: Mock search response
        mock_result = Mock(spec=TMDBSearchResult)
        mock_result.model_dump.return_value = {
            "id": 1429,
            "title": "Attack on Titan",
            "media_type": "tv",
        }
        mock_response = Mock(spec=TMDBSearchResponse)
        mock_response.results = [mock_result]
        mock_tmdb_client.search_media.return_value = mock_response

        # When: Search for title
        results = await fetcher.search("Attack on Titan")

        # Then: Returns list of dicts
        assert len(results) == 1
        assert results[0]["id"] == 1429
        assert results[0]["title"] == "Attack on Titan"
        mock_tmdb_client.search_media.assert_awaited_once_with("Attack on Titan")

    @pytest.mark.asyncio
    async def test_search_no_results(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test search with no results returns empty list."""
        # Given: Empty search response
        mock_response = Mock(spec=TMDBSearchResponse)
        mock_response.results = []
        mock_tmdb_client.search_media.return_value = mock_response

        # When: Search for unknown title
        results = await fetcher.search("Unknown Title")

        # Then: Returns empty list
        assert results == []
        mock_tmdb_client.search_media.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_connection_error(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test search with connection error raises InfrastructureError."""
        # Given: Connection error
        mock_tmdb_client.search_media.side_effect = ConnectionError("Network error")

        # When/Then: Raises InfrastructureError
        with pytest.raises(InfrastructureError) as exc_info:
            await fetcher.search("Test")

        assert exc_info.value.code == ErrorCode.TMDB_API_CONNECTION_ERROR
        assert "Network error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_search_timeout_error(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test search with timeout error raises InfrastructureError."""
        # Given: Timeout error
        mock_tmdb_client.search_media.side_effect = TimeoutError("Request timeout")

        # When/Then: Raises InfrastructureError
        with pytest.raises(InfrastructureError) as exc_info:
            await fetcher.search("Test")

        assert exc_info.value.code == ErrorCode.TMDB_API_CONNECTION_ERROR
        assert "Network error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_search_value_error(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test search with data processing error raises DomainError."""
        # Given: ValueError during model_dump
        mock_result = Mock(spec=TMDBSearchResult)
        mock_result.model_dump.side_effect = ValueError("Invalid data")
        mock_response = Mock(spec=TMDBSearchResponse)
        mock_response.results = [mock_result]
        mock_tmdb_client.search_media.return_value = mock_response

        # When/Then: Raises DomainError
        with pytest.raises(DomainError) as exc_info:
            await fetcher.search("Test")

        assert exc_info.value.code == ErrorCode.DATA_PROCESSING_ERROR
        assert "Data processing error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_search_unexpected_error(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test search with unexpected error raises InfrastructureError."""
        # Given: Unexpected error
        mock_tmdb_client.search_media.side_effect = RuntimeError("Unexpected error")

        # When/Then: Raises InfrastructureError
        with pytest.raises(InfrastructureError) as exc_info:
            await fetcher.search("Test")

        assert exc_info.value.code == ErrorCode.TMDB_API_REQUEST_FAILED
        assert "Unexpected error" in exc_info.value.message


class TestTMDBFetcherFetchDetails:
    """Tests for TMDBFetcher.fetch_details() method."""

    @pytest.mark.asyncio
    async def test_fetch_details_success(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test successful details fetch returns TMDBMediaDetails."""
        # Given: Mock media details
        mock_details = Mock(spec=TMDBMediaDetails)
        mock_tmdb_client.get_media_details.return_value = mock_details

        # When: Fetch details
        result = await fetcher.fetch_details(1429, "tv")

        # Then: Returns TMDBMediaDetails
        assert result is mock_details
        mock_tmdb_client.get_media_details.assert_awaited_once_with(1429, "tv")

    @pytest.mark.asyncio
    async def test_fetch_details_none_with_fallback(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test None response uses fallback data."""
        # Given: None response + fallback data
        mock_tmdb_client.get_media_details.return_value = None
        fallback_data = {"id": 1429, "title": "Fallback"}

        # When: Fetch details with fallback
        result = await fetcher.fetch_details(1429, "tv", fallback_data=fallback_data)

        # Then: Returns fallback data
        assert result == fallback_data

    @pytest.mark.asyncio
    async def test_fetch_details_none_without_fallback(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test None response without fallback raises DomainError."""
        # Given: None response + no fallback
        mock_tmdb_client.get_media_details.return_value = None

        # When/Then: Raises DomainError
        with pytest.raises(DomainError) as exc_info:
            await fetcher.fetch_details(1429, "tv")

        assert exc_info.value.code == ErrorCode.DATA_PROCESSING_ERROR
        assert "TMDB returned None" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_fetch_details_connection_error_with_fallback(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test connection error with fallback returns fallback data."""
        # Given: Connection error + fallback data
        mock_tmdb_client.get_media_details.side_effect = ConnectionError(
            "Network error"
        )
        fallback_data = {"id": 1429, "title": "Fallback"}

        # When: Fetch details with fallback
        result = await fetcher.fetch_details(1429, "tv", fallback_data=fallback_data)

        # Then: Returns fallback data
        assert result == fallback_data

    @pytest.mark.asyncio
    async def test_fetch_details_connection_error_without_fallback(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test connection error without fallback raises InfrastructureError."""
        # Given: Connection error + no fallback
        mock_tmdb_client.get_media_details.side_effect = ConnectionError(
            "Network error"
        )

        # When/Then: Raises InfrastructureError
        with pytest.raises(InfrastructureError) as exc_info:
            await fetcher.fetch_details(1429, "tv")

        assert exc_info.value.code == ErrorCode.TMDB_API_CONNECTION_ERROR
        assert "Network error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_fetch_details_value_error_no_fallback(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test data processing error always raises DomainError (no fallback)."""
        # Given: Mock client raises ValueError
        mock_tmdb_client.get_media_details.side_effect = ValueError("Invalid data")
        fallback_data = {"id": 1429, "title": "Fallback"}

        # When/Then: Raises DomainError (fallback not used)
        with pytest.raises(DomainError) as exc_info:
            await fetcher.fetch_details(1429, "tv", fallback_data=fallback_data)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "Data processing error" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_fetch_details_unexpected_error_with_fallback(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test unexpected error with fallback returns fallback data."""
        # Given: Unexpected error + fallback data
        mock_tmdb_client.get_media_details.side_effect = RuntimeError(
            "Unexpected error"
        )
        fallback_data = {"id": 1429, "title": "Fallback"}

        # When: Fetch details with fallback
        result = await fetcher.fetch_details(1429, "tv", fallback_data=fallback_data)

        # Then: Returns fallback data
        assert result == fallback_data

    @pytest.mark.asyncio
    async def test_fetch_details_unexpected_error_without_fallback(
        self, fetcher: TMDBFetcher, mock_tmdb_client: Mock
    ) -> None:
        """Test unexpected error without fallback raises InfrastructureError."""
        # Given: Unexpected error + no fallback
        mock_tmdb_client.get_media_details.side_effect = RuntimeError(
            "Unexpected error"
        )

        # When/Then: Raises InfrastructureError
        with pytest.raises(InfrastructureError) as exc_info:
            await fetcher.fetch_details(1429, "tv")

        assert exc_info.value.code == ErrorCode.TMDB_API_REQUEST_FAILED
        assert "Unexpected error" in exc_info.value.message
