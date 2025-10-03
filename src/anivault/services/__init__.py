"""Services module for AniVault.

This module contains service classes for external API integrations,
rate limiting, and other business logic components.
"""

from .cache_v2 import CacheEntry, JSONCacheV2
from .rate_limiter import TokenBucketRateLimiter
from .semaphore_manager import SemaphoreManager
from .state_machine import RateLimitState, RateLimitStateMachine

# Import these conditionally to avoid circular dependencies
try:
    from .metadata_enricher import EnrichedMetadata, MetadataEnricher
    from .tmdb_client import TMDBClient

    _HAS_DEPENDENCIES = True
except ImportError:
    _HAS_DEPENDENCIES = False

__all__ = [
    "CacheEntry",
    "JSONCacheV2",
    "RateLimitState",
    "RateLimitStateMachine",
    "SemaphoreManager",
    "TokenBucketRateLimiter",
]

if _HAS_DEPENDENCIES:
    __all__ += [
        "EnrichedMetadata",
        "MetadataEnricher",
        "TMDBClient",
    ]
