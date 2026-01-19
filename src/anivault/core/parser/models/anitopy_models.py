"""Typed models for anitopy parsing results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict
from collections.abc import Mapping

from anivault.shared.constants.validation_constants import (
    PARSER_ANIME_SEASON,
    PARSER_ANIME_TITLE,
    PARSER_AUDIO_TERM,
    PARSER_EPISODE_NUMBER,
    PARSER_VIDEO_RESOLUTION,
    PARSER_VIDEO_TERM,
    AnitopyFieldNames,
)


class AnitopyRaw(TypedDict, total=False):
    """External anitopy parse schema (subset)."""

    anime_title: str
    episode_number: int | str | list[int] | list[str]
    anime_season: int | str
    video_resolution: str
    source: str
    video_term: str
    audio_term: str
    release_group: str
    anime_year: int | str
    year: int | str
    file_extension: str
    title: str
    series_name: str
    show_name: str


@dataclass
class AnitopyResult:
    """Type-safe representation of anitopy parse output."""

    anime_title: str | None = None
    episode_number: int | list[int] | None = None
    anime_season: int | None = None
    video_resolution: str | None = None
    source: str | None = None
    video_term: str | None = None
    audio_term: str | None = None
    release_group: str | None = None
    anime_year: int | None = None
    year: int | None = None
    file_extension: str | None = None
    title: str | None = None
    series_name: str | None = None
    show_name: str | None = None
    _raw_dict: dict[str, object] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: object) -> AnitopyResult:
        """Create AnitopyResult from raw anitopy output."""
        if not isinstance(data, Mapping):
            raise TypeError("Anitopy output must be a mapping")

        raw_dict = _normalize_mapping(data)
        return cls(
            anime_title=_coerce_str(raw_dict.get(PARSER_ANIME_TITLE)),
            episode_number=_parse_episode_number(raw_dict.get(PARSER_EPISODE_NUMBER)),
            anime_season=_coerce_int(raw_dict.get(PARSER_ANIME_SEASON)),
            video_resolution=_coerce_str(raw_dict.get(PARSER_VIDEO_RESOLUTION)),
            source=_coerce_str(raw_dict.get(AnitopyFieldNames.SOURCE)),
            video_term=_coerce_str(raw_dict.get(PARSER_VIDEO_TERM)),
            audio_term=_coerce_str(raw_dict.get(PARSER_AUDIO_TERM)),
            release_group=_coerce_str(raw_dict.get(AnitopyFieldNames.RELEASE_GROUP)),
            anime_year=_coerce_int(raw_dict.get(AnitopyFieldNames.ANIME_YEAR)),
            year=_coerce_int(raw_dict.get(AnitopyFieldNames.YEAR)),
            file_extension=_coerce_str(raw_dict.get(AnitopyFieldNames.FILE_EXTENSION)),
            title=_coerce_str(raw_dict.get(AnitopyFieldNames.TITLE)),
            series_name=_coerce_str(raw_dict.get(AnitopyFieldNames.SERIES_NAME)),
            show_name=_coerce_str(raw_dict.get(AnitopyFieldNames.SHOW_NAME)),
            _raw_dict=raw_dict,
        )

    def get_unmapped_fields(self, mapped_fields: set[str]) -> dict[str, object]:
        """Return fields that are not mapped to ParsingResult."""
        return {key: value for key, value in self._raw_dict.items() if key not in mapped_fields}


def _normalize_mapping(data: Mapping[object, object]) -> dict[str, object]:
    return {key: value for key, value in data.items() if isinstance(key, str)}


def _coerce_str(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _coerce_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def _coerce_int_list(value: object) -> list[int] | None:
    if not isinstance(value, list):
        return None
    converted = [item for item in (_coerce_int(entry) for entry in value) if item is not None]
    return converted or None


def _parse_episode_number(value: object) -> int | list[int] | None:
    list_value = _coerce_int_list(value)
    if list_value is not None:
        return list_value
    return _coerce_int(value)
