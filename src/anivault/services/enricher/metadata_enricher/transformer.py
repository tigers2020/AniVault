"""Metadata transformation module.

This module provides the MetadataTransformer class that converts EnrichedMetadata
to FileMetadata for presentation layer consumption.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from anivault.core.parser.models import ParsingResult
from anivault.services.tmdb import TMDBMediaDetails
from anivault.shared.constants import TMDBResponseKeys
from anivault.shared.metadata_models import FileMetadata


class MetadataTransformer:
    """Transforms EnrichedMetadata to FileMetadata.

    This class encapsulates the logic for converting internal metadata
    representations (TMDBMediaDetails Pydantic models or dict fallbacks)
    into the lightweight FileMetadata dataclass used by presentation layers.

    The transformation handles:
    - Pydantic TMDBMediaDetails models (preferred)
    - Dictionary fallback format (legacy/search results)
    - None/missing data gracefully (uses ParsingResult as fallback)

    Example:
        >>> transformer = MetadataTransformer()
        >>> file_metadata = transformer.transform(
        ...     file_info=parsing_result,
        ...     tmdb_data=tmdb_details,
        ...     file_path=Path("/anime/aot.mkv")
        ... )
    """

    def transform(
        self,
        file_info: ParsingResult,
        tmdb_data: TMDBMediaDetails | dict[str, Any] | None,
        file_path: Path,
    ) -> FileMetadata:
        """Transform enriched metadata to FileMetadata for presentation.

        Args:
            file_info: Parsed file information (always available)
            tmdb_data: TMDB data (Pydantic model, dict, or None)
            file_path: Path to the media file

        Returns:
            FileMetadata instance for presentation layer

        Example:
            >>> transformer = MetadataTransformer()
            >>> result = transformer.transform(
            ...     file_info=ParsingResult(title="Attack on Titan", season=1),
            ...     tmdb_data=tmdb_details,
            ...     file_path=Path("/anime/aot.mkv")
            ... )
        """
        # Start with ParsingResult data (always available)
        title = file_info.title
        year: int | None = None
        season: int | None = file_info.season
        episode: int | None = file_info.episode

        # Initialize TMDB fields with defaults
        genres: list[str] = []
        overview: str | None = None
        poster_path: str | None = None
        vote_average: float | None = None
        tmdb_id: int | None = None
        media_type: str | None = None

        # Process TMDB data if available
        if tmdb_data is not None:
            if isinstance(tmdb_data, TMDBMediaDetails):
                # Pydantic model (preferred path)
                (
                    title,
                    genres,
                    overview,
                    poster_path,
                    vote_average,
                    tmdb_id,
                    media_type,
                    year,
                ) = self._from_pydantic(tmdb_data)
            elif isinstance(tmdb_data, dict):
                # Dictionary fallback (search results/legacy)
                (
                    title,
                    genres,
                    overview,
                    poster_path,
                    vote_average,
                    tmdb_id,
                    media_type,
                    year,
                ) = self._from_dict(tmdb_data, title)

        return FileMetadata(
            title=title,
            file_path=file_path,
            file_type=file_path.suffix.lstrip(".").lower(),
            year=year,
            season=season,
            episode=episode,
            genres=genres,
            overview=overview,
            poster_path=poster_path,
            vote_average=vote_average,
            tmdb_id=tmdb_id,
            media_type=media_type,
        )

    def _from_pydantic(
        self, tmdb_data: TMDBMediaDetails
    ) -> tuple[
        str, list[str], str | None, str | None, float | None, int, str, int | None
    ]:
        """Extract fields from TMDBMediaDetails Pydantic model.

        Args:
            tmdb_data: TMDB Pydantic model

        Returns:
            Tuple of (title, genres, overview, poster_path, vote_average,
                     tmdb_id, media_type, year)
        """
        title = tmdb_data.display_title
        genres = [genre.name for genre in tmdb_data.genres]
        overview = tmdb_data.overview
        poster_path = tmdb_data.poster_path
        vote_average = tmdb_data.vote_average
        tmdb_id = tmdb_data.id
        media_type = "tv" if tmdb_data.number_of_seasons is not None else "movie"

        # Extract year from display_date
        year = self._extract_year(tmdb_data.display_date)

        return (
            title,
            genres,
            overview,
            poster_path,
            vote_average,
            tmdb_id,
            media_type,
            year,
        )

    def _from_dict(
        self, tmdb_data: dict[str, Any], fallback_title: str
    ) -> tuple[
        str,
        list[str],
        str | None,
        str | None,
        float | None,
        int | None,
        str | None,
        int | None,
    ]:
        """Extract fields from dictionary (fallback/search result format).

        Args:
            tmdb_data: TMDB data as dictionary
            fallback_title: Title from ParsingResult (used if TMDB title missing)

        Returns:
            Tuple of (title, genres, overview, poster_path, vote_average,
                     tmdb_id, media_type, year)
        """
        # Extract title (try multiple keys)
        title = (
            tmdb_data.get(TMDBResponseKeys.TITLE)
            or tmdb_data.get(TMDBResponseKeys.NAME)
            or fallback_title
        )

        # Extract genres
        genres: list[str] = []
        genres_data = tmdb_data.get(TMDBResponseKeys.GENRES, [])
        if isinstance(genres_data, list):
            genres = [
                g.get(TMDBResponseKeys.NAME, "")
                for g in genres_data
                if isinstance(g, dict)
            ]

        # Extract other fields
        overview = tmdb_data.get(TMDBResponseKeys.OVERVIEW)
        poster_path = tmdb_data.get(TMDBResponseKeys.POSTER_PATH)
        vote_average = tmdb_data.get(TMDBResponseKeys.VOTE_AVERAGE)
        tmdb_id = tmdb_data.get(TMDBResponseKeys.ID)
        media_type = tmdb_data.get(TMDBResponseKeys.MEDIA_TYPE)

        # Extract year from date fields
        date_str = tmdb_data.get(TMDBResponseKeys.FIRST_AIR_DATE) or tmdb_data.get(
            TMDBResponseKeys.RELEASE_DATE
        )
        year = self._extract_year(date_str) if date_str else None

        return (
            title,
            genres,
            overview,
            poster_path,
            vote_average,
            tmdb_id,
            media_type,
            year,
        )

    def _extract_year(self, date_str: str | None) -> int | None:
        """Extract year from date string.

        Args:
            date_str: Date string in "YYYY-MM-DD" format (or None)

        Returns:
            Year as integer, or None if extraction fails

        Example:
            >>> transformer._extract_year("2013-04-07")
            2013
            >>> transformer._extract_year(None)
            None
        """
        if not date_str or not isinstance(date_str, str):
            return None

        try:
            return int(date_str.split("-")[0])
        except (ValueError, IndexError):
            return None


__all__ = ["MetadataTransformer"]
