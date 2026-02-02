"""Application metadata and global status constants."""

from __future__ import annotations

from .filesystem import FileSystem


class Application:
    """Application metadata constants."""

    NAME = "AniVault"
    VERSION = "0.1.0"
    DESCRIPTION = "Anime Collection Management System with TMDB Integration"


class Status:
    """Status constants for various operations."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class EnrichmentStatus:
    """Enrichment status constants."""

    PENDING = Status.PENDING
    SUCCESS = Status.SUCCESS
    FAILED = Status.FAILED
    SKIPPED = Status.SKIPPED


class MediaType:
    """Media type constants."""

    TV = "tv"
    MOVIE = "movie"
    ANIME = "anime"


class Boolean:
    """Boolean string representations."""

    TRUE = "true"
    FALSE = "false"


class Config:
    """Configuration system constants."""

    ENV_PREFIX = "ANIVAULT_"
    ENV_DELIMITER = "__"
    DEFAULT_DIR = FileSystem.HOME_DIR
    DEFAULT_FILENAME = "anivault.toml"


class FolderDefaults:
    """Default folder organization settings."""

    # Default media type for organization
    DEFAULT_MEDIA_TYPE = MediaType.TV

    # Default organization flags (deprecated - use ORGANIZE_PATH_TEMPLATE)
    ORGANIZE_BY_RESOLUTION = False
    ORGANIZE_BY_YEAR = False

    # Path template: {해상도}, {연도}, {제목}, {시즌}
    ORGANIZE_PATH_TEMPLATE = "{제목}/{시즌}"

    # Default folder structure template
    DEFAULT_STRUCTURE = "season_##/korean_title/original_filename"


class Language:
    """Language code constants."""

    ENGLISH = "en"
    KOREAN = "ko"


class JsonKeys:
    """JSON data structure keys."""

    ENTRIES = "entries"
    METADATA = "metadata"
    VERSION = "version"
    DESCRIPTION = "description"
    TOTAL_ENTRIES = "total_entries"


__all__ = [
    "Application",
    "Boolean",
    "Config",
    "EnrichmentStatus",
    "FolderDefaults",
    "JsonKeys",
    "Language",
    "MediaType",
    "Status",
]
