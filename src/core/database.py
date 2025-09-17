"""
Database layer for AniVault application using SQLAlchemy ORM.

This module provides SQLAlchemy models and database management functionality
for storing anime metadata, parsed file information, and related data.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

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
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import ParsedAnimeInfo, TMDBAnime

# Configure logging
logger = logging.getLogger(__name__)

# SQLAlchemy base class
Base = declarative_base()


class AnimeMetadata(Base):
    """
    SQLAlchemy model for storing TMDB anime metadata.

    This table stores the master metadata for anime series retrieved from TMDB API,
    including titles, descriptions, ratings, and other series-level information.
    """

    __tablename__ = "anime_metadata"

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
    )

    def to_tmdb_anime(self) -> TMDBAnime:
        """Convert to TMDBAnime model."""
        return TMDBAnime(
            tmdb_id=self.tmdb_id,
            title=self.title or "",
            original_title=self.original_title or "",
            korean_title=self.korean_title or "",
            overview=self.overview or "",
            poster_path=self.poster_path or "",
            backdrop_path=self.backdrop_path or "",
            first_air_date=self.first_air_date,
            last_air_date=self.last_air_date,
            status=self.status or "",
            vote_average=self.vote_average or 0.0,
            vote_count=self.vote_count or 0,
            popularity=self.popularity or 0.0,
            genres=self._parse_json_field(self.genres, []),
            networks=self._parse_json_field(self.networks, []),
            number_of_seasons=self.number_of_seasons or 0,
            number_of_episodes=self.number_of_episodes or 0,
            raw_data=self._parse_json_field(self.raw_data, {}),
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
        """Parse JSON field safely."""
        if not field:
            return default
        try:
            return json.loads(field)
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def _serialize_json_field(field: Any) -> str | None:
        """Serialize field to JSON string."""
        if not field:
            return None
        try:
            return json.dumps(field, ensure_ascii=False)
        except (TypeError, ValueError):
            return None


class ParsedFile(Base):
    """
    SQLAlchemy model for storing parsed file information.

    This table stores information about individual anime files that have been
    scanned and parsed, including file paths, hashes, and parsed metadata.
    """

    __tablename__ = "parsed_files"

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
    )

    def to_parsed_anime_info(self) -> ParsedAnimeInfo:
        """Convert to ParsedAnimeInfo model."""
        return ParsedAnimeInfo(
            title=self.parsed_title,
            season=self.season,
            episode=self.episode,
            episode_title=self.episode_title,
            resolution=self.resolution,
            resolution_width=self.resolution_width,
            resolution_height=self.resolution_height,
            video_codec=self.video_codec,
            audio_codec=self.audio_codec,
            release_group=self.release_group,
            file_extension=self.file_extension,
            year=self.year,
            source=self.source,
            raw_data=self._parse_json_field(self.processing_errors, {}),
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
        """Parse JSON field safely."""
        if not field:
            return default
        try:
            return json.loads(field)
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def _serialize_json_field(field: Any) -> str | None:
        """Serialize field to JSON string."""
        if not field:
            return None
        try:
            return json.dumps(field, ensure_ascii=False)
        except (TypeError, ValueError):
            return None


class DatabaseManager:
    """
    Database manager for handling SQLAlchemy operations.

    This class provides a high-level interface for database operations,
    including session management, CRUD operations, and transaction handling.
    """

    def __init__(self, database_url: str = "sqlite:///anivault.db") -> None:
        """
        Initialize the database manager.

        Args:
            database_url: SQLAlchemy database URL
        """
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._lock = threading.RLock()
        self._initialized = False

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
                logger.error(f"Failed to initialize database: {e}")
                raise

    def get_session(self) -> Session:
        """Get a new database session."""
        if not self._initialized:
            self.initialize()

        return self.SessionLocal()

    def close(self) -> None:
        """Close the database engine."""
        with self._lock:
            if self.engine:
                self.engine.dispose()
                self._initialized = False
                logger.info("Database connection closed")

    def create_anime_metadata(self, anime: TMDBAnime) -> AnimeMetadata:
        """Create a new anime metadata record."""
        with self.get_session() as session:
            try:
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
                    existing.updated_at = datetime.utcnow()

                    session.commit()
                    return existing
                else:
                    # Create new record
                    metadata = AnimeMetadata.from_tmdb_anime(anime)
                    session.add(metadata)
                    session.commit()
                    session.refresh(metadata)
                    return metadata

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to create anime metadata: {e}")
                raise

    def get_anime_metadata(self, tmdb_id: int) -> AnimeMetadata | None:
        """Get anime metadata by TMDB ID."""
        with self.get_session() as session:
            try:
                return session.query(AnimeMetadata).filter_by(tmdb_id=tmdb_id).first()
            except Exception as e:
                logger.error(f"Failed to get anime metadata: {e}")
                return None

    def search_anime_metadata(self, title: str, limit: int = 10) -> list[AnimeMetadata]:
        """Search anime metadata by title."""
        with self.get_session() as session:
            try:
                return (
                    session.query(AnimeMetadata)
                    .filter(AnimeMetadata.title.ilike(f"%{title}%"))
                    .limit(limit)
                    .all()
                )
            except Exception as e:
                logger.error(f"Failed to search anime metadata: {e}")
                return []

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
        """Create a new parsed file record."""
        with self.get_session() as session:
            try:
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
                    existing.processing_errors = ParsedFile._serialize_json_field(
                        parsed_info.raw_data
                    )
                    existing.db_updated_at = datetime.utcnow()

                    session.commit()
                    return existing
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
                    session.commit()
                    session.refresh(parsed_file)
                    return parsed_file

            except Exception as e:
                session.rollback()
                logger.error(f"Failed to create parsed file: {e}")
                raise

    def get_parsed_file(self, file_path: str | Path) -> ParsedFile | None:
        """Get parsed file by file path."""
        with self.get_session() as session:
            try:
                return session.query(ParsedFile).filter_by(file_path=str(file_path)).first()
            except Exception as e:
                logger.error(f"Failed to get parsed file: {e}")
                return None

    def get_parsed_files_by_metadata(self, metadata_id: int) -> list[ParsedFile]:
        """Get all parsed files for a specific metadata record."""
        with self.get_session() as session:
            try:
                return session.query(ParsedFile).filter_by(metadata_id=metadata_id).all()
            except Exception as e:
                logger.error(f"Failed to get parsed files by metadata: {e}")
                return []

    def delete_parsed_file(self, file_path: str | Path) -> bool:
        """Delete a parsed file record."""
        with self.get_session() as session:
            try:
                parsed_file = session.query(ParsedFile).filter_by(file_path=str(file_path)).first()
                if parsed_file:
                    session.delete(parsed_file)
                    session.commit()
                    return True
                return False
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to delete parsed file: {e}")
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
                logger.error(f"Failed to get database stats: {e}")
                return {}


# Global database manager instance
db_manager = DatabaseManager()
