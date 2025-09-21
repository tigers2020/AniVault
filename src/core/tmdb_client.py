"""TMDB API Client for retrieving anime metadata.

This module provides a comprehensive client for interacting with The Movie Database (TMDB) API
to search for anime series and retrieve detailed metadata including Korean titles, ratings,
posters, and other relevant information.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum
from typing import Any

import tmdbsimple as tmdb

from .config_manager import get_config_manager
from .models import TMDBAnime

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """Search strategy enumeration."""

    MULTI = "multi"
    TV_ONLY = "tv_only"
    MOVIE_ONLY = "movie_only"


class FallbackStrategy(Enum):
    """Fallback strategy enumeration."""

    NORMALIZED = "normalized"
    WORD_REDUCTION = "word_reduction"
    PARTIAL_MATCH = "partial_match"
    LANGUAGE_FALLBACK = "language_fallback"
    WORD_REORDER = "word_reorder"


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
    language_weight: float = 0.2
    include_person_results: bool = False


class TMDBError(Exception):
    """Base exception for TMDB API errors."""

    pass


class TMDBAPIError(TMDBError):
    """Exception for TMDB API specific errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class TMDBRateLimitError(TMDBError):
    """Exception for TMDB API rate limit errors (429)."""

    pass


class TMDBClient:
    """Client for interacting with The Movie Database (TMDB) API.

    This client provides methods to search for anime series, retrieve detailed metadata,
    and handle various error conditions including rate limiting and network issues.
    """

    def __init__(self, config: TMDBConfig):
        """Initialize the TMDB client.

        Args:
            config: TMDB configuration object containing API key and settings
        """
        self.config = config
        self._setup_tmdb()
        self._cache: dict[str, Any] = {}
        self._rate_limited_until: float | None = None

        # Load additional settings from config manager if available
        self._load_additional_settings()

        # Retry statistics for monitoring
        self._retry_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retry_attempts": 0,
            "rate_limit_hits": 0,
            "server_errors": 0,
            "network_errors": 0,
            "client_errors": 0,
        }

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info("TMDB client initialized with API key: %s", self._mask_api_key(config.api_key))

    def _load_additional_settings(self) -> None:
        """Load additional settings from config manager."""
        try:
            from .config_manager import get_config_manager

            config_manager = get_config_manager()

            # Update config with values from config manager
            self.config.high_confidence_threshold = (
                config_manager.get_tmdb_high_confidence_threshold()
            )
            self.config.medium_confidence_threshold = (
                config_manager.get_tmdb_medium_confidence_threshold()
            )
            self.config.similarity_weight = config_manager.get_tmdb_similarity_weight()
            self.config.year_weight = config_manager.get_tmdb_year_weight()
            self.config.language_weight = config_manager.get_tmdb_language_weight()
            self.config.include_person_results = config_manager.get_tmdb_include_person_results()

            logger.debug("Additional TMDB settings loaded from config manager")

        except Exception as e:
            logger.warning("Failed to load additional settings from config manager: %s", e)

    def _setup_tmdb(self) -> None:
        """Setup tmdbsimple with API key and configuration."""
        tmdb.API_KEY = self.config.api_key
        tmdb.REQUESTS_TIMEOUT = self.config.timeout

        # Set default language
        tmdb.language = self.config.language

        # Update session parameters if available
        if hasattr(tmdb, "REQUESTS_SESSION") and tmdb.REQUESTS_SESSION is not None:
            tmdb.REQUESTS_SESSION.params.update(
                {"api_key": self.config.api_key, "language": self.config.language}
            )

        logger.debug("TMDB API configured with language: %s", self.config.language)

    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key for logging purposes."""
        if not api_key:
            return ""
        if len(api_key) <= 8:
            return "***"
        return f"{api_key[:6]}****{api_key[-4:]}"

    def _is_rate_limited(self) -> bool:
        """Check if we're currently rate limited."""
        if self._rate_limited_until is None:
            return False
        return time.time() < self._rate_limited_until

    def _set_rate_limit(self, retry_after: int) -> None:
        """Set rate limit cooldown period."""
        self._rate_limited_until = time.time() + retry_after
        logger.warning("Rate limited until: %s", datetime.fromtimestamp(self._rate_limited_until))

    def _clear_rate_limit(self) -> None:
        """Clear rate limit cooldown."""
        self._rate_limited_until = None
        logger.info("Rate limit cleared")

    def _calculate_retry_delay(self, attempt: int, error_type: str = "generic") -> float:
        """Calculate exponential backoff delay with jitter and error-specific adjustments.

        Args:
            attempt: Current attempt number (0-based)
            error_type: Type of error ('rate_limit', 'server_error', 'network_error', 'generic')

        Returns:
            Delay in seconds
        """
        # Base exponential backoff
        delay = min(self.config.retry_delay_base * (2**attempt), self.config.retry_delay_max)

        # Error-specific adjustments
        if error_type == "rate_limit":
            # Longer delays for rate limiting
            delay *= 2.0
        elif error_type == "server_error":
            # Moderate delays for server errors
            delay *= 1.5
        elif error_type == "network_error":
            # Shorter delays for network errors (might be temporary)
            delay *= 1.0
        else:  # generic
            delay *= 1.0

        # Add jitter to prevent thundering herd
        # Use different jitter strategies based on error type
        if error_type == "rate_limit":
            # More aggressive jitter for rate limiting
            jitter_factor = random.uniform(0.3, 0.7)
        else:
            # Standard jitter
            jitter_factor = random.uniform(0.1, 0.5)

        jitter = jitter_factor * delay
        final_delay = delay + jitter

        logger.debug(
            "Calculated retry delay: base=%.2fs, jitter=%.2fs, final=%.2fs (attempt=%d, error_type=%s)",
            delay,
            jitter,
            final_delay,
            attempt + 1,
            error_type,
        )

        return float(final_delay)

    def _handle_api_error(self, error: Exception, attempt: int) -> None:
        """Handle API errors and determine if retry is appropriate with improved error classification.

        Args:
            error: The exception that occurred
            attempt: Current attempt number (0-based)
        """
        error_type = "generic"

        if hasattr(error, "response"):
            status_code = getattr(error.response, "status_code", None)

            if status_code == 429:  # Rate limited
                retry_after = 60  # Default to 60 seconds
                if hasattr(error.response, "headers"):
                    retry_after_header = error.response.headers.get("Retry-After")
                    if retry_after_header:
                        try:
                            retry_after = int(retry_after_header)
                        except ValueError:
                            pass

                self._set_rate_limit(retry_after)
                raise TMDBRateLimitError(
                    f"Rate limited by TMDB API. Retry after {retry_after} seconds"
                )

            elif status_code in [500, 502, 503, 504]:  # Server errors
                error_type = "server_error"
                if attempt < self.config.max_retries:
                    delay = self._calculate_retry_delay(attempt, error_type)
                    logger.warning(
                        "Server error %d, retrying in %.2f seconds (attempt %d/%d)",
                        status_code,
                        delay,
                        attempt + 1,
                        self.config.max_retries + 1,
                    )
                    time.sleep(delay)
                    return
                else:
                    raise TMDBAPIError(
                        f"Server error {status_code} after {self.config.max_retries} retries",
                        status_code=status_code,
                    )

            elif status_code in [408, 429]:  # Timeout and rate limit
                error_type = "timeout"
                if attempt < self.config.max_retries:
                    delay = self._calculate_retry_delay(attempt, error_type)
                    logger.warning(
                        "Timeout/rate limit %d, retrying in %.2f seconds (attempt %d/%d)",
                        status_code,
                        delay,
                        attempt + 1,
                        self.config.max_retries + 1,
                    )
                    time.sleep(delay)
                    return
                else:
                    raise TMDBAPIError(
                        f"Timeout/rate limit {status_code} after {self.config.max_retries} retries",
                        status_code=status_code,
                    )

            elif status_code in [400, 401, 403, 404]:  # Client errors (don't retry)
                raise TMDBAPIError(
                    f"Client error {status_code}: {error!s}", status_code=status_code
                )

            else:  # Other HTTP errors
                error_type = "http_error"
                if attempt < self.config.max_retries:
                    delay = self._calculate_retry_delay(attempt, error_type)
                    logger.warning(
                        "HTTP error %d, retrying in %.2f seconds (attempt %d/%d)",
                        status_code,
                        delay,
                        attempt + 1,
                        self.config.max_retries + 1,
                    )
                    time.sleep(delay)
                    return
                else:
                    raise TMDBAPIError(
                        f"HTTP error {status_code} after {self.config.max_retries} retries",
                        status_code=status_code,
                    )

        # Network or other errors
        error_type = "network_error"
        if attempt < self.config.max_retries:
            delay = self._calculate_retry_delay(attempt, error_type)
            logger.warning(
                "Network error, retrying in %.2f seconds (attempt %d/%d): %s",
                delay,
                attempt + 1,
                self.config.max_retries + 1,
                str(error),
            )
            time.sleep(delay)
        else:
            raise TMDBAPIError(f"Network error after {self.config.max_retries} retries: {error!s}")

    def _make_request(self, func, *args, **kwargs) -> Any:
        """Make a request with retry logic and error handling.

        Args:
            func: TMDB API function to call
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            API response data

        Raises:
            TMDBRateLimitError: When rate limited
            TMDBAPIError: When API errors occur
            TMDBError: For other errors
        """
        if self.config.cache_only_mode:
            logger.warning("Cache-only mode active, skipping API request")
            return None

        if self._is_rate_limited():
            raise TMDBRateLimitError("Currently rate limited")

        self._retry_stats["total_requests"] += 1

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(
                    "Making TMDB API request (attempt %d/%d)",
                    attempt + 1,
                    self.config.max_retries + 1,
                )

                result = func(*args, **kwargs)

                # Clear rate limit on successful request
                if self._rate_limited_until:
                    self._clear_rate_limit()

                self._retry_stats["successful_requests"] += 1
                if attempt > 0:
                    self._retry_stats["retry_attempts"] += attempt

                return result

            except Exception as e:
                if attempt == self.config.max_retries:
                    self._retry_stats["failed_requests"] += 1
                    if attempt > 0:
                        self._retry_stats["retry_attempts"] += attempt
                    self._handle_api_error(e, attempt)
                    break
                else:
                    self._retry_stats["retry_attempts"] += 1
                    self._handle_api_error(e, attempt)

        # This should never be reached due to exceptions above
        raise TMDBError("Unexpected error in _make_request")

    def search_tv_series(self, query: str, language: str | None = None) -> list[dict[str, Any]]:
        """Search for TV series using the TMDB API.

        Args:
            query: Search query (anime title)
            language: Language code for search results (defaults to config language)

        Returns:
            List of search results from TMDB API

        Raises:
            TMDBRateLimitError: When rate limited
            TMDBAPIError: When API errors occur
        """
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return []

        # Use specified language or fallback to config
        search_language = language or self.config.language

        logger.info("Searching TMDB for TV series: '%s' (language: %s)", query, search_language)

        # Check cache first
        cache_key = f"search_{query}_{search_language}"
        if cache_key in self._cache:
            logger.debug("Cache hit for search: %s", query)
            self._cache_hits += 1
            return self._cache[cache_key]  # type: ignore[no-any-return]

        logger.debug("Cache miss for search: %s", query)
        self._cache_misses += 1

        search = tmdb.Search()

        try:
            # Try with primary language first
            results = self._make_request(
                search.tv, query=query.strip(), language=search_language, include_adult=False
            )

            # Handle cache-only mode
            if results is None:
                logger.info("Cache-only mode: returning empty results for '%s'", query)
                return []

            if not results.get("results"):
                logger.info(
                    "No results found with language %s, trying fallback language", search_language
                )

                # Try with fallback language if no results
                if search_language != self.config.fallback_language:
                    results = self._make_request(
                        search.tv,
                        query=query.strip(),
                        language=self.config.fallback_language,
                        include_adult=False,
                    )

            search_results = results.get("results", [])
            logger.info("Found %d search results for '%s'", len(search_results), query)

            # Cache the results
            self._cache[cache_key] = search_results

            return search_results  # type: ignore[no-any-return]

        except TMDBRateLimitError:
            logger.error("Rate limited while searching for '%s'", query)
            raise
        except TMDBAPIError:
            logger.error("API error while searching for '%s'", query)
            raise
        except Exception as e:
            logger.error("Unexpected error while searching for '%s': %s", query, str(e))
            raise TMDBError(f"Search failed: {e!s}") from e

    def search_multi(
        self,
        query: str,
        language: str | None = None,
        region: str | None = None,
        include_adult: bool = False,
    ) -> list[dict[str, Any]]:
        """Search for movies and TV series using TMDB Multi Search API.

        Args:
            query: Search query
            language: Language code for search results
            region: Region code for search results
            include_adult: Whether to include adult content

        Returns:
            List of search results from TMDB Multi Search API

        Raises:
            TMDBRateLimitError: When rate limited
            TMDBAPIError: When API errors occur
        """
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return []

        search_language = language or self.config.language
        search_region = region or "KR"  # Default to Korea

        logger.info(
            "Searching TMDB Multi for: '%s' (language: %s, region: %s)",
            query,
            search_language,
            search_region,
        )

        # Check cache first
        cache_key = f"multi_{query}_{search_language}_{search_region}_{include_adult}"
        if cache_key in self._cache:
            logger.debug("Cache hit for multi search: %s", query)
            self._cache_hits += 1
            return self._cache[cache_key]  # type: ignore[no-any-return]

        logger.debug("Cache miss for multi search: %s", query)
        self._cache_misses += 1

        search = tmdb.Search()

        try:
            # Use Multi Search API
            logger.debug(
                "Making multi search request: query='%s', language='%s', region='%s'",
                query,
                search_language,
                search_region,
            )

            results = self._make_request(
                search.multi,
                query=query.strip(),
                language=search_language,
                region=search_region,
                include_adult=include_adult,
            )

            logger.debug("API response received: %s", type(results))
            if results:
                logger.debug(
                    "API response keys: %s",
                    list(results.keys()) if isinstance(results, dict) else "Not a dict",
                )

            search_results = results.get("results", []) if results else []
            logger.info("Raw search results: %d items", len(search_results))

            # Log detailed JSON results for debugging
            import json

            for i, result in enumerate(search_results):
                logger.info(
                    "Result %d JSON: %s", i, json.dumps(result, ensure_ascii=False, indent=2)
                )
                logger.info(
                    "Result %d - title: '%s', original_title: '%s', name: '%s', original_name: '%s'",
                    i,
                    result.get("title"),
                    result.get("original_title"),
                    result.get("name"),
                    result.get("original_name"),
                )

            # Filter to only include TV and Movie results
            filtered_results = [
                result for result in search_results if result.get("media_type") in ["tv", "movie"]
            ]
            logger.info("Filtered results: %d items", len(filtered_results))

            # If no results with requested language, try fallback language
            if not filtered_results and search_language != self.config.fallback_language:
                logger.info(
                    "No results found with language %s, trying fallback language", search_language
                )
                try:
                    fallback_results = self._make_request(
                        search.multi,
                        query=query.strip(),
                        language=self.config.fallback_language,
                        region=search_region,
                        include_adult=include_adult,
                    )

                    fallback_search_results = fallback_results.get("results", [])
                    filtered_results = [
                        result
                        for result in fallback_search_results
                        if result.get("media_type") in ["tv", "movie"]
                    ]
                    logger.info(
                        "Found %d results with fallback language %s",
                        len(filtered_results),
                        self.config.fallback_language,
                    )
                except Exception as e:
                    logger.warning("Failed to search with fallback language: %s", str(e))

            logger.info(
                "Found %d multi search results for '%s' (%d filtered)",
                len(search_results),
                query,
                len(filtered_results),
            )

            # Cache the results
            self._cache[cache_key] = filtered_results

            return filtered_results

        except TMDBRateLimitError:
            logger.error("Rate limited while multi searching for '%s'", query)
            raise
        except TMDBAPIError:
            logger.error("API error while multi searching for '%s'", query)
            raise
        except Exception as e:
            logger.error("Unexpected error while multi searching for '%s': %s", query, str(e))
            raise TMDBError(f"Multi search failed: {e!s}") from e

    def _calculate_quality_score(
        self, result: dict[str, Any], query: str, language: str, year_hint: int | None = None
    ) -> float:
        """Calculate quality score for a search result.

        Args:
            result: TMDB search result
            query: Original search query
            language: Language code
            year_hint: Year hint from filename parsing

        Returns:
            Quality score between 0.0 and 1.0
        """
        # Extract title and year from result
        title = result.get("title") or result.get("name", "")
        original_title = result.get("original_title") or result.get("original_name", "")
        release_date = result.get("release_date") or result.get("first_air_date", "")

        # Extract year from release date
        result_year = None
        if release_date:
            try:
                result_year = int(release_date.split("-")[0])
            except (ValueError, IndexError):
                pass

        # 1. Similarity score (0.6 weight)
        similarity_score = self._calculate_similarity_score(query, title, original_title)

        # 2. Year match score (0.2 weight)
        year_score = self._calculate_year_score(result_year, year_hint)

        # 3. Language match score (0.2 weight)
        language_score = self._calculate_language_score(result, language)

        # Calculate weighted total
        total_score = (
            similarity_score * self.config.similarity_weight
            + year_score * self.config.year_weight
            + language_score * self.config.language_weight
        )

        return min(1.0, max(0.0, total_score))

    def _calculate_similarity_score(self, query: str, title: str, original_title: str) -> float:
        """Calculate similarity score between query and titles."""
        # Normalize query and titles
        query_tokens = self._normalize_query_tokens(query)
        title_tokens = self._normalize_query_tokens(title)
        original_tokens = self._normalize_query_tokens(original_title)

        # Calculate Jaccard similarity for both titles
        title_similarity = self._jaccard_similarity(query_tokens, title_tokens)
        original_similarity = self._jaccard_similarity(query_tokens, original_tokens)

        # Use the higher similarity
        return max(title_similarity, original_similarity)

    def _normalize_query_tokens(self, text: str) -> set[str]:
        """Normalize text to tokens, removing brackets, resolution, release group tags."""
        if not text:
            return set()

        # Remove common anime file tags
        import re

        text = re.sub(r"\[.*?\]", "", text)  # Remove [tags]
        text = re.sub(r"\(.*?\)", "", text)  # Remove (tags)
        text = re.sub(r"[0-9]+p", "", text, flags=re.IGNORECASE)  # Remove resolution
        text = re.sub(r"[0-9]+i", "", text, flags=re.IGNORECASE)  # Remove interlaced
        text = re.sub(r"[0-9]+fps", "", text, flags=re.IGNORECASE)  # Remove fps

        # Split into tokens and normalize
        tokens = re.findall(r"\b\w+\b", text.lower())
        return set(tokens)

    def _jaccard_similarity(self, set1: set[str], set2: set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        return intersection / union if union > 0 else 0.0

    def _calculate_year_score(self, result_year: int | None, year_hint: int | None) -> float:
        """Calculate year match score."""
        if not result_year or not year_hint:
            return 0.5  # Neutral score if no year info

        year_diff = abs(result_year - year_hint)

        if year_diff == 0:
            return 1.0
        elif year_diff == 1:
            return 0.8  # ±1 year gets partial credit
        elif year_diff <= 3:
            return 0.5  # ±3 years gets some credit
        else:
            return 0.0  # Too far apart

    def _calculate_language_score(self, result: dict[str, Any], language: str) -> float:
        """Calculate language match score."""
        # Check if result has translations for the requested language
        translations = result.get("translations", {}).get("translations", [])

        for translation in translations:
            if translation.get("iso_639_1") == language.split("-")[0]:
                return 1.0

        # Check if original language matches
        original_language = result.get("original_language", "")
        if original_language == language.split("-")[0]:
            return 0.8

        return 0.5  # Neutral score for other languages

    def search_comprehensive(
        self, query: str, language: str | None = None, min_quality: float | None = None
    ) -> tuple[list[SearchResult] | None, bool]:
        """Comprehensive search using Multi Search with fallback strategies.

        Args:
            query: Search query
            language: Language code for search
            min_quality: Minimum quality threshold (uses config default if None)

        Returns:
            Tuple of (search_results, needs_manual_selection)
        """
        try:
            if not query or not query.strip():
                logger.warning("Empty search query provided")
                return None, False

            search_language = language or self.config.language
            quality_threshold = min_quality or self.config.medium_confidence_threshold

            logger.info(
                "Starting comprehensive search for: '%s' (threshold: %.2f)",
                query,
                quality_threshold,
            )

            # Extract year hint from query if possible
            year_hint = self._extract_year_from_query(query)

            # Try Multi Search with original query
            results = self._try_multi_search_with_scoring(
                query, search_language, year_hint, SearchStrategy.MULTI, 0
            )

            if results:
                logger.info("Initial raw results: %d items", len(results))
                high_confidence_results = [
                    r for r in results if r.quality_score >= self.config.high_confidence_threshold
                ]
                medium_confidence_results = [
                    r for r in results if r.quality_score >= quality_threshold
                ]
                logger.info(
                    "High confidence (>= %.2f): %d items, Medium confidence (>= %.2f): %d items",
                    self.config.high_confidence_threshold,
                    len(high_confidence_results),
                    quality_threshold,
                    len(medium_confidence_results),
                )

                if len(high_confidence_results) == 1:
                    # Single high confidence result - use directly
                    logger.info("Found single high confidence result for '%s'", query)
                    return [high_confidence_results[0]], False
                elif len(medium_confidence_results) >= 2:
                    # Multiple medium+ confidence results - need selection
                    logger.info(
                        "Found %d medium+ confidence results for '%s', needs selection",
                        len(medium_confidence_results),
                        query,
                    )
                    return medium_confidence_results, True
                elif len(medium_confidence_results) == 1:
                    # Single medium confidence result - use directly
                    logger.info("Found single medium confidence result for '%s'", query)
                    return [medium_confidence_results[0]], False

            # Try fallback strategies
            fallback_strategies = [
                (FallbackStrategy.NORMALIZED, self._normalize_query),
                (FallbackStrategy.WORD_REDUCTION, self._reduce_query_words),
                (FallbackStrategy.PARTIAL_MATCH, self._create_partial_query),
                (FallbackStrategy.LANGUAGE_FALLBACK, lambda q: q),  # Will use fallback language
                (FallbackStrategy.WORD_REORDER, self._reorder_query_words),
            ]

            for round_num, (strategy, query_modifier) in enumerate(fallback_strategies, 1):
                if strategy == FallbackStrategy.LANGUAGE_FALLBACK:
                    # Use fallback language
                    modified_query = query
                    fallback_language = self.config.fallback_language
                else:
                    modified_query = query_modifier(query)
                    fallback_language = search_language

                if not modified_query or modified_query == query:
                    continue

                logger.info(
                    "Trying fallback strategy %s (round %d): '%s'",
                    strategy.value,
                    round_num,
                    modified_query,
                )

                results = self._try_multi_search_with_scoring(
                    modified_query, fallback_language, year_hint, SearchStrategy.MULTI, round_num
                )

                if results:
                    logger.info("Raw results from %s: %d items", strategy.value, len(results))
                    medium_confidence_results = [
                        r for r in results if r.quality_score >= quality_threshold
                    ]
                    logger.info(
                        "Filtered results (quality >= %.2f): %d items",
                        quality_threshold,
                        len(medium_confidence_results),
                    )

                    if len(medium_confidence_results) >= 2:
                        logger.info(
                            "Found %d results with %s strategy, needs selection",
                            len(medium_confidence_results),
                            strategy.value,
                        )
                        return medium_confidence_results, True
                    elif len(medium_confidence_results) == 1:
                        logger.info("Found single result with %s strategy", strategy.value)
                        return [medium_confidence_results[0]], False

            # No results found
            logger.info("No results found for '%s' after all strategies", query)
            return None, False

        except Exception as e:
            logger.error("Unexpected error during comprehensive search for '%s': %s", query, str(e))
            return None, False

    def _try_multi_search_with_scoring(
        self,
        query: str,
        language: str,
        year_hint: int | None,
        strategy: SearchStrategy,
        fallback_round: int,
    ) -> list[SearchResult]:
        """Try multi search and score results."""
        try:
            raw_results = self.search_multi(query, language)
            if not raw_results:
                return []

            # Convert to SearchResult objects with scoring
            search_results = []
            for result in raw_results:
                quality_score = self._calculate_quality_score(result, query, language, year_hint)

                search_result = SearchResult(
                    id=result.get("id", 0),
                    media_type=result.get("media_type", "unknown"),
                    title=result.get("title") or result.get("name", ""),
                    original_title=result.get("original_title") or result.get("original_name", ""),
                    year=self._extract_year_from_date(
                        result.get("release_date") or result.get("first_air_date", "")
                    ),
                    overview=result.get("overview", ""),
                    poster_path=result.get("poster_path"),
                    popularity=result.get("popularity", 0.0),
                    vote_average=result.get("vote_average", 0.0),
                    vote_count=result.get("vote_count", 0),
                    quality_score=quality_score,
                    strategy_used=strategy,
                    fallback_round=fallback_round,
                )
                search_results.append(search_result)

            # Sort by quality score descending
            search_results.sort(key=lambda x: x.quality_score, reverse=True)
            return search_results

        except Exception as e:
            logger.error("Error in multi search with scoring: %s", str(e))
            return []

    def _extract_year_from_query(self, query: str) -> int | None:
        """Extract year from query string."""
        import re

        year_match = re.search(r"\b(19|20)\d{2}\b", query)
        if year_match:
            return int(year_match.group())
        return None

    def _extract_year_from_date(self, date_str: str) -> int | None:
        """Extract year from date string."""
        if not date_str:
            return None
        try:
            return int(date_str.split("-")[0])
        except (ValueError, IndexError):
            return None

    def _normalize_query(self, query: str) -> str:
        """Normalize query by removing brackets and common tags."""
        import re

        # Remove [tags], (tags), resolution, fps, etc.
        normalized = re.sub(r"\[.*?\]", "", query)
        normalized = re.sub(r"\(.*?\)", "", normalized)
        normalized = re.sub(r"[0-9]+[pi]", "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"[0-9]+fps", "", normalized, flags=re.IGNORECASE)

        # Remove common anime file suffixes
        normalized = re.sub(r"\s*-\s*[A-Za-z\s]+$", "", normalized)  # Remove "- Season 1" etc.
        normalized = re.sub(r"\s*편$", "", normalized)  # Remove Korean "편" suffix
        normalized = re.sub(
            r"\s*시즌\s*\d+$", "", normalized, flags=re.IGNORECASE
        )  # Remove Korean "시즌" suffix

        return normalized.strip()

    def _reduce_query_words(self, query: str) -> str:
        """Reduce query by removing words from the end."""
        words = query.split()
        if len(words) <= 1:
            return ""
        return " ".join(words[:-1])

    def _create_partial_query(self, query: str) -> str:
        """Create partial match query using first few words."""
        words = query.split()
        if len(words) <= 2:
            return ""
        return " ".join(words[:2])

    def _reorder_query_words(self, query: str) -> str:
        """Reorder query words (simple reversal)."""
        words = query.split()
        if len(words) <= 1:
            return query
        return " ".join(reversed(words))

    def get_media_details(
        self, media_id: int, media_type: str, language: str | None = None
    ) -> dict[str, Any]:
        """Get detailed information for TV series or movies using append_to_response.

        Args:
            media_id: TMDB media ID
            media_type: 'tv' or 'movie'
            language: Language code for details

        Returns:
            Detailed media information from TMDB API

        Raises:
            TMDBRateLimitError: When rate limited
            TMDBAPIError: When API errors occur
        """
        detail_language = language or self.config.language

        logger.info(
            "Getting %s details for ID %d (language: %s)", media_type, media_id, detail_language
        )

        # Check cache first
        cache_key = f"details_{media_type}_{media_id}_{detail_language}"
        if cache_key in self._cache:
            logger.debug("Cache hit for %s details: ID %d", media_type, media_id)
            self._cache_hits += 1
            return self._cache[cache_key]  # type: ignore[no-any-return]

        logger.debug("Cache miss for %s details: ID %d", media_type, media_id)
        self._cache_misses += 1

        try:
            if media_type == "tv":
                media_obj = tmdb.TV(media_id)
                details = self._make_request(
                    media_obj.info,
                    language=detail_language,
                    append_to_response="external_ids,credits,content_ratings,translations,alternative_titles,images",
                )
            elif media_type == "movie":
                media_obj = tmdb.Movies(media_id)
                details = self._make_request(
                    media_obj.info,
                    language=detail_language,
                    append_to_response="external_ids,credits,release_dates,translations,alternative_titles,images",
                )
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

            logger.debug("Retrieved details for %s ID %d", media_type, media_id)

            # Cache the results
            self._cache[cache_key] = details

            return details  # type: ignore[no-any-return]

        except TMDBRateLimitError:
            logger.error("Rate limited while getting %s details for ID %d", media_type, media_id)
            raise
        except TMDBAPIError:
            logger.error("API error while getting %s details for ID %d", media_type, media_id)
            raise
        except Exception as e:
            logger.error(
                "Unexpected error while getting %s details for ID %d: %s",
                media_type,
                media_id,
                str(e),
            )
            raise TMDBError(f"Details retrieval failed: {e!s}") from e

    def get_display_title(self, details: dict[str, Any], language: str | None = None) -> str:
        """Get the best display title from media details.

        Args:
            details: Media details from TMDB API
            language: Preferred language code

        Returns:
            Best available title for display
        """
        if not details:
            return "Unknown"

        target_language = language or self.config.language
        lang_code = target_language.split("-")[0] if "-" in target_language else target_language

        # Check translations first
        translations = details.get("translations", {}).get("translations", [])
        for translation in translations:
            if translation.get("iso_639_1") == lang_code:
                translated_data = translation.get("data", {})
                title = translated_data.get("title") or translated_data.get("name")
                if title:
                    return title  # type: ignore[no-any-return]

        # Fallback to main title
        title = details.get("title") or details.get("name")
        if title:
            return title  # type: ignore[no-any-return]

        # Fallback to original title
        original_title = details.get("original_title") or details.get("original_name")
        if original_title:
            return original_title  # type: ignore[no-any-return]

        return "Unknown"

    def search_and_get_metadata_with_dialog(
        self, query: str, language: str | None = None, min_quality: float | None = None
    ) -> tuple[TMDBAnime | None, bool]:
        """Search and get metadata with dialog integration support.

        Args:
            query: Search query
            language: Language code for search
            min_quality: Minimum quality threshold

        Returns:
            Tuple of (TMDBAnime object or None, needs_manual_selection)
        """
        # Use comprehensive search
        search_results, needs_selection = self.search_comprehensive(query, language, min_quality)

        if not search_results:
            return None, False

        if needs_selection:
            # Return the first result but indicate selection is needed
            # The dialog system will handle the actual selection
            first_result = search_results[0]
            return self._convert_search_result_to_anime(first_result, language), True
        else:
            # Single result, convert to TMDBAnime
            return self._convert_search_result_to_anime(search_results[0], language), False

    def _convert_search_result_to_anime(
        self, search_result: SearchResult, language: str | None = None
    ) -> TMDBAnime | None:
        """Convert SearchResult to TMDBAnime object."""
        try:
            # Get detailed information
            details = self.get_media_details(search_result.id, search_result.media_type, language)

            if not details:
                return None

            # Extract display title
            display_title = self.get_display_title(details, language)

            # Convert to TMDBAnime using from_dict for proper field conversion
            anime = TMDBAnime.from_dict(details)

            # Debug: Log genres data
            logger.debug("Raw genres from details: %s", details.get("genres"))
            logger.debug("Processed genres in anime: %s", anime.genres)
            logger.debug("Genres type: %s", type(anime.genres))
            if anime.genres and len(anime.genres) > 0:
                logger.debug(
                    "First genre type: %s, value: %s", type(anime.genres[0]), anime.genres[0]
                )

            # Override with search result specific fields
            anime.tmdb_id = search_result.id
            anime.title = display_title
            anime.original_title = search_result.original_title
            anime.overview = search_result.overview
            anime.vote_average = search_result.vote_average
            anime.vote_count = search_result.vote_count
            anime.popularity = search_result.popularity
            anime.poster_path = search_result.poster_path or ""
            anime.quality_score = search_result.quality_score
            anime.search_strategy = search_result.strategy_used.value
            anime.fallback_round = search_result.fallback_round

            return anime

        except Exception as e:
            logger.error("Error converting search result to TMDBAnime: %s", str(e))
            return None

    def get_tv_series_details(self, series_id: int, language: str | None = None) -> dict[str, Any]:
        """Get detailed information for a TV series.

        Args:
            series_id: TMDB series ID
            language: Language code for details (defaults to config language)

        Returns:
            Detailed series information from TMDB API

        Raises:
            TMDBRateLimitError: When rate limited
            TMDBAPIError: When API errors occur
        """
        detail_language = language or self.config.language

        logger.info(
            "Getting TV series details for ID %d (language: %s)", series_id, detail_language
        )

        # Check cache first
        cache_key = f"details_{series_id}_{detail_language}"
        if cache_key in self._cache:
            logger.debug("Cache hit for series details: ID %d", series_id)
            self._cache_hits += 1
            return self._cache[cache_key]  # type: ignore[no-any-return]

        logger.debug("Cache miss for series details: ID %d", series_id)
        self._cache_misses += 1

        tv = tmdb.TV(series_id)

        try:
            details = self._make_request(
                tv.info,
                language=detail_language,
                append_to_response="alternative_titles,external_ids",
            )

            logger.debug("Retrieved details for series ID %d", series_id)

            # Cache the results
            self._cache[cache_key] = details

            return details  # type: ignore[no-any-return]

        except TMDBRateLimitError:
            logger.error("Rate limited while getting details for series ID %d", series_id)
            raise
        except TMDBAPIError:
            logger.error("API error while getting details for series ID %d", series_id)
            raise
        except Exception as e:
            logger.error(
                "Unexpected error while getting details for series ID %d: %s", series_id, str(e)
            )
            raise TMDBError(f"Failed to get series details: {e!s}") from e

    def find_korean_title(self, series_data: dict[str, Any]) -> str:
        """Find the best Korean title from series data using comprehensive priority logic.

        Args:
            series_data: Series data from TMDB API

        Returns:
            Best Korean title found, or empty string if none found
        """
        korean_title = ""

        # Priority 1: Korean alternative titles (highest priority)
        alternative_titles = series_data.get("alternative_titles", {}).get("results", [])

        for alt_title in alternative_titles:
            if alt_title.get("iso_3166_1") == "KR" and alt_title.get("title"):
                korean_title = alt_title["title"]
                logger.debug("Found Korean title in alternative titles: '%s'", korean_title)
                break

        # Priority 2: If main title is Korean (original language is Korean)
        if not korean_title and series_data.get("original_language") == "ko":
            korean_title = series_data.get("name", "")
            logger.debug("Using original Korean title: '%s'", korean_title)

        # Priority 3: Check if main title contains Korean characters
        if not korean_title:
            main_title = series_data.get("name", "")
            if self._contains_korean_characters(main_title):
                korean_title = main_title
                logger.debug("Using main title with Korean characters: '%s'", korean_title)

        # Priority 4: Check original name for Korean characters
        if not korean_title:
            original_title = series_data.get("original_name", "")
            if self._contains_korean_characters(original_title):
                korean_title = original_title
                logger.debug("Using original title with Korean characters: '%s'", korean_title)

        return korean_title

    def _contains_korean_characters(self, text: str) -> bool:
        """Check if text contains Korean characters.

        Args:
            text: Text to check

        Returns:
            True if text contains Korean characters, False otherwise
        """
        if not text:
            return False

        # Korean Unicode ranges:
        # Hangul Syllables: U+AC00–U+D7AF
        # Hangul Jamo: U+1100–U+11FF
        # Hangul Compatibility Jamo: U+3130–U+318F
        for char in text:
            if (
                "\u1100" <= char <= "\u11ff"
                or "\u3130" <= char <= "\u318f"
                or "\uac00" <= char <= "\ud7af"
            ):
                return True

        return False

    def get_title_priority_matrix(self, series_data: dict[str, Any]) -> dict[str, str]:
        """Get all available titles with their priority ranking for display purposes.

        Args:
            series_data: Series data from TMDB API

        Returns:
            Dictionary mapping priority levels to titles
        """
        titles = {"korean": "", "main": "", "original": "", "english": ""}

        # Get Korean title (highest priority)
        titles["korean"] = self.find_korean_title(series_data)

        # Get main title
        titles["main"] = series_data.get("name", "")

        # Get original title
        titles["original"] = series_data.get("original_name", "")

        # Look for English title in alternative titles
        alternative_titles = series_data.get("alternative_titles", {}).get("results", [])
        for alt_title in alternative_titles:
            if alt_title.get("iso_3166_1") == "US" and alt_title.get("title"):
                titles["english"] = alt_title["title"]
                break

        # If no English alternative title, use main title if it's in English
        if not titles["english"] and series_data.get("original_language") == "en":
            titles["english"] = titles["main"]

        return titles

    def _find_best_match(
        self, query: str, search_results: list[dict[str, Any]], threshold: float = 0.7
    ) -> dict[str, Any] | None:
        """Find the best matching series from search results using similarity scoring.

        Args:
            query: Original search query
            search_results: List of search results from TMDB API
            threshold: Minimum similarity threshold (0.0 to 1.0)

        Returns:
            Best matching result or None if no good match found
        """
        if not search_results:
            return None

        best_match = None
        best_score = 0.0

        # Clean the query for comparison
        clean_query = self._clean_title_for_comparison(query)

        for result in search_results:
            # Get candidate titles from the result
            candidate_titles = []

            if result.get("name"):
                candidate_titles.append(result["name"])
            if result.get("original_name") and result["original_name"] != result.get("name"):
                candidate_titles.append(result["original_name"])

            # Calculate similarity for each candidate title
            max_score = 0.0
            for title in candidate_titles:
                clean_title = self._clean_title_for_comparison(title)
                similarity = SequenceMatcher(None, clean_query.lower(), clean_title.lower()).ratio()
                max_score = max(max_score, similarity)

            logger.debug(
                "Query: '%s' vs Title: '%s' -> Score: %.3f",
                query,
                result.get("name", ""),
                max_score,
            )

            # Update best match if this score is higher
            if max_score > best_score and max_score >= threshold:
                best_score = max_score
                best_match = result

        if best_match:
            logger.info(
                "Best match found: '%s' (score: %.3f) for query: '%s'",
                best_match.get("name", ""),
                best_score,
                query,
            )
        else:
            logger.info("No good match found for query: '%s' (threshold: %.2f)", query, threshold)

        return best_match

    def _clean_title_for_comparison(self, title: str) -> str:
        """Clean a title for similarity comparison by removing common prefixes/suffixes.

        Args:
            title: Title to clean

        Returns:
            Cleaned title
        """
        if not title:
            return ""

        # Remove common prefixes and suffixes
        title = title.strip()

        # Remove common prefixes
        prefixes_to_remove = [
            "anime:",
            "manga:",
            "tv:",
            "movie:",
            "film:",
            "애니:",
            "만화:",
            "드라마:",
            "영화:",
            "[anime]",
            "[manga]",
            "[tv]",
            "[movie]",
            "[애니]",
            "[만화]",
            "[드라마]",
            "[영화]",
            "【애니】",
            "【만화】",
            "【드라마】",
            "【영화】",
        ]

        for prefix in prefixes_to_remove:
            if title.lower().startswith(prefix.lower()):
                title = title[len(prefix) :].strip()

        # Remove common suffixes
        suffixes_to_remove = [
            " (anime)",
            " (manga)",
            " (tv)",
            " (movie)",
            " (애니)",
            " (만화)",
            " (드라마)",
            " (영화)",
            " - anime",
            " - manga",
            " - tv",
            " - movie",
        ]

        for suffix in suffixes_to_remove:
            if title.lower().endswith(suffix.lower()):
                title = title[: -len(suffix)].strip()

        # Remove extra whitespace and normalize
        title = " ".join(title.split())

        return title

    def extract_metadata(self, series_data: dict[str, Any]) -> TMDBAnime:
        """Extract and normalize metadata from TMDB series data with comprehensive validation.

        Args:
            series_data: Raw series data from TMDB API

        Returns:
            TMDBAnime object with normalized metadata
        """
        logger.debug("Extracting and normalizing metadata from TMDB series data")

        # Validate and normalize TMDB ID
        tmdb_id = self._normalize_tmdb_id(series_data.get("id"))

        # Parse and normalize dates
        first_air_date = self._parse_date(series_data.get("first_air_date"), "first_air_date")
        last_air_date = self._parse_date(series_data.get("last_air_date"), "last_air_date")

        # Extract and normalize genres
        genres = self._extract_and_normalize_genres(series_data.get("genres", []))

        # Extract and normalize networks
        networks = self._extract_and_normalize_networks(series_data.get("networks", []))

        # Normalize titles
        title = self._normalize_title(series_data.get("name", ""))
        original_title = self._normalize_title(series_data.get("original_name", ""))

        # Find Korean title using improved priority logic
        korean_title = self.find_korean_title(series_data)
        korean_title = self._normalize_title(korean_title)

        # Normalize overview text
        overview = self._normalize_overview(series_data.get("overview", ""))

        # Normalize status
        status = self._normalize_status(series_data.get("status", ""))

        # Normalize ratings and popularity
        vote_average = self._normalize_rating(series_data.get("vote_average", 0.0))
        vote_count = self._normalize_vote_count(series_data.get("vote_count", 0))
        popularity = self._normalize_popularity(series_data.get("popularity", 0.0))

        # Normalize season and episode counts
        number_of_seasons = self._normalize_count(series_data.get("number_of_seasons", 0))
        number_of_episodes = self._normalize_count(series_data.get("number_of_episodes", 0))

        # Get title priority matrix for debugging
        title_matrix = self.get_title_priority_matrix(series_data)
        logger.debug("Title priority matrix: %s", title_matrix)

        # Create TMDBAnime object with normalized data
        tmdb_anime = TMDBAnime(
            tmdb_id=tmdb_id,
            title=title,
            original_title=original_title,
            korean_title=korean_title,
            overview=overview,
            poster_path=series_data.get("poster_path", ""),
            backdrop_path=series_data.get("backdrop_path", ""),
            first_air_date=first_air_date,
            last_air_date=last_air_date,
            status=status,
            vote_average=vote_average,
            vote_count=vote_count,
            popularity=popularity,
            genres=genres,
            networks=networks,
            number_of_seasons=number_of_seasons,
            number_of_episodes=number_of_episodes,
            raw_data=series_data,
        )

        logger.debug(
            "Extracted and normalized metadata for: %s (TMDB ID: %d)",
            tmdb_anime.display_title,
            tmdb_anime.tmdb_id,
        )

        return tmdb_anime

    def _normalize_tmdb_id(self, tmdb_id: Any) -> int:
        """Normalize TMDB ID to integer."""
        try:
            return int(tmdb_id) if tmdb_id is not None else 0
        except (ValueError, TypeError):
            logger.warning("Invalid TMDB ID: %s", tmdb_id)
            return 0

    def _parse_date(self, date_str: Any, field_name: str) -> datetime | None:
        """Parse and validate date string."""
        if not date_str:
            return None

        try:
            if isinstance(date_str, str):
                # Try different date formats
                for date_format in ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"]:
                    try:
                        return datetime.strptime(date_str, date_format)
                    except ValueError:
                        continue
                logger.warning("Invalid %s format: %s", field_name, date_str)
                return None
            elif isinstance(date_str, datetime):
                return date_str
            else:
                logger.warning("Unexpected %s type: %s", field_name, type(date_str))
                return None
        except Exception as e:
            logger.error("Error parsing %s: %s", field_name, str(e))
            return None

    def _extract_and_normalize_genres(self, genres_data: list[dict[str, Any]]) -> list[str]:
        """Extract and normalize genre names."""
        genres = []
        for genre in genres_data:
            if isinstance(genre, dict) and genre.get("name"):
                # Normalize genre name
                genre_name = genre["name"].strip()
                if genre_name and genre_name not in genres:  # Avoid duplicates
                    genres.append(genre_name)
        return genres

    def _extract_and_normalize_networks(self, networks_data: list[dict[str, Any]]) -> list[str]:
        """Extract and normalize network names."""
        networks = []
        for network in networks_data:
            if isinstance(network, dict) and network.get("name"):
                # Normalize network name
                network_name = network["name"].strip()
                if network_name and network_name not in networks:  # Avoid duplicates
                    networks.append(network_name)
        return networks

    def _normalize_title(self, title: str) -> str:
        """Normalize title text."""
        if not title:
            return ""

        # Remove extra whitespace and normalize
        title = " ".join(title.strip().split())

        # Remove common unwanted characters but preserve Korean/Japanese characters
        # This is a basic normalization - more complex rules can be added
        return title

    def _normalize_overview(self, overview: str) -> str:
        """Normalize overview text."""
        if not overview:
            return ""

        # Remove extra whitespace and normalize
        overview = " ".join(overview.strip().split())

        # Truncate if too long (optional - can be configured)
        max_length = 2000  # TMDB typically has longer overviews
        if len(overview) > max_length:
            overview = overview[:max_length].rsplit(" ", 1)[0] + "..."

        return overview

    def _normalize_status(self, status: str) -> str:
        """Normalize series status."""
        if not status:
            return ""

        status = status.strip().lower()

        # Map common status variations to standard values
        status_mapping = {
            "returning series": "Returning Series",
            "ended": "Ended",
            "canceled": "Canceled",
            "cancelled": "Canceled",
            "in production": "In Production",
            "planned": "Planned",
        }

        return status_mapping.get(status, status.title())

    def _normalize_rating(self, rating: Any) -> float:
        """Normalize rating to 0-10 scale."""
        try:
            rating = float(rating)
            # Ensure rating is within valid range
            return max(0.0, min(10.0, rating))  # type: ignore[no-any-return]
        except (ValueError, TypeError):
            return 0.0

    def _normalize_vote_count(self, count: Any) -> int:
        """Normalize vote count to non-negative integer."""
        try:
            count = int(count)
            return max(0, count)  # type: ignore[no-any-return]
        except (ValueError, TypeError):
            return 0

    def _normalize_popularity(self, popularity: Any) -> float:
        """Normalize popularity score."""
        try:
            popularity = float(popularity)
            return max(0.0, popularity)  # type: ignore[no-any-return]
        except (ValueError, TypeError):
            return 0.0

    def _normalize_count(self, count: Any) -> int:
        """Normalize season/episode count to non-negative integer."""
        try:
            count = int(count)
            return max(0, count)  # type: ignore[no-any-return]
        except (ValueError, TypeError):
            return 0

    def search_and_get_metadata(
        self, query: str, language: str | None = None, similarity_threshold: float = 0.7
    ) -> TMDBAnime | None:
        """Search for a series and retrieve its metadata in one operation with improved accuracy.

        Args:
            query: Search query (anime title)
            language: Language code for search and details
            similarity_threshold: Minimum similarity threshold for matching (0.0 to 1.0)

        Returns:
            TMDBAnime object with metadata, or None if not found

        Raises:
            TMDBRateLimitError: When rate limited
            TMDBAPIError: When API errors occur
        """
        logger.info(
            "Searching and retrieving metadata for: '%s' (threshold: %.2f)",
            query,
            similarity_threshold,
        )

        # Search for the series
        search_results = self.search_tv_series(query, language)

        if not search_results:
            logger.info("No search results found for: '%s'", query)
            return None

        # Find the best matching result using similarity scoring
        best_match = self._find_best_match(query, search_results, similarity_threshold)

        if not best_match:
            logger.info(
                "No good match found for: '%s' (threshold: %.2f)", query, similarity_threshold
            )
            return None

        series_id = best_match.get("id")

        if not series_id:
            logger.warning("No ID found in best match for: '%s'", query)
            return None

        # Get detailed information for the best match
        series_details = self.get_tv_series_details(series_id, language)

        # Extract and return metadata
        return self.extract_metadata(series_details)

    def set_cache_only_mode(self, enabled: bool) -> None:
        """Enable or disable cache-only mode.

        Args:
            enabled: Whether to enable cache-only mode
        """
        self.config.cache_only_mode = enabled
        if enabled:
            logger.warning("Cache-only mode enabled - no API requests will be made")
        else:
            logger.info("Cache-only mode disabled - API requests will be made")

    def get_cache_info(self) -> dict[str, Any]:
        """Get detailed cache information including hit rates and usage statistics.

        Returns:
            Dictionary containing cache statistics and information
        """
        cache_stats = self.get_cache_stats()

        # Calculate cache hit rate if we have statistics
        hit_rate = 0.0
        if hasattr(self, "_cache_hits") and hasattr(self, "_cache_misses"):
            total_cache_requests = self._cache_hits + self._cache_misses
            if total_cache_requests > 0:
                hit_rate = self._cache_hits / total_cache_requests

        return {
            **cache_stats,
            "cache_hit_rate": hit_rate,
            "cache_keys": list(self._cache.keys()),
            "cache_size_bytes": self._estimate_cache_size(),
            "oldest_entry": self._get_oldest_cache_entry(),
            "newest_entry": self._get_newest_cache_entry(),
        }

    def _estimate_cache_size(self) -> int:
        """Estimate cache size in bytes."""
        import sys

        try:
            return sys.getsizeof(self._cache)
        except Exception:
            return 0

    def _get_oldest_cache_entry(self) -> str | None:
        """Get the oldest cache entry timestamp."""
        if not self._cache:
            return None

        # This is a simplified implementation
        # In a real implementation, you might want to track timestamps
        return "N/A"

    def _get_newest_cache_entry(self) -> str | None:
        """Get the newest cache entry timestamp."""
        if not self._cache:
            return None

        # This is a simplified implementation
        # In a real implementation, you might want to track timestamps
        return "N/A"

    def clear_cache(self) -> None:
        """Clear the internal cache."""
        self._cache.clear()
        logger.info("TMDB client cache cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self._cache),
            "rate_limited": self._is_rate_limited(),
            "rate_limited_until": self._rate_limited_until,
            "cache_only_mode": self.config.cache_only_mode,
        }

    def get_retry_stats(self) -> dict[str, Any]:
        """Get retry and error statistics."""
        stats = self._retry_stats.copy()

        # Calculate success rate
        if stats["total_requests"] > 0:
            stats["success_rate"] = int(stats["successful_requests"] / stats["total_requests"])
        else:
            stats["success_rate"] = 0

        # Calculate average retry attempts per request
        if stats["total_requests"] > 0:
            stats["avg_retry_attempts"] = int(stats["retry_attempts"] / stats["total_requests"])
        else:
            stats["avg_retry_attempts"] = 0

        return stats

    def reset_retry_stats(self) -> None:
        """Reset retry statistics."""
        self._retry_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retry_attempts": 0,
            "rate_limit_hits": 0,
            "server_errors": 0,
            "network_errors": 0,
            "client_errors": 0,
        }
        logger.info("Retry statistics reset")


def create_tmdb_client() -> TMDBClient:
    """Create a TMDB client using configuration from the config manager.

    Returns:
        Configured TMDBClient instance

    Raises:
        TMDBError: If API key is not configured
    """
    config_manager = get_config_manager()

    # Get API key from configuration
    api_key = config_manager.get_tmdb_api_key()
    if not api_key:
        raise TMDBError("TMDB API key not configured. Please set it in the configuration.")

    # Get language setting
    language = config_manager.get_tmdb_language()

    # Create configuration
    config = TMDBConfig(api_key=api_key, language=language, fallback_language="en-US")

    logger.info("Creating TMDB client with language: %s", language)
    return TMDBClient(config)


def create_tmdb_client_with_config(
    api_key: str, language: str = "ko-KR", fallback_language: str = "en-US"
) -> TMDBClient:
    """Create a TMDB client with explicit configuration.

    Args:
        api_key: TMDB API key
        language: Primary language for API requests
        fallback_language: Fallback language if primary language fails

    Returns:
        Configured TMDBClient instance
    """
    config = TMDBConfig(api_key=api_key, language=language, fallback_language=fallback_language)

    return TMDBClient(config)
