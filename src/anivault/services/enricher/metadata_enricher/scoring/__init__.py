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
    title_weight: float | None = None,
    year_weight: float | None = None,
    media_type_weight: float | None = None,
    normalize_weights: bool = True,
    weights: MatchingWeights | None = None,
) -> ScoringEngine:
    """Create a ScoringEngine with default scorers.

    This factory function creates a ScoringEngine with the standard set of
    scorers (TitleScorer, YearScorer, MediaTypeScorer) using the provided
    weights. Weights can be overridden via keyword arguments or MatchingWeights.

    Args:
        title_weight: Weight for title similarity (deprecated: use weights parameter).
                     If None and weights is provided, uses weights.enricher_title_weight.
                     Default: 0.6
        year_weight: Weight for year matching (deprecated: use weights parameter).
                    If None and weights is provided, uses weights.enricher_year_weight.
                    Default: 0.2
        media_type_weight: Weight for media type matching (deprecated: use weights parameter).
                          If None and weights is provided, uses weights.enricher_media_type_weight.
                          Default: 0.2
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

    # Use weights from MatchingWeights if individual weights not provided
    if title_weight is None:
        title_weight = weights.enricher_title_weight
    if year_weight is None:
        year_weight = weights.enricher_year_weight
    if media_type_weight is None:
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
