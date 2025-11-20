"""Media type matching scorer for metadata enrichment.

This module implements the MediaTypeScorer strategy for calculating
match scores based on media type (TV show vs movie) compatibility.
"""

from __future__ import annotations

from typing import Any

from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher.models import ScoreResult
from anivault.shared.constants.system import MediaType
from anivault.shared.errors import DomainError, ErrorCode, ErrorContext


class MediaTypeScorer:
    """Scorer for media type matching.

    This scorer implements the BaseScorer protocol and determines
    if the parsed file's expected media type (TV show vs movie)
    matches the TMDB candidate's media type.

    Attributes:
        weight: Weight applied to this score (default: 0.1)

    Example:
        >>> scorer = MediaTypeScorer(weight=0.1)
        >>> result = scorer.score(
        ...     file_info=ParsingResult(title="Attack on Titan", episode=1),
        ...     tmdb_candidate={"media_type": "tv", "id": 1429}
        ... )
        >>> print(result.score)  # 1.0 (match)
    """

    def __init__(self, weight: float = 0.1) -> None:
        """Initialize MediaTypeScorer with specified weight.

        Args:
            weight: Weight for this scorer (0.0-1.0), default 0.1

        Raises:
            ValueError: If weight is not in valid range
        """
        if not 0.0 <= weight <= 1.0:
            msg = f"weight must be between 0.0 and 1.0, got {weight}"
            raise ValueError(msg)

        self.weight = weight

    def score(
        self,
        file_info: ParsingResult,
        tmdb_candidate: dict[str, Any],
    ) -> ScoreResult:
        """Calculate media type match score.

        This method determines the expected media type from file info
        (TV if has episode/season, else Movie) and compares with TMDB.

        Logic:
        - Match → 1.0
        - Mismatch → 0.0
        - Media type unavailable → 0.0

        Args:
            file_info: Parsed file information
            tmdb_candidate: TMDB search result with media_type field

        Returns:
            ScoreResult with normalized score, weight, and reasoning

        Raises:
            DomainError: If validation fails

        Example:
            >>> scorer = MediaTypeScorer()
            >>> result = scorer.score(
            ...     ParsingResult(title="Movie Title"),
            ...     {"media_type": "movie"}
            ... )
            >>> print(result.score)  # 1.0
        """
        # Determine expected media type from file info
        expected_type = self._determine_expected_type(file_info)

        # Extract actual media type from TMDB candidate
        actual_type = self._extract_tmdb_media_type(tmdb_candidate)

        # Calculate score based on match
        if actual_type is None:
            return ScoreResult(
                score=0.0,
                weight=self.weight,
                reason="Media type unavailable in TMDB data",
                component="media_type_match",
            )

        if actual_type == expected_type:
            return ScoreResult(
                score=1.0,
                weight=self.weight,
                reason=f"Media type match: {expected_type}",
                component="media_type_match",
            )

        return ScoreResult(
            score=0.0,
            weight=self.weight,
            reason=f"Media type mismatch: expected {expected_type}, got {actual_type}",
            component="media_type_match",
        )

    def _determine_expected_type(self, file_info: ParsingResult) -> str:
        """Determine expected media type from file info.

        Rules:
        - Has episode or season info → TV
        - Otherwise → MOVIE

        Args:
            file_info: Parsed file information

        Returns:
            Expected media type string (MediaType.TV or MediaType.MOVIE)

        Raises:
            DomainError: If file_info is invalid type
        """
        if not isinstance(file_info, ParsingResult):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="file_info must be ParsingResult instance",
                context=ErrorContext(
                    operation="determine_expected_type",
                    additional_data={
                        "file_info_type": type(file_info).__name__,
                    },
                ),
            )

        # TV if has episode or season info
        if file_info.has_episode_info() or file_info.has_season_info():
            return MediaType.TV

        return MediaType.MOVIE

    def _extract_tmdb_media_type(self, tmdb_candidate: dict[str, Any]) -> str | None:
        """Extract and validate media type from TMDB candidate.

        Args:
            tmdb_candidate: TMDB search result dict

        Returns:
            Media type string (MediaType.TV or MediaType.MOVIE), or None if not available

        Raises:
            DomainError: If tmdb_candidate is invalid type
        """
        if not isinstance(tmdb_candidate, dict):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="tmdb_candidate must be a dict",
                context=ErrorContext(
                    operation="extract_tmdb_media_type",
                    additional_data={
                        "candidate_type": type(tmdb_candidate).__name__,
                    },
                ),
            )

        # Extract media_type field
        media_type_str = tmdb_candidate.get("media_type")

        if not media_type_str or not isinstance(media_type_str, str):
            return None

        # Normalize and match against MediaType constants
        media_type_lower = media_type_str.lower()

        # MediaType.TV = "tv", MediaType.MOVIE = "movie"
        if media_type_lower == MediaType.TV:
            return MediaType.TV
        if media_type_lower == MediaType.MOVIE:
            return MediaType.MOVIE

        # Unknown media type
        return None


__all__ = ["MediaTypeScorer"]
