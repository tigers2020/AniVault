"""
Core data models for AniVault application.

This module defines the fundamental data structures used throughout the application
for representing anime files, file groups, parsed information, and TMDB metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from PyQt5.QtCore import QObject, pyqtSignal


@dataclass
class AnimeFile:
    """
    Represents a single anime file with its metadata and properties.

    Attributes:
        file_path: Absolute path to the file
        filename: Just the filename without path
        file_size: Size of the file in bytes
        file_extension: File extension (e.g., '.mkv', '.mp4')
        created_at: File creation timestamp
        modified_at: File modification timestamp
        parsed_info: Parsed anime information from filename
        tmdb_info: TMDB metadata information
        is_processed: Whether the file has been processed
        processing_errors: List of errors encountered during processing
    """

    file_path: Path
    filename: str
    file_size: int
    file_extension: str
    created_at: datetime
    modified_at: datetime
    parsed_info: Optional[ParsedAnimeInfo] = None
    tmdb_info: Optional[TMDBAnime] = None
    is_processed: bool = False
    processing_errors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize derived fields after dataclass creation."""
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)

    def __hash__(self) -> int:
        """Make AnimeFile hashable for use in sets."""
        return hash(self.file_path)

    def __eq__(self, other: object) -> bool:
        """Check equality based on file path."""
        if not isinstance(other, AnimeFile):
            return False
        return self.file_path == other.file_path

        # Ensure filename is just the basename
        if not self.filename:
            self.filename = self.file_path.name

    @property
    def file_size_mb(self) -> float:
        """Return file size in megabytes."""
        return self.file_size / (1024 * 1024)

    @property
    def exists(self) -> bool:
        """Check if the file still exists on disk."""
        return self.file_path.exists()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file_path": str(self.file_path),
            "filename": self.filename,
            "file_size": self.file_size,
            "file_extension": self.file_extension,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "parsed_info": self.parsed_info.to_dict() if self.parsed_info else None,
            "tmdb_info": self.tmdb_info.to_dict() if self.tmdb_info else None,
            "is_processed": self.is_processed,
            "processing_errors": self.processing_errors,
        }


@dataclass
class FileGroup:
    """
    Represents a group of similar anime files that belong to the same series.

    Attributes:
        group_id: Unique identifier for the group
        files: List of AnimeFile objects in this group
        similarity_score: Average similarity score between files
        best_file: The highest quality file in the group
        series_title: Parsed series title from files
        season: Season number if available
        episode_range: Range of episodes in this group
        created_at: When the group was created
        is_processed: Whether the group has been processed
    """

    group_id: str
    files: list[AnimeFile] = field(default_factory=list)
    similarity_score: float = 0.0
    best_file: Optional[AnimeFile] = None
    series_title: str = ""
    season: Optional[int] = None
    episode_range: Optional[tuple[int, int]] = None
    created_at: datetime = field(default_factory=datetime.now)
    is_processed: bool = False
    tmdb_info: Optional["TMDBAnime"] = None

    def add_file(self, file: AnimeFile) -> None:
        """Add a file to this group."""
        self.files.append(file)
        self._update_best_file()
        self._update_metadata()

    def remove_file(self, file: AnimeFile) -> bool:
        """Remove a file from this group. Returns True if removed."""
        if file in self.files:
            self.files.remove(file)
            self._update_best_file()
            self._update_metadata()
            return True
        return False

    def _update_best_file(self) -> None:
        """Update the best file based on resolution and quality."""
        if not self.files:
            self.best_file = None
            return

        # Sort by resolution (height), then by file size
        sorted_files = sorted(
            self.files,
            key=lambda f: (f.parsed_info.resolution_height if f.parsed_info else 0, f.file_size),
            reverse=True,
        )
        self.best_file = sorted_files[0]

    def _update_metadata(self) -> None:
        """Update group metadata from files."""
        if not self.files:
            return

        # Use the best file's parsed info for group metadata
        if self.best_file and self.best_file.parsed_info:
            self.series_title = self.best_file.parsed_info.title
            self.season = self.best_file.parsed_info.season

    @property
    def file_count(self) -> int:
        """Return the number of files in this group."""
        return len(self.files)

    @property
    def total_size(self) -> int:
        """Return total size of all files in the group."""
        return sum(file.file_size for file in self.files)

    @property
    def total_size_mb(self) -> float:
        """Return total size in megabytes."""
        return self.total_size / (1024 * 1024)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "group_id": self.group_id,
            "files": [file.to_dict() for file in self.files],
            "similarity_score": self.similarity_score,
            "best_file": self.best_file.to_dict() if self.best_file else None,
            "series_title": self.series_title,
            "season": self.season,
            "episode_range": self.episode_range,
            "created_at": self.created_at.isoformat(),
            "is_processed": self.is_processed,
        }


