"""Data models for anime filename parsing.

This module defines the core data structures used throughout the parsing system.
All parsers should return results in the ParsingResult format for consistency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsingResult:
    """Result of parsing an anime filename.

    This dataclass represents the standardized output format for all parsers
    in the system, whether they use anitopy, regex, or other methods.

    Attributes:
        title: The anime title extracted from the filename.
        episode: Episode number (None if not found or not applicable).
        season: Season number (None if not found or single season).
        quality: Video quality indicator (e.g., "1080p", "720p").
        source: Release source (e.g., "BluRay", "WEB", "HDTV").
        codec: Video codec (e.g., "H.264", "HEVC", "x265").
        audio: Audio codec or channel info (e.g., "AAC", "FLAC", "5.1").
        release_group: Name of the release group.
        confidence: Parsing confidence score (0.0 to 1.0).
        parser_used: Name of the parser that produced this result.
        other_info: Dictionary for any additional extracted metadata.
    """

    title: str
    episode: int | None = None
    season: int | None = None
    quality: str | None = None
    source: str | None = None
    codec: str | None = None
    audio: str | None = None
    release_group: str | None = None
    confidence: float = 0.0
    parser_used: str = "unknown"
    other_info: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the parsing result after initialization.

        Returns:
            None

        Raises:
            ValueError: If confidence is not in the valid range [0.0, 1.0].
        """
        if not 0.0 <= self.confidence <= 1.0:
            msg = f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            raise ValueError(
                msg,
            )

    def is_valid(self) -> bool:
        """Check if the parsing result contains essential information.

        A valid result must have at least a title. Additional fields like
        episode and season are optional but increase confidence.

        Returns:
            True if the result has a title, False otherwise.
        """
        return bool(self.title and self.title.strip())

    def has_episode_info(self) -> bool:
        """Check if the result contains episode information.

        Returns:
            True if episode number is present, False otherwise.
        """
        return self.episode is not None

    def has_season_info(self) -> bool:
        """Check if the result contains season information.

        Returns:
            True if season number is present, False otherwise.
        """
        return self.season is not None
