"""Unit tests for database versioning functionality."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.database import AnimeMetadata, ParsedFile, Base


class TestDatabaseVersioning:
    """Test database versioning functionality."""

    @pytest.fixture
    def db_session(self):
        """Create a test database session."""
        # Create in-memory SQLite database for testing
        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        session = Session()

        yield session

        session.close()

    def test_anime_metadata_version_initialization(self, db_session):
        """Test that AnimeMetadata version is initialized to 1."""
        anime = AnimeMetadata(
            tmdb_id=12345,
            title="Test Anime",
            overview="Test overview"
        )

        db_session.add(anime)
        db_session.commit()

        # Check that version is initialized to 1
        assert anime.version == 1

    def test_anime_metadata_version_increment_on_update(self, db_session):
        """Test that AnimeMetadata version increments on update."""
        anime = AnimeMetadata(
            tmdb_id=12345,
            title="Test Anime",
            overview="Test overview"
        )

        db_session.add(anime)
        db_session.commit()

        initial_version = anime.version
        assert initial_version == 1

        # Update the anime
        anime.title = "Updated Test Anime"
        db_session.commit()

        # Check that version incremented
        assert anime.version == initial_version + 1

    def test_anime_metadata_version_multiple_updates(self, db_session):
        """Test that AnimeMetadata version increments on multiple updates."""
        anime = AnimeMetadata(
            tmdb_id=12345,
            title="Test Anime",
            overview="Test overview"
        )

        db_session.add(anime)
        db_session.commit()

        # Perform multiple updates
        for i in range(5):
            anime.title = f"Updated Test Anime {i}"
            db_session.commit()

        # Check that version incremented for each update
        assert anime.version == 6  # 1 initial + 5 updates

    def test_parsed_file_version_initialization(self, db_session):
        """Test that ParsedFile version is initialized to 1."""
        parsed_file = ParsedFile(
            file_path="/test/path/test.mkv",
            filename="test.mkv",
            file_size=1024,
            parsed_title="Test Anime"
        )

        db_session.add(parsed_file)
        db_session.commit()

        # Check that version is initialized to 1
        assert parsed_file.version == 1

    def test_parsed_file_version_increment_on_update(self, db_session):
        """Test that ParsedFile version increments on update."""
        parsed_file = ParsedFile(
            file_path="/test/path/test.mkv",
            filename="test.mkv",
            file_size=1024,
            parsed_title="Test Anime"
        )

        db_session.add(parsed_file)
        db_session.commit()

        initial_version = parsed_file.version
        assert initial_version == 1

        # Update the parsed file
        parsed_file.parsed_title = "Updated Test Anime"
        db_session.commit()

        # Check that version incremented
        assert parsed_file.version == initial_version + 1

    def test_parsed_file_version_multiple_updates(self, db_session):
        """Test that ParsedFile version increments on multiple updates."""
        parsed_file = ParsedFile(
            file_path="/test/path/test.mkv",
            filename="test.mkv",
            file_size=1024,
            parsed_title="Test Anime"
        )

        db_session.add(parsed_file)
        db_session.commit()

        # Perform multiple updates
        for i in range(3):
            parsed_file.parsed_title = f"Updated Test Anime {i}"
            db_session.commit()

        # Check that version incremented for each update
        assert parsed_file.version == 4  # 1 initial + 3 updates

    def test_version_preserves_other_fields(self, db_session):
        """Test that versioning doesn't affect other field updates."""
        anime = AnimeMetadata(
            tmdb_id=12345,
            title="Test Anime",
            overview="Test overview",
            vote_average=8.5
        )

        db_session.add(anime)
        db_session.commit()

        initial_version = anime.version

        # Update multiple fields
        anime.title = "Updated Title"
        anime.overview = "Updated overview"
        anime.vote_average = 9.0

        db_session.commit()

        # Check that version incremented
        assert anime.version == initial_version + 1

        # Check that other fields were updated
        assert anime.title == "Updated Title"
        assert anime.overview == "Updated overview"
        assert anime.vote_average == 9.0

    def test_version_with_transaction_rollback(self, db_session):
        """Test that version doesn't increment on rollback."""
        anime = AnimeMetadata(
            tmdb_id=12345,
            title="Test Anime",
            overview="Test overview"
        )

        db_session.add(anime)
        db_session.commit()

        initial_version = anime.version

        # Start a transaction and update
        anime.title = "Updated Title"

        # Rollback the transaction
        db_session.rollback()

        # Check that version didn't increment
        assert anime.version == initial_version
        assert anime.title == "Test Anime"  # Should be reverted

    def test_version_with_bulk_operations(self, db_session):
        """Test that version increments work with bulk operations."""
        # Create multiple anime records
        anime_list = []
        for i in range(3):
            anime = AnimeMetadata(
                tmdb_id=12345 + i,
                title=f"Test Anime {i}",
                overview=f"Test overview {i}"
            )
            anime_list.append(anime)
            db_session.add(anime)

        db_session.commit()

        # Check initial versions
        for anime in anime_list:
            assert anime.version == 1

        # Update all anime records
        for anime in anime_list:
            anime.title = f"Updated Test Anime {anime.tmdb_id}"

        db_session.commit()

        # Check that all versions incremented
        for anime in anime_list:
            assert anime.version == 2

    def test_version_with_relationship_updates(self, db_session):
        """Test that version increments work with relationship updates."""
        # Create anime metadata
        anime = AnimeMetadata(
            tmdb_id=12345,
            title="Test Anime",
            overview="Test overview"
        )
        db_session.add(anime)
        db_session.commit()

        # Create parsed file with relationship
        parsed_file = ParsedFile(
            file_path="/test/path/test.mkv",
            filename="test.mkv",
            file_size=1024,
            parsed_title="Test Anime",
            metadata_id=anime.tmdb_id
        )
        db_session.add(parsed_file)
        db_session.commit()

        initial_anime_version = anime.version
        initial_file_version = parsed_file.version

        # Update through relationship
        anime.title = "Updated Test Anime"
        parsed_file.parsed_title = "Updated Test Anime"

        db_session.commit()

        # Check that both versions incremented
        assert anime.version == initial_anime_version + 1
        assert parsed_file.version == initial_file_version + 1
