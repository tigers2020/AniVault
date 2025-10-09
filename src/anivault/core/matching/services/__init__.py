"""Matching engine service layer.

This module contains service classes that encapsulate specific responsibilities
of the matching engine, following the Single Responsibility Principle.
"""

from __future__ import annotations

from .cache_adapter import CacheAdapterProtocol, SQLiteCacheAdapter
from .scoring_service import CandidateScoringService
from .search_service import TMDBSearchService

__all__ = [
    "CacheAdapterProtocol",
    "CandidateScoringService",
    "SQLiteCacheAdapter",
    "TMDBSearchService",
]
