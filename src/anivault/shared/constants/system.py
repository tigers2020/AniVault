"""
System Configuration Constants

This module contains all constants related to system configuration,
timeouts, limits, and general application settings.
"""

from typing import ClassVar

# =============================================================================
# BASE CONSTANTS (Foundation values used by other constants)
# =============================================================================

# Base file size unit (1KB)
BASE_FILE_SIZE = 1024  # 1KB in bytes

# Base time units
BASE_SECOND = 1
BASE_MINUTE = 60 * BASE_SECOND
BASE_HOUR = 60 * BASE_MINUTE

# =============================================================================
# APPLICATION METADATA
# =============================================================================


class Application:
    """Application metadata constants."""

    NAME = "AniVault"
    VERSION = "0.1.0"
    DESCRIPTION = "Anime Collection Management System with TMDB Integration"


# =============================================================================
# FILE AND PATH CONFIGURATION
# =============================================================================


class FileSystem:
    """File system related constants."""

    # Base file sizes
    MIN_FILE_SIZE = BASE_FILE_SIZE  # 1KB
    MAX_FILE_SIZE = BASE_FILE_SIZE**3  # 1GB

    # Path limits
    MAX_PATH_LENGTH = 4096
    MAX_FILENAME_LENGTH = 255

    # Directory names
    LOG_DIRECTORY = "logs"
    CONFIG_DIRECTORY = "config"
    CACHE_BACKEND = "memory"
    HOME_DIR = ".anivault"
    CACHE_DIRECTORY = "cache"
    OUTPUT_DIRECTORY = "output"
    RESULTS_DIRECTORY = "results"

    # Exclusion patterns
    EXCLUDED_DIRECTORY_PATTERNS: ClassVar[list[str]] = [
        "__pycache__",
        ".git",
        ".svn",
        ".hg",
        "node_modules",
        ".vscode",
        ".idea",
        "venv",
        "env",
        ".env",
    ]
    EXCLUDED_FILENAME_PATTERNS: ClassVar[list[str]] = [
        "*.tmp",
        "*.temp",
        "*.log",
        "*.cache",
        "*.bak",
        "*.swp",
        "*.swo",
        "*.orig",
        "*.rej",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.so",
        "*.dll",
        "*.exe",
    ]

    # Media file extensions
    VIDEO_EXTENSIONS: ClassVar[list[str]] = [
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".m4v",
        ".webm",
        ".m2ts",
        ".ts",
    ]

    # CLI default video extensions (subset for CLI commands)
    CLI_VIDEO_EXTENSIONS: ClassVar[list[str]] = [
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
    ]
    SUBTITLE_EXTENSIONS: ClassVar[list[str]] = [
        ".srt",
        ".ass",
        ".ssa",
        ".sub",
        ".idx",
        ".vtt",
        ".smi",
        ".sami",
        ".mks",
        ".sup",
        ".pgs",
        ".dvb",
    ]
    SUPPORTED_VIDEO_EXTENSIONS: ClassVar[list[str]] = (
        VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS
    )
    SUPPORTED_VIDEO_EXTENSIONS_MATCH: ClassVar[list[str]] = (
        VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS
    )
    SUPPORTED_VIDEO_EXTENSIONS_ORGANIZE: ClassVar[list[str]] = (
        VIDEO_EXTENSIONS + SUBTITLE_EXTENSIONS
    )

    # File patterns
    LOG_FILE_PATTERN = "*.log"
    CACHE_FILE_PATTERN = "*.cache"
    CONFIG_FILE_PATTERN = "*.toml"
    JSON_FILE_PATTERN = "*.json"
    ADDITIONAL_VIDEO_FORMATS: ClassVar[list[str]] = [
        ".m2ts",
        ".ts",
        ".mts",
        ".m2v",
        ".m1v",
        ".mpg",
        ".mpeg",
        ".mpe",
        ".mpv",
        ".mp2",
        ".mp3",
        ".mpa",
        ".mpe",
        ".mpg",
        ".mpeg",
        ".m1v",
        ".m2v",
        ".mpv",
        ".mp2",
        ".mp3",
        ".mpa",
    ]


class Encoding:
    """Text encoding constants."""

    DEFAULT = "utf-8"
    FALLBACK = "cp1252"
    UTF8_BOM = "utf-8-sig"


# =============================================================================
# CONFIGURATION SYSTEM
# =============================================================================


class Config:
    """Configuration system constants."""

    ENV_PREFIX = "ANIVAULT_"
    ENV_DELIMITER = "__"
    DEFAULT_DIR = FileSystem.HOME_DIR
    DEFAULT_FILENAME = "anivault.toml"


# =============================================================================
# TIMEOUT CONFIGURATION
# =============================================================================


class Timeout:
    """Timeout configuration constants."""

    # Base timeouts
    SHORT = 30 * BASE_SECOND  # 30 seconds
    DEFAULT = 5 * BASE_MINUTE  # 5 minutes
    LONG = 10 * BASE_MINUTE  # 10 minutes

    # Specific service timeouts
    TMDB = 30 * BASE_SECOND  # TMDB API timeout
    PIPELINE_SENTINEL = 30.0  # Pipeline sentinel timeout
    PIPELINE_SHUTDOWN = 1.0  # Pipeline shutdown timeout
    PIPELINE_QUEUE = 1.0  # Pipeline queue timeout
    DEFAULT_REQUEST_TIMEOUT = 30 * BASE_SECOND  # 30 seconds


