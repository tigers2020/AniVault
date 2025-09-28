"""Centralized logging configuration for AniVault.

This module sets up the application's root logger with file rotation
and console output based on project configuration.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from .config import APP_CONFIG


def setup_logging(
    log_file: str | None = None,
    log_level: str | None = None,
    log_max_bytes: int | None = None,
    log_backup_count: int | None = None,
) -> None:
    """Set up the application's root logger.

    Args:
        log_file: Path to the log file. If None, uses config default.
        log_level: Logging level. If None, uses config default.
        log_max_bytes: Maximum size of log file before rotation.
        log_backup_count: Number of backup files to keep.
    """
    # Use provided values or fall back to config defaults
    log_file = log_file or APP_CONFIG.log_file
    log_level = log_level or APP_CONFIG.log_level
    log_max_bytes = log_max_bytes or APP_CONFIG.log_max_bytes
    log_backup_count = log_backup_count or APP_CONFIG.log_backup_count

    # Get the absolute path to the log file
    log_path = Path(log_file)
    if not log_path.is_absolute():
        # Make relative to project root
        project_root = _find_project_root()
        log_path = project_root / log_path

    # Ensure log directory exists
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_path),
        maxBytes=log_max_bytes,
        backupCount=log_backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Add console handler for INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


def _find_project_root() -> Path:
    """Find the project root directory.

    Returns:
        Path to the project root directory.
    """
    current = Path(__file__).parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    # Fallback to current working directory
    return Path.cwd()
