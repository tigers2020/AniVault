"""Dependency Injection container for AniVault.

This module provides a centralized DI container using dependency-injector
to manage service dependencies and avoid circular imports.

The container manages:
- Settings (Singleton)
- Rate limiting components (TokenBucketRateLimiter, SemaphoreManager, RateLimitStateMachine)
- TMDB client and related services
- Cache adapters (SQLiteCacheDB, SQLiteCacheAdapter)
- Matching engine
- File organizer (when log_manager is provided)
"""

from __future__ import annotations

from dependency_injector import containers, providers

from anivault.config.loader import load_settings
from anivault.core.matching.engine import MatchingEngine
from anivault.core.matching.services.cache_adapter import SQLiteCacheAdapter
from anivault.services import (
    RateLimitStateMachine,
    SemaphoreManager,
    SQLiteCacheDB,
    TMDBClient,
    TokenBucketRateLimiter,
)
from anivault.shared.constants.system import FileSystem
from anivault.utils.resource_path import get_project_root


class Container(containers.DeclarativeContainer):
    """Dependency Injection container for AniVault services.

    This container manages the lifecycle and dependencies of core services,
    ensuring proper initialization order and avoiding circular dependencies.

    Example:
        >>> container = Container()
        >>> container.wire(modules=[__name__])
        >>> matching_engine = container.matching_engine()
        >>> result = await matching_engine.find_match(anitopy_result)
    """

    # Configuration
    config = providers.Singleton(load_settings)

    # Cache path provider
    cache_db_path = providers.Singleton(
        lambda: get_project_root() / FileSystem.CACHE_DIRECTORY / "tmdb_cache.db"
    )

    # Cache services
    sqlite_cache_db = providers.Factory(
        SQLiteCacheDB,
        db_path=cache_db_path,
    )

    cache_adapter = providers.Factory(
        SQLiteCacheAdapter,
        backend=sqlite_cache_db,
        language=providers.Object("ko-KR"),
    )

    # Rate limiting components
    rate_limiter = providers.Factory(
        TokenBucketRateLimiter,
        capacity=providers.Callable(
            lambda config: int(config.api.tmdb.rate_limit_rps),
            config=config,
        ),
        refill_rate=providers.Callable(
            lambda config: int(config.api.tmdb.rate_limit_rps),
            config=config,
        ),
    )

    semaphore_manager = providers.Factory(
        SemaphoreManager,
        concurrency_limit=providers.Callable(
            lambda config: int(config.api.tmdb.concurrent_requests),
            config=config,
        ),
    )

    state_machine = providers.Factory(RateLimitStateMachine)

    # TMDB client
    tmdb_client = providers.Factory(
        TMDBClient,
        rate_limiter=rate_limiter,
        semaphore_manager=semaphore_manager,
        state_machine=state_machine,
    )

    # Matching engine
    matching_engine = providers.Factory(
        MatchingEngine,
        cache_adapter=cache_adapter,
        tmdb_client=tmdb_client,
    )
