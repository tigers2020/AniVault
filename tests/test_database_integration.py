"""Simplified database integration tests."""

import os
import tempfile
from datetime import datetime

import pytest
from sqlalchemy import text

from src.core.database import AnimeMetadata, DatabaseManager
from src.core.models import ParsedAnimeInfo, TMDBAnime


class TestDatabaseIntegration:
    """Simplified integration tests for SQLite database functionality."""

    @pytest.fixture
    def temp_db_path(self) -> str:
        """Create a temporary database file for testing."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_file.close()
        yield temp_file.name
        # Clean up
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)

    @pytest.fixture
    def db_manager(self, temp_db_path: str) -> DatabaseManager:
        """Create DatabaseManager instance for testing."""
        manager = DatabaseManager(database_url=f"sqlite:///{temp_db_path}")
        yield manager
        # Clean up database connections
        manager.close()

    def test_database_creation_and_schema(self, db_manager: DatabaseManager) -> None:
        """Test database creation and schema validation."""
        # Database should be created successfully
        db_path = db_manager.database_url.replace("sqlite:///", "")
        assert os.path.exists(db_path)

        # Test schema by initializing database
        db_manager.initialize()

        # Verify tables exist by querying them
        with db_manager.get_session() as session:
            # Check if anime_metadata table exists
            result = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='anime_metadata'")
            )
            assert result.fetchone() is not None

            # Check if parsed_files table exists
            result = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='parsed_files'")
            )
            assert result.fetchone() is not None

    def test_anime_metadata_crud_operations(self, db_manager: DatabaseManager) -> None:
        """Test CRUD operations for AnimeMetadata."""
        db_manager.initialize()

        # Create test TMDB anime
        test_tmdb_anime = TMDBAnime(
            tmdb_id=12345,
            title="Test Anime",
            overview="A test anime series",
            first_air_date=datetime(2020, 1, 1),
            vote_average=8.5,
            vote_count=1000,
            popularity=50.0,
            poster_path="/poster.jpg",
            backdrop_path="/backdrop.jpg",
            genres=["Animation", "Action"],
            original_title="テストアニメ",
        )

        # Test Create
        created_metadata = db_manager.create_anime_metadata(test_tmdb_anime)
        assert created_metadata.tmdb_id is not None
        assert created_metadata.tmdb_id == test_tmdb_anime.tmdb_id
        assert created_metadata.title == test_tmdb_anime.title

        # Test Read
        retrieved_metadata = db_manager.get_anime_metadata(test_tmdb_anime.tmdb_id)
        assert retrieved_metadata is not None
        assert retrieved_metadata.title == test_tmdb_anime.title
        assert retrieved_metadata.vote_average == test_tmdb_anime.vote_average

        # Test Search
        search_results = db_manager.search_anime_metadata("Test Anime")
        assert len(search_results) > 0
        assert search_results[0].title == test_tmdb_anime.title

        # Test Delete
        success = db_manager.delete_anime_metadata(test_tmdb_anime.tmdb_id)
        assert success is True
        deleted_metadata = db_manager.get_anime_metadata(test_tmdb_anime.tmdb_id)
        assert deleted_metadata is None

    def test_parsed_file_crud_operations(self, db_manager: DatabaseManager) -> None:
        """Test CRUD operations for ParsedFile."""
        db_manager.initialize()

        # Create test parsed anime info
        test_parsed_info = ParsedAnimeInfo(
            title="Test Anime",
            season=1,
            episode=1,
            episode_title="Test Episode",
            resolution="1080p",
            release_group="TestGroup",
            file_extension="mkv",
        )

        # Test Create
        created_file = db_manager.create_parsed_file(
            file_path="/test/path/anime.mkv",
            filename="anime.mkv",
            file_size=1024000,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            parsed_info=test_parsed_info,
            file_hash="test_hash_123",
        )
        assert created_file.id is not None
        assert created_file.file_path == "/test/path/anime.mkv"
        assert created_file.parsed_title == test_parsed_info.title

        # Test Read
        retrieved_file = db_manager.get_parsed_file("/test/path/anime.mkv")
        assert retrieved_file is not None
        assert retrieved_file.parsed_title == test_parsed_info.title

        # Test Delete
        success = db_manager.delete_parsed_file("/test/path/anime.mkv")
        assert success is True
        deleted_file = db_manager.get_parsed_file("/test/path/anime.mkv")
        assert deleted_file is None

    def test_database_transactions(self, db_manager: DatabaseManager) -> None:
        """Test database transaction handling."""
        db_manager.initialize()

        # Test successful transaction
        with db_manager.transaction() as session:
            metadata = AnimeMetadata(
                tmdb_id=12345,
                title="Test Anime",
                overview="A test anime",
                first_air_date=datetime(2020, 1, 1),
                vote_average=8.5,
                vote_count=1000,
                popularity=50.0,
                poster_path="/poster.jpg",
                backdrop_path="/backdrop.jpg",
                genres='["Animation", "Action"]',
                original_title="テストアニメ",
            )
            session.add(metadata)
            session.flush()
            assert metadata.tmdb_id is not None

        # Verify data was committed
        retrieved = db_manager.get_anime_metadata(12345)
        assert retrieved is not None
        assert retrieved.title == "Test Anime"

    def test_database_error_handling(self, db_manager: DatabaseManager) -> None:
        """Test database error handling."""
        db_manager.initialize()

        # Test with invalid data
        try:
            # This should fail gracefully
            invalid_metadata = AnimeMetadata(
                tmdb_id=None,  # Invalid ID
                title="",  # Empty title
                overview="",
                release_date=None,
                vote_average=None,
                vote_count=None,
                popularity=None,
                poster_path="",
                backdrop_path="",
                genre_ids=[],
                original_language="",
                original_title="",
            )
            with db_manager.transaction() as session:
                session.add(invalid_metadata)
                session.flush()
        except Exception as e:
            # Expected to fail with invalid data
            assert (
                "invalid" in str(e).lower()
                or "constraint" in str(e).lower()
                or "not null" in str(e).lower()
            )

    def test_database_stats(self, db_manager: DatabaseManager) -> None:
        """Test database statistics."""
        db_manager.initialize()

        # Get initial stats
        stats = db_manager.get_database_stats()
        assert isinstance(stats, dict)
        assert "anime_metadata_count" in stats
        assert "parsed_files_count" in stats
        assert stats["anime_metadata_count"] >= 0
        assert stats["parsed_files_count"] >= 0
