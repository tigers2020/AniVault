"""Grouping engine for orchestrating multiple matchers.

This module provides the GroupingEngine class that coordinates multiple
matching strategies with weighted scoring to produce optimal file groupings
with evidence tracking.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from .strategies import BestMatcherStrategy, GroupingStrategy

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
        strategy: GroupingStrategy | None = None,
    ) -> None:
        """Initialize the grouping engine.

        Args:
            matchers: List of matcher instances to use.
            weights: Optional custom weights for matchers.
                    If None, uses DEFAULT_WEIGHTS.
                    Must sum to 1.0.
            strategy: Optional grouping strategy to use.
                     If None, uses BestMatcherStrategy (current behavior).

        Raises:
            ValueError: If weights don't sum to 1.0 or are out of range.
            ValueError: If matchers list is empty.

        Example:
            >>> from anivault.core.file_grouper.strategies import WeightedMergeStrategy
            >>> engine = GroupingEngine(
            ...     matchers=[title_matcher, hash_matcher],
            ...     weights={"title": 0.7, "hash": 0.3},
            ...     strategy=WeightedMergeStrategy()
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

        # Use provided strategy or default to BestMatcherStrategy
        self.strategy = strategy or BestMatcherStrategy()

        logger.info(
            "GroupingEngine initialized with %d matcher(s): %s, strategy: %s",
            len(matchers),
            [m.component_name for m in matchers],
            self.strategy.__class__.__name__,
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
            msg = f"Weights must sum to 1.0, got {total}. Weights: {weights}"
            raise ValueError(msg)

        # Check all values are in valid range
        for name, weight in weights.items():
            if not (0.0 <= weight <= 1.0):
                msg = f"Weight for '{name}' must be between 0.0 and 1.0, got {weight}"
                raise ValueError(msg)

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
            except Exception:
                logger.exception(
                    "Matcher '%s' failed",
                    matcher.component_name,
                )
                # Skip failed matcher
                continue

        if not matcher_results:
            logger.warning("All matchers failed, returning empty list")
            return []

        # Step 2: Use strategy to combine matcher results
        result_groups = self.strategy.combine_results(
            matcher_results=matcher_results,
            weights=self.weights,
        )

        logger.info(
            "GroupingEngine produced %d final group(s) using %s strategy",
            len(result_groups),
            self.strategy.__class__.__name__,
        )

        return result_groups


__all__ = ["DEFAULT_WEIGHTS", "GroupingEngine"]
