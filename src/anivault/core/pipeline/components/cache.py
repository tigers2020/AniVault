"""Cache implementation for AniVault pipeline.

This module provides SQLite-based caching mechanism to avoid reprocessing
files that haven't changed. Uses the same SQLite database as TMDB cache
for unified cache management.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from anivault.services.sqlite_cache_db import SQLiteCacheDB
from anivault.shared.constants import Cache
from anivault.utils.resource_path import get_project_root

logger = logging.getLogger(__name__)


class CacheV1:
    """SQLite-based cache with TTL support for pipeline parsing results.

    This class provides a caching mechanism that stores data in SQLite database
    with metadata including creation time and TTL (Time-To-Live). Uses the same
    database as TMDB cache for unified cache management.

    Args:
        cache_dir: Directory path where cache database will be stored.
                  If None, uses project root / cache directory.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize the cache with a directory path.

        Args:
            cache_dir: Directory path where cache database will be stored.
                      If None, uses project root / cache directory.
                      The directory will be created if it doesn't exist.
        """
        if cache_dir is None:
            project_root = get_project_root()
            cache_dir = project_root / "cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Use unified cache database (same as TMDB cache)
        db_path = self.cache_dir / "anivault_cache.db"
        self._sqlite_cache = SQLiteCacheDB(db_path)

    def _generate_key(self, file_path: str, mtime: float) -> str:
        """Generate a unique cache key from file path and modification time.

        Args:
            file_path: Path to the file.
            mtime: File modification time as a float.

        Returns:
            A SHA256 hash string that uniquely identifies the file and its state.
        """
        # Create a unique identifier by combining file path and modification time
        unique_string = f"{file_path}:{mtime}"

        # Generate SHA256 hash
        hash_object = hashlib.sha256(unique_string.encode("utf-8"))
        return hash_object.hexdigest()

    def set_cache(self, key: str, data: dict[str, Any], ttl_seconds: int) -> None:
        """Store data in the cache with TTL.

        Args:
            key: Unique identifier for the cache entry.
            data: Dictionary containing the data to cache.
            ttl_seconds: Time-to-live in seconds for the cache entry.
        """
        try:
            self._sqlite_cache.set_cache(
                key=key,
                data=data,
                cache_type=Cache.TYPE_PARSER,
                ttl_seconds=ttl_seconds,
            )
        except Exception as e:
            logger.warning(
                "Failed to store cache entry for key %s: %s",
                key[:50] if len(key) > 50 else key,
                str(e),
            )
            # Don't raise - cache failures should not break the pipeline

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve data from the cache.

        Args:
            key: Unique identifier for the cache entry.

        Returns:
            The cached data if found and not expired, None otherwise.
        """
        try:
            return self._sqlite_cache.get(key, cache_type=Cache.TYPE_PARSER)
        except Exception as e:
            logger.warning(
                "Failed to retrieve cache entry for key %s: %s",
                key[:50] if len(key) > 50 else key,
                str(e),
            )
            # Return None on error - treat as cache miss
            return None

    def clear(self) -> None:
        """Clear all parser cache entries.

        Removes all parser cache entries from the SQLite database.
        """
        try:
            cleared_count = self._sqlite_cache.clear(cache_type=Cache.TYPE_PARSER)
            logger.info("Cleared %d parser cache entries", cleared_count)
        except Exception as e:
            logger.warning("Failed to clear parser cache: %s", str(e))

    def get_cache_info(self) -> dict[str, Any]:
        """Get information about the cache.

        Returns:
            Dictionary containing cache statistics and information.
        """
        try:
            cache_info = self._sqlite_cache.get_cache_info()
            # Add parser-specific information
            parser_info = {
                "cache_directory": str(self.cache_dir),
                "database_path": str(self._sqlite_cache.db_path),
                "cache_type": Cache.TYPE_PARSER,
                "total_files": cache_info.get("total_files", 0),
                "valid_entries": cache_info.get("valid_entries", 0),
                "expired_entries": cache_info.get("expired_entries", 0),
                "total_size_bytes": cache_info.get("total_size_bytes", 0),
            }
            return parser_info
        except Exception as e:
            logger.warning("Failed to get cache info: %s", str(e))
            return {
                "cache_directory": str(self.cache_dir),
                "database_path": str(self._sqlite_cache.db_path),
                "cache_type": Cache.TYPE_PARSER,
                "error": str(e),
            }

    def close(self) -> None:
        """Close the SQLite cache connection.

        Should be called when the cache is no longer needed.
        """
        try:
            self._sqlite_cache.close()
        except Exception as e:
            logger.warning("Failed to close cache connection: %s", str(e))
