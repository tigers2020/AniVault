"""
System Configuration Constants

This module contains all constants related to system configuration,
timeouts, limits, and general application settings.
"""

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


class Encoding:
    """Text encoding constants."""

    DEFAULT = "utf-8"
    FALLBACK = "cp1252"


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


class TMDBErrorHandling:
    """TMDB specific error handling."""

    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1.0
    RATE_LIMIT_DELAY = 0.25
    RATE_LIMIT_RPS = 35.0


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


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

# Application aliases
APPLICATION_NAME = Application.NAME
APPLICATION_VERSION = Application.VERSION
APPLICATION_DESCRIPTION = Application.DESCRIPTION
DEFAULT_VERSION_STRING = Application.VERSION

# Configuration aliases
CONFIG_ENV_PREFIX = Config.ENV_PREFIX
CONFIG_ENV_DELIMITER = Config.ENV_DELIMITER
CONFIG_DEFAULT_DIR = Config.DEFAULT_DIR
CONFIG_DEFAULT_FILENAME = Config.DEFAULT_FILENAME

# Encoding aliases
DEFAULT_ENCODING = Encoding.DEFAULT
FALLBACK_ENCODING = Encoding.FALLBACK

# Timeout aliases
DEFAULT_TIMEOUT = Timeout.DEFAULT
SHORT_TIMEOUT = Timeout.SHORT
LONG_TIMEOUT = Timeout.LONG
DEFAULT_TMDB_TIMEOUT = Timeout.TMDB
PIPELINE_SENTINEL_TIMEOUT = Timeout.PIPELINE_SENTINEL
PIPELINE_SHUTDOWN_TIMEOUT = Timeout.PIPELINE_SHUTDOWN
PIPELINE_QUEUE_TIMEOUT = Timeout.PIPELINE_QUEUE

# File system aliases
MIN_FILE_SIZE = FileSystem.MIN_FILE_SIZE
MAX_FILE_SIZE = FileSystem.MAX_FILE_SIZE
MAX_PATH_LENGTH = FileSystem.MAX_PATH_LENGTH
MAX_FILENAME_LENGTH = FileSystem.MAX_FILENAME_LENGTH
DEFAULT_LOG_DIRECTORY = FileSystem.LOG_DIRECTORY
DEFAULT_PROFILING_DIRECTORY = FileSystem.LOG_DIRECTORY
DEFAULT_CONFIG_DIRECTORY = FileSystem.CONFIG_DIRECTORY
DEFAULT_CACHE_BACKEND = FileSystem.CACHE_BACKEND
ANIVAULT_HOME_DIR = FileSystem.HOME_DIR

# JSON keys aliases
JSON_ENTRIES_KEY = JsonKeys.ENTRIES
JSON_METADATA_KEY = JsonKeys.METADATA
JSON_VERSION_KEY = JsonKeys.VERSION
JSON_DESCRIPTION_KEY = JsonKeys.DESCRIPTION
JSON_TOTAL_ENTRIES_KEY = JsonKeys.TOTAL_ENTRIES

# Boolean aliases
BOOLEAN_TRUE_STRING = Boolean.TRUE
BOOLEAN_FALSE_STRING = Boolean.FALSE

# Memory aliases
DEFAULT_MEMORY_LIMIT = Memory.DEFAULT_LIMIT
MEMORY_WARNING_THRESHOLD = Memory.WARNING_THRESHOLD
DEFAULT_MEMORY_LIMIT_STRING = Memory.DEFAULT_LIMIT_STRING
DEFAULT_MEMORY_LIMIT_MB = Memory.DEFAULT_LIMIT_MB
DEFAULT_CPU_LIMIT = Memory.DEFAULT_CPU_LIMIT

# Batch aliases
DEFAULT_BATCH_SIZE = Batch.DEFAULT_SIZE
MIN_BATCH_SIZE = Batch.MIN_SIZE
MAX_BATCH_SIZE = Batch.MAX_SIZE
DEFAULT_BATCH_SIZE_LARGE = Batch.LARGE_SIZE
DEFAULT_PARALLEL_THRESHOLD = Batch.PARALLEL_THRESHOLD

