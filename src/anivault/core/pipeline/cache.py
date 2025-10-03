"""Cache implementation for AniVault pipeline.

This module provides a simple, file-based JSON caching mechanism
to avoid reprocessing files that haven't changed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CacheV1:
    """Simple file-based JSON cache with TTL support.

    This class provides a caching mechanism that stores data as JSON files
    with metadata including creation time and TTL (Time-To-Live).

    Args:
        cache_dir: Directory path where cache files will be stored.
    """

    def __init__(self, cache_dir: Path) -> None:
        """Initialize the cache with a directory path.

        Args:
            cache_dir: Directory path where cache files will be stored.
                      The directory will be created if it doesn't exist.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

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
        # Create payload with metadata
        payload = {
            "data": data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": ttl_seconds,
        }

        # Write to cache file
        cache_file = self.cache_dir / f"{key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve data from the cache.

        Args:
            key: Unique identifier for the cache entry.

        Returns:
            The cached data if found and not expired, None otherwise.
        """
        cache_file = self.cache_dir / f"{key}.json"

        try:
            # Read and parse the cache file
            with open(cache_file, encoding="utf-8") as f:
                payload = json.load(f)

            # Check TTL expiration
            created_at_str = payload.get("created_at")
            ttl_seconds = payload.get("ttl_seconds", 0)

            if created_at_str and ttl_seconds > 0:
                # Parse the creation time
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00"),
                )

                # Calculate expiration time
                expiration_time = created_at.timestamp() + ttl_seconds
                current_time = datetime.now(timezone.utc).timestamp()

                # Check if expired
                if current_time > expiration_time:
                    return None  # Cache entry has expired

            # Return the cached data
            return payload.get("data")

        except FileNotFoundError:
            # Cache miss - file doesn't exist
            return None
        except (json.JSONDecodeError, KeyError, ValueError):
            # Handle corrupted cache files or invalid data
            # Log the error if logging is available, but don't raise
            # This allows the cache to gracefully handle corrupted entries
            return None

    def clear(self) -> None:
        """Clear all cache entries.

        Removes all JSON files from the cache directory.
        """
        if self.cache_dir.exists():
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()

    def get_cache_info(self) -> dict[str, Any]:
        """Get information about the cache.

        Returns:
            Dictionary containing cache statistics and information.
        """
        cache_files = (
            list(self.cache_dir.glob("*.json")) if self.cache_dir.exists() else []
        )

        total_size = 0
        valid_entries = 0
        expired_entries = 0

        for cache_file in cache_files:
            try:
                # Get file size
                total_size += cache_file.stat().st_size

                # Check if entry is valid and not expired
                with open(cache_file, encoding="utf-8") as f:
                    payload = json.load(f)

                created_at_str = payload.get("created_at")
                ttl_seconds = payload.get("ttl_seconds", 0)

                if created_at_str and ttl_seconds > 0:
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00"),
                    )
                    expiration_time = created_at.timestamp() + ttl_seconds
                    current_time = datetime.now(timezone.utc).timestamp()

                    if current_time > expiration_time:
                        expired_entries += 1
                    else:
                        valid_entries += 1
                else:
                    valid_entries += 1

            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                # Handle corrupted or inaccessible files
                expired_entries += 1

        return {
            "total_files": len(cache_files),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "total_size_bytes": total_size,
            "cache_directory": str(self.cache_dir),
        }
