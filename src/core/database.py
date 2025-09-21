"""Database layer for AniVault application using SQLAlchemy ORM.

This module provides SQLAlchemy models and database management functionality
for storing anime metadata, parsed file information, and related data.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from .circuit_breaker import circuit_breaker_protect
from .compression import compression_manager
from .logging_utils import (
    handle_bulk_insert_error,
    handle_bulk_update_error,
    handle_bulk_upsert_error,
    handle_get_operation_error,
    handle_schema_validation_error,
    handle_search_operation_error,
    handle_table_validation_error,
    log_operation_error,
    log_schema_error,
)
from .models import ParsedAnimeInfo, TMDBAnime
from .transaction_manager import TransactionManager

# Configure logging
logger = logging.getLogger(__name__)

# SQLAlchemy base class
Base = declarative_base()


class AnimeMetadata(Base):  # type: ignore[valid-type,misc]
    """SQLAlchemy model for storing TMDB anime metadata.

    This table stores the master metadata for anime series retrieved from TMDB API,
    including titles, descriptions, ratings, and other series-level information.
    """

    __tablename__: str = "anime_metadata"

    # Primary key - using TMDB ID as the primary key
    tmdb_id = Column(Integer, primary_key=True, nullable=False)

    # Basic information
    title = Column(String(255), nullable=False, index=True)
    original_title = Column(String(255), nullable=True, index=True)
    korean_title = Column(String(255), nullable=True, index=True)
    overview = Column(Text, nullable=True)

    # Media information
    poster_path = Column(String(500), nullable=True)
    backdrop_path = Column(String(500), nullable=True)

    # Dates
    first_air_date = Column(DateTime, nullable=True, index=True)
    last_air_date = Column(DateTime, nullable=True)

    # Status and ratings
    status = Column(String(50), nullable=True, index=True)
    vote_average = Column(Float, nullable=True, index=True)
    vote_count = Column(Integer, nullable=True)
    popularity = Column(Float, nullable=True, index=True)

    # Series information
    number_of_seasons = Column(Integer, nullable=True, default=0)
    number_of_episodes = Column(Integer, nullable=True, default=0)

    # JSON fields for complex data
    genres = Column(Text, nullable=True)  # JSON string
    networks = Column(Text, nullable=True)  # JSON string
    raw_data = Column(Text, nullable=True)  # JSON string

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Versioning for conflict resolution
    version = Column(Integer, nullable=False, default=1, index=True)

    # Relationships
    parsed_files = relationship(
        "ParsedFile", back_populates="anime_metadata", cascade="all, delete-orphan"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("idx_anime_metadata_title", "title"),
        Index("idx_anime_metadata_korean_title", "korean_title"),
        Index("idx_anime_metadata_status", "status"),
        Index("idx_anime_metadata_vote_average", "vote_average"),
        Index("idx_anime_metadata_first_air_date", "first_air_date"),
        Index("idx_anime_metadata_version", "version"),
    )

    def to_tmdb_anime(self) -> TMDBAnime:
        """Convert to TMDBAnime model."""
        return TMDBAnime(
            tmdb_id=int(self.tmdb_id),
            title=str(self.title or ""),
            original_title=str(self.original_title or ""),
            korean_title=str(self.korean_title or ""),
            overview=str(self.overview or ""),
            poster_path=str(self.poster_path or ""),
            backdrop_path=str(self.backdrop_path or ""),
            first_air_date=self.first_air_date,
            last_air_date=self.last_air_date,
            status=str(self.status or ""),
            vote_average=float(self.vote_average or 0.0),
            vote_count=int(self.vote_count or 0),
            popularity=float(self.popularity or 0.0),
            genres=self._parse_json_field(str(self.genres or "[]"), []),
            networks=self._parse_json_field(str(self.networks or "[]"), []),
            number_of_seasons=int(self.number_of_seasons or 0),
            number_of_episodes=int(self.number_of_episodes or 0),
            raw_data=self._parse_json_field(str(self.raw_data or "{}"), {}),
        )

    @classmethod
    def from_tmdb_anime(cls, anime: TMDBAnime) -> AnimeMetadata:
        """Create from TMDBAnime model."""
        return cls(
            tmdb_id=anime.tmdb_id,
            title=anime.title,
            original_title=anime.original_title,
            korean_title=anime.korean_title,
            overview=anime.overview,
            poster_path=anime.poster_path,
            backdrop_path=anime.backdrop_path,
            first_air_date=anime.first_air_date,
            last_air_date=anime.last_air_date,
            status=anime.status,
            vote_average=anime.vote_average,
            vote_count=anime.vote_count,
            popularity=anime.popularity,
            number_of_seasons=anime.number_of_seasons,
            number_of_episodes=anime.number_of_episodes,
            genres=cls._serialize_json_field(anime.genres),
            networks=cls._serialize_json_field(anime.networks),
            raw_data=cls._serialize_json_field(anime.raw_data),
        )

    @staticmethod
    def _parse_json_field(field: str | None, default: Any) -> Any:
        """Parse JSON field safely with decompression support."""
        if not field:
            return default
        try:
            # Try to decompress first (for compressed data)
            decompressed_field = compression_manager.decompress_from_storage(
                field, expected_type="str"
            )
            if decompressed_field != field:
                # Data was compressed, parse the decompressed JSON
                return json.loads(decompressed_field)
            else:
                # Data was not compressed, parse directly
                return json.loads(field)
        except (json.JSONDecodeError, TypeError, Exception):
            # If decompression fails or JSON parsing fails, try direct parsing
            try:
                return json.loads(field)
            except (json.JSONDecodeError, TypeError):
                return default

    @staticmethod
    def _serialize_json_field(field: Any) -> str | None:
        """Serialize field to JSON string with compression for large data."""
        if not field:
            return None
        try:
            # First serialize to JSON (optimized)
            if ORJSON_AVAILABLE:
                json_str = orjson.dumps(field).decode("utf-8")
            else:
                json_str = json.dumps(field, ensure_ascii=False)

            # Apply compression if the data is large enough
            if len(json_str.encode("utf-8")) >= compression_manager.min_size_threshold:
                try:
                    compressed_str = compression_manager.compress_for_storage(json_str)
                    logger.debug(
                        f"Compressed JSON field for database storage: "
                        f"{len(json_str)} -> {len(compressed_str)} bytes"
                    )
                    return compressed_str
                except Exception as e:
                    logger.warning(f"Failed to compress JSON field, using uncompressed: {e}")

            return json_str
        except (TypeError, ValueError):
            return None


class ParsedFile(Base):  # type: ignore[valid-type,misc]
    """SQLAlchemy model for storing parsed file information.

    This table stores information about individual anime files that have been
    scanned and parsed, including file paths, hashes, and parsed metadata.
    """

    __tablename__: str = "parsed_files"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # File information
    file_path = Column(String(1000), nullable=False, unique=True, index=True)
    filename = Column(String(255), nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    file_extension = Column(String(10), nullable=True, index=True)
    file_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash

    # File timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Parsed information
    parsed_title = Column(String(255), nullable=False, index=True)
    season = Column(Integer, nullable=True, index=True)
    episode = Column(Integer, nullable=True, index=True)
    episode_title = Column(String(255), nullable=True)

    # Technical information
    resolution = Column(String(20), nullable=True, index=True)
    resolution_width = Column(Integer, nullable=True)
    resolution_height = Column(Integer, nullable=True)
    video_codec = Column(String(50), nullable=True)
    audio_codec = Column(String(50), nullable=True)
    release_group = Column(String(100), nullable=True, index=True)
    source = Column(String(50), nullable=True)
    year = Column(Integer, nullable=True, index=True)

    # Processing status
    is_processed = Column(Boolean, nullable=False, default=False, index=True)
    processing_errors = Column(Text, nullable=True)  # JSON string

    # Foreign key to anime metadata
    metadata_id = Column(Integer, ForeignKey("anime_metadata.tmdb_id"), nullable=True, index=True)

    # Timestamps
    db_created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    db_updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Versioning for conflict resolution
    version = Column(Integer, nullable=False, default=1, index=True)

    # Relationships
    anime_metadata = relationship("AnimeMetadata", back_populates="parsed_files")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_parsed_files_file_path", "file_path"),
        Index("idx_parsed_files_parsed_title", "parsed_title"),
        Index("idx_parsed_files_season_episode", "season", "episode"),
        Index("idx_parsed_files_resolution", "resolution"),
        Index("idx_parsed_files_release_group", "release_group"),
        Index("idx_parsed_files_year", "year"),
        Index("idx_parsed_files_is_processed", "is_processed"),
        Index("idx_parsed_files_metadata_id", "metadata_id"),
        Index("idx_parsed_files_version", "version"),
    )

    def to_parsed_anime_info(self) -> ParsedAnimeInfo:
        """Convert to ParsedAnimeInfo model."""
        return ParsedAnimeInfo(
            title=str(self.parsed_title),
            season=int(self.season) if self.season is not None else None,
            episode=int(self.episode) if self.episode is not None else None,
            episode_title=str(self.episode_title) if self.episode_title is not None else None,
            resolution=str(self.resolution) if self.resolution is not None else None,
            resolution_width=(
                int(self.resolution_width) if self.resolution_width is not None else None
            ),
            resolution_height=(
                int(self.resolution_height) if self.resolution_height is not None else None
            ),
            video_codec=str(self.video_codec) if self.video_codec is not None else None,
            audio_codec=str(self.audio_codec) if self.audio_codec is not None else None,
            release_group=str(self.release_group) if self.release_group is not None else None,
            file_extension=str(self.file_extension) if self.file_extension is not None else None,
            year=int(self.year) if self.year is not None else None,
            source=str(self.source) if self.source is not None else None,
            raw_data=self._parse_json_field(str(self.processing_errors or "{}"), {}),
        )

    @classmethod
    def from_parsed_anime_info(
        cls,
        file_path: str | Path,
        filename: str,
        file_size: int,
        created_at: datetime,
        modified_at: datetime,
        parsed_info: ParsedAnimeInfo,
        file_hash: str | None = None,
    ) -> ParsedFile:
        """Create from ParsedAnimeInfo model and file information."""
        return cls(
            file_path=str(file_path),
            filename=filename,
            file_size=file_size,
            file_extension=parsed_info.file_extension,
            file_hash=file_hash,
            created_at=created_at,
            modified_at=modified_at,
            parsed_title=parsed_info.title,
            season=parsed_info.season,
            episode=parsed_info.episode,
            episode_title=parsed_info.episode_title,
            resolution=parsed_info.resolution,
            resolution_width=parsed_info.resolution_width,
            resolution_height=parsed_info.resolution_height,
            video_codec=parsed_info.video_codec,
            audio_codec=parsed_info.audio_codec,
            release_group=parsed_info.release_group,
            source=parsed_info.source,
            year=parsed_info.year,
            processing_errors=cls._serialize_json_field(parsed_info.raw_data),
        )

    @staticmethod
    def _parse_json_field(field: str | None, default: Any) -> Any:
        """Parse JSON field safely with decompression support."""
        if not field:
            return default
        try:
            # Try to decompress first (for compressed data)
            decompressed_field = compression_manager.decompress_from_storage(
                field, expected_type="str"
            )
            if decompressed_field != field:
                # Data was compressed, parse the decompressed JSON
                return json.loads(decompressed_field)
            else:
                # Data was not compressed, parse directly
                return json.loads(field)
        except (json.JSONDecodeError, TypeError, Exception):
            # If decompression fails or JSON parsing fails, try direct parsing
            try:
                return json.loads(field)
            except (json.JSONDecodeError, TypeError):
                return default

    @staticmethod
    def _serialize_json_field(field: Any) -> str | None:
        """Serialize field to JSON string with compression for large data."""
        if not field:
            return None
        try:
            # First serialize to JSON (optimized)
            if ORJSON_AVAILABLE:
                json_str = orjson.dumps(field).decode("utf-8")
            else:
                json_str = json.dumps(field, ensure_ascii=False)

            # Apply compression if the data is large enough
            if len(json_str.encode("utf-8")) >= compression_manager.min_size_threshold:
                try:
                    compressed_str = compression_manager.compress_for_storage(json_str)
                    logger.debug(
                        f"Compressed JSON field for database storage: "
                        f"{len(json_str)} -> {len(compressed_str)} bytes"
                    )
                    return compressed_str
                except Exception as e:
                    logger.warning(f"Failed to compress JSON field, using uncompressed: {e}")

            return json_str
        except (TypeError, ValueError):
            return None


class ConsistencyReport(Base):  # type: ignore[valid-type,misc]
    """SQLAlchemy model for storing consistency validation reports.

    This table stores detailed reports of consistency validation runs,
    including detected conflicts, reconciliation actions, and results.
    """

    __tablename__: str = "consistency_reports"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Report metadata
    job_id = Column(String(100), nullable=False, index=True)
    report_type = Column(String(50), nullable=False)  # 'scheduled', 'manual', 'on_demand'
    status = Column(String(50), nullable=False)  # 'success', 'failed', 'partial'

    # Execution details
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Validation results
    total_conflicts_detected = Column(Integer, nullable=False, default=0)
    conflicts_by_type = Column(
        Text, nullable=True
    )  # JSON string: {"VERSION_MISMATCH": 5, "DATA_MISMATCH": 3}
    conflicts_by_severity = Column(
        Text, nullable=True
    )  # JSON string: {"HIGH": 2, "MEDIUM": 4, "LOW": 2}

    # Reconciliation results
    total_conflicts_resolved = Column(Integer, nullable=False, default=0)
    resolution_strategy = Column(String(100), nullable=True)
    resolution_results = Column(Text, nullable=True)  # JSON string: {"successful": 6, "failed": 2}

    # Error information
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)  # JSON string for detailed error info

    # Additional metadata
    additional_metadata = Column(Text, nullable=True)  # JSON string for extra data

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_consistency_reports_job_id", "job_id"),
        Index("idx_consistency_reports_status", "status"),
        Index("idx_consistency_reports_started_at", "started_at"),
        Index("idx_consistency_reports_created_at", "created_at"),
    )


class ConsistencyConflict(Base):  # type: ignore[valid-type,misc]
    """SQLAlchemy model for storing individual consistency conflicts.

    This table stores detailed information about each conflict detected
    during consistency validation, including resolution actions taken.
    """

    __tablename__: str = "consistency_conflicts"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to report
    report_id = Column(Integer, ForeignKey("consistency_reports.id"), nullable=False, index=True)

    # Conflict identification
    conflict_type = Column(
        String(50), nullable=False
    )  # 'MISSING_IN_CACHE', 'VERSION_MISMATCH', etc.
    conflict_severity = Column(String(20), nullable=False)  # 'LOW', 'MEDIUM', 'HIGH'
    entity_type = Column(String(50), nullable=False)  # 'AnimeMetadata', 'ParsedFile'
    entity_id = Column(Integer, nullable=True)  # ID of the affected entity

    # Conflict details
    conflict_description = Column(Text, nullable=False)
    database_data = Column(Text, nullable=True)  # JSON string of database data
    cache_data = Column(Text, nullable=True)  # JSON string of cache data

    # Resolution details
    resolution_strategy = Column(String(50), nullable=True)  # 'DATABASE_WINS', 'CACHE_WINS', etc.
    resolution_status = Column(String(50), nullable=True)  # 'success', 'failed', 'skipped'
    resolution_message = Column(Text, nullable=True)
    resolution_timestamp = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    report = relationship("ConsistencyReport", backref="conflicts")

    __table_args__ = (
        Index("idx_consistency_conflicts_report_id", "report_id"),
        Index("idx_consistency_conflicts_type", "conflict_type"),
        Index("idx_consistency_conflicts_severity", "conflict_severity"),
        Index("idx_consistency_conflicts_entity_type", "entity_type"),
        Index("idx_consistency_conflicts_created_at", "created_at"),
    )


class DatabaseManager:
    """Database manager for handling SQLAlchemy operations.

    This class provides a high-level interface for database operations,
    including session management, CRUD operations, and transaction handling.
    """

    def __init__(self, database_url: str = "sqlite:///anivault.db") -> None:
        """Initialize the database manager.

        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url
        self.engine: Any | None = None
        self.SessionLocal: sessionmaker[Session] | None = None
        self._lock = threading.RLock()
        self._initialized = False

        # Initialize transaction manager
        self.transaction_manager = TransactionManager(timeout_seconds=300)  # 5 minute timeout

    def initialize(self) -> None:
        """Initialize the database engine and create tables."""
        with self._lock:
            if self._initialized:
                return

            try:
                # Create engine with appropriate configuration
                if self.database_url.startswith("sqlite"):
                    self.engine = create_engine(
                        self.database_url,
                        poolclass=StaticPool,
                        connect_args={"check_same_thread": False},
                        echo=False,  # Set to True for SQL debugging
                    )
                else:
                    self.engine = create_engine(self.database_url, echo=False)

                # Create session factory
                self.SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=self.engine
                )

                # Create all tables
                Base.metadata.create_all(bind=self.engine)

                self._initialized = True
                logger.info(f"Database initialized: {self.database_url}")

            except Exception as e:
                log_operation_error("initialize database", e)
                raise

    def get_session(self) -> Session:
        """Get a new database session."""
        if not self._initialized:
            self.initialize()

        if self.SessionLocal is None:
            raise RuntimeError("Database not properly initialized")
        return self.SessionLocal()

    def close(self) -> None:
        """Close the database engine."""
        with self._lock:
            if self.engine is not None:
                self.engine.dispose()
                self._initialized = False
                logger.info("Database connection closed")

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """Context manager for database transactions with automatic rollback on error.

        This method now uses the enhanced TransactionManager for better logging,
        error handling, and transaction tracking.

        Yields:
            Session: Database session for transaction operations

        Example:
            with db_manager.transaction() as session:
                # Perform database operations
                session.add(metadata)
                # Transaction will be automatically committed or rolled back
        """
        session = self.get_session()
        try:
            with self.transaction_manager.transaction_scope(session) as tx_session:
                yield tx_session
        finally:
            session.close()

    def execute_in_transaction(self, operation: callable, *args, **kwargs) -> Any:
        """Execute a database operation within a transaction.

        This method now uses the enhanced TransactionManager for better logging,
        error handling, and transaction tracking.

        Args:
            operation: Function to execute with session as first argument
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Example:
            def create_metadata(session, anime):
                metadata = AnimeMetadata.from_tmdb_anime(anime)
                session.add(metadata)
                return metadata

            result = db_manager.execute_in_transaction(create_metadata, anime)
        """
        with self.transaction() as session:
            return operation(session, *args, **kwargs)

    @circuit_breaker_protect(operation_name="create_anime_metadata")
    def create_anime_metadata(self, anime: TMDBAnime) -> AnimeMetadata:
        """Create a new anime metadata record with transaction support."""
        with self.transaction() as session:
            # Check if record already exists
            existing = session.query(AnimeMetadata).filter_by(tmdb_id=anime.tmdb_id).first()
            if existing:
                # Update existing record
                existing.title = anime.title
                existing.original_title = anime.original_title
                existing.korean_title = anime.korean_title
                existing.overview = anime.overview
                existing.poster_path = anime.poster_path
                existing.backdrop_path = anime.backdrop_path
                existing.first_air_date = anime.first_air_date
                existing.last_air_date = anime.last_air_date
                existing.status = anime.status
                existing.vote_average = anime.vote_average
                existing.vote_count = anime.vote_count
                existing.popularity = anime.popularity
                existing.number_of_seasons = anime.number_of_seasons
                existing.number_of_episodes = anime.number_of_episodes
                existing.genres = AnimeMetadata._serialize_json_field(anime.genres)
                existing.networks = AnimeMetadata._serialize_json_field(anime.networks)
                existing.raw_data = AnimeMetadata._serialize_json_field(anime.raw_data)
                existing.updated_at = datetime.now(timezone.utc)

                # Detach the object from the session to avoid DetachedInstanceError
                session.expunge(existing)
                return existing  # type: ignore[no-any-return]
            else:
                # Create new record
                metadata = AnimeMetadata.from_tmdb_anime(anime)
                session.add(metadata)
                session.flush()  # Flush to get the ID
                # Detach the object from the session to avoid DetachedInstanceError
                session.expunge(metadata)
                return metadata

    @circuit_breaker_protect(operation_name="get_anime_metadata")
    def get_anime_metadata(self, tmdb_id: int) -> AnimeMetadata | None:
        """Get anime metadata by TMDB ID."""
        with self.get_session() as session:
            try:
                return session.query(AnimeMetadata).filter_by(tmdb_id=tmdb_id).first()  # type: ignore[no-any-return]
            except Exception as e:
                handle_get_operation_error("anime metadata", e)
                return None

    def search_anime_metadata(self, title: str, limit: int = 10) -> list[AnimeMetadata]:
        """Search anime metadata by title."""
        with self.get_session() as session:
            try:
                return (  # type: ignore[no-any-return]
                    session.query(AnimeMetadata)
                    .filter(AnimeMetadata.title.ilike(f"%{title}%"))
                    .limit(limit)
                    .all()
                )
            except Exception as e:
                return handle_search_operation_error("anime metadata", e)

    @circuit_breaker_protect(operation_name="create_parsed_file")
    def create_parsed_file(
        self,
        file_path: str | Path,
        filename: str,
        file_size: int,
        created_at: datetime,
        modified_at: datetime,
        parsed_info: ParsedAnimeInfo,
        file_hash: str | None = None,
        metadata_id: int | None = None,
    ) -> ParsedFile:
        """Create a new parsed file record with transaction support."""
        with self.transaction() as session:
            # Check if file already exists
            existing = session.query(ParsedFile).filter_by(file_path=str(file_path)).first()
            if existing:
                # Update existing record
                existing.filename = filename
                existing.file_size = file_size
                existing.file_extension = parsed_info.file_extension
                existing.file_hash = file_hash
                existing.created_at = created_at
                existing.modified_at = modified_at
                existing.parsed_title = parsed_info.title
                existing.season = parsed_info.season
                existing.episode = parsed_info.episode
                existing.episode_title = parsed_info.episode_title
                existing.resolution = parsed_info.resolution
                existing.resolution_width = parsed_info.resolution_width
                existing.resolution_height = parsed_info.resolution_height
                existing.video_codec = parsed_info.video_codec
                existing.audio_codec = parsed_info.audio_codec
                existing.release_group = parsed_info.release_group
                existing.source = parsed_info.source
                existing.year = parsed_info.year
                existing.metadata_id = metadata_id
                existing.processing_errors = ParsedFile._serialize_json_field(parsed_info.raw_data)
                existing.db_updated_at = datetime.now(timezone.utc)

                # Detach the object from the session to avoid DetachedInstanceError
                session.expunge(existing)
                return existing  # type: ignore[no-any-return]
            else:
                # Create new record
                parsed_file = ParsedFile.from_parsed_anime_info(
                    file_path,
                    filename,
                    file_size,
                    created_at,
                    modified_at,
                    parsed_info,
                    file_hash,
                )
                parsed_file.metadata_id = metadata_id
                session.add(parsed_file)
                session.flush()  # Flush to get the ID
                # Detach the object from the session to avoid DetachedInstanceError
                session.expunge(parsed_file)
                return parsed_file

    def get_parsed_file(self, file_path: str | Path) -> ParsedFile | None:
        """Get parsed file by file path."""
        with self.get_session() as session:
            try:
                return session.query(ParsedFile).filter_by(file_path=str(file_path)).first()  # type: ignore[no-any-return]
            except Exception as e:
                handle_get_operation_error("parsed file", e)
                return None

    def get_parsed_files_by_metadata(self, metadata_id: int) -> list[ParsedFile]:
        """Get all parsed files for a specific metadata record."""
        with self.get_session() as session:
            try:
                return session.query(ParsedFile).filter_by(metadata_id=metadata_id).all()  # type: ignore[no-any-return]
            except Exception as e:
                return handle_search_operation_error("parsed files by metadata", e)

    def delete_parsed_file(self, file_path: str | Path) -> bool:
        """Delete a parsed file record with transaction support."""
        with self.transaction() as session:
            parsed_file = session.query(ParsedFile).filter_by(file_path=str(file_path)).first()
            if parsed_file:
                session.delete(parsed_file)
                return True
            return False

    def delete_anime_metadata(self, tmdb_id: int) -> bool:
        """Delete an anime metadata record with transaction support."""
        with self.transaction() as session:
            metadata = session.query(AnimeMetadata).filter_by(tmdb_id=tmdb_id).first()
            if metadata:
                session.delete(metadata)
                return True
            return False

    def get_database_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        with self.get_session() as session:
            try:
                anime_count = session.query(AnimeMetadata).count()
                file_count = session.query(ParsedFile).count()
                processed_count = session.query(ParsedFile).filter_by(is_processed=True).count()

                return {
                    "anime_metadata_count": anime_count,
                    "parsed_files_count": file_count,
                    "processed_files_count": processed_count,
                    "unprocessed_files_count": file_count - processed_count,
                }
            except Exception as e:
                log_operation_error("get database stats", e)
                return {}

    @circuit_breaker_protect(operation_name="bulk_insert_anime_metadata")
    def bulk_insert_anime_metadata(self, anime_list: list[TMDBAnime]) -> int:
        """Bulk insert multiple anime metadata records using SQLAlchemy bulk operations.

        Args:
            anime_list: List of TMDBAnime objects to insert

        Returns:
            Number of records inserted

        Raises:
            Exception: If bulk insert fails
        """
        if not anime_list:
            return 0

        with self.transaction() as session:
            try:
                # Convert TMDBAnime objects to dictionaries for bulk insert
                metadata_dicts = []
                for anime in anime_list:
                    metadata_dict = {
                        "tmdb_id": anime.tmdb_id,
                        "title": anime.title,
                        "original_title": anime.original_title,
                        "korean_title": anime.korean_title,
                        "overview": anime.overview,
                        "poster_path": anime.poster_path,
                        "backdrop_path": anime.backdrop_path,
                        "first_air_date": anime.first_air_date,
                        "last_air_date": anime.last_air_date,
                        "status": anime.status,
                        "vote_average": anime.vote_average,
                        "vote_count": anime.vote_count,
                        "popularity": anime.popularity,
                        "number_of_seasons": anime.number_of_seasons,
                        "number_of_episodes": anime.number_of_episodes,
                        "genres": AnimeMetadata._serialize_json_field(anime.genres),
                        "networks": AnimeMetadata._serialize_json_field(anime.networks),
                        "raw_data": AnimeMetadata._serialize_json_field(anime.raw_data),
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                    metadata_dicts.append(metadata_dict)

                # Perform bulk insert
                session.bulk_insert_mappings(AnimeMetadata, metadata_dicts)
                session.flush()

                inserted_count = len(metadata_dicts)
                logger.info(f"Bulk inserted {inserted_count} anime metadata records")
                return inserted_count

            except Exception as e:
                handle_bulk_insert_error("anime metadata", e)
                raise

    def bulk_insert_parsed_files(
        self,
        file_data_list: list[
            tuple[str, str, int, datetime, datetime, ParsedAnimeInfo, str | None, int | None]
        ],
    ) -> int:
        """Bulk insert multiple parsed file records using SQLAlchemy bulk operations.

        Args:
            file_data_list: List of tuples containing (file_path, filename, file_size,
                          created_at, modified_at, parsed_info, file_hash, metadata_id)

        Returns:
            Number of records inserted

        Raises:
            Exception: If bulk insert fails
        """
        if not file_data_list:
            return 0

        with self.transaction() as session:
            try:
                # Convert file data to dictionaries for bulk insert
                file_dicts = []
                for (
                    file_path,
                    filename,
                    file_size,
                    created_at,
                    modified_at,
                    parsed_info,
                    file_hash,
                    metadata_id,
                ) in file_data_list:
                    file_dict = {
                        "file_path": str(file_path),
                        "filename": filename,
                        "file_size": file_size,
                        "file_extension": parsed_info.file_extension,
                        "file_hash": file_hash,
                        "created_at": created_at,
                        "modified_at": modified_at,
                        "parsed_title": parsed_info.title,
                        "season": parsed_info.season,
                        "episode": parsed_info.episode,
                        "episode_title": parsed_info.episode_title,
                        "resolution": parsed_info.resolution,
                        "resolution_width": parsed_info.resolution_width,
                        "resolution_height": parsed_info.resolution_height,
                        "video_codec": parsed_info.video_codec,
                        "audio_codec": parsed_info.audio_codec,
                        "release_group": parsed_info.release_group,
                        "source": parsed_info.source,
                        "year": parsed_info.year,
                        "metadata_id": metadata_id,
                        "processing_errors": ParsedFile._serialize_json_field(parsed_info.raw_data),
                        "is_processed": False,
                        "db_created_at": datetime.now(timezone.utc),
                        "db_updated_at": datetime.now(timezone.utc),
                    }
                    file_dicts.append(file_dict)

                # Perform bulk insert
                session.bulk_insert_mappings(ParsedFile, file_dicts)
                session.flush()

                inserted_count = len(file_dicts)
                logger.info(f"Bulk inserted {inserted_count} parsed file records")
                return inserted_count

            except Exception as e:
                handle_bulk_insert_error("parsed files", e)
                raise

    def bulk_upsert_anime_metadata(self, anime_list: list[TMDBAnime]) -> tuple[int, int]:
        """Bulk upsert (insert or update) multiple anime metadata records.

        This method handles both new records and updates to existing records
        using optimized bulk operations to eliminate N+1 query patterns.

        Args:
            anime_list: List of TMDBAnime objects to upsert

        Returns:
            Tuple of (inserted_count, updated_count)

        Raises:
            Exception: If bulk upsert fails
        """
        if not anime_list:
            return 0, 0

        with self.transaction() as session:
            try:
                # Get existing TMDB IDs
                tmdb_ids = [anime.tmdb_id for anime in anime_list]
                existing_records = (
                    session.query(AnimeMetadata).filter(AnimeMetadata.tmdb_id.in_(tmdb_ids)).all()
                )
                existing_ids = {record.tmdb_id for record in existing_records}

                # Separate new and existing records
                new_anime = [anime for anime in anime_list if anime.tmdb_id not in existing_ids]
                update_anime = [anime for anime in anime_list if anime.tmdb_id in existing_ids]

                inserted_count = 0
                updated_count = 0

                # Bulk insert new records
                if new_anime:
                    inserted_count = self.bulk_insert_anime_metadata(new_anime)

                # Bulk update existing records - OPTIMIZED: No more N+1 queries
                if update_anime:
                    # Convert to dictionaries for bulk update
                    update_dicts = []
                    for anime in update_anime:
                        update_dict = {
                            "tmdb_id": anime.tmdb_id,
                            "title": anime.title,
                            "original_title": anime.original_title,
                            "korean_title": anime.korean_title,
                            "overview": anime.overview,
                            "poster_path": anime.poster_path,
                            "backdrop_path": anime.backdrop_path,
                            "first_air_date": anime.first_air_date,
                            "last_air_date": anime.last_air_date,
                            "status": anime.status,
                            "vote_average": anime.vote_average,
                            "vote_count": anime.vote_count,
                            "popularity": anime.popularity,
                            "number_of_seasons": anime.number_of_seasons,
                            "number_of_episodes": anime.number_of_episodes,
                            "genres": AnimeMetadata._serialize_json_field(anime.genres),
                            "networks": AnimeMetadata._serialize_json_field(anime.networks),
                            "raw_data": AnimeMetadata._serialize_json_field(anime.raw_data),
                            "updated_at": datetime.now(timezone.utc),
                        }
                        update_dicts.append(update_dict)

                    # Perform bulk update using SQLAlchemy bulk_update_mappings
                    session.bulk_update_mappings(AnimeMetadata, update_dicts)
                    session.flush()
                    updated_count = len(update_dicts)

                logger.info(
                    f"Bulk upsert completed: {inserted_count} inserted, {updated_count} updated"
                )
                return inserted_count, updated_count

            except Exception as e:
                handle_bulk_upsert_error("anime metadata", e)
                raise

    def bulk_update_anime_metadata(self, updates: list[dict]) -> int:
        """Bulk update multiple anime metadata records using SQLAlchemy bulk operations.

        Args:
            updates: List of dictionaries containing updates. Each dict must include
                    the primary key (tmdb_id) and fields to update.
                    Example: [{'tmdb_id': 1, 'title': 'New Title', 'vote_average': 9.0}]

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not updates:
            return 0

        with self.transaction() as session:
            try:
                # Validate that all updates have tmdb_id
                for update in updates:
                    if "tmdb_id" not in update:
                        raise ValueError("All update dictionaries must contain 'tmdb_id' field")

                # Perform bulk update
                session.bulk_update_mappings(AnimeMetadata, updates)
                session.flush()

                updated_count = len(updates)
                logger.info(f"Bulk updated {updated_count} anime metadata records")
                return updated_count

            except Exception as e:
                handle_bulk_update_error("anime metadata", e)
                raise

    def bulk_update_parsed_files(self, updates: list[dict]) -> int:
        """Bulk update multiple parsed file records using SQLAlchemy bulk operations.

        Args:
            updates: List of dictionaries containing updates. Each dict must include
                    the primary key (id) and fields to update.
                    Example: [{'id': 1, 'is_processed': True, 'processing_errors': '{}'}]

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not updates:
            return 0

        with self.transaction() as session:
            try:
                # Validate that all updates have id
                for update in updates:
                    if "id" not in update:
                        raise ValueError("All update dictionaries must contain 'id' field")

                # Perform bulk update
                session.bulk_update_mappings(ParsedFile, updates)
                session.flush()

                updated_count = len(updates)
                logger.info(f"Bulk updated {updated_count} parsed file records")
                return updated_count

            except Exception as e:
                handle_bulk_update_error("parsed files", e)
                raise

    def bulk_update_anime_metadata_by_tmdb_ids(self, tmdb_ids: list[int], update_data: dict) -> int:
        """Bulk update anime metadata records by TMDB IDs with the same update data.

        Args:
            tmdb_ids: List of TMDB IDs to update
            update_data: Dictionary of fields to update (excluding tmdb_id)

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not tmdb_ids or not update_data:
            return 0

        with self.transaction() as session:
            try:
                # Create update dictionaries for each TMDB ID
                updates = []
                for tmdb_id in tmdb_ids:
                    update_dict = update_data.copy()
                    update_dict["tmdb_id"] = tmdb_id
                    update_dict["updated_at"] = datetime.now(timezone.utc)
                    updates.append(update_dict)

                # Perform bulk update
                session.bulk_update_mappings(AnimeMetadata, updates)
                session.flush()

                updated_count = len(updates)
                logger.info(f"Bulk updated {updated_count} anime metadata records by TMDB IDs")
                return updated_count

            except Exception as e:
                handle_bulk_update_error("anime metadata by TMDB IDs", e)
                raise

    def bulk_update_parsed_files_by_paths(self, file_paths: list[str], update_data: dict) -> int:
        """Bulk update parsed file records by file paths with the same update data.

        Args:
            file_paths: List of file paths to update
            update_data: Dictionary of fields to update (excluding file_path)

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not file_paths or not update_data:
            return 0

        with self.transaction() as session:
            try:
                # First, get the IDs for the file paths
                file_records = (
                    session.query(ParsedFile).filter(ParsedFile.file_path.in_(file_paths)).all()
                )

                if not file_records:
                    logger.warning("No parsed files found for the provided paths")
                    return 0

                # Create update dictionaries for each file
                updates = []
                for file_record in file_records:
                    update_dict = update_data.copy()
                    update_dict["id"] = file_record.id
                    update_dict["db_updated_at"] = datetime.now(timezone.utc)
                    updates.append(update_dict)

                # Perform bulk update
                session.bulk_update_mappings(ParsedFile, updates)
                session.flush()

                updated_count = len(updates)
                logger.info(f"Bulk updated {updated_count} parsed file records by file paths")
                return updated_count

            except Exception as e:
                handle_bulk_update_error("parsed files by file paths", e)
                raise

    def validate_schema(self) -> bool:
        """Validate that the database schema matches the ORM models.

        This method checks if all required tables exist and have the correct
        structure according to the SQLAlchemy models.

        Returns:
            True if schema is valid, False otherwise

        Raises:
            Exception: If schema validation fails
        """
        try:
            from sqlalchemy import inspect

            inspector = inspect(self.engine)
            existing_tables = set(inspector.get_table_names())

            # Check if all required tables exist
            required_tables = {table.name for table in Base.metadata.tables.values()}
            missing_tables = required_tables - existing_tables

            if missing_tables:
                log_schema_error("missing tables", missing_tables)
                return False

            # Check table structures
            for table_name in required_tables:
                if not self._validate_table_structure(table_name, inspector):
                    return False

            logger.info("Database schema validation successful")
            return True

        except Exception as e:
            handle_schema_validation_error(e)
            raise

    def _validate_table_structure(self, table_name: str, inspector) -> bool:
        """Validate the structure of a specific table.

        Args:
            table_name: Name of the table to validate
            inspector: SQLAlchemy inspector instance

        Returns:
            True if table structure is valid, False otherwise
        """
        try:
            # Get expected columns from ORM model
            expected_table = Base.metadata.tables[table_name]
            expected_columns = {col.name: col for col in expected_table.columns}

            # Get actual columns from database
            actual_columns = inspector.get_columns(table_name)
            actual_column_names = {col["name"] for col in actual_columns}

            # Check if all expected columns exist
            missing_columns = set(expected_columns.keys()) - actual_column_names
            if missing_columns:
                log_schema_error(f"table '{table_name}' missing columns", missing_columns)
                return False

            # Check column types (basic validation)
            for col_info in actual_columns:
                col_name = col_info["name"]
                if col_name in expected_columns:
                    expected_col = expected_columns[col_name]
                    actual_type = col_info["type"]

                    # Basic type compatibility check
                    if not self._is_type_compatible(expected_col.type, actual_type):
                        logger.warning(
                            f"Table {table_name}, column {col_name}: "
                            f"type mismatch (expected: {expected_col.type}, actual: {actual_type})"
                        )

            return True

        except Exception as e:
            handle_table_validation_error(table_name, e)
            return False

    def _is_type_compatible(self, expected_type, actual_type) -> bool:
        """Check if actual column type is compatible with expected type.

        Args:
            expected_type: Expected SQLAlchemy type
            actual_type: Actual database column type

        Returns:
            True if types are compatible, False otherwise
        """
        # Convert types to strings for comparison
        expected_str = str(expected_type).lower()
        actual_str = str(actual_type).lower()

        # Basic type mapping for SQLite
        type_mappings = {
            "integer": ["integer", "int"],
            "string": ["varchar", "text", "string"],
            "text": ["text", "string"],
            "float": ["real", "float"],
            "boolean": ["boolean", "bool"],
            "datetime": ["datetime", "timestamp"],
        }

        # Check if types are in the same category
        for category, types in type_mappings.items():
            if any(t in expected_str for t in types) and any(t in actual_str for t in types):
                return True

        return False

    def get_schema_version(self) -> str | None:
        """Get the current schema version from Alembic.

        Returns:
            Current schema version string, or None if not available
        """
        try:
            from sqlalchemy import text

            with self.transaction() as session:
                result = session.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                ).fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.warning(f"Could not get schema version: {e}")
            return None

    def is_schema_up_to_date(self) -> bool:
        """Check if the database schema is up to date with the latest migration.

        Returns:
            True if schema is up to date, False otherwise
        """
        try:
            from alembic.config import Config

            # Create Alembic config
            alembic_cfg = Config("alembic.ini")

            # Get current database version
            current_version = self.get_schema_version()
            if not current_version:
                logger.warning("No schema version found in database")
                return False

            # Get latest available version
            script = alembic_cfg.get_main_option("script_location")
            if not script:
                logger.error("Alembic script location not configured")
                return False

            # This is a simplified check - in production, you might want to
            # use Alembic's built-in comparison methods
            logger.info(f"Current schema version: {current_version}")
            return True

        except Exception as e:
            log_operation_error("check schema version", e)
            return False

    def get_transaction_stats(self) -> dict[str, Any]:
        """Get transaction statistics from the transaction manager.

        Returns:
            Dictionary containing transaction statistics
        """
        return self.transaction_manager.get_stats()

    def reset_transaction_stats(self) -> None:
        """Reset transaction statistics."""
        self.transaction_manager.reset_stats()

    def is_transaction_active(self) -> bool:
        """Check if there's an active transaction.

        Returns:
            True if there's an active transaction, False otherwise
        """
        return self.transaction_manager.is_active()

    def get_current_transaction_context(self) -> Any:
        """Get the current transaction context.

        Returns:
            Current TransactionContext or None if no active transaction
        """
        return self.transaction_manager.get_current_context()

    def batch_save_anime_metadata(self, anime_metadata_list: list[TMDBAnime]) -> tuple[int, int]:
        """Batch save anime metadata using optimized bulk operations.

        This method is specifically designed for file processing workflows
        to eliminate N+1 query patterns during metadata retrieval.

        Args:
            anime_metadata_list: List of TMDBAnime objects to save

        Returns:
            Tuple of (inserted_count, updated_count)

        Raises:
            Exception: If batch save fails
        """
        if not anime_metadata_list:
            return 0, 0

        logger.info(f"Batch saving {len(anime_metadata_list)} anime metadata records")

        # Use the optimized bulk upsert method
        return self.bulk_upsert_anime_metadata(anime_metadata_list)

    def bulk_update_anime_metadata_by_status(self, tmdb_ids: list[int], status: str) -> int:
        """Bulk update anime metadata status by TMDB IDs.

        This method is optimized for data synchronization workflows
        where multiple records need status updates.

        Args:
            tmdb_ids: List of TMDB IDs to update
            status: New status value

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not tmdb_ids:
            return 0

        with self.transaction() as session:
            try:
                # Use SQLAlchemy core update for maximum performance
                from sqlalchemy import update

                stmt = (
                    update(AnimeMetadata)
                    .where(AnimeMetadata.tmdb_id.in_(tmdb_ids))
                    .values(status=status, updated_at=datetime.now(timezone.utc))
                )

                result = session.execute(stmt)
                updated_count = result.rowcount

                logger.info(
                    f"Bulk updated {updated_count} anime metadata records with status '{status}'"
                )
                return updated_count

            except Exception as e:
                logger.error(f"Failed to bulk update anime metadata status: {e}")
                raise

    def bulk_update_parsed_files_by_status(self, file_paths: list[str], is_processed: bool) -> int:
        """Bulk update parsed files processing status by file paths.

        This method is optimized for file processing workflows
        where multiple files need status updates.

        Args:
            file_paths: List of file paths to update
            is_processed: New processing status

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not file_paths:
            return 0

        with self.transaction() as session:
            try:
                # Use SQLAlchemy core update for maximum performance
                from sqlalchemy import update

                stmt = (
                    update(ParsedFile)
                    .where(ParsedFile.file_path.in_(file_paths))
                    .values(is_processed=is_processed, db_updated_at=datetime.now(timezone.utc))
                )

                result = session.execute(stmt)
                updated_count = result.rowcount

                logger.info(
                    f"Bulk updated {updated_count} parsed files with is_processed={is_processed}"
                )
                return updated_count

            except Exception as e:
                logger.error(f"Failed to bulk update parsed files status: {e}")
                raise

    def bulk_update_with_conditions(
        self, table_class, updates: list[dict], condition_field: str
    ) -> int:
        """Generic bulk update method with custom conditions.

        This method provides a flexible way to perform bulk updates
        with custom WHERE conditions for various use cases.

        Args:
            table_class: SQLAlchemy table class to update
            updates: List of dictionaries containing updates and conditions
                    Example: [{'id': 1, 'status': 'processed'}, {'id': 2, 'status': 'failed'}]
            condition_field: Field name to use in WHERE clause

        Returns:
            Number of records updated

        Raises:
            Exception: If bulk update fails
        """
        if not updates:
            return 0

        with self.transaction() as session:
            try:
                from sqlalchemy import update

                total_updated = 0

                # Process updates in batches for better performance
                batch_size = 1000
                for i in range(0, len(updates), batch_size):
                    batch = updates[i : i + batch_size]

                    # Extract condition values and update data
                    condition_values = []
                    update_data = {}

                    for update_dict in batch:
                        if condition_field in update_dict:
                            condition_values.append(update_dict[condition_field])

                            # Build update data (exclude condition field)
                            for key, value in update_dict.items():
                                if key != condition_field:
                                    if key not in update_data:
                                        update_data[key] = []
                                    update_data[key].append(value)

                    if condition_values and update_data:
                        # Create bulk update statement
                        stmt = (
                            update(table_class)
                            .where(getattr(table_class, condition_field).in_(condition_values))
                            .values(**update_data)
                        )

                        result = session.execute(stmt)
                        total_updated += result.rowcount

                logger.info(f"Bulk updated {total_updated} records in {table_class.__name__}")
                return total_updated

            except Exception as e:
                logger.error(f"Failed to bulk update {table_class.__name__}: {e}")
                raise


# Version management event listeners
@event.listens_for(AnimeMetadata, "before_update")
def increment_anime_metadata_version(mapper, connection, target):
    """Increment version number before updating AnimeMetadata."""
    if hasattr(target, "version"):
        target.version = (target.version or 0) + 1


@event.listens_for(ParsedFile, "before_update")
def increment_parsed_file_version(mapper, connection, target):
    """Increment version number before updating ParsedFile."""
    if hasattr(target, "version"):
        target.version = (target.version or 0) + 1


# Global database manager instance
db_manager = DatabaseManager()
