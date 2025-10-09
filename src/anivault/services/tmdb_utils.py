"""TMDB API utility functions.

This module provides utility functions for TMDB API operations,
including title processing and normalization.
"""

from __future__ import annotations

import re


def generate_shortened_titles(title: str) -> list[str]:
    """Generate shortened versions of the title for fallback search.

    Creates progressively shorter versions of the title by removing words
    from the end, useful for finding matches when the full title fails.

    Also removes common version patterns (v1, v2, year, OVA, etc.) before
    generating shortened variants.

    Examples:
        >>> generate_shortened_titles("Attack on Titan Season 2")
        ['Attack on Titan Season', 'Attack on Titan', 'Attack on']
        >>> generate_shortened_titles("Anime Title v2")
        ['Anime Title', 'Anime']

    Args:
        title: Original title to shorten

    Returns:
        List of shortened title variants, ordered by preference (longest first)
        Returns empty list if title has no spaces
    """
    # Split title into words
    words = title.strip().split()
    if len(words) <= 1:
        return []  # Cannot shorten single word titles

    shortened_titles = []

    # Remove common suffixes/versions
    version_patterns = [
        r"\s+v\d+$",  # v1, v2, etc.
        r"\s+version\s+\d+$",  # version 1, version 2, etc.
        r"\s+\d{4}$",  # year at end
        r"\s+\(.*\)$",  # parentheses at end
        r"\s+\[.*\]$",  # brackets at end
        r"\s+ext$",  # ext suffix
        r"\s+special$",  # special suffix
        r"\s+ova$",  # ova suffix
        r"\s+tv$",  # tv suffix
    ]

    base_title = title
    for pattern in version_patterns:
        base_title = re.sub(pattern, "", base_title, flags=re.IGNORECASE)

    # Add base title without version patterns
    if base_title.strip() != title.strip():
        shortened_titles.append(base_title.strip())

    # Generate progressive word removal (recursive trimming down to 1 word)
    current_words = words.copy()
    while len(current_words) > 1:
        current_words.pop()  # Remove last word
        shortened_titles.append(" ".join(current_words))

    # Remove duplicates while preserving order
    seen = set()
    unique_titles = []
    for title_var in shortened_titles:
        if title_var.lower() not in seen:
            seen.add(title_var.lower())
            unique_titles.append(title_var)

    return unique_titles

