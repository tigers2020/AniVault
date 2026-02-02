"""Metadata converter utilities for type-safe dict conversions.

This module provides centralized conversion utilities for FileMetadata and ParsingResult
models, eliminating dict[str, Any] usage and duplicate conversion logic across the codebase.

Design Principles:
- Type-safe conversions using TypedDict
- Single source of truth for conversion logic
- Backward compatible with existing code
- Clear separation of concerns

Migration Strategy:
- Replace scattered _file_metadata_to_dict() functions with MetadataConverter.to_dict()
- Replace _dict_to_file_metadata() with MetadataConverter.from_dict()
- Gradually migrate all conversion usages to this module
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anivault.shared.models.metadata import FileMetadata
    from anivault.shared.models.parser import ParsingAdditionalInfo, ParsingResult
    from anivault.shared.types.metadata_types import (
        FileMetadataDict,
        ParsingResultDict,
    )

from anivault.shared.models.metadata import FileMetadata, TMDBMatchResult

# Type imports at runtime to avoid circular dependencies
from anivault.shared.models.parser import ParsingAdditionalInfo, ParsingResult
from anivault.shared.types.metadata_types import (
    FileMetadataDict,
    ParsingResultDict,
)
from anivault.shared.utils.dataclass_serialization import from_dict as dataclass_from_dict


class MetadataConverter:
    """Utility class for converting between metadata models and dict representations.

    This class centralizes all conversion logic between FileMetadata/ParsingResult
    dataclasses and their TypedDict representations, ensuring consistency and
    type safety across the codebase.
    """

    @staticmethod
    def to_dict(metadata: FileMetadata) -> FileMetadataDict:
        """Convert FileMetadata to FileMetadataDict.

        This method converts a FileMetadata dataclass instance to its TypedDict
        representation, maintaining backward compatibility with existing JSON output.

        Args:
            metadata: FileMetadata instance to convert

        Returns:
            FileMetadataDict with all metadata fields

        Example:
            >>> metadata = FileMetadata(
            ...     title="Attack on Titan",
            ...     file_path=Path("/anime/aot.mkv"),
            ...     file_type="mkv",
            ...     tmdb_id=1429,
            ... )
            >>> result = MetadataConverter.to_dict(metadata)
            >>> isinstance(result, dict)
            True
            >>> result["title"]
            'Attack on Titan'
        """
        # Use string literals for TypedDict keys (ScanFields constants are aliases)
        result: FileMetadataDict = {
            "title": metadata.title,
            "file_path": str(metadata.file_path),
            "file_name": metadata.file_name,
            "file_type": metadata.file_type,
            "year": metadata.year,
            "season": metadata.season,
            "episode": metadata.episode,
            "genres": metadata.genres,
            "overview": metadata.overview,
            "poster_path": metadata.poster_path,
            "vote_average": metadata.vote_average,
            "tmdb_id": metadata.tmdb_id,
            "media_type": metadata.media_type,
        }
        return result

    @staticmethod
    def from_dict(data: FileMetadataDict) -> FileMetadata:
        """Convert FileMetadataDict to FileMetadata.

        This method converts a dictionary (TypedDict) representation back to a
        FileMetadata dataclass instance, with validation of required fields.

        Args:
            data: FileMetadataDict containing metadata fields

        Returns:
            FileMetadata instance with converted data

        Raises:
            ValueError: If required fields (file_path, title, file_type) are missing

        Example:
            >>> data: FileMetadataDict = {
            ...     "file_path": "/anime/aot.mkv",
            ...     "title": "Attack on Titan",
            ...     "file_type": "mkv",
            ...     "tmdb_id": 1429,
            ... }
            >>> metadata = MetadataConverter.from_dict(data)
            >>> isinstance(metadata, FileMetadata)
            True
            >>> metadata.title
            'Attack on Titan'
        """
        # Access fields directly from TypedDict (backward compatibility with ScanFields)
        # TypedDict keys are string literals, but we support both ScanFields and direct strings
        file_path_str: str | None = data.get("file_path")
        if not file_path_str or not isinstance(file_path_str, str):
            msg = "file_path is required in result dictionary"
            raise ValueError(msg)

        file_path = Path(file_path_str)

        title: str | None = data.get("title")
        if not title or not isinstance(title, str):
            msg = "title is required in result dictionary"
            raise ValueError(msg)

        file_type: str | None = data.get("file_type")
        if not file_type or not isinstance(file_type, str):
            msg = "file_type is required in result dictionary"
            raise ValueError(msg)

        # Optional fields with type casting for mypy
        year: int | None = data.get("year")
        season: int | None = data.get("season")
        episode: int | None = data.get("episode")
        genres: list[str] = data.get("genres") or []
        overview: str | None = data.get("overview")
        poster_path: str | None = data.get("poster_path")
        vote_average: float | None = data.get("vote_average")
        tmdb_id: int | None = data.get("tmdb_id")
        media_type: str | None = data.get("media_type")

        return FileMetadata(
            title=title,
            file_path=file_path,
            file_type=file_type,
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

    @staticmethod
    def file_metadata_to_parsing_result(metadata: FileMetadata) -> ParsingResult:
        """Convert FileMetadata to ParsingResult for organizing.

        Preserves TMDB match result in additional_info.match_result when metadata
        has tmdb_id, enabling year extraction in path building.

        Args:
            metadata: FileMetadata instance to convert

        Returns:
            ParsingResult instance for organize pipeline

        Example:
            >>> metadata = FileMetadata(
            ...     title="Attack on Titan",
            ...     file_path=Path("/anime/aot.mkv"),
            ...     file_type="mkv",
            ...     tmdb_id=1429,
            ...     year=2013,
            ... )
            >>> result = MetadataConverter.file_metadata_to_parsing_result(metadata)
            >>> result.additional_info.match_result is not None
            True
        """
        match_result: TMDBMatchResult | None = None
        if metadata.tmdb_id is not None:
            match_result = TMDBMatchResult(
                id=metadata.tmdb_id,
                title=metadata.title,
                media_type=metadata.media_type or "tv",
                year=metadata.year,
                genres=metadata.genres or [],
                overview=metadata.overview,
                vote_average=metadata.vote_average,
                poster_path=metadata.poster_path,
            )
        additional_info = ParsingAdditionalInfo(match_result=match_result)
        title = metadata.title or (metadata.file_path.stem if metadata.file_path else "")
        return ParsingResult(
            title=title,
            episode=metadata.episode,
            season=metadata.season,
            year=metadata.year,
            quality=None,
            source=None,
            codec=None,
            audio=None,
            release_group=None,
            confidence=1.0,
            parser_used="metadata_converter",
            additional_info=additional_info,
        )

    @staticmethod
    def parsing_result_to_dict(result: ParsingResult) -> ParsingResultDict:
        """Convert ParsingResult to ParsingResultDict.

        This method converts a ParsingResult dataclass instance to its TypedDict
        representation for serialization purposes.

        Args:
            result: ParsingResult instance to convert

        Returns:
            ParsingResultDict with all parsing result fields

        Example:
            >>> result = ParsingResult(
            ...     title="Attack on Titan",
            ...     episode=1,
            ...     season=1,
            ...     confidence=0.95,
            ... )
            >>> data = MetadataConverter.parsing_result_to_dict(result)
            >>> isinstance(data, dict)
            True
            >>> data["title"]
            'Attack on Titan'
        """
        return {
            "title": result.title,
            "episode": result.episode,
            "season": result.season,
            "year": result.year,
            "quality": result.quality,
            "source": result.source,
            "codec": result.codec,
            "audio": result.audio,
            "release_group": result.release_group,
            "confidence": result.confidence,
            "parser_used": result.parser_used,
            "additional_info": (asdict(result.additional_info) if result.additional_info and hasattr(result.additional_info, "__dict__") else {}),
        }

    @staticmethod
    def parsing_result_from_dict(data: ParsingResultDict) -> ParsingResult:
        """Convert ParsingResultDict to ParsingResult.

        This method converts a dictionary (TypedDict) representation back to a
        ParsingResult dataclass instance.

        Args:
            data: ParsingResultDict containing parsing result fields

        Returns:
            ParsingResult instance with converted data

        Raises:
            ValueError: If required fields are missing or invalid

        Example:
            >>> data = {
            ...     "title": "Attack on Titan",
            ...     "episode": 1,
            ...     "season": 1,
            ...     "confidence": 0.95,
            ...     "parser_used": "anitopy",
            ... }
            >>> result = MetadataConverter.parsing_result_from_dict(data)
            >>> isinstance(result, ParsingResult)
            True
            >>> result.title
            'Attack on Titan'
        """
        # Convert additional_info dict back to ParsingAdditionalInfo if present
        additional_info_dict = data.get("additional_info", {})
        if isinstance(additional_info_dict, dict) and additional_info_dict:
            additional_info = dataclass_from_dict(
                ParsingAdditionalInfo,
                additional_info_dict,
            )
        else:
            additional_info = ParsingAdditionalInfo()

        return ParsingResult(
            title=data["title"],
            episode=data.get("episode"),
            season=data.get("season"),
            year=data.get("year"),
            quality=data.get("quality"),
            source=data.get("source"),
            codec=data.get("codec"),
            audio=data.get("audio"),
            release_group=data.get("release_group"),
            confidence=data.get("confidence", 0.0),
            parser_used=data.get("parser_used", "unknown"),
            additional_info=additional_info,
        )


__all__ = [
    "MetadataConverter",
]
