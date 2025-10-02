"""
API Configuration Constants

This module contains all constants related to API configuration,
rate limiting, and external service interactions.
"""

# TMDB API Configuration
DEFAULT_RATE_LIMIT = 20  # requests per minute
DEFAULT_CONCURRENT_REQUESTS = 4  # maximum concurrent API calls
DEFAULT_RETRY_ATTEMPTS = 3  # number of retry attempts for failed requests
DEFAULT_RETRY_DELAY = 1.0  # delay between retries in seconds
DEFAULT_REQUEST_TIMEOUT = 300  # request timeout in seconds

# Rate Limiter Configuration
DEFAULT_TOKEN_BUCKET_CAPACITY = 20  # initial token bucket capacity
DEFAULT_TOKEN_REFILL_RATE = 20  # tokens added per minute

# API Response Configuration
DEFAULT_PAGE_SIZE = 20  # default page size for API responses
MAX_PAGE_SIZE = 1000  # maximum allowed page size

# TMDB API Configuration
TMDB_API_BASE_URL = "https://api.themoviedb.org/3"  # TMDB API base URL
DEFAULT_TMDB_RATE_LIMIT_RPS = 35.0  # TMDB rate limit in requests per second

# Cache Configuration
DEFAULT_CACHE_TTL = 3600  # cache time-to-live in seconds (1 hour)
DEFAULT_CACHE_SIZE_LIMIT = 1000  # maximum number of cached items
