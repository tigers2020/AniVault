"""TMDB search service with cache integration.

This module provides the TMDBSearchService class that encapsulates TMDB API
search operations with integrated caching support. It handles cache key generation,
cache hit/miss logic, and result validation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from anivault.core.matching.models import NormalizedQuery
from anivault.core.statistics import StatisticsCollector
from anivault.services.tmdb_models import TMDBSearchResult
from anivault.shared.constants import MatchingCacheConfig

if TYPE_CHECKING:
    from anivault.core.matching.services.cache_adapter import CacheAdapterProtocol
    from anivault.services.tmdb_client import TMDBClient

logger = logging.getLogger(__name__)


class TMDBSearchService:
    """TMDB search service with cache integration.

    This service encapsulates TMDB API search operations, providing:
    1. Cache-aware searching (check cache before API call)
    2. Language-sensitive cache key generation
    3. Pydantic-based result validation
    4. Automatic cache storage with TTL
    5. Graceful error handling

    Attributes:
        tmdb_client: TMDB API client for search operations
        cache: Cache adapter for storing/retrieving search results
        statistics: Statistics collector for performance tracking

    Example:
        >>> from anivault.services.tmdb_client import TMDBClient
        >>> from anivault.core.matching.services import SQLiteCacheAdapter
        >>>
        >>> client = TMDBClient()
        >>> cache = SQLiteCacheAdapter(db, language="ko-KR")
        >>> stats = StatisticsCollector()
        >>>
        >>> service = TMDBSearchService(client, cache, stats)
        >>> query = NormalizedQuery(title="attack on titan", year=2013)
        >>> results = await service.search(query)
    """

    def __init__(
        self,
        tmdb_client: TMDBClient,
        cache: CacheAdapterProtocol,
        statistics: StatisticsCollector,
    ) -> None:
        """Initialize TMDB search service.

        Args:
            tmdb_client: TMDB API client for search operations
            cache: Cache adapter for storing/retrieving results
            statistics: Statistics collector for performance tracking
        """
        self.tmdb_client = tmdb_client
        self.cache = cache
        self.statistics = statistics

    async def search(
        self,
        normalized_query: NormalizedQuery,
    ) -> list[TMDBSearchResult]:
        """Search TMDB with cache support.

        This method orchestrates the cache-aware search workflow:
        1. Check cache for existing results
        2. On cache hit: validate and return cached results
        3. On cache miss: call TMDB API, validate, cache, and return results

        Args:
            normalized_query: Normalized query with title and optional year

        Returns:
            List of TMDBSearchResult objects (empty list on error)

        Example:
            >>> query = NormalizedQuery(title="attack on titan", year=2013)
            >>> results = await service.search(query)
            >>> for result in results:
            ...     print(f"{result.title} ({result.year})")
        """
        title = normalized_query.title

        # Check cache first
        cached_data = self.cache.get(title, MatchingCacheConfig.CACHE_TYPE_SEARCH)
        if cached_data is not None:
            logger.debug("Cache hit for search query: %s", title)
            self.statistics.record_cache_hit("search")

            # Validate and return cached results
            cached_results = self._validate_cached_results(cached_data, title)
            if cached_results is not None:
                return cached_results

            # Invalid cache: fall through to API call
            logger.warning("Invalid cached data, falling back to API call")

        # Cache miss - search TMDB
        logger.debug(
            "Cache miss for search query: %s (language: %s)",
            title,
            self.cache.language,
        )
        self.statistics.record_cache_miss("search")

        try:
            # Call TMDB API
            self.statistics.record_api_call("tmdb_search", success=True)
            search_response = await self.tmdb_client.search_media(title)

            # Extract results
            results = search_response.results

            # Store in cache
            self._store_results_in_cache(title, results)

            logger.debug("Found %d results for query: %s", len(results), title)
            return results

        except Exception:
            # Graceful degradation: log error and return empty list
            logger.exception("TMDB search failed for query '%s'", title)
            self.statistics.record_api_call(
                "tmdb_search",
                success=False,
                error="Exception",
            )
            return []

    def _validate_cached_results(
        self,
        cached_data: dict[str, Any],
        title: str,
    ) -> list[TMDBSearchResult] | None:
        """Validate and convert cached data to TMDBSearchResult objects.

        Args:
            cached_data: Raw cached data from cache adapter
            title: Original query title (for cache invalidation on error)

        Returns:
            List of TMDBSearchResult objects, or None if validation fails
        """
        # Check structure
        if "results" not in cached_data:
            logger.warning("Cached data missing 'results' key, invalidating")
            self.cache.delete(title, MatchingCacheConfig.CACHE_TYPE_SEARCH)
            return None

        cached_results = cached_data["results"]

        # Type validation
        if not isinstance(cached_results, list):
            logger.warning(
                "Invalid cached results type: %s, expected list, invalidating",
                type(cached_results),
            )
            self.cache.delete(title, MatchingCacheConfig.CACHE_TYPE_SEARCH)
            return None

        # Convert to TMDBSearchResult objects
        try:
            search_results = [
                (
                    TMDBSearchResult(**item)
                    if isinstance(item, dict)
                    else item
                )
                for item in cached_results
            ]
            return search_results

        except Exception:
            logger.exception(
                "Failed to convert cached results to TMDBSearchResult, invalidating",
            )
            self.cache.delete(title, MatchingCacheConfig.CACHE_TYPE_SEARCH)
            return None

    def _store_results_in_cache(
        self,
        title: str,
        results: list[TMDBSearchResult],
    ) -> None:
        """Store TMDB search results in cache with TTL.

        Args:
            title: Query title (used as cache key)
            results: List of TMDBSearchResult objects to cache
        """
        # Convert to dict for caching
        results_dicts = [result.model_dump() for result in results]
        cache_data = {"results": results_dicts}

        # Store with configured TTL
        self.cache.set(
            key=title,
            data=cache_data,
            cache_type=MatchingCacheConfig.CACHE_TYPE_SEARCH,
            ttl_seconds=MatchingCacheConfig.SEARCH_CACHE_TTL_SECONDS,
        )

