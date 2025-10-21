"""Scan field constants for type safety and consistency."""

# Metadata field names
class ScanFields:
    """Constants for scan metadata field names."""

    # Core file fields
    TITLE = "title"
    FILE_PATH = "file_path"
    FILE_NAME = "file_name"
    FILE_TYPE = "file_type"
    YEAR = "year"
    SEASON = "season"
    EPISODE = "episode"

    # Metadata fields
    GENRES = "genres"
    OVERVIEW = "overview"
    POSTER_PATH = "poster_path"
    VOTE_AVERAGE = "vote_average"
    TMDB_ID = "tmdb_id"
    MEDIA_TYPE = "media_type"


# UI message constants
class ScanMessages:
    """Constants for scan UI messages."""

    SCAN_COMPLETED = "✅ File scanning completed!"
    NAME_FIELD = "name"
    VOTE_AVERAGE_FIELD = "vote_average"


# Color constants for UI
class ScanColors:
    """Constants for scan UI colors."""

    BLUE = "blue"
    YELLOW = "yellow"
