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
from anivault.config.models.matching_weights import MatchingWeights
from anivault.core.data_structures.linked_hash_table import LinkedHashTable
from anivault.core.file_grouper.models import Group
from anivault.core.models import ScannedFile

from .title_index import TitleIndex

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
        threshold: float | None = None,
        weights: MatchingWeights | None = None,
    ) -> None:
        """Initialize title similarity matcher.

        Args:
            title_extractor: Extractor for parsing titles from filenames.
            quality_evaluator: Evaluator for selecting best title variant.
            threshold: Minimum similarity score (0.0-1.0) for grouping.
                      If None, uses title_similarity_threshold from weights.
                      Default is 0.85 (85% similarity) if weights is also None.
            weights: MatchingWeights instance for configurable weights.
                    If None, loads from config or uses defaults.

        Raises:
            ValueError: If threshold is not in range [0.0, 1.0].

        Example:
            >>> from anivault.core.file_grouper import TitleExtractor, TitleQualityEvaluator
            >>> extractor = TitleExtractor()
            >>> evaluator = TitleQualityEvaluator()
            >>> matcher = TitleSimilarityMatcher(extractor, evaluator, threshold=0.9)
        """
        # Load weights if not provided
        if weights is None:
            try:
                settings = load_settings()
                weights = settings.matching_weights
            except (ImportError, AttributeError):
                weights = MatchingWeights()

        self.weights = weights

        # Use threshold from weights if not explicitly provided
        if threshold is None:
            threshold = self.weights.title_similarity_threshold

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
            (file_id_to_file[fid], file_id_to_title[fid]) for fid in file_id_to_file if fid not in processed_file_ids
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

        # Step 4: Group remaining files using LSH + keyword-based filtering with fallback
        # Build keyword sets for each remaining file
        file_keywords: dict[int, set[str]] = {}
        for file_id, title in file_id_to_title.items():
            if file_id not in processed_file_ids:
                normalized = title_index._normalize_title(title)
                file_keywords[file_id] = set(normalized.split()) if normalized else set()

        # O(1) file -> file_id lookup (avoids O(F) scan per remaining file)
        id_to_file_id: dict[int, int] = {id(f): fid for fid, f in file_id_to_file.items()}

        # Keyword reverse index for fallback: O(candidates per keyword) vs O(F) scan
        keyword_to_file_ids: dict[str, set[int]] = {}
        for fid, kw in file_keywords.items():
            for k in kw:
                keyword_to_file_ids.setdefault(k, set()).add(fid)

        # O(1) rep lookup: map rep_file_id -> (group_name, group_files) for existing groups
        rep_to_group: dict[int, tuple[str, list[ScannedFile]]] = {}
        for _gn, _gf in all_groups_table:
            if _gf:
                _rep_id = id_to_file_id.get(id(_gf[0]))
                if _rep_id is not None:
                    rep_to_group[_rep_id] = (_gn, _gf)

        # Group remaining files using LSH-first approach with keyword fallback
        for file, title in remaining_files:
            current_file_id = id_to_file_id.get(id(file))
            if current_file_id is None or current_file_id in processed_file_ids:
                continue

            file_keyword_set = file_keywords.get(current_file_id, set())
            matched_group = None

            # Strategy 1: Try LSH to find similar candidates first
            # Pre-filter LSH candidates with keyword intersection for better accuracy
            lsh_candidates = title_index.query_similar_titles(title)
            lsh_candidates = [c for c in lsh_candidates if c != current_file_id and c not in processed_file_ids]

            # Strategy 2: Check against existing groups using LSH candidates if available
            # Otherwise fall back to keyword-based filtering
            candidate_file_ids: set[int] = set()
            if lsh_candidates:
                # Filter LSH candidates by keyword intersection for better precision
                # This reduces false positives from LSH
                filtered_lsh_candidates = []
                for candidate_id in lsh_candidates:
                    candidate_keywords = file_keywords.get(candidate_id, set())
                    if file_keyword_set and candidate_keywords:
                        if file_keyword_set.intersection(candidate_keywords):
                            filtered_lsh_candidates.append(candidate_id)
                    elif not file_keyword_set or not candidate_keywords:
                        # If either has no keywords, include it (edge case)
                        filtered_lsh_candidates.append(candidate_id)

                candidate_file_ids = set(filtered_lsh_candidates)
                logger.debug(
                    "LSH found %d candidates (filtered from %d) for title '%s' (file_id=%d)",
                    len(candidate_file_ids),
                    len(lsh_candidates),
                    title,
                    current_file_id,
                )
            else:
                # Fallback: Use keyword reverse index (O(keywords * file_ids per keyword) vs O(F))
                candidate_file_ids = set()
                for k in file_keyword_set:
                    candidate_file_ids.update(keyword_to_file_ids.get(k, set()))
                candidate_file_ids.discard(current_file_id)
                candidate_file_ids -= processed_file_ids
                # Filter by keyword intersection for precision
                candidate_file_ids = {
                    oid
                    for oid in candidate_file_ids
                    if file_keyword_set.intersection(file_keywords.get(oid, set()))
                }
                logger.debug(
                    "LSH found no candidates, using keyword intersection: %d candidates for title '%s'",
                    len(candidate_file_ids),
                    title,
                )

            # Check only groups whose rep is in candidate_file_ids (O(C) vs O(G))
            for cid in candidate_file_ids:
                if cid not in rep_to_group:
                    continue
                group_name, group_files = rep_to_group[cid]
                if not group_files:
                    continue
                rep_file_id = cid

                # Additional keyword check for safety (even with LSH)
                rep_keyword_set = file_keywords.get(rep_file_id, set())
                if file_keyword_set and rep_keyword_set:
                    if not file_keyword_set.intersection(rep_keyword_set):
                        continue  # No keyword overlap, skip

                # Get representative title from group
                rep_title = file_id_to_title.get(rep_file_id, group_name)

                # Guard conditions: skip similarity calculation if titles are too different
                # Apply guard conditions early to avoid expensive operations
                len1, len2 = len(title), len(rep_title)
                if len1 > 0 and len2 > 0:
                    length_ratio = min(len1, len2) / max(len1, len2)
                    if length_ratio < 0.5:  # More than 50% difference
                        continue

                # Check token count difference (early exit)
                title_tokens = title.split()
                rep_title_tokens = rep_title.split()
                token_diff = abs(len(title_tokens) - len(rep_title_tokens))
                if token_diff > 3:
                    continue

                # Additional early guard: check if first few characters match
                # This is a fast heuristic before expensive similarity calculation
                if len1 >= 3 and len2 >= 3:
                    if title[:3].lower() != rep_title[:3].lower():
                        # Only skip if no keyword overlap (already checked above)
                        # This is a soft guard - still allow if keywords match
                        pass  # Keep this check soft to avoid false negatives

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
                        # Keep rep_to_group in sync for O(1) lookups
                        rep_id = id_to_file_id.get(id(old_files[0]))
                        if rep_id is not None:
                            rep_to_group[rep_id] = (better_title, old_files)
                    matched_group = better_title
            else:
                # Create new group
                new_list: list[ScannedFile] = [file]
                all_groups_table.put(title, new_list)
                rep_to_group[current_file_id] = (title, new_list)

        # Step 5: Convert to Group objects and apply large group splitting
        max_group_size = self._get_max_title_match_group_size()
        result = []
        for group_name, group_files in all_groups_table:
            if len(group_files) > max_group_size:
                # Split large groups recursively for better performance
                logger.debug(
                    "Splitting large group '%s' (%d files) into smaller groups",
                    group_name,
                    len(group_files),
                )
                # Recursively match the files in this large group
                subgroups = self.match(group_files)
                result.extend(subgroups)
            else:
                result.append(Group(title=group_name, files=group_files))

        logger.info(
            "Title matcher grouped %d files into %d groups (using TitleIndex optimization)",
            len(files),
            len(result),
        )

        return result

    def refine_group(self, group: Group) -> list[Group] | None:
        """Refine a group by subdividing it based on title similarity.

        This method takes an existing group (typically from Hash matcher) and
        subdivides it into smaller groups based on pairwise title similarity.
        Files with similar titles (above threshold) are grouped together.

        Optimized for Hash-first pipeline:
        - Uses Hash group's normalized title as a hint for faster matching
        - Leverages TitleIndex for efficient candidate filtering
        - Skips expensive similarity calculations when Hash match is strong

        If the group cannot be subdivided (all files are similar or only one file),
        returns None to indicate no refinement occurred.

        Args:
            group: Group object containing files to refine.

        Returns:
            List of refined Group objects if subdivision occurred (all subgroups),
            or None if no refinement was needed.

        Note:
            This method is designed to work with the Hash-first pipeline where
            Hash matcher creates initial groups, and Title matcher refines them.
            When multiple subgroups are created, returns all of them to preserve
            all files (previously only the first subgroup was returned, dropping others).

        Example:
            >>> hash_group = Group(title="Anime", files=[file1, file2, file3])
            >>> refined = matcher.refine_group(hash_group)
            >>> if refined:
            ...     sum(len(g.files) for g in refined)  # All files preserved
        """
        if not group.files:
            return None

        # If group has only one file, no refinement needed
        if len(group.files) == 1:
            return None

        # Hash-first optimization: Build TitleIndex only for this group's files
        # This reduces the search space from O(n²) to O(m²) where m = group size
        title_index = TitleIndex()
        file_id_to_file: dict[int, ScannedFile] = {}
        file_id_to_title: dict[int, str] = {}

        for file_id, file in enumerate(group.files, start=1):
            title = self._extract_title_from_file(file)
            if title:
                title_index.add_title(file_id, title)
                file_id_to_file[file_id] = file
                file_id_to_title[file_id] = title

        if not file_id_to_file:
            return None

        # Hash-first optimization: Check if all files have exact normalized match
        # If so, no refinement needed (Hash matcher already grouped them correctly)
        if len(file_id_to_title) > 1:
            first_title = next(iter(file_id_to_title.values()))
            exact_matches = title_index.get_exact_matches(first_title)
            if len(exact_matches) == len(file_id_to_file):
                # All files have exact normalized match - Hash matcher was correct
                logger.debug(
                    "Hash group '%s' has exact normalized matches, no Title refinement needed",
                    group.title,
                )
                return None

        # Use optimized match() method to subdivide the group
        # This reuses existing logic but benefits from smaller search space
        # Note: match() drops files without extractable title - we must preserve them
        subgroups = self.match(group.files)

        # If no subgroups created or only one subgroup, return None
        # (no refinement occurred - all files remain together)
        if not subgroups or len(subgroups) == 1:
            return None

        # Preserve files that match() dropped (no extractable title)
        files_in_subgroups = {f.file_path for g in subgroups for f in g.files}
        orphaned = [f for f in group.files if f.file_path not in files_in_subgroups]
        if orphaned:
            subgroups[0].files.extend(orphaned)
            logger.debug(
                "Refined group '%s': preserved %d file(s) without extractable title",
                group.title,
                len(orphaned),
            )

        # Return all subgroups to preserve all files (fix: was returning only first)
        logger.debug(
            "Refined group '%s' (%d files) into %d subgroup(s)",
            group.title,
            len(group.files),
            len(subgroups),
        )
        return subgroups


# Re-export TitleIndex for backward compatibility
__all__ = ["TitleIndex", "TitleSimilarityMatcher"]
