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
from anivault.shared.errors import (
    AniVaultError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import log_operation_error

logger = logging.getLogger(__name__)


class SubtitleMatcher:
    """Matches subtitle files with their corresponding video files."""

    def __init__(self) -> None:
        """Initialize the subtitle matcher."""
        # Supported subtitle extensions
        self.subtitle_extensions = {".srt", ".smi", ".ass", ".ssa", ".vtt", ".sub"}
        # Index for fast subtitle lookup: key -> list of subtitle file paths
        self.index: dict[str, list[Path]] = {}

    def _build_subtitle_index(self, directory: Path) -> None:
        """Build an index of subtitle files for fast lookup.

        Scans the directory for subtitle files and indexes them by hash or series prefix.

        Args:
            directory: Directory to scan for subtitle files
        """
        if not directory.exists():
            return

        # Clear existing index
        self.index.clear()

        # Scan directory for subtitle files
        for subtitle_file in directory.iterdir():
            if not self._is_subtitle_file(subtitle_file):
                continue

            # Generate index key
            key = self._get_subtitle_index_key(subtitle_file)

            # Add to index
            if key not in self.index:
                self.index[key] = []

            # Check for potential collisions (different series with same prefix)
            existing_files = self.index[key]
            if existing_files:
                # Simple collision detection: check if file names are similar
                # This is a heuristic - more sophisticated collision detection
                # could be added later if needed
                first_file_name = self._clean_subtitle_name(existing_files[0].stem)
                current_file_name = self._clean_subtitle_name(subtitle_file.stem)

                # If cleaned names are very different, log a warning
                if first_file_name != current_file_name:
                    # Check if they share a common prefix (at least 5 characters)
                    common_prefix_length = 0
                    min_length = min(len(first_file_name), len(current_file_name))
                    for i in range(min_length):
                        if first_file_name[i].lower() == current_file_name[i].lower():
                            common_prefix_length += 1
                        else:
                            break

                    if common_prefix_length < 5:
                        logger.warning(
                            "Potential index key collision for key '%s': "
                            "files '%s' and '%s' may belong to different series",
                            key,
                            existing_files[0].name,
                            subtitle_file.name,
                        )

            self.index[key].append(subtitle_file)

        logger.debug(
            "Built subtitle index with %d keys and %d total files",
            len(self.index),
            sum(len(files) for files in self.index.values()),
        )

    def _get_subtitle_matching_strategy(self) -> str:
        """Get subtitle matching strategy from configuration.

        Returns:
            Strategy name: "indexed", "fallback", or "legacy"
        """
        try:
            settings = load_settings()
            if hasattr(settings, "grouping") and settings.grouping is not None:
                return settings.grouping.subtitle_matching_strategy
        except (ImportError, AttributeError, Exception) as e:
            logger.debug(
                "Could not load subtitle_matching_strategy from config, using default 'indexed': %s",
                e,
            )

        # Default to "indexed" for optimal performance
        return "indexed"

    def find_matching_subtitles(
        self,
        video_file: ScannedFile,
        directory: Path,
    ) -> list[Path]:
        """Find subtitle files that match a video file.

        Uses strategy-based matching:
        - "indexed": Uses pre-built index for O(f+s) performance (default)
        - "fallback": Uses index but falls back to full scan if lookup fails
        - "legacy": Uses full directory scan for backward compatibility

        Args:
            video_file: The video file to find subtitles for
            directory: Directory to search for subtitle files

        Returns:
            List of matching subtitle file paths

        Raises:
            InfrastructureError: If matching fails
        """
        context = ErrorContext(
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
            video_name = video_file.file_path.stem
            matching_subtitles = []

            if strategy == "legacy":
                # Legacy mode: full directory scan (backward compatibility)
                for subtitle_file in directory.iterdir():
                    if self._is_subtitle_file(subtitle_file):
                        if self._matches_video(subtitle_file.stem, video_name):
                            matching_subtitles.append(subtitle_file)

            elif strategy in ("indexed", "fallback"):
                # Indexed mode: use index for fast lookup
                if not self.index:
                    # Index not built yet, fall back to full scan
                    logger.debug(
                        "Index not available, falling back to full scan for %s",
                        video_file.file_path.name,
                    )
                    for subtitle_file in directory.iterdir():
                        if self._is_subtitle_file(subtitle_file):
                            if self._matches_video(subtitle_file.stem, video_name):
                                matching_subtitles.append(subtitle_file)
                else:
                    # Generate index key for video file
                    video_key = self._get_video_index_key(video_file)

                    # Get candidate subtitles from index
                    candidate_subtitles: list[Path] = []
                    if video_key in self.index:
                        candidate_subtitles = self.index[video_key]

                    # Also check for hash-based matches
                    video_hash = self._extract_hash_from_name(video_name)
                    if video_hash and video_hash in self.index:
                        for subtitle_path in self.index[video_hash]:
                            if subtitle_path not in candidate_subtitles:
                                candidate_subtitles.append(subtitle_path)

                    # Check series prefix matches (for non-hash keys)
                    if not candidate_subtitles:
                        video_clean = self._clean_video_name(video_name)
                        for key, subtitle_paths in self.index.items():
                            # Skip hash keys (already checked)
                            if len(key) >= 8 and all(
                                c in "0123456789ABCDEFabcdef" for c in key
                            ):
                                continue

                            # Check if key matches video prefix
                            if video_clean.startswith(key) or key.startswith(
                                video_clean
                            ):
                                for subtitle_path in subtitle_paths:
                                    if subtitle_path not in candidate_subtitles:
                                        candidate_subtitles.append(subtitle_path)

                    # Match within candidates only
                    for subtitle_path in candidate_subtitles:
                        if self._matches_video(subtitle_path.stem, video_name):
                            matching_subtitles.append(subtitle_path)

                    # Fallback mode: if no matches found and strategy is "fallback", try full scan
                    if strategy == "fallback" and not matching_subtitles:
                        logger.debug(
                            "No matches found in index, falling back to full scan for %s",
                            video_file.file_path.name,
                        )
                        for subtitle_file in directory.iterdir():
                            if self._is_subtitle_file(subtitle_file):
                                if self._matches_video(subtitle_file.stem, video_name):
                                    if subtitle_file not in matching_subtitles:
                                        matching_subtitles.append(subtitle_file)

            logger.debug(
                "Found %d matching subtitles for %s (strategy: %s)",
                len(matching_subtitles),
                video_file.file_path.name,
                strategy,
            )

            return matching_subtitles

        except Exception as e:
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

    def _is_subtitle_file(self, file_path: Path) -> bool:
        """Check if a file is a subtitle file.

        Args:
            file_path: Path to check

        Returns:
            True if the file is a subtitle file
        """
        return file_path.suffix.lower() in self.subtitle_extensions

    def _matches_video(self, subtitle_name: str, video_name: str) -> bool:
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
        subtitle_hashes = re.findall(r"[A-Fa-f0-9]{8,}", subtitle_name)
        video_hashes = re.findall(r"[A-Fa-f0-9]{8,}", video_name)

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
        hashes = re.findall(r"[A-Fa-f0-9]{8,}", name)
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
        context = ErrorContext(
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

            logger.info(
                "Grouped %d files with subtitles in %s (index size: %d)",
                len(files),
                directory,
                len(self.index),
            )

            return grouped_files

        except Exception as e:
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
