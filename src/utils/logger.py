"""
Centralized logging system for AniVault application.

This module provides a centralized logging configuration that can be used
throughout the application to ensure consistent logging behavior.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal


class QtLogHandler(logging.Handler):
    """
    Custom logging handler that emits Qt signals for UI integration.

    This handler allows log messages to be displayed in the UI by emitting
    Qt signals that can be connected to UI components.
    """

    # Signal emitted when a log message is received
    log_message = pyqtSignal(str, int)  # message, level

    def __init__(self, level: int = logging.NOTSET) -> None:
        """
        Initialize the Qt log handler.

        Args:
            level: Minimum log level to handle
        """
        super().__init__(level)
        self.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record as a Qt signal.

        Args:
            record: Log record to emit
        """
        try:
            msg = self.format(record)
            self.log_message.emit(msg, record.levelno)
        except Exception:
            self.handleError(record)


class LogManager(QObject):
    """
    Centralized log manager for the AniVault application.

    This class manages all logging configuration and provides a single
    point of control for logging behavior throughout the application.
    """

    # Signal emitted when log configuration changes
    config_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        """
        Initialize the log manager.

        Args:
            parent: Parent QObject
        """
        super().__init__(parent)

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

    def _setup_logging(self) -> None:
        """Set up the logging configuration."""
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        simple_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Console handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)

        # File handler for all logs (DEBUG and above)
        file_handler = logging.handlers.RotatingFileHandler(
            self.app_log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # Error file handler (ERROR and above)
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",  # 5MB
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)

        # Debug file handler (DEBUG and above, separate file)
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

        logging.info("Logging system initialized")

    def _configure_module_loggers(self) -> None:
        """Configure specific module loggers with appropriate levels."""
        # PyQt5 loggers (reduce noise)
        logging.getLogger("PyQt5").setLevel(logging.WARNING)
        logging.getLogger("PyQt5.QtCore").setLevel(logging.WARNING)
        logging.getLogger("PyQt5.QtGui").setLevel(logging.WARNING)
        logging.getLogger("PyQt5.QtWidgets").setLevel(logging.WARNING)

        # Third-party library loggers
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

        # Application loggers
        logging.getLogger("anivault").setLevel(logging.DEBUG)
        logging.getLogger("anivault.core").setLevel(logging.DEBUG)
        logging.getLogger("anivault.gui").setLevel(logging.DEBUG)
        logging.getLogger("anivault.viewmodels").setLevel(logging.DEBUG)
        logging.getLogger("anivault.utils").setLevel(logging.DEBUG)

    def add_qt_handler(self) -> QtLogHandler:
        """
        Add Qt handler for UI integration.

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

    def remove_qt_handler(self) -> None:
        """Remove Qt handler from logging."""
        if self.qt_handler is not None:
            logging.getLogger().removeHandler(self.qt_handler)
            self.qt_handler = None
            logging.info("Qt log handler removed")

    def set_log_level(self, level: int) -> None:
        """
        Set the global log level.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        logging.getLogger().setLevel(level)
        logging.info(f"Log level changed to {logging.getLevelName(level)}")
        self.config_changed.emit()

    def set_module_log_level(self, module_name: str, level: int) -> None:
        """
        Set log level for a specific module.

        Args:
            module_name: Name of the module logger
            level: Log level to set
        """
        logger = logging.getLogger(module_name)
        logger.setLevel(level)
        logging.info(f"Log level for '{module_name}' changed to {logging.getLevelName(level)}")
        self.config_changed.emit()

    def get_log_files(self) -> list[Path]:
        """
        Get list of log files.

        Returns:
            List of log file paths
        """
        return [self.app_log_file, self.error_log_file, self.debug_log_file]

    def clear_logs(self) -> None:
        """Clear all log files."""
        for log_file in self.get_log_files():
            if log_file.exists():
                log_file.unlink()

        logging.info("All log files cleared")

    def get_log_size(self) -> dict[str, int]:
        """
        Get size of log files in bytes.

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

    def cleanup(self) -> None:
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
    """
    Get the global log manager instance.

    Returns:
        LogManager instance
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


def setup_logging() -> LogManager:
    """
    Set up logging for the application.

    This function should be called early in the application startup
    to ensure proper logging configuration.

    Returns:
        LogManager instance
    """
    return get_log_manager()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for the specified name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_function_call(func):
    """
    Decorator to log function calls.

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


def log_class_methods(cls):
    """
    Class decorator to add logging to all methods.

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
