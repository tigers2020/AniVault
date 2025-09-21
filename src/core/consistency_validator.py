"""Data consistency validation and conflict detection module.

This module provides functionality to compare cached data with database data
and identify inconsistencies and potential conflicts for reconciliation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from .database import AnimeMetadata, ParsedFile, db_manager
from .metadata_cache import MetadataCache
from .logging_utils import log_operation_error

# Configure logging
logger = logging.getLogger(__name__)


class ConflictType(Enum):
    """Types of data conflicts that can be detected."""
    
    MISSING_IN_CACHE = "missing_in_cache"
    MISSING_IN_DATABASE = "missing_in_database"
    VERSION_MISMATCH = "version_mismatch"
    DATA_MISMATCH = "data_mismatch"
    TIMESTAMP_MISMATCH = "timestamp_mismatch"


class ConflictSeverity(Enum):
    """Severity levels for detected conflicts."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataConflict:
    """Represents a detected data conflict between cache and database."""
    
    def __init__(
        self,
        conflict_type: ConflictType,
        entity_type: str,
        entity_id: Union[int, str],
        cache_data: Optional[Dict[str, Any]] = None,
        db_data: Optional[Dict[str, Any]] = None,
        severity: ConflictSeverity = ConflictSeverity.MEDIUM,
        details: Optional[str] = None,
        detected_at: Optional[datetime] = None
    ):
        self.conflict_type = conflict_type
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.cache_data = cache_data or {}
        self.db_data = db_data or {}
        self.severity = severity
        self.details = details or ""
        self.detected_at = detected_at or datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return (
            f"DataConflict(type={self.conflict_type.value}, "
            f"entity={self.entity_type}:{self.entity_id}, "
            f"severity={self.severity.value})"
        )