# Process aliases
DEFAULT_PROCESS_PRIORITY = Process.DEFAULT_PRIORITY
MAX_CONCURRENT_PROCESSES = Process.MAX_CONCURRENT
DEFAULT_WORKERS = Process.DEFAULT_WORKERS

# Error handling aliases
MAX_RETRY_ATTEMPTS = ErrorHandling.MAX_RETRY_ATTEMPTS
DEFAULT_RETRY_DELAY = ErrorHandling.DEFAULT_RETRY_DELAY
MAX_RETRY_DELAY = ErrorHandling.MAX_RETRY_DELAY
DEFAULT_TMDB_RETRY_ATTEMPTS = TMDBErrorHandling.RETRY_ATTEMPTS
DEFAULT_TMDB_RETRY_DELAY = TMDBErrorHandling.RETRY_DELAY
DEFAULT_TMDB_RATE_LIMIT_DELAY = TMDBErrorHandling.RATE_LIMIT_DELAY
DEFAULT_TMDB_RATE_LIMIT_RPS = TMDBErrorHandling.RATE_LIMIT_RPS

# Performance aliases
PERFORMANCE_SAMPLE_RATE = Performance.SAMPLE_RATE
PERFORMANCE_REPORT_INTERVAL = Performance.REPORT_INTERVAL

# Logging aliases
DEFAULT_LOG_MAX_BYTES = Logging.MAX_BYTES
DEFAULT_LOG_BACKUP_COUNT = Logging.BACKUP_COUNT
DEFAULT_MIN_FILE_SIZE_MB = Logging.MIN_FILE_SIZE_MB

# Pipeline aliases
DEFAULT_QUEUE_SIZE = Pipeline.QUEUE_SIZE
SENTINEL = Pipeline.SENTINEL

# Cache aliases
DEFAULT_CACHE_TTL = Cache.TTL
DEFAULT_CACHE_MAX_SIZE = Cache.MAX_SIZE
CACHE_TYPE_SEARCH = Cache.TYPE_SEARCH
CACHE_TYPE_DETAILS = Cache.TYPE_DETAILS

# Status aliases
ENRICHMENT_STATUS_PENDING = EnrichmentStatus.PENDING
ENRICHMENT_STATUS_SUCCESS = EnrichmentStatus.SUCCESS
ENRICHMENT_STATUS_FAILED = EnrichmentStatus.FAILED
ENRICHMENT_STATUS_SKIPPED = EnrichmentStatus.SKIPPED

# Media type aliases
MEDIA_TYPE_TV = MediaType.TV
MEDIA_TYPE_MOVIE = MediaType.MOVIE

# Language aliases
LANGUAGE_ENGLISH = Language.ENGLISH
LANGUAGE_KOREAN = Language.KOREAN

# CLI aliases
CLI_INDENT_SIZE = CLI.INDENT_SIZE
CLI_INFO_COMMAND_STARTED = CLI.INFO_COMMAND_STARTED
CLI_INFO_COMMAND_COMPLETED = CLI.INFO_COMMAND_COMPLETED
CLI_ERROR_SCAN_FAILED = CLI.ERROR_SCAN_FAILED
CLI_ERROR_ORGANIZE_FAILED = CLI.ERROR_ORGANIZE_FAILED
CLI_ERROR_MATCH_FAILED = CLI.ERROR_MATCH_FAILED
CLI_ERROR_VERIFY_FAILED = CLI.ERROR_VERIFY_FAILED
CLI_ERROR_ROLLBACK_FAILED = CLI.ERROR_ROLLBACK_FAILED
CLI_ERROR_TMDB_CONNECTIVITY_FAILED = CLI.ERROR_TMDB_CONNECTIVITY_FAILED
CLI_ERROR_VERIFICATION_FAILED = CLI.ERROR_VERIFICATION_FAILED
CLI_SUCCESS_RESULTS_SAVED = CLI.SUCCESS_RESULTS_SAVED
