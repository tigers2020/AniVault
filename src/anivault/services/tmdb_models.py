"""TMDB API Response Models.

This module defines Pydantic models for TMDB API responses to ensure
type safety and validation at the external API boundary.

These models inherit from BaseTypeModel which provides ConfigDict(extra='ignore')
to gracefully handle new fields added by the TMDB API without breaking validation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from anivault.shared.types.base import BaseTypeModel


class TMDBGenre(BaseTypeModel):
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

    id: int = Field(..., description="TMDB genre ID")
    name: str = Field(..., description="Genre name (localized)")


class TMDBSearchResult(BaseTypeModel):
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
    id: int = Field(..., description="TMDB media ID")
    media_type: Literal["tv", "movie"] = Field(..., description="Media type")

    # Optional title fields (movie vs TV show)
    title: str | None = Field(None, description="Movie title")
    name: str | None = Field(None, description="TV show name")
    original_title: str | None = Field(None, description="Original language title")
    original_name: str | None = Field(None, description="Original language name")

    # Optional date fields (movie vs TV show)
    release_date: str | None = Field(
        None,
        description="Movie release date (YYYY-MM-DD)",
    )
    first_air_date: str | None = Field(
        None,
        description="TV show first air date (YYYY-MM-DD)",
    )

    # Numeric metadata with defaults
    popularity: float = Field(0.0, description="Popularity score")
    vote_average: float = Field(0.0, description="Average rating (0-10)")
    vote_count: int = Field(0, description="Number of votes")

    # Text metadata
    overview: str = Field("", description="Plot synopsis")
    original_language: str = Field("", description="Original language code")

    # Image paths
    poster_path: str | None = Field(None, description="Poster image path")
    backdrop_path: str | None = Field(None, description="Backdrop image path")

    # Genre information (critical for matching engine)
    genre_ids: list[int] = Field(default_factory=list, description="Genre IDs")

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

    confidence_score: float = Field(0.0, description="Confidence score (0.0-1.0)")

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


class TMDBSearchResponse(BaseTypeModel):
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

    page: int = Field(1, description="Current page number")
    total_pages: int = Field(1, description="Total pages available")
    total_results: int = Field(0, description="Total results count")
    results: list[TMDBSearchResult] = Field(
        default_factory=list,
        description="Search results",
    )


class TMDBEpisode(BaseTypeModel):
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
        ...     name="인류의 새벽",
        ...     episode_number=28,
        ...     season_number=4,
        ...     air_date="2022-04-04"
        ... )
        >>> episode.episode_number
        28
    """

    # Required fields
    id: int = Field(..., description="TMDB episode ID")
    name: str = Field(..., description="Episode title")
    episode_number: int = Field(..., description="Episode number (1-indexed)")
    season_number: int = Field(..., description="Season number (1-indexed)")

    # Optional fields
    air_date: str | None = Field(None, description="Air date (YYYY-MM-DD)")
    overview: str = Field("", description="Episode synopsis")
    vote_average: float = Field(0.0, description="Average rating (0-10)")
    vote_count: int = Field(0, description="Number of votes")
    runtime: int | None = Field(None, description="Runtime in minutes")
    still_path: str | None = Field(None, description="Still image path")


class TMDBMediaDetails(BaseTypeModel):
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
    id: int = Field(..., description="TMDB media ID")
    genres: list[TMDBGenre] = Field(default_factory=list, description="Genre list")

    # Optional title fields (movie vs TV show)
    title: str | None = Field(None, description="Movie title")
    name: str | None = Field(None, description="TV show name")
    original_title: str | None = Field(None, description="Original language title")
    original_name: str | None = Field(None, description="Original language name")

    # Optional date fields (movie vs TV show)
    release_date: str | None = Field(
        None,
        description="Movie release date (YYYY-MM-DD)",
    )
    first_air_date: str | None = Field(
        None,
        description="TV show first air date (YYYY-MM-DD)",
    )

    # Numeric metadata
    popularity: float = Field(0.0, description="Popularity score")
    vote_average: float = Field(0.0, description="Average rating (0-10)")
    vote_count: int = Field(0, description="Number of votes")

    # Text metadata
    overview: str = Field("", description="Plot synopsis")
    original_language: str = Field("", description="Original language code")

    # Image paths
    poster_path: str | None = Field(None, description="Poster image path")
    backdrop_path: str | None = Field(None, description="Backdrop image path")

    # TV show specific fields
    number_of_episodes: int | None = Field(None, description="Total episodes (TV)")
    number_of_seasons: int | None = Field(None, description="Total seasons (TV)")
    last_episode_to_air: TMDBEpisode | None = Field(
        None,
        description="Most recent episode (TV)",
    )

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
