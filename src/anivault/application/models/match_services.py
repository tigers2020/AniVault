"""Match use case service container (Phase 5).

Moved from cli.models for Clean Architecture - app layer owns use case dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from anivault.core.matching.engine import MatchingEngine
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.infrastructure import (
    RateLimitStateMachine,
    SemaphoreManager,
    SQLiteCacheDB,
    TMDBClient,
    TokenBucketRateLimiter,
)


@dataclass(frozen=True)
class MatchServices:
    """Match use case service container."""

    cache: SQLiteCacheDB
    rate_limiter: TokenBucketRateLimiter
    semaphore_manager: SemaphoreManager
    state_machine: RateLimitStateMachine
    tmdb_client: TMDBClient
    matching_engine: MatchingEngine
    parser: AnitopyParser
