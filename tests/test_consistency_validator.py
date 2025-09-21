"""Unit tests for consistency validator and conflict detection logic."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from src.core.consistency_validator import (
    ConflictSeverity,
    ConflictType,
    ConsistencyValidator,
    DataConflict,
)
from src.core.database import AnimeMetadata, ParsedFile
from src.core.metadata_cache import MetadataCache


class TestConsistencyValidator:
    """Test consistency validator functionality."""

    @pytest.fixture
    def mock_metadata_cache(self):
        """Create a mock metadata cache."""
        cache = Mock(spec=MetadataCache)
        cache.get.return_value = None
        return cache

    @pytest.fixture
    def validator(self, mock_metadata_cache):
        """Create a consistency validator with mock cache."""
        return ConsistencyValidator(metadata_cache=mock_metadata_cache)

    def test_data_conflict_creation(self) -> None:
        """Test DataConflict object creation."""
        conflict = DataConflict(
            conflict_type=ConflictType.VERSION_MISMATCH,
            entity_type="anime_metadata",
            entity_id=12345,
            cache_data={"version": 1},
            db_data={"version": 2},
            severity=ConflictSeverity.HIGH,
            details="Version mismatch detected",
        )

        assert conflict.conflict_type == ConflictType.VERSION_MISMATCH
        assert conflict.entity_type == "anime_metadata"
        assert conflict.entity_id == 12345
        assert conflict.cache_data == {"version": 1}
        assert conflict.db_data == {"version": 2}
        assert conflict.severity == ConflictSeverity.HIGH
        assert conflict.details == "Version mismatch detected"
        assert isinstance(conflict.detected_at, datetime)

    def test_anime_metadata_missing_in_cache(self, validator, mock_metadata_cache) -> None:
        """Test detection of anime metadata missing in cache."""
        # Mock database session and query
        mock_session = Mock()
        mock_anime = Mock(spec=AnimeMetadata)
        mock_anime.tmdb_id = 12345
        mock_anime.version = 1
        mock_anime.updated_at = datetime.now(timezone.utc)
        mock_anime.title = "Test Anime"
        mock_anime.overview = "Test overview"
        mock_anime.status = "Released"
        mock_anime.vote_average = 8.5

        mock_session.query.return_value.all.return_value = [mock_anime]

        # Mock cache to return None (missing data)
        mock_metadata_cache.get.return_value = None

        with patch.object(validator.db_manager, "transaction") as mock_transaction:
            mock_transaction.return_value.__enter__.return_value = mock_session
            mock_transaction.return_value.__exit__.return_value = None

            conflicts = validator.validate_anime_metadata_consistency()

        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict.conflict_type == ConflictType.MISSING_IN_CACHE
        assert conflict.entity_type == "anime_metadata"
        assert conflict.entity_id == 12345
        assert conflict.severity == ConflictSeverity.MEDIUM

    def test_anime_metadata_version_mismatch(self, validator, mock_metadata_cache) -> None:
        """Test detection of version mismatch in anime metadata."""
        # Mock database session and query
        mock_session = Mock()
        mock_anime = Mock(spec=AnimeMetadata)
        mock_anime.tmdb_id = 12345
        mock_anime.version = 3
        mock_anime.updated_at = datetime.now(timezone.utc)
        mock_anime.title = "Test Anime"
        mock_anime.overview = "Test overview"
        mock_anime.status = "Released"
        mock_anime.vote_average = 8.5

        mock_session.query.return_value.all.return_value = [mock_anime]

        # Mock cache to return data with different version but same timestamp
        same_time = datetime.now(timezone.utc)
        cache_data = {
            "version": 1,
            "title": "Test Anime",
            "overview": "Test overview",
            "status": "Released",
            "vote_average": 8.5,
            "updated_at": same_time.isoformat(),
        }
        mock_metadata_cache.get.return_value = cache_data

        with patch.object(validator.db_manager, "transaction") as mock_transaction:
            mock_transaction.return_value.__enter__.return_value = mock_session
            mock_transaction.return_value.__exit__.return_value = None

            conflicts = validator.validate_anime_metadata_consistency()

        # Should have version mismatch conflict
        version_conflicts = [
            c for c in conflicts if c.conflict_type == ConflictType.VERSION_MISMATCH
        ]
        assert len(version_conflicts) == 1
        conflict = version_conflicts[0]
        assert conflict.entity_type == "anime_metadata"
        assert conflict.entity_id == 12345
        assert conflict.severity == ConflictSeverity.HIGH  # Version difference > 1

    def test_anime_metadata_data_mismatch(self, validator, mock_metadata_cache) -> None:
        """Test detection of data mismatch in anime metadata."""
        # Mock database session and query
        mock_session = Mock()
        mock_anime = Mock(spec=AnimeMetadata)
        mock_anime.tmdb_id = 12345
        mock_anime.version = 1
        mock_anime.updated_at = datetime.now(timezone.utc)
        mock_anime.title = "Test Anime"
        mock_anime.overview = "Test overview"
        mock_anime.status = "Released"
        mock_anime.vote_average = 8.5

        mock_session.query.return_value.all.return_value = [mock_anime]

        # Mock cache to return data with different title but same timestamp
        same_time = datetime.now(timezone.utc)
        cache_data = {
            "version": 1,
            "title": "Different Title",  # Different from DB
            "overview": "Test overview",
            "status": "Released",
            "vote_average": 8.5,
            "updated_at": same_time.isoformat(),
        }
        mock_metadata_cache.get.return_value = cache_data

        with patch.object(validator.db_manager, "transaction") as mock_transaction:
            mock_transaction.return_value.__enter__.return_value = mock_session
            mock_transaction.return_value.__exit__.return_value = None

            conflicts = validator.validate_anime_metadata_consistency()

        # Should have data mismatch conflict
        data_conflicts = [c for c in conflicts if c.conflict_type == ConflictType.DATA_MISMATCH]
        assert len(data_conflicts) == 1
        conflict = data_conflicts[0]
        assert conflict.entity_type == "anime_metadata"
        assert conflict.entity_id == 12345
        assert conflict.severity == ConflictSeverity.MEDIUM

    def test_parsed_file_missing_in_cache(self, validator, mock_metadata_cache) -> None:
        """Test detection of parsed file missing in cache."""
        # Mock database session and query
        mock_session = Mock()
        mock_file = Mock(spec=ParsedFile)
        mock_file.id = 1
        mock_file.version = 1
        mock_file.db_updated_at = datetime.now(timezone.utc)
        mock_file.parsed_title = "Test Anime"
        mock_file.season = 1
        mock_file.episode = 1
        mock_file.file_path = "/test/path/test.mkv"

        mock_session.query.return_value.all.return_value = [mock_file]

        # Mock cache to return None (missing data)
        mock_metadata_cache.get.return_value = None

        with patch.object(validator.db_manager, "transaction") as mock_transaction:
            mock_transaction.return_value.__enter__.return_value = mock_session
            mock_transaction.return_value.__exit__.return_value = None

            conflicts = validator.validate_parsed_files_consistency()

        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict.conflict_type == ConflictType.MISSING_IN_CACHE
        assert conflict.entity_type == "parsed_file"
        assert conflict.entity_id == 1
        assert conflict.severity == ConflictSeverity.MEDIUM

    def test_parsed_file_version_mismatch(self, validator, mock_metadata_cache) -> None:
        """Test detection of version mismatch in parsed file."""
        # Mock database session and query
        mock_session = Mock()
        mock_file = Mock(spec=ParsedFile)
        mock_file.id = 1
        mock_file.version = 2
        mock_file.db_updated_at = datetime.now(timezone.utc)
        mock_file.parsed_title = "Test Anime"
        mock_file.season = 1
        mock_file.episode = 1
        mock_file.file_path = "/test/path/test.mkv"

        mock_session.query.return_value.all.return_value = [mock_file]

        # Mock cache to return data with different version but same timestamp
        same_time = datetime.now(timezone.utc)
        cache_data = {
            "version": 1,
            "parsed_title": "Test Anime",
            "season": 1,
            "episode": 1,
            "file_path": "/test/path/test.mkv",
            "db_updated_at": same_time.isoformat(),
        }
        mock_metadata_cache.get.return_value = cache_data

        with patch.object(validator.db_manager, "transaction") as mock_transaction:
            mock_transaction.return_value.__enter__.return_value = mock_session
            mock_transaction.return_value.__exit__.return_value = None

            conflicts = validator.validate_parsed_files_consistency()

        # Should have version mismatch conflict
        version_conflicts = [
            c for c in conflicts if c.conflict_type == ConflictType.VERSION_MISMATCH
        ]
        assert len(version_conflicts) == 1
        conflict = version_conflicts[0]
        assert conflict.entity_type == "parsed_file"
        assert conflict.entity_id == 1
        assert conflict.severity == ConflictSeverity.MEDIUM  # Version difference = 1

    def test_validation_error_handling(self, validator, mock_metadata_cache) -> None:
        """Test handling of validation errors."""
        # Mock database session to raise an exception
        with patch.object(validator.db_manager, "transaction") as mock_transaction:
            mock_transaction.side_effect = Exception("Database connection failed")

            conflicts = validator.validate_anime_metadata_consistency()

        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict.conflict_type == ConflictType.DATA_MISMATCH
        assert conflict.entity_type == "validation_error"
        assert conflict.severity == ConflictSeverity.CRITICAL
        assert "Database connection failed" in conflict.details

    def test_anime_metadata_to_dict(self, validator) -> None:
        """Test conversion of AnimeMetadata to dictionary."""
        # Create a mock AnimeMetadata object
        mock_anime = Mock(spec=AnimeMetadata)
        mock_anime.tmdb_id = 12345
        mock_anime.title = "Test Anime"
        mock_anime.original_title = "Test Anime Original"
        mock_anime.korean_title = "테스트 애니메이션"
        mock_anime.overview = "Test overview"
        mock_anime.poster_path = "/poster.jpg"
        mock_anime.backdrop_path = "/backdrop.jpg"
        mock_anime.first_air_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_anime.last_air_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        mock_anime.status = "Released"
        mock_anime.vote_average = 8.5
        mock_anime.vote_count = 1000
        mock_anime.popularity = 75.5
        mock_anime.number_of_seasons = 1
        mock_anime.number_of_episodes = 12
        mock_anime.genres = '["Action", "Adventure"]'
        mock_anime.networks = '["Network1"]'
        mock_anime.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_anime.updated_at = datetime(2023, 6, 1, tzinfo=timezone.utc)
        mock_anime.version = 2

        result = validator._anime_metadata_to_dict(mock_anime)

        assert result["tmdb_id"] == 12345
        assert result["title"] == "Test Anime"
        assert result["original_title"] == "Test Anime Original"
        assert result["korean_title"] == "테스트 애니메이션"
        assert result["overview"] == "Test overview"
        assert result["poster_path"] == "/poster.jpg"
        assert result["backdrop_path"] == "/backdrop.jpg"
        assert result["first_air_date"] == "2023-01-01T00:00:00+00:00"
        assert result["last_air_date"] == "2023-12-31T00:00:00+00:00"
        assert result["status"] == "Released"
        assert result["vote_average"] == 8.5
        assert result["vote_count"] == 1000
        assert result["popularity"] == 75.5
        assert result["number_of_seasons"] == 1
        assert result["number_of_episodes"] == 12
        assert result["genres"] == '["Action", "Adventure"]'
        assert result["networks"] == '["Network1"]'
        assert result["created_at"] == "2023-01-01T00:00:00+00:00"
        assert result["updated_at"] == "2023-06-01T00:00:00+00:00"
        assert result["version"] == 2

    def test_parsed_file_to_dict(self, validator) -> None:
        """Test conversion of ParsedFile to dictionary."""
        # Create a mock ParsedFile object
        mock_file = Mock(spec=ParsedFile)
        mock_file.id = 1
        mock_file.file_path = "/test/path/test.mkv"
        mock_file.filename = "test.mkv"
        mock_file.file_size = 1024000
        mock_file.file_extension = ".mkv"
        mock_file.file_hash = "abc123def456"
        mock_file.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_file.modified_at = datetime(2023, 1, 2, tzinfo=timezone.utc)
        mock_file.parsed_title = "Test Anime"
        mock_file.season = 1
        mock_file.episode = 1
        mock_file.episode_title = "Episode 1"
        mock_file.resolution = "1080p"
        mock_file.resolution_width = 1920
        mock_file.resolution_height = 1080
        mock_file.video_codec = "H.264"
        mock_file.audio_codec = "AAC"
        mock_file.release_group = "Group1"
        mock_file.source = "BluRay"
        mock_file.year = 2023
        mock_file.is_processed = True
        mock_file.processing_errors = '["Error1"]'
        mock_file.metadata_id = 12345
        mock_file.db_created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_file.db_updated_at = datetime(2023, 6, 1, tzinfo=timezone.utc)
        mock_file.version = 2

        result = validator._parsed_file_to_dict(mock_file)

        assert result["id"] == 1
        assert result["file_path"] == "/test/path/test.mkv"
        assert result["filename"] == "test.mkv"
        assert result["file_size"] == 1024000
        assert result["file_extension"] == ".mkv"
        assert result["file_hash"] == "abc123def456"
        assert result["created_at"] == "2023-01-01T00:00:00+00:00"
        assert result["modified_at"] == "2023-01-02T00:00:00+00:00"
        assert result["parsed_title"] == "Test Anime"
        assert result["season"] == 1
        assert result["episode"] == 1
        assert result["episode_title"] == "Episode 1"
        assert result["resolution"] == "1080p"
        assert result["resolution_width"] == 1920
        assert result["resolution_height"] == 1080
        assert result["video_codec"] == "H.264"
        assert result["audio_codec"] == "AAC"
        assert result["release_group"] == "Group1"
        assert result["source"] == "BluRay"
        assert result["year"] == 2023
        assert result["is_processed"] is True
        assert result["processing_errors"] == '["Error1"]'
        assert result["metadata_id"] == 12345
        assert result["db_created_at"] == "2023-01-01T00:00:00+00:00"
        assert result["db_updated_at"] == "2023-06-01T00:00:00+00:00"
        assert result["version"] == 2

    def test_extract_tmdb_id_from_cache_key(self, validator) -> None:
        """Test extraction of TMDB ID from cache key."""
        assert validator._extract_tmdb_id_from_cache_key("anime_metadata:12345") == 12345
        assert validator._extract_tmdb_id_from_cache_key("anime_metadata:999") == 999
        assert validator._extract_tmdb_id_from_cache_key("parsed_file:123") is None
        assert validator._extract_tmdb_id_from_cache_key("invalid_key") is None
        assert validator._extract_tmdb_id_from_cache_key("anime_metadata:invalid") is None

    def test_extract_file_id_from_cache_key(self, validator) -> None:
        """Test extraction of file ID from cache key."""
        assert validator._extract_file_id_from_cache_key("parsed_file:123") == 123
        assert validator._extract_file_id_from_cache_key("parsed_file:999") == 999
        assert validator._extract_file_id_from_cache_key("anime_metadata:12345") is None
        assert validator._extract_file_id_from_cache_key("invalid_key") is None
        assert validator._extract_file_id_from_cache_key("parsed_file:invalid") is None
