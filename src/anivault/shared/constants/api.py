"""
API Configuration Constants

This module contains all constants related to API configuration,
rate limiting, and external service interactions.
"""

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

    # TMDB specific rate limits
    RATE_LIMIT_RPS = 35.0  # requests per second
    RATE_LIMIT_DELAY = 0.25 * BASE_SECOND  # delay between requests

    # TMDB specific timeouts
    REQUEST_TIMEOUT = 30 * BASE_SECOND  # 30 seconds
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1.0 * BASE_SECOND


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


# Backward compatibility aliases
DEFAULT_RATE_LIMIT = APIConfig.DEFAULT_RATE_LIMIT
DEFAULT_CONCURRENT_REQUESTS = APIConfig.DEFAULT_CONCURRENT_REQUESTS
DEFAULT_RETRY_ATTEMPTS = APIConfig.DEFAULT_RETRY_ATTEMPTS
DEFAULT_RETRY_DELAY = APIConfig.DEFAULT_RETRY_DELAY
DEFAULT_REQUEST_TIMEOUT = APIConfig.DEFAULT_REQUEST_TIMEOUT
DEFAULT_TOKEN_BUCKET_CAPACITY = APIConfig.DEFAULT_TOKEN_BUCKET_CAPACITY
DEFAULT_TOKEN_REFILL_RATE = APIConfig.DEFAULT_TOKEN_REFILL_RATE
DEFAULT_PAGE_SIZE = APIConfig.DEFAULT_PAGE_SIZE
MAX_PAGE_SIZE = APIConfig.MAX_PAGE_SIZE
TMDB_API_BASE_URL = TMDBConfig.BASE_URL
DEFAULT_TMDB_RATE_LIMIT_RPS = TMDBConfig.RATE_LIMIT_RPS
DEFAULT_CACHE_TTL = CacheConfig.DEFAULT_TTL
DEFAULT_CACHE_SIZE_LIMIT = CacheConfig.DEFAULT_SIZE_LIMIT
