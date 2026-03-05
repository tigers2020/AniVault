"""
Matching Engine Constants

Domain grouping for matching-related constants (Phase 3-2).
"""

from typing import ClassVar

from anivault.shared.constants.system import BASE_SECOND


class ValidationConstants:
    """Validation constants for matching domain models."""

    MIN_VALID_YEAR = 1900
    FUTURE_YEAR_TOLERANCE = 5
    MIN_CONFIDENCE_SCORE = 0.0
    MAX_CONFIDENCE_SCORE = 1.0
    VALID_MEDIA_TYPES: ClassVar[list[str]] = ["tv", "movie"]


class YearMatchingConfig:
    """Year matching configuration constants."""

    YEAR_SCORE_MAX = 100
    YEAR_DIFF_UNKNOWN = 999
    YEAR_SCORE_UNKNOWN = 0


class MatchingFieldNames:
    """Internal field names used during matching process."""

    TITLE_SCORE = "title_score"
    YEAR_SCORE = "year_score"
    YEAR_DIFF = "year_diff"
    CONFIDENCE_SCORE = "confidence_score"
    PARTIAL_MATCH_SCORE = "partial_match_score"
    USED_PARTIAL_MATCHING = "used_partial_matching"
    MATCHING_METADATA = "matching_metadata"


class DefaultLanguage:
    """Default language configuration for TMDB API."""

    KOREAN = "ko-KR"
    JAPANESE = "ja-JP"
    ENGLISH = "en-US"


class ConfidenceThresholds:
    """Confidence threshold constants for matching."""

    HIGH = 0.8
    MEDIUM = 0.5
    LOW = 0.2
    ANIMATION_MIN = 0.2
    NON_ANIMATION_MIN = 0.8
    BENCHMARK_DEFAULT = 0.7
    BENCHMARK_HIGH = 0.9
    BENCHMARK_MEDIUM = 0.8


class ValidationConfig:
    """Validation configuration constants."""

    MIN_REQUIRED_KEYS = 2
    EXPECTED_ANITOPY_KEYS: ClassVar[list[str]] = [
        "anime_title",
        "episode_number",
        "release_group",
        "video_resolution",
    ]


class MatchingAlgorithm:
    """Matching algorithm configuration."""

    DEFAULT_FUZZY_THRESHOLD = 0.8
    DEFAULT_EXACT_MATCH_BONUS = 0.1
    DEFAULT_PARTIAL_MATCH_BONUS = 0.05
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


class GenreConfig:
    """Genre-based filtering configuration."""

    ANIMATION_GENRE_ID = 16
    ANIMATION_BOOST = 0.5
    MAX_CONFIDENCE = 1.0


__all__ = [
    "ConfidenceThresholds",
    "DefaultLanguage",
    "FallbackStrategy",
    "GenreConfig",
    "MatchingAlgorithm",
    "MatchingFieldNames",
    "TitleNormalization",
    "ValidationConfig",
    "ValidationConstants",
    "YearMatchingConfig",
]
