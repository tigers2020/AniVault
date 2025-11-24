"""Candidate filtering service for matching engine.

This module provides the CandidateFilterService class that encapsulates
filtering logic based on year, genre, and other criteria.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from anivault.core.matching.filters import apply_genre_filter, filter_and_sort_by_year
from anivault.core.matching.models import NormalizedQuery
from anivault.core.statistics import StatisticsCollector
from anivault.shared.models.tmdb_models import ScoredSearchResult, TMDBSearchResult

logger = logging.getLogger(__name__)


class CandidateFilterService:
    """Service for filtering and sorting TMDB candidates.

    This service encapsulates:
    1. Year-based filtering (with configurable tolerance)
    2. Genre-based filtering (anime/animation genres)
    3. Immutable list operations (input not modified)

    Attributes:
        statistics: Statistics collector for performance tracking

    Example:
        >>> from anivault.shared.models.tmdb_models import ScoredSearchResult
        >>> from anivault.core.matching.models import NormalizedQuery
        >>>
        >>> stats = StatisticsCollector()
        >>> service = CandidateFilterService(stats)
        >>>
        >>> query = NormalizedQuery(title="attack on titan", year=2013)
        >>> candidates = [ScoredSearchResult(...), ...]
        >>> filtered = service.filter_by_year(candidates, query.year)
    """

    def __init__(self, statistics: StatisticsCollector) -> None:
        """Initialize filter service.

        Args:
            statistics: Statistics collector for performance tracking
        """
        self.statistics = statistics

    def filter_by_year(
        self,
        candidates: list[ScoredSearchResult],
        year_hint: int | None,
    ) -> list[ScoredSearchResult]:
        """Filter candidates by year proximity.

        Candidates are filtered based on year tolerance (±10 years default).
        If no year hint provided, all candidates are returned.

        Args:
            candidates: List of scored candidates to filter
            year_hint: Year hint from normalized query (optional)

        Returns:
            Filtered list of candidates (input not modified)
            Empty list if no candidates match year criteria

        Example:
            >>> filtered = service.filter_by_year(candidates, 2013)
            >>> # Only candidates with year 2003-2023 remain
        """
        if not year_hint or not candidates:
            return candidates

        # Convert to TMDBSearchResult for filter function
        # (filter function expects TMDBSearchResult, not ScoredSearchResult)
        tmdb_results = [self._to_tmdb_result(c) for c in candidates]

        # Create temp query for filter function
        temp_query = NormalizedQuery(title="temp_query_for_filter", year=year_hint)

        # Apply year filter
        filtered_tmdb = filter_and_sort_by_year(tmdb_results, temp_query)

        # Convert back to ScoredSearchResult (preserve confidence scores)
        filtered_scored = [self._find_scored_by_id(c.id, candidates) for c in filtered_tmdb]

        # Remove None values (should not happen but be safe)
        result = [c for c in filtered_scored if c is not None]

        logger.debug(
            "Filtered %d → %d candidates by year (hint: %d)",
            len(candidates),
            len(result),
            year_hint,
        )

        return result

    def filter_by_genre(
        self,
        candidates: list[TMDBSearchResult],
        genre_ids: list[int] | None = None,
    ) -> list[TMDBSearchResult]:
        """Filter candidates by genre (anime/animation).

        Args:
            candidates: List of TMDB search results
            genre_ids: List of anime genre IDs (default: from GenreConfig)

        Returns:
            Filtered list containing only anime/animation candidates

        Example:
            >>> filtered = service.filter_by_genre(candidates)
            >>> # Only candidates with anime genres remain
        """
        if not candidates:
            return candidates

        # Delegate to existing pure function
        filtered = apply_genre_filter(candidates, genre_ids)

        logger.debug(
            "Filtered %d → %d candidates by genre",
            len(candidates),
            len(filtered),
        )

        return filtered

    def _to_tmdb_result(self, scored: ScoredSearchResult) -> TMDBSearchResult:
        """Convert ScoredSearchResult to TMDBSearchResult.

        Args:
            scored: Scored search result with confidence

        Returns:
            TMDBSearchResult (without confidence_score field)
        """
        # Use asdict to get dict, then exclude confidence_score and create TMDBSearchResult
        data = asdict(scored)
        data.pop("confidence_score", None)
        return TMDBSearchResult(**data)

    def _find_scored_by_id(
        self,
        tmdb_id: int,
        scored_list: list[ScoredSearchResult],
    ) -> ScoredSearchResult | None:
        """Find scored result by TMDB ID.

        Args:
            tmdb_id: TMDB media ID
            scored_list: List of scored results to search

        Returns:
            Matching scored result, or None if not found
        """
        for scored in scored_list:
            if scored.id == tmdb_id:
                return scored
        return None
