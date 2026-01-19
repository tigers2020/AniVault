"""Cache entry dataclass models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from anivault.shared.constants import CacheValidationConstants
from anivault.shared.types.base import BaseDataclass

# Explicitly export for mypy
__all__ = ["CacheEntry", "CacheValidationConstants"]


@dataclass
class CacheEntry(BaseDataclass):
    """SQLite cache entry domain model.

    Represents a single cache entry in the SQLite database with
    TMDB API response data, expiration metadata, and access statistics.

    Attributes:
        cache_key: Original cache key (e.g., "Attack on Titan:lang=ko-KR")
        key_hash: SHA-256 hash of cache_key for efficient lookup
        cache_type: Type of cached data ("search" or "details")
        response_data: Cached TMDB API response as dict
        created_at: When the cache entry was created
        expires_at: When the cache entry expires (None for no expiration)
        hit_count: Number of cache hits (default: 0)
        last_accessed_at: Last access timestamp (None if never accessed)
        response_size: Size of response_data in bytes (default: 0)
        endpoint_category: Optional category for the endpoint
    """

    # Required fields
    cache_key: str
    key_hash: str
    cache_type: Literal["search", "details"]
    response_data: dict[str, Any]
    created_at: datetime

    # Optional fields with defaults
    expires_at: datetime | None = None
    hit_count: int = 0
    last_accessed_at: datetime | None = None
    response_size: int = 0
    endpoint_category: str | None = None

    def __post_init__(self) -> None:
        """Validate CacheEntry fields after initialization."""
        if not self.cache_key or not self.cache_key.strip():
            msg = "cache_key must be non-empty"
            raise ValueError(msg)

        self.cache_key = self.cache_key.strip()

        if len(self.key_hash) != CacheValidationConstants.SHA256_HASH_LENGTH:
            msg = f"key_hash must be {CacheValidationConstants.SHA256_HASH_LENGTH} " f"characters, got {len(self.key_hash)}"
            raise ValueError(msg)

        if not all(c in CacheValidationConstants.HEX_CHARS for c in self.key_hash.lower()):
            preview = self.key_hash[: CacheValidationConstants.ERROR_MESSAGE_PREVIEW_LENGTH]
            msg = f"key_hash must be a valid hexadecimal string, got: {preview}..."
            raise ValueError(msg)

        self.key_hash = self.key_hash.lower()

        if self.expires_at is not None and self.expires_at < self.created_at:
            msg = f"expires_at ({self.expires_at}) must not be before created_at ({self.created_at})"
            raise ValueError(msg)

        if self.hit_count < 0:
            msg = f"hit_count must be non-negative, got {self.hit_count}"
            raise ValueError(msg)

        if self.response_size < 0:
            msg = f"response_size must be non-negative, got {self.response_size}"
            raise ValueError(msg)

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.expires_at is None:
            return False

        now = datetime.now(timezone.utc)

        if self.expires_at.tzinfo is None:
            expires_at_aware = self.expires_at.replace(tzinfo=timezone.utc)
            return now > expires_at_aware

        return now > self.expires_at
