"""Filename parser module for AniVault.

This module provides a unified filename parsing system that uses anitopy as the primary
parser and falls back to the parse library for filenames that anitopy cannot handle.
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional

import anitopy
import parse

from anivault.core.logging import get_logger

logger = get_logger(__name__)


class ParsedAnimeInfo:
    """Container for parsed anime information.

    This class holds all the metadata extracted from an anime filename,
    including information about which parser was used.
    """

    def __init__(
        self,
        filename: str,
        anime_title: Optional[str] = None,
        episode_number: Optional[str] = None,
        episode_title: Optional[str] = None,
        season: Optional[int] = None,
        year: Optional[int] = None,
        release_group: Optional[str] = None,
        video_resolution: Optional[str] = None,
        video_term: Optional[str] = None,
        audio_term: Optional[str] = None,
        file_extension: Optional[str] = None,
        parser_used: str = "none",
        raw_data: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
    ) -> None:
        """Initialize ParsedAnimeInfo.

        Args:
            filename: Original filename that was parsed.
            anime_title: Extracted anime title.
            episode_number: Episode number(s).
            episode_title: Episode title.
            season: Season number.
            year: Release year.
            release_group: Release group name.
            video_resolution: Video resolution.
            video_term: Video-related terms.
            audio_term: Audio-related terms.
            file_extension: File extension.
            parser_used: Which parser was used ("anitopy", "fallback", or "none").
            raw_data: Raw parsing data from the parser.
            confidence: Confidence score (0.0 to 1.0).
        """
        self.filename = filename
        self.anime_title = anime_title
        self.episode_number = episode_number
        self.episode_title = episode_title
        self.season = season
        self.year = year
        self.release_group = release_group
        self.video_resolution = video_resolution
        self.video_term = video_term
        self.audio_term = audio_term
        self.file_extension = file_extension
        self.parser_used = parser_used
        self.raw_data = raw_data or {}
        self.confidence = confidence

    @property
    def is_parsed(self) -> bool:
        """Check if parsing was successful.

        Returns:
            True if parsing was successful, False otherwise.
        """
        return self.parser_used != "none" and self.anime_title is not None

    @property
    def has_episode_info(self) -> bool:
        """Check if episode information is available.

        Returns:
            True if episode number or title is available, False otherwise.
        """
        return bool(self.episode_number or self.episode_title)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary representation of the parsed information.
        """
        return {
            "filename": self.filename,
            "anime_title": self.anime_title,
            "episode_number": self.episode_number,
            "episode_title": self.episode_title,
            "season": self.season,
            "year": self.year,
            "release_group": self.release_group,
            "video_resolution": self.video_resolution,
            "video_term": self.video_term,
            "audio_term": self.audio_term,
            "file_extension": self.file_extension,
            "parser_used": self.parser_used,
            "raw_data": self.raw_data,
            "confidence": self.confidence,
            "is_parsed": self.is_parsed,
            "has_episode_info": self.has_episode_info,
        }


