"""Reconciliation strategies for resolving data conflicts between cache and database.

This module provides various strategies for automatically resolving detected
data inconsistencies and conflicts between the MetadataCache and database.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from sqlalchemy.orm import Session

from .consistency_validator import DataConflict, ConflictType, ConflictSeverity
from .database import AnimeMetadata, ParsedFile, db_manager
from .metadata_cache import MetadataCache
from .logging_utils import log_operation_error

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
        details: List[str],
        errors: List[str]
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
    
    def __init__(self, metadata_cache: Optional[MetadataCache] = None):
        """Initialize the reconciliation engine.
        
        Args:
            metadata_cache: MetadataCache instance for reconciliation
        """
        self.metadata_cache = metadata_cache or MetadataCache()
        self.db_manager = db_manager
    
    def reconcile_conflicts(
        self, 
        conflicts: List[DataConflict], 
        strategy: ReconciliationStrategy
    ) -> ReconciliationResult:
        """Reconcile a list of conflicts using the specified strategy.
        
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
        
        for conflict in conflicts:
            try:
                if strategy == ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH:
                    success = self._reconcile_database_wins(conflict)
                elif strategy == ReconciliationStrategy.LAST_MODIFIED_WINS:
                    success = self._reconcile_last_modified_wins(conflict)
                elif strategy == ReconciliationStrategy.CACHE_IS_SOURCE_OF_TRUTH:
                    success = self._reconcile_cache_wins(conflict)
                elif strategy == ReconciliationStrategy.MANUAL_REVIEW:
                    success = self._reconcile_manual_review(conflict)
                else:
                    raise ValueError(f"Unknown reconciliation strategy: {strategy}")
                
                if success:
                    resolved_count += 1
                    details.append(f"Resolved {conflict.conflict_type.value} for {conflict.entity_type}:{conflict.entity_id}")
                else:
                    failed_count += 1
                    errors.append(f"Failed to resolve {conflict.conflict_type.value} for {conflict.entity_type}:{conflict.entity_id}")
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Error reconciling {conflict.conflict_type.value} for {conflict.entity_type}:{conflict.entity_id}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        success = failed_count == 0
        result = ReconciliationResult(
            success=success,
            strategy_used=strategy,
            conflicts_resolved=resolved_count,
            conflicts_failed=failed_count,
            details=details,
            errors=errors
        )
        
        logger.info(f"Reconciliation completed: {resolved_count} resolved, {failed_count} failed")
        return result
    
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
                logger.warning(f"Database-wins strategy cannot resolve missing database data: {conflict}")
                return False
            elif conflict.conflict_type in [ConflictType.VERSION_MISMATCH, ConflictType.DATA_MISMATCH, ConflictType.TIMESTAMP_MISMATCH]:
                # Update cache with database data
                return self._update_cache_from_database(conflict)
            else:
                logger.warning(f"Unknown conflict type for database-wins strategy: {conflict.conflict_type}")
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
            elif conflict.conflict_type in [ConflictType.VERSION_MISMATCH, ConflictType.DATA_MISMATCH, ConflictType.TIMESTAMP_MISMATCH]:
                # Compare timestamps and update accordingly
                return self._reconcile_by_timestamp(conflict)
            else:
                logger.warning(f"Unknown conflict type for last-modified-wins strategy: {conflict.conflict_type}")
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
            elif conflict.conflict_type in [ConflictType.VERSION_MISMATCH, ConflictType.DATA_MISMATCH, ConflictType.TIMESTAMP_MISMATCH]:
                # Update database with cache data
                return self._update_database_from_cache(conflict)
            else:
                logger.warning(f"Unknown conflict type for cache-wins strategy: {conflict.conflict_type}")
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
                logger.debug(f"Updated cache with database data for anime_metadata:{conflict.entity_id}")
                return True
            elif conflict.entity_type == "parsed_file":
                cache_key = f"parsed_file:{conflict.entity_id}"
                self.metadata_cache.set(cache_key, conflict.db_data)
                logger.debug(f"Updated cache with database data for parsed_file:{conflict.entity_id}")
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
                    logger.warning(f"Unknown entity type for database update: {conflict.entity_type}")
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
                    if hasattr(anime, key) and key not in ['tmdb_id', 'created_at']:
                        setattr(anime, key, value)
                # Increment version
                anime.version = (anime.version or 0) + 1
                anime.updated_at = datetime.now(timezone.utc)
            else:
                # Create new record
                anime = AnimeMetadata(
                    tmdb_id=tmdb_id,
                    title=cache_data.get('title', ''),
                    original_title=cache_data.get('original_title'),
                    korean_title=cache_data.get('korean_title'),
                    overview=cache_data.get('overview'),
                    poster_path=cache_data.get('poster_path'),
                    backdrop_path=cache_data.get('backdrop_path'),
                    first_air_date=self._parse_datetime(cache_data.get('first_air_date')),
                    last_air_date=self._parse_datetime(cache_data.get('last_air_date')),
                    status=cache_data.get('status'),
                    vote_average=cache_data.get('vote_average'),
                    vote_count=cache_data.get('vote_count'),
                    popularity=cache_data.get('popularity'),
                    number_of_seasons=cache_data.get('number_of_seasons'),
                    number_of_episodes=cache_data.get('number_of_episodes'),
                    genres=cache_data.get('genres'),
                    networks=cache_data.get('networks'),
                    version=cache_data.get('version', 1)
                )
                session.add(anime)
            
            session.commit()
            logger.debug(f"Updated anime_metadata:{tmdb_id} in database from cache")
            return True
            
        except Exception as e:
            log_operation_error("update anime metadata from cache", e)
            session.rollback()
            return False
    
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
                    if hasattr(file, key) and key not in ['id', 'db_created_at']:
                        setattr(file, key, value)
                # Increment version
                file.version = (file.version or 0) + 1
                file.db_updated_at = datetime.now(timezone.utc)
            else:
                # Create new record
                file = ParsedFile(
                    file_path=cache_data.get('file_path', ''),
                    filename=cache_data.get('filename', ''),
                    file_size=cache_data.get('file_size', 0),
                    file_extension=cache_data.get('file_extension'),
                    file_hash=cache_data.get('file_hash'),
                    created_at=self._parse_datetime(cache_data.get('created_at')),
                    modified_at=self._parse_datetime(cache_data.get('modified_at')),
                    parsed_title=cache_data.get('parsed_title', ''),
                    season=cache_data.get('season'),
                    episode=cache_data.get('episode'),
                    episode_title=cache_data.get('episode_title'),
                    resolution=cache_data.get('resolution'),
                    resolution_width=cache_data.get('resolution_width'),
                    resolution_height=cache_data.get('resolution_height'),
                    video_codec=cache_data.get('video_codec'),
                    audio_codec=cache_data.get('audio_codec'),
                    release_group=cache_data.get('release_group'),
                    source=cache_data.get('source'),
                    year=cache_data.get('year'),
                    is_processed=cache_data.get('is_processed', False),
                    processing_errors=cache_data.get('processing_errors'),
                    metadata_id=cache_data.get('metadata_id'),
                    version=cache_data.get('version', 1)
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
                db_updated = self._parse_datetime(conflict.db_data.get('updated_at'))
                if not db_updated and conflict.entity_type == "parsed_file":
                    db_updated = self._parse_datetime(conflict.db_data.get('db_updated_at'))
            
            if conflict.cache_data:
                cache_updated = self._parse_datetime(conflict.cache_data.get('updated_at'))
                if not cache_updated and conflict.entity_type == "parsed_file":
                    cache_updated = self._parse_datetime(conflict.cache_data.get('db_updated_at'))
            
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
                logger.warning(f"No timestamps available for conflict {conflict}, using database as fallback")
                return self._update_cache_from_database(conflict)
                
        except Exception as e:
            log_operation_error("timestamp reconciliation", e)
            return False
    
    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
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
                if datetime_str.endswith('Z'):
                    datetime_str = datetime_str.replace('Z', '+00:00')
                return datetime.fromisoformat(datetime_str)
            return datetime_str
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
            return None
    
    def get_recommended_strategy(self, conflicts: List[DataConflict]) -> ReconciliationStrategy:
        """Get recommended reconciliation strategy based on conflict types.
        
        Args:
            conflicts: List of conflicts to analyze
            
        Returns:
            Recommended reconciliation strategy
        """
        if not conflicts:
            return ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH
        
        # Analyze conflict types
        missing_in_cache = sum(1 for c in conflicts if c.conflict_type == ConflictType.MISSING_IN_CACHE)
        missing_in_db = sum(1 for c in conflicts if c.conflict_type == ConflictType.MISSING_IN_DATABASE)
        version_mismatches = sum(1 for c in conflicts if c.conflict_type == ConflictType.VERSION_MISMATCH)
        data_mismatches = sum(1 for c in conflicts if c.conflict_type == ConflictType.DATA_MISMATCH)
        
        # If most conflicts are missing in cache, database is likely source of truth
        if missing_in_cache > missing_in_db and missing_in_cache > (version_mismatches + data_mismatches):
            return ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH
        
        # If most conflicts are missing in database, cache is likely source of truth
        if missing_in_db > missing_in_cache and missing_in_db > (version_mismatches + data_mismatches):
            return ReconciliationStrategy.CACHE_IS_SOURCE_OF_TRUTH
        
        # For version and data mismatches, use last-modified-wins
        if version_mismatches + data_mismatches > missing_in_cache + missing_in_db:
            return ReconciliationStrategy.LAST_MODIFIED_WINS
        
        # Default to database as source of truth
        return ReconciliationStrategy.DATABASE_IS_SOURCE_OF_TRUTH
