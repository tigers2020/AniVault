"""Cache configuration model.

This module contains the cache configuration model for managing
caching behavior including TTL, size limits, and backend selection.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from anivault.shared.constants import Cache, FileSystem


class CacheSettings(BaseModel):
    """Cache configuration.

    This class manages caching behavior including cache backend,
    TTL (time-to-live), and size limitations.
    """

    enabled: bool = Field(default=True, description="Enable caching")
    ttl: int = Field(
        default=Cache.TTL,
        gt=0,
        description="Cache time-to-live in seconds",
    )
    max_size: int = Field(
        default=Cache.MAX_SIZE,
        gt=0,
        description="Maximum cache size",
    )
    backend: str = Field(
        default=FileSystem.CACHE_BACKEND,
        description="Cache backend (memory, redis, sqlite)",
    )


# Backward compatibility alias
CacheConfig = CacheSettings


__all__ = [
    "CacheConfig",  # Backward compatibility
    "CacheSettings",
]
