"""Regex-based fallback parser for anime filenames.

This module provides a fallback parsing strategy using regular expressions
when the primary anitopy parser fails to extract essential information.
"""

from __future__ import annotations

import logging
import re
from re import Pattern
from typing import ClassVar

from anivault.core.constants import ParsingConfidence
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult

logger = logging.getLogger(__name__)


class FallbackParser:
    """Regex-based fallback parser for anime filenames.

    This parser uses a collection of regex patterns to extract metadata
    from anime filenames when the primary anitopy parser fails or produces
    low-confidence results.

    The parser operates in two stages:
    1. Primary patterns: Extract title, episode, and season
    2. Secondary patterns: Extract quality, codec, source, and other metadata
    """

    # Primary patterns for title, episode, and season extraction
    # Using named groups for clarity and easier extraction
    PATTERNS: ClassVar[list[Pattern[str]]] = [
        # Pattern 1: [Group] Title - Episode [Quality]
        re.compile(
            r"^\[(?P<group>[^\]]+)\]\s*"
            r"(?P<title>.+?)\s*-\s*"
            r"(?P<episode>\d+)"
            r"(?:\s+v\d+)?",
            re.IGNORECASE,
        ),
        # Pattern 2: Title S##E## [Quality]
        re.compile(
            r"^(?P<title>.+?)\s+S(?P<season>\d+)E(?P<episode>\d+)",
            re.IGNORECASE,
        ),
        # Pattern 3: Title - ##
        re.compile(r"^(?P<title>.+?)\s*-\s*(?P<episode>\d+)", re.IGNORECASE),
        # Pattern 4: Title EP## or Title Episode ##
        re.compile(
            r"^(?P<title>.+?)\s+(?:EP|Episode)\s*(?P<episode>\d+)",
            re.IGNORECASE,
        ),
        # Pattern 5: Title_##
        re.compile(r"^(?P<title>.+?)_(?P<episode>\d+)", re.IGNORECASE),
        # Pattern 6: Title.##
        re.compile(r"^(?P<title>.+?)\.(?P<episode>\d+)", re.IGNORECASE),
    ]

    # Secondary patterns for metadata extraction
    QUALITY_PATTERN = re.compile(r"\b(2160p|1080p|720p|480p|360p)\b", re.IGNORECASE)

    SOURCE_PATTERN = re.compile(
        r"\b(BluRay|Blu-ray|BDRip|WEB-?DL|WEBRip|HDTV|DVDRip)\b",
        re.IGNORECASE,
    )

    CODEC_PATTERN = re.compile(
        r"\b(H\.?264|H\.?265|HEVC|x264|x265|AVC|10bit|8bit)\b",
        re.IGNORECASE,
    )

    AUDIO_PATTERN = re.compile(r"\b(AAC|FLAC|MP3|DTS|AC3|5\.1|2\.0)\b", re.IGNORECASE)

    RELEASE_GROUP_PATTERN = re.compile(r"^\[([^\]]+)\]", re.IGNORECASE)

    def __init__(self) -> None:
        """Initialize the FallbackParser."""

    def parse(self, filename: str) -> ParsingResult:
        """Parse an anime filename using regex patterns.

        Args:
            filename: The anime filename to parse.

        Returns:
            ParsingResult containing extracted metadata with confidence score.

        Examples:
            >>> parser = FallbackParser()
            >>> result = parser.parse("[SubsPlease] Anime - 01 [1080p].mkv")
            >>> result.title
            'Anime'
            >>> result.episode
            1
        """
        # Try to find a match with primary patterns
        match = None

        for idx, pattern in enumerate(self.PATTERNS):
            match = pattern.search(filename)
            if match:
                logger.debug("Matched pattern %d for filename: %s", idx, filename)
                break

        # If no match found, return minimal result
        if not match:
            logger.warning("No pattern matched for filename: %s", filename)
            return ParsingResult(
                title=filename,
                confidence=ParsingConfidence.ERROR_CONFIDENCE_FALLBACK,
                parser_used="fallback",
                additional_info=ParsingAdditionalInfo(
                    parser_specific={"raw_filename": filename}
                ),
            )

        # Extract primary information from match
        result = self._extract_primary_info(match, filename)

        # Extract secondary information
        self._extract_secondary_info(result, filename)

        # Calculate confidence score
        result.confidence = self._calculate_confidence(result)
        result.parser_used = "fallback"

        logger.debug("Successfully parsed filename with fallback: %s", filename)

        return result

    def _extract_primary_info(
        self,
        match: re.Match[str],
        filename: str,
    ) -> ParsingResult:
        """Extract primary information (title, episode, season) from regex match.

        Args:
            match: Successful regex match object.
            filename: Original filename for reference.

        Returns:
            ParsingResult with primary fields populated.
        """
        groups = match.groupdict()

        # Extract title
        title = groups.get("title", "").strip()
        title = self._clean_title(title)

        # Extract episode number
        episode_str = groups.get("episode")
        episode = None
        if episode_str:
            try:
                episode = int(episode_str.lstrip("0") or "0")
            except ValueError:
                logger.warning("Failed to convert episode '%s' to int", episode_str)

        # Extract season number
        season_str = groups.get("season")
        season = None
        if season_str:
            try:
                season = int(season_str.lstrip("0") or "0")
            except ValueError:
                logger.warning("Failed to convert season '%s' to int", season_str)

        # Extract release group if present
        group = groups.get("group")

        return ParsingResult(
            title=title if title else filename,
            episode=episode,
            season=season,
            release_group=group,
        )

    def _extract_secondary_info(self, result: ParsingResult, filename: str) -> None:
        """Extract secondary metadata (quality, codec, source, etc.).

        Args:
            result: ParsingResult to populate with secondary info.
            filename: Original filename to search.
        """
        # Extract quality
        quality_match = self.QUALITY_PATTERN.search(filename)
        if quality_match:
            result.quality = quality_match.group(1)

        # Extract source
        source_match = self.SOURCE_PATTERN.search(filename)
        if source_match:
            result.source = source_match.group(1)

        # Extract codec
        codec_match = self.CODEC_PATTERN.search(filename)
        if codec_match:
            result.codec = codec_match.group(1)

        # Extract audio
        audio_match = self.AUDIO_PATTERN.search(filename)
        if audio_match:
            result.audio = audio_match.group(1)

        # Extract release group if not already found
        if not result.release_group:
            group_match = self.RELEASE_GROUP_PATTERN.search(filename)
            if group_match:
                result.release_group = group_match.group(1)

    def _clean_title(self, title: str) -> str:
        """Clean up extracted title by removing common artifacts.

        Args:
            title: Raw title string.

        Returns:
            Cleaned title string.
        """
        # Remove common separators at the end
        title = re.sub(r"[\.\-_\s]+$", "", title)

        # Replace underscores with spaces
        title = title.replace("_", " ")

        # Remove multiple spaces
        title = re.sub(r"\s+", " ", title)

        return title.strip()

    def _calculate_confidence(self, result: ParsingResult) -> float:
        """Calculate confidence score for the parsing result.

        Args:
            result: ParsingResult to score.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        confidence = 0.0

        # Title found
        if result.title and result.title.strip():
            confidence += ParsingConfidence.TITLE_FOUND_FALLBACK

        # Episode found
        if result.episode is not None:
            confidence += ParsingConfidence.EPISODE_FOUND

        # Season found
        if result.season is not None:
            confidence += ParsingConfidence.SEASON_FOUND

        # Metadata found
        if result.quality:
            confidence += ParsingConfidence.METADATA_BONUS
        if result.source:
            confidence += ParsingConfidence.METADATA_BONUS
        if result.codec:
            confidence += ParsingConfidence.METADATA_BONUS
        if result.release_group:
            confidence += ParsingConfidence.METADATA_BONUS

        return min(1.0, confidence)
