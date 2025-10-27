"""TMDB API service module.

This module provides TMDB API client and related functionality.
"""

from .tmdb_client import TMDBClient
from .tmdb_models import (
    TMDBGenre,
    TMDBSearchResult,
    ScoredSearchResult,
    TMDBCandidate,
    TMDBSearchResponse,
    TMDBEpisode,
    TMDBMediaDetails,
)
from .tmdb_strategies import (
    SearchStrategy,
    TvSearchStrategy,
    MovieSearchStrategy,
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
