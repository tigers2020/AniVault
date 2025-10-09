"""Candidate scoring service for matching engine.

This module provides the CandidateScoringService class that encapsulates
confidence score calculation and candidate ranking logic.
"""

from __future__ import annotations

import logging

from anivault.core.matching.models import NormalizedQuery
from anivault.core.matching.scoring import calculate_confidence_score
from anivault.core.statistics import StatisticsCollector
from anivault.services.tmdb_models import ScoredSearchResult, TMDBSearchResult

logger = logging.getLogger(__name__)


class CandidateScoringService:
    """Service for scoring and ranking TMDB candidates.

    This service encapsulates:
    1. Confidence score calculation for each candidate
    2. Exception handling with 0.0 fallback scores
    3. Ranking by confidence (with popularity tie-breaker)
    4. Optional statistics tracking

    Attributes:
        statistics: Statistics collector for performance tracking

    Example:
        >>> from anivault.services.tmdb_models import TMDBSearchResult
        >>> from anivault.core.matching.models import NormalizedQuery
        >>>
        >>> stats = StatisticsCollector()
        >>> service = CandidateScoringService(stats)
        >>>
        >>> query = NormalizedQuery(title="attack on titan", year=2013)
        >>> candidates = [TMDBSearchResult(...), ...]
        >>> scored = service.score_candidates(candidates, query)
        >>> best = scored[0]  # Highest confidence
    """

    def __init__(self, statistics: StatisticsCollector) -> None:
        """Initialize scoring service.

        Args:
            statistics: Statistics collector for performance tracking
        """
        self.statistics = statistics

    def score_candidates(
        self,
        candidates: list[TMDBSearchResult],
        normalized_query: NormalizedQuery,
    ) -> list[ScoredSearchResult]:
        """Score and rank candidates by confidence.

        Calculates confidence scores for all candidates and sorts them
        in descending order. Failed scoring attempts result in 0.0 score
        with warning logs.

        Args:
            candidates: List of TMDB search results to score
            normalized_query: Normalized query for scoring comparison

        Returns:
            List of scored candidates sorted by confidence (highest first)
            Uses popularity as tie-breaker for equal confidence scores

        Example:
            >>> scored = service.score_candidates(candidates, query)
            >>> for result in scored:
            ...     print(f"{result.title}: {result.confidence_score:.3f}")
        """
        scored_candidates: list[ScoredSearchResult] = []

        for candidate in candidates:
            try:
                # Calculate confidence score
                confidence_score = calculate_confidence_score(
                    normalized_query=normalized_query,
                    tmdb_result=candidate,
                )

                # Create scored result
                scored_result = ScoredSearchResult(
                    **candidate.model_dump(),
                    confidence_score=confidence_score,
                )

                scored_candidates.append(scored_result)

                logger.debug(
                    "Confidence score for '%s': %.3f",
                    candidate.display_title,
                    confidence_score,
                )

            except Exception:
                # Graceful degradation: assign 0.0 score on error
                logger.exception(
                    "Error calculating confidence score for candidate '%s'",
                    candidate.display_title,
                )

                scored_result = ScoredSearchResult(
                    **candidate.model_dump(),
                    confidence_score=0.0,
                )
                scored_candidates.append(scored_result)

        # Sort by confidence (desc) with popularity as tie-breaker
        scored_candidates.sort(
            key=lambda x: (x.confidence_score, x.popularity),
            reverse=True,
        )

        logger.debug(
            "Scored and ranked %d candidates",
            len(scored_candidates),
        )

        return scored_candidates

    def get_confidence_level(self, confidence_score: float) -> str:
        """Get confidence level label from score.

        Args:
            confidence_score: Numeric confidence score (0.0-1.0)

        Returns:
            Confidence level: "high", "medium", "low", or "very_low"

        Example:
            >>> service.get_confidence_level(0.95)
            'high'
            >>> service.get_confidence_level(0.65)
            'medium'
        """
        from anivault.shared.constants import ConfidenceThresholds

        if confidence_score >= ConfidenceThresholds.HIGH:
            return "high"
        if confidence_score >= ConfidenceThresholds.MEDIUM:
            return "medium"
        if confidence_score >= ConfidenceThresholds.LOW:
            return "low"
        return "very_low"