@dataclass
class ParsedAnimeInfo:
    """
    Represents parsed information from an anime filename using anitopy.

    Attributes:
        title: Anime series title
        season: Season number (1-based)
        episode: Episode number (1-based)
        episode_title: Episode title if available
        resolution: Video resolution (e.g., '1080p', '720p')
        resolution_width: Video width in pixels
        resolution_height: Video height in pixels
        video_codec: Video codec (e.g., 'H264', 'H265')
        audio_codec: Audio codec (e.g., 'AAC', 'FLAC')
        release_group: Release group name
        file_extension: File extension
        year: Release year
        source: Source type (e.g., 'Blu-ray', 'Web')
        raw_data: Raw parsed data from anitopy
    """

    title: str
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None
    resolution: Optional[str] = None
    resolution_width: Optional[int] = None
    resolution_height: Optional[int] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    release_group: Optional[str] = None
    file_extension: Optional[str] = None
    year: Optional[int] = None
    source: Optional[str] = None
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def is_movie(self) -> bool:
        """Check if this is a movie (no season/episode info)."""
        return self.season is None and self.episode is None

    @property
    def is_tv_series(self) -> bool:
        """Check if this is a TV series (has season/episode info)."""
        return self.season is not None or self.episode is not None

    @property
    def display_title(self) -> str:
        """Return a display-friendly title."""
        if self.is_tv_series and self.season and self.episode:
            return f"{self.title} S{self.season:02d}E{self.episode:02d}"
        elif self.is_tv_series and self.season:
            return f"{self.title} Season {self.season}"
        else:
            return self.title

    def is_valid(self) -> bool:
        """Check if the parsed info contains valid data."""
        return bool(self.title and self.title.strip())

    def has_episode_info(self) -> bool:
        """Check if episode information is available."""
        return self.episode is not None

    def has_season_info(self) -> bool:
        """Check if season information is available."""
        return self.season is not None

    def has_resolution_info(self) -> bool:
        """Check if resolution information is available."""
        return (
            self.resolution is not None
            and self.resolution_width is not None
            and self.resolution_height is not None
        )

    def get_quality_score(self) -> int:
        """Calculate a quality score based on available information."""
        score = 0

        # Base score for having a title
        if self.title:
            score += 10

        # Episode/season information
        if self.has_episode_info():
            score += 5
        if self.has_season_info():
            score += 5

        # Resolution information
        if self.has_resolution_info():
            score += 10
            # Higher resolution = higher score
            if self.resolution_height:
                if self.resolution_height >= 2160:  # 4K
                    score += 10
                elif self.resolution_height >= 1440:  # QHD
                    score += 8
                elif self.resolution_height >= 1080:  # Full HD
                    score += 6
                elif self.resolution_height >= 720:  # HD
                    score += 4
                else:
                    score += 2

        # Additional metadata
        if self.video_codec:
            score += 3
        if self.audio_codec:
            score += 3
        if self.release_group:
            score += 2
        if self.year:
            score += 2

        return score

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "season": self.season,
            "episode": self.episode,
            "episode_title": self.episode_title,
            "resolution": self.resolution,
            "resolution_width": self.resolution_width,
            "resolution_height": self.resolution_height,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "release_group": self.release_group,
            "file_extension": self.file_extension,
            "year": self.year,
            "source": self.source,
            "raw_data": self.raw_data,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParsedAnimeInfo:
        """Create ParsedAnimeInfo from dictionary."""
        return cls(
            title=data.get("title", ""),
            season=data.get("season"),
            episode=data.get("episode"),
            episode_title=data.get("episode_title"),
            resolution=data.get("resolution"),
            resolution_width=data.get("resolution_width"),
            resolution_height=data.get("resolution_height"),
            video_codec=data.get("video_codec"),
            audio_codec=data.get("audio_codec"),
            release_group=data.get("release_group"),
            file_extension=data.get("file_extension"),
            year=data.get("year"),
            source=data.get("source"),
            raw_data=data.get("raw_data", {}),
        )


