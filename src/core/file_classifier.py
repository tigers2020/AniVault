"""
File classification system for anime files.

This module provides functionality to classify anime files based on resolution,
quality, and other criteria to determine the best file to keep when multiple
versions of the same content exist.
"""

import re
from dataclasses import dataclass
from enum import Enum

from .exceptions import FileClassificationError
from .models import AnimeFile


class ResolutionQuality(Enum):
    """Resolution quality levels in descending order of preference."""

    ULTRA_HD_4K = (3840, 2160, 10)  # 4K
    FULL_HD = (1920, 1080, 9)  # 1080p
    HD_READY = (1280, 720, 8)  # 720p
    SD = (854, 480, 7)  # 480p
    LOW_SD = (640, 360, 6)  # 360p
    VERY_LOW = (426, 240, 5)  # 240p
    UNKNOWN = (0, 0, 0)  # Unknown resolution


@dataclass
class FileClassification:
    """Classification result for an anime file."""

    file: AnimeFile
    resolution: ResolutionQuality
    width: int
    height: int
    file_size_mb: float
    quality_score: float
    classification_reason: str
    is_preferred: bool = False


class FileClassifier:
    """
    Classifies anime files based on resolution, quality, and other criteria.

    This class provides methods to:
    - Extract resolution information from filenames and metadata
    - Calculate quality scores for files
    - Determine the best file among multiple versions
    - Handle various resolution formats and naming conventions
    """

    # Common resolution patterns in filenames
    RESOLUTION_PATTERNS = [
        # 4K patterns
        (r"4[kK]", ResolutionQuality.ULTRA_HD_4K),
        (r"2160[pP]", ResolutionQuality.ULTRA_HD_4K),
        (r"3840x2160", ResolutionQuality.ULTRA_HD_4K),
        (r"UHD", ResolutionQuality.ULTRA_HD_4K),
        # 1080p patterns
        (r"1080[pP]", ResolutionQuality.FULL_HD),
        (r"1920x1080", ResolutionQuality.FULL_HD),
        (r"FHD", ResolutionQuality.FULL_HD),
        (r"FullHD", ResolutionQuality.FULL_HD),
        # 720p patterns
        (r"720[pP]", ResolutionQuality.HD_READY),
        (r"1280x720", ResolutionQuality.HD_READY),
        (r"HD", ResolutionQuality.HD_READY),
        # 480p patterns
        (r"480[pP]", ResolutionQuality.SD),
        (r"854x480", ResolutionQuality.SD),
        (r"SD", ResolutionQuality.SD),
        # 360p patterns
        (r"360[pP]", ResolutionQuality.LOW_SD),
        (r"640x360", ResolutionQuality.LOW_SD),
        # 240p patterns
        (r"240[pP]", ResolutionQuality.VERY_LOW),
        (r"426x240", ResolutionQuality.VERY_LOW),
    ]

    # Quality indicators that affect scoring
    QUALITY_INDICATORS = {
        "bluray": 1.2,
        "blu-ray": 1.2,
        "bd": 1.2,
        "webrip": 1.0,
        "web-dl": 1.1,
        "webdl": 1.1,
        "hdtv": 0.9,
        "dvdrip": 0.8,
        "dvd": 0.8,
        "cam": 0.5,
        "ts": 0.6,
        "tc": 0.6,
        "scr": 0.7,
        "workprint": 0.5,
    }

    # Codec quality indicators
    CODEC_QUALITY = {
        "x264": 1.0,
        "x265": 1.1,
        "h264": 1.0,
        "h265": 1.1,
        "hevc": 1.1,
        "avc": 1.0,
        "divx": 0.8,
        "xvid": 0.8,
    }

    def __init__(self) -> None:
        """Initialize the file classifier."""
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), quality)
            for pattern, quality in self.RESOLUTION_PATTERNS
        ]

    def classify_file(self, file: AnimeFile) -> FileClassification:
        """
        Classify a single anime file based on its properties.

        Args:
            file: The AnimeFile to classify

        Returns:
            FileClassification object with classification results

        Raises:
            FileClassificationError: If classification fails
        """
        try:
            # Extract resolution information
            resolution, width, height = self._extract_resolution(file)

            # Calculate file size in MB
            file_size_mb = file.file_size / (1024 * 1024)

            # Calculate quality score
            quality_score = self._calculate_quality_score(
                file, resolution, width, height, file_size_mb
            )

            # Determine classification reason
            reason = self._get_classification_reason(file, resolution, quality_score)

            return FileClassification(
                file=file,
                resolution=resolution,
                width=width,
                height=height,
                file_size_mb=file_size_mb,
                quality_score=quality_score,
                classification_reason=reason,
            )

        except Exception as e:
            raise FileClassificationError(
                f"Failed to classify file: {file.file_path}",
                str(file.file_path),
                "resolution_extraction",
                str(e),
            ) from e

    def classify_files(self, files: list[AnimeFile]) -> list[FileClassification]:
        """
        Classify multiple anime files.

        Args:
            files: List of AnimeFile objects to classify

        Returns:
            List of FileClassification objects
        """
        classifications = []
        for file in files:
            try:
                classification = self.classify_file(file)
                classifications.append(classification)
            except FileClassificationError as e:
                # Log error but continue with other files
                print(f"Warning: {e}")
                continue

        return classifications

    def find_best_file(self, files: list[AnimeFile]) -> AnimeFile | None:
        """
        Find the best file among multiple versions of the same content.

        Args:
            files: List of AnimeFile objects to compare

        Returns:
            The best AnimeFile, or None if no files could be classified
        """
        if not files:
            return None

        classifications = self.classify_files(files)
        if not classifications:
            return None

        # Sort by quality score (descending)
        classifications.sort(key=lambda x: x.quality_score, reverse=True)

        # Mark the best file as preferred
        best_classification = classifications[0]
        best_classification.is_preferred = True

        return best_classification.file

    def group_by_series(self, files: list[AnimeFile]) -> dict[str, list[AnimeFile]]:
        """
        Group files by series title for classification.

        Args:
            files: List of AnimeFile objects to group

        Returns:
            Dictionary mapping series titles to lists of files
        """
        groups: dict[str, list[AnimeFile]] = {}

        for file in files:
            if file.parsed_info and file.parsed_info.title:
                title = file.parsed_info.title.strip()
                if title not in groups:
                    groups[title] = []
                groups[title].append(file)
            else:
                # Use filename as fallback
                title = file.filename
                if title not in groups:
                    groups[title] = []
                groups[title].append(file)

        return groups

    def _extract_resolution(self, file: AnimeFile) -> tuple[ResolutionQuality, int, int]:
        """
        Extract resolution information from a file.

        Args:
            file: The AnimeFile to analyze

        Returns:
            Tuple of (ResolutionQuality, width, height)
        """
        # First try to get resolution from parsed info
        if file.parsed_info and file.parsed_info.resolution:
            if file.parsed_info.resolution_width and file.parsed_info.resolution_height:
                width = file.parsed_info.resolution_width
                height = file.parsed_info.resolution_height
                quality = self._get_quality_from_dimensions(width, height)
                return quality, width, height

        # Fall back to filename analysis
        filename = file.filename.lower()

        # Check for explicit resolution patterns
        for pattern, quality in self._compiled_patterns:
            match = pattern.search(filename)
            if match:
                width, height, _ = quality.value
                return quality, width, height

        # Try to extract dimensions from filename
        dimension_match = re.search(r"(\d{3,4})[xX](\d{3,4})", filename)
        if dimension_match:
            width = int(dimension_match.group(1))
            height = int(dimension_match.group(2))
            quality = self._get_quality_from_dimensions(width, height)
            return quality, width, height

        # Default to unknown resolution
        return ResolutionQuality.UNKNOWN, 0, 0

    def _get_quality_from_dimensions(self, width: int, height: int) -> ResolutionQuality:
        """
        Determine ResolutionQuality from width and height dimensions.

        Args:
            width: Video width in pixels
            height: Video height in pixels

        Returns:
            Appropriate ResolutionQuality enum value
        """
        for quality in ResolutionQuality:
            if quality == ResolutionQuality.UNKNOWN:
                continue
            q_width, q_height, _ = quality.value
            if width == q_width and height == q_height:
                return quality

        # If no exact match, find closest
        if width >= 3840 and height >= 2160:
            return ResolutionQuality.ULTRA_HD_4K
        elif width >= 1920 and height >= 1080:
            return ResolutionQuality.FULL_HD
        elif width >= 1280 and height >= 720:
            return ResolutionQuality.HD_READY
        elif width >= 854 and height >= 480:
            return ResolutionQuality.SD
        elif width >= 640 and height >= 360:
            return ResolutionQuality.LOW_SD
        elif width >= 426 and height >= 240:
            return ResolutionQuality.VERY_LOW

        return ResolutionQuality.UNKNOWN

    def _calculate_quality_score(
        self,
        file: AnimeFile,
        resolution: ResolutionQuality,
        width: int,
        height: int,
        file_size_mb: float,
    ) -> float:
        """
        Calculate a quality score for a file.

        Args:
            file: The AnimeFile to score
            resolution: The file's resolution quality
            width: Video width
            height: Video height
            file_size_mb: File size in MB

        Returns:
            Quality score (higher is better)
        """
        score = 0.0

        # Base score from resolution
        _, _, base_score = resolution.value
        score += base_score

        # File size factor (larger files generally better quality)
        if file_size_mb > 0:
            size_factor = min(file_size_mb / 1000, 2.0)  # Cap at 2.0
            score += size_factor

        # Quality indicators from filename
        filename = file.filename.lower()
        for indicator, multiplier in self.QUALITY_INDICATORS.items():
            if indicator in filename:
                score *= multiplier
                break

        # Codec quality
        for codec, multiplier in self.CODEC_QUALITY.items():
            if codec in filename:
                score *= multiplier
                break

        # Bonus for specific quality terms
        if any(term in filename for term in ["remux", "untouched", "lossless"]):
            score *= 1.3

        # Penalty for low quality terms
        if any(term in filename for term in ["cam", "ts", "tc", "workprint"]):
            score *= 0.5

        return max(score, 0.1)  # Ensure minimum score

    def _get_classification_reason(
        self, file: AnimeFile, resolution: ResolutionQuality, quality_score: float
    ) -> str:
        """
        Generate a human-readable reason for the classification.

        Args:
            file: The classified file
            resolution: The file's resolution
            quality_score: The calculated quality score

        Returns:
            String describing why the file was classified this way
        """
        reasons = []

        # Resolution reason
        if resolution != ResolutionQuality.UNKNOWN:
            width, height, _ = resolution.value
            reasons.append(f"{width}x{height} resolution")
        else:
            reasons.append("unknown resolution")

        # File size reason
        file_size_mb = file.file_size / (1024 * 1024)
        if file_size_mb > 1000:
            reasons.append(f"large file ({file_size_mb:.1f}MB)")
        elif file_size_mb < 100:
            reasons.append(f"small file ({file_size_mb:.1f}MB)")

        # Quality indicators
        filename = file.filename.lower()
        quality_terms = []
        for term in ["bluray", "webrip", "hdtv", "dvdrip"]:
            if term in filename:
                quality_terms.append(term)

        if quality_terms:
            reasons.append(f"quality: {', '.join(quality_terms)}")

        return "; ".join(reasons)
