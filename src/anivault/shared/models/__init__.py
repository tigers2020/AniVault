"""Shared model exports."""

from .cache import CacheEntry
from .metadata import FileMetadata, TMDBMatchResult
from .parser import ParsingAdditionalInfo, ParsingResult
from .tmdb_models import (
    ScoredSearchResult,
    TMDBCandidate,
    TMDBEpisode,
    TMDBGenre,
    TMDBMediaDetails,
    TMDBSearchResponse,
    TMDBSearchResult,
)

__all__ = [
    "CacheEntry",
    "FileMetadata",
    "ParsingAdditionalInfo",
    "ParsingResult",
    "ScoredSearchResult",
    "TMDBCandidate",
    "TMDBEpisode",
    "TMDBGenre",
    "TMDBMatchResult",
    "TMDBMediaDetails",
    "TMDBSearchResponse",
    "TMDBSearchResult",
]
