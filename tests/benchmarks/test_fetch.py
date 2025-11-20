"""Benchmark tests for TMDB API fetching (mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from anivault.services.tmdb_client import TMDBClient
from anivault.services.tmdb_models import TMDBSearchResponse, TMDBSearchResult


@pytest.fixture
def tmdb_client():
    """Create fully mocked TMDB client."""
    # Use Mock(spec=TMDBClient) to avoid real initialization
    client = Mock(spec=TMDBClient)

    # Mock search_media (returns TMDBSearchResponse with results)
    mock_tv_result = TMDBSearchResult(
        id=1429,
        media_type="tv",
        name="Attack on Titan",
        original_name="進撃の巨人",
        first_air_date="2013-04-07",
        vote_average=8.5,
    )
    client.search_media = AsyncMock(
        return_value=TMDBSearchResponse(results=[mock_tv_result])
    )

    return client


def test_benchmark_search_tv_mocked(benchmark, tmdb_client):  # type: ignore[no-untyped-def]
    """Benchmark TV search with mocked API."""
    import asyncio

    async def search():  # type: ignore[no-untyped-def]
        return await tmdb_client.search_media("Attack on Titan")

    result = benchmark(lambda: asyncio.run(search()))
    assert result is not None
    assert len(result.results) > 0
    assert result.results[0].id == 1429


def test_benchmark_get_tv_details_mocked(benchmark, tmdb_client):  # type: ignore[no-untyped-def]
    """Benchmark getting TV details with mocked API."""
    import asyncio

    from anivault.services.tmdb_models import TMDBMediaDetails

    async def get_details():  # type: ignore[no-untyped-def]
        return await tmdb_client.get_media_details(1429, "tv")

    # Mock get_media_details method
    mock_details = TMDBMediaDetails(
        id=1429,
        media_type="tv",
        name="Attack on Titan",
        number_of_seasons=4,
        number_of_episodes=87,
    )
    tmdb_client.get_media_details = AsyncMock(return_value=mock_details)

    result = benchmark(lambda: asyncio.run(get_details()))
    assert result is not None
    assert result.id == 1429


def test_benchmark_search_movie_mocked(benchmark, tmdb_client):  # type: ignore[no-untyped-def]
    """Benchmark movie search with mocked API."""
    import asyncio

    async def search():  # type: ignore[no-untyped-def]
        return await tmdb_client.search_media("Your Name")

    # Mock movie search result
    mock_movie_result = TMDBSearchResult(
        id=372058,
        media_type="movie",
        title="Your Name",
        original_title="君の名は。",
        release_date="2016-08-26",
    )
    tmdb_client.search_media = AsyncMock(
        return_value=TMDBSearchResponse(results=[mock_movie_result])
    )

    result = benchmark(lambda: asyncio.run(search()))
    assert result is not None
    assert len(result.results) > 0
    assert result.results[0].id == 372058
