"""Incremental synchronization logic for cache-database synchronization.

This module provides mechanisms to track and synchronize only changes (deltas)
since the last successful synchronization, rather than transferring entire datasets.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from .cache_key_generator import get_cache_key_generator
from .database import AnimeMetadata, ParsedFile
from .logging_utils import logger
from .sync_enums import SyncEntityType
from .sync_monitoring import SyncOperationStatus, SyncOperationType, sync_monitor


@dataclass
class SyncState:
    """Represents the synchronization state for a specific entity type."""

    entity_type: SyncEntityType
    last_sync_timestamp: datetime
    last_sync_version: int
    records_synced: int
    sync_duration_ms: float
    status: SyncOperationStatus
    error_message: str | None = None


@dataclass
class IncrementalSyncResult:
    """Result of an incremental synchronization operation."""

    entity_type: SyncEntityType
    records_found: int
    records_processed: int
    records_updated: int
    records_inserted: int
    sync_duration_ms: float
    status: SyncOperationStatus
    error_message: str | None = None


class SyncStateManager:
    """Manages synchronization state for different entity types."""

    def __init__(self):
        """Initialize the sync state manager."""
        self._sync_states: dict[SyncEntityType, SyncState] = {}
        self._state_lock = {}
        for entity_type in SyncEntityType:
            self._state_lock[entity_type] = False

    def get_last_sync_timestamp(self, entity_type: SyncEntityType) -> datetime | None:
        """Get the last successful sync timestamp for an entity type.

        Args:
            entity_type: The type of entity to get sync state for

        Returns:
            Last sync timestamp or None if never synced
        """
        if entity_type in self._sync_states:
            return self._sync_states[entity_type].last_sync_timestamp
        return None

    def get_last_sync_version(self, entity_type: SyncEntityType) -> int:
        """Get the last successful sync version for an entity type.

        Args:
            entity_type: The type of entity to get sync state for

        Returns:
            Last sync version (defaults to 0 if never synced)
        """
        if entity_type in self._sync_states:
            return self._sync_states[entity_type].last_sync_version
        return 0

    def update_sync_state(
        self,
        entity_type: SyncEntityType,
        timestamp: datetime,
        version: int,
        records_synced: int,
        duration_ms: float,
        status: SyncOperationStatus,
        error_message: str | None = None,
    ) -> None:
        """Update the sync state for an entity type.

        Args:
            entity_type: The type of entity being synced
            timestamp: Timestamp of the sync operation
            version: Version number of the sync
            records_synced: Number of records processed
            duration_ms: Duration of sync operation in milliseconds
            status: Status of the sync operation
            error_message: Error message if sync failed
        """
        self._sync_states[entity_type] = SyncState(
            entity_type=entity_type,
            last_sync_timestamp=timestamp,
            last_sync_version=version,
            records_synced=records_synced,
            sync_duration_ms=duration_ms,
            status=status,
            error_message=error_message,
        )

        logger.info(
            f"Updated sync state for {entity_type.value}: "
            f"timestamp={timestamp}, version={version}, "
            f"records={records_synced}, duration={duration_ms:.2f}ms, "
            f"status={status.value}"
        )

    def get_sync_state(self, entity_type: SyncEntityType) -> SyncState | None:
        """Get the complete sync state for an entity type.

        Args:
            entity_type: The type of entity to get sync state for

        Returns:
            SyncState object or None if never synced
        """
        return self._sync_states.get(entity_type)

    def is_entity_locked(self, entity_type: SyncEntityType) -> bool:
        """Check if an entity type is currently being synced.

        Args:
            entity_type: The type of entity to check

        Returns:
            True if entity is locked (being synced), False otherwise
        """
        return self._state_lock.get(entity_type, False)

    def lock_entity(self, entity_type: SyncEntityType) -> bool:
        """Lock an entity type for synchronization.

        Args:
            entity_type: The type of entity to lock

        Returns:
            True if successfully locked, False if already locked
        """
        if self._state_lock.get(entity_type, False):
            return False

        self._state_lock[entity_type] = True
        logger.debug(f"Locked entity type for sync: {entity_type.value}")
        return True

    def unlock_entity(self, entity_type: SyncEntityType) -> None:
        """Unlock an entity type after synchronization.

        Args:
            entity_type: The type of entity to unlock
        """
        self._state_lock[entity_type] = False
        logger.debug(f"Unlocked entity type after sync: {entity_type.value}")


class IncrementalSyncManager:
    """Manages incremental synchronization operations."""

    def __init__(self, db_manager, cache_manager):
        """Initialize the incremental sync manager.

        Args:
            db_manager: Database manager instance
            cache_manager: Cache manager instance
        """
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.state_manager = SyncStateManager()

    def sync_tmdb_metadata_incremental(
        self, session: Session, force_full_sync: bool = False
    ) -> IncrementalSyncResult:
        """Perform incremental synchronization of TMDB metadata.

        Args:
            session: Database session
            force_full_sync: If True, perform full sync regardless of last sync state

        Returns:
            IncrementalSyncResult with sync operation details
        """
        start_time = time.time()
        entity_type = SyncEntityType.TMDB_METADATA

        # Check if entity is already being synced
        if not self.state_manager.lock_entity(entity_type):
            logger.warning("TMDB metadata sync already in progress, skipping")
            return IncrementalSyncResult(
                entity_type=entity_type,
                records_found=0,
                records_processed=0,
                records_updated=0,
                records_inserted=0,
                sync_duration_ms=0,
                status=SyncOperationStatus.FAILED,
                error_message="Sync already in progress",
            )

        try:
            with sync_monitor.monitor_operation(
                SyncOperationType.INCREMENTAL_SYNC,
                cache_hit=False,
                operation_subtype=entity_type.value,
            ) as metrics:

                # Get last sync state
                last_sync_timestamp = None
                last_sync_version = 0

                if not force_full_sync:
                    last_sync_timestamp = self.state_manager.get_last_sync_timestamp(entity_type)
                    last_sync_version = self.state_manager.get_last_sync_version(entity_type)

                logger.info(
                    f"Starting incremental TMDB metadata sync: "
                    f"last_sync={last_sync_timestamp}, "
                    f"last_version={last_sync_version}, "
                    f"force_full={force_full_sync}"
                )

                # Query for changed records since last sync
                if last_sync_timestamp is None or force_full_sync:
                    # Full sync - get all records
                    query = session.query(AnimeMetadata).order_by(AnimeMetadata.updated_at)
                    logger.info("Performing full TMDB metadata sync")
                else:
                    # Incremental sync - get only changed records
                    query = (
                        session.query(AnimeMetadata)
                        .filter(
                            or_(
                                AnimeMetadata.updated_at > last_sync_timestamp,
                                and_(
                                    AnimeMetadata.updated_at == last_sync_timestamp,
                                    AnimeMetadata.version > last_sync_version,
                                ),
                            )
                        )
                        .order_by(AnimeMetadata.updated_at, AnimeMetadata.version)
                    )
                    logger.info(
                        f"Performing incremental TMDB metadata sync since {last_sync_timestamp}"
                    )

                # Execute query and process results
                changed_records = query.all()
                records_found = len(changed_records)

                logger.info(f"Found {records_found} changed TMDB metadata records")

                records_processed = 0
                records_updated = 0
                records_inserted = 0

                for metadata in changed_records:
                    try:
                        # Convert to TMDBAnime and store in cache
                        tmdb_anime = metadata.to_tmdb_anime()
                        key_generator = get_cache_key_generator()
                        cache_key = key_generator.generate_tmdb_anime_key(metadata.tmdb_id)

                        # Check if record exists in cache
                        existing = self.cache_manager.get(cache_key)
                        if existing is not None:
                            records_updated += 1
                        else:
                            records_inserted += 1

                        # Store in cache (write-through will handle database)
                        self.cache_manager.put(cache_key, tmdb_anime)
                        records_processed += 1

                    except Exception as e:
                        logger.error(f"Failed to sync TMDB metadata {metadata.tmdb_id}: {e}")
                        continue

                # Calculate sync duration
                duration_ms = (time.time() - start_time) * 1000

                # Update sync state
                current_timestamp = datetime.now(timezone.utc)
                current_version = max(
                    (r.version for r in changed_records), default=last_sync_version
                )

                self.state_manager.update_sync_state(
                    entity_type=entity_type,
                    timestamp=current_timestamp,
                    version=current_version,
                    records_synced=records_processed,
                    duration_ms=duration_ms,
                    status=SyncOperationStatus.SUCCESS,
                )

                result = IncrementalSyncResult(
                    entity_type=entity_type,
                    records_found=records_found,
                    records_processed=records_processed,
                    records_updated=records_updated,
                    records_inserted=records_inserted,
                    sync_duration_ms=duration_ms,
                    status=SyncOperationStatus.SUCCESS,
                )

                # Update metrics
                metrics.complete(
                    SyncOperationStatus.SUCCESS,
                    affected_records=records_processed,
                    additional_context={
                        "records_found": records_found,
                        "records_updated": records_updated,
                        "records_inserted": records_inserted,
                        "force_full_sync": force_full_sync,
                    },
                )

                logger.info(
                    f"Completed incremental TMDB metadata sync: "
                    f"found={records_found}, processed={records_processed}, "
                    f"updated={records_updated}, inserted={records_inserted}, "
                    f"duration={duration_ms:.2f}ms"
                )

                return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"TMDB metadata sync failed: {e}"
            logger.error(error_msg)

            # Update sync state with error
            self.state_manager.update_sync_state(
                entity_type=entity_type,
                timestamp=datetime.now(timezone.utc),
                version=last_sync_version,
                records_synced=0,
                duration_ms=duration_ms,
                status=SyncOperationStatus.FAILED,
                error_message=error_msg,
            )

            return IncrementalSyncResult(
                entity_type=entity_type,
                records_found=0,
                records_processed=0,
                records_updated=0,
                records_inserted=0,
                sync_duration_ms=duration_ms,
                status=SyncOperationStatus.FAILED,
                error_message=error_msg,
            )

        finally:
            # Always unlock the entity
            self.state_manager.unlock_entity(entity_type)

    def sync_parsed_files_incremental(
        self, session: Session, force_full_sync: bool = False
    ) -> IncrementalSyncResult:
        """Perform incremental synchronization of parsed files.

        Args:
            session: Database session
            force_full_sync: If True, perform full sync regardless of last sync state

        Returns:
            IncrementalSyncResult with sync operation details
        """
        start_time = time.time()
        entity_type = SyncEntityType.PARSED_FILES

        # Check if entity is already being synced
        if not self.state_manager.lock_entity(entity_type):
            logger.warning("Parsed files sync already in progress, skipping")
            return IncrementalSyncResult(
                entity_type=entity_type,
                records_found=0,
                records_processed=0,
                records_updated=0,
                records_inserted=0,
                sync_duration_ms=0,
                status=SyncOperationStatus.FAILED,
                error_message="Sync already in progress",
            )

        try:
            with sync_monitor.monitor_operation(
                SyncOperationType.INCREMENTAL_SYNC,
                cache_hit=False,
                operation_subtype=entity_type.value,
            ) as metrics:

                # Get last sync state
                last_sync_timestamp = None
                last_sync_version = 0

                if not force_full_sync:
                    last_sync_timestamp = self.state_manager.get_last_sync_timestamp(entity_type)
                    last_sync_version = self.state_manager.get_last_sync_version(entity_type)

                logger.info(
                    f"Starting incremental parsed files sync: "
                    f"last_sync={last_sync_timestamp}, "
                    f"last_version={last_sync_version}, "
                    f"force_full={force_full_sync}"
                )

                # Query for changed records since last sync
                if last_sync_timestamp is None or force_full_sync:
                    # Full sync - get all records
                    query = session.query(ParsedFile).order_by(ParsedFile.db_updated_at)
                    logger.info("Performing full parsed files sync")
                else:
                    # Incremental sync - get only changed records
                    query = (
                        session.query(ParsedFile)
                        .filter(
                            or_(
                                ParsedFile.db_updated_at > last_sync_timestamp,
                                and_(
                                    ParsedFile.db_updated_at == last_sync_timestamp,
                                    ParsedFile.version > last_sync_version,
                                ),
                            )
                        )
                        .order_by(ParsedFile.db_updated_at, ParsedFile.version)
                    )
                    logger.info(
                        f"Performing incremental parsed files sync since {last_sync_timestamp}"
                    )

                # Execute query and process results
                changed_records = query.all()
                records_found = len(changed_records)

                logger.info(f"Found {records_found} changed parsed file records")

                records_processed = 0
                records_updated = 0
                records_inserted = 0

                for parsed_file in changed_records:
                    try:
                        # Convert to ParsedAnimeInfo and store in cache
                        parsed_info = parsed_file.to_parsed_anime_info()
                        key_generator = get_cache_key_generator()
                        cache_key = key_generator.generate_file_key(parsed_file.file_path)

                        # Check if record exists in cache
                        existing = self.cache_manager.get(cache_key)
                        if existing is not None:
                            records_updated += 1
                        else:
                            records_inserted += 1

                        # Store in cache (write-through will handle database)
                        self.cache_manager.put(cache_key, parsed_info)
                        records_processed += 1

                    except Exception as e:
                        logger.error(f"Failed to sync parsed file {parsed_file.file_path}: {e}")
                        continue

                # Calculate sync duration
                duration_ms = (time.time() - start_time) * 1000

                # Update sync state
                current_timestamp = datetime.now(timezone.utc)
                current_version = max(
                    (r.version for r in changed_records), default=last_sync_version
                )

                self.state_manager.update_sync_state(
                    entity_type=entity_type,
                    timestamp=current_timestamp,
                    version=current_version,
                    records_synced=records_processed,
                    duration_ms=duration_ms,
                    status=SyncOperationStatus.SUCCESS,
                )

                result = IncrementalSyncResult(
                    entity_type=entity_type,
                    records_found=records_found,
                    records_processed=records_processed,
                    records_updated=records_updated,
                    records_inserted=records_inserted,
                    sync_duration_ms=duration_ms,
                    status=SyncOperationStatus.SUCCESS,
                )

                # Update metrics
                metrics.complete(
                    SyncOperationStatus.SUCCESS,
                    affected_records=records_processed,
                    additional_context={
                        "records_found": records_found,
                        "records_updated": records_updated,
                        "records_inserted": records_inserted,
                        "force_full_sync": force_full_sync,
                    },
                )

                logger.info(
                    f"Completed incremental parsed files sync: "
                    f"found={records_found}, processed={records_processed}, "
                    f"updated={records_updated}, inserted={records_inserted}, "
                    f"duration={duration_ms:.2f}ms"
                )

                return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Parsed files sync failed: {e}"
            logger.error(error_msg)

            # Update sync state with error
            self.state_manager.update_sync_state(
                entity_type=entity_type,
                timestamp=datetime.now(timezone.utc),
                version=last_sync_version,
                records_synced=0,
                duration_ms=duration_ms,
                status=SyncOperationStatus.FAILED,
                error_message=error_msg,
            )

            return IncrementalSyncResult(
                entity_type=entity_type,
                records_found=0,
                records_processed=0,
                records_updated=0,
                records_inserted=0,
                sync_duration_ms=duration_ms,
                status=SyncOperationStatus.FAILED,
                error_message=error_msg,
            )

        finally:
            # Always unlock the entity
            self.state_manager.unlock_entity(entity_type)

    def sync_all_entities_incremental(
        self, session: Session, force_full_sync: bool = False
    ) -> dict[SyncEntityType, IncrementalSyncResult]:
        """Perform incremental synchronization of all entity types.

        Args:
            session: Database session
            force_full_sync: If True, perform full sync regardless of last sync state

        Returns:
            Dictionary mapping entity types to their sync results
        """
        logger.info(f"Starting incremental sync for all entities (force_full={force_full_sync})")

        results = {}

        # Sync TMDB metadata
        try:
            results[SyncEntityType.TMDB_METADATA] = self.sync_tmdb_metadata_incremental(
                session, force_full_sync
            )
        except Exception as e:
            logger.error(f"Failed to sync TMDB metadata: {e}")
            results[SyncEntityType.TMDB_METADATA] = IncrementalSyncResult(
                entity_type=SyncEntityType.TMDB_METADATA,
                records_found=0,
                records_processed=0,
                records_updated=0,
                records_inserted=0,
                sync_duration_ms=0,
                status=SyncOperationStatus.FAILED,
                error_message=str(e),
            )

        # Sync parsed files
        try:
            results[SyncEntityType.PARSED_FILES] = self.sync_parsed_files_incremental(
                session, force_full_sync
            )
        except Exception as e:
            logger.error(f"Failed to sync parsed files: {e}")
            results[SyncEntityType.PARSED_FILES] = IncrementalSyncResult(
                entity_type=SyncEntityType.PARSED_FILES,
                records_found=0,
                records_processed=0,
                records_updated=0,
                records_inserted=0,
                sync_duration_ms=0,
                status=SyncOperationStatus.FAILED,
                error_message=str(e),
            )

        # Log summary
        total_found = sum(r.records_found for r in results.values())
        total_processed = sum(r.records_processed for r in results.values())
        total_duration = sum(r.sync_duration_ms for r in results.values())

        logger.info(
            f"Completed incremental sync for all entities: "
            f"total_found={total_found}, total_processed={total_processed}, "
            f"total_duration={total_duration:.2f}ms"
        )

        return results

    def get_sync_status(self) -> dict[SyncEntityType, SyncState | None]:
        """Get the current sync status for all entity types.

        Returns:
            Dictionary mapping entity types to their current sync states
        """
        return {
            entity_type: self.state_manager.get_sync_state(entity_type)
            for entity_type in SyncEntityType
        }
