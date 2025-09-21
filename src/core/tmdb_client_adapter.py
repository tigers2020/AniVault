"""TMDB Client Adapter for backward compatibility and async integration.

This module provides an adapter that maintains compatibility with the existing
synchronous TMDBClient while enabling async operations when needed.
"""

import asyncio
import logging
from typing import Any

from .async_session_manager import get_session_manager, run_async
from .async_tmdb_client import AsyncTMDBClient, create_async_tmdb_client
from .tmdb_client import SearchResult, TMDBClient, TMDBConfig

logger = logging.getLogger(__name__)


class TMDBClientAdapter:
    """Adapter that provides both sync and async interfaces for TMDB operations.

    This class maintains backward compatibility with existing synchronous code
    while providing async capabilities for new implementations.
    """

    def __init__(self, config: TMDBConfig, use_async: bool = False):
        """Initialize the adapter.

        Args:
            config: TMDB configuration
            use_async: Whether to use async client by default
        """
        self.config = config
        self.use_async = use_async
        self._sync_client: TMDBClient | None = None
        self._async_client: AsyncTMDBClient | None = None
        self._session_manager = get_session_manager()

    @property
    def sync_client(self) -> TMDBClient:
        """Get or create the synchronous TMDB client."""
        if self._sync_client is None:
            self._sync_client = TMDBClient(self.config)
        return self._sync_client

    async def async_client(self) -> AsyncTMDBClient:
        """Get or create the asynchronous TMDB client."""
        if self._async_client is None:
            self._async_client = await create_async_tmdb_client(self.config)
        return self._async_client

    # Synchronous methods (delegate to sync client)
    def search_tv_series(
        self, query: str, year: int | None = None, page: int = 1
    ) -> dict[str, Any]:
        """Search for TV series (sync)."""
        return self.sync_client.search_tv_series(query, year, page)

    def search_multi(self, query: str, page: int = 1) -> dict[str, Any]:
        """Search for both TV series and movies (sync)."""
        return self.sync_client.search_multi(query, page)

    def get_tv_series_details(self, series_id: int, include_credits: bool = True) -> dict[str, Any]:
        """Get detailed information for a TV series (sync)."""
        return self.sync_client.get_tv_series_details(series_id, include_credits)

    def get_movie_details(self, movie_id: int, include_credits: bool = True) -> dict[str, Any]:
        """Get detailed information for a movie (sync)."""
        return self.sync_client.get_movie_details(movie_id, include_credits)

    def get_media_details(
        self, media_id: int, media_type: str, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get detailed information for any media type (sync)."""
        return self.sync_client.get_media_details(media_id, media_type, include_credits)

    def search_comprehensive(
        self, query: str, year: int | None = None, strategies: list | None = None
    ) -> list[SearchResult]:
        """Perform comprehensive search using multiple strategies (sync)."""
        return self.sync_client.search_comprehensive(query, year, strategies)

    # Asynchronous methods
    async def search_tv_series_async(
        self, query: str, year: int | None = None, page: int = 1
    ) -> dict[str, Any]:
        """Search for TV series (async)."""
        client = await self.async_client()
        return await client.search_tv_series(query, year, page)

    async def search_multi_async(self, query: str, page: int = 1) -> dict[str, Any]:
        """Search for both TV series and movies (async)."""
        client = await self.async_client()
        return await client.search_multi(query, page)

    async def get_tv_series_details_async(
        self, series_id: int, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get detailed information for a TV series (async)."""
        client = await self.async_client()
        return await client.get_tv_series_details(series_id, include_credits)

    async def get_movie_details_async(
        self, movie_id: int, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get detailed information for a movie (async)."""
        client = await self.async_client()
        return await client.get_movie_details(movie_id, include_credits)

    async def get_media_details_async(
        self, media_id: int, media_type: str, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get detailed information for any media type (async)."""
        client = await self.async_client()
        return await client.get_media_details(media_id, media_type, include_credits)

    async def search_comprehensive_async(
        self, query: str, year: int | None = None, strategies: list | None = None
    ) -> list[SearchResult]:
        """Perform comprehensive search using multiple strategies (async)."""
        client = await self.async_client()
        return await client.search_comprehensive(query, year, strategies)

    # Concurrent operations
    async def search_multiple_queries_async(
        self, queries: list[str], year: int | None = None
    ) -> list[dict[str, Any]]:
        """Search multiple queries concurrently.

        Args:
            queries: List of search queries
            year: Optional year filter for all queries

        Returns:
            List of search results for each query
        """
        tasks = [self.search_tv_series_async(query, year) for query in queries]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def get_multiple_series_details_async(
        self, series_ids: list[int], include_credits: bool = True
    ) -> list[dict[str, Any]]:
        """Get details for multiple TV series concurrently.

        Args:
            series_ids: List of TV series IDs
            include_credits: Whether to include credits information

        Returns:
            List of series details for each ID
        """
        tasks = [
            self.get_tv_series_details_async(series_id, include_credits) for series_id in series_ids
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def get_multiple_movie_details_async(
        self, movie_ids: list[int], include_credits: bool = True
    ) -> list[dict[str, Any]]:
        """Get details for multiple movies concurrently.

        Args:
            movie_ids: List of movie IDs
            include_credits: Whether to include credits information

        Returns:
            List of movie details for each ID
        """
        tasks = [self.get_movie_details_async(movie_id, include_credits) for movie_id in movie_ids]
        return await asyncio.gather(*tasks, return_exceptions=True)

    # Hybrid methods (sync interface that uses async internally)
    def search_tv_series_hybrid(
        self, query: str, year: int | None = None, page: int = 1
    ) -> dict[str, Any]:
        """Search for TV series using async internally but sync interface."""
        return run_async(self.search_tv_series_async(query, year, page))

    def search_multi_hybrid(self, query: str, page: int = 1) -> dict[str, Any]:
        """Search for both TV series and movies using async internally but sync interface."""
        return run_async(self.search_multi_async(query, page))

    def get_tv_series_details_hybrid(
        self, series_id: int, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get detailed information for a TV series using async internally but sync interface."""
        return run_async(self.get_tv_series_details_async(series_id, include_credits))

    def get_movie_details_hybrid(
        self, movie_id: int, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get detailed information for a movie using async internally but sync interface."""
        return run_async(self.get_movie_details_async(movie_id, include_credits))

    def get_media_details_hybrid(
        self, media_id: int, media_type: str, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get detailed information for any media type using async internally but sync interface."""
        return run_async(self.get_media_details_async(media_id, media_type, include_credits))

    def search_comprehensive_hybrid(
        self, query: str, year: int | None = None, strategies: list | None = None
    ) -> list[SearchResult]:
        """Perform comprehensive search using async internally but sync interface."""
        return run_async(self.search_comprehensive_async(query, year, strategies))

    # Cleanup methods
    async def close_async(self) -> None:
        """Close async client and clean up resources."""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None

    def close_sync(self) -> None:
        """Close sync client and clean up resources."""
        if self._sync_client:
            # Sync client doesn't have explicit close method, just clear reference
            self._sync_client = None

    def close(self) -> None:
        """Close both clients and clean up resources."""
        self.close_sync()
        # Close async client synchronously
        if self._async_client:
            run_async(self._async_client.close())
            self._async_client = None


# Factory functions
def create_tmdb_adapter(
    config: TMDBConfig | None = None, use_async: bool = False
) -> TMDBClientAdapter:
    """Create a TMDB client adapter.

    Args:
        config: Optional TMDB configuration. If None, creates default config.
        use_async: Whether to prefer async operations by default.

    Returns:
        Configured TMDBClientAdapter instance.
    """
    if config is None:
        from .config_manager import get_config_manager

        config_manager = get_config_manager()
        config = TMDBConfig(
            api_key=config_manager.get("tmdb_api_key"),
            language=config_manager.get("tmdb_language", "ko-KR"),
            fallback_language=config_manager.get("tmdb_fallback_language", "en-US"),
            timeout=config_manager.get("tmdb_timeout", 30),
            max_retries=config_manager.get("tmdb_max_retries", 3),
            cache_only_mode=config_manager.get("tmdb_cache_only_mode", False),
        )

    return TMDBClientAdapter(config, use_async)


# Global adapter instance for backward compatibility
_global_adapter: TMDBClientAdapter | None = None


def get_global_tmdb_adapter() -> TMDBClientAdapter:
    """Get the global TMDB client adapter.

    Returns:
        Global TMDBClientAdapter instance.
    """
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = create_tmdb_adapter()
    return _global_adapter


def set_global_tmdb_adapter(adapter: TMDBClientAdapter) -> None:
    """Set the global TMDB client adapter.

    Args:
        adapter: The adapter to set as global.
    """
    global _global_adapter
    _global_adapter = adapter
