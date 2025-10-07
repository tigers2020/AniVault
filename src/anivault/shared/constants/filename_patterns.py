"""Filename pattern constants for anime file processing.

This module contains all regex patterns and constants used for parsing
anime filenames, following the One Source of Truth principle.
"""

from __future__ import annotations

from typing import Final

# Release group patterns
RELEASE_GROUP_PATTERNS: Final[list[str]] = [
    r"^\[[^\]]+\]\s*",  # Remove leading [ReleaseGroup]
]

# Resolution and quality patterns
RESOLUTION_PATTERNS: Final[list[str]] = [
    r"\[(?:1080p|720p|480p|2160p|4K|HD|SD)\]",
    r"\((?:1080p|720p|480p|2160p|4K|HD|SD)\)",
    r"\(?\s*AT\s*[Xx]\s*\d{3,4}\s*[xX]\d{3,4}\s*\)?",
    r"\(?\s*ATX\s*[xX]\d{3,4}\s*\)?",
    r"\(?\s*ATXx\d{3,4}\s*\)?",
    r"\(?\s*\d{3,4}[xX]\d{3,4}\s*\)?",
    r"\(?\s*\d{3,4}[pP]\s*\)?",
]

# Codec patterns
CODEC_PATTERNS: Final[list[str]] = [
    r"\[(?:x264|x265|H\.264|H\.265)\]",
    r"\((?:x264|x265|H\.264|H\.265)\)",
    r"\(?\s*x\d{3,4}\s*\)?",
    r"\(?\s*x\d{3,4}-?\s*\)?",
    r"\(?\s*AAC\s*\)?",
    r"\(?\s*-AAC\s*\)?",
    r"\(?\s*AC3\s*\)?",
    r"\(?\s*DivX\d*\.?\d*\s*\)?",
]

# Audio patterns
AUDIO_PATTERNS: Final[list[str]] = [
    r"\[(?:AAC|AC3|FLAC|DTS)\]",
    r"\((?:AAC|AC3|FLAC|DTS)\)",
]

# Source patterns
SOURCE_PATTERNS: Final[list[str]] = [
    r"\[(?:RAW|WEB|BluRay|HDTV|DVD)\]",
    r"\((?:RAW|WEB|BluRay|HDTV|DVD)\)",
]

# Episode patterns
EPISODE_PATTERNS: Final[list[str]] = [
    r"\[(?:E\d+|Episode\s+\d+|Ep\s+\d+)\]",
    r"\((?:E\d+|Episode\s+\d+|Ep\s+\d+)\)",
    r"\(?\s*END\s*\)?",
    r"\(?\s*Part\s*\d+\s*\)?",
    # More specific episode patterns - only remove when clearly episode-related
    r"\s+E\d{1,3}\s*",  # E01, E02, etc. (limit to 1-3 digits)
    # Remove Episode patterns only when they're clearly episode numbers (1-3 digits)
    r"\s+Episode\s+\d{1,3}(?=\s|$|\[|\()",  # Episode 1, Episode 2, etc. (lookahead)
    r"\s+Ep\s+\d{1,3}\s*",  # Ep 1, Ep 2, etc. (limit to 1-3 digits)
]

# Season patterns
SEASON_PATTERNS: Final[list[str]] = [
    r"\[(?:Season\s+\d+|S\d+)\]",
    r"\((?:Season\s+\d+|S\d+)\)",
    # More specific season patterns - only remove when clearly season-related
    r"\s+Season\s+\d+\s*",  # Season 1, Season 2, etc.
    # Remove S01 from S01E01 format specifically
    r"(?<=\s)S\d+(?=E\d+)",  # S01 in S01E01 format (lookbehind and lookahead)
]

# Hash patterns
HASH_PATTERNS: Final[list[str]] = [
    r"\[[A-Fa-f0-9]{8,}\]",
    r"\([A-Fa-f0-9]{8,}\)",
]

# Special episode markers
SPECIAL_EPISODE_PATTERNS: Final[list[str]] = [
    r"\[(?:OVA|OAD|Special|SP)\]",
    r"\((?:OVA|OAD|Special|SP)\)",
]

