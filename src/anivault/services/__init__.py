"""Services module for AniVault.

This module contains service classes for external API integrations,
rate limiting, and other business logic components.
"""

from .rate_limiter import TokenBucketRateLimiter
from .semaphore_manager import SemaphoreManager
from .sqlite_cache_db import SQLiteCacheDB
from .state_machine import RateLimitState, RateLimitStateMachine

# Direct imports (no circular dependency)
from .tmdb_client import TMDBClient

# Import these conditionally to avoid circular dependencies
try:
    from .enricher import MetadataEnricher
    from .metadata_enricher.models import EnrichedMetadata

    _HAS_ENRICHER = True
except ImportError as e:
    _HAS_ENRICHER = False
    # Log the import error for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Could not import MetadataEnricher: {e}")

__all__ = [
    "RateLimitState",
    "RateLimitStateMachine",
    "SQLiteCacheDB",
    "SemaphoreManager",
    "TMDBClient",
    "TokenBucketRateLimiter",
]

if _HAS_ENRICHER:
    __all__ += [
        "EnrichedMetadata",
        "MetadataEnricher",
    ]
