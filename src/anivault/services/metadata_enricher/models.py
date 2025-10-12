"""Scoring and matching models for metadata enrichment.

This module defines data models for scoring and match evidence tracking,
providing transparency into the matching algorithm's decision-making process.
"""

from __future__ import annotations

from dataclasses import dataclass as std_dataclass
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic.dataclasses import dataclass

from anivault.core.parser.models import ParsingResult
from anivault.services.tmdb_models import TMDBMediaDetails
from anivault.shared.constants.api_fields import APIFields
from anivault.shared.metadata_models import FileMetadata


@dataclass
class ScoreResult:
    """Result of a single scoring component.

    This dataclass represents the output of a single scorer (e.g., TitleScorer),
    including the score, weight, and human-readable reason for transparency.

    Attributes:
        score: Normalized score value (0.0 to 1.0)
        weight: Weight applied to this score in final calculation
        reason: Human-readable explanation for this score
        component: Name of the scoring component (e.g., "title_similarity")

    Example:
        >>> score = ScoreResult(
        ...     score=0.85,
        ...     weight=0.6,
        ...     reason="Title similarity: 'Attack on Titan' vs 'Shingeki no Kyojin'",
        ...     component="title_scorer"
        ... )
    """

    score: float = Field(ge=0.0, le=1.0, description="Normalized score (0.0-1.0)")
    weight: float = Field(ge=0.0, le=1.0, description="Weight for this component")
    reason: str = Field(min_length=1, description="Human-readable score explanation")
    component: str = Field(min_length=1, description="Scorer component name")

    @field_validator("score", "weight")
    @classmethod
    def validate_range(cls, v: float, info: Any) -> float:
        """Validate score/weight is in valid range."""
        if not 0.0 <= v <= 1.0:
            field_name = info.field_name
            msg = f"{field_name} must be between 0.0 and 1.0, got {v}"
            raise ValueError(msg)
        return v


@dataclass
class MatchEvidence:
    """Complete evidence for a metadata match decision.

    This dataclass aggregates all scoring components' results and provides
    full transparency into why a particular match was selected.

    Attributes:
        total_score: Final weighted score (0.0 to 1.0)
        component_scores: Individual ScoreResult objects from each scorer
        file_title: Original filename title
        matched_title: TMDB matched title
        tmdb_id: TMDB unique identifier
        media_type: Type of media ("tv" or "movie")

    Example:
        >>> evidence = MatchEvidence(
        ...     total_score=0.87,
        ...     component_scores=[
        ...         ScoreResult(0.85, 0.6, "High title similarity", "title"),
        ...         ScoreResult(0.20, 0.2, "Episode info present", "episode"),
        ...     ],
        ...     file_title="Attack on Titan S01E01",
        ...     matched_title="Shingeki no Kyojin",
        ...     tmdb_id=1429,
        ...     media_type="tv"
        ... )
    """

    total_score: float = Field(ge=0.0, le=1.0, description="Final weighted score")
    component_scores: list[ScoreResult] = Field(
        min_length=1, description="Individual scorer results"
    )
    file_title: str = Field(min_length=1, description="Original filename title")
    matched_title: str = Field(min_length=1, description="TMDB matched title")
    tmdb_id: int = Field(gt=0, description="TMDB unique identifier")
    media_type: str = Field(
        pattern=r"^(tv|movie)$", description="Media type (tv or movie)"
    )

    @field_validator("total_score")
    @classmethod
    def validate_total_score(cls, v: float) -> float:
        """Validate total score is in valid range."""
        if not 0.0 <= v <= 1.0:
            msg = f"total_score must be between 0.0 and 1.0, got {v}"
            raise ValueError(msg)
        return v

    @field_validator("component_scores")
    @classmethod
    def validate_component_scores(cls, v: list[ScoreResult]) -> list[ScoreResult]:
        """Validate component scores list is not empty."""
        if not v:
            msg = "component_scores cannot be empty"
            raise ValueError(msg)
        return v

    def get_summary(self) -> str:
        """Get human-readable summary of match evidence.

        Returns:
            Multi-line string summarizing all scoring components

        Example:
            >>> print(evidence.get_summary())
            Match Score: 0.87 (87%)
            - Title similarity: 0.85 (weight: 60%)
            - Episode match: 0.20 (weight: 20%)
        """
        lines = [f"Match Score: {self.total_score:.2f} ({self.total_score * 100:.0f}%)"]
        for comp in self.component_scores:
            weighted = comp.score * comp.weight
            lines.append(
                f"  - {comp.component}: {comp.score:.2f} "
                f"(weight: {comp.weight * 100:.0f}%, "
                f"contribution: {weighted:.2f})"
            )
        return "\n".join(lines)


@std_dataclass
class EnrichedMetadata:
    """Enriched metadata combining parsed file info with TMDB data.

    This dataclass combines the original ParsingResult with additional
    metadata fetched from the TMDB API.

    Attributes:
        file_info: Original parsed file information
        tmdb_data: TMDB API response data
        match_confidence: Confidence score for the TMDB match (0.0 to 1.0)
        enrichment_status: Status of the enrichment process
    """

    file_info: ParsingResult
    tmdb_data: TMDBMediaDetails | dict[str, Any] | None = None
    match_confidence: float = 0.0
    enrichment_status: str = APIFields.ENRICHMENT_STATUS_PENDING

    def to_file_metadata(self, file_path: Path) -> FileMetadata:
        """Convert EnrichedMetadata to FileMetadata for presentation layer.

        This method delegates to MetadataTransformer to convert the internal
        metadata structure to the lightweight FileMetadata dataclass used by
        GUI and CLI layers.

        Args:
            file_path: Path to the media file

        Returns:
            FileMetadata instance for presentation layer

        Example:
            >>> enriched = EnrichedMetadata(file_info=parsing_result)
            >>> file_metadata = enriched.to_file_metadata(Path("/anime/aot.mkv"))
        """
        # Import at runtime to avoid circular dependency
        from anivault.services.metadata_enricher.transformer import MetadataTransformer

        transformer = MetadataTransformer()
        return transformer.transform(
            file_info=self.file_info,
            tmdb_data=self.tmdb_data,
            file_path=file_path,
        )


__all__ = ["EnrichedMetadata", "MatchEvidence", "ScoreResult"]
