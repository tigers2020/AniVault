"""Matching weights configuration model.

This module defines the MatchingWeights model for managing all matching
algorithm weights and thresholds in a centralized, type-safe manner.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class MatchingWeights(BaseModel):
    """Matching algorithm weights and thresholds configuration.

    This class centralizes all matching-related weights and thresholds used
    across different matching engines (core matching, grouping, enrichment).

    Attributes:
        title_jaccard_weight: Weight for Jaccard similarity in title matching.
                            Default: 0.4
        title_levenshtein_weight: Weight for Levenshtein distance in title matching.
                                 Default: 0.4
        title_length_weight: Weight for title length similarity.
                            Default: 0.2
        title_similarity_threshold: Minimum similarity score for title matching.
                                   Default: 0.6
        scoring_title_match: Weight for title match in confidence scoring.
                            Default: 0.5
        scoring_year_match: Weight for year match in confidence scoring.
                           Default: 0.25
        scoring_media_type_match: Weight for media type match in confidence scoring.
                                 Default: 0.15
        scoring_popularity_match: Weight for popularity bonus in confidence scoring.
                                 Default: 0.1
        grouping_title_weight: Weight for title matcher in grouping engine.
                              Default: 0.6
        grouping_hash_weight: Weight for hash matcher in grouping engine.
                             Default: 0.3
        grouping_season_weight: Weight for season matcher in grouping engine.
                               Default: 0.1
        enricher_title_weight: Weight for title scorer in metadata enricher.
                              Default: 0.6
        enricher_year_weight: Weight for year scorer in metadata enricher.
                             Default: 0.2
        enricher_media_type_weight: Weight for media type scorer in metadata enricher.
                                   Default: 0.2

    Example:
        >>> weights = MatchingWeights()
        >>> weights.scoring_title_match
        0.5
        >>> weights.grouping_title_weight
        0.6
    """

    # Title matching weights (for title similarity calculation)
    title_jaccard_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for Jaccard similarity in title matching",
    )
    title_levenshtein_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for Levenshtein distance in title matching",
    )
    title_length_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Weight for title length similarity",
    )
    title_similarity_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for title matching",
    )

    # Confidence scoring weights (for core matching engine)
    scoring_title_match: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for title match in confidence scoring",
    )
    scoring_year_match: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Weight for year match in confidence scoring",
    )
    scoring_media_type_match: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight for media type match in confidence scoring",
    )
    scoring_popularity_match: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Weight for popularity bonus in confidence scoring",
    )

    # Grouping engine weights
    grouping_title_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for title matcher in grouping engine",
    )
    grouping_hash_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for hash matcher in grouping engine",
    )
    grouping_season_weight: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Weight for season matcher in grouping engine",
    )

    # Metadata enricher weights
    enricher_title_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for title scorer in metadata enricher",
    )
    enricher_year_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Weight for year scorer in metadata enricher",
    )
    enricher_media_type_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Weight for media type scorer in metadata enricher",
    )

    @model_validator(mode="after")
    def validate_title_weights_sum(self) -> "MatchingWeights":
        """Validate that title matching weights sum to approximately 1.0."""
        title_sum = (
            self.title_jaccard_weight
            + self.title_levenshtein_weight
            + self.title_length_weight
        )
        if not (0.99 <= title_sum <= 1.01):  # Allow small floating point errors
            msg = (
                f"Title matching weights must sum to 1.0, got {title_sum:.3f}. "
                f"jaccard={self.title_jaccard_weight:.3f}, "
                f"levenshtein={self.title_levenshtein_weight:.3f}, "
                f"length={self.title_length_weight:.3f}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_scoring_weights_sum(self) -> "MatchingWeights":
        """Validate that confidence scoring weights sum to approximately 1.0."""
        scoring_sum = (
            self.scoring_title_match
            + self.scoring_year_match
            + self.scoring_media_type_match
            + self.scoring_popularity_match
        )
        if not (0.99 <= scoring_sum <= 1.01):  # Allow small floating point errors
            msg = (
                f"Confidence scoring weights must sum to 1.0, got {scoring_sum:.3f}. "
                f"title={self.scoring_title_match:.3f}, "
                f"year={self.scoring_year_match:.3f}, "
                f"media_type={self.scoring_media_type_match:.3f}, "
                f"popularity={self.scoring_popularity_match:.3f}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_grouping_weights_sum(self) -> "MatchingWeights":
        """Validate that grouping engine weights sum to approximately 1.0."""
        grouping_sum = (
            self.grouping_title_weight
            + self.grouping_hash_weight
            + self.grouping_season_weight
        )
        if not (0.99 <= grouping_sum <= 1.01):  # Allow small floating point errors
            msg = (
                f"Grouping engine weights must sum to 1.0, got {grouping_sum:.3f}. "
                f"title={self.grouping_title_weight:.3f}, "
                f"hash={self.grouping_hash_weight:.3f}, "
                f"season={self.grouping_season_weight:.3f}"
            )
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_enricher_weights_sum(self) -> "MatchingWeights":
        """Validate that enricher weights sum to approximately 1.0."""
        enricher_sum = (
            self.enricher_title_weight
            + self.enricher_year_weight
            + self.enricher_media_type_weight
        )
        if not (0.99 <= enricher_sum <= 1.01):  # Allow small floating point errors
            msg = (
                f"Enricher weights must sum to 1.0, got {enricher_sum:.3f}. "
                f"title={self.enricher_title_weight:.3f}, "
                f"year={self.enricher_year_weight:.3f}, "
                f"media_type={self.enricher_media_type_weight:.3f}"
            )
            raise ValueError(msg)
        return self


__all__ = ["MatchingWeights"]

