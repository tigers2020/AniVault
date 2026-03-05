"""TMDB API infrastructure (Phase 5).

Re-exports from services.tmdb for backward compatibility.
"""

from anivault.services.tmdb import (
    MovieSearchStrategy,
    ScoredSearchResult,
    SearchStrategy,
    TMDBCandidate,
    TMDBClient,
    TMDBEpisode,
    TMDBGenre,
    TMDBMediaDetails,
    TMDBSearchResponse,
    TMDBSearchResult,
    TvSearchStrategy,
    generate_shortened_titles,
)

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
