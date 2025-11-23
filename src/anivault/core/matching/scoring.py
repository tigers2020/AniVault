"""Confidence scoring system for TMDB matching results.

This module provides functions to calculate confidence scores for potential matches
returned by the TMDB API, helping to determine the best match for a given query.
"""

from __future__ import annotations

import logging

from rapidfuzz import fuzz

from anivault.core.matching.models import NormalizedQuery
from anivault.shared.constants.matching import ScoringWeights
from anivault.shared.constants.validation_constants import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    MAX_SCORE,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_TV,
)
from anivault.shared.errors import (
    AniVaultError,
    AniVaultParsingError,
    ErrorCode,
    ErrorContext,
)
from anivault.shared.models.tmdb_models import TMDBSearchResult

logger = logging.getLogger(__name__)


def calculate_confidence_score(
    normalized_query: NormalizedQuery,
    tmdb_result: TMDBSearchResult,
) -> float:
    """Calculate a confidence score for a TMDB result based on the normalized query.

    This function combines multiple scoring components to produce a final confidence
    score between 0.0 and 1.0, where 1.0 indicates a perfect match.

    **Graceful Degradation**: If scoring fails due to invalid/missing data or errors,
    returns 0.0 (no match) and logs the error. This allows the matching pipeline to
    continue evaluating other candidates rather than failing completely.

    Args:
        normalized_query: NormalizedQuery domain object containing:
            - title: Clean title for comparison
            - year: Year hint if available
        tmdb_result: TMDBSearchResult Pydantic model containing:
            - title/name: TMDB title (localized)
            - original_title/original_name: Original title
            - release_date/first_air_date: Release date string (YYYY-MM-DD format)
            - media_type: Type of media ('tv' or 'movie')
            - popularity: Popularity score from TMDB
            - genres: List of genre IDs

    Returns:
        A confidence score between 0.0 and 1.0, where:
        - 1.0 = Perfect match
        - 0.8-0.99 = Very high confidence
        - 0.6-0.79 = High confidence
        - 0.4-0.59 = Medium confidence
        - 0.2-0.39 = Low confidence
        - 0.0-0.19 = Very low confidence

        Returns 0.0 if:
        - Empty/missing title in query or result (normal case)
        - Data processing error occurs (graceful degradation with logging)

    Examples:
        >>> query = NormalizedQuery(title="Attack on Titan", year=2013)
        >>> result = TMDBSearchResult(id=1429, media_type="tv", title="Attack on Titan",
        ...           release_date="2013-04-07", popularity=85.2, ...)
        >>> calculate_confidence_score(query, result)
        0.95
    """
    try:
        # Validate input
        if not _is_valid_input(normalized_query, tmdb_result):
            return 0.0

        # Calculate individual scores
        title_score = _calculate_title_scores(normalized_query.title, tmdb_result)
        year_score = _calculate_year_score(
            normalized_query.year,
            tmdb_result.display_date,
        )
        media_type_score = _calculate_media_type_score(tmdb_result.media_type)
        popularity_bonus = _calculate_popularity_bonus(tmdb_result.popularity)

        # Aggregate scores
        confidence_score = _aggregate_scores(
            title_score,
            year_score,
            media_type_score,
            popularity_bonus,
        )

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

    except (KeyError, ValueError, AttributeError, TypeError, IndexError) as e:
        # Handle specific data processing/parsing errors

        context = ErrorContext(
            operation="calculate_confidence_score",
            additional_data={
                "query_title": normalized_query.title,
                "result_title": tmdb_result.title or tmdb_result.name or "Unknown",
                "error_type": "data_parsing",
            },
        )
        error = AniVaultParsingError(
            ErrorCode.DATA_PROCESSING_ERROR,
            f"Failed to calculate confidence score due to data parsing error: {e}",
            context,
            original_error=e,
        )
        logger.exception(
            "Error calculating confidence score for query '%s' and result '%s'",
            normalized_query.title,
            tmdb_result.title or tmdb_result.name or "Unknown",
        )
        return 0.0
    except Exception as e:
        # Handle unexpected errors

        context = ErrorContext(
            operation="calculate_confidence_score",
            additional_data={
                "query_title": normalized_query.title,
                "result_title": tmdb_result.title or tmdb_result.name or "Unknown",
                "error_type": "unexpected",
            },
        )
        error = AniVaultError(
            ErrorCode.DATA_PROCESSING_ERROR,
            f"Unexpected error calculating confidence score: {e}",
            context,
            original_error=e,
        )
        logger.exception(
            "Unexpected error calculating confidence score for query '%s' and result '%s'",
            normalized_query.title,
            tmdb_result.title or tmdb_result.name or "Unknown",
        )
        return 0.0


