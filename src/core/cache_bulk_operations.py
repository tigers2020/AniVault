"""Bulk operations for cache system.

This module provides bulk operations for storing, updating, and managing
large amounts of data efficiently.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from .cache_core import CacheCore
from .cache_database_integration import CacheDatabaseIntegration
from .logging_utils import log_operation_error
from .models import ParsedAnimeInfo, TMDBAnime
from .sync_monitoring import SyncOperationStatus, SyncOperationType, sync_monitor

# Configure logging
logger = logging.getLogger(__name__)


class CacheBulkOperations:
    """Bulk operations for cache system."""

    def __init__(self, cache_core: CacheCore, db_integration: CacheDatabaseIntegration) -> None:
        """Initialize bulk operations.

        Args:
            cache_core: Core cache instance
            db_integration: Database integration instance
        """
        self.cache_core = cache_core
        self.db_integration = db_integration

    def bulk_store_tmdb_metadata(self, session: Session, anime_list: list[TMDBAnime]) -> int:
        """Bulk store TMDB metadata in both cache and database.

        Args:
            session: Database session
            anime_list: List of TMDB anime data

        Returns:
            Number of items successfully stored
        """
        if not anime_list:
            return 0

        operation_id = sync_monitor.start_operation(
            SyncOperationType.BULK_STORE_TMDB,
            len(anime_list),
            cache_name=self.cache_core.cache_name,
        )

        try:
            stored_count = 0
            errors = 0

            for anime in anime_list:
                try:
                    # Generate cache key
                    key = f"tmdb_{anime.tmdb_id}"

                    # Store in database
                    existing = session.query(TMDBAnime).filter_by(tmdb_id=anime.tmdb_id).first()
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
                            setattr(existing, attr, getattr(anime, attr))
                    else:
                        # Create new record
                        session.add(anime)

                    # Store in cache
                    self.cache_core.put(key, anime)
                    stored_count += 1

                except Exception as e:
                    errors += 1
                    log_operation_error(
                        logger,
                        f"Failed to store TMDB anime {anime.tmdb_id}",
                        error=e,
                        operation="bulk_store_tmdb_item",
                        cache_name=self.cache_core.cache_name,
                        key=f"tmdb_{anime.tmdb_id}",
                    )

            # Commit database changes
            session.commit()

            # Update sync monitor
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.COMPLETED, stored_count, errors
            )

            logger.info(f"Bulk stored {stored_count} TMDB anime entries with {errors} errors")
            return stored_count

        except Exception as e:
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.FAILED, 0, len(anime_list)
            )
            log_operation_error(
                logger,
                "Bulk store TMDB metadata failed",
                error=e,
                operation="bulk_store_tmdb",
                cache_name=self.cache_core.cache_name,
            )
            return 0

    def bulk_store_parsed_files(
        self, session: Session, parsed_files: list[ParsedAnimeInfo], batch_size: int = 100
    ) -> int:
        """Bulk store parsed files in both cache and database.

        Args:
            session: Database session
            parsed_files: List of parsed file data
            batch_size: Batch size for processing

        Returns:
            Number of items successfully stored
        """
        if not parsed_files:
            return 0

        operation_id = sync_monitor.start_operation(
            SyncOperationType.BULK_STORE_PARSED,
            len(parsed_files),
            cache_name=self.cache_core.cache_name,
        )

        try:
            stored_count = 0
            errors = 0

            # Process in batches
            for i in range(0, len(parsed_files), batch_size):
                batch = parsed_files[i : i + batch_size]

                for parsed_file in batch:
                    try:
                        # Generate cache key
                        key = f"parsed_{parsed_file.file_path}"

                        # Store in database
                        existing = (
                            session.query(ParsedAnimeInfo)
                            .filter_by(file_path=parsed_file.file_path)
                            .first()
                        )
                        if existing:
                            # Update existing record
                            for attr in ["title", "season", "episode", "year", "quality", "group"]:
                                setattr(existing, attr, getattr(parsed_file, attr))
                        else:
                            # Create new record
                            session.add(parsed_file)

                        # Store in cache
                        self.cache_core.put(key, parsed_file)
                        stored_count += 1

                    except Exception as e:
                        errors += 1
                        log_operation_error(
                            logger,
                            f"Failed to store parsed file {parsed_file.file_path}",
                            error=e,
                            operation="bulk_store_parsed_item",
                            cache_name=self.cache_core.cache_name,
                            key=f"parsed_{parsed_file.file_path}",
                        )

                # Commit batch
                session.commit()

            # Update sync monitor
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.COMPLETED, stored_count, errors
            )

            logger.info(f"Bulk stored {stored_count} parsed files with {errors} errors")
            return stored_count

        except Exception as e:
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.FAILED, 0, len(parsed_files)
            )
            log_operation_error(
                logger,
                "Bulk store parsed files failed",
                error=e,
                operation="bulk_store_parsed",
                cache_name=self.cache_core.cache_name,
            )
            return 0

    def bulk_update_tmdb_metadata(self, session: Session, updates: list[dict]) -> int:
        """Bulk update TMDB metadata.

        Args:
            session: Database session
            updates: List of update dictionaries with 'tmdb_id' and update fields

        Returns:
            Number of items successfully updated
        """
        if not updates:
            return 0

        operation_id = sync_monitor.start_operation(
            SyncOperationType.BULK_UPDATE_TMDB, len(updates), cache_name=self.cache_core.cache_name
        )

        try:
            updated_count = 0
            errors = 0

            for update_data in updates:
                try:
                    tmdb_id = update_data.get("tmdb_id")
                    if not tmdb_id:
                        errors += 1
                        continue

                    # Update database
                    anime = session.query(TMDBAnime).filter_by(tmdb_id=tmdb_id).first()
                    if anime:
                        for field, value in update_data.items():
                            if field != "tmdb_id" and hasattr(anime, field):
                                setattr(anime, field, value)

                        # Update cache
                        key = f"tmdb_{tmdb_id}"
                        self.cache_core.put(key, anime)
                        updated_count += 1
                    else:
                        errors += 1

                except Exception as e:
                    errors += 1
                    log_operation_error(
                        logger,
                        f"Failed to update TMDB anime {update_data.get('tmdb_id')}",
                        error=e,
                        operation="bulk_update_tmdb_item",
                        cache_name=self.cache_core.cache_name,
                    )

            # Commit changes
            session.commit()

            # Update sync monitor
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.COMPLETED, updated_count, errors
            )

            logger.info(f"Bulk updated {updated_count} TMDB anime entries with {errors} errors")
            return updated_count

        except Exception as e:
            sync_monitor.update_operation(operation_id, SyncOperationStatus.FAILED, 0, len(updates))
            log_operation_error(
                logger,
                "Bulk update TMDB metadata failed",
                error=e,
                operation="bulk_update_tmdb",
                cache_name=self.cache_core.cache_name,
            )
            return 0

    def bulk_update_parsed_files(self, session: Session, updates: list[dict]) -> int:
        """Bulk update parsed files.

        Args:
            session: Database session
            updates: List of update dictionaries with 'file_path' and update fields

        Returns:
            Number of items successfully updated
        """
        if not updates:
            return 0

        operation_id = sync_monitor.start_operation(
            SyncOperationType.BULK_UPDATE_PARSED,
            len(updates),
            cache_name=self.cache_core.cache_name,
        )

        try:
            updated_count = 0
            errors = 0

            for update_data in updates:
                try:
                    file_path = update_data.get("file_path")
                    if not file_path:
                        errors += 1
                        continue

                    # Update database
                    parsed_file = (
                        session.query(ParsedAnimeInfo).filter_by(file_path=file_path).first()
                    )
                    if parsed_file:
                        for field, value in update_data.items():
                            if field != "file_path" and hasattr(parsed_file, field):
                                setattr(parsed_file, field, value)

                        # Update cache
                        key = f"parsed_{file_path}"
                        self.cache_core.put(key, parsed_file)
                        updated_count += 1
                    else:
                        errors += 1

                except Exception as e:
                    errors += 1
                    log_operation_error(
                        logger,
                        f"Failed to update parsed file {update_data.get('file_path')}",
                        error=e,
                        operation="bulk_update_parsed_item",
                        cache_name=self.cache_core.cache_name,
                    )

            # Commit changes
            session.commit()

            # Update sync monitor
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.COMPLETED, updated_count, errors
            )

            logger.info(f"Bulk updated {updated_count} parsed files with {errors} errors")
            return updated_count

        except Exception as e:
            sync_monitor.update_operation(operation_id, SyncOperationStatus.FAILED, 0, len(updates))
            log_operation_error(
                logger,
                "Bulk update parsed files failed",
                error=e,
                operation="bulk_update_parsed",
                cache_name=self.cache_core.cache_name,
            )
            return 0

    def bulk_update_tmdb_metadata_by_ids(
        self, session: Session, tmdb_ids: list[int], update_fields: dict[str, Any]
    ) -> int:
        """Bulk update TMDB metadata by IDs.

        Args:
            session: Database session
            tmdb_ids: List of TMDB IDs to update
            update_fields: Fields to update

        Returns:
            Number of items successfully updated
        """
        if not tmdb_ids or not update_fields:
            return 0

        operation_id = sync_monitor.start_operation(
            SyncOperationType.BULK_UPDATE_TMDB_BY_IDS,
            len(tmdb_ids),
            cache_name=self.cache_core.cache_name,
        )

        try:
            updated_count = 0
            errors = 0

            for tmdb_id in tmdb_ids:
                try:
                    # Update database
                    anime = session.query(TMDBAnime).filter_by(tmdb_id=tmdb_id).first()
                    if anime:
                        for field, value in update_fields.items():
                            if hasattr(anime, field):
                                setattr(anime, field, value)

                        # Update cache
                        key = f"tmdb_{tmdb_id}"
                        self.cache_core.put(key, anime)
                        updated_count += 1
                    else:
                        errors += 1

                except Exception as e:
                    errors += 1
                    log_operation_error(
                        logger,
                        f"Failed to update TMDB anime {tmdb_id}",
                        error=e,
                        operation="bulk_update_tmdb_by_id",
                        cache_name=self.cache_core.cache_name,
                    )

            # Commit changes
            session.commit()

            # Update sync monitor
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.COMPLETED, updated_count, errors
            )

            logger.info(
                f"Bulk updated {updated_count} TMDB anime entries by IDs with {errors} errors"
            )
            return updated_count

        except Exception as e:
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.FAILED, 0, len(tmdb_ids)
            )
            log_operation_error(
                logger,
                "Bulk update TMDB metadata by IDs failed",
                error=e,
                operation="bulk_update_tmdb_by_ids",
                cache_name=self.cache_core.cache_name,
            )
            return 0

    def bulk_update_parsed_files_by_paths(
        self, session: Session, file_paths: list[str], update_fields: dict[str, Any]
    ) -> int:
        """Bulk update parsed files by file paths.

        Args:
            session: Database session
            file_paths: List of file paths to update
            update_fields: Fields to update

        Returns:
            Number of items successfully updated
        """
        if not file_paths or not update_fields:
            return 0

        operation_id = sync_monitor.start_operation(
            SyncOperationType.BULK_UPDATE_PARSED_BY_PATHS,
            len(file_paths),
            cache_name=self.cache_core.cache_name,
        )

        try:
            updated_count = 0
            errors = 0

            for file_path in file_paths:
                try:
                    # Update database
                    parsed_file = (
                        session.query(ParsedAnimeInfo).filter_by(file_path=file_path).first()
                    )
                    if parsed_file:
                        for field, value in update_fields.items():
                            if hasattr(parsed_file, field):
                                setattr(parsed_file, field, value)

                        # Update cache
                        key = f"parsed_{file_path}"
                        self.cache_core.put(key, parsed_file)
                        updated_count += 1
                    else:
                        errors += 1

                except Exception as e:
                    errors += 1
                    log_operation_error(
                        logger,
                        f"Failed to update parsed file {file_path}",
                        error=e,
                        operation="bulk_update_parsed_by_path",
                        cache_name=self.cache_core.cache_name,
                    )

            # Commit changes
            session.commit()

            # Update sync monitor
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.COMPLETED, updated_count, errors
            )

            logger.info(f"Bulk updated {updated_count} parsed files by paths with {errors} errors")
            return updated_count

        except Exception as e:
            sync_monitor.update_operation(
                operation_id, SyncOperationStatus.FAILED, 0, len(file_paths)
            )
            log_operation_error(
                logger,
                "Bulk update parsed files by paths failed",
                error=e,
                operation="bulk_update_parsed_by_paths",
                cache_name=self.cache_core.cache_name,
            )
            return 0
