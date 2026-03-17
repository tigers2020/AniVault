"""Metadata adapter for organize pipeline.

Converts FileMetadata to ParsingResult for the organize pipeline.
Phase 5: moved from shared.utils.metadata_converter (legacy).
"""

from __future__ import annotations

from anivault.domain.entities.metadata import FileMetadata, TMDBMatchResult
from anivault.domain.entities.parser import ParsingAdditionalInfo, ParsingResult


def file_metadata_to_parsing_result(metadata: FileMetadata) -> ParsingResult:
    """Convert FileMetadata to ParsingResult for organizing.

    Preserves TMDB match result in additional_info.match_result when metadata
    has tmdb_id, enabling year extraction in path building.

    Args:
        metadata: FileMetadata instance to convert

    Returns:
        ParsingResult instance for organize pipeline
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
        parser_used="metadata_adapter",
        additional_info=additional_info,
    )
