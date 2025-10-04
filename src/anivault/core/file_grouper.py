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

from anivault.core.models import ScannedFile
from anivault.shared.constants import BusinessRules
from anivault.shared.constants.core import SimilarityConfig
from anivault.shared.errors import (
    AniVaultError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error

logger = logging.getLogger(__name__)


class FileGrouper:
    """Groups similar anime files based on filename patterns and similarity."""

    def __init__(
        self,
        similarity_threshold: float = BusinessRules.FUZZY_MATCH_THRESHOLD,
    ) -> None:
        """Initialize the file grouper.

        Args:
            similarity_threshold: Minimum similarity score for grouping (0.0 to 1.0)
        """
        self.similarity_threshold = similarity_threshold

    def group_files(
        self,
        scanned_files: list[ScannedFile],
    ) -> dict[str, list[ScannedFile]]:
        """Group scanned files by similarity.

        Args:
            scanned_files: List of scanned files to group

        Returns:
            Dictionary mapping group keys to lists of similar files

        Raises:
            InfrastructureError: If grouping fails
        """
        context = ErrorContext(
            operation="group_files",
            additional_data={"file_count": len(scanned_files)},
        )

        try:
            if not scanned_files:
                return {}

            # Extract base titles from filenames
            file_groups = defaultdict(list)

            for file in scanned_files:
                base_title = self._extract_base_title(file.file_path.name)
                if base_title:
                    file_groups[base_title].append(file)

            # Merge similar groups
            merged_groups = self._merge_similar_groups(file_groups)

            logger.info(
                "Grouped %d files into %d groups",
                len(scanned_files),
                len(merged_groups),
            )

            return merged_groups

        except Exception as e:
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

    def _extract_base_title(self, filename: str) -> str:
        """Extract base title from filename for grouping.

        Args:
            filename: Original filename

        Returns:
            Cleaned base title for grouping
        """
        # Remove file extension
        name_without_ext = Path(filename).stem

        # Remove common patterns that don't affect grouping
        patterns_to_remove = [
            # Resolution patterns
            r"\[(?:1080p|720p|480p|2160p|4K|HD|SD)\]",
            r"\((?:1080p|720p|480p|2160p|4K|HD|SD)\)",
            # Episode patterns
            r"\[(?:E\d+|Episode\s+\d+|Ep\s+\d+)\]",
            r"\((?:E\d+|Episode\s+\d+|Ep\s+\d+)\)",
            r"\s+\d+\s*",  # Episode numbers anywhere
            # Hash patterns
            r"\[[A-Fa-f0-9]{8,}\]",
            r"\([A-Fa-f0-9]{8,}\)",
            # File extensions
            r"\.(?:mkv|mp4|avi|mov|wmv|flv|webm|m4v|srt|smi|ass|vtt)$",
        ]

        cleaned = name_without_ext
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Clean up extra whitespace and separators
        cleaned = re.sub(r"[-\s]+", " ", cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def _merge_similar_groups(
        self,
        file_groups: dict[str, list[ScannedFile]],
    ) -> dict[str, list[ScannedFile]]:
        """Merge groups with similar base titles.

        Args:
            file_groups: Initial groups by base title

        Returns:
            Merged groups with similar titles combined
        """
        merged_groups = {}
        processed_groups = set()

        for base_title in file_groups:
            if base_title in processed_groups:
                continue

            # Find similar groups
            similar_groups = [base_title]
            for other_title in file_groups:
                if other_title != base_title and other_title not in processed_groups:
                    similarity = self._calculate_similarity(base_title, other_title)
                    if similarity >= self.similarity_threshold:
                        similar_groups.append(other_title)

            # Merge files from similar groups
            merged_files = []
            for title in similar_groups:
                merged_files.extend(file_groups[title])
                processed_groups.add(title)

            # Use the most common title as the group key
            group_key = self._select_best_group_key(similar_groups)
            merged_groups[group_key] = merged_files

        return merged_groups

    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles.

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Simple word-based similarity
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _select_best_group_key(self, titles: list[str]) -> str:
        """Select the best title to use as group key.

        Args:
            titles: List of similar titles

        Returns:
            Best title to use as group key
        """
        # Prefer titles with more words (more descriptive)
        return max(titles, key=lambda t: len(t.split()))


def group_similar_files(
    scanned_files: list[ScannedFile],
    similarity_threshold: float = SimilarityConfig.DEFAULT_SIMILARITY_THRESHOLD,
) -> dict[str, list[ScannedFile]]:
    """Convenience function to group similar files.

    Args:
        scanned_files: List of scanned files to group
        similarity_threshold: Minimum similarity score for grouping

    Returns:
        Dictionary mapping group keys to lists of similar files
    """
    grouper = FileGrouper(similarity_threshold=similarity_threshold)
    return grouper.group_files(scanned_files)
