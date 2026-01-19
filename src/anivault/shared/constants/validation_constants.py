"""Validation constants for AniVault.

This module defines constants used for validation across the application,
replacing magic values with named constants for better maintainability.
"""

# Year validation constants
MIN_YEAR = 1900
MAX_YEAR = 2030  # Conservative future limit

# Vote average validation constants
MIN_VOTE_AVERAGE = 0.0
MAX_VOTE_AVERAGE = 10.0

# Resolution validation constants
MIN_RESOLUTION_WIDTH = 854
MIN_RESOLUTION_HEIGHT = 480
HD_WIDTH = 1280
HD_HEIGHT = 720
FHD_WIDTH = 1920
FHD_HEIGHT = 1080

# Scoring constants
MAX_SCORE = 100.0
DEFAULT_CONFIDENCE_THRESHOLD = 0.7

# Media type constants
MEDIA_TYPE_TV = "tv"
MEDIA_TYPE_MOVIE = "movie"

# Parser constants
PARSER_ANIME_TITLE = "anime_title"
PARSER_EPISODE_NUMBER = "episode_number"
PARSER_ANIME_SEASON = "anime_season"
PARSER_VIDEO_RESOLUTION = "video_resolution"
PARSER_VIDEO_TERM = "video_term"
PARSER_AUDIO_TERM = "audio_term"
PARSER_RAW_FILENAME = "raw_filename"


class AnitopyFieldNames:
    """Anitopy parser field name constants."""

    RELEASE_GROUP = "release_group"
    SOURCE = "source"
    ANIME_YEAR = "anime_year"
    YEAR = "year"
    FILE_EXTENSION = "file_extension"
    TITLE = "title"
    SERIES_NAME = "series_name"
    SHOW_NAME = "show_name"


# File processing constants
FILE_TYPE_UNKNOWN = "unknown"
FILE_TYPE_FALLBACK = "fallback"
FILE_INDEX = "file_index"
RESULT_TYPE = "result_type"
BATCH_PROCESS_ITEM = "batch_process_item"
ORIGINAL_ERROR = "original_error"

# Error categories
ERROR_NETWORK = "network"
ERROR_DATA_PROCESSING = "data_processing"
ERROR_UNEXPECTED = "unexpected"

# TMDB constants
TMDB_CACHE_DB = "tmdb_cache.db"
TMDB_LANGUAGE_KO = "ko-KR"
TMDB_MEDIA_TYPE_MOVIE = "movie"
TMDB_MEDIA_TYPE_TV = "tv"

# Cache mode constants
CACHE_MODE_JSON_ONLY = "json-only"
CACHE_MODE_DB_ONLY = "db-only"
CACHE_MODE_HYBRID = "hybrid"
CACHE_TYPE_SQLITE = "SQLite"
CACHE_TYPE_HYBRID = "Hybrid"

# Scoring constants
SCORE_HIGH = "high"
SCORE_MEDIUM = "medium"
SCORE_VERY_LOW = "very_low"

# Media type constants
MEDIA_TYPE_UNKNOWN = "unknown"
MEDIA_TYPE_FALLBACK = "fallback"

# GUI constants
DIALOG_WIDTH = 600
DIALOG_HEIGHT = 400
PROGRESS_MAX = 100
DIALOG_TITLE = "dialogTitle"
STATUS_LABEL = "statusLabel"
LOG_HEADER = "logHeader"
LOG_OUTPUT = "logOutput"
CANCEL_BUTTON = "cancelButton"
DESTINATION = "destination"
CLOSE_BUTTON = "closeButton"

# Cache constants
CACHE_BATCH_SIZE = 50
CACHE_HASH_SIZE = 64

# Error messages
EMPTY_TITLE_ERROR = "title cannot be empty"
EMPTY_FILE_TYPE_ERROR = "file_type cannot be empty"
EMPTY_SERIES_TITLE_ERROR = "series_title cannot be empty"

# Year validation error message template
YEAR_RANGE_ERROR_TEMPLATE = f"year must be between {MIN_YEAR} and {MAX_YEAR}, got {{year}}"

# Season validation error message template
SEASON_NEGATIVE_ERROR_TEMPLATE = "season must be non-negative, got {season}"

# Episode validation error message template
EPISODE_NEGATIVE_ERROR_TEMPLATE = "episode must be non-negative, got {episode}"

# Vote average validation error message template
VOTE_AVERAGE_RANGE_ERROR_TEMPLATE = (
    f"vote_average must be between {MIN_VOTE_AVERAGE} and {MAX_VOTE_AVERAGE}, " f"got {{vote_average}}"  # pylint: disable=line-too-long
)
