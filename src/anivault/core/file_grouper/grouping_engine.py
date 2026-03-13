"""Grouping engine for orchestrating multiple matchers.

This module provides the GroupingEngine class that coordinates multiple
matching strategies with weighted scoring to produce optimal file groupings
with evidence tracking.
"""

from __future__ import annotations

import logging
import math

from anivault.config import load_settings
from anivault.config.models.grouping_settings import GroupingSettings
from anivault.core.file_grouper.grouping_weights import get_default_weights_from_config
from anivault.core.file_grouper.matchers.base import BaseMatcher
from anivault.core.file_grouper.models import Group, GroupingEvidence
from anivault.core.models import ScannedFile
from anivault.shared.errors import (
    AniVaultParsingError,
    ErrorCode,
    ErrorContextModel,
)

from .strategies import BestMatcherStrategy, GroupingStrategy

logger = logging.getLogger(__name__)

# Log format for matcher failure (S1192: single source for duplicated literal)
_LOG_MATCHER_FAILED = "Matcher '%s' failed: %s"


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
                    If None, uses MatchingWeights defaults.
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
            weights = get_default_weights_from_config()

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
        """Get grouping settings from configuration system.

        Loads GroupingSettings from the main Settings system.
        Falls back to default settings if configuration is not available.

        Returns:
            GroupingSettings instance with use_title_matcher and max_title_match_group_size.

        Note:
            This method attempts to load settings from the configuration system.
            If loading fails, returns default settings for graceful degradation.
        """
        try:
            settings = load_settings()
            if hasattr(settings, "grouping") and settings.grouping is not None:
                return settings.grouping
        except (ImportError, AttributeError) as e:
            logger.debug(
                "Could not load GroupingSettings from config, using defaults: %s",
                e,
            )

        # Return default settings if config not available
        return GroupingSettings()

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
            if not 0.0 <= weight <= 1.0:
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

        # Step 1: Separate Hash and Title matchers
        hash_matcher, title_matcher, other_matchers = self._separate_matchers()

        # Step 2: Run Hash matcher first (required for pipeline)
        if hash_matcher is None:
            logger.warning(
                "Hash matcher not found, falling back to parallel execution",
            )
            return self._group_files_parallel(files)

        hash_groups, matcher_results = self._run_hash_matcher(hash_matcher, files)
        if not hash_groups and not matcher_results:
            return []

        # Step 3: Run Title matcher on Hash groups (if enabled)
        self._refine_with_title_matcher(
            title_matcher,
            hash_groups,
            matcher_results,
        )

        # Step 4: Run other matchers in parallel (if any)
        self._run_other_matchers(other_matchers, files, matcher_results)

        if not matcher_results:
            logger.warning("All matchers failed, returning empty list")
            return []

        # Step 5: Use strategy to combine matcher results
        return self._combine_matcher_results(matcher_results)

    def _separate_matchers(
        self,
    ) -> tuple[BaseMatcher | None, BaseMatcher | None, list[BaseMatcher]]:
        """Separate matchers by type (Hash, Title, Other).

        Returns:
            Tuple of (hash_matcher, title_matcher, other_matchers)
        """
        hash_matcher: BaseMatcher | None = None
        title_matcher: BaseMatcher | None = None
        other_matchers: list[BaseMatcher] = []

        for matcher in self.matchers:
            if matcher.component_name == "hash":
                hash_matcher = matcher
            elif matcher.component_name == "title":
                title_matcher = matcher
            else:
                other_matchers.append(matcher)

        return hash_matcher, title_matcher, other_matchers

    def _run_hash_matcher(
        self,
        hash_matcher: BaseMatcher,
        files: list[ScannedFile],
    ) -> tuple[list[Group], dict[str, list[Group]]]:
        """Run Hash matcher and return results.

        Args:
            hash_matcher: Hash matcher instance
            files: List of files to match

        Returns:
            Tuple of (hash_groups, matcher_results dict)
            Returns empty lists on failure
        """
        matcher_results: dict[str, list[Group]] = {}

        try:
            logger.debug("Running Hash matcher (pipeline step 1)")
            hash_groups = hash_matcher.match(files)
            matcher_results["hash"] = hash_groups

            logger.info(
                "Hash matcher produced %d group(s)",
                len(hash_groups),
            )
            return hash_groups, matcher_results

        except (KeyError, ValueError, AttributeError, TypeError) as e:
            context = ErrorContextModel(
                operation="hash_matcher_match",
                additional_data={"file_count": len(files)},
            )
            error = AniVaultParsingError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"Hash matcher failed due to data parsing error: {e}",
                context,
                original_error=e,
            )
            logger.exception("Hash matcher failed, cannot continue pipeline: %s", error.message)
            return [], {}

        except Exception as e:  # pylint: disable=broad-exception-caught
            context = ErrorContextModel(
                operation="hash_matcher_match",
                additional_data={"file_count": len(files)},
            )
            error = AniVaultParsingError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"Hash matcher failed, cannot continue pipeline: {e}",
                context,
                original_error=e,
            )
            logger.exception("Hash matcher failed, cannot continue pipeline: %s", error.message)
            return [], {}

    def _refine_with_title_matcher(
        self,
        title_matcher: BaseMatcher | None,
        hash_groups: list[Group],
        matcher_results: dict[str, list[Group]],
    ) -> None:
        """Refine Hash groups using Title matcher if enabled.

        Args:
            title_matcher: Title matcher instance or None
            hash_groups: List of groups from Hash matcher
            matcher_results: Dictionary to update with Title matcher results
        """
        if title_matcher is None:
            return

        grouping_settings = self._get_grouping_settings()
        if not grouping_settings.use_title_matcher:
            return

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
                max_title_match_group_size=grouping_settings.max_title_match_group_size,
            )
            matcher_results["title"] = title_groups

            logger.info(
                "Title matcher refined %d Hash group(s) into %d group(s)",
                len(hash_groups),
                len(title_groups),
            )

        except (KeyError, ValueError, AttributeError, TypeError) as e:
            context = ErrorContextModel(
                operation="title_matcher_refine",
                additional_data={"hash_group_count": len(hash_groups)},
            )
            error = AniVaultParsingError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"Title matcher failed due to data parsing error: {e}",
                context,
                original_error=e,
            )
            logger.exception("Title matcher failed, using Hash results only: %s", error.message)

        except Exception as e:  # pylint: disable=broad-exception-caught
            context = ErrorContextModel(
                operation="title_matcher_refine",
                additional_data={"hash_group_count": len(hash_groups)},
            )
            error = AniVaultParsingError(
                ErrorCode.FILE_GROUPING_FAILED,
                f"Title matcher failed, using Hash results only: {e}",
                context,
                original_error=e,
            )
            logger.exception("Title matcher failed, using Hash results only: %s", error.message)

    def _run_other_matchers(
        self,
        other_matchers: list[BaseMatcher],
        files: list[ScannedFile],
        matcher_results: dict[str, list[Group]],
    ) -> None:
        """Run other matchers in parallel and update results.

        Args:
            other_matchers: List of matchers to run
            files: List of files to match
            matcher_results: Dictionary to update with matcher results
        """
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

            except (KeyError, ValueError, AttributeError, TypeError) as e:
                context = ErrorContextModel(
                    operation="other_matcher_match_step4",
                    additional_data={
                        "matcher_name": matcher.component_name,
                        "file_count": len(files),
                    },
                )
                error = AniVaultParsingError(
                    ErrorCode.FILE_GROUPING_FAILED,
                    f"Matcher '{matcher.component_name}' failed due to data parsing error: {e}",
                    context,
                    original_error=e,
                )
                logger.exception(_LOG_MATCHER_FAILED, matcher.component_name, error.message)
                continue

            except Exception as e:  # pylint: disable=broad-exception-caught
                context = ErrorContextModel(
                    operation="other_matcher_match_step4",
                    additional_data={
                        "matcher_name": matcher.component_name,
                        "file_count": len(files),
                    },
                )
                error = AniVaultParsingError(
                    ErrorCode.FILE_GROUPING_FAILED,
                    f"Matcher '{matcher.component_name}' failed: {e}",
                    context,
                    original_error=e,
                )
                logger.exception(_LOG_MATCHER_FAILED, matcher.component_name, error.message)
                continue

    def _combine_matcher_results(
        self,
        matcher_results: dict[str, list[Group]],
    ) -> list[Group]:
        """Combine matcher results using strategy pattern.

        Args:
            matcher_results: Dictionary of matcher results

        Returns:
            List of combined Group objects
        """
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
            except (KeyError, ValueError, AttributeError, TypeError) as e:
                # Data structure access errors during parallel matching
                context = ErrorContextModel(
                    operation="parallel_matcher_match",
                    additional_data={
                        "matcher_name": matcher.component_name,
                        "file_count": len(files),
                    },
                )
                error = AniVaultParsingError(
                    ErrorCode.FILE_GROUPING_FAILED,
                    f"Matcher '{matcher.component_name}' failed due to data parsing error: {e}",
                    context,
                    original_error=e,
                )
                logger.exception(_LOG_MATCHER_FAILED, matcher.component_name, error.message)
                # Skip failed matcher
                continue
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Unexpected errors during parallel matching (catch-all for unknown exceptions)
                context = ErrorContextModel(
                    operation="parallel_matcher_match",
                    additional_data={
                        "matcher_name": matcher.component_name,
                        "file_count": len(files),
                    },
                )
                error = AniVaultParsingError(
                    ErrorCode.FILE_GROUPING_FAILED,
                    f"Matcher '{matcher.component_name}' failed: {e}",
                    context,
                    original_error=e,
                )
                logger.exception(_LOG_MATCHER_FAILED, matcher.component_name, error.message)
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

    def _append_hash_group_fallback(
        self,
        refined_groups: list[Group],
        hash_group: Group,
        explanation_suffix: str,
    ) -> None:
        """Append hash_group to refined_groups and optionally update evidence."""
        if hash_group.evidence:
            hash_group.evidence.explanation = f"{hash_group.evidence.explanation} {explanation_suffix}"
        refined_groups.append(hash_group)

    def _refine_one_group_via_refine_group(
        self,
        hash_group: Group,
        title_matcher: BaseMatcher,
        hash_weight: float,
        title_weight: float,
    ) -> list[Group] | None:
        """Refine one hash group using title_matcher.refine_group(). Returns None to use fallback."""
        refined_result = title_matcher.refine_group(hash_group)  # type: ignore[attr-defined]
        if not refined_result:
            return None
        groups_to_add: list[Group] = refined_result if isinstance(refined_result, list) else [refined_result]
        for refined_group in groups_to_add:
            refined_group.evidence = self._merge_pipeline_evidence(
                hash_group.evidence,
                refined_group.evidence,
                hash_weight,
                title_weight,
            )
        return groups_to_add

    def _refine_one_group_via_match(
        self,
        hash_group: Group,
        title_matcher: BaseMatcher,
        hash_weight: float,
        title_weight: float,
    ) -> list[Group]:
        """Refine one hash group using title_matcher.match(). Returns list of groups or empty for fallback."""
        title_subgroups = title_matcher.match(hash_group.files)
        if not title_subgroups:
            return []
        for title_subgroup in title_subgroups:
            title_subgroup.evidence = self._merge_pipeline_evidence(
                hash_group.evidence,
                title_subgroup.evidence,
                hash_weight,
                title_weight,
            )
        return title_subgroups

    def _handle_title_refine_exception(
        self,
        refined_groups: list[Group],
        hash_group: Group,
        exc: Exception,
        parsing_error: bool,
    ) -> None:
        """Log title refinement failure and append hash group as fallback."""
        message = (
            f"Title matcher failed for group '{hash_group.title}' due to data parsing error: {exc}"
            if parsing_error
            else f"Title matcher failed for group '{hash_group.title}': {exc}"
        )
        context = ErrorContextModel(
            operation="title_matcher_refine_per_group",
            additional_data={
                "group_title": hash_group.title,
                "file_count": len(hash_group.files),
            },
        )
        error = AniVaultParsingError(
            ErrorCode.FILE_GROUPING_FAILED,
            message,
            context,
            original_error=exc,
        )
        logger.exception(
            "Title matcher failed for group '%s', using Hash result: %s",
            hash_group.title,
            error.message,
        )
        self._append_hash_group_fallback(refined_groups, hash_group, "(Title matcher failed)")

    def _process_one_hash_group_for_title_refine(
        self,
        refined_groups: list[Group],
        hash_group: Group,
        title_matcher: BaseMatcher,
        has_refine_group: bool,
        hash_weight: float,
        title_weight: float,
    ) -> None:
        """Refine a single Hash group with Title matcher and append to refined_groups."""
        try:
            if has_refine_group:
                groups = self._refine_one_group_via_refine_group(hash_group, title_matcher, hash_weight, title_weight)
                if groups is not None:
                    refined_groups.extend(groups)
                else:
                    self._append_hash_group_fallback(refined_groups, hash_group, "(Title refinement returned None)")
            else:
                groups = self._refine_one_group_via_match(hash_group, title_matcher, hash_weight, title_weight)
                if groups:
                    refined_groups.extend(groups)
                else:
                    self._append_hash_group_fallback(refined_groups, hash_group, "(Title matcher returned empty)")
        except (KeyError, ValueError, AttributeError, TypeError) as e:
            self._handle_title_refine_exception(refined_groups, hash_group, e, parsing_error=True)
        except Exception as e:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            self._handle_title_refine_exception(refined_groups, hash_group, e, parsing_error=False)

    def _refine_groups_with_title_matcher(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
        refined_groups: list[Group] = []
        has_refine_group = hasattr(title_matcher, "refine_group")

        for hash_group in hash_groups:
            if not hash_group.files:
                continue
            if len(hash_group.files) > max_title_match_group_size:
                logger.debug(
                    "Skipping Title matcher for group '%s' (size: %d > limit: %d)",
                    hash_group.title,
                    len(hash_group.files),
                    max_title_match_group_size,
                )
                refined_groups.append(hash_group)
                continue
            self._process_one_hash_group_for_title_refine(
                refined_groups,
                hash_group,
                title_matcher,
                has_refine_group,
                hash_weight,
                title_weight,
            )
        return refined_groups

    def _add_matcher_contribution(
        self,
        match_scores: dict[str, float],
        contributing_matchers: list[str],
        evidence: GroupingEvidence | None,
        matcher_key: str,
        fallback_weight: float,
    ) -> None:
        """Add one matcher's contribution to match_scores and contributing_matchers."""
        if evidence:
            match_scores.update(evidence.match_scores)
            if matcher_key in evidence.match_scores and matcher_key not in contributing_matchers:
                contributing_matchers.append(matcher_key)
        elif fallback_weight > 0.0 and matcher_key not in contributing_matchers:
            match_scores[matcher_key] = fallback_weight
            contributing_matchers.append(matcher_key)

    def _build_pipeline_explanation(
        self,
        match_scores: dict[str, float],
        contributing_matchers: list[str],
        confidence: float,
    ) -> tuple[str, str]:
        """Build explanation string and selected_matcher from merged evidence."""
        is_pipeline = len(contributing_matchers) == 2 and "hash" in contributing_matchers and "title" in contributing_matchers
        if is_pipeline:
            explanation = (
                f"Hash → Title pipeline: "
                f"Hash ({int(match_scores.get('hash', 0.0) * 100)}%) + "
                f"Title ({int(match_scores.get('title', 0.0) * 100)}%) = "
                f"{int(confidence * 100)}% confidence"
            )
            return explanation, "hash,title"
        if len(contributing_matchers) == 1:
            matcher_name = contributing_matchers[0]
            score_pct = int(match_scores.get(matcher_name, 0.0) * 100)
            return f"Grouped by {matcher_name} similarity ({score_pct}%)", matcher_name
        matcher_list = ", ".join(contributing_matchers)
        return (
            f"Grouped by {matcher_list} ({int(confidence * 100)}% confidence)",
            ",".join(contributing_matchers),
        )

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
        match_scores: dict[str, float] = {}
        contributing_matchers: list[str] = []

        self._add_matcher_contribution(match_scores, contributing_matchers, hash_evidence, "hash", hash_weight)
        self._add_matcher_contribution(match_scores, contributing_matchers, title_evidence, "title", title_weight)

        total_weight = sum(match_scores.get(m, 0.0) for m in contributing_matchers)
        confidence = total_weight / len(contributing_matchers) if contributing_matchers else 0.0

        explanation, selected_matcher = self._build_pipeline_explanation(match_scores, contributing_matchers, confidence)

        return GroupingEvidence(
            match_scores=match_scores,
            selected_matcher=selected_matcher,
            explanation=explanation,
            confidence=confidence,
        )


__all__ = ["GroupingEngine"]
