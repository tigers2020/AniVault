"""
Matching Engine Constants

This module contains all constants related to the matching engine,
confidence thresholds, and scoring algorithms.
"""

from typing import ClassVar

from .system import BASE_SECOND


class ValidationConstants:
    """Validation constants for matching domain models."""

    # Year validation
    MIN_VALID_YEAR = 1900  # Earliest valid release year
    FUTURE_YEAR_TOLERANCE = 5  # Years into future allowed for upcoming releases

    # Confidence score validation
    MIN_CONFIDENCE_SCORE = 0.0  # Minimum valid confidence score
    MAX_CONFIDENCE_SCORE = 1.0  # Maximum valid confidence score

    # Media type validation
    VALID_MEDIA_TYPES: ClassVar[list[str]] = [
        "tv",
        "movie",
    ]  # Allowed media type values


class YearMatchingConfig:
    """Year matching configuration constants."""

    # Year score calculation
    YEAR_SCORE_MAX = 100  # Maximum year score for exact match
    YEAR_DIFF_UNKNOWN = 999  # Year difference for candidates without year info
    YEAR_SCORE_UNKNOWN = 0  # Score for candidates without year info


# =============================================================================
# CACHE CONFIGURATION (Moved to cache.py)
# =============================================================================

# Cache configuration is now centralized in cache.py
# Import MatchingCacheConfig from cache module


class MatchingFieldNames:
    """Internal field names used during matching process."""

    # Scoring fields added to candidates during matching
    TITLE_SCORE = "title_score"
    YEAR_SCORE = "year_score"
    YEAR_DIFF = "year_diff"
    CONFIDENCE_SCORE = "confidence_score"
    PARTIAL_MATCH_SCORE = "partial_match_score"
    USED_PARTIAL_MATCHING = "used_partial_matching"

    # Metadata field
    MATCHING_METADATA = "matching_metadata"


class DefaultLanguage:
    """Default language configuration for TMDB API."""

    # Default language code for TMDB API requests
    KOREAN = "ko-KR"
    JAPANESE = "ja-JP"
    ENGLISH = "en-US"


class ConfidenceThresholds:
    """Confidence threshold constants for matching.

    Note: Thresholds are intentionally low because:
    - File names use Japanese romanization (e.g., "Kaifuku Jutsushi")
    - TMDB returns localized titles (e.g., "회복술사의 재시작")
    - Original titles use different scripts (e.g., "回復術士のやり直し")
    - String similarity is inherently low across different writing systems
    - TMDB's relevance algorithm already filters results effectively
    """

    # Base confidence levels - trust TMDB's relevance ranking
    HIGH = 0.8  # Very strong match (exact or near-exact title)
    MEDIUM = 0.5  # Good match (partial title match + metadata)
    LOW = 0.2  # Accept if TMDB found it (trust relevance algorithm)

    # Genre-specific thresholds (used in _apply_genre_filter)
    ANIMATION_MIN = 0.2  # Lenient for cross-script fuzzy matching
    NON_ANIMATION_MIN = 0.8  # Strict to avoid false positives (quiz shows, variety, etc.)

    # Benchmark specific thresholds
    BENCHMARK_DEFAULT = 0.7
    BENCHMARK_HIGH = 0.9
    BENCHMARK_MEDIUM = 0.8


class ValidationConfig:
    """Validation configuration constants."""

    # Minimum required keys
    MIN_REQUIRED_KEYS = 2

    # Expected anitopy keys
    EXPECTED_ANITOPY_KEYS: ClassVar[list[str]] = [
        "anime_title",
        "episode_number",
        "release_group",
        "video_resolution",
    ]


class MatchingAlgorithm:
    """Matching algorithm configuration."""

    # Fuzzy matching
    DEFAULT_FUZZY_THRESHOLD = 0.8
    DEFAULT_EXACT_MATCH_BONUS = 0.1
    DEFAULT_PARTIAL_MATCH_BONUS = 0.05

    # Genre filtering
    GENRE_FILTER_THRESHOLD = 0.7
    ANIME_GENRE_KEYWORDS: ClassVar[list[str]] = [
        "animation",
        "anime",
        "cartoon",
        "manga",
        "japanese animation",
    ]


class TitleNormalization:
    """Title normalization configuration."""

    MAX_LENGTH = 100
    MIN_LENGTH = 2


class FallbackStrategy:
    """Fallback strategy configuration."""

    TIMEOUT = 5.0 * BASE_SECOND
    MAX_ATTEMPTS = 3


class ScoringWeights:
    """Scoring weight configuration for matching.

    .. deprecated:: Use `anivault.config.models.matching_weights.MatchingWeights` instead.

    These weights are used in calculate_confidence_score() to determine
    the overall match confidence. The sum must equal 1.0.

    Note: These values are tuned based on empirical testing with anime filenames.
    This class is kept for backward compatibility but should be replaced with
    MatchingWeights from the configuration system.

    .. deprecated:: Use `MatchingWeights.scoring_*` attributes instead.
    """

    # Primary weights (sum = 1.0)
    # Deprecated: Use MatchingWeights.scoring_title_match instead
    TITLE_MATCH = 0.5  # Title similarity is most important
    # Deprecated: Use MatchingWeights.scoring_year_match instead
    YEAR_MATCH = 0.25  # Year match is important for accuracy
    # Deprecated: Use MatchingWeights.scoring_media_type_match instead
    MEDIA_TYPE_MATCH = 0.15  # Media type preference (tv vs movie)
    # Deprecated: Use MatchingWeights.scoring_popularity_match instead
    POPULARITY_MATCH = 0.1  # Popularity bonus for disambiguation

    # Legacy aliases (for backwards compatibility)
    GENRE_MATCH = MEDIA_TYPE_MATCH  # Deprecated: use MEDIA_TYPE_MATCH
    RATING_MATCH = POPULARITY_MATCH  # Deprecated: use POPULARITY_MATCH


class GenreConfig:
    """Genre-based filtering configuration.

    These constants control how the matching engine applies genre-based
    filtering and confidence boosting for animation content.
    """

    # TMDB genre IDs
    ANIMATION_GENRE_ID = 16  # TMDB Animation genre ID (verified with TMDB API)

    # Confidence boost for animation genre
    # This strong boost (0.5) ensures anime is prioritized over non-animation
    ANIMATION_BOOST = 0.5

    # Maximum confidence (safety cap)
    MAX_CONFIDENCE = 1.0


__all__ = [
    "ConfidenceThresholds",
    "DefaultLanguage",
    "FallbackStrategy",
    "GenreConfig",
    "MatchingAlgorithm",
    "MatchingFieldNames",
    "ScoringWeights",
    "TitleNormalization",
    "ValidationConfig",
    "ValidationConstants",
    "YearMatchingConfig",
]
