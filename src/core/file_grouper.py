"""
File grouper module for AniVault application.

This module provides functionality to group similar anime files based on
filename similarity using SequenceMatcher and other heuristics.
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from .models import AnimeFile, FileGroup

# Logger for this module
logger = logging.getLogger(__name__)


@dataclass
class GroupingResult:
    """Result of a file grouping operation."""

    groups: list[FileGroup]
    ungrouped_files: list[AnimeFile]
    grouping_duration: float
    total_files: int
    grouped_files: int
    similarity_threshold: float
    errors: list[str]

    @property
    def grouping_rate(self) -> float:
        """Calculate the percentage of files that were grouped."""
        if self.total_files == 0:
            return 0.0
        return (self.grouped_files / self.total_files) * 100


class FileGrouper:
    """
    Groups similar anime files based on filename similarity and other heuristics.

    This class provides intelligent file grouping using:
    - SequenceMatcher for similarity calculation
    - Filename pattern recognition
    - Episode number detection
    - Quality and resolution matching
    - Parallel processing for performance
    """

    def __init__(
        self,
        similarity_threshold: float = 0.75,
        max_workers: int = 4,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> None:
        """
        Initialize the file grouper.

        Args:
            similarity_threshold: Minimum similarity score for grouping (0.0-1.0)
            max_workers: Maximum number of worker threads for parallel processing
            progress_callback: Optional callback for progress updates
        """
        self.similarity_threshold = similarity_threshold
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self._cancelled = False

        # Compile regex patterns for better performance
        self._episode_pattern = re.compile(r"[Ee](\d+)|- (\d+)(?:\s|$)", re.IGNORECASE)
        self._season_pattern = re.compile(r"[Ss](\d+)", re.IGNORECASE)
        self._quality_pattern = re.compile(r"(\d{3,4}[pP])", re.IGNORECASE)
        self._resolution_pattern = re.compile(r"(\d{3,4}x\d{3,4})", re.IGNORECASE)

    def group_files(self, files: list[AnimeFile]) -> GroupingResult:
        """
        Group similar anime files together.

        Args:
            files: List of AnimeFile objects to group

        Returns:
            GroupingResult containing grouped files and metadata
        """
        start_time = time.time()
        errors: list[str] = []

        try:
            logger.info(f"FileGrouper.group_files called with {len(files)} files")

            if not files:
                logger.warning("No files provided to group_files")
                return GroupingResult(
                    groups=[],
                    ungrouped_files=[],
                    grouping_duration=0.0,
                    total_files=0,
                    grouped_files=0,
                    similarity_threshold=self.similarity_threshold,
                    errors=[],
                )

            if self.progress_callback:
                self.progress_callback(0, f"Starting grouping of {len(files)} files...")

            # Pre-process files for better grouping
            logger.debug("Starting file preprocessing...")
            processed_files = self._preprocess_files(files)
            logger.debug(f"Preprocessed {len(processed_files)} files")

            # Group files using similarity analysis
            logger.debug("Starting similarity grouping...")
            groups, ungrouped_files = self._group_files_similarity(processed_files)
            logger.info(
                f"Similarity grouping created {len(groups)} groups, {len(ungrouped_files)} ungrouped files"
            )

            # Post-process groups to improve accuracy
            logger.debug("Starting post-processing...")
            groups = self._postprocess_groups(groups)
            logger.info(f"After post-processing: {len(groups)} groups")

            # Create FileGroup objects
            logger.debug("Creating FileGroup objects...")
            file_groups = self._create_file_groups(groups)
            logger.info(f"Created {len(file_groups)} FileGroup objects")

            grouping_duration = time.time() - start_time
            grouped_files = sum(len(group.files) for group in file_groups)

            if self.progress_callback:
                self.progress_callback(
                    100, f"Grouping completed: {len(file_groups)} groups created"
                )

            logger.info(
                f"Grouping completed successfully: {len(file_groups)} groups, {grouped_files} files grouped"
            )
            return GroupingResult(
                groups=file_groups,
                ungrouped_files=ungrouped_files,
                grouping_duration=grouping_duration,
                total_files=len(files),
                grouped_files=grouped_files,
                similarity_threshold=self.similarity_threshold,
                errors=errors,
            )

        except Exception as e:
            error_msg = f"Error during file grouping: {str(e)}"
            errors.append(error_msg)

            if self.progress_callback:
                self.progress_callback(0, f"Error: {error_msg}")

            return GroupingResult(
                groups=[],
                ungrouped_files=files,
                grouping_duration=time.time() - start_time,
                total_files=len(files),
                grouped_files=0,
                similarity_threshold=self.similarity_threshold,
                errors=errors,
            )

    def _preprocess_files(self, files: list[AnimeFile]) -> list[AnimeFile]:
        """Pre-process files to extract useful information for grouping."""
        logger.debug(f"Preprocessing {len(files)} files...")
        processed_files = []

        for i, file in enumerate(files):
            # Extract additional metadata from filename
            file._extracted_info = self._extract_filename_info(file.filename)
            processed_files.append(file)

            if i < 3:  # Log first 3 files for debugging
                info = file._extracted_info
                logger.debug(f"  File {i+1}: {file.filename}")
                logger.debug(f"    Clean name: '{info.get('clean_name', 'N/A')}'")
                logger.debug(f"    Episode: {info.get('episode', 'N/A')}")
                logger.debug(f"    Season: {info.get('season', 'N/A')}")
                logger.debug(f"    Quality: {info.get('quality', 'N/A')}")

        logger.debug(f"Preprocessing completed for {len(processed_files)} files")
        return processed_files

    def _extract_filename_info(self, filename: str) -> dict[str, Any]:
        """Extract useful information from filename for grouping."""
        info = {
            "base_name": "",
            "episode": None,
            "season": None,
            "quality": None,
            "resolution": None,
            "clean_name": "",
        }

        # Remove file extension
        name_without_ext = filename.rsplit(".", 1)[0]

        # Extract episode number
        episode_match = self._episode_pattern.search(name_without_ext)
        if episode_match:
            # Try group 1 first (E01 pattern), then group 2 (- 01 pattern)
            episode_num = episode_match.group(1) or episode_match.group(2)
            if episode_num:
                info["episode"] = int(episode_num)

        # Extract season number
        season_match = self._season_pattern.search(name_without_ext)
        if season_match:
            info["season"] = int(season_match.group(1))

        # Extract quality (1080p, 720p, etc.)
        quality_match = self._quality_pattern.search(name_without_ext)
        if quality_match:
            info["quality"] = quality_match.group(1).lower()

        # Extract resolution (1920x1080, etc.)
        resolution_match = self._resolution_pattern.search(name_without_ext)
        if resolution_match:
            info["resolution"] = resolution_match.group(1).lower()

        # Create clean name for similarity comparison
        clean_name = self._clean_filename(name_without_ext)
        info["clean_name"] = clean_name
        info["base_name"] = clean_name

        return info

    def _clean_filename(self, filename: str) -> str:
        """Clean filename for better similarity comparison."""
        # Remove common anime release group patterns
        patterns_to_remove = [
            r"\[.*?\]",  # [GroupName]
            r"\(.*?\)",  # (Year)
            r"\.\d{4}",  # .2023
            r"[Ss]\d+[Ee]\d+",  # S01E01
            r"[Ee]\d+",  # E01
            r"[Ss]\d+",  # S01
            r"\d{3,4}[pP]",  # 1080p
            r"\d{3,4}x\d{3,4}",  # 1920x1080
            r"[Hh]\.?[Dd][Tt][Vv]",  # HDTV
            r"[Bb][Ll][Uu][Rr][Aa][Yy]",  # BluRay
            r"[Ww][Ee][Bb]",  # WEB
            r"[Dd][Vv][Dd]",  # DVD
            r"[Xx]264",  # x264
            r"[Xx]265",  # x265
            r"[Aa][Aa][Cc]",  # AAC
            r"[Ff][Ll][Aa][Cc]",  # FLAC
            r"[Mm][Kk][Vv]",  # MKV
            r"[Mm][Pp]4",  # MP4
            r"[Aa][Vv][Ii]",  # AVI
        ]

        clean_name = filename
        for pattern in patterns_to_remove:
            clean_name = re.sub(pattern, "", clean_name, flags=re.IGNORECASE)

        # Remove extra spaces and special characters
        clean_name = re.sub(r"[._-]+", " ", clean_name)
        clean_name = re.sub(r"\s+", " ", clean_name)
        clean_name = clean_name.strip()

        return clean_name

    def _group_files_similarity(
        self, files: list[AnimeFile]
    ) -> tuple[list[list[AnimeFile]], list[AnimeFile]]:
        """Group files based on filename similarity."""
        logger.debug(
            f"Starting similarity grouping with {len(files)} files, threshold={self.similarity_threshold}"
        )

        try:
            groups: list[list[AnimeFile]] = []
            ungrouped_files: list[AnimeFile] = []
            processed_files = set()
            logger.debug(
                f"Initialized variables: groups={len(groups)}, ungrouped={len(ungrouped_files)}, processed={len(processed_files)}"
            )

            for i, file1 in enumerate(files):
                logger.debug(f"=== Processing file {i+1}/{len(files)}: {file1.filename} ===")
                if file1 in processed_files:
                    logger.debug(f"Skipping file {i+1}: {file1.filename} (already processed)")
                    continue

                if self.progress_callback and i % 10 == 0:
                    progress = int((i / len(files)) * 50)  # First half of progress
                    self.progress_callback(
                        progress, f"Analyzing file similarities... {i}/{len(files)}"
                    )

                current_group = [file1]
                processed_files.add(file1)
                logger.debug(f"Processing file {i+1}: {file1.filename}")

                # Get file1's extracted info for debugging
                info1 = getattr(file1, "_extracted_info", {})
                clean_name1 = info1.get("clean_name", file1.filename)
                logger.debug(f"  File1 clean name: '{clean_name1}'")

                # Find similar files
                similar_count = 0
                for j, file2 in enumerate(files[i + 1 :], i + 1):
                    logger.debug(
                        f"  --- Comparing with file {j+1}/{len(files)}: {file2.filename} ---"
                    )
                    if file2 in processed_files:
                        logger.debug(f"  Skipping file {j+1}: {file2.filename} (already processed)")
                        continue

                    # Get file2's extracted info for debugging
                    info2 = getattr(file2, "_extracted_info", {})
                    clean_name2 = info2.get("clean_name", file2.filename)
                    logger.debug(f"  File2 clean name: '{clean_name2}'")

                    logger.debug(f"  Comparing with file {j+1}: {file2.filename}")
                    if self._are_files_similar(file1, file2):
                        current_group.append(file2)
                        processed_files.add(file2)
                        similar_count += 1
                        logger.debug(f"  Found similar file: {file2.filename}")
                    else:
                        logger.debug(f"  Files not similar: {file1.filename} vs {file2.filename}")

                logger.debug(
                    f"  Created group with {len(current_group)} files (found {similar_count} similar files)"
                )
                # Create groups (including single-file groups)
                groups.append(current_group)
                logger.debug(f"  Total groups so far: {len(groups)}")

            logger.info(f"Similarity grouping completed: {len(groups)} groups created")
            return groups, ungrouped_files
        except Exception as e:
            logger.error(f"Error in _group_files_similarity: {e}", exc_info=True)
            raise

    def _are_files_similar(self, file1: AnimeFile, file2: AnimeFile) -> bool:
        """Check if two files are similar enough to be grouped together."""
        # Get extracted info
        info1 = getattr(file1, "_extracted_info", {})
        info2 = getattr(file2, "_extracted_info", {})

        # Check base name similarity
        clean_name1 = info1.get("clean_name", file1.filename)
        clean_name2 = info2.get("clean_name", file2.filename)

        similarity = SequenceMatcher(None, clean_name1, clean_name2).ratio()
        logger.debug(
            f"Comparing '{clean_name1}' vs '{clean_name2}': similarity={similarity:.3f}, threshold={self.similarity_threshold}"
        )

        if similarity < self.similarity_threshold:
            logger.debug(
                f"  Files not similar enough: {similarity:.3f} < {self.similarity_threshold}"
            )
            return False

        # Additional heuristics for better grouping

        # Check if they have the same season
        season1 = info1.get("season")
        season2 = info2.get("season")
        if season1 is not None and season2 is not None and season1 != season2:
            logger.debug(f"  Different seasons: {season1} vs {season2}")
            return False

        # Check if they have the same quality (optional)
        quality1 = info1.get("quality")
        quality2 = info2.get("quality")
        if quality1 and quality2 and quality1 != quality2:
            # Different quality but still similar - allow grouping
            logger.debug(f"  Different quality but allowing grouping: {quality1} vs {quality2}")
            pass

        logger.debug(f"  Files are similar: {similarity:.3f} >= {self.similarity_threshold}")
        return True

    def _postprocess_groups(self, groups: list[list[AnimeFile]]) -> list[list[AnimeFile]]:
        """Post-process groups to improve accuracy and merge similar groups."""
        if not groups:
            return groups

        # Sort groups by size (larger groups first)
        groups.sort(key=len, reverse=True)

        # Try to merge similar groups
        merged_groups = []
        processed_groups = set()

        for i, group1 in enumerate(groups):
            if i in processed_groups:
                continue

            current_group = group1.copy()
            processed_groups.add(i)

            # Try to merge with other groups
            for j, group2 in enumerate(groups[i + 1 :], i + 1):
                if j in processed_groups:
                    continue

                if self._should_merge_groups(current_group, group2):
                    current_group.extend(group2)
                    processed_groups.add(j)

            merged_groups.append(current_group)

        return merged_groups

    def merge_groups_by_name(self, groups: list[FileGroup]) -> list[FileGroup]:
        """Merge groups that have the same name after TMDB metadata application."""
        if not groups:
            return groups

        # Group by name (including groups without TMDB metadata)
        groups_by_name = {}
        for group in groups:
            # Use group_name if available, otherwise use series_title as fallback
            group_name = group.group_name or group.series_title or "Unknown"
            if group_name not in groups_by_name:
                groups_by_name[group_name] = []
            groups_by_name[group_name].append(group)

        # Merge groups with the same name
        merged_groups = []
        for group_name, group_list in groups_by_name.items():
            if len(group_list) == 1:
                merged_groups.append(group_list[0])
            else:
                # Merge multiple groups with the same name
                logger.info(f"Merging {len(group_list)} groups with name '{group_name}'")

                # Use the first group as the base
                base_group = group_list[0]

                # Add all files from other groups
                for other_group in group_list[1:]:
                    for file in other_group.files:
                        base_group.add_file(file)

                # Update group metadata
                base_group.similarity_score = self._calculate_group_similarity(base_group.files)
                base_group.group_name = group_name
                base_group.series_title = group_name  # Update series_title as well

                merged_groups.append(base_group)
                logger.info(
                    f"Merged {len(group_list)} groups into one group with {len(base_group.files)} files"
                )

        logger.info(
            f"Final result: {len(merged_groups)} groups (merged {len(groups)} into {len(merged_groups)})"
        )
        return merged_groups

    def _should_merge_groups(self, group1: list[AnimeFile], group2: list[AnimeFile]) -> bool:
        """Check if two groups should be merged."""
        # Get representative files from each group
        file1 = group1[0]
        file2 = group2[0]

        # Check similarity between representative files
        return self._are_files_similar(file1, file2)

    def _create_file_groups(self, groups: list[list[AnimeFile]]) -> list[FileGroup]:
        """Create FileGroup objects from grouped files."""
        file_groups = []

        for i, group_files in enumerate(groups):
            if not group_files:
                continue

            # Generate unique group ID
            group_id = str(uuid.uuid4())

            # Create FileGroup
            file_group = FileGroup(group_id=group_id)

            # Add files to group
            for file in group_files:
                file_group.add_file(file)

            # Calculate similarity score
            file_group.similarity_score = self._calculate_group_similarity(group_files)

            # Set group metadata
            self._set_group_metadata(file_group)

            file_groups.append(file_group)

        return file_groups

    def _calculate_group_similarity(self, files: list[AnimeFile]) -> float:
        """Calculate average similarity score for a group of files."""
        if len(files) < 2:
            return 1.0

        total_similarity = 0.0
        comparisons = 0

        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                file1 = files[i]
                file2 = files[j]

                info1 = getattr(file1, "_extracted_info", {})
                info2 = getattr(file2, "_extracted_info", {})

                clean_name1 = info1.get("clean_name", file1.filename)
                clean_name2 = info2.get("clean_name", file2.filename)

                similarity = SequenceMatcher(None, clean_name1, clean_name2).ratio()
                total_similarity += similarity
                comparisons += 1

        return total_similarity / comparisons if comparisons > 0 else 0.0

    def _set_group_metadata(self, file_group: FileGroup) -> None:
        """Set metadata for a file group."""
        if not file_group.files:
            return

        # Use the best file's information for group metadata
        best_file = file_group.best_file
        if best_file:
            info = getattr(best_file, "_extracted_info", {})
            file_group.series_title = info.get("base_name", best_file.filename)

            # Set season if available
            season = info.get("season")
            if season is not None:
                file_group.season = season

    def cancel_grouping(self) -> None:
        """Cancel the current grouping operation."""
        self._cancelled = True

    def reset(self) -> None:
        """Reset the grouper state."""
        self._cancelled = False


def group_files(
    files: list[AnimeFile],
    similarity_threshold: float = 0.75,
    max_workers: int = 4,
    progress_callback: Callable[[int, str], None] | None = None,
) -> GroupingResult:
    """
    Convenience function to group anime files by similarity.

    Args:
        files: List of AnimeFile objects to group
        similarity_threshold: Minimum similarity score for grouping
        max_workers: Maximum number of worker threads
        progress_callback: Optional callback for progress updates

    Returns:
        GroupingResult containing grouped files and metadata
    """
    grouper = FileGrouper(
        similarity_threshold=similarity_threshold,
        max_workers=max_workers,
        progress_callback=progress_callback,
    )
    return grouper.group_files(files)
