"""Query normalization module for AniVault.

This module provides functionality to process raw filenames or anitopy parse results
into standardized search queries for the TMDB API. It serves as the first step in
the matching pipeline, ensuring consistent and clean query strings for optimal
search results.

The normalization process includes:
1. Title extraction from anitopy results
2. Removal of superfluous metadata (resolution, codecs, release groups)
3. Unicode and character normalization
4. Basic language detection
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

logger = logging.getLogger(__name__)


def normalize_query_from_anitopy(
    anitopy_result: dict[str, Any],
) -> dict[str, Any] | None:
    """Normalize an anitopy result into a standardized search query for TMDB API.

    This function processes an anitopy parse result through multiple stages to produce
    a clean, searchable title and detect the language.

    Args:
        anitopy_result: The result from anitopy.parse() containing anime metadata.

    Returns:
        A dictionary containing normalized query data with keys:
        - title: Clean title suitable for TMDB search
        - language: Detected language ('ja', 'ko', 'en', or 'unknown')
        - year: Year hint if available
        - original_data: The original anitopy result

    Examples:
        >>> result = anitopy.parse("[SubsPlease] Attack on Titan - 01 (1080p).mkv")
        >>> normalize_query_from_anitopy(result)
        {'title': 'Attack on Titan', 'language': 'en', 'year': None, 'original_data': {...}}
    """
    try:
        # Extract title from anitopy results
        title = _extract_title_from_anitopy(anitopy_result)

        if not title:
            logger.warning("No title found in anitopy result")
            return None

        # Remove superfluous metadata
        cleaned_title = _remove_metadata(title)

        # Normalize characters and Unicode
        normalized_title = _normalize_characters(cleaned_title)

        # Detect language
        language = _detect_language(normalized_title)

        # Extract year hint if available
        year_hint = anitopy_result.get("anime_year")
        if not year_hint:
            year_hint = anitopy_result.get("year")

        result = {
            "title": normalized_title,
            "language": language,
            "year": year_hint,
            "original_data": anitopy_result,
        }

        logger.debug(
            "Normalized anitopy result: '%s' -> '%s' (%s)",
            title,
            normalized_title,
            language,
        )

        return result

    except Exception as e:
        logger.warning(
            "Failed to normalize anitopy result '%s': %s",
            anitopy_result,
            str(e),
        )
        return None


def normalize_query(filename: str) -> tuple[str, str]:
    """Normalize a filename into a standardized search query for TMDB API.

    This is the main entry point for the normalization pipeline. It processes
    a raw filename through multiple stages to produce a clean, searchable title
    and detect the language.

    Args:
        filename: The raw filename to normalize.

    Returns:
        A tuple containing (normalized_title, language_code) where:
        - normalized_title: Clean title suitable for TMDB search
        - language_code: Detected language ('ja', 'ko', 'en', or 'unknown')

    Examples:
        >>> normalize_query("[SubsPlease] Attack on Titan - 01 (1080p).mkv")
        ('Attack on Titan', 'en')
        >>> normalize_query("進撃の巨人 - 01 [1080p].mkv")
        ('進撃の巨人', 'ja')
    """
    try:
        # Parse with anitopy to extract structured data
        import anitopy

        parsed_data = anitopy.parse(filename)

        # Extract title from anitopy results
        title = _extract_title_from_anitopy(parsed_data)

        # Remove superfluous metadata
        cleaned_title = _remove_metadata(title)

        # Normalize characters and Unicode
        normalized_title = _normalize_characters(cleaned_title)

        # Detect language
        language = _detect_language(normalized_title)

        logger.debug(
            "Normalized query: '%s' -> '%s' (%s)",
            filename,
            normalized_title,
            language,
        )

        return normalized_title, language

    except Exception as e:
        logger.warning(
            "Failed to normalize query '%s': %s. Using filename as fallback.",
            filename,
            str(e),
        )
        # Fallback to basic processing of the filename
        cleaned = _remove_metadata(filename)
        normalized = _normalize_characters(cleaned)
        language = _detect_language(normalized)
        return normalized, language


def _extract_title_from_anitopy(parsed_data: dict[str, Any]) -> str:
    """Extract the anime title from anitopy parse results.

    Args:
        parsed_data: Dictionary output from anitopy.parse().

    Returns:
        Extracted title string, or empty string if not found.
    """
    # Try to get anime_title first
    title = parsed_data.get("anime_title")

    if title and isinstance(title, str) and title.strip():
        return title.strip()

    # Fallback to other possible title fields
    fallback_fields = ["title", "series_name", "show_name"]
    for field in fallback_fields:
        value = parsed_data.get(field)
        if value and isinstance(value, str) and value.strip():
            return value.strip()

    # If no title found, return empty string
    logger.debug("No title found in anitopy results: %s", parsed_data)
    return ""


def _remove_metadata(title: str) -> str:
    """Remove superfluous metadata from a title string.

    This function removes common patterns found in anime filenames that are
    not part of the actual title, such as resolution, codecs, release groups,
    and episode numbers.

    Args:
        title: The title string to clean.

    Returns:
        Cleaned title with metadata removed.
    """
    if not title:
        return title

    # Remove common patterns in brackets and parentheses
    patterns_to_remove = [
        # Resolution patterns
        r"\[(?:1080p|720p|480p|2160p|4K|HD|SD)\]",
        r"\((?:1080p|720p|480p|2160p|4K|HD|SD)\)",
        # Codec patterns
        r"\[(?:x264|x265|H\.264|H\.265|HEVC|AVC|VP9|AV1)\]",
        r"\((?:x264|x265|H\.264|H\.265|HEVC|AVC|VP9|AV1)\)",
        # Release group patterns (common groups)
        r"\[(?:SubsPlease|HorribleSubs|EMBER|Erai-raws|AnimeTime|Judas)\]",
        r"\((?:SubsPlease|HorribleSubs|EMBER|Erai-raws|AnimeTime|Judas)\)",
        # Episode patterns
        r"\[(?:E\d+|Episode\s+\d+|Ep\s+\d+)\]",
        r"\((?:E\d+|Episode\s+\d+|Ep\s+\d+)\)",
        r"\s+\d+\s*",  # Episode numbers anywhere
        # Season patterns
        r"\[(?:S\d+|Season\s+\d+)\]",
        r"\((?:S\d+|Season\s+\d+)\)",
        # Source patterns
        r"\[(?:BluRay|WEB|HDTV|DVD|BD)\]",
        r"\((?:BluRay|WEB|HDTV|DVD|BD)\)",
        # Audio patterns
        r"\[(?:AAC|FLAC|MP3|DTS|AC3|5\.1|2\.0)\]",
        r"\((?:AAC|FLAC|MP3|DTS|AC3|5\.1|2\.0)\)",
        # Hash patterns
        r"\[[A-Fa-f0-9]{8,}\]",
        r"\([A-Fa-f0-9]{8,}\)",
        # File extensions
        r"\.(?:mkv|mp4|avi|mov|wmv|flv|webm|m4v)$",
        # Generic bracketed content (be more careful with this)
        r"\[[^\]]*\]",
        r"\([^)]*\)",
    ]

    cleaned = title
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Clean up extra whitespace and separators
    cleaned = re.sub(r"[-\s]+", " ", cleaned)
    cleaned = cleaned.strip()

    return cleaned


def _normalize_characters(title: str) -> str:
    """Normalize Unicode characters and standardize formatting.

    This function applies Unicode normalization and standardizes various
    character representations to ensure consistency.

    Args:
        title: The title string to normalize.

    Returns:
        Normalized title string.
    """
    if not title:
        return title

    # Apply Unicode normalization (NFC)
    normalized = unicodedata.normalize("NFC", title)

    # Replace full-width characters with half-width equivalents
    # ruff: noqa: RUF001 (Full-width characters are intentional for normalization)
    fullwidth_to_halfwidth = {
        "（": "(",
        "）": ")",
        "［": "[",
        "］": "]",
        "｛": "{",
        "｝": "}",
        "「": '"',
        "」": '"',
        "『": "'",
        "』": "'",
        "：": ":",
        "；": ";",
        "，": ",",
        "。": ".",
        "？": "?",
        "！": "!",
        "～": "~",
        "－": "-",
        "　": " ",  # Full-width space
    }

    for fullwidth, halfwidth in fullwidth_to_halfwidth.items():
        normalized = normalized.replace(fullwidth, halfwidth)

    # Standardize different bracket types to square brackets
    bracket_replacements = {
        "【": "[",
        "】": "]",
        "「": "[",
        "」": "]",
        "『": "[",
        "』": "]",
    }

    for old_bracket, new_bracket in bracket_replacements.items():
        normalized = normalized.replace(old_bracket, new_bracket)

    # Clean up extra whitespace
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip()

    return normalized


def _detect_language(title: str) -> str:  # noqa: PLR0911
    """Detect the language of a title string.

    This function performs basic language detection based on character
    patterns to determine if the title is Japanese, Korean, or English.

    Args:
        title: The title string to analyze.

    Returns:
        Language code: 'ja' for Japanese, 'ko' for Korean, 'en' for English,
        or 'unknown' if detection fails.
    """
    if not title:
        return "unknown"

    # Count different character types
    hiragana_count = len(re.findall(r"[\u3040-\u309F]", title))
    katakana_count = len(re.findall(r"[\u30A0-\u30FF]", title))
    kanji_count = len(re.findall(r"[\u4E00-\u9FAF]", title))
    korean_count = len(re.findall(r"[\uAC00-\uD7AF]", title))
    latin_count = len(re.findall(r"[a-zA-Z]", title))

    total_chars = len(title)

    if total_chars == 0:
        return "unknown"

    # Calculate character type ratios
    japanese_chars = hiragana_count + katakana_count + kanji_count
    japanese_ratio = japanese_chars / total_chars

    korean_ratio = korean_count / total_chars
    latin_ratio = latin_count / total_chars

    # Determine language based on dominant character type
    if japanese_ratio > 0.3:  # 30% threshold for Japanese
        return "ja"
    if korean_ratio > 0.3:  # 30% threshold for Korean
        return "ko"
    if latin_ratio > 0.5:  # 50% threshold for English
        return "en"
    if hiragana_count > 0 or katakana_count > 0 or kanji_count > 0:
        return "ja"
    if korean_count > 0:
        return "ko"
    if latin_count > 0:
        return "en"
    return "unknown"