def _is_valid_input(
    normalized_query: NormalizedQuery,
    tmdb_result: TMDBSearchResult,
) -> bool:
    """Validate input for confidence score calculation.

    Args:
        normalized_query: NormalizedQuery domain object
        tmdb_result: TMDBSearchResult Pydantic model

    Returns:
        True if input is valid, False otherwise
    """
    query_title = normalized_query.title
    localized_title = tmdb_result.title or tmdb_result.name or ""
    original_title = tmdb_result.original_title or tmdb_result.original_name or ""

    return bool(query_title and (localized_title or original_title))


def _calculate_title_scores(
    query_title: str,
    tmdb_result: TMDBSearchResult,
) -> float:
    """Calculate title similarity scores for both localized and original titles.

    Args:
        query_title: Clean title from normalized query
        tmdb_result: TMDB search result

    Returns:
        Maximum title score between 0.0 and 1.0
    """
    localized_title = tmdb_result.title or tmdb_result.name or ""
    original_title = tmdb_result.original_title or tmdb_result.original_name or ""

    title_scores = []

    if localized_title:
        localized_score = _calculate_title_score(query_title, localized_title)
        title_scores.append(localized_score)
        logger.debug(
            "📊 Localized title score: %.3f ('%s' vs '%s')",
            localized_score,
            query_title[:30],
            localized_title[:30],
        )

    if original_title:
        original_score = _calculate_title_score(query_title, original_title)
        title_scores.append(original_score)
        logger.debug(
            "📊 Original title score: %.3f ('%s' vs '%s')",
            original_score,
            query_title[:30],
            original_title[:30],
        )

    title_score = max(title_scores) if title_scores else 0.0
    logger.debug("🎯 Final title score (max): %.3f", title_score)

    return title_score


def _aggregate_scores(
    title_score: float,
    year_score: float,
    media_type_score: float,
    popularity_bonus: float,
) -> float:
    """Aggregate individual scores into final confidence score.

    Args:
        title_score: Title similarity score (0.0-1.0)
        year_score: Year match score (0.0-1.0)
        media_type_score: Media type preference score (0.0-1.0)
        popularity_bonus: Popularity bonus score (0.0-0.2)

    Returns:
        Final confidence score between 0.0 and 1.0
    """
    # Weighted aggregation using centralized constants (weights sum to 1.0)
    # Note: These weights are defined in shared.constants.matching.ScoringWeights
    # and are tuned based on empirical testing with anime filenames
    confidence_score = (
        title_score * ScoringWeights.TITLE_MATCH
        + year_score * ScoringWeights.YEAR_MATCH
        + media_type_score * ScoringWeights.MEDIA_TYPE_MATCH
        + popularity_bonus * ScoringWeights.POPULARITY_MATCH
    )

    # Ensure score is within bounds
    return max(0.0, min(1.0, confidence_score))


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
    return float(similarity_ratio) / MAX_SCORE


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
        reasonable_year_diff_threshold = 5

        if year_diff in year_scores:
            return year_scores[year_diff]
        if year_diff <= reasonable_year_diff_threshold:
            return DEFAULT_CONFIDENCE_THRESHOLD  # Reasonable year match
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
    if media_type == MEDIA_TYPE_TV:
        return 1.0
    if media_type == MEDIA_TYPE_MOVIE:
        return DEFAULT_CONFIDENCE_THRESHOLD
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
    normalized_popularity = min(popularity / MAX_SCORE, 1.0)
    return normalized_popularity * 0.2
