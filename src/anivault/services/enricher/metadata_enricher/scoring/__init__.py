"""Scoring module for metadata enrichment strategy pattern.

This module provides the base protocol and concrete scorer implementations
for the metadata matching algorithm.
"""

from __future__ import annotations

from anivault.config.models.matching_weights import MatchingWeights

from .base_scorer import BaseScorer
from .engine import ScoringEngine
from .media_type_scorer import MediaTypeScorer
from .title_scorer import TitleScorer
from .year_scorer import YearScorer


def create_default_scoring_engine(
    normalize_weights: bool = True,
    weights: MatchingWeights | None = None,
) -> ScoringEngine:
    """Create a ScoringEngine with default scorers.

    This factory function creates a ScoringEngine with the standard set of
    scorers (TitleScorer, YearScorer, MediaTypeScorer) using the provided
    weights from MatchingWeights.

    Args:
        normalize_weights: If True, normalizes weights to sum to 1.0 (default: True)
        weights: MatchingWeights instance for configurable weights.
                If None, loads from config or uses defaults.

    Returns:
        A configured ScoringEngine instance with the standard scorers.

    Example:
        >>> engine = create_default_scoring_engine()
        >>> score, evidence = engine.calculate_score(file_info, tmdb_candidate)
    """
    # Load weights if not provided
    if weights is None:
        try:
            from anivault.config import load_settings

            settings = load_settings()
            weights = settings.matching_weights
        except (ImportError, AttributeError):
            weights = MatchingWeights()

    # Use weights from MatchingWeights
    title_weight = weights.enricher_title_weight
    year_weight = weights.enricher_year_weight
    media_type_weight = weights.enricher_media_type_weight

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
