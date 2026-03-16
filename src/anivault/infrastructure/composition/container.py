"""Dependency Injection container for AniVault.

This module provides a centralized DI container using dependency-injector
to manage service dependencies and avoid circular imports.

The container manages:
- Settings (Singleton)
- Rate limiting components (TokenBucketRateLimiter, SemaphoreManager,
  RateLimitStateMachine)
- TMDB client and related services
- Cache adapters (SQLiteCacheDB, SQLiteCacheAdapter)
- Matching engine
- File organizer (when log_manager is provided)
"""

from __future__ import annotations

# pylint: disable=import-error  # dependency_injector is an optional dependency
from dependency_injector import containers, providers

from anivault.application.adapters.organize import (
    CoreOperationLoggerAdapter,
    CoreOrganizePlanEngineAdapter,
)
from anivault.application.models.match_services import MatchServices
from anivault.application.use_cases.build_groups_use_case import BuildGroupsUseCase
from anivault.application.use_cases.match_use_case import MatchUseCase
from anivault.application.use_cases.organize_use_case import OrganizeUseCase
from anivault.application.use_cases.run_use_case import RunUseCase
from anivault.application.use_cases.scan_use_case import ScanUseCase
from anivault.application.use_cases.verify_use_case import VerifyUseCase
from anivault.config.loader import load_settings
from anivault.core.matching.engine import MatchingEngine
from anivault.core.matching.services.cache_adapter import SQLiteCacheAdapter
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.infrastructure import (
    MetadataEnricher,
    RateLimitStateMachine,
    SemaphoreManager,
    SQLiteCacheDB,
    TMDBClient,
    TokenBucketRateLimiter,
)
from anivault.shared.constants.system import FileSystem
from anivault.shared.constants.validation_constants import TMDB_CACHE_DB
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
    cache_db_path = providers.Singleton(lambda: get_project_root() / FileSystem.CACHE_DIRECTORY / TMDB_CACHE_DB)

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

    # Parser (for MatchServices)
    parser = providers.Factory(AnitopyParser)

    # Match use case services bundle
    match_services = providers.Factory(
        MatchServices,
        cache=sqlite_cache_db,
        rate_limiter=rate_limiter,
        semaphore_manager=semaphore_manager,
        state_machine=state_machine,
        tmdb_client=tmdb_client,
        matching_engine=matching_engine,
        parser=parser,
    )

    # Metadata enricher (Phase R4A — scan handler enrich step)
    # R5: defined before scan_use_case so it can be injected
    metadata_enricher = providers.Factory(MetadataEnricher, tmdb_client=tmdb_client)

    # Organize adapters (Phase 2 port-based internalization)
    # These are the ONLY callers allowed to instantiate concrete core adapters.
    organize_logger_adapter = providers.Singleton(CoreOperationLoggerAdapter)
    organize_plan_engine_adapter = providers.Singleton(CoreOrganizePlanEngineAdapter)

    # Use case providers (Phase R0.5, R3, R4A, R5)
    # R5: enricher wired here so scan_handler never imports MetadataEnricher directly
    # Phase 2: logger and plan_engine ports injected so OrganizeUseCase is core-free
    scan_use_case = providers.Factory(ScanUseCase, enricher=metadata_enricher)
    match_use_case = providers.Factory(MatchUseCase, services=match_services)
    organize_use_case = providers.Factory(
        OrganizeUseCase,
        logger=organize_logger_adapter,
        plan_engine=organize_plan_engine_adapter,
    )
    build_groups_use_case = providers.Factory(BuildGroupsUseCase)

    # Run use case (Phase R4B) — orchestrates scan → match → organize
    run_use_case = providers.Factory(
        RunUseCase,
        scan_use_case=scan_use_case,
        match_use_case=match_use_case,
        organize_use_case=organize_use_case,
    )

    # Verify use case (Phase R4B) — TMDB connectivity check in app layer
    verify_use_case = providers.Factory(VerifyUseCase, tmdb_client=tmdb_client)
