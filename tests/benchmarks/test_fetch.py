"""Benchmark tests for TMDB API fetching (mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from anivault.services.tmdb_client import TMDBClient


@pytest.fixture
def tmdb_client():
    """Create TMDB client with mocked HTTP."""
    # Mock the HTTP client to avoid actual API calls
    client = TMDBClient(api_key="test_key_12345")

    # Mock the http_client
    client.http_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json = AsyncMock(
        return_value={
            "results": [
                {
                    "id": 1429,
                    "name": "Attack on Titan",
                    "original_name": "進撃の巨人",
                    "first_air_date": "2013-04-07",
                    "vote_average": 8.5,
                }
            ]
        }
    )
    client.http_client.get = AsyncMock(return_value=mock_response)

    return client


def test_benchmark_search_tv_mocked(benchmark, tmdb_client):
    """Benchmark TV search with mocked API."""
    import asyncio

    async def search():
        return await tmdb_client.search_tv("Attack on Titan")

    result = benchmark(lambda: asyncio.run(search()))
    assert result is not None


def test_benchmark_get_tv_details_mocked(benchmark, tmdb_client):
    """Benchmark getting TV details with mocked API."""
    import asyncio

    async def get_details():
        return await tmdb_client.get_tv_details(1429)

    # Update mock for details endpoint
    mock_response = MagicMock()
    mock_response.json = AsyncMock(
        return_value={
            "id": 1429,
            "name": "Attack on Titan",
            "seasons": [],
        }
    )
    tmdb_client.http_client.get = AsyncMock(return_value=mock_response)

    result = benchmark(lambda: asyncio.run(get_details()))
    assert result is not None


def test_benchmark_search_movie_mocked(benchmark, tmdb_client):
    """Benchmark movie search with mocked API."""
    import asyncio

    async def search():
        return await tmdb_client.search_movie("Your Name")

    # Update mock for movie search
    mock_response = MagicMock()
    mock_response.json = AsyncMock(
        return_value={
            "results": [
                {
                    "id": 372058,
                    "title": "Your Name",
                    "original_title": "君の名は。",
                    "release_date": "2016-08-26",
                }
            ]
        }
    )
    tmdb_client.http_client.get = AsyncMock(return_value=mock_response)

    result = benchmark(lambda: asyncio.run(search()))
    assert result is not None
