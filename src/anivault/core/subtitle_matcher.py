"""Subtitle file matching module for AniVault.

This module provides functionality to match subtitle files with their
corresponding video files based on filename patterns.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from anivault.core.models import ScannedFile
from anivault.shared.errors import ErrorCode, ErrorContext, InfrastructureError
from anivault.shared.logging import log_operation_error

logger = logging.getLogger(__name__)


class SubtitleMatcher:
    """Matches subtitle files with their corresponding video files."""

    def __init__(self) -> None:
        """Initialize the subtitle matcher."""
        # Supported subtitle extensions
        self.subtitle_extensions = {".srt", ".smi", ".ass", ".ssa", ".vtt", ".sub"}

    def find_matching_subtitles(
        self,
        video_file: ScannedFile,
        directory: Path,
    ) -> list[Path]:
        """Find subtitle files that match a video file.

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

            video_name = video_file.file_path.stem
            matching_subtitles = []

            # Search for subtitle files in the same directory
            for subtitle_file in directory.iterdir():
                if self._is_subtitle_file(subtitle_file):
                    if self._matches_video(subtitle_file.stem, video_name):
                        matching_subtitles.append(subtitle_file)

            logger.debug(
                "Found %d matching subtitles for %s",
                len(matching_subtitles),
                video_file.file_path.name,
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

        return False

    def _clean_subtitle_name(self, name: str) -> str:
        """Clean subtitle filename for matching.

        Args:
            name: Subtitle filename to clean

        Returns:
            Cleaned filename
        """
        # Remove common subtitle-specific patterns
        import re

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
        import re

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
        import re

        # Extract hash patterns (8+ character hex strings)
        subtitle_hashes = re.findall(r"[A-Fa-f0-9]{8,}", subtitle_name)
        video_hashes = re.findall(r"[A-Fa-f0-9]{8,}", video_name)

        # Check if any hashes match
        return bool(set(subtitle_hashes).intersection(set(video_hashes)))

    def group_files_with_subtitles(
        self,
        files: list[ScannedFile],
        directory: Path,
    ) -> dict[str, dict[str, Any]]:
        """Group video files with their matching subtitles.

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
            grouped_files = {}

            for video_file in files:
                subtitles = self.find_matching_subtitles(video_file, directory)
                grouped_files[str(video_file.file_path)] = {
                    "video_file": video_file,
                    "subtitles": subtitles,
                    "has_subtitles": len(subtitles) > 0,
                }

            logger.info(
                "Grouped %d files with subtitles in %s",
                len(files),
                directory,
            )

            return grouped_files

        except Exception as e:
            log_operation_error(
                logger=logger,
                operation="group_files_with_subtitles",
                error=e,
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
