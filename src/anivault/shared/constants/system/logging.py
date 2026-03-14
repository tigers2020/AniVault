"""Logging and error handling constants.

Logging constants are defined in shared.constants.logging (LogConfig).
This module re-exports Logging for backward compatibility.
"""

from anivault.shared.constants.logging import LogConfig

# Backward compatibility: code importing Logging from .system uses LogConfig
Logging = LogConfig


class ErrorHandling:
    """Error handling configuration."""

    MAX_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 1.0
    MAX_RETRY_DELAY = 60.0
    DEFAULT_RETRY_ATTEMPTS = 3


__all__ = ["ErrorHandling", "Logging"]
