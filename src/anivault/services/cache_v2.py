"""Cache v2 implementation for AniVault.

This module provides a high-performance, file-based JSON caching system
optimized for TMDB API responses. It uses orjson for fast serialization
and includes TTL support with automatic cleanup.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import orjson
except ImportError:
    orjson = None  # type: ignore[assignment]

from pydantic import BaseModel, Field

from anivault.core.statistics import StatisticsCollector

logger = logging.getLogger(__name__)


class CacheEntry(BaseModel):
    """Schema for cache entries with metadata and TTL support.

    This model defines the structure of cached data, including the actual
    data payload, creation timestamp, and expiration information.

    Attributes:
        data: The actual cached data payload.
        created_at: ISO timestamp when the entry was created.
        expires_at: ISO timestamp when the entry expires (None for no expiration).
        cache_type: Type of cache entry ('search' or 'details').
        key_hash: SHA-256 hash of the original key for verification.
    """

    data: dict[str, Any] = Field(..., description="The cached data payload")
    created_at: str = Field(..., description="ISO timestamp when entry was created")
    expires_at: str | None = Field(None, description="ISO timestamp when entry expires")
    cache_type: str = Field(
        ..., description="Type of cache entry ('search' or 'details')",
    )
    key_hash: str = Field(..., description="SHA-256 hash of the original key")


class JSONCacheV2:
    """High-performance JSON cache with TTL support and automatic cleanup.

    This cache system is optimized for storing TMDB API responses with
    separate subdirectories for different types of cached data. It uses
    orjson for fast serialization and includes comprehensive error handling.

    Args:
        cache_dir: Base directory path where cache files will be stored.
                  Subdirectories 'search/' and 'details/' will be created.
    """

    def __init__(
        self, cache_dir: Path | str, statistics: StatisticsCollector | None = None,
    ) -> None:
        """Initialize the cache with directory structure.

        Args:
            cache_dir: Base directory path for cache storage.
                      Will create subdirectories for different cache types.
            statistics: Optional statistics collector for performance tracking.

        Raises:
            ImportError: If orjson library is not installed.
        """
        if orjson is None:
            raise ImportError(
                "orjson library is not installed. "
                "Install it with: pip install orjson",
            )

        self.cache_dir = Path(cache_dir)
        self.search_dir = self.cache_dir / "search"
        self.details_dir = self.cache_dir / "details"
        self.statistics = statistics or StatisticsCollector()

        # Create cache directories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.search_dir.mkdir(parents=True, exist_ok=True)
        self.details_dir.mkdir(parents=True, exist_ok=True)

        # Cleanup expired entries on startup
        try:
            purged_count = self.purge_expired()
            if purged_count > 0:
                logger.info(
                    "Cleaned up %d expired cache entries on startup",
                    purged_count,
                )
        except Exception as e:
            logger.warning(
                "Failed to cleanup expired entries on startup: %s",
                str(e),
            )

        logger.debug(
            "Initialized JSONCacheV2 with directories: %s, %s, %s",
            self.cache_dir,
            self.search_dir,
            self.details_dir,
        )

    def _generate_file_path(self, key: str, cache_type: str = "search") -> Path:
        """Generate cache file path from key and cache type.

        Args:
            key: The cache key (will be normalized and hashed).
            cache_type: Type of cache ('search' or 'details').

        Returns:
            Path object pointing to the cache file.
        """
        # Normalize the key (remove special characters, convert to lowercase)
        normalized_key = key.lower().strip()

        # Generate SHA-256 hash
        key_hash = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()

        # Select appropriate directory
        if cache_type == "search":
            cache_dir = self.search_dir
        elif cache_type == "details":
            cache_dir = self.details_dir
        else:
            raise ValueError(
                f"Invalid cache_type: {cache_type}. Must be 'search' or 'details'",
            )

        # Return file path with .json extension
        return cache_dir / f"{key_hash}.json"

    def set(
        self,
        key: str,
        data: dict[str, Any],
        cache_type: str = "search",
        ttl_seconds: int | None = None,
    ) -> None:
        """Store data in the cache with optional TTL.

        Args:
            key: Unique identifier for the cache entry.
            data: Dictionary containing the data to cache.
            cache_type: Type of cache ('search' or 'details').
            ttl_seconds: Time-to-live in seconds (None for no expiration).

        Raises:
            ValueError: If cache_type is invalid.
        """
        try:
            # Generate file path
            cache_file = self._generate_file_path(key, cache_type)

            # Calculate timestamps
            now = datetime.now(timezone.utc)
            created_at = now.isoformat()
            expires_at = None

            if ttl_seconds is not None and ttl_seconds >= 0:
                expires_at = now + timedelta(seconds=ttl_seconds)
                expires_at = expires_at.isoformat()

            # Generate key hash for verification
            key_hash = hashlib.sha256(key.lower().strip().encode("utf-8")).hexdigest()

            # Create cache entry
            entry = CacheEntry(
                data=data,
                created_at=created_at,
                expires_at=expires_at,
                cache_type=cache_type,
                key_hash=key_hash,
            )

            # Serialize with orjson
            json_data = orjson.dumps(entry.model_dump())

            # Write to cache file
            with open(cache_file, "wb") as f:
                f.write(json_data)

            # Record cache operation
            self.statistics.record_cache_operation("set", hit=False, key=key)

            logger.debug(
                "Cached data for key '%s' (%s) in %s",
                key,
                cache_type,
                cache_file,
            )

        except Exception as e:
            logger.error(
                "Failed to cache data for key '%s': %s",
                key,
                str(e),
            )
            raise

    def get(self, key: str, cache_type: str = "search") -> dict[str, Any] | None:
        """Retrieve data from the cache.

        Args:
            key: Unique identifier for the cache entry.
            cache_type: Type of cache ('search' or 'details').

        Returns:
            The cached data if found and not expired, None otherwise.

        Raises:
            ValueError: If cache_type is invalid.
        """
        try:
            # Generate file path
            cache_file = self._generate_file_path(key, cache_type)

            if not cache_file.exists():
                self.statistics.record_cache_miss(cache_type)
                return None  # Cache miss

            # Read and parse the cache file
            with open(cache_file, "rb") as f:
                json_data = f.read()

            # Deserialize with orjson
            entry_dict = orjson.loads(json_data)
            entry = CacheEntry.model_validate(entry_dict)

            # Verify key hash
            expected_hash = hashlib.sha256(
                key.lower().strip().encode("utf-8"),
            ).hexdigest()
            if entry.key_hash != expected_hash:
                logger.warning(
                    "Key hash mismatch for '%s', treating as cache miss",
                    key,
                )
                return None

            # Check expiration
            if entry.expires_at is not None:
                try:
                    expires_at = datetime.fromisoformat(
                        entry.expires_at.replace("Z", "+00:00"),
                    )
                    if datetime.now(timezone.utc) > expires_at:
                        logger.debug("Cache entry expired for key '%s'", key)
                        # Delete expired file
                        cache_file.unlink()
                        return None
                except ValueError as e:
                    logger.warning(
                        "Invalid expiration timestamp for key '%s': %s",
                        key,
                        str(e),
                    )
                    return None

            logger.debug("Cache hit for key '%s' (%s)", key, cache_type)
            self.statistics.record_cache_hit(cache_type)
            return entry.data

        except FileNotFoundError:
            self.statistics.record_cache_miss(cache_type)
            return None  # Cache miss
        except ValueError as e:
            # Re-raise ValueError for invalid cache_type
            if "Invalid cache_type" in str(e):
                raise
            logger.error(
                "Error reading cache for key '%s': %s",
                key,
                str(e),
            )
            # Try to clean up corrupted file
            try:
                cache_file.unlink()
            except (OSError, NameError):
                pass
            return None
        except Exception as e:
            logger.error(
                "Error reading cache for key '%s': %s",
                key,
                str(e),
            )
            # Try to clean up corrupted file
            try:
                cache_file.unlink()
            except (OSError, NameError):
                pass
            return None

    def delete(self, key: str, cache_type: str = "search") -> bool:
        """Delete a specific cache entry.

        Args:
            key: Unique identifier for the cache entry.
            cache_type: Type of cache ('search' or 'details').

        Returns:
            True if the entry was deleted, False if it didn't exist.

        Raises:
            ValueError: If cache_type is invalid.
        """
        try:
            cache_file = self._generate_file_path(key, cache_type)
            if cache_file.exists():
                cache_file.unlink()
                logger.debug("Deleted cache entry for key '%s' (%s)", key, cache_type)
                return True
            return False
        except ValueError as e:
            # Re-raise ValueError for invalid cache_type
            if "Invalid cache_type" in str(e):
                raise
            logger.error(
                "Error deleting cache entry for key '%s': %s",
                key,
                str(e),
            )
            return False
        except Exception as e:
            logger.error(
                "Error deleting cache entry for key '%s': %s",
                key,
                str(e),
            )
            return False

    def clear(self, cache_type: str | None = None) -> int:
        """Clear cache entries.

        Args:
            cache_type: Type of cache to clear ('search', 'details', or None for all).

        Returns:
            Number of files deleted.

        Raises:
            ValueError: If cache_type is invalid.
        """
        deleted_count = 0

        try:
            if cache_type is None:
                # Clear all cache types
                for cache_dir in [self.search_dir, self.details_dir]:
                    for cache_file in cache_dir.glob("*.json"):
                        cache_file.unlink()
                        deleted_count += 1
            elif cache_type in ["search", "details"]:
                # Clear specific cache type
                cache_dir = (
                    self.search_dir if cache_type == "search" else self.details_dir
                )
                for cache_file in cache_dir.glob("*.json"):
                    cache_file.unlink()
                    deleted_count += 1
            else:
                raise ValueError(f"Invalid cache_type: {cache_type}")

            logger.info(
                "Cleared %d cache entries (%s)",
                deleted_count,
                cache_type or "all",
            )

        except Exception as e:
            logger.error("Error clearing cache: %s", str(e))
            raise

        return deleted_count

    def get_cache_info(self, cache_type: str | None = None) -> dict[str, Any]:
        """Get information about the cache.

        Args:
            cache_type: Type of cache to analyze ('search', 'details', or None for all).

        Returns:
            Dictionary containing cache statistics and information.

        Raises:
            ValueError: If cache_type is invalid.
        """
        total_files = 0
        valid_entries = 0
        expired_entries = 0
        total_size = 0

        try:
            if cache_type is None:
                cache_dirs = [self.search_dir, self.details_dir]
            elif cache_type in ["search", "details"]:
                cache_dirs = [
                    self.search_dir if cache_type == "search" else self.details_dir,
                ]
            else:
                raise ValueError(f"Invalid cache_type: {cache_type}")

            for cache_dir in cache_dirs:
                for cache_file in cache_dir.glob("*.json"):
                    total_files += 1
                    total_size += cache_file.stat().st_size

                    try:
                        # Try to read and validate the cache entry
                        with open(cache_file, "rb") as f:
                            json_data = f.read()

                        entry_dict = orjson.loads(json_data)
                        entry = CacheEntry.model_validate(entry_dict)

                        # Check if expired
                        if entry.expires_at is not None:
                            expires_at = datetime.fromisoformat(
                                entry.expires_at.replace("Z", "+00:00"),
                            )
                            if datetime.now(timezone.utc) > expires_at:
                                expired_entries += 1
                            else:
                                valid_entries += 1
                        else:
                            valid_entries += 1

                    except Exception:
                        # Corrupted or invalid file
                        expired_entries += 1

        except Exception as e:
            logger.error("Error getting cache info: %s", str(e))
            raise

        return {
            "total_files": total_files,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "total_size_bytes": total_size,
            "cache_directory": str(self.cache_dir),
            "cache_type": cache_type or "all",
        }

    def purge_expired(self, cache_type: str | None = None) -> int:
        """Remove all expired cache entries.

        Args:
            cache_type: Type of cache to purge ('search', 'details', or None for all).

        Returns:
            Number of expired entries removed.

        Raises:
            ValueError: If cache_type is invalid.
        """
        purged_count = 0

        try:
            if cache_type is None:
                cache_dirs = [self.search_dir, self.details_dir]
            elif cache_type in ["search", "details"]:
                cache_dirs = [
                    self.search_dir if cache_type == "search" else self.details_dir,
                ]
            else:
                raise ValueError(f"Invalid cache_type: {cache_type}")

            for cache_dir in cache_dirs:
                for cache_file in cache_dir.glob("*.json"):
                    try:
                        # Read and check expiration
                        with open(cache_file, "rb") as f:
                            json_data = f.read()

                        entry_dict = orjson.loads(json_data)
                        entry = CacheEntry.model_validate(entry_dict)

                        # Check if expired
                        if entry.expires_at is not None:
                            expires_at = datetime.fromisoformat(
                                entry.expires_at.replace("Z", "+00:00"),
                            )
                            if datetime.now(timezone.utc) > expires_at:
                                cache_file.unlink()
                                purged_count += 1

                    except Exception:
                        # Corrupted file, remove it
                        cache_file.unlink()
                        purged_count += 1

            logger.info(
                "Purged %d expired cache entries (%s)",
                purged_count,
                cache_type or "all",
            )

        except Exception as e:
            logger.error("Error purging expired cache entries: %s", str(e))
            raise

        return purged_count
