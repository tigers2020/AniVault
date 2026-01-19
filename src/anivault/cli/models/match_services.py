"""Typed service container for match CLI helpers."""

from __future__ import annotations

from dataclasses import dataclass

from anivault.core.matching.engine import MatchingEngine
from anivault.core.parser.anitopy_parser import AnitopyParser
from anivault.services import (
    RateLimitStateMachine,
    SemaphoreManager,
    SQLiteCacheDB,
    TMDBClient,
    TokenBucketRateLimiter,
)


@dataclass(frozen=True)
class MatchServices:
    """Match command service container."""

    cache: SQLiteCacheDB
    rate_limiter: TokenBucketRateLimiter
    semaphore_manager: SemaphoreManager
    state_machine: RateLimitStateMachine
    tmdb_client: TMDBClient
    matching_engine: MatchingEngine
    parser: AnitopyParser
