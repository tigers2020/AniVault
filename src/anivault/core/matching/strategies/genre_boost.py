"""Genre boost fallback strategy.

This strategy boosts confidence scores for anime/animation candidates
to prioritize them over non-animation content.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from anivault.core.matching.models import NormalizedQuery
from anivault.services.tmdb import ScoredSearchResult
from anivault.shared.constants import GenreConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GenreBoostStrategy:
    """Strategy to boost confidence for animation genre candidates.

    Attributes:
        boost: Confidence boost amount (default: from GenreConfig)
        priority: Execution priority (10 = early, before other strategies)

    Example:
        >>> strategy = GenreBoostStrategy()
        >>> boosted = strategy.apply(candidates, query)
        >>> # Animation candidates have higher confidence
    """

    boost: float = GenreConfig.ANIMATION_BOOST
    priority: int = 10

    def apply(
        self,
        candidates: list[ScoredSearchResult],
        query: NormalizedQuery,  # noqa: ARG002
    ) -> list[ScoredSearchResult]:
        """Apply genre-based confidence boost.

        Args:
            candidates: List of scored candidates
            query: Normalized query (unused, for protocol compliance)

        Returns:
            New list with boosted confidence for animation candidates
            Non-animation candidates unchanged

        Note:
            - Confidence capped at 1.0 (GenreConfig.MAX_CONFIDENCE)
            - Uses Pydantic model_copy for immutability
        """
        if not candidates:
            return []

        updated: list[ScoredSearchResult] = []

        for candidate in candidates:
            # Check if candidate has animation genre
            candidate_genres = candidate.genre_ids or []
            is_animation = GenreConfig.ANIMATION_GENRE_ID in candidate_genres

            if is_animation:
                # Boost confidence (cap at 1.0)
                new_confidence = min(
                    GenreConfig.MAX_CONFIDENCE,
                    candidate.confidence_score + self.boost,
                )

                # Create updated candidate
                boosted_candidate = replace(candidate, confidence_score=new_confidence)

                updated.append(boosted_candidate)

                logger.debug(
                    "Genre boost applied: %s (%.3f → %.3f)",
                    candidate.display_title,
                    candidate.confidence_score,
                    new_confidence,
                )
            else:
                # Keep non-animation candidates unchanged
                updated.append(candidate)

        logger.debug(
            "Genre boost strategy applied to %d candidates",
            len(candidates),
        )

        return updated
