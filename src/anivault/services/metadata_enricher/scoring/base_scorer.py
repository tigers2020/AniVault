"""Base protocol for scoring strategies in metadata enrichment.

This module defines the BaseScorer protocol that all concrete scorer
implementations must follow, enabling the Strategy pattern for scoring logic.
"""

from __future__ import annotations

from typing import Any, Protocol

from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher.models import ScoreResult


class BaseScorer(Protocol):
    """Protocol for scoring strategies.

    This protocol defines the interface that all scorer implementations
    (TitleScorer, YearScorer, MediaTypeScorer) must follow.

    The score() method takes parsed file information and a TMDB candidate,
    returning a ScoreResult with normalized score, weight, and reasoning.

    Attributes:
        component_name: A unique identifier for this scorer component.
                       Used in weight overrides and evidence reporting.
        weight: The weight assigned to this scorer (0.0 to 1.0).
                Used by ScoringEngine for weighted scoring.

    Example:
        >>> class TitleScorer:
        ...     component_name = "title"
        ...     weight = 0.6
        ...     def score(
        ...         self,
        ...         file_info: ParsingResult,
        ...         tmdb_candidate: dict[str, Any]
        ...     ) -> ScoreResult:
        ...         title_sim = calculate_similarity(file_info.title, tmdb_candidate["title"])
        ...         return ScoreResult(
        ...             score=title_sim,
        ...             weight=self.weight,
        ...             reason=f"Title similarity: {title_sim:.2f}",
        ...             component="title_scorer"
        ...         )
    """

    component_name: str
    weight: float

    def score(
        self,
        file_info: ParsingResult,
        tmdb_candidate: dict[str, Any],
    ) -> ScoreResult:
        """Calculate score for a TMDB candidate match.

        Args:
            file_info: Parsed file information from filename
            tmdb_candidate: TMDB API response for a candidate match
                           (Can be raw dict or TMDBMediaDetails)

        Returns:
            ScoreResult with normalized score (0.0-1.0), weight, and reason

        Raises:
            DomainError: If scoring fails due to invalid data

        Example:
            >>> scorer = TitleScorer()
            >>> result = scorer.score(
            ...     file_info=ParsingResult(title="Attack on Titan", ...),
            ...     tmdb_candidate={"title": "Shingeki no Kyojin", "id": 1429}
            ... )
            >>> print(result.score)  # 0.85
        """
        ...


__all__ = ["BaseScorer"]
