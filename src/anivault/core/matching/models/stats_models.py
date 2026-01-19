"""Cache statistics models for matching engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CacheStats:
    """Cache statistics data model."""

    hit_ratio: float
    total_requests: int
    cache_items: int
    cache_mode: str
    cache_type: str

    def to_dict(self) -> dict[str, Any]:
        """Convert CacheStats to dict for JSON serialization."""
        return {
            "hit_ratio": self.hit_ratio,
            "total_requests": self.total_requests,
            "cache_items": self.cache_items,
            "cache_mode": self.cache_mode,
            "cache_type": self.cache_type,
        }
