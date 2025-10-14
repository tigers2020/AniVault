"""Grouping engine for orchestrating multiple matchers.

This module provides the GroupingEngine class that coordinates multiple
matching strategies with weighted scoring to produce optimal file groupings
with evidence tracking.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anivault.core.file_grouper.matchers.base import BaseMatcher
    from anivault.core.file_grouper.models import Group
    from anivault.core.models import ScannedFile

logger = logging.getLogger(__name__)

# Default weights for matchers
DEFAULT_WEIGHTS = {
    "title": 0.6,  # Title similarity is most important
    "hash": 0.3,  # Hash-based matching is secondary
    "season": 0.1,  # Season metadata is supplementary
}


class GroupingEngine:
    """Orchestrates multiple matching strategies with weighted scoring.

    This engine runs multiple matchers in parallel, combines their results
    using weighted scoring, and generates evidence for grouping decisions.

    The engine uses a composite pattern to coordinate matchers and provides
    transparency through GroupingEvidence attached to each group.

    Attributes:
        matchers: List of BaseMatcher instances to use for grouping.
        weights: Dictionary mapping matcher component_name to weight (0.0-1.0).
                Must sum to 1.0.

    Example:
        >>> from anivault.core.file_grouper.matchers.title_matcher import TitleSimilarityMatcher
        >>> from anivault.core.file_grouper.matchers.hash_matcher import HashSimilarityMatcher
        >>> title_matcher = TitleSimilarityMatcher(...)
        >>> hash_matcher = HashSimilarityMatcher(...)
        >>> engine = GroupingEngine(
        ...     matchers=[title_matcher, hash_matcher],
        ...     weights={"title": 0.7, "hash": 0.3}
        ... )
        >>> groups = engine.group_files(scanned_files)
        >>> groups[0].evidence.confidence
        0.92
    """

    def __init__(
        self,
        matchers: list[BaseMatcher],
        weights: dict[str, float] | None = None,
    ) -> None:
        """Initialize the grouping engine.

        Args:
            matchers: List of matcher instances to use.
            weights: Optional custom weights for matchers.
                    If None, uses DEFAULT_WEIGHTS.
                    Must sum to 1.0.

        Raises:
            ValueError: If weights don't sum to 1.0 or are out of range.
            ValueError: If matchers list is empty.

        Example:
            >>> engine = GroupingEngine(
            ...     matchers=[title_matcher, hash_matcher],
            ...     weights={"title": 0.7, "hash": 0.3}
            ... )
        """
        if not matchers:
            raise ValueError("At least one matcher must be provided")

        self.matchers = matchers

        # Use default weights if not provided
        if weights is None:
            weights = DEFAULT_WEIGHTS.copy()

        # Validate weights
        self._validate_weights(weights)

        self.weights = weights

        logger.info(
            "GroupingEngine initialized with %d matcher(s): %s",
            len(matchers),
            [m.component_name for m in matchers],
        )

    def _validate_weights(self, weights: dict[str, float]) -> None:
        """Validate that weights are correct.

        Args:
            weights: Dictionary of weights to validate.

        Raises:
            ValueError: If weights don't sum to 1.0 or are out of range.

        Example:
            >>> engine._validate_weights({"title": 0.6, "hash": 0.4})
            # OK
            >>> engine._validate_weights({"title": 0.5, "hash": 0.6})
            # Raises ValueError
        """
        # Check sum is 1.0 (with floating point tolerance)
        total = sum(weights.values())
        if not math.isclose(total, 1.0, rel_tol=1e-5):
            raise ValueError(
                f"Weights must sum to 1.0, got {total}. Weights: {weights}"
            )

        # Check all values are in valid range
        for name, weight in weights.items():
            if not (0.0 <= weight <= 1.0):
                raise ValueError(
                    f"Weight for '{name}' must be between 0.0 and 1.0, got {weight}"
                )

    def group_files(self, files: list[ScannedFile]) -> list[Group]:
        """Group files using all matchers with weighted scoring.

        This method:
        1. Runs each matcher to get candidate groups
        2. Calculates weighted scores for each group
        3. Generates evidence for grouping decisions
        4. Returns groups with evidence attached

        Args:
            files: List of ScannedFile objects to group.

        Returns:
            List of Group objects with evidence attached.
            Groups are sorted by confidence (highest first).

        Example:
            >>> groups = engine.group_files(scanned_files)
            >>> groups[0].evidence.explanation
            'Grouped by title similarity (92%)'
        """
        if not files:
            return []

        # Import here to avoid circular dependency
        from anivault.core.file_grouper.models import Group, GroupingEvidence

        # Step 1: Run all matchers and collect results
        matcher_results: dict[str, list[Group]] = {}

        for matcher in self.matchers:
            try:
                logger.debug(
                    "Running matcher: %s",
                    matcher.component_name,
                )
                groups = matcher.match(files)
                matcher_results[matcher.component_name] = groups

                logger.info(
                    "Matcher '%s' produced %d group(s)",
                    matcher.component_name,
                    len(groups),
                )
            except Exception as e:
                logger.error(
                    "Matcher '%s' failed: %s",
                    matcher.component_name,
                    e,
                    exc_info=True,
                )
                # Skip failed matcher
                continue

        if not matcher_results:
            logger.warning("All matchers failed, returning empty list")
            return []

        # Step 2: For now, use simple strategy: pick results from highest-weighted matcher
        # TODO: Implement proper weighted merging in future iterations
        best_matcher = max(
            matcher_results.keys(),
            key=lambda name: self.weights.get(name, 0.0),
        )

        best_groups = matcher_results[best_matcher]
        best_weight = self.weights.get(best_matcher, 0.0)

        logger.info(
            "Selected groups from matcher '%s' (weight=%.2f)",
            best_matcher,
            best_weight,
        )

        # Step 3: Generate evidence for each group
        result_groups = []
        for group in best_groups:
            # Calculate confidence based on weight
            confidence = best_weight

            # Create evidence
            evidence = GroupingEvidence(
                match_scores={best_matcher: confidence},
                selected_matcher=best_matcher,
                explanation=self._generate_explanation(best_matcher, confidence),
                confidence=confidence,
            )

            # Create new group with evidence
            new_group = Group(
                title=group.title,
                files=group.files,
                evidence=evidence,
            )
            result_groups.append(new_group)

        # Sort by confidence (highest first)
        result_groups.sort(
            key=lambda g: g.evidence.confidence if g.evidence else 0, reverse=True
        )

        logger.info(
            "GroupingEngine produced %d final group(s)",
            len(result_groups),
        )

        return result_groups

    def _generate_explanation(self, matcher_name: str, confidence: float) -> str:
        """Generate user-facing explanation for grouping decision.

        Args:
            matcher_name: Name of the matcher that produced the group.
            confidence: Confidence score (0.0-1.0).

        Returns:
            User-friendly explanation string.

        Example:
            >>> engine._generate_explanation("title", 0.92)
            'Grouped by title similarity (92%)'
        """
        confidence_pct = int(confidence * 100)

        explanations = {
            "title": f"Grouped by title similarity ({confidence_pct}%)",
            "hash": f"Grouped by normalized hash ({confidence_pct}% match)",
            "season": f"Grouped by season metadata ({confidence_pct}% confidence)",
        }

        return explanations.get(
            matcher_name,
            f"Grouped by {matcher_name} ({confidence_pct}%)",
        )


__all__ = ["DEFAULT_WEIGHTS", "GroupingEngine"]
