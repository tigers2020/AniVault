"""Infrastructure layer (Phase 5).

DEPRECATED: No code in the codebase imports this package. Use
``anivault.services`` directly (e.g. ``from anivault.services import SQLiteCacheDB``).
TMDB: use ``from anivault.services.tmdb import TMDBClient``. S1: infrastructure/tmdb removed.
This package may be removed in a future release (S6).
"""

from anivault.services import (
    MetadataEnricher,
    RateLimitState,
    RateLimitStateMachine,
    SemaphoreManager,
    SQLiteCacheDB,
    TokenBucketRateLimiter,
)

__all__ = [
    "MetadataEnricher",
    "RateLimitState",
    "RateLimitStateMachine",
    "SQLiteCacheDB",
    "SemaphoreManager",
    "TokenBucketRateLimiter",
]
