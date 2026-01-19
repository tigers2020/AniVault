"""Filtering functions for TMDB matching candidates.

This module provides pure functions for filtering TMDB search results
based on various criteria (year, genre, substring matching, etc.).

All functions are pure (no side effects) for easy testing and composition.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rapidfuzz import fuzz

from anivault.core.matching.models import NormalizedQuery
from anivault.shared.constants import GenreConfig
from anivault.shared.models.api.tmdb import TMDBSearchResult

if TYPE_CHECKING:
    from anivault.core.matching.services.sort_cache import SortCache

logger = logging.getLogger(__name__)

# Year tolerance for filtering (years)
YEAR_FILTER_TOLERANCE = 10  # Allow ±10 years for anime (long-running series, prequels, etc.)


def filter_and_sort_by_year(
    candidates: list[TMDBSearchResult],
    normalized_query: NormalizedQuery,
    sort_cache: SortCache | None = None,
) -> list[TMDBSearchResult]:
    """Filter candidates by year proximity and sort them.

    Candidates within the year tolerance are kept and sorted by year difference.
    If year is not available in query, all candidates are returned unsorted.

    Args:
        candidates: List of TMDB search results
        normalized_query: Normalized query containing year hint
        sort_cache: Optional sort cache for optimizing repeated sorts

    Returns:
        Filtered and sorted list of candidates (closest year first)
    """
    query_year = normalized_query.year

    # If no year in query, return all candidates
    if not query_year:
        return candidates

    # Filter by year tolerance
    filtered = []
    for candidate in candidates:
        # Extract year from release_date or first_air_date
        candidate_year = _extract_year_from_candidate(candidate)

        if not candidate_year:
            # Keep candidates without year
            filtered.append(candidate)
            continue

        # Check year difference
        year_diff = abs(candidate_year - query_year)
        if year_diff <= YEAR_FILTER_TOLERANCE:
            filtered.append(candidate)
            logger.debug(
                "Year match: query=%s, candidate=%s (diff=%s)",
                query_year,
                candidate_year,
                year_diff,
            )

    # Sort by year proximity (closest first)
    def year_sort_key(candidate: TMDBSearchResult) -> tuple[int, int]:
        candidate_year = _extract_year_from_candidate(candidate)
        if not candidate_year:
            return (999, 0)  # Candidates without year go to end
        year_diff = abs(candidate_year - query_year)
        return (year_diff, candidate_year)

    # Use cache if available
    if sort_cache is not None:
        sort_criteria = f"year_{query_year}"
        filtered = sort_cache.get_or_compute_sorted(
            filtered,
            sort_criteria,
            year_sort_key,
        )
    else:
        # Fallback to direct sort (no cache)
        filtered.sort(key=year_sort_key)

    return filtered


def apply_genre_filter(
    candidates: list[TMDBSearchResult],
    genre_ids: list[int] | None = None,
) -> list[TMDBSearchResult]:
    """Filter candidates by genre (anime/animation).

    Args:
        candidates: List of TMDB search results
        genre_ids: List of anime genre IDs (default: GenreConfig.ANIMATION_GENRE_IDS)

    Returns:
        Filtered list containing only candidates with anime/animation genres
    """
    if genre_ids is None:
        genre_ids = [GenreConfig.ANIMATION_GENRE_ID]

    filtered = []
    for candidate in candidates:
        candidate_genres = candidate.genre_ids or []

        # Check if any animation genre is present
        if any(genre_id in candidate_genres for genre_id in genre_ids):
            filtered.append(candidate)
            logger.debug(
                "Genre match: candidate has animation genre (genres=%s)",
                candidate_genres,
            )

    return filtered


def apply_partial_substring_match(
    query_title: str,
    candidates: list[TMDBSearchResult],
    min_similarity: float = 0.6,
) -> list[TMDBSearchResult]:
    """Apply partial substring matching as a fallback strategy.

    Uses fuzzy partial ratio to find candidates where the query is
    a significant substring of the candidate title.

    Args:
        query_title: Query title to match
        candidates: List of TMDB search results
        min_similarity: Minimum partial ratio score (0.0-1.0, default: 0.6)

    Returns:
        Filtered list of candidates with partial matches
    """
    matched = []

    for candidate in candidates:
        candidate_title = _get_candidate_title(candidate)

        if not candidate_title:
            continue

        # Calculate partial ratio (query as substring of candidate)
        partial_score = (
            fuzz.partial_ratio(
                query_title.lower(),
                candidate_title.lower(),
            )
            / 100.0
        )

        if partial_score >= min_similarity:
            matched.append(candidate)
            logger.debug(
                "Partial match: '%s' in '%s' (score=%.2f)",
                query_title[:30],
                candidate_title[:30],
                partial_score,
            )

    return matched


def _extract_year_from_candidate(candidate: TMDBSearchResult) -> int | None:
    """Extract year from candidate's release date.

    Args:
        candidate: TMDB search result

    Returns:
        Year as integer or None if not available
    """
    # Try release_date (movies) or first_air_date (TV)
    date_str = candidate.release_date or candidate.first_air_date

    if not date_str:
        return None

    try:
        # Extract year from YYYY-MM-DD format
        return int(date_str.split("-")[0])
    except (ValueError, IndexError):
        return None


def _get_candidate_title(candidate: TMDBSearchResult) -> str:
    """Get candidate title (localized or original).

    Args:
        candidate: TMDB search result

    Returns:
        Title string (prefers localized, falls back to original)
    """
    return candidate.title or candidate.name or candidate.original_title or candidate.original_name or ""
