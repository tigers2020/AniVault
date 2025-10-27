"""Title similarity scorer using fuzzy matching algorithms.

This module implements the TitleScorer strategy for calculating similarity
between anime titles, using rapidfuzz for robust fuzzy string matching.
"""

from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz

from anivault.core.parser.models import ParsingResult
from anivault.services.enricher.metadata_enricher.models import ScoreResult
from anivault.shared.errors import DomainError, ErrorCode, ErrorContext


class TitleScorer:
    """Scorer for title similarity using fuzzy matching.

    This scorer implements the BaseScorer protocol and uses rapidfuzz
    for calculating title similarity with tolerance for typos and variations.

    Attributes:
        weight: Weight applied to this score (default: 0.6)

    Example:
        >>> scorer = TitleScorer(weight=0.6)
        >>> result = scorer.score(
        ...     file_info=ParsingResult(title="Attack on Titan", ...),
        ...     tmdb_candidate={"title": "Attack on Titan", "id": 1429}
        ... )
        >>> print(result.score)  # 1.0 (exact match)
    """

    def __init__(self, weight: float = 0.6) -> None:
        """Initialize TitleScorer with specified weight.

        Args:
            weight: Weight for this scorer (0.0-1.0), default 0.6

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
        """Calculate title similarity score.

        This method implements a multi-level matching strategy:
        1. Exact match → 1.0
        2. Case-insensitive exact → 0.95
        3. Contains substring → 0.8
        4. Fuzzy ratio (rapidfuzz) → 0.0-1.0

        Args:
            file_info: Parsed file information containing title
            tmdb_candidate: TMDB search result with title/name

        Returns:
            ScoreResult with normalized score, weight, and reasoning

        Raises:
            DomainError: If validation fails or title extraction fails

        Example:
            >>> scorer = TitleScorer()
            >>> result = scorer.score(
            ...     ParsingResult(title="Attack on Titan"),
            ...     {"title": "Shingeki no Kyojin"}
            ... )
            >>> print(result.score)  # ~0.65 (fuzzy match)
        """
        # Extract titles
        file_title = self._extract_file_title(file_info)
        tmdb_title = self._extract_tmdb_title(tmdb_candidate)

        # Calculate similarity
        similarity = self._calculate_similarity(file_title, tmdb_title)

        # Generate reason
        reason = self._generate_reason(file_title, tmdb_title, similarity)

        return ScoreResult(
            score=similarity,
            weight=self.weight,
            reason=reason,
            component="title_similarity",
        )

    def _extract_file_title(self, file_info: ParsingResult) -> str:
        """Extract and validate title from file info.

        Args:
            file_info: Parsed file information

        Returns:
            Validated title string

        Raises:
            DomainError: If title is invalid
        """
        if not isinstance(file_info, ParsingResult):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="file_info must be ParsingResult instance",
                context=ErrorContext(
                    operation="extract_file_title",
                    additional_data={
                        "file_info_type": type(file_info).__name__,
                    },
                ),
            )

        title = file_info.title
        if not title or not isinstance(title, str):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="File title cannot be empty",
                context=ErrorContext(
                    operation="extract_file_title",
                    additional_data={
                        "title_empty": not title,
                        "title_type": type(title).__name__ if title else "None",
                    },
                ),
            )

        return title

    def _extract_tmdb_title(self, tmdb_candidate: dict[str, Any]) -> str:
        """Extract and validate title from TMDB candidate.

        Args:
            tmdb_candidate: TMDB search result dict

        Returns:
            Validated title string

        Raises:
            DomainError: If title extraction fails
        """
        if not isinstance(tmdb_candidate, dict):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="tmdb_candidate must be a dict",
                context=ErrorContext(
                    operation="extract_tmdb_title",
                    additional_data={
                        "candidate_type": type(tmdb_candidate).__name__,
                    },
                ),
            )

        # Try both 'title' (movies) and 'name' (TV shows)
        title = tmdb_candidate.get("title") or tmdb_candidate.get("name")

        if not title or not isinstance(title, str):
            raise DomainError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message="TMDB result missing title/name field",
                context=ErrorContext(
                    operation="extract_tmdb_title",
                    additional_data={
                        "has_title": "title" in tmdb_candidate,
                        "has_name": "name" in tmdb_candidate,
                        "tmdb_keys_count": len(tmdb_candidate.keys()),
                    },
                ),
            )

        return title

    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity score between two titles.

        Uses a multi-level matching strategy for best accuracy:
        1. Exact match (case-sensitive) → 1.0
        2. Exact match (case-insensitive) → 0.95
        3. Contains substring → 0.8
        4. Fuzzy ratio (rapidfuzz) → scaled 0.0-1.0

        Args:
            title1: First title (from file)
            title2: Second title (from TMDB)

        Returns:
            Similarity score (0.0 to 1.0)

        Raises:
            DomainError: If calculation fails
        """
        try:
            # Normalize for comparison
            t1 = title1.strip()
            t2 = title2.strip()

            # Level 1: Exact match
            if t1 == t2:
                return 1.0

            # Normalize case
            t1_lower = t1.lower()
            t2_lower = t2.lower()

            # Level 2: Case-insensitive exact
            if t1_lower == t2_lower:
                return 0.95

            # Level 3: Contains substring
            if t1_lower in t2_lower or t2_lower in t1_lower:
                return 0.8

            # Level 4: Fuzzy matching (rapidfuzz)
            # Use token_sort_ratio for word-order independence
            fuzzy_score = fuzz.token_sort_ratio(t1_lower, t2_lower)

            # Scale from 0-100 to 0.0-1.0
            return min(fuzzy_score / 100.0, 1.0)

        except (ValueError, TypeError, AttributeError) as e:
            raise DomainError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Failed to calculate title similarity: {e}",
                context=ErrorContext(
                    operation="calculate_similarity",
                    additional_data={
                        "title1": title1[:50],  # Truncate for logging
                        "title2": title2[:50],
                        "error_type": type(e).__name__,
                    },
                ),
                original_error=e,
            ) from e
        except Exception as e:
            raise DomainError(
                code=ErrorCode.DATA_PROCESSING_ERROR,
                message=f"Unexpected error calculating title similarity: {e}",
                context=ErrorContext(
                    operation="calculate_similarity",
                    additional_data={
                        "title1": title1[:50],
                        "title2": title2[:50],
                        "error_type": type(e).__name__,
                    },
                ),
                original_error=e,
            ) from e

    def _generate_reason(
        self, file_title: str, tmdb_title: str, similarity: float
    ) -> str:
        """Generate human-readable reason for the score.

        Args:
            file_title: Original file title
            tmdb_title: TMDB matched title
            similarity: Calculated similarity score

        Returns:
            Human-readable explanation string
        """
        if similarity >= 0.9:
            category = "Excellent match"
        elif similarity >= 0.75:
            category = "High similarity"
        elif similarity >= 0.5:
            category = "Moderate similarity"
        else:
            category = "Low similarity"

        return f"{category}: '{file_title}' vs '{tmdb_title}' (score: {similarity:.2f})"


__all__ = ["TitleScorer"]
