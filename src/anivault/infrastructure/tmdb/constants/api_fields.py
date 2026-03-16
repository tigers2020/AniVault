"""
API Field Constants (S5: from shared.constants.api_fields).

String constants for API request payloads and response parsing.
"""


class APIFields:
    """API field key constants for request/response parsing."""

    TITLE = "title"
    ID = "id"
    NAME = "name"
    DATA = "data"
    NODE = "node"
    TMDB_ID = "tmdb_id"
    EXTERNAL_IDS = "external_ids"
    IMDB_ID = "imdb_id"
    TVDB_ID = "tvdb_id"
    ANILIST_ID = "anilist_id"
    AVERAGE_SCORE = "averageScore"
    ROMAJI = "romaji"
    ENGLISH = "english"
    NATIVE = "native"
    MAL_ID = "mal_id"
    SCORE = "score"
    RANK = "rank"
    MEDIA_TYPE = "media_type"
    TV = "tv"
    MOVIE = "movie"
    RESULTS = "results"
    TOTAL_PAGES = "total_pages"
    TOTAL_RESULTS = "total_results"
    PAGE = "page"
    ACCESS_TOKEN = "access_token"  # noqa: S105
    TOKEN_TYPE = "token_type"  # noqa: S105
    EXPIRES_IN = "expires_in"
    REFRESH_TOKEN = "refresh_token"  # noqa: S105
    ERROR = "error"
    ERROR_MESSAGE = "error_message"
    STATUS_CODE = "status_code"
    ENRICHMENT_STATUS_PENDING = "pending"
    ENRICHMENT_STATUS_SUCCESS = "success"
    ENRICHMENT_STATUS_FAILED = "failed"
    ENRICHMENT_STATUS_SKIPPED = "skipped"
    CACHE_TYPE_SEARCH = "search"
    CACHE_TYPE_DETAILS = "details"
