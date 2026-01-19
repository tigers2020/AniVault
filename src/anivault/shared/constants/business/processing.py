"""Processing-related business constants."""

from __future__ import annotations

from enum import Enum


class ProcessingConfig:
    """Processing configuration constants."""

    # Thread pool settings
    MAX_DOWNLOAD_WORKERS = 10
    MAX_PROCESSING_WORKERS = 4

    # Queue settings
    DEFAULT_QUEUE_SIZE = 1000
    MAX_QUEUE_SIZE = 10000

    # Batch processing
    DEFAULT_BATCH_SIZE = 100
    MAX_BATCH_SIZE = 200

    # Parallel processing threshold
    PARALLEL_THRESHOLD = 1000  # Minimum files to benefit from parallel processing

    # Memory limits
    MAX_MEMORY_USAGE_MB = 1024  # 1GB
    MEMORY_WARNING_THRESHOLD_MB = 512  # 512MB


class ProcessingThresholds:
    """Threshold constants for processing operations."""

    # Queue usage threshold (0.0 to 1.0)
    QUEUE_BACKPRESSURE_THRESHOLD = 0.8  # 80% - trigger backpressure handling

    # Minimum confidence for enrichment
    MIN_ENRICHMENT_CONFIDENCE = 0.3  # Minimum confidence score for metadata enrichment


class ProcessStatus(str, Enum):
    """Status enumeration for processing operations.

    This Enum represents the various states a processing operation
    can be in. Using Enum ensures type safety and prevents typos.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    SUCCESS = "success"  # Operation completed successfully


class ConfigKeys:
    """Configuration key constants.

    These constants represent keys used in configuration files
    and settings dictionaries to ensure consistency and prevent typos.
    """

    # Processing configuration
    BATCH_SIZE = "batch_size"
    MAX_WORKERS = "max_workers"
    TIMEOUT = "timeout"
    RETRY_COUNT = "retry_count"

    # Parser configuration
    PARSER_TYPE = "parser_type"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    ENABLE_FALLBACK = "enable_fallback"

    # Cache configuration
    CACHE_ENABLED = "cache_enabled"
    CACHE_TTL = "cache_ttl"
    CACHE_SIZE = "cache_size"

    # Pipeline configuration
    SCAN_RECURSIVE = "scan_recursive"
    INCLUDE_SUBTITLES = "include_subtitles"
    INCLUDE_METADATA = "include_metadata"


__all__ = [
    "ConfigKeys",
    "ProcessingConfig",
    "ProcessingThresholds",
    "ProcessStatus",
]
