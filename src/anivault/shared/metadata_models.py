"""Presentation layer metadata models for AniVault.

This module defines lightweight dataclasses for representing file metadata
in the GUI and CLI layers. These models decouple the presentation layer from
core domain models, providing a stable, type-safe interface for displaying
anime file information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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
            msg = "title cannot be empty"
            raise ValueError(msg)

        if not isinstance(self.file_path, Path):
            msg = f"file_path must be a Path object, got {type(self.file_path)}"
            raise TypeError(msg)

        if not self.file_type:
            msg = "file_type cannot be empty"
            raise ValueError(msg)

        # Validate year if provided
        if self.year is not None:
            current_year = 2030  # Conservative future limit
            if self.year < 1900 or self.year > current_year:
                msg = f"year must be between 1900 and {current_year}, got {self.year}"
                raise ValueError(msg)

        # Validate season/episode if provided
        if self.season is not None and self.season < 0:
            msg = f"season must be non-negative, got {self.season}"
            raise ValueError(msg)

        if self.episode is not None and self.episode < 0:
            msg = f"episode must be non-negative, got {self.episode}"
            raise ValueError(msg)

        # Validate vote_average if provided
        if self.vote_average is not None:
            if not 0.0 <= self.vote_average <= 10.0:
                msg = f"vote_average must be between 0.0 and 10.0, got {self.vote_average}"
                raise ValueError(msg)

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
