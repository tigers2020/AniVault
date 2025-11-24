"""Hash-based similarity matcher for file grouping.

This module implements hash-based grouping using normalized title hashing.
Files with identical normalized titles (after removing punctuation, case, etc.)
are grouped together.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from anivault.core.data_structures.linked_hash_table import LinkedHashTable
from anivault.core.file_grouper.models import Group
from anivault.core.models import ScannedFile

logger = logging.getLogger(__name__)

# Security: Maximum title length to prevent ReDoS attacks
MAX_TITLE_LENGTH = 500


class HashSimilarityMatcher:
    """Groups files using normalized title hashing.

    This matcher normalizes titles by removing punctuation, converting to lowercase,
    and normalizing whitespace. Files with identical normalized titles are grouped.

    This is faster than fuzzy matching but requires exact matches after normalization.

    Attributes:
        component_name: Identifier for this matcher ("hash").
        title_extractor: Extracts base titles from filenames.

    Example:
        >>> from anivault.core.file_grouper.grouper import TitleExtractor
        >>> extractor = TitleExtractor()
        >>> matcher = HashSimilarityMatcher(title_extractor=extractor)
        >>> groups = matcher.match(scanned_files)
        >>> len(groups)
        5
    """

    def __init__(self, title_extractor: Any) -> None:
        """Initialize the hash similarity matcher.

        Args:
            title_extractor: TitleExtractor instance for extracting titles.
        """
        self.component_name = "hash"
        self.title_extractor = title_extractor

    def match(self, files: list[ScannedFile]) -> list[Group]:
        """Group files by normalized title hash.

        Files with identical normalized titles are grouped together.
        Normalization includes:
        - Convert to lowercase
        - Remove punctuation
        - Normalize whitespace

        Args:
            files: List of ScannedFile objects to group.

        Returns:
            List of Group objects with identical normalized titles grouped together.
            Returns empty list if input is empty or no groupings found.

        Example:
            >>> files = [
            ...     ScannedFile(file_path=Path("Anime.Title.S01E01.mkv"), ...),
            ...     ScannedFile(file_path=Path("Anime Title - 01.mkv"), ...),
            ... ]
            >>> groups = matcher.match(files)
            >>> groups[0].title
            'Anime Title'
            >>> len(groups[0].files)
            2
        """
        if not files:
            return []

        # Step 1: Extract and normalize titles
        file_titles: list[tuple[ScannedFile, str, str]] = []  # (file, original, normalized)
        for file in files:
            title = self._extract_title_from_file(file)
            if title:
                normalized = self._normalize_title(title)
                file_titles.append((file, title, normalized))
            else:
                logger.warning(
                    "Could not extract title from file: %s",
                    file.file_path.name,
                )

        if not file_titles:
            return []

        # Step 2: Group files by normalized hash using LinkedHashTable for O(1) operations
        hash_groups = LinkedHashTable[str, list[tuple[ScannedFile, str]]](
            initial_capacity=max(len(file_titles) * 2, 64),
            load_factor=0.75,
        )
        for file, original_title, normalized_title in file_titles:
            existing_group = hash_groups.get(normalized_title)
            if existing_group:
                existing_group.append((file, original_title))
            else:
                hash_groups.put(normalized_title, [(file, original_title)])

        # Step 3: Convert to Group objects (use first original title as group name)
        result = []
        for _, file_title_pairs in hash_groups:
            if not file_title_pairs:
                continue

            # Use first original title as group name (could be improved with quality scoring)
            group_title = file_title_pairs[0][1]
            group_files = [file for file, _ in file_title_pairs]

            result.append(Group(title=group_title, files=group_files))

        logger.info(
            "Hash matcher grouped %d files into %d groups",
            len(files),
            len(result),
        )

        return result

    def _extract_title_from_file(self, file: ScannedFile) -> str | None:
        """Extract title from a scanned file.

        Tries to use parsed metadata title first, falls back to filename extraction.

        Args:
            file: ScannedFile to extract title from.

        Returns:
            Extracted title string, or None if extraction failed.

        Example:
            >>> file = ScannedFile(file_path=Path("anime_01.mkv"), metadata=...)
            >>> matcher._extract_title_from_file(file)
            'Anime Title'
        """
        # Try to get parsed title first (more accurate)
        base_title = None
        if hasattr(file, "metadata") and file.metadata and hasattr(file.metadata, "title"):
            parsed_title = file.metadata.title
            if parsed_title and parsed_title != file.file_path.name:
                base_title = parsed_title

        # Fallback to extract_base_title if parsing failed
        if not base_title:
            base_title = self.title_extractor.extract_base_title(
                file.file_path.name,
            )

        return base_title

    def _normalize_title(self, title: str) -> str:
        """Normalize title for hash-based grouping.

        Normalization process:
        1. Truncate to MAX_TITLE_LENGTH to prevent ReDoS attacks
        2. Convert to lowercase
        3. Remove punctuation (keep only alphanumeric and whitespace)
        4. Normalize whitespace (multiple spaces to single space)
        5. Strip leading/trailing whitespace

        Args:
            title: Original title to normalize.

        Returns:
            Normalized title for hashing.

        Example:
            >>> matcher._normalize_title("Attack on Titan - S01E01")
            'attack on titan s01e01'
            >>> matcher._normalize_title("  Multiple   Spaces  ")
            'multiple spaces'
            >>> matcher._normalize_title("Special!@#Characters")
            'specialcharacters'
        """
        # Security: Truncate to prevent ReDoS attacks with malicious input
        if len(title) > MAX_TITLE_LENGTH:
            logger.warning(
                "Title exceeds maximum length (%d), truncating: %s",
                MAX_TITLE_LENGTH,
                title[:50] + "...",
            )
            title = title[:MAX_TITLE_LENGTH]

        # Convert to lowercase
        normalized = title.lower()

        # Remove punctuation (keep only alphanumeric and whitespace)
        # Pattern: [^\w\s] matches anything that's NOT alphanumeric or whitespace
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Normalize whitespace (multiple spaces to single space)
        normalized = re.sub(r"\s+", " ", normalized)

        # Strip leading/trailing whitespace
        return normalized.strip()


__all__ = ["HashSimilarityMatcher"]
