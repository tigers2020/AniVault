"""TMDB search service with cache integration.

This module provides the TMDBSearchService class that encapsulates TMDB API
search operations with integrated caching support. It handles cache key generation,
cache hit/miss logic, and result validation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from anivault.core.matching.cache_models import CachedSearchData
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

            # Return cached results (already validated by Pydantic!)
            return cached_data.results

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

            # Store in cache with Pydantic model
            cached_data = CachedSearchData(
                results=results,
                language=self.cache.language,
            )
            self.cache.set(
                key=title,
                data=cached_data,
                cache_type=MatchingCacheConfig.CACHE_TYPE_SEARCH,
                ttl_seconds=MatchingCacheConfig.SEARCH_CACHE_TTL_SECONDS,
            )

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
