"""Title-based similarity matcher for file grouping.

This module implements title-based grouping using fuzzy string matching.
Files with similar titles are grouped together based on configurable threshold.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from rapidfuzz import fuzz

from anivault.config import load_settings
from anivault.core.data_structures.linked_hash_table import LinkedHashTable
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
        score: float = float(fuzz.ratio(title1.lower(), title2.lower()))
        # Normalize to 0.0-1.0 range
        return score / 100.0

    def _get_max_title_match_group_size(self) -> int:
        """Get max_title_match_group_size from configuration.

        Returns:
            Maximum group size for Title matcher processing (default: 150)
        """
        try:
            settings = load_settings()
            if hasattr(settings, "grouping") and settings.grouping is not None:
                return settings.grouping.max_title_match_group_size
        except (ImportError, AttributeError) as e:
            logger.debug(
                "Could not load max_title_match_group_size from config, using default 150: %s",
                e,
            )

        # Default to 150 (reduced from 1000 for performance)
        return 150

    def match(self, files: list[ScannedFile]) -> list[Group]:
        """Group files by title similarity.

        Files with similar titles (above threshold) are grouped together.
        The best title variant is selected as the group name using quality evaluation.

        This method uses TitleIndex for efficient matching:
        1. Builds keyword index and normalized hash for all titles
        2. Processes exact matches first (O(1) lookup)
        3. Filters candidates using keyword intersection before expensive similarity calculations

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

        # Step 1: Extract titles from all files and build TitleIndex
        file_titles: list[tuple[ScannedFile, str]] = []
        title_index = TitleIndex()
        file_id_to_file: dict[int, ScannedFile] = {}
        file_id_to_title: dict[int, str] = {}
        
        for file_id, file in enumerate(files, start=1):
            title = self._extract_title_from_file(file)
            if title:
                file_titles.append((file, title))
                title_index.add_title(file_id, title)
                file_id_to_file[file_id] = file
                file_id_to_title[file_id] = title
            else:
                logger.warning(
                    "Could not extract title from file: %s",
                    file.file_path.name,
                )

        if not file_titles:
            return []

        # Step 2: Process exact matches first (O(1) lookup using normalized_hash)
        processed_file_ids: set[int] = set()
        all_groups_table = LinkedHashTable[str, list[ScannedFile]](
            initial_capacity=max(len(file_titles) * 2, 64),
            load_factor=0.75,
        )
        
        for file_id, title in file_id_to_title.items():
            if file_id in processed_file_ids:
                continue
            
            # Get all files with exact normalized match
            exact_matches = title_index.get_exact_matches(title)
            
            if len(exact_matches) > 1:  # More than just this file
                # Create group from exact matches
                exact_files = [file_id_to_file[fid] for fid in exact_matches if fid in file_id_to_file]
                if exact_files:
                    # Select best title as group name
                    group_title = title
                    for fid in exact_matches:
                        if fid in file_id_to_title:
                            candidate_title = file_id_to_title[fid]
                            group_title = self.quality_evaluator.select_better_title(
                                group_title,
                                candidate_title,
                            )
                    
                    # Add to groups
                    existing_files = all_groups_table.get(group_title)
                    if existing_files:
                        existing_files.extend(exact_files)
                    else:
                        all_groups_table.put(group_title, exact_files.copy())
                    
                    # Mark all as processed
                    processed_file_ids.update(exact_matches)

        # Step 3: Process remaining files using keyword-based filtering
        remaining_files: list[tuple[ScannedFile, str]] = [
            (file_id_to_file[fid], file_id_to_title[fid])
            for fid in file_id_to_file.keys()
            if fid not in processed_file_ids
        ]

        if not remaining_files:
            # All files were exact matches, return groups
            result = [Group(title=group_name, files=group_files) for group_name, group_files in all_groups_table]
            logger.info(
                "Title matcher grouped %d files into %d groups (all exact matches)",
                len(files),
                len(result),
            )
            return result

        # Step 4: Group remaining files using keyword-based filtering
        # Build keyword sets for each remaining file
        file_keywords: dict[int, set[str]] = {}
        for file_id, title in file_id_to_title.items():
            if file_id not in processed_file_ids:
                normalized = title_index._normalize_title(title)
                file_keywords[file_id] = set(normalized.split()) if normalized else set()

        # Group remaining files using keyword intersection filtering
        for file, title in remaining_files:
            file_id = next((fid for fid, f in file_id_to_file.items() if f is file), None)
            if file_id is None or file_id in processed_file_ids:
                continue
            
            file_keyword_set = file_keywords.get(file_id, set())
            matched_group = None
            
            # Check against existing groups
            for group_name, group_files in all_groups_table:
                # Find a representative file from this group to compare with
                if not group_files:
                    continue
                
                # Get keywords from first file in group (as representative)
                rep_file_id = next((fid for fid, f in file_id_to_file.items() if f is group_files[0]), None)
                if rep_file_id is None:
                    continue
                
                rep_keyword_set = file_keywords.get(rep_file_id, set())
                
                # Only compare if keywords intersect (filtering step)
                if not file_keyword_set or not rep_keyword_set:
                    continue
                
                if not file_keyword_set.intersection(rep_keyword_set):
                    continue  # No keyword overlap, skip expensive similarity calculation
                
                # Get representative title from group
                rep_title = file_id_to_title.get(rep_file_id, group_name)
                
                # Guard conditions: skip similarity calculation if titles are too different
                len1, len2 = len(title), len(rep_title)
                if len1 > 0 and len2 > 0:
                    length_ratio = min(len1, len2) / max(len1, len2)
                    if length_ratio < 0.5:  # More than 50% difference
                        continue

                # Check token count difference
                title_tokens = title.split()
                rep_title_tokens = rep_title.split()
                token_diff = abs(len(title_tokens) - len(rep_title_tokens))
                if token_diff > 3:
                    continue

                # Only calculate similarity if guard conditions pass
                similarity = self._calculate_similarity(title, rep_title)
                if similarity >= self.threshold:
                    matched_group = group_name
                    break

            if matched_group:
                # Add to existing group
                existing_files = all_groups_table.get(matched_group)
                if existing_files:
                    existing_files.append(file)
                else:
                    all_groups_table.put(matched_group, [file])

                # Update group name if this title is better quality
                better_title = self.quality_evaluator.select_better_title(
                    matched_group,
                    title,
                )
                if better_title != matched_group:
                    # Replace group name with better title
                    old_files = all_groups_table.remove(matched_group)
                    if old_files:
                        all_groups_table.put(better_title, old_files)
                    matched_group = better_title
            else:
                # Create new group
                all_groups_table.put(title, [file])

        # Step 5: Convert to Group objects
        result = [Group(title=group_name, files=group_files) for group_name, group_files in all_groups_table]

        logger.info(
            "Title matcher grouped %d files into %d groups (using TitleIndex optimization)",
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


# Security: Maximum title length to prevent ReDoS attacks
MAX_TITLE_LENGTH = 500


class TitleIndex:
    """Index for efficient title matching using keyword indexing and normalized hashing.

    This class provides O(1) lookup for exact matches and efficient filtering
    for similar titles using keyword-based indexing.

    Attributes:
        keyword_index: Dictionary mapping keywords to sets of file IDs.
        normalized_hash: Dictionary mapping normalized titles to lists of file IDs.

    Example:
        >>> index = TitleIndex()
        >>> index.add_title(1, "Attack on Titan - S01E01")
        >>> index.add_title(2, "Attack on Titan - S01E02")
        >>> matches = index.get_exact_matches("Attack on Titan - S01E01")
        >>> len(matches)
        1
    """

    def __init__(self) -> None:
        """Initialize an empty TitleIndex."""
        self.keyword_index: dict[str, set[int]] = {}
        self.normalized_hash: dict[str, list[int]] = {}

    def _normalize_title(self, title: str) -> str:
        """Normalize title for indexing and matching.

        This function removes metadata (brackets, special characters, version info)
        and standardizes the title for consistent matching.

        Normalization process:
        1. Truncate to MAX_TITLE_LENGTH to prevent ReDoS attacks
        2. Convert to lowercase
        3. Remove file extensions: .mkv, .mp4, etc.
        4. Remove brackets and their contents: [], (), 【】, etc. (iteratively for nested)
        5. Remove version patterns: _v2, _v1.0, etc.
        6. Replace hyphens and underscores with spaces
        7. Remove special characters (keep only alphanumeric, Korean, and whitespace)
        8. Normalize whitespace (multiple spaces/tabs/newlines to single space)
        9. Strip leading/trailing whitespace

        Args:
            title: Original title to normalize.

        Returns:
            Normalized title string.

        Example:
            >>> index = TitleIndex()
            >>> index._normalize_title("[Group] Show Name - 01 (1080p).mkv")
            'show name 01'
            >>> index._normalize_title("Show_Name_S2_Ep2.mp4")
            'show name s2 ep2'
            >>> index._normalize_title("Title (_v2)")
            'title'
        """
        if not title:
            return ""

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

        # Remove file extensions: .mkv, .mp4, etc.
        normalized = re.sub(r"\.(?:mkv|mp4|avi|mov|wmv|flv|webm|m4v|m2ts|ts|srt|ass|ssa|sub)$", "", normalized)

        # Remove brackets and their contents: [], (), 【】, 「」, 『』
        # Use iterative removal to handle nested brackets
        bracket_patterns = [
            r"\[[^\]]*\]",  # Square brackets
            r"\([^)]*\)",  # Parentheses
            r"【[^】]*】",  # Full-width square brackets
            r"「[^」]*」",  # Japanese quotation marks
            r"『[^』]*』",  # Japanese double quotation marks
        ]
        # Iterate multiple times to handle nested brackets
        for _ in range(5):  # Max nesting depth of 5
            changed = False
            for pattern in bracket_patterns:
                new_normalized = re.sub(pattern, "", normalized)
                if new_normalized != normalized:
                    changed = True
                    normalized = new_normalized
            if not changed:
                break

        # Remove version patterns: _v2, _v1.0, _ver2, etc.
        version_patterns = [
            r"_v\d+(?:\.\d+)?",  # _v2, _v1.0
            r"_ver\d+",  # _ver2
            r"\(v\d+\)",  # (v2)
            r"\[v\d+\]",  # [v2]
        ]
        for pattern in version_patterns:
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

        # Replace hyphens and underscores with spaces (before removing special chars)
        normalized = re.sub(r"[-_]", " ", normalized)

        # Remove special characters (keep only alphanumeric, Korean, and whitespace)
        # Pattern: [^\w\s] matches anything that's NOT word character or whitespace
        # \w includes alphanumeric and Korean characters (가-힣)
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Normalize whitespace (multiple spaces/tabs/newlines to single space)
        normalized = re.sub(r"\s+", " ", normalized)

        # Strip leading/trailing whitespace
        return normalized.strip()

    def add_title(self, file_id: int, title: str) -> None:
        """Add a title to the index.

        This method normalizes the title, tokenizes it into keywords,
        and updates both the keyword_index and normalized_hash.

        Args:
            file_id: Unique identifier for the file.
            title: Original title string to index.

        Example:
            >>> index = TitleIndex()
            >>> index.add_title(1, "Attack on Titan - S01E01")
            >>> index.add_title(2, "Attack on Titan - S01E02")
            >>> "attack" in index.keyword_index
            True
            >>> 1 in index.keyword_index["attack"]
            True
            >>> 2 in index.keyword_index["attack"]
            True
        """
        if not title:
            return

        # Normalize the title
        normalized = self._normalize_title(title)
        
        if not normalized:
            return

        # Update normalized_hash (for exact match lookup)
        if normalized not in self.normalized_hash:
            self.normalized_hash[normalized] = []
        if file_id not in self.normalized_hash[normalized]:
            self.normalized_hash[normalized].append(file_id)

        # Tokenize normalized title into keywords (split by whitespace)
        keywords = normalized.split()
        
        # Update keyword_index: each keyword maps to a set of file IDs
        for keyword in keywords:
            if keyword:  # Skip empty strings
                if keyword not in self.keyword_index:
                    self.keyword_index[keyword] = set()
                self.keyword_index[keyword].add(file_id)

    def get_exact_matches(self, title: str) -> list[int]:
        """Get all file IDs with titles that normalize to the same string.

        This method provides O(1) lookup for exact matches after normalization.
        Titles that differ only in metadata (brackets, special characters, etc.)
        will be matched together.

        Args:
            title: Original title to find matches for.

        Returns:
            List of file IDs that have titles normalizing to the same string.
            Returns empty list if no matches found.

        Example:
            >>> index = TitleIndex()
            >>> index.add_title(1, "Show Title - 01.mkv")
            >>> index.add_title(2, "show title - 01 [1080p].mp4")
            >>> matches = index.get_exact_matches("Show Title - 01")
            >>> sorted(matches)
            [1, 2]
        """
        if not title:
            return []

        # Normalize the input title
        normalized = self._normalize_title(title)
        
        if not normalized:
            return []

        # Return file IDs from normalized_hash (O(1) lookup)
        return self.normalized_hash.get(normalized, []).copy()


__all__ = ["TitleSimilarityMatcher", "TitleIndex"]
