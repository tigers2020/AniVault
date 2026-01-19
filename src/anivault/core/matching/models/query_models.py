"""Query models for matching engine inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from anivault.core.normalization import normalize_query_from_anitopy
from anivault.core.parser.models import ParsingResult

if TYPE_CHECKING:
    from anivault.core.matching.models import NormalizedQuery


@dataclass
class MatchQuery:
    """Matching engine input query data model."""

    anime_title: str
    episode: str | None = None
    season: str | None = None
    release_group: str | None = None
    video_resolution: str | None = None
    year: int | None = None

    @classmethod
    def from_parsing_result(cls, result: ParsingResult) -> MatchQuery:
        """Create MatchQuery from ParsingResult."""
        return cls(
            anime_title=result.title,
            episode=_coerce_str(result.episode),
            season=_coerce_str(result.season),
            release_group=result.release_group,
            video_resolution=result.quality,
            year=result.year,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MatchQuery:
        """Create MatchQuery from dict (backward compatibility)."""
        return cls(
            anime_title=_coerce_str(data.get("anime_title")) or "",
            episode=_coerce_str(data.get("episode")) or _coerce_str(data.get("episode_number")),
            season=_coerce_str(data.get("season")) or _coerce_str(data.get("anime_season")),
            release_group=_coerce_str(data.get("release_group")),
            video_resolution=_coerce_str(data.get("video_resolution")),
            year=_coerce_int(data.get("year")) or _coerce_int(data.get("anime_year")),
        )

    def to_normalized_query(self) -> NormalizedQuery | None:
        """Convert MatchQuery to NormalizedQuery."""
        normalized = normalize_query_from_anitopy(
            {
                "anime_title": self.anime_title,
                "anime_year": self.year,
            },
        )
        return normalized


def _coerce_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
