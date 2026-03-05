"""Subtitle index for efficient matching using content hash and normalized names.

Extracted from subtitle_matcher.py for better code organization.
Provides O(1) lookup for exact matches and O(log n) prefix search.
"""

from __future__ import annotations

import bisect
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from anivault.core.subtitle_hash import calculate_file_hash

logger = logging.getLogger(__name__)


class SubtitleIndex:
    """Index for efficient subtitle file matching using content hash and normalized names.

    Attributes:
        hash_index: Mapping content hashes to lists of subtitle file paths.
        name_index: Mapping normalized names to lists of subtitle file paths.

    Example:
        >>> index = SubtitleIndex()
        >>> index.build_index([Path("sub1.srt"), Path("sub2.srt")])
        >>> matches = index.get_by_hash("abc123...")
    """

    def __init__(self) -> None:
        """Initialize an empty SubtitleIndex."""
        self.hash_index: dict[str, list[Path]] = {}
        self.name_index: dict[str, list[Path]] = {}
        self._sorted_name_keys: list[str] = []
        self.path_to_metadata: dict[Path, tuple[str, str]] = {}

    def normalize_subtitle_name(self, name: str) -> str:
        """Normalize subtitle filename for indexing."""
        return self._normalize_subtitle_name(name)

    def _normalize_subtitle_name(self, name: str) -> str:
        """Internal normalization method."""
        if not name:
            return ""

        patterns_to_remove = [
            r"\.(?:srt|smi|ass|ssa|vtt|sub)$",
            r"\[(?:sub|subs|subtitles)\]",
            r"\((?:sub|subs|subtitles)\)",
            r"\.(?:eng|kor|jpn|jap)",
            r"\[(?:eng|kor|jpn|jap)\]",
            r"\((?:eng|kor|jpn|jap)\)",
            r"\[[^\]]*\]",
            r"\([^)]*\)",
        ]

        normalized = name.lower()
        for pattern in patterns_to_remove:
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized.strip()

    def build_index(self, subtitle_files: list[Path]) -> None:
        """Build hash_index and name_index from subtitle files."""
        self.hash_index.clear()
        self.name_index.clear()
        self._sorted_name_keys.clear()

        for subtitle_file in subtitle_files:
            if not subtitle_file.exists():
                logger.warning("Subtitle file does not exist: %s", subtitle_file)
                continue

            try:
                content_hash = calculate_file_hash(subtitle_file)
                if content_hash not in self.hash_index:
                    self.hash_index[content_hash] = []
                if subtitle_file not in self.hash_index[content_hash]:
                    self.hash_index[content_hash].append(subtitle_file)

                normalized_name = self.normalize_subtitle_name(subtitle_file.stem)
                if normalized_name:
                    if normalized_name not in self.name_index:
                        self.name_index[normalized_name] = []
                    if subtitle_file not in self.name_index[normalized_name]:
                        self.name_index[normalized_name].append(subtitle_file)

                self.path_to_metadata[subtitle_file] = (content_hash, normalized_name)
            except (OSError, FileNotFoundError) as e:
                logger.warning(
                    "Failed to index subtitle file %s: %s",
                    subtitle_file,
                    e,
                )
                continue

        self._sorted_name_keys = sorted(self.name_index.keys())

        logger.debug(
            "Built SubtitleIndex: %d hash entries, %d name entries, %d total files",
            len(self.hash_index),
            len(self.name_index),
            len(subtitle_files),
        )

    def get_by_hash(self, content_hash: str) -> list[Path]:
        """Get subtitle files with the given content hash."""
        return self.hash_index.get(content_hash, []).copy()

    def get_by_name(self, normalized_name: str) -> list[Path]:
        """Get subtitle files with the given normalized name."""
        return self.name_index.get(normalized_name, []).copy()

    def get_by_name_prefix(self, prefix: str) -> list[Path]:
        """Get subtitle files whose normalized names start with the given prefix."""
        if not prefix or not self._sorted_name_keys:
            return []

        start_idx = bisect.bisect_left(self._sorted_name_keys, prefix)
        matches: list[Path] = []

        for i in range(start_idx, len(self._sorted_name_keys)):
            name = self._sorted_name_keys[i]
            if name.startswith(prefix):
                matches.extend(self.name_index[name])
            else:
                break

        return matches

    def add_file(self, subtitle_file: Path) -> None:
        """Add a subtitle file to the index (incremental update)."""
        if not subtitle_file.exists():
            logger.warning("Subtitle file does not exist: %s", subtitle_file)
            return

        if subtitle_file in self.path_to_metadata:
            logger.debug("Subtitle file already in index: %s", subtitle_file)
            return

        try:
            content_hash = calculate_file_hash(subtitle_file)
            if content_hash not in self.hash_index:
                self.hash_index[content_hash] = []
            if subtitle_file not in self.hash_index[content_hash]:
                self.hash_index[content_hash].append(subtitle_file)

            normalized_name = self.normalize_subtitle_name(subtitle_file.stem)
            if normalized_name:
                is_new_name = normalized_name not in self.name_index
                if is_new_name:
                    self.name_index[normalized_name] = []
                if subtitle_file not in self.name_index[normalized_name]:
                    self.name_index[normalized_name].append(subtitle_file)
                    if is_new_name:
                        bisect.insort(self._sorted_name_keys, normalized_name)

            self.path_to_metadata[subtitle_file] = (content_hash, normalized_name)
            logger.debug("Added subtitle file to index: %s", subtitle_file)

        except (OSError, FileNotFoundError) as e:
            logger.warning(
                "Failed to add subtitle file to index %s: %s",
                subtitle_file,
                e,
            )

    def remove_file(self, subtitle_file: Path) -> None:
        """Remove a subtitle file from the index (incremental update)."""
        metadata = self.path_to_metadata.get(subtitle_file)
        if metadata is None:
            logger.debug("Subtitle file not in index: %s", subtitle_file)
            return

        content_hash, normalized_name = metadata

        if content_hash in self.hash_index:
            if subtitle_file in self.hash_index[content_hash]:
                self.hash_index[content_hash].remove(subtitle_file)
            if not self.hash_index[content_hash]:
                del self.hash_index[content_hash]

        if normalized_name and normalized_name in self.name_index:
            if subtitle_file in self.name_index[normalized_name]:
                self.name_index[normalized_name].remove(subtitle_file)
            if not self.name_index[normalized_name]:
                del self.name_index[normalized_name]
                if normalized_name in self._sorted_name_keys:
                    self._sorted_name_keys.remove(normalized_name)

        self.path_to_metadata.pop(subtitle_file, None)
        logger.debug("Removed subtitle file from index: %s", subtitle_file)


