"""Path construction service for anime files.

This module provides the PathBuilder class for constructing
destination file paths based on metadata and naming conventions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from anivault.core.models import ScannedFile
from anivault.shared.constants.path_constants import PathConstants
from anivault.shared.models.metadata import TMDBMatchResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PathContext:
    """Context information for path construction.

    This immutable dataclass encapsulates all information needed
    to construct a destination path for a file.

    Attributes:
        scanned_file: The file to construct a path for
        series_has_mixed_resolutions: Whether the series has mixed resolutions
        target_folder: Root directory for organized files
        media_type: Type of media (e.g., "TV", "Movies")
        organize_path_template: Path template with placeholders:
            {해상도}, {연도}, {제목}, {시즌}
    """

    scanned_file: ScannedFile
    series_has_mixed_resolutions: bool
    target_folder: Path
    media_type: str
    organize_path_template: str

    def __post_init__(self) -> None:
        """Validate path context data."""
        if not self.target_folder:
            raise ValueError("target_folder cannot be empty")
        if not self.media_type:
            raise ValueError("media_type cannot be empty")


class PathBuilder:
    """Constructs destination paths for anime files.

    This class builds file paths based on metadata, naming conventions,
    and resolution information.

    Attributes:
        settings: Settings instance containing configuration
        logger: Logger instance for this builder
    """

    # Characters not allowed in filenames on most filesystems
    INVALID_FILENAME_CHARS = '<>:"/\\|?*'

    # Resolution detection patterns
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
        """Initialize the PathBuilder.

        Args:
            settings: Settings instance containing configuration
        """
        self.settings = settings
        self.logger = logger

    # Placeholder keys for path template
    PLACEHOLDER_RESOLUTION = "해상도"
    PLACEHOLDER_YEAR = "연도"
    PLACEHOLDER_TITLE = "제목"
    PLACEHOLDER_SEASON = "시즌"

    def build_path(self, context: PathContext) -> Path:
        """Build the destination path for a file.

        This method orchestrates the path construction process:
        1. Extract values for template placeholders
        2. Substitute placeholders in organize_path_template
        3. Combine with original filename

        Args:
            context: PathContext containing file and template

        Returns:
            Path object representing the destination path

        Example:
            Template "{해상도}/{연도}/{제목}/{시즌}" -> 1080p/2013/Attack on Titan/Season 01
        """
        # 1. Extract values for placeholders
        series_title = self._extract_series_title(context.scanned_file)
        series_title = self.sanitize_filename(series_title)
        season_number = self._extract_season_number(context.scanned_file)
        season_dir = self._build_season_dir(season_number)
        resolution = self._extract_resolution(context.scanned_file)
        year = self._extract_year_from_tmdb(context.scanned_file)

        # 2. Build folder structure from template
        series_dir = self._build_path_from_template(
            template=context.organize_path_template,
            series_title=series_title,
            season_dir=season_dir,
            resolution=resolution,
            year=year,
            target_folder=context.target_folder,
            media_type=context.media_type,
        )

        # 3. Use original filename
        original_filename = context.scanned_file.file_path.name
        return series_dir / original_filename

    def _extract_series_title(self, scanned_file: ScannedFile) -> str:
        """Extract series title from scanned file metadata.

        Priority order:
        1. TMDB matched title (most accurate)
        2. Parsed title from metadata
        3. Filename-based extraction
        4. Fallback to "Unknown Series"

        Args:
            scanned_file: ScannedFile to extract title from

        Returns:
            Series title string
        """
        metadata = scanned_file.metadata

        # Priority 1: TMDB matched title
        match_result = metadata.additional_info.match_result
        if isinstance(match_result, TMDBMatchResult):
            # Type narrowing: match_result is TMDBMatchResult, title is str
            return match_result.title

        # Priority 2: Parsed title
        if metadata.title and isinstance(metadata.title, str):
            return metadata.title

        # Priority 3: Extract from filename
        filename = scanned_file.file_path.name
        title_match = re.search(r"\[([^\]]+)\]|([^(]+?)(?:\s*\(\d+\)|\s*-\s*\d+)", filename)
        if title_match:
            extracted_title = (title_match.group(1) or title_match.group(2)).strip()
            if extracted_title:
                return extracted_title

        # Try filename stem as last resort
        stem = scanned_file.file_path.stem
        if stem:
            return stem

        # Fallback
        return PathConstants.UNKNOWN_SERIES

    def _extract_season_number(self, scanned_file: ScannedFile) -> int:
        """Extract season number from scanned file metadata.

        Args:
            scanned_file: ScannedFile to extract season from

        Returns:
            Season number (defaults to 1 if not specified)
        """
        season_number = scanned_file.metadata.season
        return season_number if season_number is not None else 1

    def _extract_year_from_tmdb(self, scanned_file: ScannedFile) -> int | None:
        """Extract year from TMDB match result.

        This method extracts the year from TMDB match result's year field,
        which is already processed from first_air_date or release_date.

        Args:
            scanned_file: ScannedFile to extract year from

        Returns:
            Year as integer, or None if not available

        Example:
            >>> builder = PathBuilder()
            >>> year = builder._extract_year_from_tmdb(scanned_file)
            >>> print(year)  # 2013
        """
        metadata = scanned_file.metadata
        match_result = metadata.additional_info.match_result

        if not isinstance(match_result, TMDBMatchResult):
            self.logger.debug(
                "Match result is not TMDBMatchResult: %s (expected for year extraction)",
                type(match_result).__name__ if match_result else "None",
            )
            return None

        # Use year field from MatchResult (already processed from date fields)
        year = match_result.year

        if year is None:
            self.logger.debug(
                "TMDBMatchResult.year is None for file: %s",
                scanned_file.file_path.name[:60],
            )
            return None

        # Sanity check: reasonable year range
        if not PathConstants.MIN_YEAR <= year <= PathConstants.MAX_YEAR:
            self.logger.warning(
                "Year %s is outside valid range [%s, %s] for file: %s",
                year,
                PathConstants.MIN_YEAR,
                PathConstants.MAX_YEAR,
                scanned_file.file_path.name[:60],
            )
            return None

        return year

    @staticmethod
    def _build_season_dir(season_number: int) -> str:
        """Build season directory string.

        Args:
            season_number: Season number

        Returns:
            Season directory string (e.g., "Season 01")
        """
        return f"Season {season_number:02d}"

    def _build_path_from_template(
        self,
        template: str,
        series_title: str,
        season_dir: str,
        resolution: str | None,
        year: int | None,
        target_folder: Path,
        media_type: str,
    ) -> Path:
        """Build folder path from template with placeholder substitution.

        Placeholders: {해상도}, {연도}, {제목}, {시즌}
        Missing values default to PathConstants.UNKNOWN.

        Args:
            template: Path template (e.g., "{해상도}/{연도}/{제목}/{시즌}")
            series_title: Sanitized series title
            season_dir: Season directory string (e.g., "Season 01")
            resolution: Resolution string or None
            year: Year as int or None
            target_folder: Root target folder
            media_type: Media type subfolder

        Returns:
            Path to the series directory (without filename)
        """
        values = {
            self.PLACEHOLDER_RESOLUTION: (resolution or PathConstants.UNKNOWN).lower(),
            self.PLACEHOLDER_YEAR: str(year) if year else PathConstants.UNKNOWN,
            self.PLACEHOLDER_TITLE: series_title,
            self.PLACEHOLDER_SEASON: season_dir,
        }
        # Substitute placeholders
        result = template
        for key, val in values.items():
            result = result.replace(f"{{{key}}}", val)
        # Remove any remaining unknown placeholders (replace with Unknown)
        result = re.sub(r"\{[^}]+\}", PathConstants.UNKNOWN, result)
        # Normalize path: strip slashes, collapse multiple slashes
        parts = [p for p in result.replace("\\", "/").split("/") if p.strip()]
        base = target_folder / media_type
        final_path = base / Path(*parts) if parts else base / series_title / season_dir
        self.logger.debug("Built path from template: %s -> %s", template, final_path)
        return final_path

    def _extract_resolution(self, scanned_file: ScannedFile) -> str | None:
        """Extract resolution from scanned file.

        Tries multiple methods in order:
        1. Metadata quality field (from TMDB)
        2. Filename pattern matching
        3. Dimension pattern matching

        Args:
            scanned_file: ScannedFile to extract resolution from

        Returns:
            Resolution string (e.g., "1080P", "720P") or None if not found
        """
        metadata = scanned_file.metadata

        # Try metadata quality field first
        normalized_quality = self._normalize_quality(metadata.quality)
        if normalized_quality:
            return normalized_quality.upper()

        # Extract from filename
        filename = scanned_file.file_path.name

        # Try standard resolution patterns
        for pattern in self.RESOLUTION_PATTERNS:
            resolution_match = re.search(pattern, filename, re.IGNORECASE)
            if resolution_match:
                resolution = resolution_match.group(1).upper()
                self.logger.debug(
                    "Extracted resolution from filename: %s = %s",
                    filename[:50] + "..." if len(filename) > 50 else filename,
                    resolution,
                )
                return resolution

        # Try dimension pattern (e.g., 1920x1080)
        dimension_match = re.search(self.DIMENSION_PATTERN, filename, re.IGNORECASE)
        if dimension_match:
            width = int(dimension_match.group(1))
            height = int(dimension_match.group(2))

            # Map dimension to standard resolution
            resolution = self._map_dimensions_to_resolution(width, height)
            self.logger.debug(
                "Extracted resolution from dimensions: %s = %s",
                filename[:50] + "..." if len(filename) > 50 else filename,
                resolution,
            )
            return resolution

        return None

    @staticmethod
    def _normalize_quality(value: object) -> str | None:
        """Normalize quality value to a string if possible."""
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, str) and item.strip():
                    return item
        return None

    @staticmethod
    def _map_dimensions_to_resolution(width: int, height: int) -> str:
        """Map video dimensions to standard resolution string.

        Args:
            width: Video width in pixels
            height: Video height in pixels

        Returns:
            Standard resolution string (e.g., "1080P", "720P", "SD")
        """
        if width >= PathConstants.HD_WIDTH or height >= PathConstants.HD_HEIGHT:
            return PathConstants.HD_LABEL
        if width >= PathConstants.SD_WIDTH or height >= PathConstants.SD_HEIGHT:
            return PathConstants.SD_LABEL
        if width >= PathConstants.LD_WIDTH or height >= PathConstants.LD_HEIGHT:
            return PathConstants.LD_LABEL
        return "SD"

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize a filename for Windows compatibility.

        Removes or replaces characters that are not allowed in Windows filenames.
        This implementation:
        - Replaces invalid characters with underscores
        - Converts underscores to spaces
        - Collapses multiple spaces into single space
        - Strips leading/trailing whitespace and dots
        - Ensures filename is not empty

        Args:
            filename: Original filename to sanitize

        Returns:
            Sanitized filename safe for Windows filesystems

        Example:
            >>> PathBuilder.sanitize_filename("Attack<>Titan?")
            "Attack  Titan "
            >>> PathBuilder.sanitize_filename("My_Series_Name")
            "My Series Name"
        """
        # Characters not allowed in filenames on most filesystems
        invalid_chars = PathBuilder.INVALID_FILENAME_CHARS

        # Replace invalid characters with underscores
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, "_")

        # Replace underscores with spaces
        sanitized = sanitized.replace("_", " ")

        # Replace multiple spaces with single space
        sanitized = re.sub(r"\s+", " ", sanitized)

        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(" .")

        # Ensure filename is not empty
        if not sanitized:
            sanitized = "Unknown"

        return sanitized
