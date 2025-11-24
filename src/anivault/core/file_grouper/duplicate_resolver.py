"""Duplicate file resolution module for AniVault.

This module provides functionality to resolve duplicate files by selecting
the best version based on version number, quality, and file size.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from anivault.core.models import ScannedFile

logger = logging.getLogger(__name__)


@dataclass
class ResolutionConfig:
    """Configuration for duplicate resolution strategies.

    Attributes:
        prefer_higher_version: If True, prefer files with higher version numbers.
                              Example: v2 > v1 > no version
        prefer_higher_quality: If True, prefer files with higher video quality.
                              Example: 1080p > 720p > 480p
        prefer_larger_size: If True, prefer files with larger file size.
                           Only used when version and quality are equal.
        quality_scores: Custom quality score mapping. If empty, uses defaults.
                       Example: {"2160p": 2160, "1080p": 1080}
    """

    prefer_higher_version: bool = True
    prefer_higher_quality: bool = True
    prefer_larger_size: bool = True
    quality_scores: dict[str, int] = field(default_factory=dict)


class DuplicateResolver:
    """Resolves duplicate files by selecting the best version.

    This class implements a multi-criteria selection algorithm:
    1. Version comparison: v2 > v1 > no version
    2. Quality comparison: 1080p > 720p > 480p > SD
    3. Size comparison: larger > smaller (fallback)

    Example:
        >>> from pathlib import Path
        >>> from anivault.core.models import ScannedFile
        >>> resolver = DuplicateResolver()
        >>> files = [
        ...     ScannedFile(file_path=Path("anime_ep01_v1_720p.mkv"), file_size=500_000_000),
        ...     ScannedFile(file_path=Path("anime_ep01_v2_1080p.mkv"), file_size=800_000_000),
        ... ]
        >>> best = resolver.resolve_duplicates(files)
        >>> best.file_path.name
        'anime_ep01_v2_1080p.mkv'
    """

    def __init__(self, config: ResolutionConfig | None = None) -> None:
        """Initialize the duplicate resolver.

        Args:
            config: Configuration for resolution strategies.
                   If None, uses default configuration.
        """
        self.config = config or ResolutionConfig()

        # Default quality score mapping
        self._default_quality_scores = {
            "8K": 7680,
            "4K": 3840,
            "UHD": 3840,
            "2160p": 2160,
            "1440p": 1440,
            "QHD": 1440,
            "FHD": 1080,
            "1080p": 1080,
            "HD": 720,
            "720p": 720,
            "480p": 480,
            "SD": 360,
        }

        # Merge custom quality scores with defaults
        self.quality_scores = {
            **self._default_quality_scores,
            **self.config.quality_scores,
        }

    def resolve_duplicates(self, files: list[ScannedFile]) -> ScannedFile:
        """Select the best file from a list of duplicates.

        Selection criteria (in order):
        1. Version number (v2 > v1 > no version)
        2. Video quality (1080p > 720p > 480p)
        3. File size (larger > smaller)

        Args:
            files: List of duplicate files to compare.

        Returns:
            The best file based on selection criteria.

        Raises:
            ValueError: If files list is empty.

        Example:
            >>> files = [
            ...     ScannedFile(file_path=Path("anime_v1.mkv"), file_size=500_000_000),
            ...     ScannedFile(file_path=Path("anime_v2.mkv"), file_size=600_000_000),
            ... ]
            >>> best = resolver.resolve_duplicates(files)
            >>> best.file_path.name
            'anime_v2.mkv'
        """
        if not files:
            raise ValueError("Cannot resolve duplicates: files list is empty")

        if len(files) == 1:
            return files[0]

        # Sort files by all criteria
        def comparison_key(file: ScannedFile) -> tuple[int, int, int]:
            """Generate comparison key for sorting.

            Returns:
                Tuple of (version, quality_score, file_size) for sorting.
                Higher values are considered better.
            """
            filename = file.file_path.name
            version = self._extract_version(filename) or 0
            quality_score = self._extract_quality(filename)
            file_size = file.file_size or 0

            # Apply configuration preferences
            if not self.config.prefer_higher_version:
                version = -version
            if not self.config.prefer_higher_quality:
                quality_score = -quality_score
            if not self.config.prefer_larger_size:
                file_size = -file_size

            return (version, quality_score, file_size)

        # Sort in descending order (best first)
        sorted_files = sorted(files, key=comparison_key, reverse=True)
        return sorted_files[0]

    def _extract_version(self, filename: str) -> int | None:
        """Extract version number from filename.

        Supports patterns:
        - _v1, _v2, .v1, .v2
        - [v1], (v2), {v3}
        - version1, version2
        - v1.0, v2.5 (extracts major version)

        Args:
            filename: Filename to extract version from.

        Returns:
            Version number (int) or None if not found.

        Example:
            >>> resolver._extract_version("anime_ep01_v2_1080p.mkv")
            2
            >>> resolver._extract_version("anime_[v3].mkv")
            3
            >>> resolver._extract_version("anime_version1.mkv")
            1
            >>> resolver._extract_version("anime_no_version.mkv")
            None
        """
        # Remove file extension
        name_without_ext = Path(filename).stem

        # Version patterns (in order of specificity)
        version_patterns = [
            r"[_.\-\s]v(\d+)",  # _v1, .v2, -v3, v4
            r"[\[\(\{]v(\d+)[\]\)\}]",  # [v1], (v2), {v3}
            r"version[_.\-\s]?(\d+)",  # version1, version_2, version.3
            r"ver[_.\-\s]?(\d+)",  # ver1, ver_2, ver.3
        ]

        for pattern in version_patterns:
            match = re.search(pattern, name_without_ext, re.IGNORECASE)
            if match:
                try:
                    version = int(match.group(1))
                    logger.debug(
                        "Extracted version %d from filename: %s",
                        version,
                        filename,
                    )
                    return version
                except (ValueError, IndexError):
                    continue

        logger.debug("No version found in filename: %s", filename)
        return None

    def _extract_quality(self, filename: str) -> int:
        """Extract quality score from filename.

        Maps quality tags to numeric scores for comparison:
        - 8K/7680p: 7680
        - 4K/2160p/UHD: 3840
        - 1440p/QHD: 1440
        - 1080p/FHD: 1080
        - 720p/HD: 720
        - 480p: 480
        - SD: 360
        - Unknown: 0

        Args:
            filename: Filename to extract quality from.

        Returns:
            Quality score (int). Higher score = better quality.
            Returns 0 if no quality tag found.

        Example:
            >>> resolver._extract_quality("anime_1080p.mkv")
            1080
            >>> resolver._extract_quality("anime_720p.mkv")
            720
            >>> resolver._extract_quality("anime_4K.mkv")
            3840
            >>> resolver._extract_quality("anime.mkv")
            0
        """
        # Check each quality pattern (sorted by score descending to match highest first)
        for quality_tag, score in sorted(self.quality_scores.items(), key=lambda x: x[1], reverse=True):
            # Build pattern that matches the quality tag (case-insensitive)
            # Match tag surrounded by delimiters or at boundaries
            escaped_tag = re.escape(quality_tag)
            # Match tag with word boundaries (considering underscore, dot, space as delimiters)
            pattern = rf"(?:^|[_.\-\s\[]){escaped_tag}(?:[_.\-\s\]]|$)"
            if re.search(pattern, filename, re.IGNORECASE):
                logger.debug(
                    "Extracted quality %s (score=%d) from filename: %s",
                    quality_tag,
                    score,
                    filename,
                )
                return score

        logger.debug("No quality tag found in filename: %s", filename)
        return 0


def resolve_duplicates(
    files: list[ScannedFile],
    config: ResolutionConfig | None = None,
) -> ScannedFile:
    """Convenience function to resolve duplicate files.

    Args:
        files: List of duplicate files to compare.
        config: Optional configuration for resolution strategies.

    Returns:
        The best file based on selection criteria.

    Raises:
        ValueError: If files list is empty.

    Example:
        >>> from pathlib import Path
        >>> files = [
        ...     ScannedFile(file_path=Path("anime_v1.mkv"), file_size=500_000_000),
        ...     ScannedFile(file_path=Path("anime_v2.mkv"), file_size=600_000_000),
        ... ]
        >>> best = resolve_duplicates(files)
        >>> best.file_path.name
        'anime_v2.mkv'
    """
    resolver = DuplicateResolver(config=config)
    return resolver.resolve_duplicates(files)