@dataclass
class TMDBAnime:
    """
    Represents metadata retrieved from TMDB API for an anime series.

    Attributes:
        tmdb_id: TMDB series ID
        title: Primary title
        original_title: Original title
        korean_title: Korean title if available
        overview: Series description
        poster_path: Path to poster image
        backdrop_path: Path to backdrop image
        first_air_date: First air date
        last_air_date: Last air date
        status: Series status (e.g., 'Ended', 'Ongoing')
        vote_average: Average rating
        vote_count: Number of votes
        popularity: Popularity score
        genres: List of genre names
        networks: List of network names
        number_of_seasons: Total number of seasons
        number_of_episodes: Total number of episodes
        raw_data: Raw data from TMDB API
    """

    tmdb_id: int
    title: str
    original_title: str = ""
    korean_title: str = ""
    overview: str = ""
    poster_path: str = ""
    backdrop_path: str = ""
    first_air_date: Optional[datetime] = None
    last_air_date: Optional[datetime] = None
    status: str = ""
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    genres: list[str] = field(default_factory=list)
    networks: list[str] = field(default_factory=list)
    number_of_seasons: int = 0
    number_of_episodes: int = 0
    raw_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TMDBAnime":
        """
        Create TMDBAnime instance from TMDB API response data.
        
        Args:
            data: Raw data from TMDB API
            
        Returns:
            TMDBAnime instance
        """
        # Parse first air date
        first_air_date = None
        if data.get("first_air_date"):
            try:
                from datetime import datetime
                first_air_date = datetime.strptime(data["first_air_date"], "%Y-%m-%d")
            except ValueError:
                pass
        
        # Parse last air date
        last_air_date = None
        if data.get("last_air_date"):
            try:
                from datetime import datetime
                last_air_date = datetime.strptime(data["last_air_date"], "%Y-%m-%d")
            except ValueError:
                pass
        
        # Extract genres
        genres = []
        if data.get("genres"):
            genres = [genre.get("name", "") for genre in data["genres"]]
        
        # Extract networks
        networks = []
        if data.get("networks"):
            networks = [network.get("name", "") for network in data["networks"]]
        
        return cls(
            tmdb_id=data.get("id", 0),
            title=data.get("name", ""),
            original_title=data.get("original_name", ""),
            korean_title=data.get("korean_title", ""),  # This might not exist in TMDB response
            overview=data.get("overview", ""),
            poster_path=data.get("poster_path", ""),
            backdrop_path=data.get("backdrop_path", ""),
            first_air_date=first_air_date,
            last_air_date=last_air_date,
            status=data.get("status", ""),
            vote_average=data.get("vote_average", 0.0),
            vote_count=data.get("vote_count", 0),
            popularity=data.get("popularity", 0.0),
            genres=genres,
            networks=networks,
            number_of_seasons=data.get("number_of_seasons", 0),
            number_of_episodes=data.get("number_of_episodes", 0),
            raw_data=data,
        )

    @property
    def display_title(self) -> str:
        """Return the best available title for display."""
        if self.korean_title:
            return self.korean_title
        elif self.title:
            return self.title
        else:
            return self.original_title

    @property
    def poster_url(self) -> str:
        """Return full URL for poster image."""
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w500{self.poster_path}"
        return ""

    @property
    def backdrop_url(self) -> str:
        """Return full URL for backdrop image."""
        if self.backdrop_path:
            return f"https://image.tmdb.org/t/p/w1280{self.backdrop_path}"
        return ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tmdb_id": self.tmdb_id,
            "title": self.title,
            "original_title": self.original_title,
            "korean_title": self.korean_title,
            "overview": self.overview,
            "poster_path": self.poster_path,
            "backdrop_path": self.backdrop_path,
            "first_air_date": self.first_air_date.isoformat() if self.first_air_date else None,
            "last_air_date": self.last_air_date.isoformat() if self.last_air_date else None,
            "status": self.status,
            "vote_average": self.vote_average,
            "vote_count": self.vote_count,
            "popularity": self.popularity,
            "genres": self.genres,
            "networks": self.networks,
            "number_of_seasons": self.number_of_seasons,
            "number_of_episodes": self.number_of_episodes,
            "raw_data": self.raw_data,
        }


