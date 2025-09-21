"""Reconciliation strategies for resolving data conflicts between cache and database.

This module provides various strategies for automatically resolving detected
data inconsistencies and conflicts between the MetadataCache and database.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import Session

from .consistency_validator import ConflictType, DataConflict
from .database import AnimeMetadata, ParsedFile, db_manager
from .logging_utils import log_operation_error
from .metadata_cache import MetadataCache
from .services.bulk_update_task import ConcreteBulkUpdateTask

# Configure logging
logger = logging.getLogger(__name__)


class ReconciliationStrategy(Enum):
    """Available reconciliation strategies."""

    DATABASE_IS_SOURCE_OF_TRUTH = "database_is_source_of_truth"
    LAST_MODIFIED_WINS = "last_modified_wins"
    CACHE_IS_SOURCE_OF_TRUTH = "cache_is_source_of_truth"
    MANUAL_REVIEW = "manual_review"


class ReconciliationResult:
    """Result of a reconciliation operation."""

    def __init__(
        self,
        success: bool,
        strategy_used: ReconciliationStrategy,
        conflicts_resolved: int,
        conflicts_failed: int,
        details: list[str],
        errors: list[str],
    ):
        self.success = success
        self.strategy_used = strategy_used
        self.conflicts_resolved = conflicts_resolved
        self.conflicts_failed = conflicts_failed
        self.details = details
        self.errors = errors
        self.timestamp = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return (
            f"ReconciliationResult(success={self.success}, "
            f"strategy={self.strategy_used.value}, "
            f"resolved={self.conflicts_resolved}, "
            f"failed={self.conflicts_failed})"
        )


class ReconciliationEngine:
    """Engine for executing reconciliation strategies."""

    def __init__(self, metadata_cache: MetadataCache | None = None):
        """Initialize the reconciliation engine.

        Args:
            metadata_cache: MetadataCache instance for reconciliation
        """
        self.metadata_cache = metadata_cache or MetadataCache()
        self.db_manager = db_manager

    def reconcile_conflicts(
        self, conflicts: list[DataConflict], strategy: ReconciliationStrategy
    ) -> ReconciliationResult:
        """Reconcile a list of conflicts using the specified strategy.

        This method has been optimized to use batch processing for better performance
        and to eliminate N+1 query patterns.

        Args:
            conflicts: List of conflicts to reconcile
            strategy: Reconciliation strategy to use

        Returns:
            ReconciliationResult with details of the operation
        """
        logger.info(f"Starting reconciliation of {len(conflicts)} conflicts using {strategy.value}")

        details = []
        errors = []
        resolved_count = 0
        failed_count = 0

        try:
            # Use batch processing for cache-based reconciliation strategies
            if strategy == ReconciliationStrategy.CACHE_IS_SOURCE_OF_TRUTH:
                resolved_count = self._bulk_reconcile_cache_wins(conflicts)
                details.append(
                    f"Bulk reconciled {resolved_count} conflicts using cache as source of truth"
                )
            else:
                # Use bulk processing for other strategies to eliminate N+1 queries
                if strategy == ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH:
                    resolved_count = self._bulk_reconcile_database_wins(conflicts)
                    details.append(
                        f"Bulk reconciled {resolved_count} conflicts using database as source of truth"
                    )
                elif strategy == ReconciliationStrategy.LAST_MODIFIED_WINS:
                    resolved_count = self._bulk_reconcile_last_modified_wins(conflicts)
                    details.append(
                        f"Bulk reconciled {resolved_count} conflicts using last modified wins"
                    )
                elif strategy == ReconciliationStrategy.MANUAL_REVIEW:
                    # Manual review still needs individual processing
                    for conflict in conflicts:
                        try:
                            success = self._reconcile_manual_review(conflict)
                            if success:
                                resolved_count += 1
                                details.append(
                                    f"Resolved {conflict.conflict_type.value} for {conflict.entity_type}:{conflict.entity_id}"
                                )
                            else:
                                failed_count += 1
                                errors.append(
                                    f"Failed to resolve {conflict.conflict_type.value} for {conflict.entity_type}:{conflict.entity_id}"
                                )
                        except Exception as e:
                            failed_count += 1
                            error_msg = f"Error reconciling {conflict.conflict_type.value} for {conflict.entity_type}:{conflict.entity_id}: {e}"
                            errors.append(error_msg)
                            logger.error(error_msg)
                else:
                    raise ValueError(f"Unknown reconciliation strategy: {strategy}")

            success = failed_count == 0
            result = ReconciliationResult(
                success=success,
                strategy_used=strategy,
                conflicts_resolved=resolved_count,
                conflicts_failed=failed_count,
                details=details,
                errors=errors,
            )

            logger.info(
                f"Reconciliation completed: {resolved_count} resolved, {failed_count} failed"
            )
            return result

        except Exception as e:
            error_msg = f"Bulk reconciliation failed: {e}"
            logger.error(error_msg, exc_info=True)
            return ReconciliationResult(
                success=False,
                strategy_used=strategy,
                conflicts_resolved=0,
                conflicts_failed=len(conflicts),
                details=[],
                errors=[error_msg],
            )

    def _bulk_reconcile_cache_wins(self, conflicts: list[DataConflict]) -> int:
        """Bulk reconcile conflicts using cache as source of truth.

        This method eliminates N+1 query patterns by collecting all updates
        and applying them in optimized batch operations.

        Args:
            conflicts: List of conflicts to reconcile

        Returns:
            Number of conflicts resolved
        """
        if not conflicts:
            return 0

        try:
            # Separate conflicts by entity type for batch processing
            anime_conflicts = []
            file_conflicts = []

            for conflict in conflicts:
                if conflict.entity_type == ConflictType.ANIME_METADATA:
                    anime_conflicts.append(conflict)
                elif conflict.entity_type == ConflictType.PARSED_FILE:
                    file_conflicts.append(conflict)

            total_resolved = 0

            # Bulk update anime metadata from cache
            if anime_conflicts:
                resolved_count = self._bulk_update_anime_metadata_from_cache(anime_conflicts)
                total_resolved += resolved_count

            # Bulk update parsed files from cache
            if file_conflicts:
                resolved_count = self._bulk_update_parsed_files_from_cache(file_conflicts)
                total_resolved += resolved_count

            logger.info(f"Bulk reconciliation completed: {total_resolved} conflicts resolved")
            return total_resolved

        except Exception as e:
            logger.error(f"Bulk reconciliation failed: {e}", exc_info=True)
            return 0

    def _reconcile_database_wins(self, conflict: DataConflict) -> bool:
        """Reconcile conflict by using database as source of truth.

        Args:
            conflict: Conflict to reconcile

        Returns:
            True if reconciliation was successful, False otherwise
        """
        try:
            if conflict.conflict_type == ConflictType.MISSING_IN_CACHE:
                # Update cache with database data
                return self._update_cache_from_database(conflict)
            elif conflict.conflict_type == ConflictType.MISSING_IN_DATABASE:
                # This shouldn't happen with database-wins strategy, but log it
                logger.warning(
                    f"Database-wins strategy cannot resolve missing database data: {conflict}"
                )
                return False
            elif conflict.conflict_type in [
                ConflictType.VERSION_MISMATCH,
                ConflictType.DATA_MISMATCH,
                ConflictType.TIMESTAMP_MISMATCH,
            ]:
                # Update cache with database data
                return self._update_cache_from_database(conflict)
            else:
                logger.warning(
                    f"Unknown conflict type for database-wins strategy: {conflict.conflict_type}"
                )
                return False

        except Exception as e:
            log_operation_error("database-wins reconciliation", e)
            return False

    def _reconcile_last_modified_wins(self, conflict: DataConflict) -> bool:
        """Reconcile conflict by using the most recently modified data.

        Args:
            conflict: Conflict to reconcile

        Returns:
            True if reconciliation was successful, False otherwise
        """
        try:
            if conflict.conflict_type == ConflictType.MISSING_IN_CACHE:
                # Update cache with database data
                return self._update_cache_from_database(conflict)
            elif conflict.conflict_type == ConflictType.MISSING_IN_DATABASE:
                # Update database with cache data
                return self._update_database_from_cache(conflict)
            elif conflict.conflict_type in [
                ConflictType.VERSION_MISMATCH,
                ConflictType.DATA_MISMATCH,
                ConflictType.TIMESTAMP_MISMATCH,
            ]:
                # Compare timestamps and update accordingly
                return self._reconcile_by_timestamp(conflict)
            else:
                logger.warning(
                    f"Unknown conflict type for last-modified-wins strategy: {conflict.conflict_type}"
                )
                return False

        except Exception as e:
            log_operation_error("last-modified-wins reconciliation", e)
            return False

    def _reconcile_cache_wins(self, conflict: DataConflict) -> bool:
        """Reconcile conflict by using cache as source of truth.

        Args:
            conflict: Conflict to reconcile

        Returns:
            True if reconciliation was successful, False otherwise
        """
        try:
            if conflict.conflict_type == ConflictType.MISSING_IN_DATABASE:
                # Update database with cache data
                return self._update_database_from_cache(conflict)
            elif conflict.conflict_type == ConflictType.MISSING_IN_CACHE:
                # This shouldn't happen with cache-wins strategy, but log it
                logger.warning(f"Cache-wins strategy cannot resolve missing cache data: {conflict}")
                return False
            elif conflict.conflict_type in [
                ConflictType.VERSION_MISMATCH,
                ConflictType.DATA_MISMATCH,
                ConflictType.TIMESTAMP_MISMATCH,
            ]:
                # Update database with cache data
                return self._update_database_from_cache(conflict)
            else:
                logger.warning(
                    f"Unknown conflict type for cache-wins strategy: {conflict.conflict_type}"
                )
                return False

        except Exception as e:
            log_operation_error("cache-wins reconciliation", e)
            return False

    def _reconcile_manual_review(self, conflict: DataConflict) -> bool:
        """Mark conflict for manual review (no automatic resolution).

        Args:
            conflict: Conflict to mark for review

        Returns:
            True (conflict is marked for review)
        """
        logger.info(f"Marking conflict for manual review: {conflict}")
        # In a real implementation, this might:
        # - Add to a review queue
        # - Send notifications
        # - Log to a special review table
        return True

    def _update_cache_from_database(self, conflict: DataConflict) -> bool:
        """Update cache with database data.

        Args:
            conflict: Conflict containing database data

        Returns:
            True if update was successful, False otherwise
        """
        try:
            if conflict.entity_type == "anime_metadata":
                cache_key = f"anime_metadata:{conflict.entity_id}"
                self.metadata_cache.set(cache_key, conflict.db_data)
                logger.debug(
                    f"Updated cache with database data for anime_metadata:{conflict.entity_id}"
                )
                return True
            elif conflict.entity_type == "parsed_file":
                cache_key = f"parsed_file:{conflict.entity_id}"
                self.metadata_cache.set(cache_key, conflict.db_data)
                logger.debug(
                    f"Updated cache with database data for parsed_file:{conflict.entity_id}"
                )
                return True
            else:
                logger.warning(f"Unknown entity type for cache update: {conflict.entity_type}")
                return False

        except Exception as e:
            log_operation_error("update cache from database", e)
            return False

    def _update_database_from_cache(self, conflict: DataConflict) -> bool:
        """Update database with cache data.

        Args:
            conflict: Conflict containing cache data

        Returns:
            True if update was successful, False otherwise
        """
        try:
            with self.db_manager.transaction() as session:
                if conflict.entity_type == "anime_metadata":
                    return self._update_anime_metadata_from_cache(session, conflict)
                elif conflict.entity_type == "parsed_file":
                    return self._update_parsed_file_from_cache(session, conflict)
                else:
                    logger.warning(
                        f"Unknown entity type for database update: {conflict.entity_type}"
                    )
                    return False

        except Exception as e:
            log_operation_error("update database from cache", e)
            return False

    def _update_anime_metadata_from_cache(self, session: Session, conflict: DataConflict) -> bool:
        """Update anime metadata in database from cache data.

        Args:
            session: Database session
            conflict: Conflict containing cache data

        Returns:
            True if update was successful, False otherwise
        """
        try:
            tmdb_id = conflict.entity_id
            cache_data = conflict.cache_data

            # Find existing record
            anime = session.query(AnimeMetadata).filter(AnimeMetadata.tmdb_id == tmdb_id).first()

            if anime:
                # Update existing record
                for key, value in cache_data.items():
                    if hasattr(anime, key) and key not in ["tmdb_id", "created_at"]:
                        setattr(anime, key, value)
                # Increment version
                anime.version = (anime.version or 0) + 1
                anime.updated_at = datetime.now(timezone.utc)
            else:
                # Create new record
                anime = AnimeMetadata(
                    tmdb_id=tmdb_id,
                    title=cache_data.get("title", ""),
                    original_title=cache_data.get("original_title"),
                    korean_title=cache_data.get("korean_title"),
                    overview=cache_data.get("overview"),
                    poster_path=cache_data.get("poster_path"),
                    backdrop_path=cache_data.get("backdrop_path"),
                    first_air_date=self._parse_datetime(cache_data.get("first_air_date")),
                    last_air_date=self._parse_datetime(cache_data.get("last_air_date")),
                    status=cache_data.get("status"),
                    vote_average=cache_data.get("vote_average"),
                    vote_count=cache_data.get("vote_count"),
                    popularity=cache_data.get("popularity"),
                    number_of_seasons=cache_data.get("number_of_seasons"),
                    number_of_episodes=cache_data.get("number_of_episodes"),
                    genres=cache_data.get("genres"),
                    networks=cache_data.get("networks"),
                    version=cache_data.get("version", 1),
                )
                session.add(anime)

            session.commit()
            logger.debug(f"Updated anime_metadata:{tmdb_id} in database from cache")
            return True

        except Exception as e:
            log_operation_error("update anime metadata from cache", e)
            session.rollback()
            return False

    def _bulk_update_anime_metadata_from_cache(self, conflicts: list[DataConflict]) -> int:
        """Bulk update anime metadata in database from cache data.

        This method eliminates N+1 query patterns by collecting all updates
        and applying them in optimized batch operations.

        Args:
            conflicts: List of conflicts containing cache data

        Returns:
            Number of records updated
        """
        if not conflicts:
            return 0

        try:
            # Collect all updates for batch processing
            anime_updates = []
            tmdb_ids_to_update = []

            for conflict in conflicts:
                if conflict.entity_type == ConflictType.ANIME_METADATA:
                    tmdb_id = conflict.entity_id
                    cache_data = conflict.cache_data

                    # Prepare update dictionary
                    update_dict = {"tmdb_id": tmdb_id, "updated_at": datetime.now(timezone.utc)}

                    # Add cache data fields to update
                    for key, value in cache_data.items():
                        if key not in ["tmdb_id", "created_at"] and value is not None:
                            if key in ["first_air_date", "last_air_date"]:
                                update_dict[key] = self._parse_datetime(value)
                            else:
                                update_dict[key] = value

                    anime_updates.append(update_dict)
                    tmdb_ids_to_update.append(tmdb_id)

            if not anime_updates:
                return 0

            # Use bulk update task for optimal performance
            from .bulk_update_task import ConcreteBulkUpdateTask

            bulk_task = ConcreteBulkUpdateTask(
                update_type="anime_metadata", updates=anime_updates, db_manager=self.db_manager
            )

            updated_count = bulk_task.execute()
            logger.info(f"Bulk updated {updated_count} anime metadata records from cache conflicts")
            return updated_count

        except Exception as e:
            log_operation_error("bulk update anime metadata from cache", e)
            return 0

    def _bulk_reconcile_database_wins(self, conflicts: list[DataConflict]) -> int:
        """Bulk reconcile conflicts using database as source of truth.

        Args:
            conflicts: List of conflicts to resolve

        Returns:
            Number of conflicts resolved
        """
        if not conflicts:
            return 0

        try:
            # Group conflicts by entity type for batch processing
            anime_conflicts = []
            file_conflicts = []

            for conflict in conflicts:
                if conflict.entity_type == ConflictType.ANIME_METADATA:
                    anime_conflicts.append(conflict)
                elif conflict.entity_type == ConflictType.PARSED_FILE:
                    file_conflicts.append(conflict)

            resolved_count = 0

            # Bulk update cache from database for anime metadata conflicts
            if anime_conflicts:
                resolved_count += self._bulk_update_cache_from_database(anime_conflicts)

            # Bulk update cache from database for parsed file conflicts
            if file_conflicts:
                resolved_count += self._bulk_update_cache_from_database(file_conflicts)

            logger.info(
                f"Bulk reconciled {resolved_count} conflicts using database as source of truth"
            )
            return resolved_count

        except Exception as e:
            log_operation_error("bulk reconcile database wins", e)
            return 0

    def _bulk_reconcile_last_modified_wins(self, conflicts: list[DataConflict]) -> int:
        """Bulk reconcile conflicts using last modified timestamp.

        Args:
            conflicts: List of conflicts to resolve

        Returns:
            Number of conflicts resolved
        """
        if not conflicts:
            return 0

        try:
            resolved_count = 0

            # Group conflicts by which side is newer
            cache_newer = []
            db_newer = []

            for conflict in conflicts:
                cache_time = conflict.cache_data.get("updated_at")
                db_time = (
                    conflict.database_data.get("updated_at") if conflict.database_data else None
                )

                if cache_time and db_time:
                    if cache_time > db_time:
                        cache_newer.append(conflict)
                    else:
                        db_newer.append(conflict)
                elif cache_time:
                    cache_newer.append(conflict)
                elif db_time:
                    db_newer.append(conflict)

            # Update database from cache for cache-newer conflicts
            if cache_newer:
                resolved_count += self._bulk_update_anime_metadata_from_cache(cache_newer)

            # Update cache from database for db-newer conflicts
            if db_newer:
                resolved_count += self._bulk_update_cache_from_database(db_newer)

            logger.info(f"Bulk reconciled {resolved_count} conflicts using last modified wins")
            return resolved_count

        except Exception as e:
            log_operation_error("bulk reconcile last modified wins", e)
            return 0

    def _bulk_update_cache_from_database(self, conflicts: list[DataConflict]) -> int:
        """Bulk update cache from database data.

        Args:
            conflicts: List of conflicts containing database data

        Returns:
            Number of records updated
        """
        if not conflicts:
            return 0

        try:
            updated_count = 0

            for conflict in conflicts:
                if conflict.database_data:
                    entity_id = conflict.entity_id
                    db_data = conflict.database_data

                    # Update cache with database data
                    if conflict.entity_type == ConflictType.ANIME_METADATA:
                        cache_key = f"tmdb:{entity_id}"
                        if self.cache:
                            self.cache.put(cache_key, db_data)
                            updated_count += 1
                    elif conflict.entity_type == ConflictType.PARSED_FILE:
                        cache_key = f"file:{entity_id}"
                        if self.cache:
                            self.cache.put(cache_key, db_data)
                            updated_count += 1

            logger.info(f"Bulk updated {updated_count} cache entries from database")
            return updated_count

        except Exception as e:
            log_operation_error("bulk update cache from database", e)
            return 0

    def _bulk_update_parsed_files_from_cache(self, conflicts: list[DataConflict]) -> int:
        """Bulk update parsed files in database from cache data.

        This method eliminates N+1 query patterns by collecting all updates
        and applying them in optimized batch operations.

        Args:
            conflicts: List of conflicts containing cache data

        Returns:
            Number of records updated
        """
        if not conflicts:
            return 0

        try:
            # Collect all updates for batch processing
            file_updates = []

            for conflict in conflicts:
                if conflict.entity_type == ConflictType.PARSED_FILE:
                    file_id = conflict.entity_id
                    cache_data = conflict.cache_data

                    # Prepare update data
                    update_data = {
                        "file_path": cache_data.get("file_path", ""),
                        "filename": cache_data.get("filename", ""),
                        "file_size": cache_data.get("file_size", 0),
                        "file_extension": cache_data.get("file_extension", ""),
                        "parsed_title": cache_data.get("parsed_title"),
                        "parsed_season": cache_data.get("parsed_season"),
                        "parsed_episode": cache_data.get("parsed_episode"),
                        "parsed_episode_range": cache_data.get("parsed_episode_range"),
                        "parsed_resolution": cache_data.get("parsed_resolution"),
                        "parsed_quality": cache_data.get("parsed_quality"),
                        "parsed_source": cache_data.get("parsed_source"),
                        "parsed_codec": cache_data.get("parsed_codec"),
                        "parsed_audio": cache_data.get("parsed_audio"),
                        "parsed_subtitle": cache_data.get("parsed_subtitle"),
                        "parsed_release_group": cache_data.get("parsed_release_group"),
                        "parsed_year": cache_data.get("parsed_year"),
                        "parsed_month": cache_data.get("parsed_month"),
                        "parsed_day": cache_data.get("parsed_day"),
                        "parsed_week": cache_data.get("parsed_week"),
                        "parsed_episode_title": cache_data.get("parsed_episode_title"),
                        "parsed_special": cache_data.get("parsed_special"),
                        "parsed_ova": cache_data.get("parsed_ova"),
                        "parsed_movie": cache_data.get("parsed_movie"),
                        "parsed_complete": cache_data.get("parsed_complete"),
                        "parsed_uncensored": cache_data.get("parsed_uncensored"),
                        "parsed_censored": cache_data.get("parsed_censored"),
                        "parsed_3d": cache_data.get("parsed_3d"),
                        "parsed_hdr": cache_data.get("parsed_hdr"),
                        "parsed_dv": cache_data.get("parsed_dv"),
                        "parsed_atmos": cache_data.get("parsed_atmos"),
                        "parsed_truehd": cache_data.get("parsed_truehd"),
                        "parsed_dts": cache_data.get("parsed_dts"),
                        "parsed_dtshd": cache_data.get("parsed_dtshd"),
                        "parsed_dtsx": cache_data.get("parsed_dtsx"),
                        "parsed_aac": cache_data.get("parsed_aac"),
                        "parsed_ac3": cache_data.get("parsed_ac3"),
                        "parsed_eac3": cache_data.get("parsed_eac3"),
                        "parsed_flac": cache_data.get("parsed_flac"),
                        "parsed_mp3": cache_data.get("parsed_mp3"),
                        "parsed_opus": cache_data.get("parsed_opus"),
                        "parsed_pcm": cache_data.get("parsed_pcm"),
                        "parsed_vorbis": cache_data.get("parsed_vorbis"),
                        "parsed_dual_audio": cache_data.get("parsed_dual_audio"),
                        "parsed_multisub": cache_data.get("parsed_multisub"),
                        "parsed_softsub": cache_data.get("parsed_softsub"),
                        "parsed_hardsub": cache_data.get("parsed_hardsub"),
                        "parsed_raw": cache_data.get("parsed_raw"),
                        "parsed_remux": cache_data.get("parsed_remux"),
                        "parsed_repack": cache_data.get("parsed_repack"),
                        "parsed_proper": cache_data.get("parsed_proper"),
                        "parsed_read_nfo": cache_data.get("parsed_read_nfo"),
                        "parsed_limited": cache_data.get("parsed_limited"),
                        "parsed_web_dl": cache_data.get("parsed_web_dl"),
                        "parsed_webrip": cache_data.get("parsed_webrip"),
                        "parsed_hdtv": cache_data.get("parsed_hdtv"),
                        "parsed_pdtv": cache_data.get("parsed_pdtv"),
                        "parsed_dsr": cache_data.get("parsed_dsr"),
                        "parsed_tvrip": cache_data.get("parsed_tvrip"),
                        "parsed_vhsrip": cache_data.get("parsed_vhsrip"),
                        "parsed_camrip": cache_data.get("parsed_camrip"),
                        "parsed_ts": cache_data.get("parsed_ts"),
                        "parsed_tc": cache_data.get("parsed_tc"),
                        "parsed_scr": cache_data.get("parsed_scr"),
                        "parsed_workprint": cache_data.get("parsed_workprint"),
                        "parsed_telecine": cache_data.get("parsed_telecine"),
                        "parsed_pay_per_view": cache_data.get("parsed_pay_per_view"),
                        "parsed_sdtv": cache_data.get("parsed_sdtv"),
                        "parsed_dvd": cache_data.get("parsed_dvd"),
                        "parsed_dvdrip": cache_data.get("parsed_dvdrip"),
                        "parsed_hddvd": cache_data.get("parsed_hddvd"),
                        "parsed_hddvdrip": cache_data.get("parsed_hddvdrip"),
                        "parsed_bluray": cache_data.get("parsed_bluray"),
                        "parsed_bdrip": cache_data.get("parsed_bdrip"),
                        "parsed_uhd_bluray": cache_data.get("parsed_uhd_bluray"),
                        "parsed_uhd_bdrip": cache_data.get("parsed_uhd_bdrip"),
                        "parsed_uhd_web_dl": cache_data.get("parsed_uhd_web_dl"),
                        "parsed_uhd_webrip": cache_data.get("parsed_uhd_webrip"),
                        "parsed_uhd_hdtv": cache_data.get("parsed_uhd_hdtv"),
                        "parsed_uhd_pdtv": cache_data.get("parsed_uhd_pdtv"),
                        "parsed_uhd_dsr": cache_data.get("parsed_uhd_dsr"),
                        "parsed_uhd_tvrip": cache_data.get("parsed_uhd_tvrip"),
                        "parsed_uhd_vhsrip": cache_data.get("parsed_uhd_vhsrip"),
                        "parsed_uhd_camrip": cache_data.get("parsed_uhd_camrip"),
                        "parsed_uhd_ts": cache_data.get("parsed_uhd_ts"),
                        "parsed_uhd_tc": cache_data.get("parsed_uhd_tc"),
                        "parsed_uhd_scr": cache_data.get("parsed_uhd_scr"),
                        "parsed_uhd_workprint": cache_data.get("parsed_uhd_workprint"),
                        "parsed_uhd_telecine": cache_data.get("parsed_uhd_telecine"),
                        "parsed_uhd_pay_per_view": cache_data.get("parsed_uhd_pay_per_view"),
                        "parsed_uhd_sdtv": cache_data.get("parsed_uhd_sdtv"),
                        "parsed_uhd_dvd": cache_data.get("parsed_uhd_dvd"),
                        "parsed_uhd_dvdrip": cache_data.get("parsed_uhd_dvdrip"),
                        "parsed_uhd_hddvd": cache_data.get("parsed_uhd_hddvd"),
                        "parsed_uhd_hddvdrip": cache_data.get("parsed_uhd_hddvdrip"),
                        "resolution_width": cache_data.get("resolution_width"),
                        "resolution_height": cache_data.get("resolution_height"),
                        "video_codec": cache_data.get("video_codec"),
                        "audio_codec": cache_data.get("audio_codec"),
                        "release_group": cache_data.get("release_group"),
                        "source": cache_data.get("source"),
                        "year": cache_data.get("year"),
                        "is_processed": cache_data.get("is_processed", False),
                        "processing_errors": cache_data.get("processing_errors"),
                        "metadata_id": cache_data.get("metadata_id"),
                        "db_updated_at": datetime.now(timezone.utc),
                    }

                    file_updates.append(update_data)

            if file_updates:
                # Use bulk update task for optimized processing
                bulk_task = ConcreteBulkUpdateTask(
                    update_type="parsed_files", updates=file_updates, db_manager=db_manager
                )

                updated_count = bulk_task.execute()
                logger.info(f"Bulk updated {updated_count} parsed file records from cache")
                return updated_count

            return 0

        except Exception as e:
            log_operation_error("bulk update parsed files from cache", e)
            return 0

    def _update_parsed_file_from_cache(self, session: Session, conflict: DataConflict) -> bool:
        """Update parsed file in database from cache data.

        Args:
            session: Database session
            conflict: Conflict containing cache data

        Returns:
            True if update was successful, False otherwise
        """
        try:
            file_id = conflict.entity_id
            cache_data = conflict.cache_data

            # Find existing record
            file = session.query(ParsedFile).filter(ParsedFile.id == file_id).first()

            if file:
                # Update existing record
                for key, value in cache_data.items():
                    if hasattr(file, key) and key not in ["id", "db_created_at"]:
                        setattr(file, key, value)
                # Increment version
                file.version = (file.version or 0) + 1
                file.db_updated_at = datetime.now(timezone.utc)
            else:
                # Create new record
                file = ParsedFile(
                    file_path=cache_data.get("file_path", ""),
                    filename=cache_data.get("filename", ""),
                    file_size=cache_data.get("file_size", 0),
                    file_extension=cache_data.get("file_extension"),
                    file_hash=cache_data.get("file_hash"),
                    created_at=self._parse_datetime(cache_data.get("created_at")),
                    modified_at=self._parse_datetime(cache_data.get("modified_at")),
                    parsed_title=cache_data.get("parsed_title", ""),
                    season=cache_data.get("season"),
                    episode=cache_data.get("episode"),
                    episode_title=cache_data.get("episode_title"),
                    resolution=cache_data.get("resolution"),
                    resolution_width=cache_data.get("resolution_width"),
                    resolution_height=cache_data.get("resolution_height"),
                    video_codec=cache_data.get("video_codec"),
                    audio_codec=cache_data.get("audio_codec"),
                    release_group=cache_data.get("release_group"),
                    source=cache_data.get("source"),
                    year=cache_data.get("year"),
                    is_processed=cache_data.get("is_processed", False),
                    processing_errors=cache_data.get("processing_errors"),
                    metadata_id=cache_data.get("metadata_id"),
                    version=cache_data.get("version", 1),
                )
                session.add(file)

            session.commit()
            logger.debug(f"Updated parsed_file:{file_id} in database from cache")
            return True

        except Exception as e:
            log_operation_error("update parsed file from cache", e)
            session.rollback()
            return False

    def _reconcile_by_timestamp(self, conflict: DataConflict) -> bool:
        """Reconcile conflict by comparing timestamps.

        Args:
            conflict: Conflict to reconcile

        Returns:
            True if reconciliation was successful, False otherwise
        """
        try:
            # Get timestamps from both sources
            db_updated = None
            cache_updated = None

            if conflict.db_data:
                db_updated = self._parse_datetime(conflict.db_data.get("updated_at"))
                if not db_updated and conflict.entity_type == "parsed_file":
                    db_updated = self._parse_datetime(conflict.db_data.get("db_updated_at"))

            if conflict.cache_data:
                cache_updated = self._parse_datetime(conflict.cache_data.get("updated_at"))
                if not cache_updated and conflict.entity_type == "parsed_file":
                    cache_updated = self._parse_datetime(conflict.cache_data.get("db_updated_at"))

            # Determine which is newer
            if db_updated and cache_updated:
                if db_updated > cache_updated:
                    # Database is newer, update cache
                    return self._update_cache_from_database(conflict)
                else:
                    # Cache is newer, update database
                    return self._update_database_from_cache(conflict)
            elif db_updated:
                # Only database has timestamp, update cache
                return self._update_cache_from_database(conflict)
            elif cache_updated:
                # Only cache has timestamp, update database
                return self._update_database_from_cache(conflict)
            else:
                # No timestamps available, use database as fallback
                logger.warning(
                    f"No timestamps available for conflict {conflict}, using database as fallback"
                )
                return self._update_cache_from_database(conflict)

        except Exception as e:
            log_operation_error("timestamp reconciliation", e)
            return False

    def _parse_datetime(self, datetime_str: str | None) -> datetime | None:
        """Parse datetime string to datetime object.

        Args:
            datetime_str: Datetime string to parse

        Returns:
            Parsed datetime object or None if parsing fails
        """
        if not datetime_str:
            return None

        try:
            if isinstance(datetime_str, str):
                # Handle ISO format with timezone
                if datetime_str.endswith("Z"):
                    datetime_str = datetime_str.replace("Z", "+00:00")
                return datetime.fromisoformat(datetime_str)
            return datetime_str
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
            return None

    def get_recommended_strategy(self, conflicts: list[DataConflict]) -> ReconciliationStrategy:
        """Get recommended reconciliation strategy based on conflict types.

        Args:
            conflicts: List of conflicts to analyze

        Returns:
            Recommended reconciliation strategy
        """
        if not conflicts:
            return ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH

        # Analyze conflict types
        missing_in_cache = sum(
            1 for c in conflicts if c.conflict_type == ConflictType.MISSING_IN_CACHE
        )
        missing_in_db = sum(
            1 for c in conflicts if c.conflict_type == ConflictType.MISSING_IN_DATABASE
        )
        version_mismatches = sum(
            1 for c in conflicts if c.conflict_type == ConflictType.VERSION_MISMATCH
        )
        data_mismatches = sum(1 for c in conflicts if c.conflict_type == ConflictType.DATA_MISMATCH)

        # If most conflicts are missing in cache, database is likely source of truth
        if missing_in_cache > missing_in_db and missing_in_cache > (
            version_mismatches + data_mismatches
        ):
            return ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH

        # If most conflicts are missing in database, cache is likely source of truth
        if missing_in_db > missing_in_cache and missing_in_db > (
            version_mismatches + data_mismatches
        ):
            return ReconciliationStrategy.CACHE_IS_SOURCE_OF_TRUTH

        # For version and data mismatches, use last-modified-wins
        if version_mismatches + data_mismatches > missing_in_cache + missing_in_db:
            return ReconciliationStrategy.LAST_MODIFIED_WINS

        # Default to database as source of truth
        return ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH
