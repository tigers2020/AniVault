"""TMDB API Response Models.

This module defines dataclasses for TMDB API responses to ensure
type safety and validation at the external API boundary.

These models inherit from BaseDataclass which provides extra='ignore'
to gracefully handle new fields added by the TMDB API without breaking validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from anivault.shared.types.base import BaseDataclass


@dataclass
class TMDBGenre(BaseDataclass):
    """TMDB genre information.

    Represents a single genre as returned by TMDB API.
    Used in both search results and detailed media information.

    Attributes:
        id: TMDB genre ID (e.g., 16 for Animation)
        name: Genre name (localized based on API request language)

    Example:
        >>> genre = TMDBGenre(id=16, name="Animation")
        >>> genre.id
        16
        >>> genre.name
        'Animation'
    """

    id: int
    name: str


@dataclass
class TMDBSearchResult(BaseDataclass):
    """Single search result from TMDB API.

    Represents either a movie or TV show from search results.
    Movie results have 'title' and 'release_date',
    TV show results have 'name' and 'first_air_date'.

    Attributes:
        id: TMDB media ID
        media_type: Type of media ("tv" or "movie")
        title: Movie title (None for TV shows)
        name: TV show name (None for movies)
        original_title: Original language title (movie)
        original_name: Original language name (TV show)
        release_date: Movie release date (YYYY-MM-DD format)
        first_air_date: TV show first air date (YYYY-MM-DD format)
        popularity: Popularity score
        vote_average: Average user rating (0-10)
        vote_count: Number of votes
        overview: Plot synopsis
        poster_path: Poster image path (relative)
        backdrop_path: Backdrop image path (relative)
        genre_ids: List of genre IDs (e.g., [16] for Animation)
        original_language: Original language code (e.g., "ja", "en")

    Example:
        >>> # TV show result
        >>> tv_result = TMDBSearchResult(
        ...     id=1429,
        ...     media_type="tv",
        ...     name="진격의 거인",
        ...     first_air_date="2013-04-07",
        ...     genre_ids=[16, 10759]
        ... )
        >>> tv_result.media_type
        'tv'
        >>> # Movie result
        >>> movie_result = TMDBSearchResult(
        ...     id=100,
        ...     media_type="movie",
        ...     title="Test Movie",
        ...     release_date="2024-01-01"
        ... )
    """

    # Required fields
    id: int
    media_type: Literal["tv", "movie"]

    # Optional title fields (movie vs TV show)
    title: str | None = None
    name: str | None = None
    original_title: str | None = None
    original_name: str | None = None

    # Optional date fields (movie vs TV show)
    release_date: str | None = None
    first_air_date: str | None = None

    # Numeric metadata with defaults
    popularity: float = 0.0
    vote_average: float = 0.0
    vote_count: int = 0

    # Text metadata
    overview: str = ""
    original_language: str = ""

    # Image paths
    poster_path: str | None = None
    backdrop_path: str | None = None

    # Genre information (critical for matching engine)
    genre_ids: list[int] = field(default_factory=list)

    @property
    def display_title(self) -> str:
        """Get display title regardless of media type.

        Returns:
            Movie title, TV show name, or "Unknown" if both are None
        """
        return self.title or self.name or "Unknown"

    @property
    def display_date(self) -> str | None:
        """Get display date regardless of media type.

        Returns:
            TV show first air date or movie release date, None if both are None
        """
        return self.first_air_date or self.release_date


@dataclass
class ScoredSearchResult(TMDBSearchResult):
    """TMDB search result with confidence score.

    Extends TMDBSearchResult with a confidence_score field for ranking candidates.
    Used internally by MatchingEngine after scoring phase.

    Attributes:
        confidence_score: Confidence score (0.0-1.0) from MatchingEngine

    Example:
        >>> result = ScoredSearchResult(
        ...     id=1429,
        ...     media_type="tv",
        ...     name="Attack on Titan",
        ...     confidence_score=0.95
        ... )
        >>> result.confidence_score
        0.95
    """

    confidence_score: float = 0.0

    @property
    def display_title(self) -> str:
        """Get display title regardless of media type.

        Returns:
            Movie title, TV show name, or "Unknown" if both are None
        """
        return self.title or self.name or "Unknown"

    @property
    def display_date(self) -> str | None:
        """Get display date regardless of media type.

        Returns:
            TV show first air date or movie release date, None if both are None
        """
        return self.first_air_date or self.release_date


# Type alias for TMDB matching candidates (used by CandidateScoringService)
TMDBCandidate = ScoredSearchResult


@dataclass
class TMDBSearchResponse(BaseDataclass):
    """Complete TMDB search API response.

    Top-level response structure returned by TMDB search endpoints.
    Contains a list of search results and pagination information.

    Attributes:
        page: Current page number (1-indexed)
        total_pages: Total number of pages available
        total_results: Total number of results across all pages
        results: List of search results (movies or TV shows)

    Example:
        >>> response = TMDBSearchResponse(
        ...     page=1,
        ...     total_pages=5,
        ...     total_results=100,
        ...     results=[
        ...         TMDBSearchResult(id=1, media_type="tv", name="Test Show"),
        ...         TMDBSearchResult(id=2, media_type="movie", title="Test Movie")
        ...     ]
        ... )
        >>> len(response.results)
        2
        >>> response.total_results
        100
    """

    page: int = 1
    total_pages: int = 1
    total_results: int = 0
    results: list[TMDBSearchResult] = field(default_factory=list)


@dataclass
class TMDBEpisode(BaseDataclass):
    """TMDB TV show episode information.

    Represents a single episode from a TV show season.

    Attributes:
        id: TMDB episode ID
        name: Episode title
        overview: Episode plot synopsis
        episode_number: Episode number within the season (1-indexed)
        season_number: Season number (1-indexed)
        air_date: Original air date (YYYY-MM-DD format)
        vote_average: Average user rating (0-10)
        vote_count: Number of votes
        runtime: Episode runtime in minutes
        still_path: Episode still image path (relative)

    Example:
        >>> episode = TMDBEpisode(
        ...     id=3508327,
        ...     name="帰還",
        ...     episode_number=28,
        ...     season_number=4,
        ...     air_date="2022-04-04"
        ... )
        >>> episode.episode_number
        28
    """

    # Required fields
    id: int
    name: str
    episode_number: int
    season_number: int

    # Optional fields
    air_date: str | None = None
    overview: str = ""
    vote_average: float = 0.0
    vote_count: int = 0
    runtime: int | None = None
    still_path: str | None = None


@dataclass
class TMDBMediaDetails(BaseDataclass):
    """TMDB media details (movie or TV show).

    Comprehensive details about a specific media item.
    TV shows include episode information, movies do not.

    Attributes:
        id: TMDB media ID
        genres: List of genre information
        title: Movie title (None for TV shows)
        name: TV show name (None for movies)
        original_title: Original language title (movie)
        original_name: Original language name (TV show)
        release_date: Movie release date (YYYY-MM-DD)
        first_air_date: TV show first air date (YYYY-MM-DD)
        popularity: Popularity score
        vote_average: Average user rating (0-10)
        vote_count: Number of votes
        overview: Plot synopsis
        poster_path: Poster image path (relative)
        backdrop_path: Backdrop image path (relative)
        original_language: Original language code
        number_of_episodes: Total episode count (TV shows only)
        number_of_seasons: Total season count (TV shows only)
        last_episode_to_air: Most recent episode (TV shows only)

    Example:
        >>> # TV show details
        >>> tv_details = TMDBMediaDetails(
        ...     id=1429,
        ...     name="진격의 거인",
        ...     first_air_date="2013-04-07",
        ...     number_of_episodes=87,
        ...     number_of_seasons=4,
        ...     genres=[TMDBGenre(id=16, name="Animation")]
        ... )
        >>> tv_details.number_of_seasons
        4
    """

    # Required fields
    id: int
    genres: list[TMDBGenre] = field(default_factory=list)

    # Optional title fields (movie vs TV show)
    title: str | None = None
    name: str | None = None
    original_title: str | None = None
    original_name: str | None = None

    # Optional date fields (movie vs TV show)
    release_date: str | None = None
    first_air_date: str | None = None

    # Numeric metadata
    popularity: float = 0.0
    vote_average: float = 0.0
    vote_count: int = 0

    # Text metadata
    overview: str = ""
    original_language: str = ""

    # Image paths
    poster_path: str | None = None
    backdrop_path: str | None = None

    # TV show specific fields
    number_of_episodes: int | None = None
    number_of_seasons: int | None = None
    last_episode_to_air: TMDBEpisode | None = None

    @property
    def display_title(self) -> str:
        """Get display title regardless of media type.

        Returns:
            Movie title, TV show name, or "Unknown" if both are None
        """
        return self.title or self.name or "Unknown"

    @property
    def display_date(self) -> str | None:
        """Get display date regardless of media type.

        Returns:
            TV show first air date or movie release date, None if both are None
        """
        return self.first_air_date or self.release_date