class ProcessingState(QObject):
    """
    Observable state object for tracking processing progress and status.

    This class provides signals for UI updates and maintains the current
    processing state of the application.
    """

    # Signals for UI updates
    progress_updated = pyqtSignal(int)  # progress percentage (0-100)
    status_message_updated = pyqtSignal(str)  # current status message
    file_processed = pyqtSignal(AnimeFile)  # when a file is processed
    group_processed = pyqtSignal(FileGroup)  # when a group is processed
    error_occurred = pyqtSignal(str)  # when an error occurs
    processing_finished = pyqtSignal()  # when processing is complete

    def __init__(self) -> None:
        super().__init__()
        self._progress: int = 0
        self._status_message: str = "Ready"
        self._is_processing: bool = False
        self._total_files: int = 0
        self._processed_files: int = 0
        self._errors: list[str] = []

    @property
    def progress(self) -> int:
        """Current progress percentage (0-100)."""
        return self._progress

    @progress.setter
    def progress(self, value: int) -> None:
        """Set progress and emit signal."""
        self._progress = max(0, min(100, value))
        self.progress_updated.emit(self._progress)

    @property
    def status_message(self) -> str:
        """Current status message."""
        return self._status_message

    @status_message.setter
    def status_message(self, value: str) -> None:
        """Set status message and emit signal."""
        self._status_message = value
        self.status_message_updated.emit(self._status_message)

    @property
    def is_processing(self) -> bool:
        """Whether processing is currently active."""
        return self._is_processing

    @is_processing.setter
    def is_processing(self, value: bool) -> None:
        """Set processing state."""
        self._is_processing = value
        if not value:
            self.processing_finished.emit()

    @property
    def total_files(self) -> int:
        """Total number of files to process."""
        return self._total_files

    @total_files.setter
    def total_files(self, value: int) -> None:
        """Set total files and reset progress."""
        self._total_files = value
        self._processed_files = 0
        self.progress = 0

    @property
    def processed_files(self) -> int:
        """Number of files processed so far."""
        return self._processed_files

    def increment_processed_files(self) -> None:
        """Increment processed files and update progress."""
        self._processed_files += 1
        if self._total_files > 0:
            self.progress = int((self._processed_files / self._total_files) * 100)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self._errors.append(error)
        self.error_occurred.emit(error)

    def clear_errors(self) -> None:
        """Clear all error messages."""
        self._errors.clear()

    @property
    def errors(self) -> list[str]:
        """List of all error messages."""
        return self._errors.copy()

    def reset(self) -> None:
        """Reset all state to initial values."""
        self._progress = 0
        self._status_message = "Ready"
        self._is_processing = False
        self._total_files = 0
        self._processed_files = 0
        self._errors.clear()
        self.progress_updated.emit(0)
        self.status_message_updated.emit("Ready")
