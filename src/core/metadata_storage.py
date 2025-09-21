"""Metadata storage system with cache-DB synchronization.

This module provides a unified interface for storing and retrieving anime metadata
with automatic synchronization between in-memory cache and SQLite database.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from .database import db_manager
from .metadata_cache import cache_manager
from .models import ParsedAnimeInfo, TMDBAnime
from .transaction_manager import transactional
from .logging_utils import log_operation_error

# Configure logging
logger = logging.getLogger(__name__)


class MetadataStorage:
    """Unified metadata storage system with cache-DB synchronization.

    This class provides a high-level interface for storing and retrieving
    anime metadata with automatic synchronization between cache and database.
    """

    def __init__(
        self,
        cache_max_size: int = 1000,
        cache_max_memory_mb: int = 100,
        cache_ttl_seconds: int | None = 3600,  # 1 hour
        enable_cache: bool = True,
        enable_db: bool = True,
    ) -> None:
        """Initialize the metadata storage system.

        Args:
            cache_max_size: Maximum number of entries in cache
            cache_max_memory_mb: Maximum memory usage for cache in MB
            cache_ttl_seconds: Cache entry TTL in seconds
            enable_cache: Whether to enable caching
            enable_db: Whether to enable database storage
        """
        # Type annotations for instance variables
        self.cache: Any | None = None
        self.db: Any | None = None

        self.enable_cache = enable_cache
        self.enable_db = enable_db

        # Initialize cache
        if self.enable_cache:
            self.cache = cache_manager.get_combined_cache()
            self.cache.set_max_size(cache_max_size)
            self.cache.set_max_memory_mb(cache_max_memory_mb)
            if cache_ttl_seconds:
                self.cache.ttl_seconds = cache_ttl_seconds
        else:
            self.cache = None

        # Initialize database
        if self.enable_db:
            self.db = db_manager
            self.db.initialize()
        else:
            self.db = None

        # Thread safety
        self._lock = threading.RLock()

        # Statistics
        self._stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "db_hits": 0,
            "db_misses": 0,
            "total_requests": 0,
            "sync_operations": 0,
        }

    @transactional
    def store_tmdb_metadata(self, session, anime: TMDBAnime) -> bool:
        """Store TMDB metadata in both cache and database with atomicity.

        Args:
            session: Database session (automatically provided by decorator)
            anime: TMDBAnime object to store

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                key = f"tmdb:{anime.tmdb_id}"
                
                # Store in database first (atomic operation)
                if self.enable_db and self.db:
                    self.db.create_anime_metadata(anime)
                    logger.debug(f"Stored TMDB metadata in database: {anime.tmdb_id}")
                
                # Only update cache after successful database operation
                if self.enable_cache and self.cache:
                    self.cache.put(key, anime)
                    logger.debug(f"Stored TMDB metadata in cache: {key}")

                self._stats["sync_operations"] += 1
                return True

            except Exception as e:
                log_operation_error("store TMDB metadata", e)
                # If database operation failed, ensure cache is not updated
                if self.enable_cache and self.cache:
                    self.cache.delete(key)
                return False

    def get_tmdb_metadata(self, tmdb_id: int) -> TMDBAnime | None:
        """Retrieve TMDB metadata from cache or database.

        Args:
            tmdb_id: TMDB ID to retrieve

        Returns:
            TMDBAnime object if found, None otherwise
        """
        with self._lock:
            self._stats["total_requests"] += 1
            key = f"tmdb:{tmdb_id}"

            # Try cache first
            if self.enable_cache and self.cache:
                cached = self.cache.get(key)
                if cached:
                    self._stats["cache_hits"] += 1
                    logger.debug(f"Retrieved TMDB metadata from cache: {key}")
                    # Ensure we return TMDBAnime or None
                    if isinstance(cached, TMDBAnime):
                        return cached
                    # If it's ParsedAnimeInfo, we can't convert it to TMDBAnime here
                    # so we'll fall through to database lookup
                else:
                    self._stats["cache_misses"] += 1

            # Try database
            if self.enable_db and self.db:
                try:
                    metadata = self.db.get_anime_metadata(tmdb_id)
                    if metadata:
                        anime = metadata.to_tmdb_anime()

                        # Store in cache for future use
                        if self.enable_cache and self.cache:
                            self.cache.put(key, anime)

                        self._stats["db_hits"] += 1
                        logger.debug(f"Retrieved TMDB metadata from database: {tmdb_id}")
                        return anime  # type: ignore[no-any-return]
                    else:
                        self._stats["db_misses"] += 1

                except Exception as e:
                    log_operation_error("retrieve TMDB metadata from database", e)
                    self._stats["db_misses"] += 1

            return None

    def search_tmdb_metadata(self, title: str, limit: int = 10) -> list[TMDBAnime]:
        """Search TMDB metadata by title.

        Args:
            title: Title to search for
            limit: Maximum number of results

        Returns:
            List of TMDBAnime objects
        """
        with self._lock:
            if not self.enable_db or not self.db:
                return []

            try:
                metadata_list = self.db.search_anime_metadata(title, limit)
                results = []

                for metadata in metadata_list:
                    anime = metadata.to_tmdb_anime()
                    results.append(anime)

                    # Cache individual results
                    if self.enable_cache and self.cache:
                        key = f"tmdb:{anime.tmdb_id}"
                        self.cache.put(key, anime)

                logger.debug(f"Found {len(results)} TMDB metadata results for: {title}")
                return results

            except Exception as e:
                log_operation_error("search TMDB metadata", e)
                return []

    @transactional
    def store_parsed_file(
        self,
        session,
        file_path: str | Path,
        filename: str,
        file_size: int,
        created_at: datetime,
        modified_at: datetime,
        parsed_info: ParsedAnimeInfo,
        tmdb_id: int | None = None,
    ) -> bool:
        """Store parsed file information in both cache and database with atomicity.

        Args:
            session: Database session (automatically provided by decorator)
            file_path: Path to the file
            filename: Name of the file
            file_size: Size of the file in bytes
            created_at: File creation time
            modified_at: File modification time
            parsed_info: Parsed anime information
            tmdb_id: Associated TMDB ID if available

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                file_path_str = str(file_path)
                key = f"file:{file_path_str}"

                # Calculate file hash for change detection
                file_hash = self._calculate_file_hash(file_path)

                # Store in database first (atomic operation)
                if self.enable_db and self.db:
                    self.db.create_parsed_file(
                        file_path=file_path,
                        filename=filename,
                        file_size=file_size,
                        created_at=created_at,
                        modified_at=modified_at,
                        parsed_info=parsed_info,
                        file_hash=file_hash,
                        metadata_id=tmdb_id,
                    )
                    logger.debug(f"Stored parsed file in database: {file_path_str}")

                # Only update cache after successful database operation
                if self.enable_cache and self.cache:
                    # Store the parsed_info directly as it implements the cache interface
                    self.cache.put(key, parsed_info)
                    logger.debug(f"Stored parsed file in cache: {key}")

                self._stats["sync_operations"] += 1
                return True

            except Exception as e:
                log_operation_error("store parsed file", e)
                # If database operation failed, ensure cache is not updated
                if self.enable_cache and self.cache:
                    self.cache.delete(key)
                return False

    def get_parsed_file(self, file_path: str | Path) -> dict[str, Any] | None:
        """Retrieve parsed file information from cache or database.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file information if found, None otherwise
        """
        with self._lock:
            self._stats["total_requests"] += 1
            file_path_str = str(file_path)
            key = f"file:{file_path_str}"

            # Try cache first
            if self.enable_cache and self.cache:
                cached = self.cache.get(key)
                if cached:
                    self._stats["cache_hits"] += 1
                    logger.debug(f"Retrieved parsed file from cache: {key}")
                    # Convert ParsedAnimeInfo to dict format
                    if hasattr(cached, "__dict__"):
                        # Convert to the same format as database result
                        result = {
                            "file_path": str(file_path),
                            "filename": getattr(cached, 'filename', ''),
                            "file_size": getattr(cached, 'file_size', 0),
                            "created_at": getattr(cached, 'created_at', None),
                            "modified_at": getattr(cached, 'modified_at', None),
                            "parsed_info": cached,
                            "tmdb_id": getattr(cached, 'tmdb_id', None),
                            "file_hash": getattr(cached, 'file_hash', None),
                        }
                        return result
                    return None
                else:
                    self._stats["cache_misses"] += 1

            # Try database
            if self.enable_db and self.db:
                try:
                    parsed_file = self.db.get_parsed_file(file_path)
                    if parsed_file:
                        # Convert to dictionary format
                        result = {
                            "file_path": parsed_file.file_path,
                            "filename": parsed_file.filename,
                            "file_size": parsed_file.file_size,
                            "created_at": parsed_file.created_at,
                            "modified_at": parsed_file.modified_at,
                            "parsed_info": parsed_file.to_parsed_anime_info(),
                            "tmdb_id": parsed_file.metadata_id,
                            "file_hash": parsed_file.file_hash,
                        }

                        # Store in cache for future use
                        if self.enable_cache and self.cache:
                            self.cache.put(key, result)

                        self._stats["db_hits"] += 1
                        logger.debug(f"Retrieved parsed file from database: {file_path_str}")
                        return result
                    else:
                        self._stats["db_misses"] += 1

                except Exception as e:
                    log_operation_error("retrieve parsed file from database", e)
                    self._stats["db_misses"] += 1

            return None

    def get_files_by_tmdb_id(self, tmdb_id: int) -> list[dict[str, Any]]:
        """Get all parsed files associated with a TMDB ID.

        Args:
            tmdb_id: TMDB ID to search for

        Returns:
            List of file information dictionaries
        """
        with self._lock:
            if not self.enable_db or not self.db:
                return []

            try:
                parsed_files = self.db.get_parsed_files_by_metadata(tmdb_id)
                results = []

                for parsed_file in parsed_files:
                    result = {
                        "file_path": parsed_file.file_path,
                        "filename": parsed_file.filename,
                        "file_size": parsed_file.file_size,
                        "created_at": parsed_file.created_at,
                        "modified_at": parsed_file.modified_at,
                        "parsed_info": parsed_file.to_parsed_anime_info(),
                        "tmdb_id": parsed_file.metadata_id,
                        "file_hash": parsed_file.file_hash,
                    }
                    results.append(result)

                logger.debug(f"Found {len(results)} files for TMDB ID: {tmdb_id}")
                return results

            except Exception as e:
                log_operation_error("get files by TMDB ID", e)
                return []

    @transactional
    def delete_parsed_file(self, session, file_path: str | Path) -> bool:
        """Delete parsed file information from both cache and database with atomicity.

        Args:
            session: Database session (automatically provided by decorator)
            file_path: Path to the file to delete

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                file_path_str = str(file_path)
                key = f"file:{file_path_str}"
                success = True

                # Remove from database first (atomic operation)
                if self.enable_db and self.db:
                    success = self.db.delete_parsed_file(file_path)
                    if success:
                        logger.debug(f"Removed parsed file from database: {file_path_str}")
                    else:
                        logger.warning(f"Failed to remove parsed file from database: {file_path_str}")
                        return False

                # Only remove from cache after successful database operation
                if self.enable_cache and self.cache:
                    self.cache.delete(key)
                    logger.debug(f"Removed parsed file from cache: {key}")

                return success

            except Exception as e:
                log_operation_error("delete parsed file", e)
                return False

    def sync_cache_to_db(self) -> int:
        """Synchronize all cache entries to database.

        Returns:
            Number of entries synchronized
        """
        with self._lock:
            if not self.enable_cache or not self.cache or not self.enable_db or not self.db:
                return 0

            try:
                synced_count = 0
                entries = self.cache.get_entries_info()

                for entry in entries:
                    key = entry["key"]
                    if key.startswith("tmdb:"):
                        # This is a TMDB metadata entry
                        cached_data = self.cache.get(key)
                        if cached_data and isinstance(cached_data, TMDBAnime):
                            self.db.create_anime_metadata(cached_data)
                            synced_count += 1
                    elif key.startswith("file:"):
                        # This is a parsed file entry
                        cached_data = self.cache.get(key)
                        if cached_data and isinstance(cached_data, dict):
                            # Reconstruct the parsed file data
                            parsed_info = cached_data.get("parsed_info")
                            if parsed_info:
                                self.db.create_parsed_file(
                                    file_path=cached_data["file_path"],
                                    filename=cached_data["filename"],
                                    file_size=cached_data["file_size"],
                                    created_at=cached_data["created_at"],
                                    modified_at=cached_data["modified_at"],
                                    parsed_info=parsed_info,
                                    file_hash=cached_data.get("file_hash"),
                                    metadata_id=cached_data.get("tmdb_id"),
                                )
                                synced_count += 1

                logger.info(f"Synchronized {synced_count} entries from cache to database")
                return synced_count

            except Exception as e:
                log_operation_error("sync cache to database", e)
                return 0

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            if self.enable_cache and self.cache:
                self.cache.clear()
                logger.info("Cleared all cache entries")

    def get_stats(self) -> dict[str, Any]:
        """Get storage system statistics."""
        with self._lock:
            stats = self._stats.copy()

            # Add cache stats
            if self.enable_cache and self.cache:
                cache_stats = self.cache.get_stats()
                stats.update(
                    {
                        "cache_hit_rate": int(cache_stats.hit_rate * 100),  # Convert to percentage
                        "cache_miss_rate": int(
                            cache_stats.miss_rate * 100
                        ),  # Convert to percentage
                        "cache_size": int(cache_stats.cache_size),
                        "cache_memory_mb": int(cache_stats.memory_usage_bytes / (1024 * 1024)),
                    }
                )

            # Add database stats
            if self.enable_db and self.db:
                db_stats = self.db.get_database_stats()
                stats.update(db_stats)

            return stats

    def reset_stats(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._stats = {
                "cache_hits": 0,
                "cache_misses": 0,
                "db_hits": 0,
                "db_misses": 0,
                "total_requests": 0,
                "sync_operations": 0,
            }

            if self.enable_cache and self.cache:
                self.cache.reset_stats()

    def _calculate_file_hash(self, file_path: str | Path) -> str | None:
        """Calculate SHA-256 hash of a file."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return None

            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            log_operation_error("calculate file hash", e)
            return None


# Global metadata storage instance
metadata_storage = MetadataStorage()
