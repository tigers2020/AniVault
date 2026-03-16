"""
TMDB API Error Messages (S5: from shared.constants.tmdb_messages).
"""


class TMDBErrorMessages:
    """TMDB API error message constants."""

    AUTHENTICATION_FAILED = "TMDB API authentication failed"
    ACCESS_FORBIDDEN = "TMDB API access forbidden"
    RATE_LIMIT_EXCEEDED = "TMDB API rate limit exceeded"
    REQUEST_FAILED = "TMDB API request failed: {status_code}"
    CLIENT_ERROR = "TMDB API client error: {status_code}"
    SERVER_ERROR = "TMDB API server error: {status_code}"
    TIMEOUT = "TMDB API request timeout"
    CONNECTION_FAILED = "TMDB API connection failed"
    NETWORK_ERROR = "TMDB API network error: {error}"
    SEARCH_FAILED = "TMDB search failed: {error}"
    NO_RESULTS = "No results found for query: {query}"
    DETAILS_FAILED = "Failed to get TMDB details: {error}"
    SEASON_DETAILS_FAILED = "Failed to get season details: {error}"


class TMDBOperationNames:
    """TMDB operation name constants for logging."""

    SEARCH_TV = "search_tv"
    SEARCH_MOVIE = "search_movie"
    GET_TV_DETAILS = "get_tv_details"
    GET_MOVIE_DETAILS = "get_movie_details"
    GET_SEASON_DETAILS = "get_season_details"
