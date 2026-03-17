"""Scan DTOs for application-presentation contract.

Presentation layer consumes these types only. Domain entities (FileMetadata)
are never exposed to presentation for scan output.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class ScanResultItem(BaseModel):
    """DTO for a single scan result item.

    Replaces FileMetadata for presentation consumption.
    Fields aligned with FileMetadata; file_path is str for JSON serialization.
    """

    title: str = Field(..., description="Display title")
    file_path: str = Field(..., description="File path as string")
    file_type: str = Field(..., description="File extension/type")
    year: int | None = Field(None, description="Release year")
    season: int | None = Field(None, description="Season number")
    episode: int | None = Field(None, description="Episode number")
    genres: list[str] = Field(default_factory=list, description="Genre names")
    overview: str | None = Field(None, description="Brief synopsis")
    poster_path: str | None = Field(None, description="TMDB poster path")
    vote_average: float | None = Field(None, description="TMDB rating")
    tmdb_id: int | None = Field(None, description="TMDB media ID")
    media_type: str | None = Field(None, description="tv or movie")
    match_confidence: float | None = Field(None, description="0.0-1.0 from matching")

    @property
    def file_name(self) -> str:
        """Filename without path."""
        return Path(self.file_path).name


def file_metadata_to_dto(metadata: object) -> ScanResultItem:
    """Convert FileMetadata to ScanResultItem (duck-typed, no domain import in presentation)."""
    return ScanResultItem(
        title=str(getattr(metadata, "title", "")),
        file_path=str(getattr(metadata, "file_path", "")),
        file_type=str(getattr(metadata, "file_type", "")),
        year=getattr(metadata, "year", None),
        season=getattr(metadata, "season", None),
        episode=getattr(metadata, "episode", None),
        genres=list(getattr(metadata, "genres", []) or []),
        overview=getattr(metadata, "overview", None),
        poster_path=getattr(metadata, "poster_path", None),
        vote_average=getattr(metadata, "vote_average", None),
        tmdb_id=getattr(metadata, "tmdb_id", None),
        media_type=getattr(metadata, "media_type", None),
        match_confidence=getattr(metadata, "match_confidence", None),
    )
