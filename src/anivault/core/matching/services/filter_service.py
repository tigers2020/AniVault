"""Candidate filtering service for matching engine.

This module provides the CandidateFilterService class that encapsulates
filtering logic based on year, genre, and other criteria.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from anivault.core.matching.filters import apply_genre_filter
from anivault.core.matching.services.sort_cache import SortCache
from anivault.core.statistics import StatisticsCollector
from anivault.shared.models.tmdb_models import ScoredSearchResult, TMDBSearchResult

logger = logging.getLogger(__name__)


class CandidateFilterService:
    """Service for filtering and sorting TMDB candidates.

    This service encapsulates:
    1. Year-based filtering (with configurable tolerance)
    2. Genre-based filtering (anime/animation genres)
    3. Immutable list operations (input not modified)
    4. Sort caching for performance optimization

    Attributes:
        statistics: Statistics collector for performance tracking
        sort_cache: Cache for sorted candidate lists

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
        self.sort_cache = SortCache()

    def filter_by_year(
        self,
        candidates: list[ScoredSearchResult],
        year_hint: int | None,
    ) -> list[ScoredSearchResult]:
        """Filter candidates by year proximity while preserving confidence order.

        Candidates are filtered based on year tolerance (±10 years default).
        After filtering, candidates are re-sorted by confidence score (descending)
        to maintain the original confidence-based ranking.

        Args:
            candidates: List of scored candidates to filter (should be pre-sorted by confidence)
            year_hint: Year hint from normalized query (optional)

        Returns:
            Filtered list of candidates sorted by confidence (descending)
            Empty list if no candidates match year criteria

        Example:
            >>> filtered = service.filter_by_year(candidates, 2013)
            >>> # Only candidates with year 2003-2023 remain, sorted by confidence
        """
        if not year_hint or not candidates:
            return candidates

        # Filter by year tolerance (±10 years)
        from anivault.core.matching.filters import YEAR_FILTER_TOLERANCE

        filtered = []
        for candidate in candidates:
            # Extract year from release_date or first_air_date
            candidate_year = self._extract_year_from_candidate(candidate)

            if not candidate_year:
                # Keep candidates without year (they go to end after sorting)
                filtered.append(candidate)
                continue

            # Check year difference
            year_diff = abs(candidate_year - year_hint)
            if year_diff <= YEAR_FILTER_TOLERANCE:
                filtered.append(candidate)
                logger.debug(
                    "Year match: query=%s, candidate=%s (diff=%s, confidence=%.3f)",
                    year_hint,
                    candidate_year,
                    year_diff,
                    candidate.confidence_score,
                )

        # CRITICAL: Re-sort by confidence to maintain original ranking
        # This ensures the highest confidence candidate is selected even after filtering
        filtered.sort(key=lambda c: c.confidence_score, reverse=True)

        logger.debug(
            "Filtered %d → %d candidates by year (hint: %d), re-sorted by confidence",
            len(candidates),
            len(filtered),
            year_hint,
        )

        return filtered

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

    def _extract_year_from_candidate(self, candidate: ScoredSearchResult) -> int | None:
        """Extract year from candidate's release date.

        Args:
            candidate: Scored search result

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
