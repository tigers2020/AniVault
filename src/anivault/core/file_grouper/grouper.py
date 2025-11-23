"""File grouping module for AniVault.

This module provides functionality to group similar anime files based on
filename similarity and common patterns, enabling batch processing of
related files.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path


from anivault.core.file_grouper.duplicate_resolver import DuplicateResolver
from anivault.core.file_grouper.grouping_engine import GroupingEngine
from anivault.core.file_grouper.matchers.hash_matcher import HashSimilarityMatcher
from anivault.core.file_grouper.matchers.season_matcher import SeasonEpisodeMatcher
from anivault.core.file_grouper.matchers.title_matcher import TitleSimilarityMatcher
from anivault.core.file_grouper.models import Group
from anivault.core.models import ScannedFile
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.shared.constants import BusinessRules
from anivault.shared.constants.core import SimilarityConfig
from anivault.shared.constants.filename_patterns import (
    ADDITIONAL_CLEANUP_PATTERNS,
    AGGRESSIVE_CLEANUP_PATTERNS,
    ALL_CLEANING_PATTERNS,
    TECHNICAL_PATTERNS,
    GroupNaming,
    TitlePatterns,
    TitleQualityScores,
    TitleSelectionThresholds,
)
from anivault.shared.errors import (
    AniVaultError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error

# Type aliases
DuplicateResolverType = DuplicateResolver
GroupingEngineType = GroupingEngine

logger = logging.getLogger(__name__)


class TitleExtractor:
    """제목 추출 및 정제 - 단일 책임: 파일명에서 제목 추출."""

    def __init__(self) -> None:
        """Initialize the title extractor."""
        self.parser = AnitopyParser()

    def extract_base_title(self, filename: str) -> str:
        """Extract base title from filename."""
        try:
            name_without_ext = Path(filename).stem
            patterns_to_remove = ALL_CLEANING_PATTERNS
            cleaned = name_without_ext
            for pattern in patterns_to_remove:
                cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

            # Additional cleanup for remaining patterns
            for pattern in ADDITIONAL_CLEANUP_PATTERNS:
                cleaned = re.sub(pattern, "", cleaned)

            # Aggressive cleanup for stubborn patterns
            for pattern in AGGRESSIVE_CLEANUP_PATTERNS:
                cleaned = re.sub(pattern, "", cleaned)

            # Split on technical info patterns and take first part
            clean_part = re.split(TitlePatterns.TECHNICAL_SPLIT_PATTERN, cleaned)[0]

            # Final cleanup
            clean_part = re.sub(r"^\s*[-_]\s*", "", clean_part)
            clean_part = re.sub(r"\s*[-_]\s*$", "", clean_part)
            clean_part = re.sub(r"\s+", " ", clean_part).strip()

            return clean_part if clean_part else "unknown"

        except (ValueError, TypeError, AttributeError) as e:
            logger.warning("Failed to extract title from %s: %s", filename, e)
            return "unknown"

    def extract_title_with_parser(self, filename: str) -> str:
        """Extract title using anitopy parser."""
        try:
            parsed = self.parser.parse(filename)
            # parser.parse() returns ParsingResult (dataclass) in production,
            # but tests mock it as dict for backward compatibility
            if isinstance(parsed, dict):
                title: str = parsed.get("anime_title", "")
            else:
                title = parsed.title if parsed.title else ""
            if title:
                return title.strip()
            return self.extract_base_title(filename)
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug("Parser failed for %s, using fallback: %s", filename, e)
            return self.extract_base_title(filename)


class TitleQualityEvaluator:
    """제목 품질 평가 - 단일 책임: 제목 품질 점수 계산."""

    def __init__(self) -> None:
        """Initialize the title quality evaluator."""

    def score_title_quality(self, title: str) -> int:
        """Calculate quality score for a title."""
        if not title or title == "unknown":
            return 0

        score = 0
        length = len(title)

        # Length factor
        max_length_threshold = 100

        if (
            TitleQualityScores.GOOD_LENGTH_MIN
            <= length
            <= TitleQualityScores.GOOD_LENGTH_MAX
        ):
            score += TitleQualityScores.GOOD_LENGTH_BONUS
        elif (
            length < TitleQualityScores.GOOD_LENGTH_MIN or length > max_length_threshold
        ):
            score += TitleQualityScores.BAD_LENGTH_PENALTY

        # Technical pattern penalties
        for pattern in TECHNICAL_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                score += TitleQualityScores.TECHNICAL_PATTERN_PENALTY

        # Special character penalty
        special_chars = len(
            re.findall(r"[^a-zA-Z0-9\s\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]", title),
        )
        if special_chars > TitleQualityScores.MAX_SPECIAL_CHARS:
            score += TitleQualityScores.SPECIAL_CHAR_PENALTY

        # Quality bonuses
        if re.search(TitlePatterns.TITLE_CASE_PATTERN, title):  # Title Case
            score += TitleQualityScores.TITLE_CASE_BONUS

        if re.search(TitlePatterns.JAPANESE_CHAR_PATTERN, title):  # Japanese chars
            score += TitleQualityScores.JAPANESE_CHAR_BONUS

        return score

    def is_cleaner_title(self, title1: str, title2: str) -> bool:
        """Check if title1 is cleaner than title2."""
        score1 = self.score_title_quality(title1)
        score2 = self.score_title_quality(title2)
        return score1 > score2

    def contains_technical_info(self, title: str) -> bool:
        """Check if title contains technical information."""
        for pattern in TECHNICAL_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                return True
        return False

    def select_better_title(self, title1: str, title2: str) -> str:
        """Select the better title between two options."""
        if not title1 or title1 == "unknown":
            return title2 or "unknown"
        if not title2 or title2 == "unknown":
            return title1

        score1 = self.score_title_quality(title1)
        score2 = self.score_title_quality(title2)

        # If one is significantly better, choose it
        if abs(score1 - score2) >= TitleQualityScores.SIGNIFICANT_QUALITY_DIFF:
            return title1 if score1 > score2 else title2

        # If scores are close, prefer shorter title (but not too short)
        if (
            len(title1)
            < len(title2) * TitleSelectionThresholds.LENGTH_REDUCTION_THRESHOLD
        ):
            return title2
        if (
            len(title2)
            < len(title1) * TitleSelectionThresholds.LENGTH_REDUCTION_THRESHOLD
        ):
            return title1

        # Default to first title
        return title1


class GroupNameManager:
    """그룹명 관리 - 단일 책임: 그룹명 생성 및 병합."""

    def __init__(self) -> None:
        """Initialize the group name manager."""

    def ensure_unique_group_name(
        self,
        group_name: str,
        existing_groups: dict[str, list[ScannedFile]],
    ) -> str:
        """Ensure group name is unique by adding suffix if needed."""
        if group_name not in existing_groups:
            return group_name

        counter = 1
        while (
            f"{group_name}{GroupNaming.DUPLICATE_SUFFIX_FORMAT.format(counter)}"
            in existing_groups
        ):
            counter += 1
        return f"{group_name}{GroupNaming.DUPLICATE_SUFFIX_FORMAT.format(counter)}"

    def merge_similar_group_names(
        self,
        grouped_files: dict[str, list[ScannedFile]],
    ) -> dict[str, list[ScannedFile]]:
        """Merge groups with similar names using O(n) algorithm.

        Uses defaultdict to group by normalized base name in a single pass,
        achieving O(n) time complexity instead of O(n²).
        """
        if len(grouped_files) <= 1:
            return grouped_files

        # Group by normalized base name using defaultdict for O(n) complexity
        numbered_pattern = re.compile(GroupNaming.NUMBERED_SUFFIX_PATTERN)
        grouped_by_base: defaultdict[str, list[tuple[str, list[ScannedFile]]]] = (
            defaultdict(list)
        )

        # Single pass: normalize each group name and group by base name
        for group_name, files in grouped_files.items():
            match = numbered_pattern.match(group_name)
            base_name = match.group(1) if match else group_name
            grouped_by_base[base_name].append((group_name, files))

        # Merge groups with the same base name
        merged: dict[str, list[ScannedFile]] = {}
        for base_name, group_list in grouped_by_base.items():
            if len(group_list) > 1:
                # Multiple groups with same base name: merge them
                merged_files: list[ScannedFile] = []
                for _, files in group_list:
                    merged_files.extend(files)

                final_name = self.ensure_unique_group_name(base_name, merged)
                merged[final_name] = merged_files
            else:
                # Single group: keep original name
                original_name, files = group_list[0]
                merged[original_name] = files

        return merged


class FileGrouper:
    """Facade for file grouping operations.

    This class provides a simple interface for grouping files, delegating
    the actual work to GroupingEngine, DuplicateResolver, and GroupNameManager.
    It maintains backward compatibility with existing code while using the
    new Strategy pattern architecture internally.

    Attributes:
        engine: GroupingEngine instance for orchestrating matchers.
        resolver: DuplicateResolver instance for selecting best files.
        name_manager: GroupNameManager instance for group name normalization.
        similarity_threshold: Threshold for similarity-based grouping (legacy).
    """

    def __init__(
        self,
        engine: GroupingEngineType | None = None,
        resolver: DuplicateResolverType | None = None,
        name_manager: GroupNameManager | None = None,
        similarity_threshold: float = BusinessRules.FUZZY_MATCH_THRESHOLD,
    ) -> None:
        """Initialize the file grouper facade.

        Args:
            engine: Optional GroupingEngine instance. If None, creates default.
            resolver: Optional DuplicateResolver instance. If None, creates default.
            name_manager: Optional GroupNameManager instance. If None, creates default.
            similarity_threshold: Minimum similarity score (for backward compatibility).

        Example:
            >>> # Default usage (backward compatible)
            >>> grouper = FileGrouper()
            >>> groups = grouper.group_files(scanned_files)
            >>>
            >>> # With dependency injection
            >>> custom_engine = GroupingEngine(matchers=[...], weights={...})
            >>> grouper = FileGrouper(engine=custom_engine)
        """
        # Store threshold for backward compatibility
        self.similarity_threshold = similarity_threshold

        # Create default instances if not provided
        self.engine = (
            engine
            if engine is not None
            else self._create_default_engine(similarity_threshold)
        )
        self.resolver = (
            resolver if resolver is not None else self._create_default_resolver()
        )
        self.name_manager = (
            name_manager if name_manager is not None else GroupNameManager()
        )

        logger.info(
            "FileGrouper initialized (Facade pattern) with similarity_threshold=%.2f",
            similarity_threshold,
        )

    def _create_default_engine(self, similarity_threshold: float) -> GroupingEngineType:
        """Create default GroupingEngine with matchers.

        Args:
            similarity_threshold: Minimum similarity score for matching

        Returns:
            Configured GroupingEngine instance
        """
        # Create helper instances for matchers
        title_extractor = TitleExtractor()
        quality_evaluator = TitleQualityEvaluator()

        # Create default matchers with proper dependencies
        title_matcher = TitleSimilarityMatcher(
            title_extractor=title_extractor,
            quality_evaluator=quality_evaluator,
            threshold=similarity_threshold,
        )
        hash_matcher = HashSimilarityMatcher(title_extractor=title_extractor)
        season_matcher = SeasonEpisodeMatcher()

        # Create engine with default weights
        return GroupingEngine(
            matchers=[title_matcher, hash_matcher, season_matcher],
        )

    def _create_default_resolver(self) -> DuplicateResolverType:
        """Create default DuplicateResolver.

        Returns:
            DuplicateResolver instance
        """
        return DuplicateResolver()

    def _reconstruct_groups_with_evidence(
        self,
        normalized_dict: dict[str, list[ScannedFile]],
        original_groups: list[Group],
    ) -> list[Group]:
        """Reconstruct Group objects from normalized dict, preserving evidence.

        Args:
            normalized_dict: Dictionary mapping group titles to file lists
            original_groups: Original groups before normalization

        Returns:
            List of Group objects with evidence preserved where possible
        """
        final_groups = []
        for title, files in normalized_dict.items():
            original_group = self._find_matching_original_group(
                title, files, original_groups
            )
            if original_group and original_group.evidence:
                final_groups.append(
                    Group(title=title, files=files, evidence=original_group.evidence)
                )
            else:
                final_groups.append(Group(title=title, files=files))
        return final_groups

    def _find_matching_original_group(
        self,
        title: str,
        files: list[ScannedFile],
        original_groups: list[Group],
    ) -> Group | None:
        """Find the original group that matches the normalized title and files.

        Args:
            title: Normalized group title
            files: List of files in the normalized group
            original_groups: List of original groups to search

        Returns:
            Matching original group or None if not found
        """
        # Note: Cannot use set() as ScannedFile is not hashable
        for group in original_groups:
            if group.title == title:
                return group

            # Check if files match (same count and same file paths)
            if len(group.files) == len(files):
                file_paths = {f.file_path for f in files}
                group_file_paths = {f.file_path for f in group.files}
                if file_paths == group_file_paths:
                    return group

        return None

    def group_files(
        self,
        scanned_files: list[ScannedFile],
    ) -> list[Group]:
        """Group scanned files by similarity (Facade delegation).

        This method delegates the actual grouping work to the GroupingEngine,
        then applies duplicate resolution and group name normalization.

        Args:
            scanned_files: List of scanned files to group

        Returns:
            List of Group objects with similar files grouped together

        Raises:
            InfrastructureError: If grouping fails

        Example:
            >>> grouper = FileGrouper()
            >>> groups = grouper.group_files(scanned_files)
            >>> for group in groups:
            ...     print(f"{group.title}: {len(group.files)} files")
        """
        context = ErrorContext(
            operation="group_files",
            additional_data={"file_count": len(scanned_files)},
        )

        try:
            if not scanned_files:
                return []

            # Step 1: Delegate to GroupingEngine (strategy pattern)
            logger.debug("Delegating to GroupingEngine for grouping")
            groups = self.engine.group_files(scanned_files)

            # Step 2: Resolve duplicates within each group
            logger.debug("Resolving duplicates in %d group(s)", len(groups))
            for group in groups:
                if group.has_duplicates():
                    # Keep only the best file
                    best_file = self.resolver.resolve_duplicates(group.files)
                    group.files = [best_file]
                    logger.debug(
                        "Group '%s': resolved %d duplicates to 1 file",
                        group.title,
                        len(group.files),
                    )

            # Step 3: Normalize group names (merge similar names)
            logger.debug("Normalizing group names")
            groups_dict = {group.title: group.files for group in groups}
            normalized_dict = self.name_manager.merge_similar_group_names(groups_dict)

            # Step 4: Convert back to list[Group] (preserve evidence if exists)
            final_groups = self._reconstruct_groups_with_evidence(
                normalized_dict, groups
            )

            logger.info(
                "Grouped %d files into %d groups (via Facade)",
                len(scanned_files),
                len(final_groups),
            )

            return final_groups

        except Exception as e:
            # Preserve existing error handling behavior
            if isinstance(e, AniVaultError):
                log_operation_error(
                    logger=logger,
                    operation="group_files",
                    error=e,
                    additional_context=context.additional_data if context else None,
                )
            else:
                error = InfrastructureError(
                    code=ErrorCode.FILE_GROUPING_FAILED,
                    message=f"Failed to group files: {e!s}",
                    context=context,
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    operation="group_files",
                    error=error,
                    additional_context=context.additional_data if context else None,
                )
            raise InfrastructureError(
                code=ErrorCode.FILE_GROUPING_FAILED,
                message=f"Failed to group files: {e!s}",
                context=context,
                original_error=e,
            ) from e


def group_similar_files(
    scanned_files: list[ScannedFile],
    similarity_threshold: float = SimilarityConfig.DEFAULT_SIMILARITY_THRESHOLD,
) -> list[Group]:
    """Convenience function to group similar files.

    Args:
        scanned_files: List of scanned files to group
        similarity_threshold: Minimum similarity score for grouping

    Returns:
        List of Group objects with similar files grouped together
    """
    grouper = FileGrouper(similarity_threshold=similarity_threshold)
    return grouper.group_files(scanned_files)
