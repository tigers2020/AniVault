"""
System Configuration Constants

This module contains all constants related to system configuration,
timeouts, limits, and general application settings.
"""

# Timeout Configuration
DEFAULT_TIMEOUT = 300  # default timeout in seconds (5 minutes)
SHORT_TIMEOUT = 30  # short timeout in seconds
LONG_TIMEOUT = 600  # long timeout in seconds (10 minutes)

# File Size Limits
MIN_FILE_SIZE = 1024  # 1KB in bytes
MAX_FILE_SIZE = MIN_FILE_SIZE**3  # 1GB in bytes


# Batch Processing
DEFAULT_BATCH_SIZE = 50  # default batch size for processing
MIN_BATCH_SIZE = 1  # minimum batch size
MAX_BATCH_SIZE = 1000  # maximum batch size

# Memory Configuration
DEFAULT_MEMORY_LIMIT = MIN_FILE_SIZE**3  # 1GB in bytes
MEMORY_WARNING_THRESHOLD = 512 * MIN_FILE_SIZE**2  # 512MB in bytes

# Application Version
APPLICATION_VERSION = "0.1.0"
APPLICATION_NAME = "AniVault"
APPLICATION_DESCRIPTION = "Anime Collection Management System with TMDB Integration"

# Configuration Constants
CONFIG_ENV_PREFIX = "ANIVAULT_"
CONFIG_ENV_DELIMITER = "__"
CONFIG_DEFAULT_DIR = ".anivault"
CONFIG_DEFAULT_FILENAME = "anivault.toml"

# Encoding Configuration
DEFAULT_ENCODING = "utf-8"
FALLBACK_ENCODING = "cp1252"

# Process Configuration
DEFAULT_PROCESS_PRIORITY = "normal"

# Path Configuration
MAX_PATH_LENGTH = 4096  # maximum path length
MAX_FILENAME_LENGTH = 255  # maximum filename length

# Process Configuration
DEFAULT_PROCESS_PRIORITY = "normal"  # process priority
MAX_CONCURRENT_PROCESSES = 16  # maximum concurrent processes

# Directory and File Paths
DEFAULT_LOG_DIRECTORY = "logs"  # default log directory
DEFAULT_PROFILING_DIRECTORY = "logs"  # default profiling directory
DEFAULT_CONFIG_DIRECTORY = "config"  # default config directory
DEFAULT_CACHE_BACKEND = "memory"  # default cache backend
ANIVAULT_HOME_DIR = ".anivault"  # AniVault home directory

# JSON and Data Keys
JSON_ENTRIES_KEY = "entries"  # key for entries in JSON data
JSON_METADATA_KEY = "metadata"  # key for metadata in JSON data
JSON_VERSION_KEY = "version"  # key for version in JSON data
JSON_DESCRIPTION_KEY = "description"  # key for description in JSON data
JSON_TOTAL_ENTRIES_KEY = "total_entries"  # key for total entries count

# Boolean String Values
BOOLEAN_TRUE_STRING = "true"  # string representation of true
BOOLEAN_FALSE_STRING = "false"  # string representation of false

# Memory and Version Configuration
DEFAULT_MEMORY_LIMIT_STRING = "2GB"  # default memory limit string
DEFAULT_VERSION_STRING = "0.1.0"  # default version string

# Error Handling
MAX_RETRY_ATTEMPTS = 3  # maximum retry attempts for failed operations
DEFAULT_RETRY_DELAY = 1.0  # default delay between retries in seconds
MAX_RETRY_DELAY = 60.0  # maximum delay between retries in seconds

# Performance Monitoring
PERFORMANCE_SAMPLE_RATE = 0.1  # 10% of operations sampled for performance monitoring
PERFORMANCE_REPORT_INTERVAL = 60  # performance report interval in seconds

# Configuration Defaults
DEFAULT_MIN_FILE_SIZE_MB = 50  # minimum file size in MB
DEFAULT_BATCH_SIZE_LARGE = 100  # large batch size for processing
DEFAULT_PARALLEL_THRESHOLD = 1000  # minimum file count for parallel processing
DEFAULT_LOG_MAX_BYTES = 10485760  # 10MB in bytes
DEFAULT_LOG_BACKUP_COUNT = 5  # number of backup log files
DEFAULT_TMDB_TIMEOUT = 30  # TMDB API timeout in seconds
DEFAULT_TMDB_RETRY_ATTEMPTS = 3  # TMDB retry attempts
DEFAULT_TMDB_RETRY_DELAY = 1.0  # TMDB retry delay in seconds
DEFAULT_TMDB_RATE_LIMIT_DELAY = 0.25  # TMDB rate limit delay in seconds
DEFAULT_TMDB_RATE_LIMIT_RPS = 35.0  # TMDB rate limit requests per second

# Pipeline timeout values
PIPELINE_SENTINEL_TIMEOUT = 30.0  # timeout for sentinel value operations
PIPELINE_SHUTDOWN_TIMEOUT = 1.0  # timeout for graceful shutdown
PIPELINE_QUEUE_TIMEOUT = 1.0  # timeout for queue operations

# Pipeline sentinel value - unique object to signal end of processing
SENTINEL = object()
DEFAULT_CACHE_TTL = 3600  # cache TTL in seconds
DEFAULT_CACHE_MAX_SIZE = 1000  # maximum cache size
DEFAULT_CPU_LIMIT = 4  # CPU limit for application
DEFAULT_MEMORY_LIMIT_MB = 1024

# Cache Type Constants
CACHE_TYPE_SEARCH = "search"  # cache type for search results
CACHE_TYPE_DETAILS = "details"  # cache type for detailed results

# Enrichment Status Constants
ENRICHMENT_STATUS_PENDING = "pending"  # enrichment pending
ENRICHMENT_STATUS_SUCCESS = "success"  # enrichment success
ENRICHMENT_STATUS_FAILED = "failed"  # enrichment failed
ENRICHMENT_STATUS_SKIPPED = "skipped"  # enrichment skipped

# Media Type Constants
MEDIA_TYPE_TV = "tv"  # TV media type
MEDIA_TYPE_MOVIE = "movie"  # movie media type

# Language Constants
LANGUAGE_ENGLISH = "en"  # English language code
LANGUAGE_KOREAN = "ko"  # Korean language code  # memory limit in MB

# Pipeline Configuration
DEFAULT_QUEUE_SIZE = 1000  # default queue size for pipeline processing
DEFAULT_WORKERS = 4  # default number of worker processes

# CLI Constants
CLI_INFO_COMMAND_STARTED = "Starting {command} command..."
CLI_INFO_COMMAND_COMPLETED = "Completed {command} command"
CLI_ERROR_SCAN_FAILED = "Scan command failed: {error}"
CLI_ERROR_ORGANIZE_FAILED = "Organize command failed: {error}"
CLI_ERROR_MATCH_FAILED = "Match command failed: {error}"
CLI_ERROR_VERIFY_FAILED = "Verify command failed: {error}"
CLI_ERROR_ROLLBACK_FAILED = "Rollback command failed: {error}"
CLI_ERROR_TMDB_CONNECTIVITY_FAILED = "TMDB API connectivity failed: {error}"
CLI_ERROR_VERIFICATION_FAILED = "Verification failed: {error}"
CLI_SUCCESS_RESULTS_SAVED = "Results saved to: {path}"
CLI_INDENT_SIZE = 2
