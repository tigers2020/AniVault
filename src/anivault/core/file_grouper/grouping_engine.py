"""Grouping engine for orchestrating multiple matchers.

This module provides the GroupingEngine class that coordinates multiple
matching strategies with weighted scoring to produce optimal file groupings
with evidence tracking.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .strategies import BestMatcherStrategy, GroupingStrategy

if TYPE_CHECKING:
    from anivault.core.file_grouper.matchers.base import BaseMatcher
    from anivault.core.file_grouper.models import Group, GroupingEvidence
    from anivault.core.models import ScannedFile

logger = logging.getLogger(__name__)


@dataclass
class GroupingSettings:
    """Settings for grouping operations.

    This dataclass provides configuration for the grouping pipeline,
    including whether to use Title matcher and size limits for performance.

    Attributes:
        use_title_matcher: Whether to run Title matcher after Hash matcher.
                          Default: True
        max_title_match_group_size: Maximum number of files in a group for
                                   Title matcher processing. Groups larger than
                                   this will skip Title matcher (DoS protection).
                                   Default: 1000

    Note:
        This is a temporary dataclass until GroupingSettings is integrated
        into the main Settings system (Task 3). Once integrated, this
        dataclass may be removed or moved to the settings module.
    """

    use_title_matcher: bool = True
    max_title_match_group_size: int = 1000


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

    def _get_grouping_settings(self) -> GroupingSettings:
        """Get grouping settings with fallback to defaults.

        Attempts to load GroupingSettings from configuration system.
        If not available, returns default settings.

        Returns:
            GroupingSettings instance with use_title_matcher and max_title_match_group_size.

        Note:
            This method is designed to work with or without GroupingSettings.
            When Task 3 (settings system) is completed, this method will
            read from the actual configuration. Until then, it returns defaults.
        """
        # Try to import and use GroupingSettings if available
        try:
            # Future: When GroupingSettings is implemented, uncomment this:
            # from anivault.core.file_grouper.settings import GroupingSettings
            # from anivault.config.loader import load_settings
            # settings = load_settings()
            # return settings.grouping  # or however it's structured
            pass
        except (ImportError, AttributeError):
            # GroupingSettings not available yet, use defaults
            pass

        # Return default settings (dataclass for type safety)
        return GroupingSettings(
            use_title_matcher=True,
            max_title_match_group_size=1000,  # Default: 1000 files per group
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
        """Group files using Hash-first pipeline with optional Title refinement.

        This method implements a pipeline approach:
        1. Runs Hash matcher first to create initial groups
        2. Optionally runs Title matcher on each Hash group for refinement
        3. Combines results using strategy pattern
        4. Returns groups with evidence attached

        Args:
            files: List of ScannedFile objects to group.

        Returns:
            List of Group objects with evidence attached.
            Groups are sorted by confidence (highest first).

        Example:
            >>> groups = engine.group_files(scanned_files)
            >>> groups[0].evidence.explanation
            'Grouped by hash + title similarity (92%)'
        """
        if not files:
            return []

        # Import here to avoid circular dependency

        # Step 1: Separate Hash and Title matchers
        hash_matcher = None
        title_matcher = None
        other_matchers: list[BaseMatcher] = []

        for matcher in self.matchers:
            if matcher.component_name == "hash":
                hash_matcher = matcher
            elif matcher.component_name == "title":
                title_matcher = matcher
            else:
                other_matchers.append(matcher)

        # Step 2: Run Hash matcher first (required for pipeline)
        matcher_results: dict[str, list[Group]] = {}

        if hash_matcher is None:
            logger.warning(
                "Hash matcher not found, falling back to parallel execution",
            )
            # Fallback to original parallel execution
            return self._group_files_parallel(files)

        try:
            logger.debug("Running Hash matcher (pipeline step 1)")
            hash_groups = hash_matcher.match(files)
            matcher_results["hash"] = hash_groups

            logger.info(
                "Hash matcher produced %d group(s)",
                len(hash_groups),
            )
        except Exception:
            logger.exception("Hash matcher failed, cannot continue pipeline")
            # Hash matcher failure is critical for pipeline
            return []

        # Step 3: Run Title matcher on Hash groups (if enabled)
        grouping_settings = self._get_grouping_settings()
        use_title_matcher = grouping_settings.use_title_matcher
        max_title_match_group_size = grouping_settings.max_title_match_group_size

        if use_title_matcher and title_matcher is not None:
            try:
                logger.debug(
                    "Running Title matcher on %d Hash group(s) (pipeline step 2)",
                    len(hash_groups),
                )
                title_groups = self._refine_groups_with_title_matcher(
                    hash_groups,
                    title_matcher,
                    hash_weight=self.weights.get("hash", 0.0),
                    title_weight=self.weights.get("title", 0.0),
                    max_title_match_group_size=max_title_match_group_size,
                )
                matcher_results["title"] = title_groups

                logger.info(
                    "Title matcher refined %d Hash group(s) into %d group(s)",
                    len(hash_groups),
                    len(title_groups),
                )
            except Exception:
                logger.exception(
                    "Title matcher failed, using Hash results only",
                )
                # Title matcher failure is non-critical, use Hash results

        # Step 4: Run other matchers in parallel (if any)
        for matcher in other_matchers:
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

        # Step 5: Use strategy to combine matcher results
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

    def _group_files_parallel(self, files: list[ScannedFile]) -> list[Group]:
        """Fallback: Group files using parallel matcher execution.

        This is the original implementation used when Hash matcher is not available.

        Args:
            files: List of ScannedFile objects to group.

        Returns:
            List of Group objects with evidence attached.
        """
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

    def _refine_groups_with_title_matcher(
        self,
        hash_groups: list[Group],
        title_matcher: BaseMatcher,
        hash_weight: float = 0.0,
        title_weight: float = 0.0,
        max_title_match_group_size: int = 1000,
    ) -> list[Group]:
        """Refine Hash groups using Title matcher.

        For each Hash group, extracts files and runs Title matcher to create
        refined sub-groups. If Title matcher has refine_group() method, uses it;
        otherwise falls back to match() method.

        Updates evidence to reflect both Hash and Title matcher contributions
        in the pipeline approach.

        Args:
            hash_groups: List of Group objects from Hash matcher.
            title_matcher: Title matcher instance to use for refinement.
            hash_weight: Weight for Hash matcher (for evidence calculation).
            title_weight: Weight for Title matcher (for evidence calculation).

        Returns:
            List of refined Group objects from Title matcher with updated evidence.
        """
        # Import here to avoid circular dependency

        refined_groups: list[Group] = []

        # Check if Title matcher has refine_group method (Task 2.1)
        has_refine_group = hasattr(title_matcher, "refine_group")

        for hash_group in hash_groups:
            if not hash_group.files:
                continue

            # Check group size limit (DoS protection)
            if len(hash_group.files) > max_title_match_group_size:
                logger.debug(
                    "Skipping Title matcher for group '%s' (size: %d > limit: %d)",
                    hash_group.title,
                    len(hash_group.files),
                    max_title_match_group_size,
                )
                # Use Hash group as-is (skip Title matcher for large groups)
                refined_groups.append(hash_group)
                continue

            try:
                if has_refine_group:
                    # Use refine_group if available (preferred)
                    refined_group = title_matcher.refine_group(hash_group)  # type: ignore[attr-defined]
                    if refined_group:
                        # Merge evidence from Hash and Title matchers
                        refined_group.evidence = self._merge_pipeline_evidence(
                            hash_group.evidence,
                            refined_group.evidence,
                            hash_weight,
                            title_weight,
                        )
                        refined_groups.append(refined_group)
                    else:
                        # Fallback to Hash group if refinement returns None
                        # Update evidence to indicate pipeline was attempted
                        if hash_group.evidence:
                            hash_group.evidence.explanation = (
                                f"{hash_group.evidence.explanation} "
                                "(Title refinement returned None)"
                            )
                        refined_groups.append(hash_group)
                else:
                    # Fallback: Extract files and use match() method
                    title_subgroups = title_matcher.match(hash_group.files)
                    if title_subgroups:
                        # Merge evidence for each Title subgroup
                        for title_subgroup in title_subgroups:
                            title_subgroup.evidence = self._merge_pipeline_evidence(
                                hash_group.evidence,
                                title_subgroup.evidence,
                                hash_weight,
                                title_weight,
                            )
                        refined_groups.extend(title_subgroups)
                    else:
                        # Fallback to Hash group if Title matcher returns empty
                        # Update evidence to indicate Title matcher was attempted
                        if hash_group.evidence:
                            hash_group.evidence.explanation = (
                                f"{hash_group.evidence.explanation} "
                                "(Title matcher returned empty)"
                            )
                        refined_groups.append(hash_group)

            except Exception:
                logger.exception(
                    "Title matcher failed for group '%s', using Hash result",
                    hash_group.title,
                )
                # Use Hash group as fallback
                # Update evidence to indicate Title matcher failed
                if hash_group.evidence:
                    hash_group.evidence.explanation = (
                        f"{hash_group.evidence.explanation} (Title matcher failed)"
                    )
                refined_groups.append(hash_group)

        return refined_groups

    def _merge_pipeline_evidence(
        self,
        hash_evidence: GroupingEvidence | None,
        title_evidence: GroupingEvidence | None,
        hash_weight: float,
        title_weight: float,
    ) -> GroupingEvidence:
        """Merge evidence from Hash and Title matchers in pipeline approach.

        Combines evidence from both matchers to reflect the pipeline process
        where Hash matcher creates initial groups and Title matcher refines them.

        Args:
            hash_evidence: Evidence from Hash matcher (may be None).
            title_evidence: Evidence from Title matcher (may be None).
            hash_weight: Weight for Hash matcher.
            title_weight: Weight for Title matcher.

        Returns:
            Merged GroupingEvidence reflecting both matchers' contributions.
        """
        # Import here to avoid circular dependency
        from anivault.core.file_grouper.models import GroupingEvidence

        # Start with empty evidence
        match_scores: dict[str, float] = {}
        contributing_matchers: list[str] = []

        # Add Hash matcher contribution
        if hash_evidence:
            match_scores.update(hash_evidence.match_scores)
            if "hash" in hash_evidence.match_scores:
                contributing_matchers.append("hash")
        elif hash_weight > 0.0:
            match_scores["hash"] = hash_weight
            contributing_matchers.append("hash")

        # Add Title matcher contribution
        if title_evidence:
            match_scores.update(title_evidence.match_scores)
            if "title" in title_evidence.match_scores:
                if "title" not in contributing_matchers:
                    contributing_matchers.append("title")
        elif title_weight > 0.0:
            match_scores["title"] = title_weight
            if "title" not in contributing_matchers:
                contributing_matchers.append("title")

        # Calculate combined confidence (weighted average)
        if contributing_matchers:
            total_weight = sum(
                match_scores.get(matcher, 0.0) for matcher in contributing_matchers
            )
            confidence = (
                total_weight / len(contributing_matchers)
                if contributing_matchers
                else 0.0
            )
        else:
            confidence = 0.0

        # Generate explanation with pipeline information
        if (
            len(contributing_matchers) == 2
            and "hash" in contributing_matchers
            and "title" in contributing_matchers
        ):
            explanation = (
                f"Hash → Title pipeline: "
                f"Hash ({int(match_scores.get('hash', 0.0) * 100)}%) + "
                f"Title ({int(match_scores.get('title', 0.0) * 100)}%) = "
                f"{int(confidence * 100)}% confidence"
            )
            selected_matcher = "hash,title"
        elif len(contributing_matchers) == 1:
            matcher_name = contributing_matchers[0]
            explanation = (
                f"Grouped by {matcher_name} similarity "
                f"({int(match_scores.get(matcher_name, 0.0) * 100)}%)"
            )
            selected_matcher = matcher_name
        else:
            matcher_list = ", ".join(contributing_matchers)
            explanation = (
                f"Grouped by {matcher_list} ({int(confidence * 100)}% confidence)"
            )
            selected_matcher = ",".join(contributing_matchers)

        return GroupingEvidence(
            match_scores=match_scores,
            selected_matcher=selected_matcher,
            explanation=explanation,
            confidence=confidence,
        )


__all__ = ["DEFAULT_WEIGHTS", "GroupingEngine"]
