"""Cache data models for matching engine.

This module defines strongly-typed dataclass models for cache data structures,
eliminating dict[str, Any] usage and providing type safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from anivault.shared.models.tmdb_models import TMDBSearchResult


@dataclass
class CachedSearchData:
    """Cached TMDB search results with metadata.

    This model ensures type-safe cache storage and retrieval,
    eliminating magic key access patterns like cached_data["results"].

    Attributes:
        results: List of TMDB search results
        language: Language code used for the search
        cached_at: Timestamp when data was cached

    Example:
        >>> from anivault.shared.models.tmdb_models import TMDBSearchResult
        >>> result = TMDBSearchResult(id=1, name="Test", media_type="tv", ...)
        >>> cached = CachedSearchData(results=[result], language="ko-KR")
        >>> cached.results[0].name
        'Test'
    """

    results: list[TMDBSearchResult]
    language: str = "ko-KR"
    cached_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