class FallbackParser:
    """Fallback parser using the parse library for anitopy failures.

    This class provides fallback parsing capabilities using the parse library
    with predefined patterns for common anime filename formats.
    """

    def __init__(self) -> None:
        """Initialize the fallback parser with common patterns."""
        # Common anime filename patterns using parse library format
        # Order matters: more specific patterns should come first
        self.patterns = [
            # Season/Episode format: Title S##E## [Release Group] [Quality]
            "{title} S{season:d}E{episode} [{release_group}] [{quality}]",
            "{title} Season {season:d} Episode {episode} [{release_group}] [{quality}]",
            # Underscore format: Title_Season_Episode_[Release_Group]_[Quality]
            "{title}_{season:d}_{episode}_{release_group}_{quality}",
            "{title}_S{season:d}E{episode}_{release_group}_{quality}",
            # Standard format: Title - Episode - [Release Group] - [Quality]
            "{title} - Episode {episode} - [{release_group}] - [{quality}]",
            "{title} - {episode} - [{release_group}] - [{quality}]",
            "{title} - E{episode} - [{release_group}] - [{quality}]",
            # Bracket format: [Release Group] Title - Episode [Quality]
            "[{release_group}] {title} - Episode {episode} [{quality}]",
            "[{release_group}] {title} - {episode} [{quality}]",
            # Quality-first format: [Quality] Title - Episode [Release Group]
            "[{quality}] {title} - Episode {episode} [{release_group}]",
            "[{quality}] {title} - {episode} [{release_group}]",
            # Year format: Title (Year) - Episode
            "{title} ({year:d}) - Episode {episode}",
            "{title} ({year:d}) - {episode}",
            # Simple format: Title Episode (most specific first)
            "{title} Episode {episode}",
            "{title} {episode}",
        ]

    def parse(self, filename: str) -> Optional[ParsedAnimeInfo]:
        """Parse filename using fallback patterns.

        Args:
            filename: Filename to parse.

        Returns:
            ParsedAnimeInfo if parsing succeeds, None otherwise.
        """
        # Remove file extension for parsing
        filename_without_ext = Path(filename).stem
        file_extension = Path(filename).suffix.lower()

        # Try each pattern
        for pattern in self.patterns:
            try:
                result = parse.parse(pattern, filename_without_ext)
                if result is not None:
                    logger.debug(f"Fallback parser matched pattern: {pattern}")

                    # Extract information from parsed result
                    anime_title = result.named.get("title", "").strip()
                    episode_number = result.named.get("episode", "").strip()
                    episode_title = result.named.get("episode_title", "").strip()
                    season = result.named.get("season")
                    year = result.named.get("year")
                    release_group = result.named.get("release_group", "").strip()
                    quality = result.named.get("quality", "").strip()

                    # Clean up title
                    if anime_title:
                        anime_title = self._clean_title(anime_title)

                    # Clean up episode number (remove "Episode" prefix if present)
                    if episode_number and episode_number.lower().startswith("episode "):
                        episode_number = episode_number[8:].strip()

                    # Extract video resolution from quality
                    video_resolution = self._extract_resolution(quality)
                    if not video_resolution and quality:
                        # If no resolution found but we have quality info, use it
                        video_resolution = quality

                    # Create ParsedAnimeInfo
                    parsed_info = ParsedAnimeInfo(
                        filename=filename,
                        anime_title=anime_title if anime_title else None,
                        episode_number=episode_number if episode_number else None,
                        episode_title=episode_title if episode_title else None,
                        season=season,
                        year=year,
                        release_group=release_group if release_group else None,
                        video_resolution=video_resolution,
                        video_term=quality if quality else None,
                        file_extension=file_extension if file_extension else None,
                        parser_used="fallback",
                        raw_data=result.named,
                        confidence=0.6,  # Lower confidence for fallback parser
                    )

                    # Validate that we got meaningful information (more lenient)
                    if parsed_info.anime_title:
                        # Additional validation for bracket patterns to avoid conflicts
                        if self._validate_bracket_pattern(parsed_info, pattern):
                            logger.debug(f"Fallback parsing successful for: {filename}")
                            return parsed_info

            except Exception as e:
                logger.debug(f"Fallback pattern failed: {pattern}, error: {e}")
                continue

        logger.debug(f"Fallback parsing failed for: {filename}")
        return None

    def _clean_title(self, title: str) -> str:
        """Clean and normalize anime title.

        Args:
            title: Raw title string.

        Returns:
            Cleaned title string.
        """
        # Remove common prefixes/suffixes
        title = re.sub(r"^\[.*?\]\s*", "", title)  # Remove leading brackets
        title = re.sub(r"\s*\[.*?\]$", "", title)  # Remove trailing brackets
        title = re.sub(r"^\(.*?\)\s*", "", title)  # Remove leading parentheses
        title = re.sub(r"\s*\(.*?\)$", "", title)  # Remove trailing parentheses

        # Replace underscores and dashes with spaces
        title = title.replace("_", " ").replace("-", " ")

        # Normalize whitespace
        title = re.sub(r"\s+", " ", title).strip()

        return title

    def _extract_resolution(self, quality: str) -> Optional[str]:
        """Extract video resolution from quality string.

        Args:
            quality: Quality string that may contain resolution info.

        Returns:
            Extracted resolution or None.
        """
        if not quality:
            return None

        # Common resolution patterns
        resolution_patterns = [
            r"(\d{3,4}p)",  # 720p, 1080p, etc.
            r"(\d{3,4}x\d{3,4})",  # 1920x1080, etc.
        ]

        for pattern in resolution_patterns:
            match = re.search(pattern, quality, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def _validate_bracket_pattern(
        self,
        parsed_info: ParsedAnimeInfo,
        pattern: str,
    ) -> bool:
        """Validate bracket patterns to avoid conflicts between similar patterns.

        Args:
            parsed_info: Parsed information to validate.
            pattern: The pattern that was matched.

        Returns:
            True if the pattern is valid for this content, False otherwise.
        """
        # For bracket patterns, validate that the content makes sense
        if "[{release_group}]" in pattern and "[{quality}]" in pattern:
            # Bracket format: [Release Group] Title - Episode [Quality]
            # Validate that release_group looks like a release group name
            # and quality looks like a quality indicator
            release_group = parsed_info.release_group or ""
            quality = parsed_info.video_term or ""

            # Release groups typically don't contain resolution info
            # Quality indicators typically contain resolution info or are common quality terms
            quality_indicators = [
                "1080p",
                "720p",
                "480p",
                "2160p",
                "4K",
                "HD",
                "SD",
                "BluRay",
                "WEB-DL",
                "WEBRip",
                "HDRip",
                "DVDRip",
            ]

            # If the "release_group" field contains quality indicators, it's likely misidentified
            if any(indicator in release_group for indicator in quality_indicators):
                return False

        elif "[{quality}]" in pattern and "[{release_group}]" in pattern:
            # Quality-first format: [Quality] Title - Episode [Release Group]
            # Validate that quality looks like a quality indicator
            # and release_group looks like a release group name
            quality = parsed_info.video_term or ""
            release_group = parsed_info.release_group or ""

            # Quality indicators typically contain resolution info or are common quality terms
            quality_indicators = [
                "1080p",
                "720p",
                "480p",
                "2160p",
                "4K",
                "HD",
                "SD",
                "BluRay",
                "WEB-DL",
                "WEBRip",
                "HDRip",
                "DVDRip",
            ]

            # If the "quality" field doesn't contain quality indicators, it's likely misidentified
            if not any(indicator in quality for indicator in quality_indicators):
                return False

        return True


class UnifiedFilenameParser:
    """Unified filename parser with primary and fallback parsing.

    This class provides a unified interface for parsing anime filenames,
    using anitopy as the primary parser and falling back to custom patterns
    when anitopy fails or provides insufficient information.
    """

    def __init__(self) -> None:
        """Initialize the unified parser."""
        self.fallback_parser = FallbackParser()

        # Statistics tracking
        self.stats = {
            "total_parsed": 0,
            "anitopy_successes": 0,
            "fallback_successes": 0,
            "total_failures": 0,
            "anitopy_failures": 0,
            "fallback_failures": 0,
        }

    def parse_filename(self, filename: str) -> ParsedAnimeInfo:
        """Parse anime filename using primary and fallback parsers.

        Args:
            filename: Filename to parse.

        Returns:
            ParsedAnimeInfo containing extracted metadata.
        """
        self.stats["total_parsed"] += 1

        # Try primary parser (anitopy) first
        anitopy_result = self._parse_with_anitopy(filename)
        if anitopy_result and anitopy_result.is_parsed:
            self.stats["anitopy_successes"] += 1
            logger.debug(f"Primary parser (anitopy) successful for: {filename}")
            return anitopy_result
        self.stats["anitopy_failures"] += 1
        logger.debug(f"Primary parser (anitopy) failed for: {filename}")

        # Try fallback parser
        fallback_result = self.fallback_parser.parse(filename)
        if fallback_result and fallback_result.is_parsed:
            self.stats["fallback_successes"] += 1
            logger.info(f"Fallback parser successful for: {filename}")
            return fallback_result
        self.stats["fallback_failures"] += 1
        logger.debug(f"Fallback parser failed for: {filename}")

        # Both parsers failed
        self.stats["total_failures"] += 1
        logger.warning(f"Both parsers failed for: {filename}")

        return ParsedAnimeInfo(
            filename=filename,
            parser_used="none",
            confidence=0.0,
        )

    def _parse_with_anitopy(self, filename: str) -> Optional[ParsedAnimeInfo]:
        """Parse filename using anitopy.

        Args:
            filename: Filename to parse.

        Returns:
            ParsedAnimeInfo if parsing succeeds, None otherwise.
        """
        try:
            # Parse with anitopy
            parsed_data = anitopy.parse(filename)

            if not parsed_data:
                return None

            # Extract information from anitopy result
            anime_title = parsed_data.get("anime_title", "").strip()
            episode_number = parsed_data.get("episode_number", "").strip()
            episode_title = parsed_data.get("episode_title", "").strip()
            season = parsed_data.get("season")
            # Anitopy sometimes uses 'anime_year' instead of 'year'
            year = parsed_data.get("year") or parsed_data.get("anime_year")
            release_group = parsed_data.get("release_group", "").strip()
            video_resolution = parsed_data.get("video_resolution", "").strip()
            video_term = parsed_data.get("video_term", "").strip()
            audio_term = parsed_data.get("audio_term", "").strip()
            file_extension = parsed_data.get("file_extension", "").strip()

            # Validate that we got meaningful information
            if not anime_title:
                return None

            # Calculate confidence based on extracted information
            confidence = self._calculate_confidence(parsed_data)

            # Create ParsedAnimeInfo
            parsed_info = ParsedAnimeInfo(
                filename=filename,
                anime_title=anime_title,
                episode_number=episode_number if episode_number else None,
                episode_title=episode_title if episode_title else None,
                season=season,
                year=year,
                release_group=release_group if release_group else None,
                video_resolution=video_resolution if video_resolution else None,
                video_term=video_term if video_term else None,
                audio_term=audio_term if audio_term else None,
                file_extension=file_extension if file_extension else None,
                parser_used="anitopy",
                raw_data=parsed_data,
                confidence=confidence,
            )

            return parsed_info

        except Exception as e:
            logger.debug(f"Anitopy parsing failed for {filename}: {e}")
            return None

    def _calculate_confidence(self, parsed_data: Dict[str, Any]) -> float:
        """Calculate confidence score for parsed data.

        Args:
            parsed_data: Raw parsed data from anitopy.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        confidence = 0.0

        # Base confidence for having a title
        if parsed_data.get("anime_title"):
            confidence += 0.4

        # Bonus for episode information
        if parsed_data.get("episode_number"):
            confidence += 0.3
        elif parsed_data.get("episode_title"):
            confidence += 0.2

        # Bonus for season information
        if parsed_data.get("season"):
            confidence += 0.1

        # Bonus for year information
        if parsed_data.get("year"):
            confidence += 0.1

        # Bonus for technical information
        if parsed_data.get("video_resolution"):
            confidence += 0.05
        if parsed_data.get("release_group"):
            confidence += 0.05

        return round(min(confidence, 1.0), 2)

    def get_stats(self) -> Dict[str, Any]:
        """Get parsing statistics.

        Returns:
            Dictionary containing parsing statistics.
        """
        stats = self.stats.copy()

        # Calculate success rates
        if stats["total_parsed"] > 0:
            stats["overall_success_rate"] = (
                stats["anitopy_successes"] + stats["fallback_successes"]
            ) / stats["total_parsed"]
            stats["anitopy_success_rate"] = (
                stats["anitopy_successes"] / stats["total_parsed"]
            )
            stats["fallback_success_rate"] = (
                stats["fallback_successes"] / stats["total_parsed"]
            )
            stats["failure_rate"] = stats["total_failures"] / stats["total_parsed"]
        else:
            stats.update(
                {
                    "overall_success_rate": 0.0,
                    "anitopy_success_rate": 0.0,
                    "fallback_success_rate": 0.0,
                    "failure_rate": 0.0,
                },
            )

        return stats

    def reset_stats(self) -> None:
        """Reset parsing statistics."""
        self.stats = {
            "total_parsed": 0,
            "anitopy_successes": 0,
            "fallback_successes": 0,
            "total_failures": 0,
            "anitopy_failures": 0,
            "fallback_failures": 0,
        }
        logger.debug("Parser statistics reset")


# Global parser instance
_parser_instance: Optional[UnifiedFilenameParser] = None


def get_parser() -> UnifiedFilenameParser:
    """Get the global parser instance.

    Returns:
        Global UnifiedFilenameParser instance.
    """
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = UnifiedFilenameParser()
    return _parser_instance


def parse_filename(filename: str) -> ParsedAnimeInfo:
    """Parse anime filename using the unified parser.

    Args:
        filename: Filename to parse.

    Returns:
        ParsedAnimeInfo containing extracted metadata.
    """
    parser = get_parser()
    return parser.parse_filename(filename)
