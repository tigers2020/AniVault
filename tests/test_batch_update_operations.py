"""Tests for batch database update operations functionality.

This module tests the bulk update operations for both
anime metadata and parsed files to ensure performance and data integrity.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from src.core.database import DatabaseManager, AnimeMetadata, ParsedFile
from src.core.models import TMDBAnime, ParsedAnimeInfo


class TestBatchUpdateOperations:
    """Test cases for batch database update operations."""

    @pytest.fixture
    def db_manager(self):
        """Create a test database manager."""
        manager = DatabaseManager("sqlite:///:memory:")
        manager.initialize()
        return manager

    @pytest.fixture
    def sample_anime_data(self, db_manager):
        """Create and insert sample anime data for testing."""
        anime_list = [
            TMDBAnime(
                tmdb_id=1,
                title="Attack on Titan",
                original_title="進撃の巨人",
                overview="Humanity fights for survival against Titans.",
                vote_average=8.5,
                vote_count=15000,
                popularity=95.5,
                genres=["Action", "Drama", "Fantasy"],
                number_of_seasons=4,
                number_of_episodes=75
            ),
            TMDBAnime(
                tmdb_id=2,
                title="Demon Slayer",
                original_title="鬼滅の刃",
                overview="A young boy becomes a demon slayer.",
                vote_average=8.7,
                vote_count=20000,
                popularity=98.2,
                genres=["Action", "Supernatural"],
                number_of_seasons=3,
                number_of_episodes=44
            ),
            TMDBAnime(
                tmdb_id=3,
                title="One Piece",
                original_title="ワンピース",
                overview="A pirate's journey to find the ultimate treasure.",
                vote_average=9.0,
                vote_count=50000,
                popularity=99.8,
                genres=["Action", "Adventure"],
                number_of_seasons=20,
                number_of_episodes=1000
            )
        ]
        
        # Insert the data
        db_manager.bulk_insert_anime_metadata(anime_list)
        return anime_list

    @pytest.fixture
    def sample_file_data(self, db_manager):
        """Create and insert sample file data for testing."""
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
            source="Blu-ray"
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
            source="Web"
        )
        
        now = datetime.now(timezone.utc)
        file_data = [
            ("/path/to/attack_on_titan_s01e01.mkv", "attack_on_titan_s01e01.mkv", 
             1024000000, now, now, parsed_info1, "hash1", 1),
            ("/path/to/demon_slayer_s01e01.mp4", "demon_slayer_s01e01.mp4", 
             512000000, now, now, parsed_info2, "hash2", 2)
        ]
        
        # Insert the data
        db_manager.bulk_insert_parsed_files(file_data)
        return file_data

    def test_bulk_update_anime_metadata_empty_list(self, db_manager):
        """Test bulk update with empty list."""
        result = db_manager.bulk_update_anime_metadata([])
        assert result == 0

    def test_bulk_update_anime_metadata_success(self, db_manager, sample_anime_data):
        """Test successful bulk update of anime metadata."""
        # Prepare updates
        updates = [
            {'tmdb_id': 1, 'title': 'Attack on Titan - Updated', 'vote_average': 9.0},
            {'tmdb_id': 2, 'title': 'Demon Slayer - Updated', 'vote_average': 9.2},
            {'tmdb_id': 3, 'title': 'One Piece - Updated', 'vote_average': 9.5}
        ]
        
        # Perform bulk update
        result = db_manager.bulk_update_anime_metadata(updates)
        assert result == 3
        
        # Verify updates
        with db_manager.get_session() as session:
            aot = session.query(AnimeMetadata).filter_by(tmdb_id=1).first()
            assert aot.title == "Attack on Titan - Updated"
            assert aot.vote_average == 9.0
            
            ds = session.query(AnimeMetadata).filter_by(tmdb_id=2).first()
            assert ds.title == "Demon Slayer - Updated"
            assert ds.vote_average == 9.2
            
            op = session.query(AnimeMetadata).filter_by(tmdb_id=3).first()
            assert op.title == "One Piece - Updated"
            assert op.vote_average == 9.5

    def test_bulk_update_anime_metadata_missing_primary_key(self, db_manager):
        """Test bulk update with missing primary key raises error."""
        updates = [
            {'title': 'Invalid Update', 'vote_average': 9.0}  # Missing tmdb_id
        ]
        
        with pytest.raises(ValueError, match="All update dictionaries must contain 'tmdb_id' field"):
            db_manager.bulk_update_anime_metadata(updates)

    def test_bulk_update_anime_metadata_by_tmdb_ids(self, db_manager, sample_anime_data):
        """Test bulk update by TMDB IDs with same update data."""
        tmdb_ids = [1, 2]
        update_data = {
            'status': 'Completed',
            'vote_average': 9.5
        }
        
        # Perform bulk update
        result = db_manager.bulk_update_anime_metadata_by_tmdb_ids(tmdb_ids, update_data)
        assert result == 2
        
        # Verify updates
        with db_manager.get_session() as session:
            aot = session.query(AnimeMetadata).filter_by(tmdb_id=1).first()
            assert aot.status == "Completed"
            assert aot.vote_average == 9.5
            
            ds = session.query(AnimeMetadata).filter_by(tmdb_id=2).first()
            assert ds.status == "Completed"
            assert ds.vote_average == 9.5
            
            # Verify One Piece was not updated
            op = session.query(AnimeMetadata).filter_by(tmdb_id=3).first()
            assert op.status != "Completed"
            assert op.vote_average == 9.0  # Original value

    def test_bulk_update_anime_metadata_by_tmdb_ids_empty_lists(self, db_manager):
        """Test bulk update by TMDB IDs with empty lists."""
        result1 = db_manager.bulk_update_anime_metadata_by_tmdb_ids([], {'status': 'Test'})
        assert result1 == 0
        
        result2 = db_manager.bulk_update_anime_metadata_by_tmdb_ids([1, 2], {})
        assert result2 == 0

    def test_bulk_update_parsed_files_empty_list(self, db_manager):
        """Test bulk update with empty file list."""
        result = db_manager.bulk_update_parsed_files([])
        assert result == 0

    def test_bulk_update_parsed_files_success(self, db_manager, sample_file_data):
        """Test successful bulk update of parsed files."""
        # First get the file IDs
        with db_manager.get_session() as session:
            files = session.query(ParsedFile).all()
            file_ids = [f.id for f in files]
        
        # Prepare updates
        updates = [
            {'id': file_ids[0], 'is_processed': True, 'processing_errors': '{}'},
            {'id': file_ids[1], 'is_processed': True, 'processing_errors': '{}'}
        ]
        
        # Perform bulk update
        result = db_manager.bulk_update_parsed_files(updates)
        assert result == 2
        
        # Verify updates
        with db_manager.get_session() as session:
            for file_id in file_ids:
                file_record = session.query(ParsedFile).filter_by(id=file_id).first()
                assert file_record.is_processed is True
                assert file_record.processing_errors == '{}'

    def test_bulk_update_parsed_files_missing_primary_key(self, db_manager):
        """Test bulk update with missing primary key raises error."""
        updates = [
            {'is_processed': True}  # Missing id
        ]
        
        with pytest.raises(ValueError, match="All update dictionaries must contain 'id' field"):
            db_manager.bulk_update_parsed_files(updates)

    def test_bulk_update_parsed_files_by_paths(self, db_manager, sample_file_data):
        """Test bulk update by file paths with same update data."""
        file_paths = ["/path/to/attack_on_titan_s01e01.mkv", "/path/to/demon_slayer_s01e01.mp4"]
        update_data = {
            'is_processed': True,
            'processing_errors': '{"status": "completed"}'
        }
        
        # Perform bulk update
        result = db_manager.bulk_update_parsed_files_by_paths(file_paths, update_data)
        assert result == 2
        
        # Verify updates
        with db_manager.get_session() as session:
            for file_path in file_paths:
                file_record = session.query(ParsedFile).filter_by(file_path=file_path).first()
                assert file_record.is_processed is True
                assert file_record.processing_errors == '{"status": "completed"}'

    def test_bulk_update_parsed_files_by_paths_nonexistent(self, db_manager):
        """Test bulk update by file paths with nonexistent paths."""
        file_paths = ["/nonexistent/path1.mkv", "/nonexistent/path2.mp4"]
        update_data = {'is_processed': True}
        
        # Perform bulk update
        result = db_manager.bulk_update_parsed_files_by_paths(file_paths, update_data)
        assert result == 0

    def test_bulk_update_performance(self, db_manager, sample_anime_data):
        """Test performance of bulk update operations."""
        import time
        
        # Create large update dataset
        updates = []
        for i in range(1000):
            updates.append({
                'tmdb_id': (i % 3) + 1,  # Cycle through existing IDs
                'vote_average': 8.0 + (i % 10) * 0.1,
                'vote_count': 1000 + i
            })
        
        # Measure bulk update time
        start_time = time.time()
        result = db_manager.bulk_update_anime_metadata(updates)
        end_time = time.time()
        
        assert result == 1000
        execution_time = end_time - start_time
        
        # Should complete within reasonable time
        assert execution_time < 3.0  # 3 seconds for 1000 updates

    def test_bulk_update_data_integrity(self, db_manager, sample_anime_data):
        """Test that bulk update maintains data integrity."""
        # Update only specific fields
        updates = [
            {'tmdb_id': 1, 'title': 'Attack on Titan - Final Season', 'vote_average': 9.5},
            {'tmdb_id': 2, 'title': 'Demon Slayer - Entertainment District Arc', 'vote_average': 9.3}
        ]
        
        # Perform update
        db_manager.bulk_update_anime_metadata(updates)
        
        # Verify only specified fields were updated
        with db_manager.get_session() as session:
            aot = session.query(AnimeMetadata).filter_by(tmdb_id=1).first()
            assert aot.title == "Attack on Titan - Final Season"
            assert aot.vote_average == 9.5
            # Verify other fields remain unchanged
            assert aot.original_title == "進撃の巨人"
            assert aot.overview == "Humanity fights for survival against Titans."
            assert aot.vote_count == 15000  # Original value
            
            ds = session.query(AnimeMetadata).filter_by(tmdb_id=2).first()
            assert ds.title == "Demon Slayer - Entertainment District Arc"
            assert ds.vote_average == 9.3
            # Verify other fields remain unchanged
            assert ds.original_title == "鬼滅の刃"
            assert ds.overview == "A young boy becomes a demon slayer."
            assert ds.vote_count == 20000  # Original value

    def test_bulk_update_transaction_rollback(self, db_manager, sample_anime_data):
        """Test that bulk update properly handles transaction rollback on error."""
        # Create invalid update data
        updates = [
            {'tmdb_id': 1, 'title': 'Valid Update'},
            {'tmdb_id': 'invalid_id', 'title': 'Invalid Update'}  # Invalid tmdb_id type
        ]
        
        with pytest.raises(Exception):
            db_manager.bulk_update_anime_metadata(updates)
        
        # Verify no data was updated due to rollback
        with db_manager.get_session() as session:
            aot = session.query(AnimeMetadata).filter_by(tmdb_id=1).first()
            assert aot.title == "Attack on Titan"  # Original value
            assert aot.vote_average == 8.5  # Original value

    def test_bulk_update_with_metadata_cache(self):
        """Test bulk update functionality through MetadataCache."""
        from src.core.metadata_cache import MetadataCache
        
        # Create cache with database
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        cache = MetadataCache(db_manager=db_manager, enable_db=True)
        
        # Insert sample data
        anime_list = [
            TMDBAnime(
                tmdb_id=1,
                title="Test Anime 1",
                overview="Test description 1",
                vote_average=8.0,
                genres=["Action"],
                number_of_seasons=1,
                number_of_episodes=12
            ),
            TMDBAnime(
                tmdb_id=2,
                title="Test Anime 2",
                overview="Test description 2",
                vote_average=8.5,
                genres=["Drama"],
                number_of_seasons=2,
                number_of_episodes=24
            )
        ]
        
        # Store data
        cache.bulk_store_tmdb_metadata(anime_list)
        
        # Prepare updates
        updates = [
            {'tmdb_id': 1, 'title': 'Updated Anime 1', 'vote_average': 9.0},
            {'tmdb_id': 2, 'title': 'Updated Anime 2', 'vote_average': 9.5}
        ]
        
        # Test bulk update
        result = cache.bulk_update_tmdb_metadata(updates)
        assert result == 2
        
        # Verify data is updated in both cache and database
        # Cache should be invalidated and reloaded from database
        aot = cache.get("tmdb:1")
        assert aot is not None
        assert aot.title == "Updated Anime 1"
        assert aot.vote_average == 9.0
        
        with db_manager.get_session() as session:
            count = session.query(AnimeMetadata).count()
            assert count == 2
            
            aot_db = session.query(AnimeMetadata).filter_by(tmdb_id=1).first()
            assert aot_db.title == "Updated Anime 1"
            assert aot_db.vote_average == 9.0

    def test_bulk_update_by_ids_with_cache(self):
        """Test bulk update by IDs functionality through MetadataCache."""
        from src.core.metadata_cache import MetadataCache
        
        # Create cache with database
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.initialize()
        cache = MetadataCache(db_manager=db_manager, enable_db=True)
        
        # Insert sample data
        anime_list = [
            TMDBAnime(tmdb_id=1, title="Anime 1", vote_average=8.0),
            TMDBAnime(tmdb_id=2, title="Anime 2", vote_average=8.5),
            TMDBAnime(tmdb_id=3, title="Anime 3", vote_average=9.0)
        ]
        
        cache.bulk_store_tmdb_metadata(anime_list)
        
        # Update by IDs
        tmdb_ids = [1, 2]
        update_data = {'status': 'Completed', 'vote_average': 9.5}
        
        result = cache.bulk_update_tmdb_metadata_by_ids(tmdb_ids, update_data)
        assert result == 2
        
        # Verify updates
        with db_manager.get_session() as session:
            for tmdb_id in tmdb_ids:
                record = session.query(AnimeMetadata).filter_by(tmdb_id=tmdb_id).first()
                assert record.status == "Completed"
                assert record.vote_average == 9.5
            
            # Verify third record unchanged
            record3 = session.query(AnimeMetadata).filter_by(tmdb_id=3).first()
            assert record3.status != "Completed"
            assert record3.vote_average == 9.0
