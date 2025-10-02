"""
Matching Engine Constants

This module contains all constants related to the matching engine,
confidence thresholds, and scoring algorithms.
"""

# Confidence Thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.8  # High confidence threshold
MEDIUM_CONFIDENCE_THRESHOLD = 0.6  # Medium confidence threshold
LOW_CONFIDENCE_THRESHOLD = 0.4  # Low confidence threshold

# Minimum Required Keys for Validation
MIN_REQUIRED_KEYS = 2  # minimum number of required keys for anitopy validation

# Expected Keys for Anitopy Validation
EXPECTED_ANITOPY_KEYS = [
    "anime_title",
    "episode_number",
    "release_group",
    "video_resolution",
]

# Matching Algorithm Configuration
DEFAULT_FUZZY_THRESHOLD = 0.8  # default fuzzy matching threshold
DEFAULT_EXACT_MATCH_BONUS = 0.1  # bonus score for exact matches
DEFAULT_PARTIAL_MATCH_BONUS = 0.05  # bonus score for partial matches

# Genre Filtering
GENRE_FILTER_THRESHOLD = 0.7  # threshold for genre-based filtering
ANIME_GENRE_KEYWORDS = ["animation", "anime", "cartoon", "manga", "japanese animation"]

# Title Normalization
MAX_TITLE_LENGTH = 100  # maximum title length for normalization
MIN_TITLE_LENGTH = 2  # minimum title length for normalization

# Fallback Strategy Configuration
FALLBACK_STRATEGY_TIMEOUT = 5.0  # timeout for fallback strategies in seconds
MAX_FALLBACK_ATTEMPTS = 3  # maximum number of fallback attempts

# Scoring Weights
TITLE_MATCH_WEIGHT = 0.4  # weight for title matching
YEAR_MATCH_WEIGHT = 0.3  # weight for year matching
GENRE_MATCH_WEIGHT = 0.2  # weight for genre matching
RATING_MATCH_WEIGHT = 0.1  # weight for rating matching

# Benchmark Configuration
DEFAULT_BENCHMARK_CONFIDENCE_THRESHOLD = (
    0.7  # default confidence threshold for benchmarks
)
HIGH_BENCHMARK_CONFIDENCE_THRESHOLD = 0.9  # high confidence threshold for benchmarks
MEDIUM_BENCHMARK_CONFIDENCE_THRESHOLD = (
    0.8  # medium confidence threshold for benchmarks
)
