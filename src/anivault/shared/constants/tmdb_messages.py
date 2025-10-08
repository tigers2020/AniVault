"""
TMDB API Error Messages Constants

This module contains all constants for TMDB API error messages,
ensuring consistency in error handling and making it easier to
maintain error messages across the application.
"""


class TMDBErrorMessages:
    """TMDB API error message constants."""

    # Authentication errors
    AUTHENTICATION_FAILED = "TMDB API authentication failed"
    ACCESS_FORBIDDEN = "TMDB API access forbidden"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "TMDB API rate limit exceeded"

    # Client errors (4xx)
    REQUEST_FAILED = "TMDB API request failed: {status_code}"
    CLIENT_ERROR = "TMDB API client error: {status_code}"

    # Server errors (5xx)
    SERVER_ERROR = "TMDB API server error: {status_code}"

    # Network errors
    TIMEOUT = "TMDB API request timeout"
    CONNECTION_FAILED = "TMDB API connection failed"
    NETWORK_ERROR = "TMDB API network error: {error}"

    # Search errors
    SEARCH_FAILED = "TMDB search failed: {error}"
    NO_RESULTS = "No results found for query: {query}"

    # Details errors
    DETAILS_FAILED = "Failed to get TMDB details: {error}"
    SEASON_DETAILS_FAILED = "Failed to get season details: {error}"


class TMDBOperationNames:
    """TMDB operation name constants for logging."""

    SEARCH_TV = "search_tv"
    SEARCH_MOVIE = "search_movie"
    GET_TV_DETAILS = "get_tv_details"
    GET_MOVIE_DETAILS = "get_movie_details"
    GET_SEASON_DETAILS = "get_season_details"


# Export all classes
__all__ = [
    "TMDBErrorMessages",
    "TMDBOperationNames",
]

