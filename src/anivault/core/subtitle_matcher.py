"""Subtitle file matching module for AniVault.

This module provides functionality to match subtitle files with their
corresponding video files based on filename patterns.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from anivault.config import load_settings
from anivault.core.models import ScannedFile
from anivault.shared.constants import SubtitleMatchingStrategy
from anivault.core.subtitle_hash import HASH_CHUNK_SIZE, calculate_file_hash
from anivault.core.subtitle_index import SubtitleIndex, SubtitleIndexCache
from anivault.shared.errors import (
    AniVaultError,
    ErrorCode,
    ErrorContextModel,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error

logger = logging.getLogger(__name__)

# Regex for 8+ character hex strings (e.g. content hashes in filenames)
_HEX_HASH_PATTERN = r"[A-Fa-f0-9]{8,}"


class SubtitleMatcher:
    """Matches subtitle files with their corresponding video files."""

    def __init__(self) -> None:
        """Initialize the subtitle matcher."""
        # Supported subtitle extensions
        self.subtitle_extensions = {".srt", ".smi", ".ass", ".ssa", ".vtt", ".sub"}
        # Cache for SubtitleIndex instances per directory
        self._index_cache = SubtitleIndexCache()

    def _build_subtitle_index(self, directory: Path) -> None:
        """Build an index of subtitle files for fast lookup.

        Scans the directory for subtitle files and builds a SubtitleIndex using caching.

        Args:
            directory: Directory to scan for subtitle files
        """
        if not directory.exists():
            return

        # Scan directory for subtitle files
        subtitle_files = [f for f in directory.iterdir() if self._is_subtitle_file(f)]

        # Build or get cached SubtitleIndex (cache is used internally)
        subtitle_index = self._index_cache.get_or_build(directory, subtitle_files)

        logger.debug(
            "Built subtitle index with %d hash keys, %d name keys, and %d total files",
            len(subtitle_index.hash_index),
            len(subtitle_index.name_index),
            len(subtitle_files),
        )

    def _get_subtitle_matching_strategy(self) -> str:
        """Get subtitle matching strategy from configuration.

        Returns:
            Strategy name: SubtitleMatchingStrategy.INDEXED/FALLBACK/LEGACY
        """
        try:
            settings = load_settings()
            if hasattr(settings, "grouping") and settings.grouping is not None:
                return settings.grouping.subtitle_matching_strategy
        except (ImportError, AttributeError) as e:
            logger.debug(
                "Could not load subtitle_matching_strategy from config, using default 'indexed': %s",
                e,
            )

        # Default to indexed for optimal performance
        return SubtitleMatchingStrategy.INDEXED

    def find_matching_subtitles(
        self,
        video_file: ScannedFile,
        directory: Path,
    ) -> list[Path]:
        """Find subtitle files that match a video file.

        Uses strategy-based matching:
        - INDEXED: Uses pre-built index for O(f+s) performance (default)
        - FALLBACK: Uses index but falls back to full scan if lookup fails
        - LEGACY: Uses full directory scan for backward compatibility

        Args:
            video_file: The video file to find subtitles for
            directory: Directory to search for subtitle files

        Returns:
            List of matching subtitle file paths

        Raises:
            InfrastructureError: If matching fails
        """
        context = ErrorContextModel(
            operation="find_matching_subtitles",
            additional_data={
                "video_file": str(video_file.file_path),
                "directory": str(directory),
            },
        )

        try:
            if not directory.exists():
                return []

            strategy = self._get_subtitle_matching_strategy()
            matching_subtitles = self._find_matching_subtitles_by_strategy(video_file, directory, strategy)

            logger.debug(
                "Found %d matching subtitles for %s (strategy: %s)",
                len(matching_subtitles),
                video_file.file_path.name,
                strategy,
            )
            return matching_subtitles

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(
                "Failed to find matching subtitles",
                extra={"context": context.additional_data if context else None},
            )
            raise InfrastructureError(
                code=ErrorCode.SUBTITLE_MATCHING_FAILED,
                message=f"Failed to find matching subtitles for {video_file.file_path}: {e!s}",
                context=context,
                original_error=e,
            ) from e

    def _find_matching_subtitles_by_strategy(
        self,
        video_file: ScannedFile,
        directory: Path,
        strategy: str,
    ) -> list[Path]:
        """Dispatch to strategy-specific matching and return matched paths."""
        if strategy == SubtitleMatchingStrategy.LEGACY:
            return self._match_legacy(video_file, directory)
        if strategy in (SubtitleMatchingStrategy.INDEXED, SubtitleMatchingStrategy.FALLBACK):
            return self._match_indexed_or_fallback(video_file, directory, strategy)
        return []

    def _match_legacy(self, video_file: ScannedFile, directory: Path) -> list[Path]:
        """Legacy mode: full directory scan (backward compatibility)."""
        video_name = video_file.file_path.stem
        matching: list[Path] = []
        for subtitle_file in directory.iterdir():
            if self._is_subtitle_file(subtitle_file) and self._matches_video(subtitle_file.stem, video_name):
                matching.append(subtitle_file)
        return matching

    def _match_indexed_or_fallback(
        self,
        video_file: ScannedFile,
        directory: Path,
        strategy: str,
    ) -> list[Path]:
        """Use index for lookup; optionally fall back to full scan if no matches."""
        subtitle_files = [f for f in directory.iterdir() if self._is_subtitle_file(f)]
        subtitle_index = self._index_cache.get_or_build(directory, subtitle_files)
        matching = self._match_via_index(video_file, subtitle_index)
        if strategy == SubtitleMatchingStrategy.FALLBACK and not matching:
            logger.debug(
                "No matches found in index, falling back to full scan for %s",
                video_file.file_path.name,
            )
            matching = self._match_legacy(video_file, directory)
        return matching

    def _match_via_index(
        self,
        video_file: ScannedFile,
        subtitle_index: SubtitleIndex,
    ) -> list[Path]:
        """Find matching subtitles using the pre-built index."""
        video_name = video_file.file_path.stem
        candidates = self._collect_candidates_from_index(video_name, subtitle_index)
        return [p for p in candidates if self._matches_video(p.stem, video_name)]

    def _collect_candidates_from_index(
        self,
        video_name: str,
        subtitle_index: SubtitleIndex,
    ) -> list[Path]:
        """Collect unique candidate subtitle paths from hash, name, and prefix lookups."""
        candidate_subtitles: list[Path] = []

        video_hash = self._extract_hash_from_name(video_name)
        if video_hash:
            candidate_subtitles.extend(subtitle_index.get_by_hash(video_hash))

        video_clean = self._clean_video_name(video_name)
        normalized_video_name = subtitle_index.normalize_subtitle_name(video_clean)
        if normalized_video_name:
            candidate_subtitles.extend(subtitle_index.get_by_name(normalized_video_name))
            candidate_subtitles.extend(subtitle_index.get_by_name_prefix(normalized_video_name))

        seen: set[Path] = set()
        unique: list[Path] = []
        for path in candidate_subtitles:
            if path not in seen:
                seen.add(path)
                unique.append(path)
        return unique

    def _is_subtitle_file(self, file_path: Path) -> bool:
        """Check if a file is a subtitle file.

        Args:
            file_path: Path to check

        Returns:
            True if the file is a subtitle file
        """
        return file_path.suffix.lower() in self.subtitle_extensions

    def _matches_video(self, subtitle_name: str, video_name: str) -> bool:  # pylint: disable=too-many-return-statements
        """Check if a subtitle filename matches a video filename.

        Args:
            subtitle_name: Subtitle filename (without extension)
            video_name: Video filename (without extension)

        Returns:
            True if the subtitle matches the video
        """
        # Remove common subtitle-specific suffixes
        subtitle_clean = self._clean_subtitle_name(subtitle_name)
        video_clean = self._clean_video_name(video_name)

        # Check for exact match
        if subtitle_clean == video_clean:
            return True

        # Check for partial match (subtitle might have additional info)
        if subtitle_clean.startswith(video_clean) or video_clean.startswith(
            subtitle_clean,
        ):
            return True

        # Check for hash-based matching (common in anime releases)
        if self._has_matching_hash(subtitle_name, video_name):
            return True

        # NEW: Fuzzy matching with last word removal
        # This handles cases where one has an extra word like "Part" or "Season"
        subtitle_words = subtitle_clean.split()
        video_words = video_clean.split()

        # Try removing last word from subtitle and matching
        if len(subtitle_words) > 1:
            subtitle_without_last = " ".join(subtitle_words[:-1])
            if subtitle_without_last == video_clean:
                return True

        # Try removing last word from video and matching
        if len(video_words) > 1:
            video_without_last = " ".join(video_words[:-1])
            if video_without_last == subtitle_clean:
                return True

        # Fuzzy match: check if first N-1 words match
        if len(subtitle_words) > 1 and len(video_words) > 1:
            subtitle_prefix = " ".join(subtitle_words[:-1])
            video_prefix = " ".join(video_words[:-1])
            if subtitle_prefix == video_prefix:
                return True

        return False

    def _clean_subtitle_name(self, name: str) -> str:
        """Clean subtitle filename for matching.

        Args:
            name: Subtitle filename to clean

        Returns:
            Cleaned filename
        """
        # Remove common subtitle-specific patterns

        patterns_to_remove = [
            r"\.(?:srt|smi|ass|ssa|vtt|sub)$",  # File extensions
            r"\[(?:sub|subs|subtitles)\]",  # Subtitle indicators
            r"\((?:sub|subs|subtitles)\)",
            r"\.(?:eng|kor|jpn|jap)",  # Language codes
            r"\[(?:eng|kor|jpn|jap)\]",
            r"\((?:eng|kor|jpn|jap)\)",
        ]

        cleaned = name
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _clean_video_name(self, name: str) -> str:
        """Clean video filename for matching.

        Args:
            name: Video filename to clean

        Returns:
            Cleaned filename
        """
        # Remove common video-specific patterns

        patterns_to_remove = [
            r"\.(?:mkv|mp4|avi|mov|wmv|flv|webm|m4v)$",  # File extensions
            r"\[(?:1080p|720p|480p|2160p|4K|HD|SD)\]",  # Resolution
            r"\((?:1080p|720p|480p|2160p|4K|HD|SD)\)",
            r"\[(?:x264|x265|H\.264|H\.265|HEVC|AVC|VP9|AV1)\]",  # Codecs
            r"\((?:x264|x265|H\.264|H\.265|HEVC|AVC|VP9|AV1)\)",
        ]

        cleaned = name
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    def _has_matching_hash(self, subtitle_name: str, video_name: str) -> bool:
        """Check if subtitle and video have matching hash patterns.

        Args:
            subtitle_name: Subtitle filename
            video_name: Video filename

        Returns:
            True if they have matching hash patterns
        """

        # Extract hash patterns (8+ character hex strings)
        subtitle_hashes = re.findall(_HEX_HASH_PATTERN, subtitle_name)
        video_hashes = re.findall(_HEX_HASH_PATTERN, video_name)

        # Check if any hashes match
        return bool(set(subtitle_hashes).intersection(set(video_hashes)))

    def _extract_hash_from_name(self, name: str) -> str | None:
        """Extract hash pattern from a filename.

        Args:
            name: Filename to extract hash from

        Returns:
            First hash found, or None if no hash exists
        """

        # Extract hash patterns (8+ character hex strings)
        hashes = re.findall(_HEX_HASH_PATTERN, name)
        return hashes[0] if hashes else None

    def _get_subtitle_index_key(self, subtitle_path: Path) -> str:
        """Generate an index key for a subtitle file.

        Uses hash if available, otherwise falls back to series-like prefix.

        Args:
            subtitle_path: Path to the subtitle file

        Returns:
            Index key (hash or series prefix)

        Example:
            >>> matcher = SubtitleMatcher()
            >>> key = matcher._get_subtitle_index_key(Path("Series.S01E01.abc12345.srt"))
            >>> key
            'abc12345'
        """
        subtitle_name = subtitle_path.stem

        # Try to extract hash first
        hash_value = self._extract_hash_from_name(subtitle_name)
        if hash_value:
            return hash_value

        # Fallback: use cleaned subtitle name as series prefix
        # This creates a consistent key for files with similar names
        series_prefix = self._clean_subtitle_name(subtitle_name)
        return series_prefix

    def _get_video_index_key(self, video_file: ScannedFile) -> str:
        """Generate an index key for a video file.

        Uses hash if available, otherwise falls back to series-like prefix.

        Args:
            video_file: The video file to generate key for

        Returns:
            Index key (hash or series prefix)

        Example:
            >>> matcher = SubtitleMatcher()
            >>> key = matcher._get_video_index_key(ScannedFile(...))
            >>> key
            'abc12345'
        """
        video_name = video_file.file_path.stem

        # Try to extract hash first
        hash_value = self._extract_hash_from_name(video_name)
        if hash_value:
            return hash_value

        # Fallback: use cleaned video name as series prefix
        series_prefix = self._clean_video_name(video_name)
        return series_prefix

    def group_files_with_subtitles(
        self,
        files: list[ScannedFile],
        directory: Path,
    ) -> dict[str, dict[str, Any]]:
        """Group video files with their matching subtitles.

        This method builds an index of subtitle files for fast lookup,
        then uses the index to match subtitles with video files.

        Args:
            files: List of video files to group
            directory: Directory containing the files

        Returns:
            Dictionary mapping video file paths to their metadata including subtitles

        Raises:
            InfrastructureError: If grouping fails
        """
        context = ErrorContextModel(
            operation="group_files_with_subtitles",
            additional_data={"file_count": len(files), "directory": str(directory)},
        )

        try:
            # Build subtitle index once
            self._build_subtitle_index(directory)

            grouped_files = {}

            for video_file in files:
                subtitles = self.find_matching_subtitles(video_file, directory)
                grouped_files[str(video_file.file_path)] = {
                    "video_file": video_file,
                    "subtitles": subtitles,
                    "has_subtitles": len(subtitles) > 0,
                }

            # Get index size from cache if available
            subtitle_index = self._index_cache.get(directory)
            index_size = len(subtitle_index.hash_index) + len(subtitle_index.name_index) if subtitle_index else 0
            logger.info(
                "Grouped %d files with subtitles in %s (index size: %d)",
                len(files),
                directory,
                index_size,
            )

            return grouped_files

        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

        except Exception as e:  # pylint: disable=broad-exception-caught
            if isinstance(e, AniVaultError):
                log_operation_error(
                    logger=logger,
                    operation="group_files_with_subtitles",
                    error=e,
                    additional_context=context.additional_data if context else None,
                )
            else:
                error = InfrastructureError(
                    code=ErrorCode.SUBTITLE_GROUPING_FAILED,
                    message=f"Failed to group files with subtitles: {e!s}",
                    context=context,
                    original_error=e,
                )
                log_operation_error(
                    logger=logger,
                    operation="group_files_with_subtitles",
                    error=error,
                    additional_context=context.additional_data if context else None,
                )
            raise InfrastructureError(
                code=ErrorCode.SUBTITLE_GROUPING_FAILED,
                message=f"Failed to group files with subtitles: {e!s}",
                context=context,
                original_error=e,
            ) from e


# Re-export for backward compatibility (tests import from subtitle_matcher)
__all__ = [
    "HASH_CHUNK_SIZE",
    "SubtitleIndex",
    "SubtitleIndexCache",
    "SubtitleMatcher",
    "calculate_file_hash",
    "find_subtitles_for_video",
]


def find_subtitles_for_video(video_file: ScannedFile, directory: Path) -> list[Path]:
    """Convenience function to find subtitles for a single video file.

    Args:
        video_file: The video file to find subtitles for
        directory: Directory to search for subtitle files

    Returns:
        List of matching subtitle file paths
    """
    matcher = SubtitleMatcher()
    return matcher.find_matching_subtitles(video_file, directory)
