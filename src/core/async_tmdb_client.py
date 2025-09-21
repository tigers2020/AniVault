"""Async TMDB API Client for retrieving anime metadata.

This module provides an asynchronous client for interacting with The Movie Database (TMDB) API
using aiohttp for non-blocking HTTP operations. It maintains compatibility with the existing
TMDBClient interface while providing better performance for concurrent operations.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urljoin

import aiohttp
from aiolimiter import AsyncLimiter

from .async_session_manager import get_http_session
from .cache_key_generator import get_cache_key_generator
from .config_manager import get_config_manager
from .optimized_quality_calculator import OptimizedQualityCalculator, QualityScoreConfig

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """Search strategy enumeration."""

    MULTI = "multi"
    TV_ONLY = "tv_only"
    MOVIE_ONLY = "movie_only"


class SearchStrategyType(Enum):
    """Search strategy type enumeration for 3-strategy approach."""

    EXACT_TITLE_WITH_YEAR = "exact_title_with_year"
    EXACT_TITLE_ONLY = "exact_title_only"
    CLEANED_TITLE = "cleaned_title"


class FallbackStrategy(Enum):
    """Fallback strategy enumeration (deprecated - use SearchStrategyType)."""

    NORMALIZED = "normalized"
    WORD_REDUCTION = "word_reduction"
    LANGUAGE_FALLBACK = "language_fallback"


@dataclass
class SearchResult:
    """Search result with quality scoring."""

    id: int
    media_type: str  # 'tv' or 'movie'
    title: str
    original_title: str
    year: int | None
    overview: str
    poster_path: str | None
    popularity: float
    vote_average: float
    vote_count: int
    quality_score: float
    strategy_used: SearchStrategy
    fallback_round: int = 0


@dataclass
class TMDBConfig:
    """Configuration for TMDB API client."""

    api_key: str
    language: str = "ko-KR"
    fallback_language: str = "en-US"
    base_url: str = "https://api.themoviedb.org/3"
    image_base_url: str = "https://image.tmdb.org/t/p"
    timeout: int = 30
    max_retries: int = 3
    retry_delay_base: float = 1.0
    retry_delay_max: float = 60.0
    cache_only_mode: bool = False

    # Multi search configuration
    high_confidence_threshold: float = 0.7
    medium_confidence_threshold: float = 0.3
    similarity_weight: float = 0.6
    year_weight: float = 0.2
    popularity_weight: float = 0.2

    # Rate limiting - TMDB API limits
    requests_per_second: float = 4.0  # 40 requests per 10 seconds = 4 req/s
    burst_limit: int = 40  # TMDB allows 40 requests per 10-second window
    rate_limit_window: int = 10  # 10-second window for rate limiting

    # Cache configuration
    cache_ttl: int = 3600  # 1 hour
    cache_max_size: int = 1000

    # Quality scoring
    quality_score_config: QualityScoreConfig | None = None

    def __post_init__(self) -> None:
        """Initialize default quality score config if not provided."""
        if self.quality_score_config is None:
            self.quality_score_config = QualityScoreConfig()


class AsyncTMDBClient:
    """Asynchronous TMDB API client using aiohttp."""

    def __init__(self, config: TMDBConfig) -> None:
        """Initialize the async TMDB client.

        Args:
            config: TMDB configuration object.
        """
        self.config = config
        self._cache: dict[str, Any] = {}

        # Advanced rate limiting with token bucket algorithm
        self._rate_limiter = AsyncLimiter(config.burst_limit, config.rate_limit_window)

        # Concurrency limiting (separate from rate limiting)
        self._concurrency_limiter = asyncio.Semaphore(10)  # Max 10 concurrent requests

        self._last_request_time = 0.0
        self._request_count = 0
        self._session: aiohttp.ClientSession | None = None
        self._quality_calculator = OptimizedQualityCalculator(config.quality_score_config)
        self._cache_key_generator = get_cache_key_generator()

        # Initialize session lazily when first needed
        self._initialization_task: asyncio.Task[None] | None = None

    async def _initialize_session(self) -> None:
        """Initialize the aiohttp session."""
        try:
            self._session = await get_http_session()
            logger.info("AsyncTMDBClient session initialized")
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            raise

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """Make an async HTTP request to the TMDB API with advanced rate limiting and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            retry_count: Current retry attempt

        Returns:
            JSON response data

        Raises:
            aiohttp.ClientError: For HTTP errors
            asyncio.TimeoutError: For timeout errors
            Exception: For other errors
        """
        if self.config.cache_only_mode:
            raise RuntimeError("Client is in cache-only mode")

        if not self._session:
            if self._initialization_task is None:
                self._initialization_task = asyncio.create_task(self._initialize_session())
            await self._initialization_task

        # Apply both rate limiting and concurrency limiting
        async with self._rate_limiter:  # Token bucket rate limiting
            async with self._concurrency_limiter:  # Concurrency limiting
                try:
                    # Prepare request
                    url = urljoin(self.config.base_url, endpoint.lstrip("/"))
                    request_params = {
                        "api_key": self.config.api_key,
                        "language": self.config.language,
                        **(params or {}),
                    }

                    # Make request
                    timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                    async with self._session.request(
                        method, url, params=request_params, timeout=timeout
                    ) as response:
                        # Handle HTTP 429 (Too Many Requests) specifically
                        if response.status == 429:
                            retry_after = int(response.headers.get("Retry-After", "10"))
                            logger.warning(
                                f"Rate limit hit (429). Retrying after {retry_after}s. Attempt {retry_count + 1}/{self.config.max_retries + 1}"
                            )

                            if retry_count < self.config.max_retries:
                                await asyncio.sleep(retry_after)
                                return await self._make_request(
                                    method, endpoint, params, retry_count + 1
                                )
                            else:
                                raise aiohttp.ClientResponseError(
                                    request_info=response.request_info,
                                    history=response.history,
                                    status=429,
                                    message=f"Rate limit exceeded after {self.config.max_retries} retries",
                                )

                        # Raise for other HTTP errors
                        response.raise_for_status()
                        data = await response.json()

                        # Update request stats
                        self._last_request_time = time.time()
                        self._request_count += 1

                        return data

                except aiohttp.ClientError as e:
                    if retry_count < self.config.max_retries:
                        # Exponential backoff with jitter
                        base_delay = self.config.retry_delay_base * (2**retry_count)
                        jitter = random.uniform(0.1, 0.5)  # Add jitter to prevent thundering herd
                        delay = min(base_delay + jitter, self.config.retry_delay_max)

                        logger.warning(
                            f"Request failed (attempt {retry_count + 1}), retrying in {delay:.2f}s: {e}"
                        )
                        await asyncio.sleep(delay)
                        return await self._make_request(method, endpoint, params, retry_count + 1)
                    else:
                        logger.error(f"Request failed after {self.config.max_retries} retries: {e}")
                        raise

                except asyncio.TimeoutError:
                    if retry_count < self.config.max_retries:
                        # Exponential backoff with jitter
                        base_delay = self.config.retry_delay_base * (2**retry_count)
                        jitter = random.uniform(0.1, 0.5)
                        delay = min(base_delay + jitter, self.config.retry_delay_max)

                        logger.warning(
                            f"Request timed out (attempt {retry_count + 1}), retrying in {delay:.2f}s"
                        )
                        await asyncio.sleep(delay)
                        return await self._make_request(method, endpoint, params, retry_count + 1)
                    else:
                        logger.error(f"Request timed out after {self.config.max_retries} retries")
                        raise

    async def search_tv_series(
        self, query: str, year: int | None = None, page: int = 1
    ) -> dict[str, Any]:
        """Search for TV series.

        Args:
            query: Search query
            year: Release year filter
            page: Page number

        Returns:
            Search results dictionary
        """
        params = {"query": query, "page": page}
        if year:
            params["first_air_date_year"] = year

        return await self._make_request("GET", "/search/tv", params)

    async def search_multi(self, query: str, page: int = 1) -> dict[str, Any]:
        """Search for both TV series and movies.

        Args:
            query: Search query
            page: Page number

        Returns:
            Multi search results dictionary
        """
        params = {"query": query, "page": page}
        return await self._make_request("GET", "/search/multi", params)

    async def get_tv_series_details(
        self, series_id: int, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get detailed information for a TV series.

        Args:
            series_id: TMDB TV series ID
            include_credits: Whether to include credits information

        Returns:
            TV series details dictionary
        """
        params = {}
        if include_credits:
            params["append_to_response"] = "credits,external_ids"

        return await self._make_request("GET", f"/tv/{series_id}", params)

    async def get_movie_details(
        self, movie_id: int, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get detailed information for a movie.

        Args:
            movie_id: TMDB movie ID
            include_credits: Whether to include credits information

        Returns:
            Movie details dictionary
        """
        params = {}
        if include_credits:
            params["append_to_response"] = "credits,external_ids"

        return await self._make_request("GET", f"/movie/{movie_id}", params)

    async def get_media_details(
        self, media_id: int, media_type: str, include_credits: bool = True
    ) -> dict[str, Any]:
        """Get detailed information for any media type.

        Args:
            media_id: TMDB media ID
            media_type: Media type ('tv' or 'movie')
            include_credits: Whether to include credits information

        Returns:
            Media details dictionary
        """
        if media_type == "tv":
            return await self.get_tv_series_details(media_id, include_credits)
        elif media_type == "movie":
            return await self.get_movie_details(media_id, include_credits)
        else:
            raise ValueError(f"Unsupported media type: {media_type}")

    async def search_comprehensive(
        self,
        query: str,
        year: int | None = None,
        strategies: list[SearchStrategyType] | None = None,
    ) -> list[SearchResult]:
        """Perform comprehensive search using multiple strategies.

        Args:
            query: Search query
            year: Release year filter
            strategies: List of search strategies to use

        Returns:
            List of search results with quality scores
        """
        if strategies is None:
            strategies = [
                SearchStrategyType.EXACT_TITLE_WITH_YEAR,
                SearchStrategyType.EXACT_TITLE_ONLY,
                SearchStrategyType.CLEANED_TITLE,
            ]

        results = []

        for strategy in strategies:
            try:
                if strategy == SearchStrategyType.EXACT_TITLE_WITH_YEAR:
                    search_results = await self.search_tv_series(query, year)
                elif strategy == SearchStrategyType.EXACT_TITLE_ONLY:
                    search_results = await self.search_tv_series(query)
                elif strategy == SearchStrategyType.CLEANED_TITLE:
                    cleaned_query = self._clean_title(query)
                    search_results = await self.search_tv_series(cleaned_query, year)
                else:
                    continue

                # Process results
                for item in search_results.get("results", []):
                    if item.get("media_type") == "tv":
                        result = self._create_search_result(
                            item, SearchStrategy.TV_ONLY, strategy, query, "en", year
                        )
                        results.append(result)

            except Exception as e:
                logger.warning(f"Search strategy {strategy} failed: {e}")
                continue

        # Sort by quality score
        results.sort(key=lambda x: x.quality_score, reverse=True)
        return results

    def _clean_title(self, title: str) -> str:
        """Clean title for better search results.

        Args:
            title: Original title

        Returns:
            Cleaned title
        """
        # Remove common anime suffixes
        suffixes = ["(TV)", "(OVA)", "(ONA)", "(Movie)", "(Special)"]
        cleaned = title
        for suffix in suffixes:
            cleaned = cleaned.replace(suffix, "").strip()

        return cleaned

    def _create_search_result(
        self,
        item: dict[str, Any],
        strategy: SearchStrategy,
        strategy_type: SearchStrategyType,
        query: str,
        language: str,
        year_hint: int | None = None,
    ) -> SearchResult:
        """Create a SearchResult from API response item.

        Args:
            item: API response item
            strategy: Search strategy used
            strategy_type: Specific strategy type

        Returns:
            SearchResult object
        """
        # Calculate quality score
        quality_score = self._quality_calculator.calculate_quality_score(
            result=item, query=query, language=language, year_hint=year_hint
        )

        return SearchResult(
            id=item.get("id", 0),
            media_type=item.get("media_type", "tv"),
            title=item.get("name", ""),
            original_title=item.get("original_name", ""),
            year=int(item.get("first_air_date", "")[:4]) if item.get("first_air_date") else None,
            overview=item.get("overview", ""),
            poster_path=item.get("poster_path"),
            popularity=item.get("popularity", 0),
            vote_average=item.get("vote_average", 0),
            vote_count=item.get("vote_count", 0),
            quality_score=quality_score,
            strategy_used=strategy,
        )

    async def close(self) -> None:
        """Close the client and clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("AsyncTMDBClient session closed")

    async def __aenter__(self) -> AsyncTMDBClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()


# Factory function for creating async TMDB client
def create_async_tmdb_client(config: TMDBConfig | None = None) -> AsyncTMDBClient:
    """Create an async TMDB client with configuration.

    Args:
        config: Optional TMDB configuration. If None, loads from config manager.

    Returns:
        Configured AsyncTMDBClient instance.
    """
    if config is None:
        config_manager = get_config_manager()
        config = TMDBConfig(
            api_key=config_manager.get("tmdb_api_key"),
            language=config_manager.get("tmdb_language", "ko-KR"),
            fallback_language=config_manager.get("tmdb_fallback_language", "en-US"),
            timeout=config_manager.get("tmdb_timeout", 30),
            max_retries=config_manager.get("tmdb_max_retries", 3),
            cache_only_mode=config_manager.get("tmdb_cache_only_mode", False),
        )

    return AsyncTMDBClient(config)
