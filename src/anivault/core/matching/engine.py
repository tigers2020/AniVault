"""Multi-stage matching engine for finding anime titles in TMDB.

This module provides the core matching functionality that uses normalized queries
to search TMDB and find potential matches using various strategies including
fuzzy matching, year-based filtering, and confidence scoring.
"""

from __future__ import annotations

import logging
from typing import Any

from anivault.core.matching.models import MatchResult, NormalizedQuery
from anivault.core.matching.services import SQLiteCacheAdapter
from anivault.core.normalization import normalize_query_from_anitopy
from anivault.core.statistics import StatisticsCollector
from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.services.tmdb_client import TMDBClient
from anivault.services.tmdb_models import ScoredSearchResult, TMDBSearchResult
from anivault.shared.constants import (
    ConfidenceThresholds,
    DefaultLanguage,
    TMDBSearchKeys,
)

logger = logging.getLogger(__name__)


class MatchingEngine:
    """Multi-stage matching engine for finding anime titles in TMDB.

    This engine orchestrates the entire matching process by:
    1. Normalizing the input query
    2. Searching TMDB with caching
    3. Scoring candidates using fuzzy matching
    4. Filtering and sorting by year
    5. Returning the best match

    Args:
        cache: Cache v2 instance for storing TMDB search results
        tmdb_client: TMDB client for API calls
    """

    def __init__(
        self,
        cache: SQLiteCacheDB,
        tmdb_client: TMDBClient,
        statistics: StatisticsCollector | None = None,
    ):
        """Initialize the matching engine.

        Args:
            cache: SQLite cache database for storing TMDB search results
            tmdb_client: TMDB client for API calls
            statistics: Optional statistics collector for performance tracking
        """
        self.statistics = statistics or StatisticsCollector()

        # Create cache adapter with language from TMDB client
        language = getattr(tmdb_client, TMDBSearchKeys.LANGUAGE, DefaultLanguage.KOREAN)
        self.cache = SQLiteCacheAdapter(backend=cache, language=language)

        self.tmdb_client = tmdb_client

        # Initialize services
        from anivault.core.matching.services import (
            CandidateFilterService,
            CandidateScoringService,
            FallbackStrategyService,
            TMDBSearchService,
        )
        from anivault.core.matching.strategies import (
            GenreBoostStrategy,
            PartialMatchStrategy,
        )

        self._search_service = TMDBSearchService(
            cache=self.cache,
            tmdb_client=tmdb_client,
            statistics=self.statistics,
        )
        self._scoring_service = CandidateScoringService(statistics=self.statistics)
        self._filter_service = CandidateFilterService(statistics=self.statistics)

        # Initialize fallback strategies
        from typing import cast

        from anivault.core.matching.strategies import FallbackStrategy

        fallback_strategies: list[FallbackStrategy] = cast(
            list[FallbackStrategy],
            [
                GenreBoostStrategy(),
                PartialMatchStrategy(),
            ],
        )
        self._fallback_service = FallbackStrategyService(
            statistics=self.statistics,
            strategies=fallback_strategies,
        )


    async def find_match(self, anitopy_result: dict[str, Any]) -> MatchResult | None:
        """Find the best match for an anime title using multi-stage matching with fallback strategies.

        This method orchestrates the entire matching process by delegating to service layer.

        Args:
            anitopy_result: Result from anitopy.parse() containing anime metadata

        Returns:
            MatchResult domain object with confidence metadata or None if no good match found
        """
        self.statistics.start_timing("matching_operation")

        try:
            # Step 1: Validate and normalize input
            normalized_query = self._validate_and_normalize_input(anitopy_result)
            if not normalized_query:
                return None

            # Step 2: Search for candidates (delegate to SearchService)
            candidates = await self._search_service.search(normalized_query)
            if not candidates:
                logger.info("No candidates found for query: %s", normalized_query.title)
                return None

            # Step 3: Score and rank candidates (delegate to ScoringService)
            scored_candidates = self._scoring_service.score_candidates(
                candidates,
                normalized_query,
            )
            if not scored_candidates:
                return None

            # Step 4: Apply filters (delegate to FilterService)
            filtered_candidates = self._filter_service.filter_by_year(
                scored_candidates,
                normalized_query.year,
            )
            if not filtered_candidates:
                logger.debug("All candidates filtered out")
                return None

            # Step 5: Get initial best candidate
            best_candidate = filtered_candidates[0]
            best_confidence = best_candidate.confidence_score

            logger.info(
                "Best candidate for '%s': '%s' (confidence: %.3f)",
                normalized_query.title,
                best_candidate.display_title,
                best_confidence,
            )

            # Step 6: Apply fallback strategies if confidence < HIGH
            if best_confidence < ConfidenceThresholds.HIGH:
                logger.info(
                    "Confidence below HIGH threshold (%.3f < %.3f), applying fallback",
                    best_confidence,
                    ConfidenceThresholds.HIGH,
                )

                enhanced_candidates = self._fallback_service.apply_strategies(
                    filtered_candidates,
                    normalized_query,
                )

                if enhanced_candidates:
                    best_candidate = enhanced_candidates[0]
                    logger.info(
                        "Fallback improved confidence: %.3f → %.3f",
                        best_confidence,
                        best_candidate.confidence_score,
                    )

            # Step 7: Validate final confidence
            if not self._validate_final_confidence(best_candidate):
                return None

            # Step 8: Create MatchResult
            match_result = self._create_match_result(
                best_candidate,
                normalized_query,
            )

            # Record stats
            self._record_successful_match(best_candidate, normalized_query, candidates)
            self.statistics.end_timing("matching_operation")

            return match_result

        except Exception:
            logger.exception("Error in find_match")
            self.statistics.record_match_failure()
            self.statistics.end_timing("matching_operation")
            return None

    def _validate_and_normalize_input(
        self,
        anitopy_result: dict[str, Any],
    ) -> NormalizedQuery | None:
        """Validate and normalize the input query.

        Args:
            anitopy_result: Result from anitopy.parse() containing anime metadata

        Returns:
            NormalizedQuery domain object or None if validation fails
        """
        normalized_query = normalize_query_from_anitopy(anitopy_result)
        if not normalized_query:
            logger.warning("Failed to normalize query from anitopy result")
            return None

        logger.info("Searching for match: %s", normalized_query.title)
        return normalized_query


    def _validate_final_confidence(self, best_candidate: ScoredSearchResult) -> bool:
        """Validate that the final confidence meets minimum threshold.

        Args:
            best_candidate: The best candidate to validate

        Returns:
            True if confidence is acceptable, False otherwise
        """
        best_confidence = best_candidate.confidence_score

        if best_confidence < ConfidenceThresholds.LOW:
            logger.warning(
                "Very low confidence (%.3f < %.3f), returning None",
                best_confidence,
                ConfidenceThresholds.LOW,
            )
            return False

        return True

    def _create_match_result(
        self,
        best_candidate: ScoredSearchResult,
        normalized_query: NormalizedQuery,
    ) -> MatchResult:
        """Create MatchResult domain object from best candidate.

        Args:
            best_candidate: The best matching ScoredSearchResult
            normalized_query: NormalizedQuery domain object

        Returns:
            MatchResult domain object with match details
        """
        # Extract year from date fields
        year = None
        date_str = best_candidate.display_date
        if date_str:
            try:
                year = int(date_str.split("-")[0])
            except (ValueError, IndexError, AttributeError):
                pass

        match_result = MatchResult(
            tmdb_id=best_candidate.id,
            title=best_candidate.display_title,
            year=year,
            confidence_score=best_candidate.confidence_score,
            media_type=best_candidate.media_type,
            poster_path=best_candidate.poster_path,
            backdrop_path=best_candidate.backdrop_path,
            overview=best_candidate.overview,
            popularity=best_candidate.popularity,
            vote_average=best_candidate.vote_average,
            original_language=best_candidate.original_language,
        )

        logger.info(
            "Found best match for '%s': '%s' (confidence: %.3f)",
            normalized_query.title,
            match_result.title,
            match_result.confidence_score,
        )

        return match_result

    def _record_successful_match(
        self,
        result: ScoredSearchResult,
        query: NormalizedQuery,  # noqa: ARG002 - For future metadata extension
        candidates: list[TMDBSearchResult],
    ) -> None:
        """Record statistics for successful match.

        Args:
            result: The successful ScoredSearchResult
            query: The NormalizedQuery used for matching
            candidates: Original list of candidates
        """
        best_confidence = result.confidence_score
        used_fallback = best_confidence < ConfidenceThresholds.HIGH

        self.statistics.record_match_success(
            confidence=best_confidence,
            candidates_count=len(candidates),
            used_fallback=used_fallback,
        )

    def get_cache_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics for GUI display.

        Returns:
            Dictionary containing cache statistics:
            - hit_ratio: Cache hit ratio percentage (0.0-100.0)
            - total_requests: Total cache requests (hits + misses)
            - cache_items: Total items in cache
            - cache_mode: Current cache mode (hybrid/db-only/json-only)
            - cache_type: Primary cache type (SQLite/JSON/Hybrid)
        """
        # Get cache hit ratio from statistics
        hit_ratio = self.statistics.get_cache_hit_ratio()
        total_requests = (
            self.statistics.metrics.cache_hits + self.statistics.metrics.cache_misses
        )

        # Get cache item count from SQLite backend if available
        cache_items = 0
        if hasattr(self.cache, "backend"):
            try:
                cache_info = self.cache.backend.get_cache_info()
                cache_items = cache_info.get("total_files", 0)
            except OSError as e:
                logger.warning("Failed to get cache item count: %s", e)

        # Determine primary cache type for display
        cache_mode = getattr(self, "cache_mode", "json-only")
        if cache_mode == "hybrid":
            cache_type = "Hybrid"
        elif cache_mode == "db-only":
            cache_type = "SQLite"
        elif cache_mode == "json-only":
            cache_type = "JSON"
        else:
            cache_type = "Unknown"

        return {
            "hit_ratio": hit_ratio,
            "total_requests": total_requests,
            "cache_items": cache_items,
            "cache_mode": cache_mode,
            "cache_type": cache_type,
        }
