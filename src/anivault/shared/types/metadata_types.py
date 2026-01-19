"""Type definitions for metadata dictionary representations.

This module provides TypedDict definitions for type-safe dictionary representations
of metadata models, eliminating dict[str, Any] usage across the codebase.

Design Principles:
- TypedDict for type-safe dict structures
- total=False for optional fields (matches dataclass defaults)
- Explicit field types matching source dataclasses
"""

from __future__ import annotations

from typing import TypedDict


class FileMetadataDict(TypedDict, total=False):
    """Type-safe dictionary representation of FileMetadata.

    This TypedDict defines the structure of dictionaries used to represent
    FileMetadata instances, ensuring type safety when converting between
    FileMetadata dataclass and dict formats.

    Fields:
        file_path: File path as string (required)
        file_name: Filename without path (optional)
        title: Display title (required)
        file_type: File extension/type (required)
        year: Release year (optional)
        season: Season number (optional)
        episode: Episode number (optional)
        genres: List of genre names (optional)
        overview: Brief description/synopsis (optional)
        poster_path: TMDB poster image path (optional)
        vote_average: TMDB rating (optional)
        tmdb_id: TMDB unique identifier (optional)
        media_type: Type of media "tv" or "movie" (optional)
    """

    file_path: str
    file_name: str
    title: str
    file_type: str
    year: int | None
    season: int | None
    episode: int | None
    genres: list[str]
    overview: str | None
    poster_path: str | None
    vote_average: float | None
    tmdb_id: int | None
    media_type: str | None


class ParsingResultDict(TypedDict, total=False):
    """Type-safe dictionary representation of ParsingResult.

    This TypedDict defines the structure of dictionaries used to represent
    ParsingResult instances, ensuring type safety when converting between
    ParsingResult dataclass and dict formats.

    Fields:
        title: The anime title (required)
        episode: Episode number (optional)
        season: Season number (optional)
        year: Release year (optional)
        quality: Video quality indicator (optional)
        source: Release source (optional)
        codec: Video codec (optional)
        audio: Audio codec or channel info (optional)
        release_group: Name of release group (optional)
        confidence: Parsing confidence score (optional, defaults to 0.0)
        parser_used: Name of parser that produced result (optional)
        additional_info: Additional parsing information as dict (optional)
    """

    title: str
    episode: int | None
    season: int | None
    year: int | None
    quality: str | None
    source: str | None
    codec: str | None
    audio: str | None
    release_group: str | None
    confidence: float
    parser_used: str
    additional_info: dict[str, object]


__all__ = [
    "FileMetadataDict",
    "ParsingResultDict",
]
