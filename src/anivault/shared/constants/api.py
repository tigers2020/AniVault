"""
API Configuration Constants

This module contains all constants related to API configuration,
rate limiting, and external service interactions.
"""

from typing import ClassVar

from .system import BASE_SECOND


class APIConfig:
    """Base API configuration constants."""

    # Base timeouts
    DEFAULT_REQUEST_TIMEOUT = 300 * BASE_SECOND  # 5 minutes
    DEFAULT_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 1.0 * BASE_SECOND

    # Rate limiting
    DEFAULT_RATE_LIMIT = 20  # requests per minute
    DEFAULT_CONCURRENT_REQUESTS = 4

    # Token bucket configuration
    DEFAULT_TOKEN_BUCKET_CAPACITY = 20
    DEFAULT_TOKEN_REFILL_RATE = 20  # tokens per minute

    # Response configuration
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 1000


class TMDBConfig(APIConfig):
    """TMDB API specific configuration."""

    # TMDB API endpoints
    BASE_URL = "https://api.themoviedb.org/3"
    SEARCH_TV_ENDPOINT = "/search/tv"
    SEARCH_MOVIE_ENDPOINT = "/search/movie"
    TV_DETAILS_ENDPOINT = "/tv/{tv_id}"
    MOVIE_DETAILS_ENDPOINT = "/movie/{movie_id}"

    # TMDB specific rate limits
    RATE_LIMIT_RPS = 35.0  # requests per second
    RATE_LIMIT_DELAY = 0.25 * BASE_SECOND  # delay between requests

    # TMDB specific timeouts
    REQUEST_TIMEOUT = 30 * BASE_SECOND  # 30 seconds
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1.0 * BASE_SECOND

    # TMDB request headers
    HEADERS: ClassVar[dict[str, str]] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # TMDB query parameters
    DEFAULT_LANGUAGE = "en-US"
    DEFAULT_PAGE = 1
    DEFAULT_INCLUDE_ADULT = False


class CacheConfig:
    """Cache configuration constants."""

    # Cache TTL
    DEFAULT_TTL = 3600 * BASE_SECOND  # 1 hour
    SEARCH_TTL = 1800 * BASE_SECOND  # 30 minutes
    DETAILS_TTL = 3600 * BASE_SECOND  # 1 hour

    # Cache size limits
    DEFAULT_SIZE_LIMIT = 1000
    MAX_SIZE_LIMIT = 10000

    # Cache types
    TYPE_SEARCH = "search"
    TYPE_DETAILS = "details"
