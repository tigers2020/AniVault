"""Normalization-related constants."""

from __future__ import annotations

import re
from typing import ClassVar


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
        """
        if cls._compiled_patterns is None:
            patterns_to_compile = [
                *cls.RESOLUTION_PATTERNS,
                *cls.CODEC_PATTERNS,
                *cls.RELEASE_GROUP_PATTERNS,
                *cls.EPISODE_PATTERNS,
                *cls.SEASON_PATTERNS,
                *cls.SOURCE_PATTERNS,
                *cls.AUDIO_PATTERNS,
                *cls.HASH_PATTERNS,
                *cls.FILE_EXTENSION_PATTERNS,
                *cls.BRACKET_PATTERNS,
            ]

            cls._compiled_patterns = [re.compile(pattern, flags=re.IGNORECASE) for pattern in patterns_to_compile]

        return cls._compiled_patterns


__all__ = [
    "LanguageDetectionConfig",
    "NormalizationConfig",
    "SimilarityConfig",
]
