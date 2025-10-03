"""
Matching Engine Constants

This module contains all constants related to the matching engine,
confidence thresholds, and scoring algorithms.
"""

from typing import ClassVar

from .system import BASE_SECOND


class ConfidenceThresholds:
    """Confidence threshold constants for matching."""

    # Base confidence levels
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4

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
    """Scoring weight configuration for matching."""

    TITLE_MATCH = 0.4
    YEAR_MATCH = 0.3
    GENRE_MATCH = 0.2
    RATING_MATCH = 0.1


__all__ = ["ConfidenceThresholds", "MatchingAlgorithm", "ScoringWeights"]
