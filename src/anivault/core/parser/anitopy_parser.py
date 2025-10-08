"""Anitopy-based filename parser for anime files.

This module provides a wrapper around the anitopy library, which is the
primary parsing engine for extracting metadata from anime filenames.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    import anitopy
except ImportError:
    anitopy = None

from anivault.core.parser.models import ParsingResult

logger = logging.getLogger(__name__)


class AnitopyParser:
    """Parser that wraps the anitopy library for anime filename parsing.

    This class serves as the primary parsing engine, leveraging the anitopy
    library to extract metadata from anime filenames. It translates anitopy's
    dictionary output into our standardized ParsingResult format.

    The parser handles common anime filename patterns including:
    - Release group names
    - Anime titles
    - Episode and season numbers
    - Quality/resolution markers
    - Video/audio codecs
    - Source information (BluRay, WEB, etc.)
    """

    def __init__(self) -> None:
        """Initialize the AnitopyParser.

        Raises:
            ImportError: If anitopy library is not installed.
        """
        if anitopy is None:
            raise ImportError(
                "anitopy library is not installed. "
                "Install it with: pip install anitopy",
            )

    def parse(self, filename: str) -> ParsingResult:
        """Parse an anime filename and extract metadata.

        Args:
            filename: The anime filename to parse (with or without extension).

        Returns:
            ParsingResult containing extracted metadata with confidence score.

        Examples:
            >>> parser = AnitopyParser()
            >>> result = parser.parse("[SubsPlease] Anime - 01 (1080p).mkv")
            >>> result.title
            'Anime'
            >>> result.episode
            1
        """
        try:
            # Call anitopy parser
            parsed = anitopy.parse(filename)

            # Convert anitopy output to our ParsingResult format
            result = self._convert_to_result(parsed, filename)

            logger.debug("Successfully parsed filename with anitopy: %s", filename)

            return result

        except (KeyError, ValueError, TypeError, AttributeError) as e:
            # Handle specific data processing errors
            logger.warning(
                "Anitopy failed to parse filename '%s' due to data processing error: %s",
                filename,
                str(e),
            )

            return ParsingResult(
                title=filename,
                confidence=0.1,
                parser_used="anitopy",
                other_info={"error": str(e), "raw_filename": filename},
            )
        except Exception as e:
            # Handle unexpected errors
            logger.exception(
                "Anitopy failed to parse filename '%s' due to unexpected error",
                filename,
            )

            return ParsingResult(
                title=filename,
                confidence=0.1,
                parser_used="anitopy",
                other_info={"error": str(e), "raw_filename": filename},
            )

    def _convert_to_result(
        self,
        parsed: dict[str, Any],
        original_filename: str,
    ) -> ParsingResult:
        """Convert anitopy's dictionary output to ParsingResult.

        Args:
            parsed: Dictionary output from anitopy.parse().
            original_filename: Original filename for reference.

        Returns:
            ParsingResult object with mapped fields and confidence score.
        """
        # Extract basic fields with direct mapping
        title = parsed.get("anime_title", "")
        release_group = parsed.get("release_group")
        quality = parsed.get("video_resolution")
        source = parsed.get("source")
        codec = parsed.get("video_term")
        audio = parsed.get("audio_term")

        # Extract and convert episode number
        episode = self._extract_episode_number(parsed)

        # Extract and convert season number
        season = self._extract_season_number(parsed)

        # Calculate confidence score
        confidence = self._calculate_confidence(title, episode, season, parsed)

        # Collect unmapped fields into other_info
        other_info = self._collect_other_info(parsed)

        return ParsingResult(
            title=title if title else original_filename,
            episode=episode,
            season=season,
            quality=quality,
            source=source,
            codec=codec,
            audio=audio,
            release_group=release_group,
            confidence=confidence,
            parser_used="anitopy",
            other_info=other_info,
        )

    def _extract_episode_number(self, parsed: dict[str, Any]) -> int | None:
        """Extract episode number from anitopy output.

        Args:
            parsed: Dictionary output from anitopy.

        Returns:
            Episode number as integer, or None if not found.
        """
        episode_raw = parsed.get("episode_number")

        if episode_raw is None:
            return None

        # Handle list of episodes (take the first one)
        if isinstance(episode_raw, list):
            episode_raw = episode_raw[0] if episode_raw else None

        if episode_raw is None:
            return None

        # Convert to integer
        try:
            # Remove leading zeros and convert
            return int(str(episode_raw).lstrip("0") or "0")
        except (ValueError, AttributeError):
            logger.warning("Failed to convert episode number: %s", episode_raw)
            return None

    def _extract_season_number(self, parsed: dict[str, Any]) -> int | None:
        """Extract season number from anitopy output.

        Args:
            parsed: Dictionary output from anitopy.

        Returns:
            Season number as integer, or None if not found.
        """
        season_raw = parsed.get("anime_season")

        if season_raw is None:
            return None

        # Convert to integer
        try:
            return int(str(season_raw).lstrip("0") or "0")
        except (ValueError, AttributeError):
            logger.warning("Failed to convert season number: %s", season_raw)
            return None

    def _calculate_confidence(
        self,
        title: str,
        episode: int | None,
        season: int | None,
        parsed: dict[str, Any],
    ) -> float:
        """Calculate confidence score based on extracted information.

        Args:
            title: Extracted anime title.
            episode: Extracted episode number.
            season: Extracted season number.
            parsed: Full anitopy output dictionary.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        # Start with base confidence
        confidence = 0.0

        # Title found
        if title and title.strip():
            confidence += 0.5

        # Episode number found
        if episode is not None:
            confidence += 0.3

        # Season number found
        if season is not None:
            confidence += 0.1

        # Additional metadata found
        metadata_fields = [
            "release_group",
            "video_resolution",
            "source",
            "video_term",
            "audio_term",
        ]
        found_metadata = sum(1 for field in metadata_fields if parsed.get(field))

        # Add small bonus for metadata (up to 0.1)
        confidence += min(0.1, found_metadata * 0.02)

        # Ensure confidence doesn't exceed 1.0
        return min(1.0, confidence)

    def _collect_other_info(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Collect unmapped fields from anitopy output.

        Args:
            parsed: Dictionary output from anitopy.

        Returns:
            Dictionary containing unmapped metadata.
        """
        # Fields that are already mapped to ParsingResult
        mapped_fields = {
            "anime_title",
            "episode_number",
            "anime_season",
            "video_resolution",
            "source",
            "video_term",
            "audio_term",
            "release_group",
        }

        # Collect all other fields
        return {key: value for key, value in parsed.items() if key not in mapped_fields}
