"""Type definitions for match command JSON output."""

from __future__ import annotations

from typing import TypedDict


class MatchSummaryDict(TypedDict):
    """Match summary output."""

    total_files: int
    successful_matches: int
    high_confidence_matches: int
    medium_confidence_matches: int
    low_confidence_matches: int
    errors: int
    total_size_bytes: int
    total_size_formatted: str
    scanned_directory: str
    success_rate: float


class FileStatisticsDict(TypedDict):
    """File statistics output."""

    counts_by_extension: dict[str, int]
    scanned_paths: list[str]


class MatchTmdbDataDict(TypedDict, total=False):
    """TMDB match data output."""

    id: int
    title: str
    media_type: str | None
    poster_path: str | None
    overview: str | None
    vote_average: float | None


class MatchResultInfoDict(TypedDict):
    """Match result output."""

    match_confidence: float
    tmdb_data: MatchTmdbDataDict | None
    enrichment_status: str


class MatchFileInfoDict(TypedDict):
    """Matched file output."""

    file_path: str
    file_name: str
    file_size: int
    file_extension: str
    title: str | None
    year: int | None
    season: int | None
    episode: int | None
    match_result: MatchResultInfoDict


class MatchDataDict(TypedDict):
    """Match command JSON output."""

    match_summary: MatchSummaryDict
    file_statistics: FileStatisticsDict
    files: list[MatchFileInfoDict]


class MatchStatisticsDict(TypedDict):
    """Internal statistics for matching results."""

    successful_matches: int
    high_confidence: int
    medium_confidence: int
    low_confidence: int
    errors: int


class FileStatisticsInternalDict(TypedDict):
    """Internal statistics for match results."""

    total_size: int
    file_counts: dict[str, int]
    scanned_paths: list[str]
    file_data: list[MatchFileInfoDict]


__all__ = [
    "FileStatisticsDict",
    "FileStatisticsInternalDict",
    "MatchDataDict",
    "MatchFileInfoDict",
    "MatchResultInfoDict",
    "MatchStatisticsDict",
    "MatchSummaryDict",
    "MatchTmdbDataDict",
]