class ConsistencyValidator:
    """Validates data consistency between cache and database."""
    
    def __init__(self, metadata_cache: Optional[MetadataCache] = None):
        """Initialize the consistency validator.
        
        Args:
            metadata_cache: MetadataCache instance to validate against database
        """
        self.metadata_cache = metadata_cache or MetadataCache()
        self.db_manager = db_manager
    
    def validate_anime_metadata_consistency(self) -> List[DataConflict]:
        """Validate consistency of anime metadata between cache and database.
        
        Returns:
            List of detected conflicts
        """
        conflicts = []
        logger.info("Starting anime metadata consistency validation")
        
        try:
            with self.db_manager.transaction() as session:
                # Get all anime metadata from database
                db_anime_list = session.query(AnimeMetadata).all()
                logger.debug(f"Found {len(db_anime_list)} anime records in database")
                
                # Check each database record against cache
                for db_anime in db_anime_list:
                    cache_key = f"anime_metadata:{db_anime.tmdb_id}"
                    cache_data = self.metadata_cache.get(cache_key)
                    
                    if cache_data is None:
                        # Data exists in DB but not in cache
                        conflict = DataConflict(
                            conflict_type=ConflictType.MISSING_IN_CACHE,
                            entity_type="anime_metadata",
                            entity_id=db_anime.tmdb_id,
                            db_data=self._anime_metadata_to_dict(db_anime),
                            severity=ConflictSeverity.MEDIUM,
                            details=f"Anime metadata for TMDB ID {db_anime.tmdb_id} exists in database but not in cache"
                        )
                        conflicts.append(conflict)
                        logger.debug(f"Missing in cache: anime_metadata:{db_anime.tmdb_id}")
                    else:
                        # Compare versions and data
                        version_conflicts = self._compare_anime_metadata_versions(
                            db_anime, cache_data, db_anime.tmdb_id
                        )
                        conflicts.extend(version_conflicts)
                
                # Check for data that exists in cache but not in database
                cache_keys = self._get_anime_metadata_cache_keys()
                for cache_key in cache_keys:
                    tmdb_id = self._extract_tmdb_id_from_cache_key(cache_key)
                    if tmdb_id and not any(anime.tmdb_id == tmdb_id for anime in db_anime_list):
                        cache_data = self.metadata_cache.get(cache_key)
                        conflict = DataConflict(
                            conflict_type=ConflictType.MISSING_IN_DATABASE,
                            entity_type="anime_metadata",
                            entity_id=tmdb_id,
                            cache_data=cache_data,
                            severity=ConflictSeverity.HIGH,
                            details=f"Anime metadata for TMDB ID {tmdb_id} exists in cache but not in database"
                        )
                        conflicts.append(conflict)
                        logger.debug(f"Missing in database: anime_metadata:{tmdb_id}")
        
        except Exception as e:
            log_operation_error("anime metadata consistency validation", e)
            # Create a critical conflict for the validation failure
            conflict = DataConflict(
                conflict_type=ConflictType.DATA_MISMATCH,
                entity_type="validation_error",
                entity_id="anime_metadata",
                severity=ConflictSeverity.CRITICAL,
                details=f"Failed to validate anime metadata consistency: {e}"
            )
            conflicts.append(conflict)
        
        logger.info(f"Anime metadata validation completed: {len(conflicts)} conflicts found")
        return conflicts
    
    def validate_parsed_files_consistency(self) -> List[DataConflict]:
        """Validate consistency of parsed files between cache and database.
        
        Returns:
            List of detected conflicts
        """
        conflicts = []
        logger.info("Starting parsed files consistency validation")
        
        try:
            with self.db_manager.transaction() as session:
                # Get all parsed files from database
                db_files = session.query(ParsedFile).all()
                logger.debug(f"Found {len(db_files)} parsed file records in database")
                
                # Check each database record against cache
                for db_file in db_files:
                    cache_key = f"parsed_file:{db_file.id}"
                    cache_data = self.metadata_cache.get(cache_key)
                    
                    if cache_data is None:
                        # Data exists in DB but not in cache
                        conflict = DataConflict(
                            conflict_type=ConflictType.MISSING_IN_CACHE,
                            entity_type="parsed_file",
                            entity_id=db_file.id,
                            db_data=self._parsed_file_to_dict(db_file),
                            severity=ConflictSeverity.MEDIUM,
                            details=f"Parsed file {db_file.id} exists in database but not in cache"
                        )
                        conflicts.append(conflict)
                        logger.debug(f"Missing in cache: parsed_file:{db_file.id}")
                    else:
                        # Compare versions and data
                        version_conflicts = self._compare_parsed_file_versions(
                            db_file, cache_data, db_file.id
                        )
                        conflicts.extend(version_conflicts)
                
                # Check for data that exists in cache but not in database
                cache_keys = self._get_parsed_file_cache_keys()
                for cache_key in cache_keys:
                    file_id = self._extract_file_id_from_cache_key(cache_key)
                    if file_id and not any(f.id == file_id for f in db_files):
                        cache_data = self.metadata_cache.get(cache_key)
                        conflict = DataConflict(
                            conflict_type=ConflictType.MISSING_IN_DATABASE,
                            entity_type="parsed_file",
                            entity_id=file_id,
                            cache_data=cache_data,
                            severity=ConflictSeverity.HIGH,
                            details=f"Parsed file {file_id} exists in cache but not in database"
                        )
                        conflicts.append(conflict)
                        logger.debug(f"Missing in database: parsed_file:{file_id}")
        
        except Exception as e:
            log_operation_error("parsed files consistency validation", e)
            # Create a critical conflict for the validation failure
            conflict = DataConflict(
                conflict_type=ConflictType.DATA_MISMATCH,
                entity_type="validation_error",
                entity_id="parsed_files",
                severity=ConflictSeverity.CRITICAL,
                details=f"Failed to validate parsed files consistency: {e}"
            )
            conflicts.append(conflict)
        
        logger.info(f"Parsed files validation completed: {len(conflicts)} conflicts found")
        return conflicts
    
    def validate_all_consistency(self) -> List[DataConflict]:
        """Validate consistency of all data between cache and database.
        
        Returns:
            List of all detected conflicts
        """
        logger.info("Starting comprehensive consistency validation")
        
        all_conflicts = []
        
        # Validate anime metadata
        anime_conflicts = self.validate_anime_metadata_consistency()
        all_conflicts.extend(anime_conflicts)
        
        # Validate parsed files
        file_conflicts = self.validate_parsed_files_consistency()
        all_conflicts.extend(file_conflicts)
        
        logger.info(f"Comprehensive validation completed: {len(all_conflicts)} total conflicts found")
        return all_conflicts
    
    def _compare_anime_metadata_versions(
        self, 
        db_anime: AnimeMetadata, 
        cache_data: Dict[str, Any], 
        tmdb_id: int
    ) -> List[DataConflict]:
        """Compare versions and data between database and cache anime metadata.
        
        Args:
            db_anime: Database anime metadata record
            cache_data: Cached anime metadata data
            tmdb_id: TMDB ID of the anime
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Compare versions
        db_version = getattr(db_anime, 'version', 1)
        cache_version = cache_data.get('version', 1)
        
        if db_version != cache_version:
            severity = ConflictSeverity.HIGH if abs(db_version - cache_version) > 1 else ConflictSeverity.MEDIUM
            conflict = DataConflict(
                conflict_type=ConflictType.VERSION_MISMATCH,
                entity_type="anime_metadata",
                entity_id=tmdb_id,
                cache_data=cache_data,
                db_data=self._anime_metadata_to_dict(db_anime),
                severity=severity,
                details=f"Version mismatch: DB version {db_version}, Cache version {cache_version}"
            )
            conflicts.append(conflict)
            logger.debug(f"Version mismatch for anime {tmdb_id}: DB={db_version}, Cache={cache_version}")
        
        # Compare timestamps
        db_updated = getattr(db_anime, 'updated_at', None)
        cache_updated = cache_data.get('updated_at')
        
        if db_updated and cache_updated:
            if isinstance(cache_updated, str):
                # Parse string timestamp if needed
                try:
                    cache_updated = datetime.fromisoformat(cache_updated.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    cache_updated = None
            
            if cache_updated and db_updated != cache_updated:
                conflict = DataConflict(
                    conflict_type=ConflictType.TIMESTAMP_MISMATCH,
                    entity_type="anime_metadata",
                    entity_id=tmdb_id,
                    cache_data=cache_data,
                    db_data=self._anime_metadata_to_dict(db_anime),
                    severity=ConflictSeverity.LOW,
                    details=f"Timestamp mismatch: DB updated {db_updated}, Cache updated {cache_updated}"
                )
                conflicts.append(conflict)
                logger.debug(f"Timestamp mismatch for anime {tmdb_id}")
        
        # Compare key data fields
        key_fields = ['title', 'overview', 'status', 'vote_average']
        for field in key_fields:
            db_value = getattr(db_anime, field, None)
            cache_value = cache_data.get(field)
            
            if db_value != cache_value:
                conflict = DataConflict(
                    conflict_type=ConflictType.DATA_MISMATCH,
                    entity_type="anime_metadata",
                    entity_id=tmdb_id,
                    cache_data=cache_data,
                    db_data=self._anime_metadata_to_dict(db_anime),
                    severity=ConflictSeverity.MEDIUM,
                    details=f"Data mismatch in field '{field}': DB='{db_value}', Cache='{cache_value}'"
                )
                conflicts.append(conflict)
                logger.debug(f"Data mismatch for anime {tmdb_id} field {field}")
        
        return conflicts
    
    def _compare_parsed_file_versions(
        self, 
        db_file: ParsedFile, 
        cache_data: Dict[str, Any], 
        file_id: int
    ) -> List[DataConflict]:
        """Compare versions and data between database and cache parsed file.
        
        Args:
            db_file: Database parsed file record
            cache_data: Cached parsed file data
            file_id: ID of the parsed file
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Compare versions
        db_version = getattr(db_file, 'version', 1)
        cache_version = cache_data.get('version', 1)
        
        if db_version != cache_version:
            severity = ConflictSeverity.HIGH if abs(db_version - cache_version) > 1 else ConflictSeverity.MEDIUM
            conflict = DataConflict(
                conflict_type=ConflictType.VERSION_MISMATCH,
                entity_type="parsed_file",
                entity_id=file_id,
                cache_data=cache_data,
                db_data=self._parsed_file_to_dict(db_file),
                severity=severity,
                details=f"Version mismatch: DB version {db_version}, Cache version {cache_version}"
            )
            conflicts.append(conflict)
            logger.debug(f"Version mismatch for file {file_id}: DB={db_version}, Cache={cache_version}")
        
        # Compare timestamps
        db_updated = getattr(db_file, 'db_updated_at', None)
        cache_updated = cache_data.get('db_updated_at')
        
        if db_updated and cache_updated:
            if isinstance(cache_updated, str):
                # Parse string timestamp if needed
                try:
                    cache_updated = datetime.fromisoformat(cache_updated.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    cache_updated = None
            
            if cache_updated and db_updated != cache_updated:
                conflict = DataConflict(
                    conflict_type=ConflictType.TIMESTAMP_MISMATCH,
                    entity_type="parsed_file",
                    entity_id=file_id,
                    cache_data=cache_data,
                    db_data=self._parsed_file_to_dict(db_file),
                    severity=ConflictSeverity.LOW,
                    details=f"Timestamp mismatch: DB updated {db_updated}, Cache updated {cache_updated}"
                )
                conflicts.append(conflict)
                logger.debug(f"Timestamp mismatch for file {file_id}")
        
        # Compare key data fields
        key_fields = ['parsed_title', 'season', 'episode', 'file_path']
        for field in key_fields:
            db_value = getattr(db_file, field, None)
            cache_value = cache_data.get(field)
            
            if db_value != cache_value:
                conflict = DataConflict(
                    conflict_type=ConflictType.DATA_MISMATCH,
                    entity_type="parsed_file",
                    entity_id=file_id,
                    cache_data=cache_data,
                    db_data=self._parsed_file_to_dict(db_file),
                    severity=ConflictSeverity.MEDIUM,
                    details=f"Data mismatch in field '{field}': DB='{db_value}', Cache='{cache_value}'"
                )
                conflicts.append(conflict)
                logger.debug(f"Data mismatch for file {file_id} field {field}")
        
        return conflicts
    
    def _anime_metadata_to_dict(self, anime: AnimeMetadata) -> Dict[str, Any]:
        """Convert AnimeMetadata object to dictionary for comparison.
        
        Args:
            anime: AnimeMetadata object
            
        Returns:
            Dictionary representation of the anime metadata
        """
        return {
            'tmdb_id': anime.tmdb_id,
            'title': anime.title,
            'original_title': anime.original_title,
            'korean_title': anime.korean_title,
            'overview': anime.overview,
            'poster_path': anime.poster_path,
            'backdrop_path': anime.backdrop_path,
            'first_air_date': anime.first_air_date.isoformat() if anime.first_air_date else None,
            'last_air_date': anime.last_air_date.isoformat() if anime.last_air_date else None,
            'status': anime.status,
            'vote_average': anime.vote_average,
            'vote_count': anime.vote_count,
            'popularity': anime.popularity,
            'number_of_seasons': anime.number_of_seasons,
            'number_of_episodes': anime.number_of_episodes,
            'genres': anime.genres,
            'networks': anime.networks,
            'created_at': anime.created_at.isoformat() if anime.created_at else None,
            'updated_at': anime.updated_at.isoformat() if anime.updated_at else None,
            'version': getattr(anime, 'version', 1)
        }
    
    def _parsed_file_to_dict(self, file: ParsedFile) -> Dict[str, Any]:
        """Convert ParsedFile object to dictionary for comparison.
        
        Args:
            file: ParsedFile object
            
        Returns:
            Dictionary representation of the parsed file
        """
        return {
            'id': file.id,
            'file_path': file.file_path,
            'filename': file.filename,
            'file_size': file.file_size,
            'file_extension': file.file_extension,
            'file_hash': file.file_hash,
            'created_at': file.created_at.isoformat() if file.created_at else None,
            'modified_at': file.modified_at.isoformat() if file.modified_at else None,
            'parsed_title': file.parsed_title,
            'season': file.season,
            'episode': file.episode,
            'episode_title': file.episode_title,
            'resolution': file.resolution,
            'resolution_width': file.resolution_width,
            'resolution_height': file.resolution_height,
            'video_codec': file.video_codec,
            'audio_codec': file.audio_codec,
            'release_group': file.release_group,
            'source': file.source,
            'year': file.year,
            'is_processed': file.is_processed,
            'processing_errors': file.processing_errors,
            'metadata_id': file.metadata_id,
            'db_created_at': file.db_created_at.isoformat() if file.db_created_at else None,
            'db_updated_at': file.db_updated_at.isoformat() if file.db_updated_at else None,
            'version': getattr(file, 'version', 1)
        }
    
    def _get_anime_metadata_cache_keys(self) -> List[str]:
        """Get all anime metadata cache keys.
        
        Returns:
            List of cache keys for anime metadata
        """
        # This is a simplified implementation
        # In a real implementation, you might need to iterate through cache keys
        # or maintain a separate index of cached anime metadata
        return []
    
    def _get_parsed_file_cache_keys(self) -> List[str]:
        """Get all parsed file cache keys.
        
        Returns:
            List of cache keys for parsed files
        """
        # This is a simplified implementation
        # In a real implementation, you might need to iterate through cache keys
        # or maintain a separate index of cached parsed files
        return []
    
    def _extract_tmdb_id_from_cache_key(self, cache_key: str) -> Optional[int]:
        """Extract TMDB ID from cache key.
        
        Args:
            cache_key: Cache key string
            
        Returns:
            TMDB ID if found, None otherwise
        """
        if cache_key.startswith("anime_metadata:"):
            try:
                return int(cache_key.split(":")[1])
            except (ValueError, IndexError):
                return None
        return None
    
    def _extract_file_id_from_cache_key(self, cache_key: str) -> Optional[int]:
        """Extract file ID from cache key.
        
        Args:
            cache_key: Cache key string
            
        Returns:
            File ID if found, None otherwise
        """
        if cache_key.startswith("parsed_file:"):
            try:
                return int(cache_key.split(":")[1])
            except (ValueError, IndexError):
                return None
        return None
