"""TMDB client protocol for dependency inversion (Phase 5).

Defines the interface that TMDB clients must implement.
"""

from __future__ import annotations

from typing import Protocol

from anivault.shared.models.api.tmdb import TMDBMediaDetails, TMDBSearchResponse


class TMDBClientProtocol(Protocol):
    """Protocol for TMDB API client.

    This protocol defines the interface that TMDB clients must implement,
    allowing core modules to use TMDB functionality without directly
    depending on the services layer.
    """

    async def search_media(self, title: str) -> TMDBSearchResponse:
        """Search for media (TV shows and movies) by title.

        Args:
            title: Title to search for

        Returns:
            TMDBSearchResponse with typed search results
        """

    async def get_media_details(
        self,
        media_id: int,
        media_type: str,
    ) -> TMDBMediaDetails | None:
        """Get detailed information for a specific media item.

        Args:
            media_id: TMDB ID of the media item
            media_type: Type of media ('tv' or 'movie')

        Returns:
            TMDBMediaDetails or None if not found
        """
