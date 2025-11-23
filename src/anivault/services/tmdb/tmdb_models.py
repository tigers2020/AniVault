"""TMDB API Response Models.

DEPRECATED: This module is kept for backward compatibility only.
All models have been moved to anivault.shared.models.tmdb_models
to avoid dependency layer violations.

Please use: from anivault.shared.models.tmdb_models import ...
"""

from __future__ import annotations

# Re-export from shared for backward compatibility
from anivault.shared.models.tmdb_models import (
    ScoredSearchResult,
    TMDBCandidate,
    TMDBEpisode,
    TMDBGenre,
    TMDBMediaDetails,
    TMDBSearchResponse,
    TMDBSearchResult,
)

__all__ = [
    "ScoredSearchResult",
    "TMDBCandidate",
    "TMDBEpisode",
    "TMDBGenre",
    "TMDBMediaDetails",
    "TMDBSearchResponse",
    "TMDBSearchResult",
]
