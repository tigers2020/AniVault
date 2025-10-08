"""
API Field Constants

This module contains all string constants used as keys for API request payloads
and response parsing in the services module.
"""


class APIFields:
    """API field key constants for request/response parsing."""

    # Common fields
    TITLE = "title"
    ID = "id"
    NAME = "name"
    DATA = "data"
    NODE = "node"

    # TMDB specific fields
    TMDB_ID = "tmdb_id"
    EXTERNAL_IDS = "external_ids"
    IMDB_ID = "imdb_id"
    TVDB_ID = "tvdb_id"

    # AniList specific fields
    ANILIST_ID = "anilist_id"
    AVERAGE_SCORE = "averageScore"
    ROMAJI = "romaji"
    ENGLISH = "english"
    NATIVE = "native"

    # MyAnimeList specific fields
    MAL_ID = "mal_id"
    SCORE = "score"
    RANK = "rank"

    # Media type fields
    MEDIA_TYPE = "media_type"
    TV = "tv"
    MOVIE = "movie"

    # Search result fields
    RESULTS = "results"
    TOTAL_PAGES = "total_pages"
    TOTAL_RESULTS = "total_results"
    PAGE = "page"

    # Authentication fields
    ACCESS_TOKEN = "access_token"  # noqa: S105
    TOKEN_TYPE = "token_type"  # noqa: S105
    EXPIRES_IN = "expires_in"
    REFRESH_TOKEN = "refresh_token"  # noqa: S105

    # Error fields
    ERROR = "error"
    ERROR_MESSAGE = "error_message"
    STATUS_CODE = "status_code"

    # Enrichment status fields
    ENRICHMENT_STATUS_PENDING = "pending"
    ENRICHMENT_STATUS_SUCCESS = "success"
    ENRICHMENT_STATUS_FAILED = "failed"
    ENRICHMENT_STATUS_SKIPPED = "skipped"

    # Cache type fields
    CACHE_TYPE_SEARCH = "search"
    CACHE_TYPE_DETAILS = "details"
