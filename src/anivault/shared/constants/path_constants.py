"""Path building constants for type safety and consistency."""


class PathConstants:
    """Constants for path building."""

    # Default values
    UNKNOWN_SERIES = "Unknown Series"
    UNKNOWN = "unknown"

    # Year validation
    MIN_YEAR = 1900
    MAX_YEAR = 2100

    # Resolution thresholds
    RESOLUTION_THRESHOLD = 50
    HD_WIDTH = 1920
    HD_HEIGHT = 1080
    HD_LABEL = "1080P"
    SD_WIDTH = 1280
    SD_HEIGHT = 720
    SD_LABEL = "720P"
    LD_WIDTH = 854
    LD_HEIGHT = 480
    LD_LABEL = "480P"

    # File extensions
    FILE_EXTENSION_SEPARATOR = " ."


class OrganizerConstants:
    """Constants for organizer."""

    # Default media type
    DEFAULT_MEDIA_TYPE = "anime"

    # Timestamp format
    TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

    # Match result key
    MATCH_RESULT_KEY = "match_result"
