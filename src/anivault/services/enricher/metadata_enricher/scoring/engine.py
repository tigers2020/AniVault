"""Scoring engine for composing multiple scoring strategies.

This module implements the ScoringEngine that orchestrates multiple
BaseScorer implementations to calculate comprehensive match scores
with transparent evidence collection.
"""

from __future__ import annotations

import logging

from anivault.core.parser.models import ParsingResult
from anivault.services.enricher.metadata_enricher.models import (
    MatchEvidence,
    ScoreResult,
)
from anivault.services.enricher.metadata_enricher.scoring.base_scorer import BaseScorer
from anivault.services.tmdb import TMDBSearchResult
from anivault.shared.errors import DomainError, ErrorCode, ErrorContext

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Engine for composing multiple scoring strategies.

    This engine orchestrates multiple BaseScorer implementations,
    collecting their individual scores and combining them into a
    final match score with transparent evidence.

    Attributes:
        scorers: List of scorer implementations to use
        normalize_weights: Whether to normalize weights to sum to 1.0

    Example:
        >>> engine = ScoringEngine([
        ...     TitleScorer(weight=0.6),
        ...     YearScorer(weight=0.2),
        ...     MediaTypeScorer(weight=0.2)
        ... ])
        >>> score, evidence = engine.calculate_score(file_info, tmdb_candidate)
        >>> print(f"Score: {score}, Components: {len(evidence.component_scores)}")
    """

    def __init__(
        self,
        scorers: list[BaseScorer],
        normalize_weights: bool = False,
    ) -> None:
        """Initialize ScoringEngine with scorer list.

        Args:
            scorers: List of scorer implementations
            normalize_weights: If True, normalize weights to sum to 1.0

        Raises:
            ValueError: If scorers list is empty
            DomainError: If scorer validation fails
        """
        if not scorers:
            msg = "scorers list cannot be empty"
            raise ValueError(msg)

        self.scorers = scorers
        self.normalize_weights = normalize_weights

        # Validate scorers
        self._validate_scorers()

        # Normalize weights if requested
        if self.normalize_weights:
            self._normalize_weights()

    def calculate_score(
        self,
        file_info: ParsingResult,
        tmdb_candidate: TMDBSearchResult,
    ) -> tuple[float, MatchEvidence]:
        """Calculate comprehensive match score using all scorers.

        This method orchestrates all configured scorers, collects their
        individual results, and combines them into a final score with
        transparent evidence.

        Args:
            file_info: Parsed file information
            tmdb_candidate: TMDB search result dataclass instance

        Returns:
            Tuple of (final_score, match_evidence)

        Raises:
            DomainError: If input validation fails

        Example:
            >>> score, evidence = engine.calculate_score(
            ...     ParsingResult(title="Attack on Titan", year=2013),
            ...     TMDBSearchResult(id=1429, media_type="tv", name="Attack on Titan")
            ... )
            >>> print(f"Final score: {score:.2f}")
        """
        # Validate inputs
        if not isinstance(file_info, ParsingResult):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="file_info must be ParsingResult instance",
                context=ErrorContext(
                    operation="calculate_score",
                    additional_data={
                        "file_info_type": type(file_info).__name__,
                    },
                ),
            )

        if not isinstance(tmdb_candidate, TMDBSearchResult):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="tmdb_candidate must be a TMDBSearchResult instance",
                context=ErrorContext(
                    operation="calculate_score",
                    additional_data={
                        "candidate_type": type(tmdb_candidate).__name__,
                    },
                ),
            )

        # Collect scores from all scorers
        component_scores: list[ScoreResult] = []
        total_score = 0.0

        for scorer in self.scorers:
            try:
                result = scorer.score(file_info, tmdb_candidate)
                component_scores.append(result)

                # Weighted contribution
                contribution = result.score * result.weight
                total_score += contribution

                logger.debug(
                    "Scorer %s: score=%.3f, weight=%.3f, contribution=%.3f",
                    result.component,
                    result.score,
                    result.weight,
                    contribution,
                )

            except DomainError:
                # Re-raise domain errors
                raise
            except Exception as e:  # noqa: BLE001
                # Log and skip scorer on unexpected errors
                logger.warning(
                    "Scorer %s raised unexpected error: %s. Skipping.",
                    scorer.__class__.__name__,
                    str(e),
                    exc_info=True,
                )
                # Add zero score result for transparency
                component_scores.append(
                    ScoreResult(
                        score=0.0,
                        weight=0.0,
                        reason=f"Scorer error: {type(e).__name__}",
                        component=scorer.__class__.__name__,
                    )
                )

        # Clamp total score to [0.0, 1.0]
        total_score = max(0.0, min(1.0, total_score))

        # Build MatchEvidence
        evidence = self._build_evidence(
            total_score=total_score,
            component_scores=component_scores,
            file_info=file_info,
            tmdb_candidate=tmdb_candidate,
        )

        logger.debug(
            "Final score: %.3f (from %d scorers)",
            total_score,
            len(self.scorers),
        )

        return total_score, evidence

    def _validate_scorers(self) -> None:
        """Validate scorer list.

        Raises:
            DomainError: If validation fails
        """
        for i, scorer in enumerate(self.scorers):
            # Check if scorer has score method (Protocol check)
            if not hasattr(scorer, "score"):
                raise DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Scorer at index {i} does not implement score method",
                    context=ErrorContext(
                        operation="validate_scorers",
                        additional_data={
                            "scorer_index": i,
                            "scorer_type": type(scorer).__name__,
                        },
                    ),
                )

            # Check if scorer has weight attribute
            if not hasattr(scorer, "weight"):
                raise DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Scorer at index {i} does not have weight attribute",
                    context=ErrorContext(
                        operation="validate_scorers",
                        additional_data={
                            "scorer_index": i,
                            "scorer_type": type(scorer).__name__,
                        },
                    ),
                )

            # Validate weight range
            weight = scorer.weight
            if not isinstance(weight, (int, float)):
                raise DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Scorer weight must be numeric, got {type(weight).__name__}",
                    context=ErrorContext(
                        operation="validate_scorers",
                        additional_data={
                            "scorer_index": i,
                            "weight_type": type(weight).__name__,
                        },
                    ),
                )

            if not 0.0 <= weight <= 1.0:
                raise DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Scorer weight must be in [0.0, 1.0], got {weight}",
                    context=ErrorContext(
                        operation="validate_scorers",
                        additional_data={
                            "scorer_index": i,
                            "weight": weight,
                        },
                    ),
                )

    def _normalize_weights(self) -> None:
        """Normalize scorer weights to sum to 1.0.

        This modifies the weights in-place to ensure they sum to exactly 1.0.
        """
        total_weight = sum(scorer.weight for scorer in self.scorers)

        if total_weight == 0.0:
            # All weights are zero, assign equal weights
            equal_weight = 1.0 / len(self.scorers)
            for scorer in self.scorers:
                scorer.weight = equal_weight
            logger.warning(
                "All scorer weights were 0.0, assigned equal weights: %.3f",
                equal_weight,
            )
        elif total_weight != 1.0:
            # Normalize to sum to 1.0
            for scorer in self.scorers:
                scorer.weight = scorer.weight / total_weight
            logger.debug(
                "Normalized scorer weights from total %.3f to 1.0",
                total_weight,
            )

    def _build_evidence(
        self,
        total_score: float,
        component_scores: list[ScoreResult],
        file_info: ParsingResult,
        tmdb_candidate: TMDBSearchResult,
    ) -> MatchEvidence:
        """Build MatchEvidence from scoring results.

        Args:
            total_score: Final combined score
            component_scores: List of individual scorer results
            file_info: File information
            tmdb_candidate: TMDB search result dataclass instance

        Returns:
            MatchEvidence instance
        """
        # Extract TMDB ID (guaranteed to be int > 0 from TMDBSearchResult)
        tmdb_id = tmdb_candidate.id
        if tmdb_id <= 0:
            tmdb_id = 1  # MatchEvidence requires > 0

        # Extract media type (guaranteed to be "tv" or "movie" from TMDBSearchResult)
        media_type = tmdb_candidate.media_type

        # Extract TMDB title (use display_title property)
        matched_title = tmdb_candidate.display_title
        if not matched_title:
            # MatchEvidence requires min_length=1
            matched_title = "Unknown"

        # Build evidence
        return MatchEvidence(
            total_score=total_score,
            component_scores=component_scores,
            file_title=file_info.title,
            matched_title=matched_title,
            tmdb_id=tmdb_id,
            media_type=media_type,
        )


__all__ = ["ScoringEngine"]
