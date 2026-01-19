"""Performance and processing constants."""

from __future__ import annotations

from .base import BASE_FILE_SIZE, BASE_MINUTE, BASE_SECOND
from .filesystem import FileSystem


class Timeout:
    """Timeout configuration constants."""

    # Base timeouts
    SHORT = 30 * BASE_SECOND  # 30 seconds
    DEFAULT = 5 * BASE_MINUTE  # 5 minutes
    LONG = 10 * BASE_MINUTE  # 10 minutes

    # Specific service timeouts
    TMDB = 30 * BASE_SECOND  # TMDB API timeout
    PIPELINE_SENTINEL = 30.0  # Pipeline sentinel timeout
    PIPELINE_SHUTDOWN = 1.0  # Pipeline shutdown timeout
    PIPELINE_QUEUE = 1.0  # Pipeline queue timeout
    DEFAULT_REQUEST_TIMEOUT = 30 * BASE_SECOND  # 30 seconds


class Batch:
    """Batch processing constants."""

    DEFAULT_SIZE = 50
    MIN_SIZE = 1
    MAX_SIZE = 1000
    LARGE_SIZE = 100
    PARALLEL_THRESHOLD = 1000


class Process:
    """Process configuration constants."""

    DEFAULT_PRIORITY = "normal"
    MAX_CONCURRENT = 16
    DEFAULT_WORKERS = 4


class Memory:
    """Memory configuration constants."""

    # Base memory limits
    DEFAULT_LIMIT = FileSystem.MAX_FILE_SIZE  # 1GB
    WARNING_THRESHOLD = 512 * BASE_FILE_SIZE**2  # 512MB
    DEFAULT_LIMIT_MB = 1024  # 1GB in MB
    DEFAULT_LIMIT_STRING = "2GB"

    # CPU limits
    DEFAULT_CPU_LIMIT = 4


class Performance:
    """Performance monitoring constants."""

    SAMPLE_RATE = 0.1  # 10% sampling
    REPORT_INTERVAL = 60  # 60 seconds


__all__ = ["Batch", "Memory", "Performance", "Process", "Timeout"]
