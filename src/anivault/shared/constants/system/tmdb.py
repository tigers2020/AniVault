"""TMDB-related constants."""


class TMDBErrorHandling:
    """TMDB specific error handling."""

    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1.0
    RATE_LIMIT_DELAY = 0.25
    RATE_LIMIT_RPS = 35
    DEFAULT_RATE_LIMIT = 35


class TMDB:
    """TMDB API configuration constants."""

    API_BASE_URL = "https://api.themoviedb.org/3"
    API_KEY_ENV = "TMDB_API_KEY"
    DEFAULT_LANGUAGE = "en-US"
    DEFAULT_REGION = "US"


__all__ = ["TMDB", "TMDBErrorHandling"]
