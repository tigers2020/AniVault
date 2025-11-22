"""TMDB search service with cache integration.

This module provides the TMDBSearchService class that encapsulates TMDB API
search operations with integrated caching support. It handles cache key generation,
cache hit/miss logic, and result validation.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from anivault.core.matching.cache_models import CachedSearchData
from anivault.core.matching.models import NormalizedQuery
from anivault.core.statistics import StatisticsCollector
from anivault.services.tmdb import TMDBSearchResult
from anivault.shared.constants import MatchingCacheConfig, NormalizationConfig

if TYPE_CHECKING:
    from anivault.core.matching.services.cache_adapter import CacheAdapterProtocol
    from anivault.services.tmdb import TMDBClient

logger = logging.getLogger(__name__)

# Compile episode/season patterns once at module level for series title extraction
_EPISODE_SEASON_PATTERNS = [
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in [
        *NormalizationConfig.EPISODE_PATTERNS,
        *NormalizationConfig.SEASON_PATTERNS,
    ]
]


def _extract_series_title(title: str) -> str:
    """Extract series title from normalized query title for cache key generation.

    Removes episode and season information to ensure all episodes of the same
    series use the same cache key, reducing redundant API calls.

    Args:
        title: Normalized title that may contain episode/season information

    Returns:
        Series title with episode/season information removed, lowercased and normalized

    Example:
        >>> _extract_series_title("Attack on Titan S01E01")
        'attack on titan'
        >>> _extract_series_title("Attack on Titan S01E02")
        'attack on titan'
        >>> _extract_series_title("My Series - Episode 5")
        'my series'
    """
    if not title:
        return ""

    # Remove episode and season patterns
    cleaned = title
    for pattern in _EPISODE_SEASON_PATTERNS:
        cleaned = pattern.sub("", cleaned)

    # Clean up extra whitespace and separators
    cleaned = re.sub(r"[-\s]+", " ", cleaned)
    cleaned = cleaned.strip().lower()

    return cleaned


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
        >>> from anivault.services.tmdb import TMDBClient
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

        # Generate cache key from series title (removes episode/season info)
        # This ensures all episodes of the same series use the same cache key
        cache_key = _extract_series_title(title)

        # Check cache first using series-based key
        cached_data = self.cache.get(cache_key, MatchingCacheConfig.CACHE_TYPE_SEARCH)
        if cached_data is not None:
            logger.debug(
                "Cache hit for search query: %s (cache key: %s)",
                title,
                cache_key,
            )
            self.statistics.record_cache_hit("search")

            # Return cached results (already validated by Pydantic!)
            return cached_data.results

        # Cache miss - search TMDB
        logger.debug(
            "Cache miss for search query: %s (cache key: %s, language: %s)",
            title,
            cache_key,
            self.cache.language,
        )
        self.statistics.record_cache_miss("search")

        try:
            # Call TMDB API
            self.statistics.record_api_call("tmdb_search", success=True)
            search_response = await self.tmdb_client.search_media(title)

            # Extract results
            results = search_response.results

            # Store in cache with series-based key for reuse across episodes
            cached_data = CachedSearchData(
                results=results,
                language=self.cache.language,
            )
            self.cache.set(
                key=cache_key,  # Use series-based key, not original title
                data=cached_data,
                cache_type=MatchingCacheConfig.CACHE_TYPE_SEARCH,
                ttl_seconds=MatchingCacheConfig.SEARCH_CACHE_TTL,
            )

            logger.debug(
                "Found %d results for query: %s (cached with key: %s)",
                len(results),
                title,
                cache_key,
            )
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
