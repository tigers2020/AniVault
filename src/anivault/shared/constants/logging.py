"""
Logging Configuration Constants

This module contains all constants related to logging configuration,
log levels, and log formatting.
"""

# Log Levels (using Python logging module constants)
LOG_LEVEL_DEBUG = 10  # DEBUG level
LOG_LEVEL_INFO = 20  # INFO level
LOG_LEVEL_WARNING = 30  # WARNING level
LOG_LEVEL_ERROR = 40  # ERROR level
LOG_LEVEL_CRITICAL = 50  # CRITICAL level

# Default Log Configuration
DEFAULT_LOG_LEVEL = LOG_LEVEL_INFO
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LOG_FILE = "anivault.log"

# Log File Configuration
LOG_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10MB in bytes
LOG_FILE_BACKUP_COUNT = 5  # number of backup log files to keep
LOG_FILE_ENCODING = "utf-8"

# Console Output Configuration
DEFAULT_CONSOLE_OUTPUT = True
DEFAULT_FILE_OUTPUT = True

# Log Message Templates
LOG_STARTUP_MESSAGE = "AniVault v{version} starting up..."
LOG_SHUTDOWN_MESSAGE = "AniVault shutting down gracefully"
LOG_OPERATION_START = "Starting operation: {operation}"
LOG_OPERATION_COMPLETE = "Operation completed: {operation} (took {duration:.2f}s)"
LOG_OPERATION_ERROR = "Operation failed: {operation} - {error}"

# Performance Logging
LOG_PERFORMANCE_THRESHOLD = 1.0  # log operations taking longer than 1 second
LOG_MEMORY_THRESHOLD = 100 * 1024 * 1024  # log memory usage above 100MB

# Error Logging
LOG_ERROR_STACK_TRACE = True  # include stack traces in error logs
LOG_ERROR_CONTEXT = True  # include context information in error logs

# Log File Paths and Patterns
DEFAULT_LOG_FILE_PATH = "logs/anivault.log"  # default log file path
DEFAULT_PROFILING_FILE_PATH = "logs/profiling.json"  # default profiling file path
ORGANIZE_LOG_PREFIX = "organize-"  # prefix for organize log files
ROLLBACK_LOG_PREFIX = "rollback-"  # prefix for rollback log files
LOG_FILE_EXTENSION = ".json"  # log file extension
