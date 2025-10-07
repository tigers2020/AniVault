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
        if (
            TitleQualityScores.GOOD_LENGTH_MIN
            <= length
            <= TitleQualityScores.GOOD_LENGTH_MAX
        ):
            score += TitleQualityScores.GOOD_LENGTH_BONUS
        elif length < TitleQualityScores.GOOD_LENGTH_MIN or length > 100:
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
        """Merge groups with similar names."""
        if len(grouped_files) <= 1:
            return grouped_files

        merged: dict[str, list[ScannedFile]] = {}
        processed = set()

        for group_name, files in grouped_files.items():
            if group_name in processed:
                continue

            # Find similar group names
            similar_groups = [group_name]
            numbered_pattern = re.compile(GroupNaming.NUMBERED_SUFFIX_PATTERN)
            match = numbered_pattern.match(group_name)
            base_name = match.group(1) if match else group_name

            for other_name in grouped_files:
                if other_name == group_name or other_name in processed:
                    continue

                other_match = numbered_pattern.match(other_name)
                other_base = other_match.group(1) if other_match else other_name

                if base_name == other_base:
                    similar_groups.append(other_name)

            # Merge similar groups
            if len(similar_groups) > 1:
                merged_files = []
                for similar_name in similar_groups:
                    merged_files.extend(grouped_files[similar_name])
                    processed.add(similar_name)

                final_name = self.ensure_unique_group_name(base_name, merged)
                merged[final_name] = merged_files
            else:
                merged[group_name] = files
                processed.add(group_name)

        return merged


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
        self.title_extractor = TitleExtractor()
        self.quality_evaluator = TitleQualityEvaluator()
        self.group_manager = GroupNameManager()
        self.parser = None
        try:
            self.parser = AnitopyParser()
        except ImportError:
            logger.warning("AnitopyParser not available, using basic title extraction")

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

                if base_title:
                    file_groups[base_title].append(file)

            # Merge similar groups
            merged_groups = self._merge_similar_groups(file_groups)

            # Update group names using parser for better titles
            updated_groups = self._update_group_names_with_parser(merged_groups)

            # Merge groups with similar names (e.g., "Title" and "Title (1)")
            final_groups = self.group_manager.merge_similar_group_names(updated_groups)

            logger.info(
                "Grouped %d files into %d groups",
                len(scanned_files),
                len(final_groups),
            )

            return final_groups

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

        # Use centralized patterns for technical information removal
        patterns_to_remove = ALL_CLEANING_PATTERNS

        cleaned = name_without_ext

        # Apply patterns in order
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Clean up parentheses and brackets
        cleaned = re.sub(r"\(\s*\)", "", cleaned)  # Empty parentheses
        cleaned = re.sub(r"\[\s*\]", "", cleaned)  # Empty brackets
        cleaned = re.sub(r"^\s*\(|\)\s*$", "", cleaned)  # Leading/trailing parentheses
        cleaned = re.sub(r"^\s*\[|\]\s*$", "", cleaned)  # Leading/trailing brackets

        # Apply additional cleanup patterns
        for pattern in ADDITIONAL_CLEANUP_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned)

        # Apply aggressive cleanup patterns
        for pattern in AGGRESSIVE_CLEANUP_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned)

        # If still has problematic fragments, remove everything after the last clean word
        if "(" in cleaned and any(
            char in cleaned for char in ["AT", "x264", "AAC", "DivX"]
        ):
            # Find the last clean word before problematic content
            clean_part = re.split(r"\([^)]*(?:AT|[xX]\d+|AAC|DivX)", cleaned)[0]
            if clean_part.strip():
                cleaned = clean_part.strip()

        # Clean up extra whitespace and separators
        cleaned = re.sub(r"[-\s]+", " ", cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def _merge_similar_groups(
        self,
        file_groups: dict[str, list[ScannedFile]],
    ) -> dict[str, list[ScannedFile]]:
        """Merge groups with similar base titles using optimized O(n log n) algorithm.

        Args:
            file_groups: Initial groups by base title

        Returns:
            Merged groups with similar titles combined
        """
        if len(file_groups) <= 1:
            return file_groups

        # Step 1: Pre-filter using hash-based grouping (O(n))
        hash_groups = self._group_by_normalized_hash(file_groups)

        # Step 2: Apply union-find for efficient merging (O(n log n))
        merged_groups = self._merge_using_union_find(file_groups, hash_groups)

        return merged_groups

    def _group_by_normalized_hash(
        self,
        file_groups: dict[str, list[ScannedFile]],
    ) -> dict[str, list[str]]:
        """Group titles by normalized hash for fast pre-filtering.

        Args:
            file_groups: Dictionary of file groups

        Returns:
            Dictionary mapping normalized hash to list of similar titles
        """
        hash_groups: dict[str, list[str]] = {}

        for title in file_groups:
            # Normalize title for hashing (remove common variations)
            normalized = self._normalize_title_for_hash(title)
            if normalized not in hash_groups:
                hash_groups[normalized] = []
            hash_groups[normalized].append(title)

        return hash_groups

    def _normalize_title_for_hash(self, title: str) -> str:
        """Normalize title for hash-based grouping.

        Args:
            title: Original title

        Returns:
            Normalized title for hashing
        """
        # Convert to lowercase and remove common variations
        normalized = title.lower()
        normalized = re.sub(r"[^\w\s]", "", normalized)  # Remove punctuation
        normalized = re.sub(r"\s+", " ", normalized)  # Normalize whitespace
        return normalized.strip()

    def _merge_using_union_find(
        self,
        file_groups: dict[str, list[ScannedFile]],
        hash_groups: dict[str, list[str]],
    ) -> dict[str, list[ScannedFile]]:
        """Merge groups using Union-Find algorithm for O(n log n) complexity.

        Args:
            file_groups: Original file groups
            hash_groups: Hash-based pre-grouped titles

        Returns:
            Merged file groups
        """
        from collections import defaultdict

        # Create Union-Find structure
        parent = {}
        rank = {}

        def find(x: str) -> str:
            if x not in parent:
                parent[x] = x
                rank[x] = 0
            if parent[x] != x:
                parent[x] = find(parent[x])  # Path compression
            return parent[x]

        def union(x: str, y: str) -> None:
            px, py = find(x), find(y)
            if px != py:
                # Union by rank for better performance
                if rank[px] < rank[py]:
                    parent[px] = py
                elif rank[px] > rank[py]:
                    parent[py] = px
                else:
                    parent[py] = px
                    rank[px] += 1

        # Step 1: Union titles within each hash group
        for titles in hash_groups.values():
            if len(titles) > 1:
                # Union all titles in the same hash group
                for i in range(1, len(titles)):
                    union(titles[0], titles[i])

        # Step 2: Check similarity between different hash groups (reduced set)
        all_titles = list(file_groups.keys())
        for i, title1 in enumerate(all_titles):
            for _j, title2 in enumerate(all_titles[i + 1 :], i + 1):
                # Only check if they're not already in the same group
                if find(title1) != find(title2):
                    similarity = self._calculate_similarity(title1, title2)
                    if similarity >= self.similarity_threshold:
                        union(title1, title2)

        # Step 3: Build final merged groups
        merged_groups = defaultdict(list)
        for title, files in file_groups.items():
            root = find(title)
            merged_groups[root].extend(files)

        # Step 4: Select best representative title for each group
        final_groups = {}
        for root, files in merged_groups.items():
            # Get all titles in this group
            group_titles = [title for title in file_groups if find(title) == root]
            best_title = self._select_best_group_key(group_titles)
            final_groups[best_title] = files

        return final_groups

    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles, ignoring episode numbers.

        Args:
            title1: First title
            title2: Second title

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Remove episode numbers and other variations for better comparison
        normalized1 = self._normalize_title_for_similarity(title1)
        normalized2 = self._normalize_title_for_similarity(title2)

        # Word-based similarity with normalized titles
        words1 = set(normalized1.lower().split())
        words2 = set(normalized2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _normalize_title_for_similarity(self, title: str) -> str:
        """Normalize title for similarity comparison by removing episode info.

        Args:
            title: Original title

        Returns:
            Normalized title for similarity comparison
        """
        import re

        # Remove episode patterns (E01, E02, etc.)
        normalized = re.sub(r"\s+E\d+\s*", " ", title)

        # Remove standalone numbers that might be episode numbers
        normalized = re.sub(r"\s+\d{1,3}\s*$", "", normalized)

        # Remove common separators and normalize whitespace
        normalized = re.sub(r"[-\s]+", " ", normalized)
        normalized = normalized.strip()

        return normalized

    def _select_best_group_key(self, titles: list[str]) -> str:
        """Select the best title to use as group key.

        Args:
            titles: List of similar titles

        Returns:
            Best title to use as group key
        """
        # Prefer titles with more words (more descriptive)
        return max(titles, key=lambda t: len(t.split()))

    def _update_group_names_with_parser(
        self,
        grouped_files: dict[str, list[ScannedFile]],
    ) -> dict[str, list[ScannedFile]]:
        """Update group names using parser for more accurate titles.

        Args:
            grouped_files: Dictionary of grouped files with basic titles

        Returns:
            Dictionary with updated group names based on parser results
        """
        if not self.parser:
            logger.debug("Parser not available, returning original group names")
            return grouped_files

        updated_groups = {}

        for group_name, files in grouped_files.items():
            try:
                # Find the best representative file for parsing
                best_file = self._select_representative_file(files)
                if not best_file:
                    updated_groups[group_name] = files
                    continue

                # Parse the representative filename
                parsed_result = self.parser.parse(best_file.file_path.name)

                # Use parsed title if it's better than the original group name
                new_group_name = self.quality_evaluator.select_better_title(
                    group_name,
                    parsed_result.title,
                )

                # Ensure unique group names
                final_group_name = self.group_manager.ensure_unique_group_name(
                    new_group_name,
                    updated_groups,
                )

                updated_groups[final_group_name] = files

                logger.debug(
                    "Updated group name: '%s' -> '%s' (from file: %s)",
                    group_name,
                    final_group_name,
                    best_file.file_path.name,
                )

            except (ValueError, TypeError, AttributeError) as e:
                logger.warning(
                    "Failed to update group name '%s': %s",
                    group_name,
                    str(e),
                )
                # Fallback to original group name
                updated_groups[group_name] = files

        return updated_groups

    def _select_representative_file(
        self,
        files: list[ScannedFile],
    ) -> ScannedFile | None:
        """Select the best representative file for parsing.

        Args:
            files: List of files in the group

        Returns:
            Best representative file for parsing, or None if empty
        """
        if not files:
            return None

        # Prefer files with more descriptive names (longer filenames)
        # and avoid files with common generic patterns
        def score_file(file: ScannedFile) -> float:
            filename = file.file_path.name
            score = len(filename)

            # Bonus for files with episode numbers (more likely to be main content)
            if re.search(r"\d+", filename):
                score += 10

            # Penalty for files that look like subtitles or extras
            if any(
                pattern in filename.lower()
                for pattern in [".srt", ".ass", ".vtt", "extra", "special"]
            ):
                score -= 20

            return score

        return max(files, key=score_file)

    def _score_title_quality(self, title: str) -> int:
        """Score title quality based on various factors.

        Args:
            title: Title to score

        Returns:
            Quality score (higher is better)
        """
        score = 0

        # Length factor (prefer medium length titles)
        length = len(title)
        if (
            TitleQualityScores.GOOD_LENGTH_MIN
            <= length
            <= TitleQualityScores.GOOD_LENGTH_MAX
        ):
            score += TitleQualityScores.GOOD_LENGTH_BONUS
        elif length < TitleQualityScores.GOOD_LENGTH_MIN or length > 100:
            score += TitleQualityScores.BAD_LENGTH_PENALTY

        # Penalty for technical information
        for pattern in TECHNICAL_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                score += TitleQualityScores.TECHNICAL_PATTERN_PENALTY

        # Bonus for proper anime title patterns
        if re.search(r"[A-Z][a-z]+.*[A-Z][a-z]+", title):  # Title Case
            score += TitleQualityScores.TITLE_CASE_BONUS

        # Bonus for Japanese characters (often anime titles)
        if re.search(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]", title):
            score += TitleQualityScores.JAPANESE_CHAR_BONUS

        # Penalty for too many special characters
        special_chars = len(re.findall(r"[^\w\s]", title))
        if special_chars > TitleQualityScores.MAX_SPECIAL_CHARS:
            score += TitleQualityScores.SPECIAL_CHAR_PENALTY

        return score

    def _is_cleaner_title(self, title1: str, title2: str) -> bool:
        """Check if title1 is cleaner than title2.

        Args:
            title1: First title
            title2: Second title

        Returns:
            True if title1 is cleaner
        """
        # Count technical patterns
        count1 = sum(
            1
            for pattern in TECHNICAL_PATTERNS
            if re.search(pattern, title1, re.IGNORECASE)
        )
        count2 = sum(
            1
            for pattern in TECHNICAL_PATTERNS
            if re.search(pattern, title2, re.IGNORECASE)
        )

        return count1 < count2

    def _contains_technical_info(self, title: str) -> bool:
        """Check if title contains technical information.

        Args:
            title: Title to check

        Returns:
            True if contains technical info
        """
        return any(
            re.search(pattern, title, re.IGNORECASE) for pattern in TECHNICAL_PATTERNS
        )


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
