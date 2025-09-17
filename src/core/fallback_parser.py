"""
Fallback parsing mechanisms for anime filenames.

This module provides alternative parsing strategies when anitopy fails
to extract meaningful information from anime filenames.
"""

import re
from pathlib import Path
from typing import Any

from src.core.models import ParsedAnimeInfo
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FallbackAnimeParser:
    """
    Provides fallback parsing strategies for anime filenames.

    When anitopy fails to parse a filename, this class attempts to extract
    basic information using regex patterns and heuristics.
    """

    def __init__(self) -> None:
        """Initialize the fallback parser."""
        # Common patterns for anime filenames
        self.patterns = {
            # Episode patterns
            "episode_simple": re.compile(r"[Ee]p(?:isode)?\s*(\d+)", re.IGNORECASE),
            "episode_dash": re.compile(r"-\s*(\d+)\s*[\[\(]", re.IGNORECASE),
            "episode_bracket": re.compile(r"\[(\d+)\]", re.IGNORECASE),
            "episode_space": re.compile(r"\s+(\d+)\s+", re.IGNORECASE),
            # Season patterns
            "season_simple": re.compile(r"[Ss]eason\s*(\d+)", re.IGNORECASE),
            "season_s": re.compile(r"[Ss](\d+)", re.IGNORECASE),
            # Resolution patterns
            "resolution_p": re.compile(r"(\d+)[pP]", re.IGNORECASE),
            "resolution_x": re.compile(r"(\d+)[xX](\d+)", re.IGNORECASE),
            "resolution_4k": re.compile(r"4[kK]", re.IGNORECASE),
            # Year patterns
            "year_bracket": re.compile(r"\[(\d{4})\]", re.IGNORECASE),
            "year_paren": re.compile(r"\((\d{4})\)", re.IGNORECASE),
            # Quality patterns
            "quality_web": re.compile(r"[Ww]eb", re.IGNORECASE),
            "quality_bluray": re.compile(r"[Bb]lu[-\s]?[Rr]ay", re.IGNORECASE),
            "quality_dvd": re.compile(r"[Dd][Vv][Dd]", re.IGNORECASE),
            "quality_hdtv": re.compile(r"[Hh][Dd][Tt][Vv]", re.IGNORECASE),
        }

        # Common anime file extensions
        self.anime_extensions = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"}

        # Common release group patterns
        self.release_group_patterns = [
            re.compile(r"\[([A-Za-z0-9\-_]+)\]", re.IGNORECASE),
            re.compile(r"\(([A-Za-z0-9\-_]+)\)", re.IGNORECASE),
        ]

    def extract_basic_info(self, filename: str) -> dict[str, Any]:
        """
        Extract basic information using regex patterns.

        Args:
            filename: Filename to parse

        Returns:
            Dictionary with extracted information
        """
        info = {
            "title": "",
            "episode": None,
            "season": None,
            "resolution": None,
            "resolution_width": None,
            "resolution_height": None,
            "year": None,
            "source": None,
            "release_group": None,
            "file_extension": None,
        }

        # Extract file extension
        file_path = Path(filename)
        if file_path.suffix:
            info["file_extension"] = file_path.suffix.lower()

        # Extract episode number
        for pattern_name, pattern in self.patterns.items():
            if "episode" in pattern_name:
                match = pattern.search(filename)
                if match:
                    try:
                        info["episode"] = int(match.group(1))
                        break
                    except (ValueError, IndexError):
                        continue

        # Extract season number
        for pattern_name, pattern in self.patterns.items():
            if "season" in pattern_name:
                match = pattern.search(filename)
                if match:
                    try:
                        info["season"] = int(match.group(1))
                        break
                    except (ValueError, IndexError):
                        continue

        # Extract resolution
        # Check for 4K first
        if self.patterns["resolution_4k"].search(filename):
            info["resolution"] = "4K"
            info["resolution_width"] = 3840
            info["resolution_height"] = 2160
        else:
            # Check for explicit width x height
            match = self.patterns["resolution_x"].search(filename)
            if match:
                try:
                    width = int(match.group(1))
                    height = int(match.group(2))
                    info["resolution"] = f"{width}x{height}"
                    info["resolution_width"] = width
                    info["resolution_height"] = height
                except (ValueError, IndexError):
                    pass
            else:
                # Check for 'p' format
                match = self.patterns["resolution_p"].search(filename)
                if match:
                    try:
                        height = int(match.group(1))
                        info["resolution"] = f"{height}p"
                        # Assume 16:9 aspect ratio
                        width = int(height * (16 / 9))
                        info["resolution_width"] = width
                        info["resolution_height"] = height
                    except (ValueError, IndexError):
                        pass

        # Extract year
        for pattern_name, pattern in self.patterns.items():
            if "year" in pattern_name:
                match = pattern.search(filename)
                if match:
                    try:
                        year = int(match.group(1))
                        if 1900 <= year <= 2030:  # Reasonable year range
                            info["year"] = year
                            break
                    except (ValueError, IndexError):
                        continue

        # Extract source/quality
        for pattern_name, pattern in self.patterns.items():
            if "quality" in pattern_name:
                if pattern.search(filename):
                    if "web" in pattern_name:
                        info["source"] = "Web"
                    elif "bluray" in pattern_name:
                        info["source"] = "Blu-ray"
                    elif "dvd" in pattern_name:
                        info["source"] = "DVD"
                    elif "hdtv" in pattern_name:
                        info["source"] = "HDTV"
                    break

        # Extract release group
        for pattern in self.release_group_patterns:
            matches = pattern.findall(filename)
            if matches:
                # Take the first match that looks like a release group
                for match in matches:
                    if len(match) > 2 and not match.isdigit():
                        info["release_group"] = match
                        break

        # Extract title (everything before episode/season info)
        title = self._extract_title(filename, info)
        info["title"] = title

        return info

    def _extract_title(self, filename: str, info: dict[str, Any]) -> str:
        """
        Extract title from filename by removing known patterns.

        Args:
            filename: Original filename
            info: Extracted information dictionary

        Returns:
            Extracted title
        """
        title = filename

        # Remove file extension
        if info["file_extension"]:
            title = title.replace(info["file_extension"], "")

        # Remove common patterns
        patterns_to_remove = [
            r"\[.*?\]",  # Remove [brackets]
            r"\(.*?\)",  # Remove (parentheses)
            r"[Ee]p(?:isode)?\s*\d+",  # Remove episode info
            r"[Ss]eason\s*\d+",  # Remove season info
            r"[Ss]\d+",  # Remove S1, S2, etc.
            r"\d+[pP]",  # Remove resolution
            r"\d+[xX]\d+",  # Remove resolution
            r"4[kK]",  # Remove 4K
            r"[Ww]eb",  # Remove Web
            r"[Bb]lu[-\s]?[Rr]ay",  # Remove Blu-ray
            r"[Dd][Vv][Dd]",  # Remove DVD
            r"[Hh][Dd][Tt][Vv]",  # Remove HDTV
        ]

        for pattern in patterns_to_remove:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        # Clean up the title
        title = re.sub(r"\s+", " ", title)  # Multiple spaces to single
        title = title.strip(" -_")  # Remove leading/trailing separators

        return title

    def create_fallback_parsed_info(self, filename: str) -> ParsedAnimeInfo | None:
        """
        Create a ParsedAnimeInfo object using fallback parsing.

        Args:
            filename: Filename to parse

        Returns:
            ParsedAnimeInfo object or None if no meaningful info could be extracted
        """
        try:
            # First check if this looks like an anime file
            if not self.is_likely_anime_file(filename):
                return None

            info = self.extract_basic_info(filename)

            # Only create ParsedAnimeInfo if we have at least a title and some anime-like content
            if not info["title"] or len(info["title"]) < 2:
                return None

            # Must have at least episode info or resolution to be considered anime
            if not info["episode"] and not info["resolution"] and not info["season"]:
                return None

            return ParsedAnimeInfo(
                title=info["title"],
                season=info["season"],
                episode=info["episode"],
                episode_title=None,
                resolution=info["resolution"],
                resolution_width=info["resolution_width"],
                resolution_height=info["resolution_height"],
                video_codec=None,
                audio_codec=None,
                release_group=info["release_group"],
                file_extension=info["file_extension"],
                year=info["year"],
                source=info["source"],
                raw_data={"fallback_parsing": True, "original_filename": filename},
            )
        except Exception as e:
            logger.error(f"Fallback parsing failed for '{filename}': {e}")
            return None

    def is_likely_anime_file(self, filename: str) -> bool:
        """
        Check if a filename is likely to be an anime file.

        Args:
            filename: Filename to check

        Returns:
            True if likely to be anime, False otherwise
        """
        filename_lower = filename.lower()

        # Check file extension
        file_path = Path(filename)
        if file_path.suffix.lower() not in self.anime_extensions:
            return False

        # Check for common anime patterns
        anime_indicators = [
            r"[Ee]p(?:isode)?\s*\d+",  # Episode pattern
            r"[Ss]eason\s*\d+",  # Season pattern
            r"[Ss]\d+",  # S1, S2, etc.
            r"\[.*?\]",  # Bracket patterns (common in anime)
            r"\(\d{4}\)",  # Year in parentheses
            r"\d+[pP]",  # Resolution
            r"4[kK]",  # 4K resolution
        ]

        # Must have at least one anime indicator
        has_anime_indicator = False
        for pattern in anime_indicators:
            if re.search(pattern, filename_lower):
                has_anime_indicator = True
                break

        if not has_anime_indicator:
            return False

        # Additional checks to avoid false positives
        # Don't consider files that are clearly not anime
        non_anime_indicators = [
            r"\.txt$",  # Text files
            r"\.pdf$",  # PDF files
            r"\.doc",  # Document files
            r"\.zip$",  # Archive files
            r"\.rar$",  # Archive files
            r"vacation",  # Vacation videos
            r"family",  # Family videos
            r"birthday",  # Birthday videos
            r"wedding",  # Wedding videos
        ]

        for pattern in non_anime_indicators:
            if re.search(pattern, filename_lower):
                return False

        return True
