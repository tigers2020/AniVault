"""Tests for batch database operations functionality.

This module tests the bulk insert and upsert operations for both
anime metadata and parsed files to ensure performance and data integrity.
"""

from datetime import datetime, timezone

import pytest

from src.core.database import AnimeMetadata, DatabaseManager, ParsedFile
from src.core.models import ParsedAnimeInfo, TMDBAnime


class TestBatchDBOperations:
    """Test cases for batch database operations."""

    @pytest.fixture
    def db_manager(self):
        """Create a test database manager."""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.initialize()
        return manager

    @pytest.fixture
    def sample_tmdb_anime_list(self):
        """Create sample TMDB anime data for testing."""
        return [
            TMDBAnime(
                tmdb_id=1,
                title="Attack on Titan",
                original_title="進撃の巨人",
                korean_title="진격의 거인",
                overview="Humanity fights for survival against Titans.",
                poster_path="/poster1.jpg",
                backdrop_path="/backdrop1.jpg",
                first_air_date=datetime(2013, 4, 7),
                last_air_date=datetime(2023, 11, 5),
                status="Ended",
                vote_average=8.5,
                vote_count=15000,
                popularity=95.5,
                genres=["Action", "Drama", "Fantasy"],
                networks=["NHK"],
                number_of_seasons=4,
                number_of_episodes=75,
                raw_data={"test": "data1"},
            ),
            TMDBAnime(
                tmdb_id=2,
                title="Demon Slayer",
                original_title="鬼滅の刃",
                korean_title="귀멸의 칼날",
                overview="A young boy becomes a demon slayer.",
                poster_path="/poster2.jpg",
                backdrop_path="/backdrop2.jpg",
                first_air_date=datetime(2019, 4, 6),
                last_air_date=datetime(2023, 6, 18),
                status="Ended",
                vote_average=8.7,
                vote_count=20000,
                popularity=98.2,
                genres=["Action", "Supernatural", "Historical"],
                networks=["Fuji TV"],
                number_of_seasons=3,
                number_of_episodes=44,
                raw_data={"test": "data2"},
            ),
            TMDBAnime(
                tmdb_id=3,
                title="One Piece",
                original_title="ワンピース",
                korean_title="원피스",
                overview="A pirate's journey to find the ultimate treasure.",
                poster_path="/poster3.jpg",
                backdrop_path="/backdrop3.jpg",
                first_air_date=datetime(1999, 10, 20),
                last_air_date=None,
                status="Ongoing",
                vote_average=9.0,
                vote_count=50000,
                popularity=99.8,
                genres=["Action", "Adventure", "Comedy"],
                networks=["Fuji TV"],
                number_of_seasons=20,
                number_of_episodes=1000,
                raw_data={"test": "data3"},
            ),
        ]

    @pytest.fixture
    def sample_parsed_file_data(self):
        """Create sample parsed file data for testing."""
        parsed_info1 = ParsedAnimeInfo(
            title="Attack on Titan",
            season=1,
            episode=1,
            episode_title="To You, in 2000 Years",
            resolution="1080p",
            resolution_width=1920,
            resolution_height=1080,
            video_codec="H264",
            audio_codec="AAC",
            release_group="Erai-raws",
            file_extension=".mkv",
            year=2013,
            source="Blu-ray",
            raw_data={"quality": "high"},
        )

        parsed_info2 = ParsedAnimeInfo(
            title="Demon Slayer",
            season=1,
            episode=1,
            episode_title="Cruelty",
            resolution="720p",
            resolution_width=1280,
            resolution_height=720,
            video_codec="H265",
            audio_codec="FLAC",
            release_group="SubsPlease",
            file_extension=".mp4",
            year=2019,
            source="Web",
            raw_data={"quality": "medium"},
        )

        now = datetime.now(timezone.utc)
        return [
            (
                "/path/to/attack_on_titan_s01e01.mkv",
                "attack_on_titan_s01e01.mkv",
                1024000000,
                now,
                now,
                parsed_info1,
                "hash1",
                1,
            ),
            (
                "/path/to/demon_slayer_s01e01.mp4",
                "demon_slayer_s01e01.mp4",
                512000000,
                now,
                now,
                parsed_info2,
                "hash2",
                2,
            ),
        ]

    def test_bulk_insert_anime_metadata_empty_list(self, db_manager) -> None:
        """Test bulk insert with empty list."""
        result = db_manager.bulk_insert_anime_metadata([])
        assert result == 0

    def test_bulk_insert_anime_metadata_success(self, db_manager, sample_tmdb_anime_list) -> None:
        """Test successful bulk insert of anime metadata."""
        # Insert the data
        result = db_manager.bulk_insert_anime_metadata(sample_tmdb_anime_list)
        assert result == 3

        # Verify data was inserted
        with db_manager.get_session() as session:
            count = session.query(AnimeMetadata).count()
            assert count == 3

            # Check specific records
            aot = session.query(AnimeMetadata).filter_by(tmdb_id=1).first()
            assert aot is not None
            assert aot.title == "Attack on Titan"
            assert aot.korean_title == "진격의 거인"
            assert aot.vote_average == 8.5
            assert aot.number_of_episodes == 75

    def test_bulk_insert_anime_metadata_duplicate_handling(
        self, db_manager, sample_tmdb_anime_list
    ) -> None:
        """Test bulk insert with duplicate TMDB IDs."""
        # Insert first time
        result1 = db_manager.bulk_insert_anime_metadata(sample_tmdb_anime_list)
        assert result1 == 3

        # Try to insert again (should fail due to primary key constraint)
        with pytest.raises(Exception):
            db_manager.bulk_insert_anime_metadata(sample_tmdb_anime_list)

    def test_bulk_insert_parsed_files_empty_list(self, db_manager) -> None:
        """Test bulk insert with empty file list."""
        result = db_manager.bulk_insert_parsed_files([])
        assert result == 0

    def test_bulk_insert_parsed_files_success(self, db_manager, sample_parsed_file_data) -> None:
        """Test successful bulk insert of parsed files."""
        # Insert the data
        result = db_manager.bulk_insert_parsed_files(sample_parsed_file_data)
        assert result == 2

        # Verify data was inserted
        with db_manager.get_session() as session:
            count = session.query(ParsedFile).count()
            assert count == 2

            # Check specific records
            aot_file = (
                session.query(ParsedFile)
                .filter_by(file_path="/path/to/attack_on_titan_s01e01.mkv")
                .first()
            )
            assert aot_file is not None
            assert aot_file.parsed_title == "Attack on Titan"
            assert aot_file.season == 1
            assert aot_file.episode == 1
            assert aot_file.resolution == "1080p"
            assert aot_file.video_codec == "H264"

    def test_bulk_upsert_anime_metadata_new_records(
        self, db_manager, sample_tmdb_anime_list
    ) -> None:
        """Test bulk upsert with all new records."""
        inserted, updated = db_manager.bulk_upsert_anime_metadata(sample_tmdb_anime_list)
        assert inserted == 3
        assert updated == 0

        # Verify all records exist
        with db_manager.get_session() as session:
            count = session.query(AnimeMetadata).count()
            assert count == 3

    def test_bulk_upsert_anime_metadata_mixed_records(
        self, db_manager, sample_tmdb_anime_list
    ) -> None:
        """Test bulk upsert with mix of new and existing records."""
        # Insert first two records
        db_manager.bulk_insert_anime_metadata(sample_tmdb_anime_list[:2])

        # Create modified version of first record and add new third record
        modified_first = sample_tmdb_anime_list[0]
        modified_first.title = "Attack on Titan - Updated"
        modified_first.vote_average = 9.0

        mixed_list = [modified_first, sample_tmdb_anime_list[2]]

        # Upsert mixed list
        inserted, updated = db_manager.bulk_upsert_anime_metadata(mixed_list)
        assert inserted == 1  # Third record is new
        assert updated == 1  # First record is updated

        # Verify updates
        with db_manager.get_session() as session:
            aot = session.query(AnimeMetadata).filter_by(tmdb_id=1).first()
            assert aot.title == "Attack on Titan - Updated"
            assert aot.vote_average == 9.0

    def test_bulk_upsert_anime_metadata_empty_list(self, db_manager) -> None:
        """Test bulk upsert with empty list."""
        inserted, updated = db_manager.bulk_upsert_anime_metadata([])
        assert inserted == 0
        assert updated == 0

    def test_bulk_insert_performance(self, db_manager) -> None:
        """Test performance of bulk insert operations."""
        import time

        # Create large dataset
        large_anime_list = []
        for i in range(1000):
            anime = TMDBAnime(
                tmdb_id=i + 1000,
                title=f"Test Anime {i}",
                original_title=f"テストアニメ {i}",
                overview=f"Test description {i}",
                vote_average=8.0 + (i % 10) * 0.1,
                vote_count=1000 + i,
                popularity=50.0 + i,
                genres=["Action", "Drama"],
                number_of_seasons=1,
                number_of_episodes=12,
                raw_data={"test_id": i},
            )
            large_anime_list.append(anime)

        # Measure bulk insert time
        start_time = time.time()
        result = db_manager.bulk_insert_anime_metadata(large_anime_list)
        end_time = time.time()

        assert result == 1000
        execution_time = end_time - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert execution_time < 5.0  # 5 seconds for 1000 records

        # Verify all records were inserted
        with db_manager.get_session() as session:
            count = session.query(AnimeMetadata).count()
            assert count == 1000

    def test_bulk_insert_data_integrity(self, db_manager, sample_tmdb_anime_list) -> None:
        """Test that bulk insert maintains data integrity."""
        # Insert data
        db_manager.bulk_insert_anime_metadata(sample_tmdb_anime_list)

        # Verify all fields are correctly stored
        with db_manager.get_session() as session:
            aot = session.query(AnimeMetadata).filter_by(tmdb_id=1).first()
            assert aot.title == "Attack on Titan"
            assert aot.original_title == "進撃の巨人"
            assert aot.korean_title == "진격의 거인"
            assert aot.overview == "Humanity fights for survival against Titans."
            assert aot.poster_path == "/poster1.jpg"
            assert aot.backdrop_path == "/backdrop1.jpg"
            assert aot.first_air_date == datetime(2013, 4, 7)
            assert aot.last_air_date == datetime(2023, 11, 5)
            assert aot.status == "Ended"
            assert aot.vote_average == 8.5
            assert aot.vote_count == 15000
            assert aot.popularity == 95.5
            assert aot.number_of_seasons == 4
            assert aot.number_of_episodes == 75

            # Check JSON fields
            assert aot.genres == '["Action", "Drama", "Fantasy"]'
            assert aot.networks == '["NHK"]'
            assert aot.raw_data == '{"test": "data1"}'

    def test_bulk_insert_transaction_rollback(self, db_manager, sample_tmdb_anime_list) -> None:
        """Test that bulk insert properly handles transaction rollback on error."""
        # Create invalid data that will cause an error
        # Use a string for tmdb_id which should cause a type error
        invalid_anime = TMDBAnime(
            tmdb_id="invalid_id",  # This should cause a type error
            title="Invalid Anime",
            overview="This should fail",
        )

        with pytest.raises(Exception):
            db_manager.bulk_insert_anime_metadata([invalid_anime])

        # Verify no data was inserted due to rollback
        with db_manager.get_session() as session:
            count = session.query(AnimeMetadata).count()
            assert count == 0

    def test_bulk_insert_with_metadata_cache(self) -> None:
        """Test bulk insert functionality through MetadataCache."""
        from src.core.metadata_cache import MetadataCache

        # Create cache with database
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        cache = MetadataCache(db_manager=db_manager, enable_db=True)

        # Create sample data
        anime_list = [
            TMDBAnime(
                tmdb_id=1,
                title="Test Anime 1",
                overview="Test description 1",
                vote_average=8.0,
                genres=["Action"],
                number_of_seasons=1,
                number_of_episodes=12,
            ),
            TMDBAnime(
                tmdb_id=2,
                title="Test Anime 2",
                overview="Test description 2",
                vote_average=8.5,
                genres=["Drama"],
                number_of_seasons=2,
                number_of_episodes=24,
            ),
        ]

        # Test bulk store
        result = cache.bulk_store_tmdb_metadata(anime_list)
        assert result == 2

        # Verify data is in both cache and database
        assert cache.get("tmdb:1") is not None
        assert cache.get("tmdb:2") is not None

        with db_manager.get_session() as session:
            count = session.query(AnimeMetadata).count()
            assert count == 2
