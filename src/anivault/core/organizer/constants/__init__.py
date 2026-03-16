"""
Organizer and path building constants (S5: extracted from shared.constants.path_constants).
"""

# Year validation (aligned with validation_constants)
MIN_YEAR = 1900
MAX_YEAR = 2030


class PathConstants:
    """Constants for path building."""

    UNKNOWN_SERIES = "Unknown Series"
    UNKNOWN = "unknown"

    MIN_YEAR = MIN_YEAR
    MAX_YEAR = MAX_YEAR

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

    FILE_EXTENSION_SEPARATOR = " ."


class OrganizerConstants:
    """Constants for organizer."""

    DEFAULT_MEDIA_TYPE = "anime"
    TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
    MATCH_RESULT_KEY = "match_result"


__all__ = [
    "OrganizerConstants",
    "PathConstants",
]
