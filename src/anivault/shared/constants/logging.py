"""
Logging Configuration Constants

This module contains all constants related to logging configuration,
log levels, and log formatting.
"""

import logging

from .system import BASE_FILE_SIZE
from .system import Logging as SystemLogging


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


class LogConfig:
    """Log configuration constants."""

    # Default settings
    DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_FILE = "anivault.log"
    DEFAULT_ENCODING = "utf-8"

    # File configuration (inherited from system)
    MAX_SIZE = SystemLogging.MAX_BYTES  # 10MB
    BACKUP_COUNT = SystemLogging.BACKUP_COUNT  # 5

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
    ROLLBACK_PREFIX = "rollback-"

    # File extensions
    LOG_EXTENSION = ".json"


# Backward compatibility aliases
LOG_LEVEL_DEBUG = LogLevels.DEBUG
LOG_LEVEL_INFO = LogLevels.INFO
LOG_LEVEL_WARNING = LogLevels.WARNING
LOG_LEVEL_ERROR = LogLevels.ERROR
LOG_LEVEL_CRITICAL = LogLevels.CRITICAL
DEFAULT_LOG_LEVEL = LogLevels.DEFAULT
DEFAULT_LOG_FORMAT = LogConfig.DEFAULT_FORMAT
DEFAULT_LOG_FILE = LogConfig.DEFAULT_FILE
LOG_FILE_MAX_SIZE = LogConfig.MAX_SIZE
LOG_FILE_BACKUP_COUNT = LogConfig.BACKUP_COUNT
LOG_FILE_ENCODING = LogConfig.DEFAULT_ENCODING
DEFAULT_CONSOLE_OUTPUT = LogConfig.DEFAULT_CONSOLE_OUTPUT
DEFAULT_FILE_OUTPUT = LogConfig.DEFAULT_FILE_OUTPUT
LOG_STARTUP_MESSAGE = LogMessages.STARTUP
LOG_SHUTDOWN_MESSAGE = LogMessages.SHUTDOWN
LOG_OPERATION_START = LogMessages.OPERATION_START
LOG_OPERATION_COMPLETE = LogMessages.OPERATION_COMPLETE
LOG_OPERATION_ERROR = LogMessages.OPERATION_ERROR
LOG_PERFORMANCE_THRESHOLD = PerformanceLogging.PERFORMANCE_THRESHOLD
LOG_MEMORY_THRESHOLD = PerformanceLogging.MEMORY_THRESHOLD
LOG_ERROR_STACK_TRACE = ErrorLogging.INCLUDE_STACK_TRACE
LOG_ERROR_CONTEXT = ErrorLogging.INCLUDE_CONTEXT
DEFAULT_LOG_FILE_PATH = LogPaths.DEFAULT_LOG_PATH
DEFAULT_PROFILING_FILE_PATH = LogPaths.DEFAULT_PROFILING_PATH
ORGANIZE_LOG_PREFIX = LogPaths.ORGANIZE_PREFIX
ROLLBACK_LOG_PREFIX = LogPaths.ROLLBACK_PREFIX
LOG_FILE_EXTENSION = LogPaths.LOG_EXTENSION
