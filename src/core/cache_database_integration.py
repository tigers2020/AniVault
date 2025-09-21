"""Database integration layer for cache operations.

This module provides database integration functionality for the cache system,
including loading from database, storing to database, and database health monitoring.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .cache_core import CacheCore
from .database import DatabaseManager
from .database_health import HealthStatus, get_database_health_status
from .logging_utils import log_operation_error
from .models import ParsedAnimeInfo, TMDBAnime

# Configure logging
logger = logging.getLogger(__name__)


class CacheDatabaseIntegration:
    """Database integration layer for cache operations."""

    def __init__(self, cache_core: CacheCore, db_manager: DatabaseManager | None = None) -> None:
        """Initialize database integration.

        Args:
            cache_core: Core cache instance
            db_manager: Database manager instance
        """
        self.cache_core = cache_core
        self.db_manager = db_manager
        self._auto_cache_only_enabled = False

    def enable_auto_cache_only_mode(self) -> None:
        """Enable automatic cache-only mode based on database health."""
        if self._auto_cache_only_enabled:
            return

        def health_status_callback(old_status: HealthStatus, new_status: HealthStatus) -> None:
            """Handle database health status changes."""
            if new_status == HealthStatus.UNHEALTHY:
                self.cache_core.enable_cache_only_mode("Database health check failed")
            elif new_status == HealthStatus.HEALTHY and old_status == HealthStatus.UNHEALTHY:
                self.cache_core.disable_cache_only_mode()

        # Register health status callback
        health_monitor = get_database_health_status()
        health_monitor.add_status_change_callback(health_status_callback)

        self._auto_cache_only_enabled = True
        logger.info(f"Enabled auto cache-only mode for cache '{self.cache_core.cache_name}'")

    def check_database_health_and_adapt(self) -> None:
        """Check database health and adapt cache behavior accordingly."""
        if not self.db_manager:
            return

        try:
            health_status = get_database_health_status().get_current_status()
            if health_status == HealthStatus.UNHEALTHY:
                self.cache_core.enable_cache_only_mode("Database health check failed")
            elif health_status == HealthStatus.HEALTHY:
                self.cache_core.disable_cache_only_mode()
        except Exception as e:
            logger.warning(f"Failed to check database health: {e}")
            self.cache_core.enable_cache_only_mode("Database health check error")

    def _store_in_database(self, key: str, value: ParsedAnimeInfo | TMDBAnime) -> None:
        """Store value in database.

        Args:
            key: Cache key
            value: Value to store
        """
        if not self.db_manager or self.cache_core.is_cache_only_mode():
            return

        try:
            with self.db_manager.get_session() as session:
                if isinstance(value, ParsedAnimeInfo):
                    # Store ParsedAnimeInfo
                    existing = (
                        session.query(ParsedAnimeInfo).filter_by(file_path=value.file_path).first()
                    )
                    if existing:
                        # Update existing record
                        for attr in ["title", "season", "episode", "year", "quality", "group"]:
                            setattr(existing, attr, getattr(value, attr))
                    else:
                        # Create new record
                        session.add(value)
                elif isinstance(value, TMDBAnime):
                    # Store TMDBAnime
                    existing = session.query(TMDBAnime).filter_by(tmdb_id=value.tmdb_id).first()
                    if existing:
                        # Update existing record
                        for attr in [
                            "title",
                            "original_title",
                            "overview",
                            "poster_path",
                            "backdrop_path",
                            "release_date",
                        ]:
                            setattr(existing, attr, getattr(value, attr))
                    else:
                        # Create new record
                        session.add(value)

                session.commit()
                logger.debug(f"Stored {type(value).__name__} in database for key: {key}")

        except Exception as e:
            log_operation_error(
                logger,
                f"Failed to store {type(value).__name__} in database",
                error=e,
                operation="store_database",
                cache_name=self.cache_core.cache_name,
                key=key,
            )

    def _load_from_database(self, key: str) -> ParsedAnimeInfo | TMDBAnime | None:
        """Load value from database.

        Args:
            key: Cache key

        Returns:
            Loaded value or None if not found
        """
        if not self.db_manager or self.cache_core.is_cache_only_mode():
            return None

        try:
            with self.db_manager.get_session() as session:
                # Try to determine type from key or search both tables
                # This is a simplified approach - in practice, you might want to store type info

                # Try ParsedAnimeInfo first (assuming key contains file path)
                if "file_path" in key or "parsed" in key.lower():
                    parsed_info = session.query(ParsedAnimeInfo).filter_by(file_path=key).first()
                    if parsed_info:
                        return parsed_info

                # Try TMDBAnime (assuming key contains tmdb_id)
                if "tmdb" in key.lower() or key.isdigit():
                    try:
                        tmdb_id = int(key)
                        tmdb_anime = session.query(TMDBAnime).filter_by(tmdb_id=tmdb_id).first()
                        if tmdb_anime:
                            return tmdb_anime
                    except ValueError:
                        pass

                # Fallback: search by title in both tables
                search_terms = key.split("_")
                for term in search_terms:
                    if len(term) > 2:  # Skip very short terms
                        # Search in ParsedAnimeInfo
                        parsed_info = (
                            session.query(ParsedAnimeInfo)
                            .filter(ParsedAnimeInfo.title.ilike(f"%{term}%"))
                            .first()
                        )
                        if parsed_info:
                            return parsed_info

                        # Search in TMDBAnime
                        tmdb_anime = (
                            session.query(TMDBAnime)
                            .filter(TMDBAnime.title.ilike(f"%{term}%"))
                            .first()
                        )
                        if tmdb_anime:
                            return tmdb_anime

                return None

        except Exception as e:
            log_operation_error(
                logger,
                "Failed to load from database",
                error=e,
                operation="load_database",
                cache_name=self.cache_core.cache_name,
                key=key,
            )
            return None

    def _delete_from_database(self, key: str) -> None:
        """Delete value from database.

        Args:
            key: Cache key
        """
        if not self.db_manager or self.cache_core.is_cache_only_mode():
            return

        try:
            with self.db_manager.get_session() as session:
                # Try to determine type and delete accordingly
                if "file_path" in key or "parsed" in key.lower():
                    parsed_info = session.query(ParsedAnimeInfo).filter_by(file_path=key).first()
                    if parsed_info:
                        session.delete(parsed_info)
                        session.commit()
                        logger.debug(f"Deleted ParsedAnimeInfo from database for key: {key}")
                        return

                if "tmdb" in key.lower() or key.isdigit():
                    try:
                        tmdb_id = int(key)
                        tmdb_anime = session.query(TMDBAnime).filter_by(tmdb_id=tmdb_id).first()
                        if tmdb_anime:
                            session.delete(tmdb_anime)
                            session.commit()
                            logger.debug(f"Deleted TMDBAnime from database for key: {key}")
                            return
                    except ValueError:
                        pass

        except Exception as e:
            log_operation_error(
                logger,
                "Failed to delete from database",
                error=e,
                operation="delete_database",
                cache_name=self.cache_core.cache_name,
                key=key,
            )

    def store_with_database(
        self, key: str, value: ParsedAnimeInfo | TMDBAnime, ttl_seconds: int | None = None
    ) -> None:
        """Store value in both cache and database.

        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: TTL for cache entry
        """
        # Store in cache
        self.cache_core.put(key, value, ttl_seconds)

        # Store in database
        self._store_in_database(key, value)

    def load_with_database(self, key: str) -> ParsedAnimeInfo | TMDBAnime | None:
        """Load value from cache, fallback to database.

        Args:
            key: Cache key

        Returns:
            Loaded value or None if not found
        """
        # Try cache first
        value = self.cache_core.get(key)
        if value is not None:
            return value

        # Fallback to database
        value = self._load_from_database(key)
        if value is not None:
            # Store in cache for future access
            self.cache_core.put(key, value)
            return value

        return None

    def delete_with_database(self, key: str) -> bool:
        """Delete value from both cache and database.

        Args:
            key: Cache key

        Returns:
            True if key was found and deleted
        """
        # Delete from cache
        cache_deleted = self.cache_core.delete(key)

        # Delete from database
        self._delete_from_database(key)

        return cache_deleted

    def sync_with_database(self) -> dict[str, Any]:
        """Sync cache with database.

        Returns:
            Sync statistics
        """
        if not self.db_manager or self.cache_core.is_cache_only_mode():
            return {"status": "skipped", "reason": "Database unavailable or cache-only mode"}

        try:
            stats = {
                "status": "success",
                "cache_entries": len(self.cache_core._cache),
                "database_entries": 0,
                "synced_entries": 0,
                "errors": 0,
            }

            with self.db_manager.get_session() as session:
                # Count database entries
                parsed_count = session.query(ParsedAnimeInfo).count()
                tmdb_count = session.query(TMDBAnime).count()
                stats["database_entries"] = parsed_count + tmdb_count

                # Load all database entries into cache
                for parsed_info in session.query(ParsedAnimeInfo).all():
                    key = f"parsed_{parsed_info.file_path}"
                    self.cache_core.put(key, parsed_info)
                    stats["synced_entries"] += 1

                for tmdb_anime in session.query(TMDBAnime).all():
                    key = f"tmdb_{tmdb_anime.tmdb_id}"
                    self.cache_core.put(key, tmdb_anime)
                    stats["synced_entries"] += 1

            logger.info(f"Synced cache with database: {stats}")
            return stats

        except Exception as e:
            log_operation_error(
                logger,
                "Failed to sync with database",
                error=e,
                operation="sync_database",
                cache_name=self.cache_core.cache_name,
            )
            return {
                "status": "error",
                "error": str(e),
                "cache_entries": len(self.cache_core._cache),
                "database_entries": 0,
                "synced_entries": 0,
                "errors": 1,
            }
