"""Subtitle file matching module for AniVault.

This module provides functionality to match subtitle files with their
corresponding video files based on filename patterns.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
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

# Chunk size for streaming file hash calculation (64KB)
HASH_CHUNK_SIZE = 65536


class SubtitleMatcher:
    """Matches subtitle files with their corresponding video files."""

    def __init__(self) -> None:
        """Initialize the subtitle matcher."""
        # Supported subtitle extensions
        self.subtitle_extensions = {".srt", ".smi", ".ass", ".ssa", ".vtt", ".sub"}
        # Index for fast subtitle lookup: key -> list of subtitle file paths
        # DEPRECATED: Kept for backward compatibility, use _index_cache instead
        self.index: dict[str, list[Path]] = {}
        # Cache for SubtitleIndex instances per directory
        self._index_cache = SubtitleIndexCache()

    def _build_subtitle_index(self, directory: Path) -> None:
        """Build an index of subtitle files for fast lookup.

        Scans the directory for subtitle files and builds a SubtitleIndex using caching.
        Also maintains backward compatibility by populating self.index.

        Args:
            directory: Directory to scan for subtitle files
        """
        if not directory.exists():
            return

        # Scan directory for subtitle files
        subtitle_files = [f for f in directory.iterdir() if self._is_subtitle_file(f)]

        # Build or get cached SubtitleIndex (cache is used internally)
        self._index_cache.get_or_build(directory, subtitle_files)

        # Populate legacy self.index for backward compatibility
        self.index.clear()
        for subtitle_file in subtitle_files:
            key = self._get_subtitle_index_key(subtitle_file)
            if key not in self.index:
                self.index[key] = []
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
        except (ImportError, AttributeError, Exception) as e:  # pylint: disable=broad-exception-caught
            logger.debug(
                "Could not load subtitle_matching_strategy from config, using default 'indexed': %s",
                e,
            )

        # Default to "indexed" for optimal performance
        return "indexed"

    def find_matching_subtitles(  # pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks  # pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks
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
                # Indexed mode: use SubtitleIndex for fast lookup
                # Build or get cached index
                subtitle_files = [f for f in directory.iterdir() if self._is_subtitle_file(f)]
                subtitle_index = self._index_cache.get_or_build(
                    directory,
                    subtitle_files,
                )

                # Get candidate subtitles using SubtitleIndex
                candidate_subtitles: list[Path] = []

                # 1. Check hash-based matches (content hash)
                video_hash = self._extract_hash_from_name(video_name)
                if video_hash:
                    # Try to get content hash from video file if possible
                    # For now, use name-based hash matching
                    hash_matches = subtitle_index.get_by_hash(video_hash)
                    candidate_subtitles.extend(hash_matches)

                # 2. Check normalized name matches
                video_clean = self._clean_video_name(video_name)
                # Use SubtitleIndex's normalization (public method)
                normalized_video_name = subtitle_index.normalize_subtitle_name(
                    video_clean,
                )
                if normalized_video_name:
                    name_matches = subtitle_index.get_by_name(normalized_video_name)
                    candidate_subtitles.extend(name_matches)

                # 3. Check prefix matches
                if normalized_video_name:
                    prefix_matches = subtitle_index.get_by_name_prefix(
                        normalized_video_name,
                    )
                    candidate_subtitles.extend(prefix_matches)

                # Remove duplicates while preserving order
                seen = set()
                unique_candidates: list[Path] = []
                for path in candidate_subtitles:
                    if path not in seen:
                        seen.add(path)
                        unique_candidates.append(path)

                # Match within candidates only
                for subtitle_path in unique_candidates:
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

        # pylint: disable-next=broad-exception-caught

        # pylint: disable-next=broad-exception-caught

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


class SubtitleIndex:
    """Index for efficient subtitle file matching using content hash and normalized names.

    This class provides O(1) lookup for exact content matches and efficient filtering
    for similar filenames using normalized name indexing.

    Attributes:
        hash_index: Dictionary mapping content hashes to lists of subtitle file paths.
        name_index: Dictionary mapping normalized names to lists of subtitle file paths.

    Example:
        >>> index = SubtitleIndex()
        >>> subtitle_files = [Path("sub1.srt"), Path("sub2.srt")]
        >>> index.build_index(subtitle_files)
        >>> matches = index.get_by_hash("abc123...")
        >>> len(matches)
        1
    """

    def __init__(self) -> None:
        """Initialize an empty SubtitleIndex."""
        self.hash_index: dict[str, list[Path]] = {}
        self.name_index: dict[str, list[Path]] = {}

    def normalize_subtitle_name(self, name: str) -> str:
        """Normalize subtitle filename for indexing.

        This function removes common subtitle-specific patterns and standardizes
        the name for consistent matching.

        Args:
            name: Original filename (without extension) to normalize.

        Returns:
            Normalized name string.

        Example:
            >>> index = SubtitleIndex()
            >>> index.normalize_subtitle_name("Series.S01E01.[SubsPlease].srt")
            'series s01e01'
        """
        return self._normalize_subtitle_name(name)

    def _normalize_subtitle_name(self, name: str) -> str:
        """Internal normalization method.

        Args:
            name: Original filename (without extension) to normalize.

        Returns:
            Normalized name string.
        """
        if not name:
            return ""

        # Remove common subtitle-specific patterns
        patterns_to_remove = [
            r"\.(?:srt|smi|ass|ssa|vtt|sub)$",  # File extensions
            r"\[(?:sub|subs|subtitles)\]",  # Subtitle indicators
            r"\((?:sub|subs|subtitles)\)",
            r"\.(?:eng|kor|jpn|jap)",  # Language codes
            r"\[(?:eng|kor|jpn|jap)\]",
            r"\((?:eng|kor|jpn|jap)\)",
            r"\[[^\]]*\]",  # Any brackets
            r"\([^)]*\)",  # Any parentheses
        ]

        normalized = name.lower()
        for pattern in patterns_to_remove:
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

        # Remove special characters (keep only alphanumeric, Korean, and whitespace)
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized.strip()

    def build_index(self, subtitle_files: list[Path]) -> None:
        """Build hash_index and name_index from subtitle files.

        This method processes each subtitle file to:
        1. Calculate content hash and add to hash_index
        2. Normalize filename and add to name_index

        Args:
            subtitle_files: List of subtitle file paths to index.

        Example:
            >>> index = SubtitleIndex()
            >>> files = [Path("sub1.srt"), Path("sub2.srt")]
            >>> index.build_index(files)
            >>> len(index.hash_index)
            2
        """
        # Clear existing indices
        self.hash_index.clear()
        self.name_index.clear()

        for subtitle_file in subtitle_files:
            if not subtitle_file.exists():
                logger.warning("Subtitle file does not exist: %s", subtitle_file)
                continue

            try:
                # Build hash_index: content hash -> list of paths
                content_hash = calculate_file_hash(subtitle_file)
                if content_hash not in self.hash_index:
                    self.hash_index[content_hash] = []
                if subtitle_file not in self.hash_index[content_hash]:
                    self.hash_index[content_hash].append(subtitle_file)

                # Build name_index: normalized name -> list of paths
                normalized_name = self.normalize_subtitle_name(subtitle_file.stem)
                if normalized_name:
                    if normalized_name not in self.name_index:
                        self.name_index[normalized_name] = []
                    if subtitle_file not in self.name_index[normalized_name]:
                        self.name_index[normalized_name].append(subtitle_file)

            except (OSError, FileNotFoundError) as e:
                logger.warning(
                    "Failed to index subtitle file %s: %s",
                    subtitle_file,
                    e,
                )
                continue

        logger.debug(
            "Built SubtitleIndex: %d hash entries, %d name entries, %d total files",
            len(self.hash_index),
            len(self.name_index),
            len(subtitle_files),
        )

    def get_by_hash(self, content_hash: str) -> list[Path]:
        """Get subtitle files with the given content hash.

        Args:
            content_hash: SHA256 hash of the file content.

        Returns:
            List of subtitle file paths with matching content hash.
            Returns empty list if no matches found.

        Example:
            >>> index = SubtitleIndex()
            >>> index.build_index([Path("sub1.srt")])
            >>> matches = index.get_by_hash("abc123...")
            >>> len(matches)
            1
        """
        return self.hash_index.get(content_hash, []).copy()

    def get_by_name(self, normalized_name: str) -> list[Path]:
        """Get subtitle files with the given normalized name.

        Args:
            normalized_name: Normalized filename (should be normalized using _normalize_subtitle_name).

        Returns:
            List of subtitle file paths with matching normalized name.
            Returns empty list if no matches found.

        Example:
            >>> index = SubtitleIndex()
            >>> index.build_index([Path("Series.S01E01.srt")])
            >>> matches = index.get_by_name("series s01e01")
            >>> len(matches)
            1
        """
        return self.name_index.get(normalized_name, []).copy()

    def get_by_name_prefix(self, prefix: str) -> list[Path]:
        """Get subtitle files whose normalized names start with the given prefix.

        Args:
            prefix: Prefix to search for (should be normalized).

        Returns:
            List of subtitle file paths with matching prefix.
            Returns empty list if no matches found.

        Example:
            >>> index = SubtitleIndex()
            >>> index.build_index([Path("Series.S01E01.srt"), Path("Series.S01E02.srt")])
            >>> matches = index.get_by_name_prefix("series s01")
            >>> len(matches)
            2
        """
        matches: list[Path] = []
        for name, paths in self.name_index.items():
            if name.startswith(prefix):
                matches.extend(paths)
        return matches


@dataclass
class CachedSubtitleIndex:
    """Cached SubtitleIndex with metadata for cache validation."""

    index: SubtitleIndex
    directory_mtime: float
    cached_at: float


class SubtitleIndexCache:
    """Cache manager for SubtitleIndex objects.

    This class caches SubtitleIndex instances per directory to avoid
    repeated file system scans and hash calculations.

    Attributes:
        _cache: Dictionary mapping directory paths to CachedSubtitleIndex objects.

    Example:
        >>> cache = SubtitleIndexCache()
        >>> index = cache.get_or_build(Path("/path/to/dir"), subtitle_files)
        >>> # Second call returns cached index if directory unchanged
        >>> index2 = cache.get_or_build(Path("/path/to/dir"), subtitle_files)
    """

    def __init__(self) -> None:
        """Initialize an empty cache."""
        self._cache: dict[str, CachedSubtitleIndex] = {}

    def get_or_build(
        self,
        directory: Path,
        subtitle_files: list[Path],
    ) -> SubtitleIndex:
        """Get cached SubtitleIndex or build a new one.

        Checks if the directory has been modified since the last cache.
        If modified or cache miss, builds a new index and caches it.

        Args:
            directory: Directory path to cache for.
            subtitle_files: List of subtitle file paths in the directory.

        Returns:
            SubtitleIndex instance (cached or newly built).

        Example:
            >>> cache = SubtitleIndexCache()
            >>> files = [Path("sub1.srt"), Path("sub2.srt")]
            >>> index = cache.get_or_build(Path("/dir"), files)
        """
        directory_str = str(directory.resolve())

        # Check if we have a cached index
        if directory_str in self._cache:
            cached = self._cache[directory_str]

            # Check if directory has been modified
            try:
                current_mtime = directory.stat().st_mtime
                if current_mtime == cached.directory_mtime:
                    # Cache is valid, return cached index
                    logger.debug(
                        "Using cached SubtitleIndex for directory: %s",
                        directory,
                    )
                    return cached.index
                # Directory modified, invalidate cache
                logger.debug(
                    "Directory modified, invalidating cache for: %s",
                    directory,
                )
                del self._cache[directory_str]
            except OSError as e:
                # Directory access error, invalidate cache
                logger.warning(
                    "Error accessing directory %s, invalidating cache: %s",
                    directory,
                    e,
                )
                if directory_str in self._cache:
                    del self._cache[directory_str]

        # Build new index and cache it
        index = SubtitleIndex()
        index.build_index(subtitle_files)

        try:
            directory_mtime = directory.stat().st_mtime
        except OSError:
            # If we can't get mtime, use 0 (will always rebuild)
            directory_mtime = 0.0

        try:
            cached_at = directory.stat().st_mtime if directory.exists() else 0.0
        except OSError:
            cached_at = 0.0

        self._cache[directory_str] = CachedSubtitleIndex(
            index=index,
            directory_mtime=directory_mtime,
            cached_at=cached_at,
        )

        logger.debug(
            "Built and cached SubtitleIndex for directory: %s (%d files)",
            directory,
            len(subtitle_files),
        )

        return index

    def clear(self) -> None:
        """Clear all cached indices."""
        self._cache.clear()
        logger.debug("Cleared SubtitleIndex cache")

    def invalidate(self, directory: Path) -> None:
        """Invalidate cache for a specific directory.

        Args:
            directory: Directory path to invalidate.
        """
        directory_str = str(directory.resolve())
        if directory_str in self._cache:
            del self._cache[directory_str]
            logger.debug("Invalidated cache for directory: %s", directory)


def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file's contents using streaming.

    This function reads the file in chunks to minimize memory usage,
    making it suitable for large subtitle files.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Hexadecimal string representation of the SHA256 hash.

    Raises:
        OSError: If the file cannot be read.
        FileNotFoundError: If the file does not exist.

    Example:
        >>> from pathlib import Path
        >>> hash1 = calculate_file_hash(Path("subtitle1.srt"))
        >>> hash2 = calculate_file_hash(Path("subtitle2.srt"))
        >>> hash1 == hash2  # True if files have identical content
        True

    Note:
        Empty files will return a hash of the empty string:
        SHA256("") = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    """
    sha256_hash = hashlib.sha256()

    try:
        with file_path.open("rb") as f:
            # Read file in chunks to minimize memory usage
            while True:
                chunk = f.read(HASH_CHUNK_SIZE)
                if not chunk:
                    break
                sha256_hash.update(chunk)
    except FileNotFoundError:
        logger.error("File not found for hashing: %s", file_path)
        raise
    except OSError as e:
        logger.error("Error reading file for hashing %s: %s", file_path, e)
        raise

    return sha256_hash.hexdigest()


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
