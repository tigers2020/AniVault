"""Utility functions for parsing and normalizing anime-related data.

This module provides helper functions for processing parsed anime information,
including resolution parsing, title normalization, and data validation.
"""

import re


def parse_resolution_string(res_str: str | None) -> tuple[int | None, int | None]:
    """Parses a resolution string (e.g., '1080p', '1920x1080', '4K') into width and height.

    Assumes 16:9 aspect ratio for 'p' resolutions where width is not explicitly given.

    Args:
        res_str: Resolution string to parse (e.g., '1080p', '1920x1080', '4K')

    Returns:
        Tuple of (width, height) in pixels, or (None, None) if parsing fails

    Examples:
        >>> parse_resolution_string("1080p")
        (1920, 1080)
        >>> parse_resolution_string("1920x1080")
        (1920, 1080)
        >>> parse_resolution_string("4K")
        (3840, 2160)
        >>> parse_resolution_string("720p")
        (1280, 720)
    """
    if not res_str:
        return None, None

    res_str_lower = res_str.lower().strip()

    # Handle "1920x1080" format
    match_x = re.match(r"(\d+)[xX](\d+)", res_str_lower)
    if match_x:
        return int(match_x.group(1)), int(match_x.group(2))

    # Handle "1080p", "720p", "4k", "2160p" etc.
    if "p" in res_str_lower or "k" in res_str_lower:
        # Common standard resolutions (16:9 aspect ratio)
        if "2160p" in res_str_lower or "4k" in res_str_lower:
            return 3840, 2160
        if "1440p" in res_str_lower:
            return 2560, 1440  # QHD
        if "1080p" in res_str_lower:
            return 1920, 1080  # Full HD
        if "720p" in res_str_lower:
            return 1280, 720  # HD
        if "480p" in res_str_lower:
            return 854, 480  # SD (widescreen)
        if "360p" in res_str_lower:
            return 640, 360  # SD (widescreen)

        # Try to extract height if 'p' is present
        height_match = re.search(r"(\d+)p", res_str_lower)
        if height_match:
            try:
                height = int(height_match.group(1))
                # Fallback for less common 'p' resolutions, assuming 16:9
                width = int(height * (16 / 9))
                return width, height
            except ValueError:
                pass  # Not a simple 'p' resolution

    return None, None


def normalize_title(title: str) -> str:
    """Normalizes an anime title by cleaning up common artifacts.

    Args:
        title: Raw title string from parsing

    Returns:
        Normalized title string
    """
    if not title:
        return ""

    # Strip whitespace and common artifacts
    normalized = title.strip()

    # Remove common release group patterns that might leak into title
    # This is a basic cleanup - anitopy should handle most of this
    patterns_to_remove = [
        r"^\[.*?\]\s*",  # Remove leading [brackets]
        r"\s*\[.*?\]$",  # Remove trailing [brackets]
    ]

    for pattern in patterns_to_remove:
        normalized = re.sub(pattern, "", normalized)

    return normalized.strip()


def validate_episode_number(episode: int | None) -> int | None:
    """Validates and normalizes episode numbers.

    Args:
        episode: Raw episode number

    Returns:
        Validated episode number or None if invalid
    """
    if episode is None:
        return None

    # Episode numbers should be positive integers
    if isinstance(episode, int) and episode > 0:
        return episode

    return None


def validate_season_number(season: int | None) -> int | None:
    """Validates and normalizes season numbers.

    Args:
        season: Raw season number

    Returns:
        Validated season number or None if invalid
    """
    if season is None:
        return None

    # Season numbers should be positive integers
    if isinstance(season, int) and season > 0:
        return season

    return None


def validate_year(year: int | None) -> int | None:
    """Validates and normalizes year values.

    Args:
        year: Raw year value

    Returns:
        Validated year or None if invalid
    """
    if year is None:
        return None

    # Reasonable year range for anime (1900-2100)
    if isinstance(year, int) and 1900 <= year <= 2100:
        return year

    return None