# =============================================================================
# BATCH AND PROCESSING
# =============================================================================


class Batch:
    """Batch processing constants."""

    DEFAULT_SIZE = 50
    MIN_SIZE = 1
    MAX_SIZE = 1000
    LARGE_SIZE = 100
    PARALLEL_THRESHOLD = 1000


class Process:
    """Process configuration constants."""

    DEFAULT_PRIORITY = "normal"
    MAX_CONCURRENT = 16
    DEFAULT_WORKERS = 4


# =============================================================================
# MEMORY CONFIGURATION
# =============================================================================


class Memory:
    """Memory configuration constants."""

    # Base memory limits
    DEFAULT_LIMIT = FileSystem.MAX_FILE_SIZE  # 1GB
    WARNING_THRESHOLD = 512 * BASE_FILE_SIZE**2  # 512MB
    DEFAULT_LIMIT_MB = 1024  # 1GB in MB
    DEFAULT_LIMIT_STRING = "2GB"

    # CPU limits
    DEFAULT_CPU_LIMIT = 4


# =============================================================================
# CACHE CONFIGURATION
# =============================================================================


class Cache:
    """Cache configuration constants."""

    TTL = 3600  # 1 hour in seconds
    MAX_SIZE = 1000
    TYPE_SEARCH = "search"
    TYPE_DETAILS = "details"

    # Cache TTL values (in seconds)
    DEFAULT_TTL = 3600  # 1 hour
    SEARCH_TTL = 1800  # 30 minutes
    DETAILS_TTL = 3600  # 1 hour
    PARSER_CACHE_TTL = 86400  # 24 hours

    # Legacy constants for backward compatibility
    CACHE_TYPE_DETAILS = TYPE_DETAILS
    CACHE_TYPE_SEARCH = TYPE_SEARCH


# =============================================================================
# STATUS CONSTANTS
# =============================================================================


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


# =============================================================================
# MEDIA AND LANGUAGE
# =============================================================================


class MediaType:
    """Media type constants."""

    TV = "tv"
    MOVIE = "movie"
    ANIME = "anime"


class FolderDefaults:
    """Default folder organization settings."""

    # Default media type for organization
    DEFAULT_MEDIA_TYPE = MediaType.TV

    # Default organization flags
    ORGANIZE_BY_RESOLUTION = False
    ORGANIZE_BY_YEAR = False

    # Default folder structure template
    DEFAULT_STRUCTURE = "season_##/korean_title/original_filename"


class Language:
    """Language code constants."""

    ENGLISH = "en"
    KOREAN = "ko"


# =============================================================================
# JSON DATA KEYS
# =============================================================================


class JsonKeys:
    """JSON data structure keys."""

    ENTRIES = "entries"
    METADATA = "metadata"
    VERSION = "version"
    DESCRIPTION = "description"
    TOTAL_ENTRIES = "total_entries"


# =============================================================================
# BOOLEAN VALUES
# =============================================================================


class Boolean:
    """Boolean string representations."""

    TRUE = "true"
    FALSE = "false"


# =============================================================================
# ERROR HANDLING
# =============================================================================


class ErrorHandling:
    """Error handling configuration."""

    MAX_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 1.0
    MAX_RETRY_DELAY = 60.0
    DEFAULT_RETRY_ATTEMPTS = 3


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


# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================


class Performance:
    """Performance monitoring constants."""

    SAMPLE_RATE = 0.1  # 10% sampling
    REPORT_INTERVAL = 60  # 60 seconds


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================


class Logging:
    """Logging configuration constants."""

    MAX_BYTES = 10485760  # 10MB
    BACKUP_COUNT = 5
    MIN_FILE_SIZE_MB = 50
    DEFAULT_FILE_PATH = "logs/anivault.log"
    DEFAULT_PROFILING_FILE_PATH = "logs/profiling.prof"
    FILE_EXTENSION = ".log"
    ORGANIZE_LOG_PREFIX = "organize"


# =============================================================================
# PIPELINE CONFIGURATION
# =============================================================================


class Pipeline:
    """Pipeline configuration constants."""

    QUEUE_SIZE = 1000
    SENTINEL = object()  # Unique sentinel object


# =============================================================================
# CLI CONSTANTS
# =============================================================================


class CLI:
    """CLI related constants."""

    INDENT_SIZE = 2

    # Message templates
    INFO_COMMAND_STARTED = "Starting {command} command..."
    INFO_COMMAND_COMPLETED = "Completed {command} command"
    SUCCESS_RESULTS_SAVED = "Results saved to: {path}"

    # Error messages
    ERROR_SCAN_FAILED = "Scan command failed: {error}"
    ERROR_ORGANIZE_FAILED = "Organize command failed: {error}"
    ERROR_MATCH_FAILED = "Match command failed: {error}"
    ERROR_VERIFY_FAILED = "Verify command failed: {error}"
    ERROR_ROLLBACK_FAILED = "Rollback command failed: {error}"
    ERROR_TMDB_CONNECTIVITY_FAILED = "TMDB API connectivity failed: {error}"
    ERROR_VERIFICATION_FAILED = "Verification failed: {error}"
