"""Core module constants.

This module defines constants used specifically within the core module,
including parsing confidence scores, processing thresholds, and status values.

Note: For shared constants used across multiple modules, see `shared/constants/`.
"""

from enum import Enum


class ParsingConfidence:
    """Confidence score constants for parsing operations.

    These values represent the confidence boost given when specific
    information is successfully extracted from filenames.
    """

    # Base confidence scores for different parsing components
    TITLE_FOUND = 0.5  # Confidence boost when title is found
    TITLE_FOUND_FALLBACK = 0.4  # Confidence boost for fallback parser
    EPISODE_FOUND = 0.3  # Confidence boost when episode number is found
    SEASON_FOUND = 0.1  # Confidence boost when season number is found
    RESOLUTION_DETECTED = 0.8  # Confidence when resolution is successfully detected

    # Error case confidence scores
    ERROR_CONFIDENCE_ANITOPY = 0.1  # Confidence for anitopy parser error cases
    ERROR_CONFIDENCE_FALLBACK = 0.2  # Confidence for fallback parser error cases

    # Metadata bonus scores
    METADATA_BONUS = 0.05  # Small bonus for each metadata field found
    METADATA_BONUS_MAX = 0.1  # Maximum bonus for metadata fields
    METADATA_BONUS_MULTIPLIER = 0.02  # Multiplier for metadata bonus calculation


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
    "ParsingConfidence",
    "ProcessStatus",
    "ProcessingThresholds",
]