# File extensions (backup)
FILE_EXTENSION_PATTERNS: Final[list[str]] = [
    r"\.(?:mkv|mp4|avi|mov|wmv|flv|webm|m4v|srt|smi|ass|vtt)$",
]

# Combined patterns for title cleaning
ALL_CLEANING_PATTERNS: Final[list[str]] = (
    RELEASE_GROUP_PATTERNS
    + RESOLUTION_PATTERNS
    + CODEC_PATTERNS
    + AUDIO_PATTERNS
    + SOURCE_PATTERNS
    + EPISODE_PATTERNS
    + SEASON_PATTERNS
    + HASH_PATTERNS
    + SPECIAL_EPISODE_PATTERNS
    + FILE_EXTENSION_PATTERNS
)

# Technical patterns for quality scoring
TECHNICAL_PATTERNS: Final[list[str]] = [
    r"\d{3,4}p",
    r"\d{3,4}x\d{3,4}",
    r"x264",
    r"x265",
    r"AAC",
    r"AC3",
    r"\[.*\]",
    r"\(.*\)",
    r"RAW",
    r"WEB",
    r"BluRay",
    r"HDTV",
]

# Additional cleanup patterns - more conservative approach
ADDITIONAL_CLEANUP_PATTERNS: Final[list[str]] = [
    r"\([^)]*[xX]264[^)]*\)",  # Only x264 codec patterns
    r"\([^)]*[xX]265[^)]*\)",  # Only x265 codec patterns
    r"\([^)]*AAC[^)]*\)",  # Only AAC audio patterns
    r"\([^)]*AC3[^)]*\)",  # Only AC3 audio patterns
]

# Conservative cleanup patterns - only remove clearly technical info
AGGRESSIVE_CLEANUP_PATTERNS: Final[list[str]] = [
    # Remove empty parentheses and brackets
    r"\(\s*\)",
    r"\[\s*\]",
]


# Quality scoring constants
class TitleQualityScores:
    """Constants for title quality scoring."""

    # Length factors
    GOOD_LENGTH_MIN: Final[int] = 5
    GOOD_LENGTH_MAX: Final[int] = 50
    BAD_LENGTH_PENALTY: Final[int] = -2
    GOOD_LENGTH_BONUS: Final[int] = 2

    # Technical info penalties
    TECHNICAL_PATTERN_PENALTY: Final[int] = -1

    # Special character limits
    MAX_SPECIAL_CHARS: Final[int] = 5
    SPECIAL_CHAR_PENALTY: Final[int] = -1

    # Quality bonuses
    TITLE_CASE_BONUS: Final[int] = 1
    JAPANESE_CHAR_BONUS: Final[int] = 1

    # Title selection thresholds
    SIGNIFICANT_QUALITY_DIFF: Final[int] = 2


# Group naming constants
class GroupNaming:
    """Constants for group naming and merging."""

    # Numbered suffix pattern
    NUMBERED_SUFFIX_PATTERN: Final[str] = r"^(.+?)\s*\(\d+\)$"

    # Group name generation
    UNKNOWN_GROUP_PREFIX: Final[str] = "unknown_"
    DUPLICATE_SUFFIX_FORMAT: Final[str] = " ({})"


class TitleSelectionThresholds:
    """Constants for title selection thresholds."""

    # Length reduction threshold for preferring shorter titles
    LENGTH_REDUCTION_THRESHOLD: Final[float] = 0.6


class TitlePatterns:
    """Constants for title pattern matching."""

    # Title case pattern
    TITLE_CASE_PATTERN: Final[str] = r"[A-Z][a-z]+.*[A-Z][a-z]+"

    # Japanese character pattern
    JAPANESE_CHAR_PATTERN: Final[str] = r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]"

    # Technical info split pattern
    TECHNICAL_SPLIT_PATTERN: Final[str] = r"\([^)]*(?:AT|[xX]\d+|AAC|DivX)"
