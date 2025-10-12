"""Services module for AniVault.

This module contains service classes for external API integrations,
rate limiting, and other business logic components.
"""

from .rate_limiter import TokenBucketRateLimiter
from .semaphore_manager import SemaphoreManager
from .sqlite_cache_db import SQLiteCacheDB
from .state_machine import RateLimitState, RateLimitStateMachine

# Import these conditionally to avoid circular dependencies
try:
    from .enricher import MetadataEnricher
    from .metadata_enricher.models import EnrichedMetadata
    from .tmdb_client import TMDBClient

    _HAS_DEPENDENCIES = True
except ImportError:
    _HAS_DEPENDENCIES = False

__all__ = [
    "RateLimitState",
    "RateLimitStateMachine",
    "SQLiteCacheDB",
    "SemaphoreManager",
    "TokenBucketRateLimiter",
]

if _HAS_DEPENDENCIES:
    __all__ += [
        "EnrichedMetadata",
        "MetadataEnricher",
        "TMDBClient",
    ]
