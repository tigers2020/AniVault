"""Title-based similarity matcher for file grouping.

This module implements title-based grouping using fuzzy string matching.
Files with similar titles are grouped together based on configurable threshold.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from rapidfuzz import fuzz

if TYPE_CHECKING:
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

        # Step 2: Group files by similar titles
        groups_dict: dict[str, list[ScannedFile]] = {}
        title_to_group: dict[str, str] = {}  # Map title -> group name

        for file, title in file_titles:
            # Check if title is similar to any existing group
            matched_group = None
            for group_name, group_title in title_to_group.items():
                similarity = self._calculate_similarity(title, group_title)
                if similarity >= self.threshold:
                    matched_group = group_name
                    break

            if matched_group:
                # Add to existing group
                groups_dict[matched_group].append(file)

                # Update group name if this title is better quality
                better_title = self.quality_evaluator.select_better_title(
                    matched_group,
                    title,
                )
                if better_title != matched_group:
                    # Replace group name with better title
                    groups_dict[better_title] = groups_dict.pop(matched_group)
                    # Update mapping
                    for t, g in list(title_to_group.items()):
                        if g == matched_group:
                            title_to_group[t] = better_title
                    matched_group = better_title
            else:
                # Create new group
                groups_dict[title] = [file]
                title_to_group[title] = title

        # Step 3: Convert to Group objects
        result = [
            Group(title=group_name, files=group_files)
            for group_name, group_files in groups_dict.items()
        ]

        logger.info(
            "Title matcher grouped %d files into %d groups",
            len(files),
            len(result),
        )

        return result


__all__ = ["TitleSimilarityMatcher"]
