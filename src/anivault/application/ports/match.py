"""Ports (Protocol interfaces) for metadata search (manual TMDB search dialog)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from anivault.application.dtos.match import ManualSearchResultDTO


@runtime_checkable
class MetadataSearchPort(Protocol):
    """Port: search TMDB by query string.

    Used by TmdbManualSearchDialog to avoid direct tmdb_client injection.
    MatchUseCase implements this protocol.
    """

    async def search_metadata(self, query: str) -> list[ManualSearchResultDTO]:
        """Search TMDB by query. Returns application DTO only."""
        ...
