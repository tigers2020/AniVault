"""Match DTOs for application ??presentation contract.

Presentation consumes these types only. TMDB/shared models are never
exposed directly to presentation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ManualSearchResultDTO(BaseModel):
    """DTO for manual TMDB search result (presentation display).

    Replaces TMDBSearchResult for presentation consumption.
    """

    id: int = Field(..., description="TMDB media ID")
    media_type: str = Field(..., description="tv or movie")
    title: str = Field(..., description="Display title")
    first_air_date: str | None = Field(None, description="First air date")
    poster_path: str | None = Field(None, description="Poster path")

    @property
    def display_date(self) -> str | None:
        """Alias for first_air_date (compatible with dialog logic)."""
        return self.first_air_date
