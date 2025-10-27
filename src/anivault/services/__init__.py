"""Services module for AniVault.

This module contains service classes for external API integrations,
rate limiting, and other business logic components.
"""

from anivault.shared.constants.service_exports import ServiceExports

from .rate_limiter import TokenBucketRateLimiter
from .semaphore_manager import SemaphoreManager
from .state_machine import RateLimitState, RateLimitStateMachine

# Import from submodules
from .cache import SQLiteCacheDB
from .tmdb import TMDBClient

# Import these conditionally to avoid circular dependencies
# Note: MetadataEnricher is imported directly from enricher.py to avoid circular imports
_HAS_ENRICHER = True

__all__ = [
    "RateLimitState",
    "RateLimitStateMachine",
    "SQLiteCacheDB",
    "SemaphoreManager",
    "TMDBClient",
    "TokenBucketRateLimiter",
]

if _HAS_ENRICHER:
    from .enricher import MetadataEnricher

    __all__ += [
        "MetadataEnricher",
    ]
