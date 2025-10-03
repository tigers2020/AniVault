"""
AniVault Utilities Module

This module provides utility functions and configurations for the AniVault application,
including UTF-8 encoding support and centralized logging configuration.
"""

from .encoding import (UTF8_ENCODING, ensure_utf8_string, get_file_encoding,
                       open_utf8, read_text_file, safe_filename,
                       setup_utf8_environment, write_text_file)
from .logging_config import (AniVaultFormatter, LoggingContext,
                             configure_module_logging, get_logger,
                             log_shutdown, log_startup, log_system_info,
                             quick_setup, setup_logging)

__all__ = [
    "UTF8_ENCODING",
    "AniVaultFormatter",
    "LoggingContext",
    "configure_module_logging",
    "ensure_utf8_string",
    "get_file_encoding",
    "get_logger",
    "log_shutdown",
    "log_startup",
    "log_system_info",
    "open_utf8",
    "quick_setup",
    "read_text_file",
    "safe_filename",
    "setup_logging",
    "setup_utf8_environment",
    "write_text_file",
]
