"""Matching Engine Domain Models.

This module defines immutable domain models for the matching engine's
internal data structures. These models use frozen dataclasses for
immutability and performance.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from anivault.shared.constants import ValidationConstants


@dataclass(frozen=True)
class NormalizedQuery:
    """Normalized search query for matching.

    Immutable domain object representing a normalized user query.
    Used internally by the matching engine for consistent comparison.

    Attributes:
        title: Normalized title string (non-empty, trimmed)
        year: Optional year hint for filtering (1900-future)

    Example:
        >>> query = NormalizedQuery(title="진격의 거인", year=2013)
        >>> query.title
        '진격의 거인'
        >>> query.year
        2013

    Raises:
        ValueError: If title is empty or year is out of valid range
    """

    title: str
    year: int | None = None

    def __post_init__(self) -> None:
        """Validate normalized query fields.

        Raises:
            ValueError: If title is empty/whitespace or year is invalid
        """
        # Validate title
        if not self.title or not self.title.strip():
            raise ValueError("Title cannot be empty or whitespace")

        # Validate year if provided
        if self.year is not None:
            current_year = datetime.now().year
            future_limit = current_year + ValidationConstants.FUTURE_YEAR_TOLERANCE

            if self.year < ValidationConstants.MIN_VALID_YEAR:
                msg = f"Year {self.year} is too old (must be >= {ValidationConstants.MIN_VALID_YEAR})"
                raise ValueError(msg)

            if self.year > future_limit:
                msg = (
                    f"Year {self.year} is too far in future (must be <= {future_limit})"
                )
                raise ValueError(
                    msg,
                )


@dataclass(frozen=True)
class MatchResult:
    """Match result with confidence score.

    Immutable domain object representing a matching result between
    a query and a TMDB media item.

    Attributes:
        tmdb_id: TMDB media ID
        title: Media title
        year: Release/first air year
        confidence_score: Match confidence (0.0-1.0)
        media_type: Type of media ("tv" or "movie")

    Example:
        >>> result = MatchResult(
        ...     tmdb_id=1429,
        ...     title="진격의 거인",
        ...     year=2013,
        ...     confidence_score=0.95,
        ...     media_type="tv"
        ... )
        >>> result.confidence_score
        0.95

    Raises:
        ValueError: If title is empty or confidence_score is out of range
    """

    tmdb_id: int
    title: str
    year: int | None
    confidence_score: float
    media_type: str

    def __post_init__(self) -> None:
        """Validate match result fields.

        Raises:
            ValueError: If title is empty or confidence_score is invalid
        """
        # Validate title
        if not self.title or not self.title.strip():
            raise ValueError("Title cannot be empty or whitespace")

        # Validate confidence_score
        if not (
            ValidationConstants.MIN_CONFIDENCE_SCORE
            <= self.confidence_score
            <= ValidationConstants.MAX_CONFIDENCE_SCORE
        ):
            msg = (
                f"Confidence score {self.confidence_score} must be between "
                f"{ValidationConstants.MIN_CONFIDENCE_SCORE} and {ValidationConstants.MAX_CONFIDENCE_SCORE}"
            )
            raise ValueError(
                msg,
            )

        # Validate media_type
        if self.media_type not in ValidationConstants.VALID_MEDIA_TYPES:
            msg = f"Media type '{self.media_type}' must be one of {ValidationConstants.VALID_MEDIA_TYPES}"
            raise ValueError(
                msg,
            )
