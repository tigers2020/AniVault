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

import functools
import logging
import re
import unicodedata
from typing import Any

from anivault.core.matching.models import NormalizedQuery
from anivault.shared.constants import NormalizationConfig
from anivault.shared.constants.core import LanguageDetectionConfig

logger = logging.getLogger(__name__)

# Compile whitespace patterns once at module level
_WHITESPACE_PATTERN = re.compile(r"[-\s]+")
_WHITESPACE_NORMALIZE_PATTERN = re.compile(r"\s+")


def normalize_query_from_anitopy(
    anitopy_result: dict[str, Any],
) -> NormalizedQuery | None:
    """Normalize an anitopy result into a NormalizedQuery domain object.

    This function processes an anitopy parse result through multiple stages to produce
    a clean, searchable title and extract year metadata.

    Args:
        anitopy_result: The result from anitopy.parse() containing anime metadata.

    Returns:
        NormalizedQuery domain object with validated title and optional year,
        or None if normalization fails.

    Examples:
        >>> result = anitopy.parse("[SubsPlease] Attack on Titan - 01 (1080p).mkv")
        >>> query = normalize_query_from_anitopy(result)
        >>> query.title
        'Attack on Titan'
        >>> query.year
        None
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

        # Extract year hint if available
        year_hint = anitopy_result.get("anime_year")
        if not year_hint:
            year_hint = anitopy_result.get("year")

        # Convert year to int if present
        year_int: int | None = None
        if year_hint is not None:
            try:
                year_int = int(year_hint)
            except (ValueError, TypeError):
                logger.debug("Failed to convert year hint to int: %s", year_hint)

        # Create NormalizedQuery domain object (validates title and year)
        from anivault.core.matching.models import NormalizedQuery

        try:
            normalized_query = NormalizedQuery(title=normalized_title, year=year_int)
        except ValueError as e:
            logger.warning("Failed to create NormalizedQuery: %s", str(e))
            return None

        logger.debug(
            "Normalized anitopy result: '%s' -> '%s' (year: %s)",
            title,
            normalized_title,
            year_int,
        )

        return normalized_query

    except Exception as e:  # noqa: BLE001
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

    except Exception as e:  # noqa: BLE001
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
    if isinstance(title, str) and title.strip():
        return title.strip()

    # Fallback to other possible title fields
    fallback_fields = ["title", "series_name", "show_name"]
    for field in fallback_fields:
        value = parsed_data.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    # If no title found, return empty string
    logger.debug("No title found in anitopy results: %s", parsed_data)
    return ""


@functools.lru_cache(maxsize=4096)
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

    # Get compiled patterns from NormalizationConfig
    patterns_to_remove = NormalizationConfig.get_compiled_patterns()

    cleaned = title
    for pattern in patterns_to_remove:
        cleaned = pattern.sub("", cleaned)

    # Clean up extra whitespace and separators
    cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned)
    cleaned = cleaned.strip()

    return cleaned


@functools.lru_cache(maxsize=4096)
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
    normalized = _WHITESPACE_NORMALIZE_PATTERN.sub(" ", normalized)
    normalized = normalized.strip()

    return normalized


def _detect_language(title: str) -> str:
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
    if japanese_ratio > LanguageDetectionConfig.JAPANESE_RATIO_THRESHOLD:
        return "ja"
    if korean_ratio > LanguageDetectionConfig.KOREAN_RATIO_THRESHOLD:
        return "ko"
    if latin_ratio > LanguageDetectionConfig.LATIN_RATIO_THRESHOLD:
        return "en"
    if hiragana_count > 0 or katakana_count > 0 or kanji_count > 0:
        return "ja"
    if korean_count > 0:
        return "ko"
    if latin_count > 0:
        return "en"
    return "unknown"
