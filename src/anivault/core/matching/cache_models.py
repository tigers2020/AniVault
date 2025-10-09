"""Cache data models for matching engine.

This module defines strongly-typed Pydantic models for cache data structures,
eliminating dict[str, Any] usage and providing type safety.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from anivault.services.tmdb_models import TMDBSearchResult


class CachedSearchData(BaseModel):
    """Cached TMDB search results with metadata.

    This model ensures type-safe cache storage and retrieval,
    eliminating magic key access patterns like cached_data["results"].

    Attributes:
        results: List of TMDB search results
        language: Language code used for the search
        cached_at: Timestamp when data was cached

    Example:
        >>> from anivault.services.tmdb_models import TMDBSearchResult
        >>> result = TMDBSearchResult(id=1, name="Test", media_type="tv", ...)
        >>> cached = CachedSearchData(results=[result], language="ko-KR")
        >>> cached.results[0].name
        'Test'
    """

    results: list[TMDBSearchResult] = Field(
        description="List of TMDB search results",
    )
    language: str = Field(
        default="ko-KR",
        description="Language code used for the search",
    )
    cached_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when data was cached (UTC)",
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

