"""Service protocols for dependency inversion.

This module defines Protocol interfaces to break dependency layer violations.
Core modules can use these protocols without importing from services layer.
"""

from __future__ import annotations

from typing import Protocol

from anivault.shared.models.api.tmdb import TMDBMediaDetails, TMDBSearchResponse


class TMDBClientProtocol(Protocol):
    """Protocol for TMDB API client.

    This protocol defines the interface that TMDB clients must implement,
    allowing core modules to use TMDB functionality without directly
    depending on the services layer.

    Example:
        >>> from anivault.shared.protocols.services import TMDBClientProtocol
        >>> from anivault.services.tmdb import TMDBClient
        >>>
        >>> client: TMDBClientProtocol = TMDBClient()
        >>> results = await client.search_media("Attack on Titan")
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
