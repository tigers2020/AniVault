"""
Logging Configuration Constants

Single source of truth for logging configuration, log levels, and formatting.
All logging-related constants used by shared/logging, utils/logging_config,
and config should be defined here.
"""

import logging

from .system import BASE_FILE_SIZE


class LogLevels:
    """Log level constants."""

    # Standard log levels
    DEBUG = logging.DEBUG  # 10
    INFO = logging.INFO  # 20
    WARNING = logging.WARNING  # 30
    ERROR = logging.ERROR  # 40
    CRITICAL = logging.CRITICAL  # 50

    # Default level
    DEFAULT = INFO


# 10 MB for file rotation (single source of truth)
_DEFAULT_MAX_BYTES = 10 * 1024 * 1024


class LogConfig:
    """Log configuration constants (single source of truth for bootstrap)."""

    # Default format and file (single source of truth for all logging formatters)
    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    DEFAULT_FILE = "anivault.log"
    DEFAULT_ENCODING = "utf-8"

    # File rotation (used by configure_logging and RotatingFileHandler)
    MAX_BYTES = _DEFAULT_MAX_BYTES
    MAX_SIZE = _DEFAULT_MAX_BYTES
    BACKUP_COUNT = 5

    # Paths (used by config, CLI, GUI)
    DEFAULT_LOG_DIR = "logs"
    DEFAULT_FILE_PATH = "logs/anivault.log"
    DEFAULT_PROFILING_FILE_PATH = "logs/profiling.prof"
    MIN_FILE_SIZE_MB = 50
    FILE_EXTENSION = ".log"
    ORGANIZE_LOG_PREFIX = "organize"

    # Output configuration
    DEFAULT_CONSOLE_OUTPUT = True
    DEFAULT_FILE_OUTPUT = True


class LogMessages:
    """Log message templates."""

    # Application lifecycle
    STARTUP = "AniVault v{version} starting up..."
    SHUTDOWN = "AniVault shutting down gracefully"

    # Operation messages
    OPERATION_START = "Starting operation: {operation}"
    OPERATION_COMPLETE = "Operation completed: {operation} (took {duration:.2f}s)"
    OPERATION_ERROR = "Operation failed: {operation} - {error}"


class PerformanceLogging:
    """Performance logging configuration."""

    # Thresholds
    PERFORMANCE_THRESHOLD = 1.0  # seconds
    MEMORY_THRESHOLD = 100 * BASE_FILE_SIZE**2  # 100MB


class ErrorLogging:
    """Error logging configuration."""

    # Error logging options
    INCLUDE_STACK_TRACE = True
    INCLUDE_CONTEXT = True


class LogPaths:
    """Log file paths and patterns."""

    # Default paths
    DEFAULT_LOG_PATH = "logs/anivault.log"
    DEFAULT_PROFILING_PATH = "logs/profiling.json"

    # Log prefixes
    ORGANIZE_PREFIX = "organize-"

    # File extensions
    LOG_EXTENSION = ".json"
