"""
Validation logic for parsed anime information.

This module provides comprehensive validation and normalization functions
for parsed anime data to ensure data quality and consistency.
"""

import re
from dataclasses import dataclass
from typing import Any

from src.core.models import ParsedAnimeInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    normalized_data: dict[str, Any] | None = None


class AnimeDataValidator:
    """
    Validates and normalizes parsed anime information.

    Provides comprehensive validation for all aspects of parsed anime data
    including title validation, episode/season validation, resolution validation,
    and overall data consistency checks.
    """

    def __init__(self) -> None:
        """Initialize the validator."""
        # Common patterns for validation
        self.title_patterns = {
            "invalid_chars": re.compile(r'[<>:"/\\|?*]'),
            "multiple_spaces": re.compile(r"\s{2,}"),
            "leading_trailing_spaces": re.compile(r"^\s+|\s+$"),
        }

        # Valid video codecs
        self.valid_video_codecs = {
            "H264",
            "H.264",
            "x264",
            "AVC",
            "H265",
            "H.265",
            "x265",
            "HEVC",
            "VP9",
            "VP8",
            "AV1",
            "XVID",
            "DIVX",
            "WMV",
            "MPEG",
        }

        # Valid audio codecs
        self.valid_audio_codecs = {
            "AAC",
            "MP3",
            "FLAC",
            "AC3",
            "AC-3",
            "DTS",
            "DTS-HD",
            "TrueHD",
            "PCM",
            "OGG",
            "VORBIS",
            "OPUS",
        }

        # Valid sources
        self.valid_sources = {
            "Blu-ray",
            "BluRay",
            "BDRip",
            "BRRip",
            "Web",
            "WebRip",
            "WEB-DL",
            "WEBRip",
            "HDTV",
            "TV",
            "DVD",
            "DVDRip",
            "CAM",
            "TS",
            "TC",
            "R5",
            "R6",
        }

    def validate_title(self, title: str) -> tuple[bool, list[str], str]:
        """
        Validate and normalize anime title.

        Args:
            title: Raw title string

        Returns:
            Tuple of (is_valid, errors, normalized_title)
        """
        errors = []

        if not title:
            errors.append("Title cannot be empty")
            return False, errors, ""

        # Check for invalid characters
        if self.title_patterns["invalid_chars"].search(title):
            errors.append("Title contains invalid characters")

        # Normalize title
        normalized = title.strip()

        # Remove multiple spaces
        normalized = self.title_patterns["multiple_spaces"].sub(" ", normalized)

        # Check minimum length
        if len(normalized) < 2:
            errors.append("Title is too short")

        # Check maximum length (reasonable limit)
        if len(normalized) > 200:
            errors.append("Title is too long")

        return len(errors) == 0, errors, normalized

    def validate_episode_number(
        self, episode: int | None
    ) -> tuple[bool, list[str], int | None]:
        """
        Validate episode number.

        Args:
            episode: Episode number to validate

        Returns:
            Tuple of (is_valid, errors, normalized_episode)
        """
        errors = []

        if episode is None:
            return True, errors, None

        if not isinstance(episode, int):
            errors.append("Episode number must be an integer")
            return False, errors, None

        if episode < 0:
            errors.append("Episode number cannot be negative")

        if episode > 10000:  # Reasonable upper limit
            errors.append("Episode number is unreasonably high")

        return len(errors) == 0, errors, episode

    def validate_season_number(
        self, season: int | None
    ) -> tuple[bool, list[str], int | None]:
        """
        Validate season number.

        Args:
            season: Season number to validate

        Returns:
            Tuple of (is_valid, errors, normalized_season)
        """
        errors = []

        if season is None:
            return True, errors, None

        if not isinstance(season, int):
            errors.append("Season number must be an integer")
            return False, errors, None

        if season < 0:
            errors.append("Season number cannot be negative")

        if season > 100:  # Reasonable upper limit
            errors.append("Season number is unreasonably high")

        return len(errors) == 0, errors, season

    def validate_resolution(
        self, resolution: str | None, width: int | None, height: int | None
    ) -> tuple[bool, list[str], tuple[str | None, int | None, int | None]]:
        """
        Validate resolution information.

        Args:
            resolution: Resolution string (e.g., '1080p')
            width: Width in pixels
            height: Height in pixels

        Returns:
            Tuple of (is_valid, errors, (normalized_resolution, normalized_width, normalized_height))
        """
        errors = []
        warnings = []

        # If no resolution info, that's valid
        if not resolution and width is None and height is None:
            return True, errors, (None, None, None)

        # Validate width and height if provided
        if width is not None:
            if not isinstance(width, int) or width <= 0:
                errors.append("Width must be a positive integer")
            elif width > 7680:  # 8K width
                warnings.append("Width is very high, may be incorrect")

        if height is not None:
            if not isinstance(height, int) or height <= 0:
                errors.append("Height must be a positive integer")
            elif height > 4320:  # 8K height
                warnings.append("Height is very high, may be incorrect")

        # Check consistency between width and height
        if width is not None and height is not None:
            aspect_ratio = width / height
            if aspect_ratio < 1.0:  # Portrait mode
                warnings.append("Unusual aspect ratio detected (portrait)")
            elif aspect_ratio > 3.0:  # Very wide
                warnings.append("Unusual aspect ratio detected (very wide)")

        # Validate resolution string format
        if resolution:
            if not re.match(r"^\d+[pP]|^\d+[xX]\d+$|^4[kK]$", resolution):
                warnings.append("Resolution string format may be non-standard")

        return len(errors) == 0, errors + warnings, (resolution, width, height)

    def validate_codec(
        self, codec: str | None, codec_type: str
    ) -> tuple[bool, list[str], str | None]:
        """
        Validate video or audio codec.

        Args:
            codec: Codec string to validate
            codec_type: Type of codec ('video' or 'audio')

        Returns:
            Tuple of (is_valid, errors, normalized_codec)
        """
        errors = []

        if not codec:
            return True, errors, None

        codec_upper = codec.upper()
        valid_codecs = self.valid_video_codecs if codec_type == "video" else self.valid_audio_codecs

        if codec_upper not in valid_codecs:
            errors.append(f"Unknown {codec_type} codec: {codec}")

        return len(errors) == 0, errors, codec_upper

    def validate_year(self, year: int | None) -> tuple[bool, list[str], int | None]:
        """
        Validate release year.

        Args:
            year: Year to validate

        Returns:
            Tuple of (is_valid, errors, normalized_year)
        """
        errors = []

        if year is None:
            return True, errors, None

        if not isinstance(year, int):
            errors.append("Year must be an integer")
            return False, errors, None

        if year < 1900:
            errors.append("Year is too early for anime")

        if year > 2030:  # Reasonable future limit
            errors.append("Year is in the far future")

        return len(errors) == 0, errors, year

    def validate_source(self, source: str | None) -> tuple[bool, list[str], str | None]:
        """
        Validate source type.

        Args:
            source: Source string to validate

        Returns:
            Tuple of (is_valid, errors, normalized_source)
        """
        errors = []

        if not source:
            return True, errors, None

        source_normalized = source.strip()

        if source_normalized.upper() not in {s.upper() for s in self.valid_sources}:
            errors.append(f"Unknown source type: {source}")

        return len(errors) == 0, errors, source_normalized

    def validate_parsed_info(self, parsed_info: ParsedAnimeInfo) -> ValidationResult:
        """
        Comprehensive validation of ParsedAnimeInfo.

        Args:
            parsed_info: ParsedAnimeInfo object to validate

        Returns:
            ValidationResult with validation status and details
        """
        errors = []
        warnings = []
        normalized_data = {}

        # Validate title
        title_valid, title_errors, normalized_title = self.validate_title(parsed_info.title)
        errors.extend(title_errors)
        normalized_data["title"] = normalized_title

        # Validate episode number
        episode_valid, episode_errors, normalized_episode = self.validate_episode_number(
            parsed_info.episode
        )
        errors.extend(episode_errors)
        normalized_data["episode"] = normalized_episode

        # Validate season number
        season_valid, season_errors, normalized_season = self.validate_season_number(
            parsed_info.season
        )
        errors.extend(season_errors)
        normalized_data["season"] = normalized_season

        # Validate resolution
        res_valid, res_errors, (norm_res, norm_width, norm_height) = self.validate_resolution(
            parsed_info.resolution, parsed_info.resolution_width, parsed_info.resolution_height
        )
        errors.extend(res_errors)
        normalized_data["resolution"] = norm_res
        normalized_data["resolution_width"] = norm_width
        normalized_data["resolution_height"] = norm_height

        # Validate video codec
        vcodec_valid, vcodec_errors, normalized_vcodec = self.validate_codec(
            parsed_info.video_codec, "video"
        )
        errors.extend(vcodec_errors)
        normalized_data["video_codec"] = normalized_vcodec

        # Validate audio codec
        acodec_valid, acodec_errors, normalized_acodec = self.validate_codec(
            parsed_info.audio_codec, "audio"
        )
        errors.extend(acodec_errors)
        normalized_data["audio_codec"] = normalized_acodec

        # Validate year
        year_valid, year_errors, normalized_year = self.validate_year(parsed_info.year)
        errors.extend(year_errors)
        normalized_data["year"] = normalized_year

        # Validate source
        source_valid, source_errors, normalized_source = self.validate_source(parsed_info.source)
        errors.extend(source_errors)
        normalized_data["source"] = normalized_source

        # Additional consistency checks
        if parsed_info.is_movie and (
            parsed_info.season is not None or parsed_info.episode is not None
        ):
            warnings.append("Movie detected but has season/episode information")

        if parsed_info.is_tv_series and parsed_info.season is None and parsed_info.episode is None:
            warnings.append("TV series detected but no season/episode information")

        # Check for missing critical information
        if not parsed_info.title:
            errors.append("Title is required")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            normalized_data=normalized_data if is_valid else None,
        )

    def normalize_parsed_info(self, parsed_info: ParsedAnimeInfo) -> ParsedAnimeInfo:
        """
        Normalize a ParsedAnimeInfo object based on validation results.

        Args:
            parsed_info: ParsedAnimeInfo object to normalize

        Returns:
            Normalized ParsedAnimeInfo object
        """
        validation_result = self.validate_parsed_info(parsed_info)

        if not validation_result.is_valid:
            logger.warning(f"Validation failed for {parsed_info.title}: {validation_result.errors}")
            return parsed_info

        if validation_result.normalized_data:
            # Create new ParsedAnimeInfo with normalized data
            return ParsedAnimeInfo(
                title=validation_result.normalized_data.get("title", parsed_info.title),
                season=validation_result.normalized_data.get("season", parsed_info.season),
                episode=validation_result.normalized_data.get("episode", parsed_info.episode),
                episode_title=parsed_info.episode_title,
                resolution=validation_result.normalized_data.get(
                    "resolution", parsed_info.resolution
                ),
                resolution_width=validation_result.normalized_data.get(
                    "resolution_width", parsed_info.resolution_width
                ),
                resolution_height=validation_result.normalized_data.get(
                    "resolution_height", parsed_info.resolution_height
                ),
                video_codec=validation_result.normalized_data.get(
                    "video_codec", parsed_info.video_codec
                ),
                audio_codec=validation_result.normalized_data.get(
                    "audio_codec", parsed_info.audio_codec
                ),
                release_group=parsed_info.release_group,
                file_extension=parsed_info.file_extension,
                year=validation_result.normalized_data.get("year", parsed_info.year),
                source=validation_result.normalized_data.get("source", parsed_info.source),
                raw_data=parsed_info.raw_data,
            )

        return parsed_info
