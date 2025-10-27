"""
Cache Configuration Constants

This module provides centralized cache configuration constants for different
domains of the AniVault application. Each cache configuration is tailored
for specific use cases while maintaining consistency.
"""

# Base time units for TTL calculations
BASE_SECOND = 1
BASE_MINUTE = 60 * BASE_SECOND
BASE_HOUR = 60 * BASE_MINUTE
BASE_DAY = 24 * BASE_HOUR


class BaseCacheConfig:
    """Base cache configuration with common settings."""

    # Common TTL values
    DEFAULT_TTL = BASE_HOUR  # 1 hour
    SHORT_TTL = 5 * BASE_MINUTE  # 5 minutes
    LONG_TTL = BASE_DAY  # 24 hours

    # Common size limits
    DEFAULT_SIZE_LIMIT = 1000
    MAX_SIZE_LIMIT = 10000

    # Common cache types
    TYPE_SEARCH = "search"
    TYPE_DETAILS = "details"


class APICacheConfig(BaseCacheConfig):
    """API-specific cache configuration."""

    # API-specific TTL values
    SEARCH_TTL = 30 * BASE_MINUTE  # 30 minutes
    DETAILS_TTL = BASE_HOUR  # 1 hour
    GENRE_TTL = 7 * BASE_DAY  # 7 days (genres rarely change)

    # API-specific size limits
    SEARCH_CACHE_SIZE = 500
    DETAILS_CACHE_SIZE = 2000

    # API-specific cache types
    TYPE_GENRE = "genre"
    TYPE_CREDITS = "credits"


class CLICacheConfig(BaseCacheConfig):
    """CLI-specific cache configuration."""

    # CLI-specific settings
    DEFAULT_DIR = "cache"
    CLI_CACHE_SIZE = 100  # Smaller cache for CLI usage

    # CLI-specific TTL (shorter for interactive use)
    CLI_TTL = 15 * BASE_MINUTE  # 15 minutes


class CoreCacheConfig(BaseCacheConfig):
    """Core system cache configuration."""

    # Core-specific TTL values
    PARSER_CACHE_TTL = BASE_DAY  # 24 hours
    METADATA_CACHE_TTL = 2 * BASE_HOUR  # 2 hours

    # Core-specific size limits
    PARSER_CACHE_SIZE = 5000
    METADATA_CACHE_SIZE = 2000

    # Core-specific cache keys
    CACHE_KEY_PREFIX = "anivault:"
    CACHE_VERSION = "v1"

    # Cache cleanup settings
    CACHE_CLEANUP_INTERVAL = BASE_HOUR  # 1 hour


class MatchingCacheConfig(BaseCacheConfig):
    """Matching engine cache configuration."""

    # Matching-specific TTL values
    SEARCH_CACHE_TTL = 7 * BASE_DAY  # 7 days
    DETAILS_CACHE_TTL = 30 * BASE_DAY  # 30 days

    # Matching-specific size limits
    MATCHING_CACHE_SIZE = 3000

    # Matching-specific cache types
    CACHE_TYPE_SEARCH = "search"
    CACHE_TYPE_DETAILS = "details"
    CACHE_TYPE_PARTIAL_MATCH = "partial_match"


class CacheValidationConstants:
    """Cache validation constants."""

    # Validation thresholds
    MIN_TTL = BASE_MINUTE  # 1 minute minimum
    MAX_TTL = 365 * BASE_DAY  # 1 year maximum

    # Size validation
    MIN_CACHE_SIZE = 10
    MAX_CACHE_SIZE = 100000

    # Key validation
    MAX_KEY_LENGTH = 255
    MIN_KEY_LENGTH = 1

    # Value validation
    MAX_VALUE_SIZE_MB = 100  # 100MB max value size
