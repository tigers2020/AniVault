"""Concurrent TMDB operations for high-performance batch processing.

This module provides utilities for executing multiple TMDB API calls concurrently
using asyncio primitives to maximize throughput and minimize latency.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .async_tmdb_client import AsyncTMDBClient
from .async_tmdb_client_pool import async_tmdb_client_context

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result of a batch operation."""

    successful: list[Any]
    failed: list[tuple[Any, Exception]]
    total_time: float
    success_rate: float


class ConcurrentTMDBOperations:
    """High-level concurrent operations for TMDB API calls."""

    def __init__(self, max_concurrent: int = 10):
        """Initialize concurrent operations manager.

        Args:
            max_concurrent: Maximum number of concurrent operations
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def search_multiple_queries(
        self, queries: list[str], year: int | None = None, include_details: bool = False
    ) -> BatchResult:
        """Search multiple queries concurrently.

        Args:
            queries: List of search queries
            year: Optional year filter for all queries
            include_details: Whether to fetch detailed information for each result

        Returns:
            BatchResult with successful and failed operations
        """
        start_time = datetime.now()

        async with async_tmdb_client_context() as client:
            tasks = [
                self._search_with_semaphore(client, query, year, include_details)
                for query in queries
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = []
            failed = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed.append((queries[i], result))
                    logger.warning(f"Search failed for query '{queries[i]}': {result}")
                else:
                    successful.append(result)

            total_time = (datetime.now() - start_time).total_seconds()
            success_rate = len(successful) / len(queries) if queries else 0.0

            return BatchResult(
                successful=successful,
                failed=failed,
                total_time=total_time,
                success_rate=success_rate,
            )

    async def get_multiple_series_details(
        self, series_ids: list[int], include_credits: bool = True
    ) -> BatchResult:
        """Get details for multiple TV series concurrently.

        Args:
            series_ids: List of TV series IDs
            include_credits: Whether to include credits information

        Returns:
            BatchResult with successful and failed operations
        """
        start_time = datetime.now()

        async with async_tmdb_client_context() as client:
            tasks = [
                self._get_series_details_with_semaphore(client, series_id, include_credits)
                for series_id in series_ids
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = []
            failed = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed.append((series_ids[i], result))
                    logger.warning(f"Failed to get details for series {series_ids[i]}: {result}")
                else:
                    successful.append(result)

            total_time = (datetime.now() - start_time).total_seconds()
            success_rate = len(successful) / len(series_ids) if series_ids else 0.0

            return BatchResult(
                successful=successful,
                failed=failed,
                total_time=total_time,
                success_rate=success_rate,
            )

    async def get_multiple_movie_details(
        self, movie_ids: list[int], include_credits: bool = True
    ) -> BatchResult:
        """Get details for multiple movies concurrently.

        Args:
            movie_ids: List of movie IDs
            include_credits: Whether to include credits information

        Returns:
            BatchResult with successful and failed operations
        """
        start_time = datetime.now()

        async with async_tmdb_client_context() as client:
            tasks = [
                self._get_movie_details_with_semaphore(client, movie_id, include_credits)
                for movie_id in movie_ids
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful = []
            failed = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed.append((movie_ids[i], result))
                    logger.warning(f"Failed to get details for movie {movie_ids[i]}: {result}")
                else:
                    successful.append(result)

            total_time = (datetime.now() - start_time).total_seconds()
            success_rate = len(successful) / len(movie_ids) if movie_ids else 0.0

            return BatchResult(
                successful=successful,
                failed=failed,
                total_time=total_time,
                success_rate=success_rate,
            )

    async def search_and_get_details(
        self, queries: list[str], year: int | None = None, include_credits: bool = True
    ) -> BatchResult:
        """Search for multiple queries and get detailed information for each result.

        Args:
            queries: List of search queries
            year: Optional year filter for all queries
            include_credits: Whether to include credits information

        Returns:
            BatchResult with successful and failed operations
        """
        start_time = datetime.now()

        async with async_tmdb_client_context() as client:
            # First, search for all queries
            search_tasks = [
                self._search_with_semaphore(client, query, year, False) for query in queries
            ]

            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            # Then, get details for successful searches
            detail_tasks = []
            successful_searches = []

            for i, result in enumerate(search_results):
                if isinstance(result, Exception):
                    continue

                if result and result.get("results"):
                    # Get the first (best) result
                    best_result = result["results"][0]
                    media_id = best_result.get("id")
                    media_type = best_result.get("media_type", "tv")

                    if media_id:
                        if media_type == "tv":
                            detail_tasks.append(
                                self._get_series_details_with_semaphore(
                                    client, media_id, include_credits
                                )
                            )
                        elif media_type == "movie":
                            detail_tasks.append(
                                self._get_movie_details_with_semaphore(
                                    client, media_id, include_credits
                                )
                            )

                        successful_searches.append((queries[i], best_result))

            # Execute detail retrieval concurrently
            detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)

            successful = []
            failed = []

            for i, result in enumerate(detail_results):
                query, search_result = successful_searches[i]

                if isinstance(result, Exception):
                    failed.append((query, result))
                    logger.warning(f"Failed to get details for query '{query}': {result}")
                else:
                    successful.append(
                        {"query": query, "search_result": search_result, "details": result}
                    )

            total_time = (datetime.now() - start_time).total_seconds()
            success_rate = len(successful) / len(queries) if queries else 0.0

            return BatchResult(
                successful=successful,
                failed=failed,
                total_time=total_time,
                success_rate=success_rate,
            )

    async def _search_with_semaphore(
        self,
        client: AsyncTMDBClient,
        query: str,
        year: int | None = None,
        include_details: bool = False,
    ) -> dict[str, Any]:
        """Search with semaphore for concurrency control."""
        async with self._semaphore:
            result = await client.search_tv_series(query, year)

            if include_details and result.get("results"):
                # Get details for the first result
                best_result = result["results"][0]
                media_id = best_result.get("id")
                media_type = best_result.get("media_type", "tv")

                if media_id:
                    if media_type == "tv":
                        details = await client.get_tv_series_details(media_id)
                    elif media_type == "movie":
                        details = await client.get_movie_details(media_id)
                    else:
                        details = None

                    if details:
                        result["details"] = details

            return result

    async def _get_series_details_with_semaphore(
        self, client: AsyncTMDBClient, series_id: int, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get series details with semaphore for concurrency control."""
        async with self._semaphore:
            return await client.get_tv_series_details(series_id, include_credits)

    async def _get_movie_details_with_semaphore(
        self, client: AsyncTMDBClient, movie_id: int, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get movie details with semaphore for concurrency control."""
        async with self._semaphore:
            return await client.get_movie_details(movie_id, include_credits)


class StreamingTMDBOperations:
    """Streaming operations for processing results as they become available."""

    def __init__(self, max_concurrent: int = 10):
        """Initialize streaming operations manager.

        Args:
            max_concurrent: Maximum number of concurrent operations
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def search_with_streaming(
        self, queries: list[str], year: int | None = None, callback: callable | None = None
    ) -> list[dict[str, Any]]:
        """Search multiple queries with streaming results.

        Args:
            queries: List of search queries
            year: Optional year filter for all queries
            callback: Optional callback function for each result

        Returns:
            List of all results
        """
        results = []

        async with async_tmdb_client_context() as client:
            tasks = [self._search_with_semaphore(client, query, year) for query in queries]

            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    results.append(result)

                    if callback:
                        callback(result)

                except Exception as e:
                    logger.warning(f"Search failed: {e}")
                    if callback:
                        callback(None, e)

        return results

    async def get_details_with_streaming(
        self,
        media_items: list[dict[str, Any]],
        include_credits: bool = True,
        callback: callable | None = None,
    ) -> list[dict[str, Any]]:
        """Get details for multiple media items with streaming results.

        Args:
            media_items: List of media items with 'id' and 'media_type'
            include_credits: Whether to include credits information
            callback: Optional callback function for each result

        Returns:
            List of all results
        """
        results = []

        async with async_tmdb_client_context() as client:
            tasks = [
                self._get_media_details_with_semaphore(client, item, include_credits)
                for item in media_items
            ]

            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    results.append(result)

                    if callback:
                        callback(result)

                except Exception as e:
                    logger.warning(f"Details retrieval failed: {e}")
                    if callback:
                        callback(None, e)

        return results

    async def _search_with_semaphore(
        self, client: AsyncTMDBClient, query: str, year: int | None = None
    ) -> dict[str, Any]:
        """Search with semaphore for concurrency control."""
        async with self._semaphore:
            return await client.search_tv_series(query, year)

    async def _get_media_details_with_semaphore(
        self, client: AsyncTMDBClient, media_item: dict[str, Any], include_credits: bool = True
    ) -> dict[str, Any]:
        """Get media details with semaphore for concurrency control."""
        async with self._semaphore:
            media_id = media_item.get("id")
            media_type = media_item.get("media_type", "tv")

            if media_type == "tv":
                return await client.get_tv_series_details(media_id, include_credits)
            elif media_type == "movie":
                return await client.get_movie_details(media_id, include_credits)
            else:
                raise ValueError(f"Unsupported media type: {media_type}")


# Factory functions
def create_concurrent_operations(max_concurrent: int = 10) -> ConcurrentTMDBOperations:
    """Create a concurrent operations manager.

    Args:
        max_concurrent: Maximum number of concurrent operations

    Returns:
        ConcurrentTMDBOperations instance
    """
    return ConcurrentTMDBOperations(max_concurrent)


def create_streaming_operations(max_concurrent: int = 10) -> StreamingTMDBOperations:
    """Create a streaming operations manager.

    Args:
        max_concurrent: Maximum number of concurrent operations

    Returns:
        StreamingTMDBOperations instance
    """
    return StreamingTMDBOperations(max_concurrent)


# Global instances
_concurrent_ops: ConcurrentTMDBOperations | None = None
_streaming_ops: StreamingTMDBOperations | None = None


def get_concurrent_operations() -> ConcurrentTMDBOperations:
    """Get the global concurrent operations manager.

    Returns:
        Global ConcurrentTMDBOperations instance
    """
    global _concurrent_ops
    if _concurrent_ops is None:
        _concurrent_ops = create_concurrent_operations()
    return _concurrent_ops


def get_streaming_operations() -> StreamingTMDBOperations:
    """Get the global streaming operations manager.

    Returns:
        Global StreamingTMDBOperations instance
    """
    global _streaming_ops
    if _streaming_ops is None:
        _streaming_ops = create_streaming_operations()
    return _streaming_ops
