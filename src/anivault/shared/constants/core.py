"""
Core Business Logic Constants

This module contains all constants related to core business logic,
processing rules, and application behavior.
"""

from __future__ import annotations

import re
from typing import ClassVar


class BusinessRules:
    """Business logic constants."""

    # Score thresholds
    HIGH_SCORE_THRESHOLD = 8.5
    MEDIUM_SCORE_THRESHOLD = 6.0
    LOW_SCORE_THRESHOLD = 4.0

    # Title length limits
    MAX_TITLE_LENGTH = 100
    MIN_TITLE_LENGTH = 1

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.9
    MEDIUM_CONFIDENCE_THRESHOLD = 0.7
    LOW_CONFIDENCE_THRESHOLD = 0.5

    # Matching thresholds
    EXACT_MATCH_THRESHOLD = 0.95
    FUZZY_MATCH_THRESHOLD = 0.8
    MIN_MATCH_THRESHOLD = 0.3


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


# =============================================================================
# CACHE CONFIGURATION (Moved to cache.py)
# =============================================================================

# Cache configuration is now centralized in cache.py
# Import CoreCacheConfig from cache module


class LanguageDetectionConfig:
    """Language detection configuration constants."""

    # Character type thresholds for language detection
    JAPANESE_RATIO_THRESHOLD = 0.3
    KOREAN_RATIO_THRESHOLD = 0.3
    LATIN_RATIO_THRESHOLD = 0.5


class SimilarityConfig:
    """Similarity calculation configuration constants."""

    # Default similarity threshold for file grouping
    DEFAULT_SIMILARITY_THRESHOLD = 0.7


class NormalizationConfig:
    """Title normalization configuration constants."""

    # Regex patterns for metadata removal
    RESOLUTION_PATTERNS: ClassVar[list[str]] = [
        r"\[(?:1080p|720p|480p|2160p|4K|HD|SD)\]",
        r"\((?:1080p|720p|480p|2160p|4K|HD|SD)\)",
    ]

    CODEC_PATTERNS: ClassVar[list[str]] = [
        r"\[(?:x264|x265|H\.264|H\.265|HEVC|AVC|VP9|AV1)\]",
        r"\((?:x264|x265|H\.264|H\.265|HEVC|AVC|VP9|AV1)\)",
    ]

    RELEASE_GROUP_PATTERNS: ClassVar[list[str]] = [
        r"\[(?:SubsPlease|HorribleSubs|EMBER|Erai-raws|AnimeTime|Judas)\]",
        r"\((?:SubsPlease|HorribleSubs|EMBER|Erai-raws|AnimeTime|Judas)\)",
    ]

    EPISODE_PATTERNS: ClassVar[list[str]] = [
        r"\[(?:E\d+|Episode\s+\d+|Ep\s+\d+)\]",
        r"\((?:E\d+|Episode\s+\d+|Ep\s+\d+)\)",
        r"(?:\s*-\s*\d+)$",
        r"(?:\s+\d+\s*$)",
    ]

    SEASON_PATTERNS: ClassVar[list[str]] = [
        r"\[(?:S\d+|Season\s+\d+)\]",
        r"\((?:S\d+|Season\s+\d+)\)",
    ]

    SOURCE_PATTERNS: ClassVar[list[str]] = [
        r"\[(?:BluRay|WEB|HDTV|DVD|BD)\]",
        r"\((?:BluRay|WEB|HDTV|DVD|BD)\)",
    ]

    AUDIO_PATTERNS: ClassVar[list[str]] = [
        r"\[(?:AAC|FLAC|MP3|DTS|AC3|5\.1|2\.0)\]",
        r"\((?:AAC|FLAC|MP3|DTS|AC3|5\.1|2\.0)\)",
    ]

    HASH_PATTERNS: ClassVar[list[str]] = [
        r"\[[A-Fa-f0-9]{8,}\]",
        r"\([A-Fa-f0-9]{8,}\)",
    ]

    FILE_EXTENSION_PATTERNS: ClassVar[list[str]] = [
        r"\.(?:mkv|mp4|avi|mov|wmv|flv|webm|m4v)$",
    ]

    # Generic patterns
    BRACKET_PATTERNS: ClassVar[list[str]] = [
        r"\[[^\]]*\]",
        r"\([^)]*\)",
    ]

    # Compiled patterns cache (lazy initialization)
    _compiled_patterns: ClassVar[list[re.Pattern[str]] | None] = None

    @classmethod
    def get_compiled_patterns(cls) -> list[re.Pattern[str]]:
        """Get compiled regex patterns for metadata removal.

        Compiles all pattern strings into regex Pattern objects for efficient reuse.
        Uses lazy initialization to compile patterns only once.

        Security Note:
            All patterns have been reviewed for ReDoS (Regular Expression Denial of Service)
            vulnerabilities. Patterns use:
            - Fixed strings or limited character classes (e.g., [^\\]]*, [^)]*)
            - No nested quantifiers (e.g., (a+)+)
            - No overlapping quantifiers that could cause catastrophic backtracking
            - Bounded quantifiers where applicable (e.g., {8,} for hash patterns)

        Returns:
            List of compiled regex Pattern objects.

        Example:
            >>> patterns = NormalizationConfig.get_compiled_patterns()
            >>> len(patterns) > 0
            True
        """
        if cls._compiled_patterns is None:
            # Compile all patterns once
            # Note: All patterns have been reviewed for ReDoS safety
            patterns_to_compile = [
                # Resolution patterns - Fixed strings, safe
                *cls.RESOLUTION_PATTERNS,
                # Codec patterns - Fixed strings, safe
                *cls.CODEC_PATTERNS,
                # Release group patterns - Fixed strings, safe
                *cls.RELEASE_GROUP_PATTERNS,
                # Episode patterns - Bounded quantifiers (\d+), safe
                *cls.EPISODE_PATTERNS,
                # Season patterns - Bounded quantifiers (\d+), safe
                *cls.SEASON_PATTERNS,
                # Source patterns - Fixed strings, safe
                *cls.SOURCE_PATTERNS,
                # Audio patterns - Fixed strings, safe
                *cls.AUDIO_PATTERNS,
                # Hash patterns - Bounded quantifier ({8,}), safe
                *cls.HASH_PATTERNS,
                # File extensions - Fixed strings, safe
                *cls.FILE_EXTENSION_PATTERNS,
                # Generic bracketed content - Character class [^\]]*, safe
                # Note: [^\]]* uses negated character class, which is efficient
                # and safe from ReDoS as it doesn't cause catastrophic backtracking
                *cls.BRACKET_PATTERNS,
            ]

            cls._compiled_patterns = [re.compile(pattern, flags=re.IGNORECASE) for pattern in patterns_to_compile]

        return cls._compiled_patterns
