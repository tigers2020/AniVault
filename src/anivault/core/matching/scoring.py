"""Confidence scoring system for TMDB matching results.

This module provides functions to calculate confidence scores for potential matches
returned by the TMDB API, helping to determine the best match for a given query.
"""

from __future__ import annotations

import logging
from typing import Any

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def calculate_confidence_score(
    normalized_query: dict[str, Any],
    tmdb_result: dict[str, Any],
) -> float:
    """Calculate a confidence score for a TMDB result based on the normalized query.

    This function combines multiple scoring components to produce a final confidence
    score between 0.0 and 1.0, where 1.0 indicates a perfect match.

    Args:
        normalized_query: Dictionary containing normalized query data with keys:
            - title: Clean title for comparison
            - language: Detected language ('ja', 'ko', 'en', or 'unknown')
            - year: Year hint if available
        tmdb_result: Dictionary containing TMDB result data with keys:
            - title: TMDB title
            - release_date: Release date string (YYYY-MM-DD format)
            - media_type: Type of media ('tv' or 'movie')
            - popularity: Popularity score from TMDB
            - genres: List of genre dictionaries with 'name' key

    Returns:
        A confidence score between 0.0 and 1.0, where:
        - 1.0 = Perfect match
        - 0.8-0.99 = Very high confidence
        - 0.6-0.79 = High confidence
        - 0.4-0.59 = Medium confidence
        - 0.2-0.39 = Low confidence
        - 0.0-0.19 = Very low confidence

    Examples:
        >>> query = {"title": "Attack on Titan", "language": "en", "year": 2013}
        >>> result = {"title": "Attack on Titan", "release_date": "2013-04-07",
        ...           "media_type": "tv", "popularity": 85.2, "genres": [{"name": "Animation"}]}
        >>> calculate_confidence_score(query, result)
        0.95
    """
    try:
        # Check for empty query or result
        query_title = normalized_query.get("title", "")
        result_title = tmdb_result.get("title", "")

        if not query_title or not result_title:
            return 0.0

        # Calculate individual score components
        title_score = _calculate_title_score(query_title, result_title)
        year_score = _calculate_year_score(
            normalized_query.get("year"),
            tmdb_result.get("release_date"),
        )
        media_type_score = _calculate_media_type_score(tmdb_result.get("media_type"))
        popularity_bonus = _calculate_popularity_bonus(tmdb_result.get("popularity", 0))

        # Weighted aggregation (weights sum to 1.0)
        weights = {
            "title": 0.5,  # Title similarity is most important
            "year": 0.25,  # Year match is important for accuracy
            "media_type": 0.15,  # Media type preference
            "popularity": 0.1,  # Popularity bonus
        }

        # Calculate weighted average
        confidence_score = (
            title_score * weights["title"]
            + year_score * weights["year"]
            + media_type_score * weights["media_type"]
            + popularity_bonus * weights["popularity"]
        )

        # Ensure score is within bounds
        confidence_score = max(0.0, min(1.0, confidence_score))

        logger.debug(
            "Confidence score calculation: title=%.3f, year=%.3f, media_type=%.3f, "
            "popularity=%.3f, final=%.3f",
            title_score,
            year_score,
            media_type_score,
            popularity_bonus,
            confidence_score,
        )

        return confidence_score

    except Exception:
        logger.exception(
            "Error calculating confidence score for query '%s' and result '%s'",
            normalized_query.get("title", ""),
            tmdb_result.get("title", ""),
        )
        return 0.0


def _calculate_title_score(normalized_title: str, tmdb_title: str) -> float:
    """Calculate title similarity score using fuzzy matching.

    Args:
        normalized_title: Clean title from normalized query
        tmdb_title: Title from TMDB result

    Returns:
        A score between 0.0 and 1.0 based on title similarity
    """
    if not normalized_title or not tmdb_title:
        return 0.0

    # Use rapidfuzz ratio for title comparison
    # This gives a score from 0-100, so we normalize to 0-1
    similarity_ratio = fuzz.ratio(normalized_title.lower(), tmdb_title.lower())
    return float(similarity_ratio) / 100.0


def _calculate_year_score(query_year: int | None, release_date: str | None) -> float:
    """Calculate year match score.

    Args:
        query_year: Year from normalized query (if available)
        release_date: Release date string from TMDB (YYYY-MM-DD format)

    Returns:
        A score between 0.0 and 1.0 based on year match quality
    """
    if not query_year or not release_date:
        return 0.5  # Neutral score when year information is missing

    try:
        # Extract year from release date
        tmdb_year = int(release_date.split("-")[0])
        year_diff = abs(query_year - tmdb_year)

        # Year score mapping
        year_scores = {0: 1.0, 1: 0.8, 2: 0.6}
        if year_diff in year_scores:
            return year_scores[year_diff]
        if year_diff <= 5:
            return 0.4  # Reasonable year match
        return 0.1  # Poor year match

    except (ValueError, IndexError) as e:
        logger.warning(
            "Error parsing release date '%s': %s",
            release_date,
            str(e),
        )
        return 0.5  # Neutral score for invalid date format


def _calculate_media_type_score(media_type: str | None) -> float:
    """Calculate media type preference score.

    Args:
        media_type: Type of media from TMDB ('tv' or 'movie')

    Returns:
        A score between 0.0 and 1.0 based on media type preference
    """
    if not media_type:
        return 0.5  # Neutral score for unknown media type

    # Prefer TV shows for anime content
    if media_type == "tv":
        return 1.0
    if media_type == "movie":
        return 0.7
    return 0.5  # Neutral score for other media types


def _calculate_popularity_bonus(popularity: float) -> float:
    """Calculate popularity bonus score.

    Args:
        popularity: Popularity score from TMDB

    Returns:
        A bonus score between 0.0 and 0.2 based on popularity
    """
    if popularity <= 0:
        return 0.0

    # Normalize popularity to a 0-0.2 bonus range
    # TMDB popularity typically ranges from 0-100+
    # We cap the bonus at 0.2 to prevent it from overwhelming other factors
    normalized_popularity = min(popularity / 100.0, 1.0)
    return normalized_popularity * 0.2
