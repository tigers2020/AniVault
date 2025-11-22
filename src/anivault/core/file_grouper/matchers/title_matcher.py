"""Title-based similarity matcher for file grouping.

This module implements title-based grouping using fuzzy string matching.
Files with similar titles are grouped together based on configurable threshold.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from rapidfuzz import fuzz

from anivault.core.data_structures.linked_hash_table import LinkedHashTable

if TYPE_CHECKING:
    from anivault.core.file_grouper.models import Group
    from anivault.core.models import ScannedFile
else:
    from anivault.core.file_grouper.models import Group
    from anivault.core.models import ScannedFile

logger = logging.getLogger(__name__)


class TitleSimilarityMatcher:
    """Matcher that groups files by title similarity using fuzzy matching.

    This matcher uses rapidfuzz for calculating string similarity between titles.
    Files with titles above the similarity threshold are grouped together.

    Attributes:
        component_name: Identifier for this matcher ("title").
        threshold: Minimum similarity score (0.0-1.0) for grouping.
        title_extractor: Extracts base titles from filenames.
        quality_evaluator: Selects best title as group name.

    Example:
        >>> matcher = TitleSimilarityMatcher(threshold=0.85)
        >>> groups = matcher.match(scanned_files)
        >>> groups
        {"Attack on Titan": [<file1>, <file2>], ...}
    """

    def __init__(
        self,
        title_extractor: Any,
        quality_evaluator: Any,
        threshold: float = 0.85,
    ) -> None:
        """Initialize title similarity matcher.

        Args:
            title_extractor: Extractor for parsing titles from filenames.
            quality_evaluator: Evaluator for selecting best title variant.
            threshold: Minimum similarity score (0.0-1.0) for grouping.
                      Default is 0.85 (85% similarity).

        Raises:
            ValueError: If threshold is not in range [0.0, 1.0].

        Example:
            >>> from anivault.core.file_grouper import TitleExtractor, TitleQualityEvaluator
            >>> extractor = TitleExtractor()
            >>> evaluator = TitleQualityEvaluator()
            >>> matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=0.9)
        """
        if not 0.0 <= threshold <= 1.0:
            msg = f"Threshold must be between 0.0 and 1.0, got {threshold}"
            raise ValueError(msg)

        self.component_name = "title"
        self.threshold = threshold
        self.title_extractor = title_extractor
        self.quality_evaluator = quality_evaluator

    def _extract_title_from_file(self, file: ScannedFile) -> str | None:
        """Extract title from a scanned file.

        Tries to use parsed metadata title first, falls back to filename extraction.

        Args:
            file: ScannedFile to extract title from.

        Returns:
            Extracted title string, or None if extraction failed.

        Example:
            >>> file = ScannedFile(file_path=Path("attack_01.mkv"), metadata=...)
            >>> matcher._extract_title_from_file(file)
            'Attack on Titan'
        """
        # Try to get parsed title first (more accurate)
        base_title = None
        if (
            hasattr(file, "metadata")
            and file.metadata
            and hasattr(file.metadata, "title")
        ):
            parsed_title = file.metadata.title
            if parsed_title and parsed_title != file.file_path.name:
                base_title = parsed_title

        # Fallback to extract_base_title if parsing failed
        if not base_title:
            base_title = self.title_extractor.extract_base_title(
                file.file_path.name,
            )

        return base_title

    def _generate_blocking_key(self, title: str, k: int = 4) -> str:
        """Generate a blocking key from a title for bucket-based grouping.

        Extracts alphanumeric and Korean characters, converts to lowercase,
        and returns the first k characters. This creates buckets for similar titles
        to reduce comparison complexity from O(n²) to O(bucket_size²).

        Args:
            title: Title string to generate key from.
            k: Number of characters to use for blocking key. Default is 4.

        Returns:
            Blocking key string (first k characters of cleaned title).

        Example:
            >>> matcher._generate_blocking_key("Attack on Titan", k=4)
            'atta'
            >>> matcher._generate_blocking_key("attack-on-titan", k=4)
            'atta'
            >>> matcher._generate_blocking_key("진격의 거인 1기", k=4)
            '진격의거'
        """
        # Extract only alphanumeric and Korean characters
        # Pattern matches: a-z, A-Z, 0-9, and Korean characters (가-힣)
        cleaned = re.sub(r"[^a-zA-Z0-9가-힣]", "", title)
        # Convert to lowercase
        cleaned = cleaned.lower()
        # Return first k characters, or entire string if shorter
        return cleaned[:k] if cleaned else ""

    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity score between two titles.

        Uses rapidfuzz.fuzz.ratio() for fuzzy string matching.

        Args:
            title1: First title to compare.
            title2: Second title to compare.

        Returns:
            Similarity score between 0.0 (completely different) and 1.0 (identical).

        Example:
            >>> matcher._calculate_similarity("Attack on Titan", "Attack on Titan")
            1.0
            >>> matcher._calculate_similarity("Attack on Titan", "Shingeki no Kyojin")
            0.42
        """
        # Use rapidfuzz for similarity calculation (returns 0-100)
        score = fuzz.ratio(title1.lower(), title2.lower())
        # Normalize to 0.0-1.0 range
        return score / 100.0

    def match(self, files: list[ScannedFile]) -> list[Group]:
        """Group files by title similarity.

        Files with similar titles (above threshold) are grouped together.
        The best title variant is selected as the group name using quality evaluation.

        Args:
            files: List of ScannedFile objects to group.

        Returns:
            List of Group objects with similar files grouped together.
            Returns empty list if input is empty or no groupings found.

        Example:
            >>> files = [ScannedFile(...), ScannedFile(...)]
            >>> groups = matcher.match(files)
            >>> groups[0].title
            'Attack on Titan'
            >>> len(groups[0].files)
            2
        """
        if not files:
            return []

        # Import here to avoid circular dependency at runtime
        from anivault.core.file_grouper.models import Group

        # Step 1: Extract titles from all files
        file_titles: list[tuple[ScannedFile, str]] = []
        for file in files:
            title = self._extract_title_from_file(file)
            if title:
                file_titles.append((file, title))
            else:
                logger.warning(
                    "Could not extract title from file: %s",
                    file.file_path.name,
                )

        if not file_titles:
            return []

        # Step 2: Group files into buckets using blocking keys
        buckets: dict[str, list[tuple[ScannedFile, str]]] = {}
        for file, title in file_titles:
            blocking_key = self._generate_blocking_key(title, k=4)
            if blocking_key not in buckets:
                buckets[blocking_key] = []
            buckets[blocking_key].append((file, title))

        # Monitor bucket sizes for imbalance detection
        bucket_size_threshold = 100  # Warn if bucket exceeds this size
        for key, bucket_files in buckets.items():
            if len(bucket_files) > bucket_size_threshold:
                logger.warning(
                    "Large bucket detected for key '%s': %d files. "
                    "Blocking efficiency may be reduced.",
                    key,
                    len(bucket_files),
                )

        # Step 3: Process each bucket independently using LinkedHashTable
        all_groups_table = LinkedHashTable[str, list[ScannedFile]](
            initial_capacity=max(len(file_titles) * 2, 64),
            load_factor=0.75,
        )

        for blocking_key, bucket_files in buckets.items():
            # Create LinkedHashTable for this bucket
            bucket_groups_table = LinkedHashTable[str, list[ScannedFile]](
                initial_capacity=max(len(bucket_files) * 2, 64),
                load_factor=0.75,
            )
            bucket_title_to_group = LinkedHashTable[str, str](
                initial_capacity=max(len(bucket_files) * 2, 64),
                load_factor=0.75,
            )

            # Process files within this bucket
            for file, title in bucket_files:
                # Check if title is similar to any existing group in this bucket
                matched_group = None
                for group_name, group_title in bucket_title_to_group:
                    similarity = self._calculate_similarity(title, group_title)
                    if similarity >= self.threshold:
                        matched_group = group_name
                        break

                if matched_group:
                    # Add to existing group
                    existing_files = bucket_groups_table.get(matched_group)
                    if existing_files:
                        existing_files.append(file)
                    else:
                        bucket_groups_table.put(matched_group, [file])

                    # Update group name if this title is better quality
                    better_title = self.quality_evaluator.select_better_title(
                        matched_group,
                        title,
                    )
                    if better_title != matched_group:
                        # Replace group name with better title
                        old_files = bucket_groups_table.remove(matched_group)
                        if old_files:
                            bucket_groups_table.put(better_title, old_files)
                        # Update mapping
                        for t, g in bucket_title_to_group:
                            if g == matched_group:
                                bucket_title_to_group.put(t, better_title)
                        matched_group = better_title
                else:
                    # Create new group
                    bucket_groups_table.put(title, [file])
                    bucket_title_to_group.put(title, title)

            # Merge bucket groups into all_groups_table
            for group_name, group_files in bucket_groups_table:
                # Check if group name already exists in all_groups_table
                existing_all_files = all_groups_table.get(group_name)
                if existing_all_files:
                    # Merge files
                    existing_all_files.extend(group_files)
                else:
                    # Add new group
                    all_groups_table.put(group_name, group_files.copy())

        # Step 4: Convert to Group objects
        result = [
            Group(title=group_name, files=group_files)
            for group_name, group_files in all_groups_table
        ]

        logger.info(
            "Title matcher grouped %d files into %d groups",
            len(files),
            len(result),
        )

        return result

    def refine_group(self, group: Group) -> Group | None:
        """Refine a group by subdividing it based on title similarity.

        This method takes an existing group (typically from Hash matcher) and
        subdivides it into smaller groups based on pairwise title similarity.
        Files with similar titles (above threshold) are grouped together.

        If the group cannot be subdivided (all files are similar or only one file),
        returns None to indicate no refinement occurred.

        Args:
            group: Group object containing files to refine.

        Returns:
            Refined Group object if subdivision occurred (first subgroup),
            or None if no refinement was needed.

        Note:
            This method is designed to work with the Hash-first pipeline where
            Hash matcher creates initial groups, and Title matcher refines them.
            If multiple subgroups are created, only the first one is returned.
            The grouping engine handles multiple subgroups via the match() fallback.

        Example:
            >>> hash_group = Group(title="Anime", files=[file1, file2, file3])
            >>> refined = matcher.refine_group(hash_group)
            >>> if refined:
            ...     len(refined.files)  # May be smaller than original
        """
        if not group.files:
            return None

        # If group has only one file, no refinement needed
        if len(group.files) == 1:
            return None

        # Use match() method to subdivide the group
        # This reuses existing logic for consistency
        subgroups = self.match(group.files)

        # If no subgroups created or only one subgroup, return None
        # (no refinement occurred - all files remain together)
        if not subgroups or len(subgroups) == 1:
            return None

        # If multiple subgroups created, return the first one
        # Note: The grouping engine's fallback logic will handle
        # multiple subgroups if needed via the match() method
        logger.debug(
            "Refined group '%s' (%d files) into %d subgroup(s), returning first",
            group.title,
            len(group.files),
            len(subgroups),
        )
        return subgroups[0]


__all__ = ["TitleSimilarityMatcher"]
