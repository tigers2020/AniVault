"""Service module export constants."""


class ServiceExports:
    """Constants for service module exports."""

    # Core services
    RATE_LIMIT_STATE = "RateLimitState"
    RATE_LIMIT_STATE_MACHINE = "RateLimitStateMachine"
    SQLITE_CACHE_DB = "SQLiteCacheDB"
    SEMAPHORE_MANAGER = "SemaphoreManager"
    TMDB_CLIENT = "TMDBClient"
    TOKEN_BUCKET_RATE_LIMITER = "TokenBucketRateLimiter"  # noqa: S105

    # Enricher services (conditional)
    ENRICHED_METADATA = "EnrichedMetadata"
    METADATA_ENRICHER = "MetadataEnricher"
