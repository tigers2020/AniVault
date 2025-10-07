"""Cache entry Pydantic models.

This module defines Pydantic models for SQLite cache entries,
providing type safety and validation for cached TMDB API responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from anivault.shared.constants import CacheValidationConstants


class CacheEntry(BaseModel):
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

    Example:
        >>> entry = CacheEntry(
        ...     cache_key="search:movie:test",
        ...     key_hash="a" * 64,
        ...     cache_type="search",
        ...     response_data={"results": []},
        ...     created_at=datetime.now(),
        ...     expires_at=datetime.now() + timedelta(days=7),
        ... )
    """

    # Required fields
    cache_key: str = Field(..., min_length=1, description="Original cache key")
    key_hash: str = Field(
        ...,
        min_length=CacheValidationConstants.SHA256_HASH_LENGTH,
        max_length=CacheValidationConstants.SHA256_HASH_LENGTH,
        description="SHA-256 hash of cache_key",
    )
    cache_type: Literal["search", "details"] = Field(
        ...,
        description="Type of cached data",
    )
    response_data: dict[str, Any] = Field(
        ...,
        description="Cached TMDB API response",
    )
    created_at: datetime = Field(
        ...,
        description="Entry creation timestamp",
    )

    # Optional fields with defaults
    expires_at: datetime | None = Field(
        default=None,
        description="Entry expiration timestamp (None for no expiration)",
    )
    hit_count: int = Field(
        default=0,
        ge=0,
        description="Number of cache hits",
    )
    last_accessed_at: datetime | None = Field(
        default=None,
        description="Last access timestamp",
    )
    response_size: int = Field(
        default=0,
        ge=0,
        description="Response data size in bytes",
    )
    endpoint_category: str | None = Field(
        default=None,
        description="Optional endpoint category",
    )

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @field_validator("key_hash")
    @classmethod
    def validate_key_hash_format(cls, v: str) -> str:
        """Validate that key_hash is a valid SHA-256 hex string.

        Args:
            v: key_hash value to validate

        Returns:
            Validated key_hash

        Raises:
            ValueError: If key_hash is not a valid SHA-256 hex string
        """
        if not all(c in CacheValidationConstants.HEX_CHARS for c in v.lower()):
            preview = v[: CacheValidationConstants.ERROR_MESSAGE_PREVIEW_LENGTH]
            msg = f"key_hash must be a valid hexadecimal string, got: {preview}..."
            raise ValueError(msg)
        return v.lower()

    @field_validator("expires_at")
    @classmethod
    def validate_expires_after_created(
        cls, v: datetime | None, info: Any,
    ) -> datetime | None:
        """Validate that expires_at is after created_at.

        Args:
            v: expires_at value to validate
            info: Validation info containing other field values

        Returns:
            Validated expires_at

        Raises:
            ValueError: If expires_at is before created_at
        """
        if v is not None and "created_at" in info.data:
            created_at = info.data["created_at"]
            if v < created_at:
                msg = f"expires_at ({v}) must not be before created_at ({created_at})"
                raise ValueError(msg)
        return v

    def is_expired(self) -> bool:
        """Check if cache entry is expired.

        Returns:
            True if entry is expired, False otherwise
        """
        from datetime import timezone

        if self.expires_at is None:
            return False

        # Use UTC timezone-aware datetime for comparison
        now = datetime.now(timezone.utc)

        # Handle both timezone-aware and naive datetimes
        if self.expires_at.tzinfo is None:
            # expires_at is naive, make it UTC
            expires_at_aware = self.expires_at.replace(tzinfo=timezone.utc)
            return now > expires_at_aware

        return now > self.expires_at

