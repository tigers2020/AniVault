"""Year matching scorer for metadata enrichment.

This module implements the YearScorer strategy for calculating similarity
based on release/air date year matching with tolerance.
"""

from __future__ import annotations

from anivault.core.parser.models import ParsingResult
from anivault.services.enricher.metadata_enricher.models import ScoreResult
from anivault.services.tmdb import TMDBSearchResult
from anivault.shared.errors import DomainError, ErrorCode, ErrorContext


class YearScorer:
    """Scorer for year matching with tolerance.

    This scorer implements the BaseScorer protocol and compares
    the parsed file year with TMDB candidate year, allowing
    a configurable tolerance for matches.

    Attributes:
        weight: Weight applied to this score (default: 0.2)
        tolerance: Year difference tolerance (default: 1)

    Example:
        >>> scorer = YearScorer(weight=0.2, tolerance=1)
        >>> result = scorer.score(
        ...     file_info=ParsingResult(title="Attack on Titan", year=2013),
        ...     tmdb_candidate=TMDBSearchResult(id=1429, media_type="tv", first_air_date="2013-04-07")
        ... )
        >>> print(result.score)  # 1.0 (exact match)
    """

    component_name: str = "year"

    def __init__(self, weight: float = 0.2, tolerance: int = 1) -> None:
        """Initialize YearScorer with specified weight and tolerance.

        Args:
            weight: Weight for this scorer (0.0-1.0), default 0.2
            tolerance: Maximum year difference for partial match, default 1

        Raises:
            ValueError: If weight is not in valid range or tolerance is negative
        """
        if not 0.0 <= weight <= 1.0:
            msg = f"weight must be between 0.0 and 1.0, got {weight}"
            raise ValueError(msg)
        if tolerance < 0:
            msg = f"tolerance must be non-negative, got {tolerance}"
            raise ValueError(msg)

        self.weight = weight
        self.tolerance = tolerance

    def score(
        self,
        file_info: ParsingResult,
        tmdb_candidate: TMDBSearchResult,
    ) -> ScoreResult:
        """Calculate year match score.

        This method compares the file year with TMDB candidate year:
        - Exact match → 1.0
        - Within tolerance → scaled 0.0-1.0
        - Beyond tolerance → 0.0
        - Year unavailable → 0.0

        Args:
            file_info: Parsed file information containing year (optional)
            tmdb_candidate: TMDB search result with date fields

        Returns:
            ScoreResult with normalized score, weight, and reasoning

        Raises:
            DomainError: If validation fails

        Example:
            >>> scorer = YearScorer()
            >>> result = scorer.score(
            ...     ParsingResult(title="Attack on Titan", year=2013),
            ...     {"first_air_date": "2013-04-07"}
            ... )
            >>> print(result.score)  # 1.0
        """
        # Extract years
        file_year = self._extract_file_year(file_info)
        tmdb_year = self._extract_tmdb_year(tmdb_candidate)

        # Handle missing years
        if file_year is None or tmdb_year is None:
            return ScoreResult(
                score=0.0,
                weight=self.weight,
                reason="Year unavailable (file or TMDB missing year)",
                component="year_match",
            )

        # Calculate year difference
        delta = abs(file_year - tmdb_year)

        # Calculate score based on delta and tolerance
        if delta == 0:
            score = 1.0
            category = "Exact year match"
        elif delta <= self.tolerance:
            # Linear decay within tolerance
            score = 1.0 - (delta / (self.tolerance + 1))
            category = "Within tolerance"
        else:
            score = 0.0
            category = "Year mismatch"

        reason = f"{category}: {file_year} vs {tmdb_year} (delta: {delta})"

        return ScoreResult(
            score=score,
            weight=self.weight,
            reason=reason,
            component="year_match",
        )

    def _extract_file_year(self, file_info: ParsingResult) -> int | None:
        """Extract and validate year from file info.

        The year is extracted from ParsingResult.year field,
        which is populated by parsers like anitopy.

        Args:
            file_info: Parsed file information

        Returns:
            Year as integer, or None if not available

        Raises:
            DomainError: If file_info is invalid type
        """
        if not isinstance(file_info, ParsingResult):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="file_info must be ParsingResult instance",
                context=ErrorContext(
                    operation="extract_file_year",
                    additional_data={
                        "file_info_type": type(file_info).__name__,
                    },
                ),
            )

        # Extract year from ParsingResult.year field
        year = file_info.year

        if year is None or not isinstance(year, int):
            return None

        # Sanity check: reasonable year range
        if not 1900 <= year <= 2100:
            return None

        return year

    def _extract_tmdb_year(self, tmdb_candidate: TMDBSearchResult) -> int | None:
        """Extract and validate year from TMDB candidate.

        This method uses display_date property which handles both
        first_air_date (TV shows) and release_date (movies).

        Args:
            tmdb_candidate: TMDB search result dataclass instance

        Returns:
            Year as integer, or None if not available/parseable

        Raises:
            DomainError: If tmdb_candidate is invalid type
        """
        if not isinstance(tmdb_candidate, TMDBSearchResult):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="tmdb_candidate must be a TMDBSearchResult instance",
                context=ErrorContext(
                    operation="extract_tmdb_year",
                    additional_data={
                        "candidate_type": type(tmdb_candidate).__name__,
                    },
                ),
            )

        # Use display_date property (handles both first_air_date and release_date)
        date_str = tmdb_candidate.display_date

        if not date_str or not isinstance(date_str, str):
            return None

        # Parse year from ISO date format (YYYY-MM-DD)
        try:
            year = int(date_str.split("-")[0])
            # Sanity check: reasonable year range
            if not 1900 <= year <= 2100:
                return None
            return year
        except (ValueError, IndexError, AttributeError):
            return None


__all__ = ["YearScorer"]
