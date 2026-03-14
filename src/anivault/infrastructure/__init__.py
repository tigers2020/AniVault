"""Infrastructure layer (Phase 5).

DEPRECATED: No code in the codebase imports this package. Use
``anivault.services`` directly (e.g. ``from anivault.services import SQLiteCacheDB, TMDBClient``).
This package may be removed in a future release.
"""

from anivault.services import (
    MetadataEnricher,
    RateLimitState,
    RateLimitStateMachine,
    SemaphoreManager,
    SQLiteCacheDB,
    TMDBClient,
    TokenBucketRateLimiter,
)

__all__ = [
    "MetadataEnricher",
    "RateLimitState",
    "RateLimitStateMachine",
    "SQLiteCacheDB",
    "SemaphoreManager",
    "TMDBClient",
    "TokenBucketRateLimiter",
]
