"""Presentation layer metadata models for AniVault.

This module defines lightweight dataclasses for representing file metadata
in the GUI and CLI layers. These models decouple the presentation layer from
core domain models, providing a stable, type-safe interface for displaying
anime file information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .constants.validation_constants import (
    EMPTY_FILE_TYPE_ERROR,
    EMPTY_TITLE_ERROR,
    EPISODE_NEGATIVE_ERROR_TEMPLATE,
    MAX_VOTE_AVERAGE,
    MAX_YEAR,
    MIN_VOTE_AVERAGE,
    MIN_YEAR,
    SEASON_NEGATIVE_ERROR_TEMPLATE,
    VOTE_AVERAGE_RANGE_ERROR_TEMPLATE,
    YEAR_RANGE_ERROR_TEMPLATE,
)


@dataclass
class FileMetadata:
    """Lightweight metadata model for presentation layer (GUI/CLI).

    This dataclass represents anime file metadata optimized for display
    in user interfaces. It contains essential information extracted from
    both filename parsing and TMDB API enrichment.

    Attributes:
        title: The display title of the anime (localized if available)
        year: Release or first air year
        season: Season number (None for single-season anime or movies)
        episode: Episode number (None for movies)
        file_path: Path to the media file
        file_type: File extension/type (e.g., "mkv", "mp4")
        genres: List of genre names (defaults to empty list)
        overview: Brief description/synopsis from TMDB
        poster_path: TMDB poster image path (relative)
        vote_average: TMDB rating/vote average
        tmdb_id: TMDB unique identifier
        media_type: Type of media ("tv" or "movie")

    Example:
        >>> metadata = FileMetadata(
        ...     title="Attack on Titan",
        ...     year=2013,
        ...     season=1,
        ...     episode=1,
        ...     file_path=Path("/anime/aot_s01e01.mkv"),
        ...     file_type="mkv",
        ...     genres=["Action", "Fantasy"],
        ... )
    """

    # Required fields
    title: str
    file_path: Path
    file_type: str

    # Optional core fields
    year: int | None = None
    season: int | None = None
    episode: int | None = None

    # TMDB enrichment fields
    genres: list[str] = field(default_factory=list)
    overview: str | None = None
    poster_path: str | None = None
    vote_average: float | None = None
    tmdb_id: int | None = None
    media_type: str | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.title:
            raise ValueError(EMPTY_TITLE_ERROR)

        # Type check removed - dataclass type hint enforces this at runtime

        if not self.file_type:
            raise ValueError(EMPTY_FILE_TYPE_ERROR)

        # Validate year if provided
        if self.year is not None:
            if self.year < MIN_YEAR or self.year > MAX_YEAR:
                raise ValueError(YEAR_RANGE_ERROR_TEMPLATE.format(year=self.year))

        # Validate season/episode if provided
        if self.season is not None and self.season < 0:
            raise ValueError(SEASON_NEGATIVE_ERROR_TEMPLATE.format(season=self.season))

        if self.episode is not None and self.episode < 0:
            raise ValueError(EPISODE_NEGATIVE_ERROR_TEMPLATE.format(episode=self.episode))

        # Validate vote_average if provided
        if self.vote_average is not None:
            if not MIN_VOTE_AVERAGE <= self.vote_average <= MAX_VOTE_AVERAGE:
                raise ValueError(VOTE_AVERAGE_RANGE_ERROR_TEMPLATE.format(vote_average=self.vote_average))

    @property
    def display_name(self) -> str:
        """Get formatted display name with season/episode info.

        Returns:
            Formatted string like "Attack on Titan S01E01" or "Attack on Titan (2013)"

        Example:
            >>> metadata = FileMetadata(
            ...     title="Attack on Titan",
            ...     year=2013,
            ...     season=1,
            ...     episode=1,
            ...     file_path=Path("/anime/aot.mkv"),
            ...     file_type="mkv",
            ... )
            >>> metadata.display_name
            'Attack on Titan S01E01'
        """
        parts = [self.title]

        # Add season and episode if both are available
        if self.season is not None and self.episode is not None:
            season_str = f"S{self.season:02d}"
            episode_str = f"E{self.episode:02d}"
            parts.append(f"{season_str}{episode_str}")
        # Add only episode if season is None
        elif self.episode is not None:
            parts.append(f"E{self.episode:02d}")
        # Add year if no episode info
        elif self.year is not None:
            parts.append(f"({self.year})")

        return " ".join(parts)

    @property
    def file_name(self) -> str:
        """Get the filename without path.

        Returns:
            Filename string

        Example:
            >>> metadata = FileMetadata(
            ...     title="Attack on Titan",
            ...     file_path=Path("/anime/aot_s01e01.mkv"),
            ...     file_type="mkv",
            ... )
            >>> metadata.file_name
            'aot_s01e01.mkv'
        """
        return self.file_path.name


@dataclass
class TMDBMatchResult:
    """TMDB API match result for anime files.

    This dataclass represents the result of matching a file against TMDB API,
    containing all the metadata retrieved from TMDB for display purposes.

    Attributes:
        id: TMDB unique identifier
        title: Official title from TMDB
        media_type: Type of media ("tv" or "movie")
        genres: List of genre names
        overview: Brief description/synopsis
        vote_average: TMDB rating/vote average
        poster_path: TMDB poster image path (relative)
    """

    id: int
    title: str
    media_type: str
    year: int | None = None
    genres: list[str] = field(default_factory=list)
    overview: str | None = None
    vote_average: float | None = None
    poster_path: str | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.title:
            raise ValueError(EMPTY_TITLE_ERROR)

        if self.id <= 0:
            msg = f"id must be positive, got {self.id}"
            raise ValueError(msg)

        if self.vote_average is not None:
            if not MIN_VOTE_AVERAGE <= self.vote_average <= MAX_VOTE_AVERAGE:
                raise ValueError(VOTE_AVERAGE_RANGE_ERROR_TEMPLATE.format(vote_average=self.vote_average))
