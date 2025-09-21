"""Centralized logging system for AniVault application.

This module provides a centralized logging configuration that can be used
throughout the application to ensure consistent logging behavior.
"""

import logging
import logging.handlers
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from PyQt5.QtCore import QObject, pyqtSignal

from .conditional_json_formatter import (
    ConditionalJsonFormatter,
    create_optimized_formatter,
    create_simple_formatter,
)

F = TypeVar("F", bound=Callable[..., Any])


class QtLogHandler(logging.Handler):
    """Custom logging handler that emits Qt signals for UI integration.

    This handler allows log messages to be displayed in the UI by emitting
    Qt signals that can be connected to UI components.
    """

    # Signal emitted when a log message is received
    log_message = pyqtSignal(str, int)  # message, level

    def __init__(self: "QtLogHandler", level: int = logging.NOTSET) -> None:
        """Initialize the Qt log handler.

        Args:
            level: Minimum log level to handle
        """
        super().__init__(level)
        # Use simple formatter for UI display
        self.setFormatter(create_simple_formatter())

    def emit(self: "QtLogHandler", record: logging.LogRecord) -> None:
        """Emit a log record as a Qt signal.

        Args:
            record: Log record to emit
        """
        try:
            msg = self.format(record)
            self.log_message.emit(msg, record.levelno)
        except Exception:
            self.handleError(record)


class LogManager(QObject):
    """Centralized log manager for the AniVault application.

    This class manages all logging configuration and provides a single
    point of control for logging behavior throughout the application.
    """

    # Signal emitted when log configuration changes
    config_changed = pyqtSignal()

    def __init__(self: "LogManager", parent: QObject | None = None) -> None:
        """Initialize the log manager.

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)

        # Determine environment and logging configuration
        self.environment = self._determine_environment()
        self.debug_enabled = self._should_enable_debug()

        # Log directory
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # Log file paths
        self.app_log_file = self.log_dir / "anivault.log"
        self.error_log_file = self.log_dir / "anivault_errors.log"
        self.debug_log_file = self.log_dir / "anivault_debug.log"

        # Qt handler for UI integration
        self.qt_handler: QtLogHandler | None = None

        # Configure logging
        self._setup_logging()

    def _determine_environment(self: "LogManager") -> str:
        """Determine the current environment from environment variables or configuration.

        Returns:
            Environment string: 'production', 'development', or 'debug'
        """
        # Check APP_ENV environment variable first
        app_env = os.getenv("APP_ENV", "").lower()
        if app_env in ["production", "prod"]:
            return "production"
        elif app_env in ["development", "dev"]:
            return "development"
        elif app_env in ["debug", "test"]:
            return "debug"

        # Fallback: check DEBUG environment variable
        if os.getenv("DEBUG", "").lower() in ["true", "1", "yes"]:
            return "debug"

        # Default to development for safety
        return "development"

    def _should_enable_debug(self: "LogManager") -> bool:
        """Determine if debug logging should be enabled based on environment.

        Returns:
            True if debug logging should be enabled, False otherwise
        """
        return self.environment in ["development", "debug"]

    def _get_console_log_level(self: "LogManager") -> int:
        """Get the console log level based on environment.

        Returns:
            Logging level for console output
        """
        if self.environment == "production":
            return logging.WARNING
        elif self.environment == "development":
            return logging.INFO
        else:  # debug
            return logging.DEBUG

    def _get_file_log_level(self: "LogManager") -> int:
        """Get the file log level based on environment.

        Returns:
            Logging level for file output
        """
        if self.environment == "production":
            return logging.WARNING
        else:  # development, debug
            return logging.DEBUG

    def _get_application_log_level(self: "LogManager") -> int:
        """Get the application logger level based on environment.

        Returns:
            Logging level for application loggers
        """
        if self.environment == "production":
            return logging.WARNING
        elif self.environment == "development":
            return logging.DEBUG
        else:  # debug
            return logging.DEBUG

    def _setup_logging(self: "LogManager") -> None:
        """Set up the logging configuration based on environment."""
        # Get root logger
        root_logger = logging.getLogger()

        # Set root logger level based on environment
        root_log_level = logging.DEBUG if self.debug_enabled else logging.INFO
        root_logger.setLevel(root_log_level)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Create optimized formatters
        # Use conditional JSON formatter for file handlers (WARNING+ as JSON)
        json_formatter = create_optimized_formatter(
            json_levels=[logging.WARNING, logging.ERROR, logging.CRITICAL],
            use_orjson=True,
            include_extra=True,
        )
        
        # Use simple formatter for console and debug levels
        simple_formatter = create_simple_formatter()
        
        # Detailed formatter for backward compatibility
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )

        # Console handler with environment-specific level
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._get_console_log_level())
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)

        # File handler with conditional JSON formatting
        file_handler = logging.handlers.RotatingFileHandler(
            self.app_log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",  # 10MB
        )
        file_handler.setLevel(self._get_file_log_level())
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)

        # Error file handler (always ERROR and above) - use JSON formatting
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",  # 5MB
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(json_formatter)
        root_logger.addHandler(error_handler)

        # Debug file handler (only if debug is enabled) - use simple formatting
        if self.debug_enabled:
            debug_handler = logging.handlers.RotatingFileHandler(
                self.debug_log_file,
                maxBytes=20 * 1024 * 1024,
                backupCount=2,
                encoding="utf-8",  # 20MB
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(debug_handler)

        # Configure specific loggers
        self._configure_module_loggers()

        # Log initialization with environment info
        logging.info(
            f"Logging system initialized - Environment: {self.environment}, Debug: {self.debug_enabled}"
        )

    def _configure_module_loggers(self: "LogManager") -> None:
        """Configure specific module loggers with appropriate levels based on environment."""
        # PyQt5 loggers (reduce noise in all environments)
        logging.getLogger("PyQt5").setLevel(logging.WARNING)
        logging.getLogger("PyQt5.QtCore").setLevel(logging.WARNING)
        logging.getLogger("PyQt5.QtGui").setLevel(logging.WARNING)
        logging.getLogger("PyQt5.QtWidgets").setLevel(logging.WARNING)

        # Third-party library loggers (reduce noise in all environments)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

        # Application loggers with environment-specific levels
        app_log_level = self._get_application_log_level()
        logging.getLogger("anivault").setLevel(app_log_level)
        logging.getLogger("anivault.core").setLevel(app_log_level)
        logging.getLogger("anivault.gui").setLevel(app_log_level)
        logging.getLogger("anivault.viewmodels").setLevel(app_log_level)
        logging.getLogger("anivault.utils").setLevel(app_log_level)

    def add_qt_handler(self: "LogManager") -> QtLogHandler:
        """Add Qt handler for UI integration.

        Returns:
            QtLogHandler instance for connecting to UI
        """
        if self.qt_handler is None:
            self.qt_handler = QtLogHandler()
            self.qt_handler.setLevel(logging.INFO)

            # Add to root logger
            logging.getLogger().addHandler(self.qt_handler)

            logging.info("Qt log handler added")

        return self.qt_handler

    def remove_qt_handler(self: "LogManager") -> None:
        """Remove Qt handler from logging."""
        if self.qt_handler is not None:
            logging.getLogger().removeHandler(self.qt_handler)
            self.qt_handler = None
            logging.info("Qt log handler removed")

    def set_log_level(self: "LogManager", level: int) -> None:
        """Set the global log level.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        logging.getLogger().setLevel(level)
        logging.info(f"Log level changed to {logging.getLevelName(level)}")
        self.config_changed.emit()

    def set_module_log_level(self: "LogManager", module_name: str, level: int) -> None:
        """Set log level for a specific module.

        Args:
            module_name: Name of the module logger
            level: Log level to set
        """
        logger = logging.getLogger(module_name)
        logger.setLevel(level)
        logging.info(f"Log level for '{module_name}' changed to {logging.getLevelName(level)}")
        self.config_changed.emit()

    def get_log_files(self: "LogManager") -> list[Path]:
        """Get list of log files.

        Returns:
            List of log file paths
        """
        return [self.app_log_file, self.error_log_file, self.debug_log_file]

    def clear_logs(self: "LogManager") -> None:
        """Clear all log files."""
        for log_file in self.get_log_files():
            if log_file.exists():
                log_file.unlink()

        logging.info("All log files cleared")

    def get_log_size(self: "LogManager") -> dict[str, int]:
        """Get size of log files in bytes.

        Returns:
            Dictionary mapping log file names to sizes
        """
        sizes = {}
        for log_file in self.get_log_files():
            if log_file.exists():
                sizes[log_file.name] = log_file.stat().st_size
            else:
                sizes[log_file.name] = 0

        return sizes

    def get_environment_info(self: "LogManager") -> dict[str, Any]:
        """Get information about the current logging environment.

        Returns:
            Dictionary containing environment information
        """
        return {
            "environment": self.environment,
            "debug_enabled": self.debug_enabled,
            "console_log_level": logging.getLevelName(self._get_console_log_level()),
            "file_log_level": logging.getLevelName(self._get_file_log_level()),
            "application_log_level": logging.getLevelName(self._get_application_log_level()),
            "debug_file_enabled": self.debug_enabled,
        }

    def cleanup(self: "LogManager") -> None:
        """Clean up logging resources."""
        logging.info("Cleaning up logging system")

        # Remove Qt handler
        self.remove_qt_handler()

        # Close all handlers
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)

        logging.info("Logging system cleanup completed")


