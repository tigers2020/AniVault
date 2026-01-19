"""TMDB API service module.

This module provides TMDB API client and related functionality.
"""

# Re-export models from shared to maintain backward compatibility
from anivault.shared.models.api.tmdb import (
    ScoredSearchResult,
    TMDBCandidate,
    TMDBEpisode,
    TMDBGenre,
    TMDBMediaDetails,
    TMDBSearchResponse,
    TMDBSearchResult,
)

from .tmdb_client import TMDBClient
from .tmdb_strategies import (
    MovieSearchStrategy,
    SearchStrategy,
    TvSearchStrategy,
)
from .tmdb_utils import generate_shortened_titles

__all__ = [
    "MovieSearchStrategy",
    "ScoredSearchResult",
    "SearchStrategy",
    "TMDBCandidate",
    "TMDBClient",
    "TMDBEpisode",
    "TMDBGenre",
    "TMDBMediaDetails",
    "TMDBSearchResponse",
    "TMDBSearchResult",
    "TvSearchStrategy",
    "generate_shortened_titles",
]
