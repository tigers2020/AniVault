"""Scoring and matching models for metadata enrichment.

This module defines data models for scoring and match evidence tracking,
providing transparency into the matching algorithm's decision-making process.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from anivault.core.parser.models import ParsingResult
from anivault.services.tmdb import TMDBMediaDetails
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

    score: float
    weight: float
    reason: str
    component: str

    def __post_init__(self) -> None:
        """Validate ScoreResult fields after initialization.

        Raises:
            ValueError: If validation fails for any field
        """
        # Validate score range
        if not 0.0 <= self.score <= 1.0:
            msg = f"score must be between 0.0 and 1.0, got {self.score}"
            raise ValueError(msg)

        # Validate weight range
        if not 0.0 <= self.weight <= 1.0:
            msg = f"weight must be between 0.0 and 1.0, got {self.weight}"
            raise ValueError(msg)

        # Validate reason is not empty
        if not self.reason or not self.reason.strip():
            msg = "reason must not be empty"
            raise ValueError(msg)

        # Validate component is not empty
        if not self.component or not self.component.strip():
            msg = "component must not be empty"
            raise ValueError(msg)


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

    total_score: float
    component_scores: list[ScoreResult]
    file_title: str
    matched_title: str
    tmdb_id: int
    media_type: str

    def __post_init__(self) -> None:
        """Validate MatchEvidence fields after initialization.

        Raises:
            ValueError: If validation fails for any field
        """
        # Validate total_score range
        if not 0.0 <= self.total_score <= 1.0:
            msg = f"total_score must be between 0.0 and 1.0, got {self.total_score}"
            raise ValueError(msg)

        # Validate component_scores is not empty
        if not self.component_scores:
            msg = "component_scores cannot be empty"
            raise ValueError(msg)

        # Validate file_title is not empty
        if not self.file_title or not self.file_title.strip():
            msg = "file_title must not be empty"
            raise ValueError(msg)

        # Validate matched_title is not empty
        if not self.matched_title or not self.matched_title.strip():
            msg = "matched_title must not be empty"
            raise ValueError(msg)

        # Validate tmdb_id is positive
        if self.tmdb_id <= 0:
            msg = f"tmdb_id must be positive, got {self.tmdb_id}"
            raise ValueError(msg)

        # Validate media_type is valid
        if self.media_type not in ("tv", "movie"):
            msg = f"media_type must be 'tv' or 'movie', got {self.media_type}"
            raise ValueError(msg)

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


@dataclass
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
        from anivault.services.enricher.metadata_enricher.transformer import (
            MetadataTransformer,
        )

        transformer = MetadataTransformer()
        return transformer.transform(
            file_info=self.file_info,
            tmdb_data=self.tmdb_data,
            file_path=file_path,
        )


__all__ = ["EnrichedMetadata", "MatchEvidence", "ScoreResult"]