# Global log manager instance
_log_manager: LogManager | None = None


def get_log_manager() -> LogManager:
    """Get the global log manager instance.

    Returns:
        LogManager instance
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


def reset_log_manager() -> None:
    """Reset the global log manager instance.

    This is useful for testing or when environment variables change.
    """
    global _log_manager
    if _log_manager is not None:
        _log_manager.cleanup()
        _log_manager = None


def setup_logging() -> LogManager:
    """Set up logging for the application.

    This function should be called early in the application startup
    to ensure proper logging configuration.

    Returns:
        LogManager instance
    """
    return get_log_manager()


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_function_call(func: F) -> F:
    """Decorator to log function calls.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {e}", exc_info=True)
            raise

    return wrapper


def log_class_methods(cls: type) -> type:
    """Class decorator to add logging to all methods.

    Args:
        cls: Class to decorate

    Returns:
        Decorated class
    """
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith("_"):
            setattr(cls, attr_name, log_function_call(attr))

    return cls


# Convenience functions for common logging operations
def log_info(message: str, module: str = "anivault") -> None:
    """Log an info message."""
    get_logger(module).info(message)


def log_warning(message: str, module: str = "anivault") -> None:
    """Log a warning message."""
    get_logger(module).warning(message)


def log_error(message: str, module: str = "anivault", exc_info: bool = False) -> None:
    """Log an error message."""
    get_logger(module).error(message, exc_info=exc_info)


def log_debug(message: str, module: str = "anivault") -> None:
    """Log a debug message."""
    get_logger(module).debug(message)


def log_critical(message: str, module: str = "anivault", exc_info: bool = False) -> None:
    """Log a critical message."""
    get_logger(module).critical(message, exc_info=exc_info)
