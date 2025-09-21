"""Incremental synchronization for cache system.

This module provides incremental synchronization functionality for keeping
cache and database in sync efficiently.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from .cache_core import CacheCore
from .cache_database_integration import CacheDatabaseIntegration
from .incremental_sync import IncrementalSyncManager
from .logging_utils import log_operation_error
from .models import ParsedAnimeInfo, TMDBAnime
from .sync_monitoring import SyncOperationStatus, SyncOperationType, sync_monitor

# Configure logging
logger = logging.getLogger(__name__)


class CacheIncrementalSync:
    """Incremental synchronization for cache system."""

    def __init__(
        self,
        cache_core: CacheCore,
        db_integration: CacheDatabaseIntegration,
        incremental_sync_manager: IncrementalSyncManager | None = None,
    ) -> None:
        """Initialize incremental sync.

        Args:
            cache_core: Core cache instance
            db_integration: Database integration instance
            incremental_sync_manager: Incremental sync manager
        """
        self.cache_core = cache_core
        self.db_integration = db_integration
        self.incremental_sync_manager = incremental_sync_manager
        self._incremental_sync_enabled = False

    def enable_incremental_sync(self) -> None:
        """Enable incremental synchronization."""
        self._incremental_sync_enabled = True
        logger.info(f"Enabled incremental sync for cache '{self.cache_core.cache_name}'")

    def disable_incremental_sync(self) -> None:
        """Disable incremental synchronization."""
        self._incremental_sync_enabled = False
        logger.info(f"Disabled incremental sync for cache '{self.cache_core.cache_name}'")

    def is_incremental_sync_enabled(self) -> bool:
        """Check if incremental sync is enabled.

        Returns:
            True if incremental sync is enabled
        """
        return self._incremental_sync_enabled

    def get_incremental_sync_manager(self) -> IncrementalSyncManager | None:
        """Get incremental sync manager.

        Returns:
            Incremental sync manager or None
        """
        return self.incremental_sync_manager

    def sync_tmdb_metadata_incremental(
        self, session: Session, last_sync_timestamp: float | None = None, batch_size: int = 100
    ) -> dict[str, Any]:
        """Incremental sync for TMDB metadata.

        Args:
            session: Database session
            last_sync_timestamp: Last sync timestamp
            batch_size: Batch size for processing

        Returns:
            Sync statistics
        """
        if not self._incremental_sync_enabled:
            return {"status": "disabled", "reason": "Incremental sync not enabled"}

        operation_id = sync_monitor.start_operation(
            SyncOperationType.INCREMENTAL_SYNC_TMDB,
            batch_size,
            cache_name=self.cache_core.cache_name,
        )

        try:
            # Get incremental sync manager
            sync_manager = self.get_incremental_sync_manager()
            if not sync_manager:
                return {"status": "error", "reason": "No incremental sync manager available"}

            # Get last sync timestamp
            if last_sync_timestamp is None:
                last_sync_timestamp = sync_manager.get_last_sync_timestamp("tmdb_metadata")

            # Query for updated records
            query = session.query(TMDBAnime)
            if last_sync_timestamp:
                query = query.filter(TMDBAnime.updated_at > last_sync_timestamp)

            updated_anime = query.limit(batch_size).all()

            synced_count = 0
            errors = 0

            for anime in updated_anime:
                try:
                    # Update cache
                    key = f"tmdb_{anime.tmdb_id}"
                    self.cache_core.put(key, anime)
                    synced_count += 1

                except Exception as e:
                    errors += 1
                    log_operation_error(
                        logger,
                        f"Failed to sync TMDB anime {anime.tmdb_id}",
                        error=e,
                        operation="incremental_sync_tmdb_item",
                        cache_name=self.cache_core.cache_name,
                        key=f"tmdb_{anime.tmdb_id}",
                    )

            # Update last sync timestamp
            if synced_count > 0:
                sync_manager.update_last_sync_timestamp("tmdb_metadata")

            # Update sync monitor
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.COMPLETED, synced_count, errors
            )

            result = {
                "status": "success",
                "synced_count": synced_count,
                "errors": errors,
                "last_sync_timestamp": last_sync_timestamp,
                "batch_size": batch_size,
            }

            logger.info(f"Incremental sync TMDB metadata: {result}")
            return result

        except Exception as e:
            sync_monitor.update_operation(operation_id, SyncOperationStatus.FAILED, 0, batch_size)
            log_operation_error(
                logger,
                "Incremental sync TMDB metadata failed",
                error=e,
                operation="incremental_sync_tmdb",
                cache_name=self.cache_core.cache_name,
            )
            return {"status": "error", "error": str(e), "synced_count": 0, "errors": batch_size}

    def sync_parsed_files_incremental(
        self, session: Session, last_sync_timestamp: float | None = None, batch_size: int = 100
    ) -> dict[str, Any]:
        """Incremental sync for parsed files.

        Args:
            session: Database session
            last_sync_timestamp: Last sync timestamp
            batch_size: Batch size for processing

        Returns:
            Sync statistics
        """
        if not self._incremental_sync_enabled:
            return {"status": "disabled", "reason": "Incremental sync not enabled"}

        operation_id = sync_monitor.start_operation(
            SyncOperationType.INCREMENTAL_SYNC_PARSED,
            batch_size,
            cache_name=self.cache_core.cache_name,
        )

        try:
            # Get incremental sync manager
            sync_manager = self.get_incremental_sync_manager()
            if not sync_manager:
                return {"status": "error", "reason": "No incremental sync manager available"}

            # Get last sync timestamp
            if last_sync_timestamp is None:
                last_sync_timestamp = sync_manager.get_last_sync_timestamp("parsed_files")

            # Query for updated records
            query = session.query(ParsedAnimeInfo)
            if last_sync_timestamp:
                query = query.filter(ParsedAnimeInfo.updated_at > last_sync_timestamp)

            updated_files = query.limit(batch_size).all()

            synced_count = 0
            errors = 0

            for parsed_file in updated_files:
                try:
                    # Update cache
                    key = f"parsed_{parsed_file.file_path}"
                    self.cache_core.put(key, parsed_file)
                    synced_count += 1

                except Exception as e:
                    errors += 1
                    log_operation_error(
                        logger,
                        f"Failed to sync parsed file {parsed_file.file_path}",
                        error=e,
                        operation="incremental_sync_parsed_item",
                        cache_name=self.cache_core.cache_name,
                        key=f"parsed_{parsed_file.file_path}",
                    )

            # Update last sync timestamp
            if synced_count > 0:
                sync_manager.update_last_sync_timestamp("parsed_files")

            # Update sync monitor
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.COMPLETED, synced_count, errors
            )

            result = {
                "status": "success",
                "synced_count": synced_count,
                "errors": errors,
                "last_sync_timestamp": last_sync_timestamp,
                "batch_size": batch_size,
            }

            logger.info(f"Incremental sync parsed files: {result}")
            return result

        except Exception as e:
            sync_monitor.update_operation(operation_id, SyncOperationStatus.FAILED, 0, batch_size)
            log_operation_error(
                logger,
                "Incremental sync parsed files failed",
                error=e,
                operation="incremental_sync_parsed",
                cache_name=self.cache_core.cache_name,
            )
            return {"status": "error", "error": str(e), "synced_count": 0, "errors": batch_size}

    def sync_all_entities_incremental(
        self, session: Session, last_sync_timestamp: float | None = None, batch_size: int = 100
    ) -> dict[str, Any]:
        """Incremental sync for all entities.

        Args:
            session: Database session
            last_sync_timestamp: Last sync timestamp
            batch_size: Batch size for processing

        Returns:
            Combined sync statistics
        """
        if not self._incremental_sync_enabled:
            return {"status": "disabled", "reason": "Incremental sync not enabled"}

        operation_id = sync_monitor.start_operation(
            SyncOperationType.INCREMENTAL_SYNC_ALL,
            batch_size * 2,  # TMDB + Parsed
            cache_name=self.cache_core.cache_name,
        )

        try:
            # Sync TMDB metadata
            tmdb_result = self.sync_tmdb_metadata_incremental(
                session, last_sync_timestamp, batch_size
            )

            # Sync parsed files
            parsed_result = self.sync_parsed_files_incremental(
                session, last_sync_timestamp, batch_size
            )

            # Combine results
            combined_result = {
                "status": "success",
                "tmdb_sync": tmdb_result,
                "parsed_sync": parsed_result,
                "total_synced": tmdb_result.get("synced_count", 0)
                + parsed_result.get("synced_count", 0),
                "total_errors": tmdb_result.get("errors", 0) + parsed_result.get("errors", 0),
            }

            # Update sync monitor
            sync_monitor.update_operation(
                operation_id,
                SyncOperationStatus.COMPLETED,
                combined_result["total_synced"],
                combined_result["total_errors"],
            )

            logger.info(f"Incremental sync all entities: {combined_result}")
            return combined_result

        except Exception as e:
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.FAILED, 0, batch_size * 2
            )
            log_operation_error(
                logger,
                "Incremental sync all entities failed",
                error=e,
                operation="incremental_sync_all",
                cache_name=self.cache_core.cache_name,
            )
            return {
                "status": "error",
                "error": str(e),
                "total_synced": 0,
                "total_errors": batch_size * 2,
            }

    def get_sync_status(self) -> dict[str, Any]:
        """Get current sync status.

        Returns:
            Sync status information
        """
        sync_manager = self.get_incremental_sync_manager()
        if not sync_manager:
            return {
                "incremental_sync_enabled": self._incremental_sync_enabled,
                "sync_manager_available": False,
                "last_sync_timestamps": {},
            }

        return {
            "incremental_sync_enabled": self._incremental_sync_enabled,
            "sync_manager_available": True,
            "last_sync_timestamps": {
                "tmdb_metadata": sync_manager.get_last_sync_timestamp("tmdb_metadata"),
                "parsed_files": sync_manager.get_last_sync_timestamp("parsed_files"),
            },
            "sync_manager_status": sync_manager.get_status(),
        }
