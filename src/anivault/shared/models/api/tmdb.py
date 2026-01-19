"""TMDB API Response Models.

This module defines dataclasses for TMDB API responses to ensure
type safety and validation at the external API boundary.

These models are moved to shared to avoid dependency layer violations.
Core modules can use these models without importing from services layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from anivault.shared.types.base import BaseDataclass


@dataclass
class TMDBGenre(BaseDataclass):
    """TMDB genre information."""

    id: int
    name: str


@dataclass
class TMDBSearchResult(BaseDataclass):
    """Single search result from TMDB API."""

    id: int
    media_type: Literal["tv", "movie"]
    title: str | None = None
    name: str | None = None
    original_title: str | None = None
    original_name: str | None = None
    release_date: str | None = None
    first_air_date: str | None = None
    popularity: float = 0.0
    vote_average: float = 0.0
    vote_count: int = 0
    overview: str = ""
    original_language: str = ""
    poster_path: str | None = None
    backdrop_path: str | None = None
    genre_ids: list[int] = field(default_factory=list)

    @property
    def display_title(self) -> str:
        """Get display title regardless of media type."""
        return self.title or self.name or "Unknown"

    @property
    def display_date(self) -> str | None:
        """Get display date regardless of media type."""
        return self.first_air_date or self.release_date


@dataclass
class ScoredSearchResult(TMDBSearchResult):
    """TMDB search result with confidence score."""

    confidence_score: float = 0.0

    @property
    def display_title(self) -> str:
        """Get display title regardless of media type."""
        return self.title or self.name or "Unknown"

    @property
    def display_date(self) -> str | None:
        """Get display date regardless of media type."""
        return self.first_air_date or self.release_date


TMDBCandidate = ScoredSearchResult


@dataclass
class TMDBSearchResponse(BaseDataclass):
    """Complete TMDB search API response."""

    page: int = 1
    total_pages: int = 1
    total_results: int = 0
    results: list[TMDBSearchResult] = field(default_factory=list)


@dataclass
class TMDBEpisode(BaseDataclass):
    """TMDB TV show episode information."""

    id: int
    name: str
    episode_number: int
    season_number: int
    air_date: str | None = None
    overview: str = ""
    vote_average: float = 0.0
    vote_count: int = 0
    runtime: int | None = None
    still_path: str | None = None


@dataclass
class TMDBMediaDetails(BaseDataclass):
    """TMDB media details (movie or TV show)."""

    id: int
    genres: list[TMDBGenre] = field(default_factory=list)
    title: str | None = None
    name: str | None = None
    original_title: str | None = None
    original_name: str | None = None
    release_date: str | None = None
    first_air_date: str | None = None
    popularity: float = 0.0
    vote_average: float = 0.0
    vote_count: int = 0
    overview: str = ""
    original_language: str = ""
    poster_path: str | None = None
    backdrop_path: str | None = None
    number_of_episodes: int | None = None
    number_of_seasons: int | None = None
    last_episode_to_air: TMDBEpisode | None = None

    @property
    def display_title(self) -> str:
        """Get display title regardless of media type."""
        return self.title or self.name or "Unknown"

    @property
    def display_date(self) -> str | None:
        """Get display date regardless of media type."""
        return self.first_air_date or self.release_date


__all__ = [
    "ScoredSearchResult",
    "TMDBCandidate",
    "TMDBEpisode",
    "TMDBGenre",
    "TMDBMediaDetails",
    "TMDBSearchResponse",
    "TMDBSearchResult",
]
