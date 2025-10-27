"""Partial match fallback strategy.

This strategy applies substring matching and confidence boost
for candidates where the query is contained within the title.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from rapidfuzz import fuzz

from anivault.core.matching.models import NormalizedQuery
from anivault.services.tmdb import ScoredSearchResult
from anivault.shared.constants import GenreConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PartialMatchStrategy:
    """Strategy to boost confidence for partial substring matches.

    Attributes:
        boost: Confidence boost amount (default: from GenreConfig)
        min_ratio: Minimum fuzzy match ratio to apply boost (default: 60)
        priority: Execution priority (20 = after genre boost)

    Example:
        >>> strategy = PartialMatchStrategy()
        >>> boosted = strategy.apply(candidates, query)
        >>> # Candidates with query substring have higher confidence
    """

    boost: float = GenreConfig.ANIMATION_BOOST  # Reuse same boost value
    min_ratio: int = 60  # Minimum partial ratio for boost
    priority: int = 20  # After genre boost

    def apply(
        self,
        candidates: list[ScoredSearchResult],
        query: NormalizedQuery,
    ) -> list[ScoredSearchResult]:
        """Apply partial substring matching boost.

        Args:
            candidates: List of scored candidates
            query: Normalized query for substring matching

        Returns:
            New list with boosted confidence for partial matches
            Non-matching candidates unchanged

        Note:
            - Uses rapidfuzz.fuzz.partial_ratio for substring matching
            - Confidence capped at 1.0 (GenreConfig.MAX_CONFIDENCE)
            - Uses Pydantic model_copy for immutability
        """
        if not candidates or not query.title:
            return candidates if candidates else []

        updated: list[ScoredSearchResult] = []
        query_title_lower = query.title.lower()

        for candidate in candidates:
            # Get candidate title
            candidate_title = (candidate.display_title or "").lower()

            if not candidate_title:
                updated.append(candidate)
                continue

            # Check for partial substring match
            partial_ratio = fuzz.partial_ratio(query_title_lower, candidate_title)

            if partial_ratio >= self.min_ratio:
                # Boost confidence (cap at 1.0)
                new_confidence = min(
                    GenreConfig.MAX_CONFIDENCE,
                    candidate.confidence_score + self.boost,
                )

                # Create updated candidate
                boosted_candidate = replace(
                    candidate,
                    confidence_score=new_confidence,
                )

                updated.append(boosted_candidate)

                logger.debug(
                    "Partial match boost applied: %s (ratio: %d, %.3f → %.3f)",
                    candidate.display_title,
                    partial_ratio,
                    candidate.confidence_score,
                    new_confidence,
                )
            else:
                # Keep non-matching candidates unchanged
                updated.append(candidate)

        logger.debug(
            "Partial match strategy applied to %d candidates",
            len(candidates),
        )

        return updated
