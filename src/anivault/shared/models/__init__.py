"""Shared model exports.

FileMetadata, TMDBMatchResult: domain.entities.metadata
ParsingResult, ParsingAdditionalInfo: domain.entities.parser
"""

from .cache import CacheEntry
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
    "ScoredSearchResult",
    "TMDBCandidate",
    "TMDBEpisode",
    "TMDBGenre",
    "TMDBMediaDetails",
    "TMDBSearchResponse",
    "TMDBSearchResult",
]
