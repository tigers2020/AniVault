"""TMDB API utility functions.

This module provides utility functions for TMDB API operations,
including title processing and normalization.
"""

from __future__ import annotations

import re

# Patterns stripped from the end before building prefixes (episode/suffix noise)
_VERSION_SUFFIX_PATTERNS = [
    r"\s+v\d+$",  # v1, v2, etc.
    r"\s+version\s+\d+$",
    r"\s+\d{4}$",  # year at end
    r"\s+\(.*\)$",
    r"\s+\[.*\]$",
    r"\s+ext$",
    r"\s+special$",
    r"\s+ova$",
    r"\s+tv$",
]


def generate_title_prefixes(title: str) -> list[str]:
    """Generate title prefixes by adding words from the front (for fallback search).

    Filenames usually have the title first, then episode/subtitle info. Building
    the query from the front and using the shortest prefix that returns results
    gives the most accurate match (minimal sufficient query).

    Examples:
        >>> generate_title_prefixes("명탐정 코난 132화 마술 애호가 살인 사건")
        ['명탐정', '명탐정 코난', '명탐정 코난 132화', ...]
        >>> generate_title_prefixes("Attack on Titan")
        ['Attack', 'Attack on', 'Attack on Titan']

    Args:
        title: Original title (e.g. from filename).

    Returns:
        List of prefixes from shortest to longest (first word, then first two, ...).
        Empty list if title is empty or single-word (no fallback needed).
    """
    base = title.strip()
    for pattern in _VERSION_SUFFIX_PATTERNS:
        base = re.sub(pattern, "", base, flags=re.IGNORECASE)
    base = base.strip()
    if not base:
        return []

    words = base.split()
    if len(words) <= 1:
        return []

    prefixes = []
    acc = []
    for w in words:
        acc.append(w)
        prefixes.append(" ".join(acc))
    return prefixes


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

    base_title = title
    for pattern in _VERSION_SUFFIX_PATTERNS:
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