@dataclass
class CachedSubtitleIndex:
    """Cached SubtitleIndex with metadata for cache validation."""

    index: SubtitleIndex
    directory_mtime: float
    cached_at: float


class SubtitleIndexCache:
    """Cache manager for SubtitleIndex objects per directory."""

    def __init__(self) -> None:
        """Initialize an empty cache."""
        self._cache: dict[str, CachedSubtitleIndex] = {}

    def get_or_build(
        self,
        directory: Path,
        subtitle_files: list[Path],
    ) -> SubtitleIndex:
        """Get cached SubtitleIndex or build a new one."""
        directory_str = str(directory.resolve())

        if directory_str in self._cache:
            cached = self._cache[directory_str]

            try:
                current_mtime = directory.stat().st_mtime
                if current_mtime == cached.directory_mtime:
                    logger.debug(
                        "Using cached SubtitleIndex for directory: %s",
                        directory,
                    )
                    return cached.index
                logger.debug(
                    "Directory modified, invalidating cache for: %s",
                    directory,
                )
                del self._cache[directory_str]
            except OSError as e:
                logger.warning(
                    "Error accessing directory %s, invalidating cache: %s",
                    directory,
                    e,
                )
                if directory_str in self._cache:
                    del self._cache[directory_str]

        index = SubtitleIndex()
        index.build_index(subtitle_files)

        try:
            directory_mtime = directory.stat().st_mtime
        except OSError:
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

    def get(self, directory: Path) -> SubtitleIndex | None:
        """Get cached SubtitleIndex for a directory if available."""
        directory_str = str(directory.resolve())
        cached = self._cache.get(directory_str)
        return cached.index if cached else None

    def clear(self) -> None:
        """Clear all cached indices."""
        self._cache.clear()
        logger.debug("Cleared SubtitleIndex cache")

    def invalidate(self, directory: Path) -> None:
        """Invalidate cache for a specific directory."""
        directory_str = str(directory.resolve())
        if directory_str in self._cache:
            del self._cache[directory_str]
            logger.debug("Invalidated cache for directory: %s", directory)


__all__ = [
    "CachedSubtitleIndex",
    "SubtitleIndex",
    "SubtitleIndexCache",
]
