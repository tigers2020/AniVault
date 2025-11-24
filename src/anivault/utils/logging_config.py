"""
Logging Configuration Module

This module provides centralized logging configuration for the AniVault application.
It sets up both console and file logging with rotation support, ensuring consistent
logging across all modules.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import platform
import sys
import types
from pathlib import Path
from typing import ClassVar

# Default logging configuration
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# File rotation settings
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5


class AniVaultFormatter(logging.Formatter):
    """
    Custom formatter for AniVault logging.

    Provides consistent formatting with colors for console output and
    structured formatting for file output.
    """

    # Color codes for different log levels
    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def __init__(self, *, use_colors: bool = True, detailed: bool = False):
        """
        Initialize the formatter.

        Args:
            use_colors: Whether to use colors in the output
            detailed: Whether to include detailed information (file, line, function)
        """
        self.use_colors = use_colors
        self.detailed = detailed

        if detailed:
            format_str = "%(asctime)s - %(name)s - %(levelname)s - " "%(filename)s:%(lineno)d - %(funcName)s - %(message)s"
        else:
            format_str = DEFAULT_LOG_FORMAT

        super().__init__(format_str, DEFAULT_DATE_FORMAT)

    def format_record(self, record: logging.LogRecord) -> str:
        """
        Format the log record.

        Args:
            record: Log record to format

        Returns:
            Formatted log message
        """
        if self.use_colors and hasattr(record, "levelname"):
            color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
            reset = self.COLORS["RESET"]
            record.levelname = f"{color}{record.levelname}{reset}"

        return super().format(record)


def setup_logging(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    log_level: int = DEFAULT_LOG_LEVEL,
    log_dir: Path | None = None,
    log_file: str | None = None,
    *,
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    use_colors: bool = True,
    detailed_console: bool = False,
) -> logging.Logger:
    """
    Set up logging configuration for the AniVault application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (defaults to 'logs' in project root)
        log_file: Name of the log file (defaults to 'anivault.log')
        console_output: Whether to output logs to console
        file_output: Whether to output logs to file
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        use_colors: Whether to use colors in console output
        detailed_console: Whether to include detailed info in console output

    Returns:
        Configured root logger
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = AniVaultFormatter(
            use_colors=use_colors,
            detailed=detailed_console,
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    if file_output:
        # Set up log directory
        if log_dir is None:
            # Default to 'logs' directory in project root
            project_root = Path(__file__).parent.parent.parent.parent
            log_dir = project_root / "logs"

        log_dir.mkdir(parents=True, exist_ok=True)

        # Set up log file
        if log_file is None:
            log_file = "anivault.log"

        log_path = log_dir / log_file

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)

        # File formatter (always detailed, no colors)
        file_formatter = AniVaultFormatter(
            use_colors=False,
            detailed=True,
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Name of the module (typically __name__)

    Returns:
        Logger instance for the module
    """
    return logging.getLogger(name)


def configure_module_logging(
    module_name: str,
    log_level: int | None = None,
    *,
    propagate: bool = True,
) -> logging.Logger:
    """
    Configure logging for a specific module.

    Args:
        module_name: Name of the module
        log_level: Specific log level for this module (optional)
        propagate: Whether to propagate logs to parent loggers

    Returns:
        Configured logger for the module
    """
    logger = logging.getLogger(module_name)

    if log_level is not None:
        logger.setLevel(log_level)

    logger.propagate = propagate

    return logger


def log_system_info(logger: logging.Logger) -> None:
    """
    Log system information for debugging purposes.

    Args:
        logger: Logger instance to use for logging
    """

    logger.info("=== AniVault System Information ===")
    logger.info("Python version: %s", sys.version)
    logger.info("Platform: %s", platform.platform())
    logger.info("Architecture: %s", platform.architecture())
    logger.info("Processor: %s", platform.processor())
    logger.info("Working directory: %s", Path.cwd())
    logger.info("Python executable: %s", sys.executable)

    # Log environment variables that might affect UTF-8 handling
    utf8_vars = ["PYTHONUTF8", "LC_ALL", "LANG", "LC_CTYPE"]
    for var in utf8_vars:
        value = os.environ.get(var, "Not set")
        logger.info("Environment %s: %s", var, value)


def log_startup(logger: logging.Logger, version: str = "unknown") -> None:
    """
    Log application startup information.

    Args:
        logger: Logger instance to use for logging
        version: Application version
    """
    logger.info("=== AniVault Startup ===")
    logger.info("Version: %s", version)
    logger.info("Logging configured successfully")
    log_system_info(logger)


def log_shutdown(logger: logging.Logger) -> None:
    """
    Log application shutdown information.

    Args:
        logger: Logger instance to use for logging
    """
    logger.info("=== AniVault Shutdown ===")
    logger.info("Application shutting down gracefully")


def cleanup_logging(logger: logging.Logger | None = None) -> None:
    """
    Clean up logging handlers and close file handles.

    Args:
        logger: Specific logger to clean up (defaults to root logger)
    """
    if logger is None:
        logger = logging.getLogger()

    # Close all handlers
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


# Context manager for temporary logging configuration
class LoggingContext:
    """
    Context manager for temporarily modifying logging configuration.
    """

    def __init__(self, level: int, logger_name: str | None = None):
        """
        Initialize the logging context.

        Args:
            level: Temporary log level to set
            logger_name: Specific logger to modify (defaults to root logger)
        """
        self.level = level
        self.logger_name = logger_name
        self.original_level: int | None = None

    def __enter__(self) -> logging.Logger:
        """Enter the context and set the log level."""
        logger = logging.getLogger(self.logger_name) if self.logger_name else logging.getLogger()
        self.original_level = logger.level
        logger.setLevel(self.level)
        return logger

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit the context and restore the original log level."""
        logger = logging.getLogger(self.logger_name) if self.logger_name else logging.getLogger()
        if self.original_level is not None:
            logger.setLevel(self.original_level)


# Convenience function for quick setup
def quick_setup(level: str = "INFO") -> logging.Logger:
    """
    Quick setup of logging with sensible defaults.

    Args:
        level: Log level as string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

    Returns:
        Configured root logger
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    return setup_logging(log_level=log_level)
