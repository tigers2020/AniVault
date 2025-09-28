"""Enhanced caching system v2 with TTL and versioning."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    value: Any
    created_at: float
    expires_at: float | None
    access_count: int = 0
    last_accessed: float | None = None
    version: str = "1.0"
    tags: list[str] | None = None

    def is_expired(self) -> bool:
        """Check if cache entry is expired.

        Returns:
            True if expired, False otherwise
        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self) -> None:
        """Update access information."""
        self.access_count += 1
        self.last_accessed = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheEntry:
        """Create from dictionary."""
        return cls(**data)


class CacheV2:
    """Enhanced caching system with TTL, versioning, and statistics."""

    def __init__(self, cache_dir: Path | None = None, default_ttl: int = 86400):
        """Initialize cache v2.

        Args:
            cache_dir: Directory for cache files
            default_ttl: Default TTL in seconds (24 hours)
        """
        self.cache_dir = cache_dir or Path(".cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        self.entries: dict[str, CacheEntry] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "expired": 0,
        }

        # Load existing cache
        self._load_cache()

    def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.entries:
            self.stats["misses"] += 1
            return None

        entry = self.entries[key]

        # Check if expired
        if entry.is_expired():
            del self.entries[key]
            self.stats["expired"] += 1
            self.stats["misses"] += 1
            return None

        # Update access info
        entry.touch()
        self.stats["hits"] += 1

        logger.debug(f"Cache hit for key: {key}")
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        version: str = "1.0",
        tags: list[str] | None = None,
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            version: Version string
            tags: Optional tags for categorization
        """
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=expires_at,
            version=version,
            tags=tags,
        )

        self.entries[key] = entry
        self.stats["sets"] += 1

        logger.debug(f"Cache set for key: {key}, TTL: {ttl}s")

    def delete(self, key: str) -> bool:
        """Delete entry from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False if not found
        """
        if key in self.entries:
            del self.entries[key]
            self.stats["deletes"] += 1
            logger.debug(f"Cache delete for key: {key}")
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self.entries.clear()
        logger.info("Cache cleared")

    def clear_expired(self) -> int:
        """Clear expired entries.

        Returns:
            Number of expired entries removed
        """
        expired_keys = []
        for key, entry in self.entries.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self.entries[key]

        self.stats["expired"] += len(expired_keys)
        logger.info(f"Cleared {len(expired_keys)} expired entries")
        return len(expired_keys)

    def clear_by_tag(self, tag: str) -> int:
        """Clear entries by tag.

        Args:
            tag: Tag to match

        Returns:
            Number of entries removed
        """
        tagged_keys = []
        for key, entry in self.entries.items():
            if entry.tags and tag in entry.tags:
                tagged_keys.append(key)

        for key in tagged_keys:
            del self.entries[key]

        logger.info(f"Cleared {len(tagged_keys)} entries with tag: {tag}")
        return len(tagged_keys)

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary containing cache statistics
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / max(1, total_requests)

        return {
            "entries_count": len(self.entries),
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "sets": self.stats["sets"],
            "deletes": self.stats["deletes"],
            "expired": self.stats["expired"],
            "total_requests": total_requests,
        }

    def get_entries_by_tag(self, tag: str) -> list[CacheEntry]:
        """Get all entries with a specific tag.

        Args:
            tag: Tag to match

        Returns:
            List of cache entries
        """
        return [
            entry for entry in self.entries.values() if entry.tags and tag in entry.tags
        ]

    def _load_cache(self) -> None:
        """Load cache from disk."""
        cache_file = self.cache_dir / "cache_v2.json"
        if not cache_file.exists():
            return

        try:
            with open(cache_file, encoding="utf-8") as f:
                data = json.load(f)

            for key, entry_data in data.get("entries", {}).items():
                entry = CacheEntry.from_dict(entry_data)
                # Only load non-expired entries
                if not entry.is_expired():
                    self.entries[key] = entry
                else:
                    self.stats["expired"] += 1

            logger.info(f"Loaded {len(self.entries)} cache entries")

        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")

    def save_cache(self) -> None:
        """Save cache to disk."""
        cache_file = self.cache_dir / "cache_v2.json"

        try:
            # Clear expired entries before saving
            self.clear_expired()

            data = {
                "version": "2.0",
                "created_at": time.time(),
                "entries": {
                    key: entry.to_dict() for key, entry in self.entries.items()
                },
                "stats": self.stats,
            }

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self.entries)} cache entries")

        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.save_cache()
