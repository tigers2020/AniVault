"""Shared TMDB matching pipeline helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from anivault.core.matching.engine import MatchingEngine
from anivault.core.matching.models import MatchResult
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.core.parser.models import ParsingAdditionalInfo, ParsingResult
from anivault.shared.metadata_models import FileMetadata

MatchQuery = dict[str, object]


@dataclass(frozen=True)
class MatchOptions:
    """Options for matching pipeline behavior."""

    language: str = "ko"
    region: str = "KR"
    auto_accept: bool = False
    force_rematch: bool = False


@dataclass(frozen=True)
class MatchResultBundle:
    """Bundle containing intermediate matching results."""

    file_path: Path
    parsing: ParsingResult | None
    parsing_dict: MatchQuery | None
    match: MatchResult | None
    metadata: FileMetadata | None


def normalize_parsing_result(
    parsing_result: ParsingResult | Mapping[str, object] | object,
    *,
    fallback_title: str,
    fallback_episode: int | None = None,
    fallback_season: int | None = None,
    fallback_year: int | None = None,
) -> ParsingResult:
    """Normalize parsing result into ParsingResult."""
    if isinstance(parsing_result, ParsingResult):
        return parsing_result

    if isinstance(parsing_result, Mapping):
        return ParsingResult(
            title=_coerce_str(parsing_result.get("anime_title"), fallback_title),
            episode=_coerce_int(parsing_result.get("episode_number"), fallback_episode),
            season=_coerce_int(parsing_result.get("season"), fallback_season),
            year=_coerce_int(parsing_result.get("anime_year"), fallback_year),
            quality=_coerce_str(parsing_result.get("video_resolution"), None),
            release_group=_coerce_str(parsing_result.get("release_group"), None),
            additional_info=ParsingAdditionalInfo(),
        )

    return ParsingResult(
        title=_coerce_str(getattr(parsing_result, "title", None), fallback_title),
        episode=_coerce_int(getattr(parsing_result, "episode", None), fallback_episode),
        season=_coerce_int(getattr(parsing_result, "season", None), fallback_season),
        year=_coerce_int(getattr(parsing_result, "year", None), fallback_year),
        quality=_coerce_str(getattr(parsing_result, "quality", None), None),
        release_group=_coerce_str(getattr(parsing_result, "release_group", None), None),
        additional_info=ParsingAdditionalInfo(),
    )


def parsing_result_to_dict(parsing_result: ParsingResult) -> MatchQuery:
    """Convert ParsingResult to dict for matching engine."""
    return {
        "anime_title": parsing_result.title,
        "episode_number": parsing_result.episode,
        "release_group": parsing_result.release_group,
        "video_resolution": parsing_result.quality,
        "anime_year": parsing_result.year,
    }


def match_result_to_file_metadata(
    file_path: Path,
    parsing_result: ParsingResult,
    match_result: MatchResult | None,
) -> FileMetadata:
    """Convert match result to FileMetadata."""
    title = parsing_result.title
    year = parsing_result.year
    season = parsing_result.season
    episode = parsing_result.episode

    overview = None
    poster_path = None
    vote_average = None
    tmdb_id = None
    media_type = None

    if match_result is not None:
        title = match_result.title
        year = match_result.year or year
        tmdb_id = match_result.tmdb_id
        media_type = match_result.media_type
        poster_path = match_result.poster_path
        overview = match_result.overview
        vote_average = match_result.vote_average

    return FileMetadata(
        title=title,
        file_path=file_path,
        file_type=file_path.suffix.lstrip(".").lower(),
        year=year,
        season=season,
        episode=episode,
        genres=[],
        overview=overview,
        poster_path=poster_path,
        vote_average=vote_average,
        tmdb_id=tmdb_id,
        media_type=media_type,
    )


async def process_file_for_matching(
    file_path: Path,
    *,
    engine: MatchingEngine,
    parser: AnitopyParser,
    options: MatchOptions = MatchOptions(),
) -> MatchResultBundle:
    """Process a single file through parsing and matching."""
    parsing_result = parser.parse(str(file_path.name))
    if not parsing_result:
        return MatchResultBundle(
            file_path=file_path,
            parsing=None,
            parsing_dict=None,
            match=None,
            metadata=None,
        )

    normalized = normalize_parsing_result(
        parsing_result,
        fallback_title=str(file_path.name),
    )
    parsing_dict = parsing_result_to_dict(normalized)
    match_result = await engine.find_match(parsing_dict)
    
    # Convert MatchResult to TMDBMatchResult and store in ParsingResult for organize
    tmdb_match_result = None
    if match_result:
        from anivault.shared.metadata_models import TMDBMatchResult
        tmdb_match_result = TMDBMatchResult(
            id=match_result.tmdb_id,
            title=match_result.title,
            media_type=match_result.media_type,
            year=match_result.year,  # Preserve year from MatchResult
            genres=[],  # MatchResult doesn't have genres
            overview=match_result.overview,
            vote_average=match_result.vote_average,
            poster_path=match_result.poster_path,
        )
        # Update ParsingResult with TMDB match result
        normalized.additional_info.match_result = tmdb_match_result
    
    metadata = match_result_to_file_metadata(file_path, normalized, match_result)
    _ = options

    return MatchResultBundle(
        file_path=file_path,
        parsing=normalized,
        parsing_dict=parsing_dict,
        match=match_result,
        metadata=metadata,
    )


def _coerce_str(value: object, fallback: str | None) -> str | None:
    if isinstance(value, str):
        return value
    return fallback


def _coerce_int(value: object, fallback: int | None) -> int | None:
    if isinstance(value, int):
        return value
    return fallback


__all__ = [
    "MatchOptions",
    "MatchResultBundle",
    "MatchQuery",
    "match_result_to_file_metadata",
    "normalize_parsing_result",
    "parsing_result_to_dict",
    "process_file_for_matching",
]
