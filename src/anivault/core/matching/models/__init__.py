"""Domain models for the matching engine.

This module defines frozen dataclasses that represent the domain concepts
in the anime matching system, ensuring immutability and type safety.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from anivault.shared.constants.matching import ValidationConstants


@dataclass(frozen=True)
class NormalizedQuery:
    """Normalized query for TMDB matching.

    This frozen dataclass represents a normalized user query, ensuring immutability
    and type safety for the matching process.

    Attributes:
        title: Clean title for comparison (required, non-empty)
        year: Year hint if available (must be between 1900 and 5 years in the future)
    """

    title: str
    year: int | None

    def __post_init__(self) -> None:
        """Validate normalized query invariants.

        Raises:
            ValueError: If title is empty/whitespace or year is out of valid range
        """
        # Validate title
        if not self.title or not self.title.strip():
            error_message = "title cannot be empty or whitespace"
            raise ValueError(error_message)

        # Validate year (if provided)
        if self.year is not None:
            current_year = datetime.now().year
            max_year = current_year + ValidationConstants.FUTURE_YEAR_TOLERANCE

            if self.year < ValidationConstants.MIN_VALID_YEAR or self.year > max_year:
                error_message = f"year must be between {ValidationConstants.MIN_VALID_YEAR} " f"and {max_year}, got {self.year}"
                raise ValueError(error_message)


@dataclass(frozen=True)
class MatchResult:
    """Result of a TMDB match operation.

    This frozen dataclass represents the result of matching a user query
    against TMDB data, ensuring immutability and type safety.

    Attributes:
        tmdb_id: TMDB identifier (required, positive integer)
        title: TMDB title (required, non-empty)
        year: Release/first air year (if available)
        confidence_score: Match confidence (0.0 to 1.0)
        media_type: Type of media ('tv' or 'movie')
        poster_path: Relative path to poster image (e.g., "/abc123.jpg")
        backdrop_path: Relative path to backdrop image (if available)
        overview: Plot synopsis/description (if available)
        popularity: TMDB popularity score (if available)
        vote_average: Average user rating (if available)
        original_language: Original language code (if available)
    """

    tmdb_id: int
    title: str
    year: int | None
    confidence_score: float
    media_type: str
    poster_path: str | None = None
    backdrop_path: str | None = None
    overview: str | None = None
    popularity: float | None = None
    vote_average: float | None = None
    original_language: str | None = None

    def __post_init__(self) -> None:
        """Validate match result invariants.

        Raises:
            ValueError: If any field is invalid
        """
        # Validate title
        if not self.title or not self.title.strip():
            error_message = "title cannot be empty or whitespace"
            raise ValueError(error_message)

        # Validate confidence_score
        if not (ValidationConstants.MIN_CONFIDENCE_SCORE <= self.confidence_score <= ValidationConstants.MAX_CONFIDENCE_SCORE):
            error_message = (
                "Confidence score must be between "
                f"{ValidationConstants.MIN_CONFIDENCE_SCORE} and "
                f"{ValidationConstants.MAX_CONFIDENCE_SCORE}, "
                f"got {self.confidence_score}"
            )
            raise ValueError(error_message)

        # Validate media_type
        if self.media_type not in ValidationConstants.VALID_MEDIA_TYPES:
            error_message = f"media_type must be one of {ValidationConstants.VALID_MEDIA_TYPES}, " f"got {self.media_type}"
            raise ValueError(error_message)

    def to_dict(self) -> dict[str, Any]:
        """Convert MatchResult to dict for backward compatibility.

        Returns:
            Dictionary representation of the match result
        """
        return {
            "id": self.tmdb_id,
            "title": self.title,
            "year": self.year,
            "confidence_score": self.confidence_score,
            "media_type": self.media_type,
            "poster_path": self.poster_path,
            "backdrop_path": self.backdrop_path,
            "overview": self.overview,
            "popularity": self.popularity,
            "vote_average": self.vote_average,
            "original_language": self.original_language,
        }


from .query_models import MatchQuery  # noqa: E402
from .stats_models import CacheStats  # noqa: E402

__all__ = [
    "CacheStats",
    "MatchQuery",
    "MatchResult",
    "NormalizedQuery",
]
