"""Scoring module for metadata enrichment strategy pattern.

This module provides the base protocol and concrete scorer implementations
for the metadata matching algorithm.
"""

from .base_scorer import BaseScorer
from .engine import ScoringEngine
from .media_type_scorer import MediaTypeScorer
from .title_scorer import TitleScorer
from .year_scorer import YearScorer


def create_default_scoring_engine(
    title_weight: float = 0.6,
    year_weight: float = 0.2,
    media_type_weight: float = 0.2,
    normalize_weights: bool = True,
) -> ScoringEngine:
    """Create a ScoringEngine with default scorers.

    This factory function creates a ScoringEngine with the standard set of
    scorers (TitleScorer, YearScorer, MediaTypeScorer) using the provided
    weights. Weights can be overridden via keyword arguments.

    Args:
        title_weight: Weight for title similarity (default: 0.6)
        year_weight: Weight for year matching (default: 0.2)
        media_type_weight: Weight for media type matching (default: 0.2)
        normalize_weights: If True, normalizes weights to sum to 1.0 (default: True)

    Returns:
        A configured ScoringEngine instance with the standard scorers.

    Example:
        >>> engine = create_default_scoring_engine()
        >>> score, evidence = engine.calculate_score(file_info, tmdb_candidate)
    """
    scorers: list[BaseScorer] = [
        TitleScorer(weight=title_weight),
        YearScorer(weight=year_weight),
        MediaTypeScorer(weight=media_type_weight),
    ]
    return ScoringEngine(scorers=scorers, normalize_weights=normalize_weights)


__all__ = [
    "BaseScorer",
    "MediaTypeScorer",
    "ScoringEngine",
    "TitleScorer",
    "YearScorer",
    "create_default_scoring_engine",
]
