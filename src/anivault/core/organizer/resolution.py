"""Resolution analysis service for anime files.

This module provides the ResolutionAnalyzer class for detecting
and analyzing video resolutions in anime file collections.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, ClassVar

from anivault.core.data_structures.linked_hash_table import LinkedHashTable
from anivault.core.models import ScannedFile
from anivault.shared.constants import VideoQuality
from anivault.shared.constants.validation_constants import (
    EMPTY_SERIES_TITLE_ERROR,
    FHD_HEIGHT,
    FHD_WIDTH,
    HD_HEIGHT,
    HD_WIDTH,
    MIN_RESOLUTION_HEIGHT,
    MIN_RESOLUTION_WIDTH,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolutionSummary:
    """Summary of resolution analysis for a series.

    This immutable dataclass represents the resolution analysis result
    for a single anime series, containing information about whether
    the series has files with mixed resolutions.

    Attributes:
        series_title: Title of the series
        has_mixed_resolutions: Whether the series has both high and low resolution files
        resolutions: Set of resolution types found (True=high, False=low)
        file_count: Total number of files analyzed for this series
    """

    series_title: str
    has_mixed_resolutions: bool
    resolutions: frozenset[bool]  # True = high res, False = low res
    file_count: int

    def __post_init__(self) -> None:
        """Validate the resolution summary data."""
        if self.file_count < 0:
            msg = f"file_count must be non-negative, got {self.file_count}"
            raise ValueError(msg)
        if not self.series_title:
            raise ValueError(EMPTY_SERIES_TITLE_ERROR)


@dataclass(frozen=True)
class FileResolutionInfo:
    """Resolution information extracted from a single file.

    Attributes:
        series_title: Series title extracted from metadata or filename
        is_high_res: Whether the file is high resolution (True) or low (False)
        quality_string: Original quality string (e.g., "1080p", "720p")
        detection_method: How the resolution was detected
            ("tmdb_metadata", "tmdb_filename", "filename_only")  # pylint: disable=line-too-long
    """

    series_title: str
    is_high_res: bool
    quality_string: str
    detection_method: str


class ResolutionAnalyzer:
    """Analyzes video resolutions in anime file collections.

    This class detects resolutions from metadata and filenames,
    determining which series have mixed resolution types.

    The analysis follows a priority order:
    1. TMDB metadata quality field (most reliable)
    2. Filename resolution patterns for TMDB-matched files
    3. Filename-based title extraction + resolution patterns (fallback)

    Attributes:
        settings: Settings instance containing configuration
        logger: Logger instance for this analyzer
    """

    # Resolution detection patterns (shared across methods)
    RESOLUTION_PATTERNS: ClassVar[list[str]] = [
        r"\[(\d+p|4K|UHD|SD)\]",  # [1080p], [4K]
        r"\((\d+p|4K|UHD|SD)\)",  # (1080p), (4K)
        r"\b(\d+p|4K|UHD|SD)\b",  # 1080p, 4K (word boundary)
        r"(\d+p|4K|UHD|SD)\.",  # 1080p.mkv, 4K.mp4
        r"(\d+p|4K|UHD|SD)\s",  # 1080p BluRay, 4K HDR
        r"(\d+p|4K|UHD|SD)$",  # 1080p at end of filename
    ]

    DIMENSION_PATTERN: ClassVar[str] = r"(\d{3,4})\s*x\s*(\d{3,4})"

    def __init__(self, settings: Any = None) -> None:
        """Initialize the ResolutionAnalyzer.

        Args:
            settings: Settings instance containing configuration
        """
        self.settings = settings
        self.logger = logger

    def analyze_series(self, scanned_files: list[ScannedFile]) -> LinkedHashTable[str, ResolutionSummary]:
        """Analyze resolutions for all series in the file list.

        This method processes all scanned files, extracts resolution information,
        groups by series title, and determines which series have mixed resolutions.

        Args:
            scanned_files: List of ScannedFile objects to analyze

        Returns:
            LinkedHashTable mapping series titles to ResolutionSummary objects

        Example:
            >>> analyzer = ResolutionAnalyzer()
            >>> summaries = analyzer.analyze_series(scanned_files)
            >>> for title, summary in summaries:
            ...     if summary.has_mixed_resolutions:
            ...         print(f"{title} has mixed resolutions")
        """
        # Extract resolution info from all files
        resolution_infos: list[FileResolutionInfo] = []

        for scanned_file in scanned_files:
            info = self._extract_file_resolution(scanned_file)
            if info:
                resolution_infos.append(info)

        # Group by series title using LinkedHashTable for better performance
        series_resolutions: LinkedHashTable[str, set[bool]] = LinkedHashTable()
        series_file_counts: LinkedHashTable[str, int] = LinkedHashTable()

        for info in resolution_infos:
            # Get existing resolution set or create new one
            existing_resolutions = series_resolutions.get(info.series_title)
            if existing_resolutions is None:
                existing_resolutions = set()
                series_resolutions.put(info.series_title, existing_resolutions)
            existing_resolutions.add(info.is_high_res)

            # Increment file count
            existing_count = series_file_counts.get(info.series_title)
            if existing_count is None:
                existing_count = 0
            series_file_counts.put(info.series_title, existing_count + 1)

        # Create summaries using LinkedHashTable
        summaries: LinkedHashTable[str, ResolutionSummary] = LinkedHashTable()
        for series_title, res_types in series_resolutions:
            summaries.put(
                series_title,
                ResolutionSummary(
                    series_title=series_title,
                    has_mixed_resolutions=len(res_types) > 1,
                    resolutions=frozenset(res_types),
                    file_count=series_file_counts.get(series_title) or 0,
                ),
            )

        self.logger.debug(
            "Resolution analysis: %d series, %d with mixed resolutions",
            summaries.size,
            sum(1 for _, s in summaries if s.has_mixed_resolutions),
        )

        # Log detailed results for debugging
        for _, summary in summaries:
            self.logger.debug(
                "Series '%s': mixed=%s, resolutions=%s, files=%d",
                summary.series_title,
                summary.has_mixed_resolutions,
                sorted(summary.resolutions),
                summary.file_count,
            )

        return summaries

    def _extract_file_resolution(self, scanned_file: ScannedFile) -> FileResolutionInfo | None:
        """Extract resolution information from a single file.

        Tries multiple detection methods in priority order:
        1. TMDB metadata quality
        2. Filename pattern for TMDB-matched files
        3. Filename-only detection (with title extraction)

        Args:
            scanned_file: ScannedFile object to analyze

        Returns:
            FileResolutionInfo if successful, None if resolution cannot be determined
        """
        # Method 1: Try TMDB match result first (preferred)
        match_result = scanned_file.metadata.additional_info.match_result
        if match_result:
            series_title = match_result.title
            quality = scanned_file.metadata.quality

            # Try metadata quality first
            if quality:
                return self._detect_from_tmdb_metadata(
                    series_title=series_title,
                    quality=quality,
                )

            # Fallback: Extract from filename for TMDB-matched files
            filename = scanned_file.file_path.name
            resolution_info = self._detect_from_filename_pattern(filename)
            if resolution_info:
                quality_str, is_high_res = resolution_info
                return FileResolutionInfo(
                    series_title=series_title,
                    is_high_res=is_high_res,
                    quality_string=quality_str,
                    detection_method="tmdb_filename",
                )

        # Method 2: Fallback to filename-only detection
        filename = scanned_file.file_path.name
        title_info = self._extract_title_from_filename(filename)
        resolution_info = self._detect_from_filename_pattern(filename)

        if title_info and resolution_info:
            quality_str, is_high_res = resolution_info
            return FileResolutionInfo(
                series_title=title_info,
                is_high_res=is_high_res,
                quality_string=quality_str,
                detection_method="filename_only",
            )

        return None

    def _detect_from_tmdb_metadata(self, series_title: str, quality: str) -> FileResolutionInfo:
        """Detect resolution from TMDB metadata quality field.

        This is the most reliable method as it uses structured metadata
        from TMDB rather than parsing filenames.

        Args:
            series_title: Series title from TMDB match result
            quality: Quality string from metadata (e.g., "1080p", "720p")

        Returns:
            FileResolutionInfo with metadata-based detection
        """
        is_high_res = VideoQuality.is_high_resolution(quality)

        self.logger.debug(
            "TMDB metadata resolution: %s = %s (%s)",
            series_title,
            quality,
            "high" if is_high_res else "low",
        )

        return FileResolutionInfo(
            series_title=series_title,
            is_high_res=is_high_res,
            quality_string=quality,
            detection_method="tmdb_metadata",
        )

    def _detect_from_filename_pattern(self, filename: str) -> tuple[str, bool] | None:
        """Detect resolution from filename patterns.

        Tries multiple regex patterns to extract resolution information:
        1. Standard patterns: [1080p], (720p), 4K, etc.
        2. Dimension patterns: 1920x1080, 1280x720, etc.

        Args:
            filename: Filename to analyze

        Returns:
            Tuple of (quality_string, is_high_res) if found, None otherwise

        Example:
            >>> analyzer = ResolutionAnalyzer()
            >>> analyzer._detect_from_filename_pattern("Anime [1080p].mkv")
            ("1080P", True)
        """
        # Try standard resolution patterns first
        for pattern in self.RESOLUTION_PATTERNS:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                resolution = match.group(1).upper()
                is_high_res = VideoQuality.is_high_resolution(resolution)
                return (resolution, is_high_res)

        # Try dimension pattern (e.g., 1920x1080)
        dimension_match = re.search(self.DIMENSION_PATTERN, filename, re.IGNORECASE)
        if dimension_match:
            width = int(dimension_match.group(1))
            height = int(dimension_match.group(2))

            # Map dimensions to standard resolution
            resolution = self._map_dimensions_to_resolution(width, height)
            is_high_res = VideoQuality.is_high_resolution(resolution)
            return (resolution, is_high_res)

        return None

    def _map_dimensions_to_resolution(self, width: int, height: int) -> str:
        """Map video dimensions to standard resolution string.

        Args:
            width: Video width in pixels
            height: Video height in pixels

        Returns:
            Standard resolution string (e.g., "1080P", "720P", "SD")
        """
        if width >= FHD_WIDTH or height >= FHD_HEIGHT:
            return "1080P"
        if width >= HD_WIDTH or height >= HD_HEIGHT:
            return "720P"
        if width >= MIN_RESOLUTION_WIDTH or height >= MIN_RESOLUTION_HEIGHT:
            return "480P"
        return "SD"

    def _extract_title_from_filename(self, filename: str) -> str | None:
        """Extract series title from filename.

        Uses heuristics to extract the main title part from anime filenames,
        removing episode numbers, quality tags, and other metadata.

        Args:
            filename: Filename to analyze

        Returns:
            Extracted series title if found, None otherwise

        Example:
            >>> analyzer = ResolutionAnalyzer()
            >>> analyzer._extract_title_from_filename("[Group] Title - 01.mkv")
            "Title"
        """
        # Remove file extension for cleaner matching
        name_without_ext = filename

        # Pattern 1: [Group] Title - 01 style
        title_match = re.search(r"\[([^\]]+)\]|([^(]+?)(?:\s*\(\d+\)|\s*-\s*\d+)", name_without_ext)
        if title_match:
            series_title = title_match.group(1) or title_match.group(2)
            return series_title.strip()

        # Fallback: Use filename without extension
        # Remove common suffixes and clean up
        cleaned = re.sub(r"\s*-\s*\d+.*$", "", name_without_ext)
        cleaned = re.sub(r"\s*\(\d+\).*$", "", cleaned)
        return cleaned.strip() if cleaned else None
