"""Logging and error handling constants."""


class Logging:
    """Logging configuration constants."""

    MAX_BYTES = 10485760  # 10MB
    BACKUP_COUNT = 5
    MIN_FILE_SIZE_MB = 50
    DEFAULT_FILE_PATH = "logs/anivault.log"
    DEFAULT_PROFILING_FILE_PATH = "logs/profiling.prof"
    FILE_EXTENSION = ".log"
    ORGANIZE_LOG_PREFIX = "organize"


class ErrorHandling:
    """Error handling configuration."""

    MAX_RETRY_ATTEMPTS = 3
    DEFAULT_RETRY_DELAY = 1.0
    MAX_RETRY_DELAY = 60.0
    DEFAULT_RETRY_ATTEMPTS = 3


__all__ = ["ErrorHandling", "Logging"]
