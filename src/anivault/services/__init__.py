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
from anivault.shared.constants.service_exports import ServiceExports

# Import these conditionally to avoid circular dependencies
try:
    from .enricher import MetadataEnricher
    from .metadata_enricher.models import EnrichedMetadata

    _HAS_ENRICHER = True
except ImportError:
    _HAS_ENRICHER = False

__all__ = [
    ServiceExports.RATE_LIMIT_STATE,
    ServiceExports.RATE_LIMIT_STATE_MACHINE,
    ServiceExports.SQLITE_CACHE_DB,
    ServiceExports.SEMAPHORE_MANAGER,
    ServiceExports.TMDB_CLIENT,
    ServiceExports.TOKEN_BUCKET_RATE_LIMITER,
]

if _HAS_ENRICHER:
    __all__ += [
        ServiceExports.ENRICHED_METADATA,
        ServiceExports.METADATA_ENRICHER,
    ]
