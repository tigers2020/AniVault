"""
Grouping Strategy Implementations

This module provides different strategies for combining matcher results
in the GroupingEngine. Each strategy implements a different approach
to merging multiple matcher outputs into final groups.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from anivault.core.file_grouper.models import Group, GroupingEvidence

logger = logging.getLogger(__name__)


class GroupingStrategy(ABC):
    """Abstract base class for grouping strategies.

    Each strategy defines how to combine results from multiple matchers
    into final groups with evidence.
    """

    @abstractmethod
    def combine_results(
        self,
        matcher_results: dict[str, list[Group]],
        weights: dict[str, float],
    ) -> list[Group]:
        """Combine matcher results into final groups.

        Args:
            matcher_results: Dictionary mapping matcher names to their Group results
            weights: Dictionary mapping matcher names to their weights

        Returns:
            List of final Group objects with evidence
        """

    @staticmethod
    def _format_confidence_percentage(confidence: float) -> int:
        """Format confidence value as percentage integer.

        Args:
            confidence: Confidence value between 0.0 and 1.0

        Returns:
            Percentage as integer (0-100)
        """
        return int(confidence * 100)

    @staticmethod
    def _create_evidence(
        match_scores: dict[str, float],
        contributing_matchers: list[str],
        explanation: str,
        confidence: float,
    ) -> GroupingEvidence:
        """Create GroupingEvidence with consistent formatting.

        Args:
            match_scores: Dictionary mapping matcher names to their scores
            contributing_matchers: List of matcher names that contributed
            explanation: Human-readable explanation of the grouping
            confidence: Overall confidence score (0.0-1.0)

        Returns:
            GroupingEvidence instance
        """
        return GroupingEvidence(
            match_scores=match_scores,
            selected_matcher=",".join(contributing_matchers),
            explanation=explanation,
            confidence=confidence,
        )


class WeightedMergeStrategy(GroupingStrategy):
    """Strategy that merges groups based on weighted scoring.

    This strategy:
    1. Identifies overlapping groups across matchers
    2. Calculates weighted confidence scores
    3. Merges overlapping groups with highest combined score
    4. Generates evidence showing contribution from each matcher
    """

    def combine_results(
        self,
        matcher_results: dict[str, list[Group]],
        weights: dict[str, float],
    ) -> list[Group]:
        """Combine results using weighted merge strategy."""
        if not matcher_results:
            return []

        # Step 1: Create file-to-group mapping for each matcher
        file_groups: dict[str, dict[str, Group]] = {}
        for matcher_name, groups in matcher_results.items():
            file_groups[matcher_name] = {}
            for group in groups:
                for file in group.files:
                    file_groups[matcher_name][file.file_path.name] = group

        # Step 2: Find overlapping groups across matchers
        merged_groups = self._merge_overlapping_groups(
            matcher_results, weights, file_groups
        )

        # Step 3: Generate evidence for each merged group
        final_groups = []
        for group in merged_groups:
            evidence = self._generate_merge_evidence(group, matcher_results, weights)
            final_group = Group(
                title=group.title,
                files=group.files,
                evidence=evidence,
            )
            final_groups.append(final_group)

        # Sort by confidence (highest first)
        final_groups.sort(
            key=lambda g: g.evidence.confidence if g.evidence else 0, reverse=True
        )

        logger.info("WeightedMergeStrategy produced %d final groups", len(final_groups))

        return final_groups

    def _merge_overlapping_groups(
        self,
        matcher_results: dict[str, list[Group]],
        weights: dict[str, float],
        _file_groups: dict[str, dict[str, Group]],
    ) -> list[Group]:
        """Merge groups that have overlapping files."""
        # Create a mapping of files to all groups they belong to
        file_to_groups: dict[str, list[tuple[str, Group]]] = {}

        for matcher_name, groups in matcher_results.items():
            for group in groups:
                for file in group.files:
                    file_name = file.file_path.name
                    if file_name not in file_to_groups:
                        file_to_groups[file_name] = []
                    file_to_groups[file_name].append((matcher_name, group))

        # Group files by their overlapping groups
        merged_groups = []
        processed_files = set()

        for file_name, groups_info in file_to_groups.items():
            if file_name in processed_files:
                continue

            # Find all files that share groups with this file
            cluster_files = {file_name}
            cluster_groups = set(groups_info)

            # Expand cluster by finding connected files
            changed = True
            while changed:
                changed = False
                for other_file, other_groups in file_to_groups.items():
                    if other_file in processed_files:
                        continue

                    # Check if this file shares any groups with cluster
                    if any(
                        (matcher_name, group) in cluster_groups
                        for matcher_name, group in other_groups
                    ):
                        cluster_files.add(other_file)
                        cluster_groups.update(other_groups)
                        changed = True

            # Create merged group from cluster
            if cluster_files:
                merged_group = self._create_merged_group(
                    cluster_files, cluster_groups, matcher_results, weights
                )
                merged_groups.append(merged_group)
                processed_files.update(cluster_files)

        return merged_groups

    def _create_merged_group(
        self,
        cluster_files: set[str],
        cluster_groups: set[tuple[str, Group]],
        _matcher_results: dict[str, list[Group]],
        weights: dict[str, float],
    ) -> Group:
        """Create a single group from overlapping groups."""
        # Collect all files from overlapping groups
        all_files = []
        for _matcher_name, group in cluster_groups:
            for file in group.files:
                if file.file_path.name in cluster_files:
                    all_files.append(file)

        # Remove duplicates while preserving order
        seen_files = set()
        unique_files = []
        for file in all_files:
            if file.file_path.name not in seen_files:
                unique_files.append(file)
                seen_files.add(file.file_path.name)

        # Select best title using weighted scoring
        title_scores = {}
        for matcher_name, group in cluster_groups:
            weight = weights.get(matcher_name, 0.0)
            if group.title not in title_scores:
                title_scores[group.title] = 0.0
            title_scores[group.title] += weight

        best_title = max(title_scores.keys(), key=lambda t: title_scores[t])

        return Group(title=best_title, files=unique_files)

    def _generate_merge_evidence(
        self,
        group: Group,
        matcher_results: dict[str, list[Group]],
        weights: dict[str, float],
    ) -> GroupingEvidence:
        """Generate evidence showing contribution from each matcher."""
        match_scores = {}
        contributing_matchers = []

        # Calculate contribution from each matcher
        for matcher_name, groups in matcher_results.items():
            weight = weights.get(matcher_name, 0.0)
            for matcher_group in groups:
                # Check if this group contributed files to the merged group
                group_files = {f.file_path.name for f in group.files}
                matcher_files = {f.file_path.name for f in matcher_group.files}

                if group_files.intersection(matcher_files):
                    match_scores[matcher_name] = weight
                    contributing_matchers.append(matcher_name)
                    break

        # Calculate overall confidence
        confidence = (
            sum(match_scores.values()) / len(contributing_matchers)
            if contributing_matchers
            else 0.0
        )

        # Generate explanation
        confidence_pct = self._format_confidence_percentage(confidence)
        if len(contributing_matchers) == 1:
            explanation = (
                f"Grouped by {contributing_matchers[0]} similarity ({confidence_pct}%)"
            )
        else:
            matcher_list = ", ".join(contributing_matchers)
            explanation = (
                f"Grouped by multiple matchers ({matcher_list}) - "
                f"{confidence_pct}% confidence"
            )

        return self._create_evidence(
            match_scores=match_scores,
            contributing_matchers=contributing_matchers,
            explanation=explanation,
            confidence=confidence,
        )


class BestMatcherStrategy(GroupingStrategy):
    """Strategy that selects results from the highest-weighted matcher only.

    This is the current implementation in GroupingEngine.
    It's simpler but doesn't leverage multiple matchers effectively.
    """

    def combine_results(
        self,
        matcher_results: dict[str, list[Group]],
        weights: dict[str, float],
    ) -> list[Group]:
        """Select results from highest-weighted matcher."""
        if not matcher_results:
            return []

        # Find highest-weighted matcher
        best_matcher = max(
            matcher_results.keys(),
            key=lambda name: weights.get(name, 0.0),
        )

        best_groups = matcher_results[best_matcher]
        best_weight = weights.get(best_matcher, 0.0)

        # Generate evidence for each group
        result_groups = []
        confidence_pct = self._format_confidence_percentage(best_weight)
        for group in best_groups:
            explanation = f"Grouped by {best_matcher} similarity ({confidence_pct}%)"
            evidence = self._create_evidence(
                match_scores={best_matcher: best_weight},
                contributing_matchers=[best_matcher],
                explanation=explanation,
                confidence=best_weight,
            )

            final_group = Group(
                title=group.title,
                files=group.files,
                evidence=evidence,
            )
            result_groups.append(final_group)

        logger.info(
            "BestMatcherStrategy selected %d groups from matcher '%s'",
            len(result_groups),
            best_matcher,
        )

        return result_groups


class ConsensusStrategy(GroupingStrategy):
    """Strategy that requires consensus from multiple matchers.

    Only creates groups when multiple matchers agree on the grouping.
    More conservative but higher confidence.
    """

    def __init__(self, min_consensus: int = 2):
        """Initialize consensus strategy.

        Args:
            min_consensus: Minimum number of matchers that must agree
        """
        self.min_consensus = min_consensus

    def combine_results(
        self,
        matcher_results: dict[str, list[Group]],
        weights: dict[str, float],
    ) -> list[Group]:
        """Combine results requiring consensus from multiple matchers."""
        if not matcher_results:
            return []

        # Find groups that appear in multiple matchers
        consensus_groups = self._find_consensus_groups(matcher_results, weights)

        # Generate evidence
        result_groups = []
        for group in consensus_groups:
            evidence = self._generate_consensus_evidence(
                group, matcher_results, weights
            )
            final_group = Group(
                title=group.title,
                files=group.files,
                evidence=evidence,
            )
            result_groups.append(final_group)

        logger.info(
            "ConsensusStrategy produced %d consensus groups",
            len(result_groups),
        )

        return result_groups

    def _find_consensus_groups(
        self,
        matcher_results: dict[str, list[Group]],
        weights: dict[str, float],
    ) -> list[Group]:
        """Find groups that have consensus from multiple matchers."""
        # Count how many matchers agree on each file grouping
        file_group_counts: dict[frozenset[str], list[str]] = {}

        for matcher_name, groups in matcher_results.items():
            for group in groups:
                file_set = frozenset(f.file_path.name for f in group.files)
                if file_set not in file_group_counts:
                    file_group_counts[file_set] = []
                file_group_counts[file_set].append(matcher_name)

        # Find groups with sufficient consensus
        consensus_groups = []
        for file_set, matchers in file_group_counts.items():
            if len(matchers) >= self.min_consensus:
                # Reconstruct group from file set
                all_files = []
                for matcher_name, groups in matcher_results.items():
                    if matcher_name in matchers:
                        for group in groups:
                            group_file_set = frozenset(
                                f.file_path.name for f in group.files
                            )
                            if group_file_set == file_set:
                                all_files = group.files
                                break
                        break

                if all_files:
                    # Use title from highest-weighted matcher
                    best_matcher = max(matchers, key=lambda m: weights.get(m, 0.0))
                    best_title = None
                    for group in matcher_results[best_matcher]:
                        group_file_set = frozenset(
                            f.file_path.name for f in group.files
                        )
                        if group_file_set == file_set:
                            best_title = group.title
                            break

                    if best_title:
                        consensus_groups.append(
                            Group(title=best_title, files=all_files)
                        )

        return consensus_groups

    def _generate_consensus_evidence(
        self,
        group: Group,
        matcher_results: dict[str, list[Group]],
        weights: dict[str, float],
    ) -> GroupingEvidence:
        """Generate evidence for consensus-based grouping."""
        # Find which matchers contributed to this group
        contributing_matchers = []
        match_scores = {}

        group_file_set = frozenset(f.file_path.name for f in group.files)

        for matcher_name, groups in matcher_results.items():
            weight = weights.get(matcher_name, 0.0)
            for matcher_group in groups:
                matcher_file_set = frozenset(
                    f.file_path.name for f in matcher_group.files
                )
                if matcher_file_set == group_file_set:
                    contributing_matchers.append(matcher_name)
                    match_scores[matcher_name] = weight
                    break

        # Calculate confidence based on consensus
        consensus_ratio = len(contributing_matchers) / len(matcher_results)
        confidence = sum(match_scores.values()) * consensus_ratio

        confidence_pct = self._format_confidence_percentage(confidence)
        explanation = (
            f"Consensus from {len(contributing_matchers)} matcher(s) - "
            f"{confidence_pct}% confidence"
        )

        return self._create_evidence(
            match_scores=match_scores,
            contributing_matchers=contributing_matchers,
            explanation=explanation,
            confidence=confidence,
        )


__all__ = [
    "BestMatcherStrategy",
    "ConsensusStrategy",
    "GroupingStrategy",
    "WeightedMergeStrategy",
]
