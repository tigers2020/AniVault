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
