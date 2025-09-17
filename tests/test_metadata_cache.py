"""
Tests for metadata caching system.

This module contains comprehensive tests for the metadata cache,
database operations, and cache-DB synchronization functionality.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from src.core.database import DatabaseManager
from src.core.metadata_cache import MetadataCache
from src.core.metadata_storage import MetadataStorage
from src.core.models import ParsedAnimeInfo, TMDBAnime


class TestMetadataCache(unittest.TestCase):
    """Test cases for MetadataCache class."""

    def setUp(self):
        """Set up test fixtures."""
        self.cache = MetadataCache(max_size=10, max_memory_mb=1, ttl_seconds=60)

    def tearDown(self):
        """Clean up after tests."""
        self.cache.clear()

    def test_cache_initialization(self) -> None:
        """Test cache initialization."""
        self.assertEqual(self.cache.max_size, 10)
        self.assertEqual(self.cache.max_memory_bytes, 1024 * 1024)
        self.assertEqual(self.cache.ttl_seconds, 60)
        self.assertTrue(self.cache.is_enabled())

    def test_put_and_get(self) -> None:
        """Test basic put and get operations."""
        anime = TMDBAnime(tmdb_id=1, title="Test Anime", overview="Test overview")

        # Test put
        self.cache.put("test_key", anime)

        # Test get
        result = self.cache.get("test_key")
        self.assertIsNotNone(result)
        self.assertEqual(result.tmdb_id, 1)
        self.assertEqual(result.title, "Test Anime")

    def test_get_nonexistent_key(self) -> None:
        """Test getting a non-existent key."""
        result = self.cache.get("nonexistent_key")
        self.assertIsNone(result)

    def test_get_with_default(self) -> None:
        """Test getting with default value."""
        default_anime = TMDBAnime(tmdb_id=0, title="Default")
        result = self.cache.get("nonexistent_key", default_anime)
        self.assertEqual(result.tmdb_id, 0)
        self.assertEqual(result.title, "Default")

    def test_delete(self) -> None:
        """Test deleting cache entries."""
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")
        self.cache.put("test_key", anime)

        # Verify it exists
        self.assertIsNotNone(self.cache.get("test_key"))

        # Delete it
        result = self.cache.delete("test_key")
        self.assertTrue(result)

        # Verify it's gone
        self.assertIsNone(self.cache.get("test_key"))

    def test_delete_nonexistent_key(self) -> None:
        """Test deleting a non-existent key."""
        result = self.cache.delete("nonexistent_key")
        self.assertFalse(result)

    def test_clear(self) -> None:
        """Test clearing all cache entries."""
        # Add some entries
        for i in range(5):
            anime = TMDBAnime(tmdb_id=i, title=f"Anime {i}")
            self.cache.put(f"key_{i}", anime)

        # Verify they exist
        self.assertEqual(len(self.cache._cache), 5)

        # Clear cache
        self.cache.clear()

        # Verify it's empty
        self.assertEqual(len(self.cache._cache), 0)

    def test_lru_eviction(self) -> None:
        """Test LRU eviction when cache is full."""
        # Fill cache to capacity
        for i in range(10):
            anime = TMDBAnime(tmdb_id=i, title=f"Anime {i}")
            self.cache.put(f"key_{i}", anime)

        # Access some entries to make them more recent
        self.cache.get("key_0")  # Make key_0 most recent
        self.cache.get("key_1")  # Make key_1 second most recent

        # Add one more entry to trigger eviction
        anime = TMDBAnime(tmdb_id=10, title="Anime 10")
        self.cache.put("key_10", anime)

        # key_2 should be evicted (least recently used)
        self.assertIsNone(self.cache.get("key_2"))

        # key_0 and key_1 should still be there
        self.assertIsNotNone(self.cache.get("key_0"))
        self.assertIsNotNone(self.cache.get("key_1"))

    def test_ttl_expiration(self) -> None:
        """Test TTL expiration."""
        # Create cache with short TTL
        cache = MetadataCache(ttl_seconds=1)

        anime = TMDBAnime(tmdb_id=1, title="Test Anime")
        cache.put("test_key", anime)

        # Should be available immediately
        self.assertIsNotNone(cache.get("test_key"))

        # Wait for expiration
        import time

        time.sleep(1.1)

        # Should be expired
        self.assertIsNone(cache.get("test_key"))

    def test_invalidate_pattern(self) -> None:
        """Test pattern-based invalidation."""
        # Add entries with different patterns
        for i in range(5):
            anime = TMDBAnime(tmdb_id=i, title=f"Anime {i}")
            self.cache.put(f"anime_{i}", anime)

        for i in range(3):
            anime = TMDBAnime(tmdb_id=i, title=f"Movie {i}")
            self.cache.put(f"movie_{i}", anime)

        # Invalidate all anime entries
        count = self.cache.invalidate_pattern("anime_*")
        self.assertEqual(count, 5)

        # Verify anime entries are gone
        for i in range(5):
            self.assertIsNone(self.cache.get(f"anime_{i}"))

        # Verify movie entries are still there
        for i in range(3):
            self.assertIsNotNone(self.cache.get(f"movie_{i}"))

    def test_stats_tracking(self) -> None:
        """Test statistics tracking."""
        # Initial stats
        stats = self.cache.get_stats()
        self.assertEqual(stats.hits, 0)
        self.assertEqual(stats.misses, 0)
        self.assertEqual(stats.total_requests, 0)

        # Add an entry
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")
        self.cache.put("test_key", anime)

        # Test hit
        self.cache.get("test_key")
        stats = self.cache.get_stats()
        self.assertEqual(stats.hits, 1)
        self.assertEqual(stats.misses, 0)
        self.assertEqual(stats.total_requests, 1)

        # Test miss
        self.cache.get("nonexistent_key")
        stats = self.cache.get_stats()
        self.assertEqual(stats.hits, 1)
        self.assertEqual(stats.misses, 1)
        self.assertEqual(stats.total_requests, 2)

    def test_memory_usage_tracking(self) -> None:
        """Test memory usage tracking."""
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")
        self.cache.put("test_key", anime)

        memory_mb = self.cache.get_memory_usage_mb()
        self.assertGreater(memory_mb, 0)

        stats = self.cache.get_stats()
        self.assertGreater(stats.memory_usage_bytes, 0)

    def test_disable_enable(self) -> None:
        """Test disabling and enabling cache."""
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")

        # Disable cache
        self.cache.disable()
        self.assertFalse(self.cache.is_enabled())

        # Put should not work
        self.cache.put("test_key", anime)
        self.assertIsNone(self.cache.get("test_key"))

        # Enable cache
        self.cache.enable()
        self.assertTrue(self.cache.is_enabled())

        # Put should work now
        self.cache.put("test_key", anime)
        self.assertIsNotNone(self.cache.get("test_key"))

    def test_entries_info(self) -> None:
        """Test getting entries information."""
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")
        self.cache.put("test_key", anime)

        entries = self.cache.get_entries_info()
        self.assertEqual(len(entries), 1)

        entry = entries[0]
        self.assertEqual(entry["key"], "test_key")
        self.assertEqual(entry["type"], "TMDBAnime")
        self.assertGreater(entry["size_bytes"], 0)
        self.assertGreater(entry["age_seconds"], 0)


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.db_manager = DatabaseManager(f"sqlite:///{self.temp_db.name}")
        self.db_manager.initialize()

    def tearDown(self):
        """Clean up after tests."""
        self.db_manager.close()
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_database_initialization(self) -> None:
        """Test database initialization."""
        self.assertIsNotNone(self.db_manager.engine)
        self.assertIsNotNone(self.db_manager.SessionLocal)

    def test_create_anime_metadata(self) -> None:
        """Test creating anime metadata."""
        anime = TMDBAnime(
            tmdb_id=1,
            title="Test Anime",
            overview="Test overview",
            genres=["Action", "Adventure"],
            networks=["Test Network"],
        )

        metadata = self.db_manager.create_anime_metadata(anime)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.tmdb_id, 1)
        self.assertEqual(metadata.title, "Test Anime")
        self.assertEqual(metadata.overview, "Test overview")

    def test_get_anime_metadata(self) -> None:
        """Test getting anime metadata."""
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")
        self.db_manager.create_anime_metadata(anime)

        result = self.db_manager.get_anime_metadata(1)
        self.assertIsNotNone(result)
        self.assertEqual(result.tmdb_id, 1)
        self.assertEqual(result.title, "Test Anime")

    def test_search_anime_metadata(self) -> None:
        """Test searching anime metadata."""
        # Create test data
        anime1 = TMDBAnime(tmdb_id=1, title="Attack on Titan")
        anime2 = TMDBAnime(tmdb_id=2, title="One Piece")
        anime3 = TMDBAnime(tmdb_id=3, title="Naruto")

        self.db_manager.create_anime_metadata(anime1)
        self.db_manager.create_anime_metadata(anime2)
        self.db_manager.create_anime_metadata(anime3)

        # Search for "Titan"
        results = self.db_manager.search_anime_metadata("Titan")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Attack on Titan")

    def test_create_parsed_file(self) -> None:
        """Test creating parsed file."""
        parsed_info = ParsedAnimeInfo(title="Test Anime", season=1, episode=1, resolution="1080p")

        file_path = "/path/to/test/file.mkv"
        filename = "test file.mkv"
        file_size = 1024 * 1024
        created_at = datetime.now()
        modified_at = datetime.now()

        parsed_file = self.db_manager.create_parsed_file(
            file_path=file_path,
            filename=filename,
            file_size=file_size,
            created_at=created_at,
            modified_at=modified_at,
            parsed_info=parsed_info,
            file_hash="test_hash",
        )

        self.assertIsNotNone(parsed_file)
        self.assertEqual(parsed_file.file_path, file_path)
        self.assertEqual(parsed_file.parsed_title, "Test Anime")
        self.assertEqual(parsed_file.season, 1)
        self.assertEqual(parsed_file.episode, 1)

    def test_get_parsed_file(self) -> None:
        """Test getting parsed file."""
        parsed_info = ParsedAnimeInfo(title="Test Anime")
        file_path = "/path/to/test/file.mkv"

        self.db_manager.create_parsed_file(
            file_path=file_path,
            filename="test.mkv",
            file_size=1024,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            parsed_info=parsed_info,
        )

        result = self.db_manager.get_parsed_file(file_path)
        self.assertIsNotNone(result)
        self.assertEqual(result.file_path, file_path)

    def test_delete_parsed_file(self) -> None:
        """Test deleting parsed file."""
        parsed_info = ParsedAnimeInfo(title="Test Anime")
        file_path = "/path/to/test/file.mkv"

        self.db_manager.create_parsed_file(
            file_path=file_path,
            filename="test.mkv",
            file_size=1024,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            parsed_info=parsed_info,
        )

        # Verify it exists
        self.assertIsNotNone(self.db_manager.get_parsed_file(file_path))

        # Delete it
        result = self.db_manager.delete_parsed_file(file_path)
        self.assertTrue(result)

        # Verify it's gone
        self.assertIsNone(self.db_manager.get_parsed_file(file_path))

    def test_get_database_stats(self) -> None:
        """Test getting database statistics."""
        # Create some test data
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")
        self.db_manager.create_anime_metadata(anime)

        parsed_info = ParsedAnimeInfo(title="Test Anime")
        self.db_manager.create_parsed_file(
            file_path="/path/to/test.mkv",
            filename="test.mkv",
            file_size=1024,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            parsed_info=parsed_info,
            metadata_id=1,
        )

        stats = self.db_manager.get_database_stats()
        self.assertEqual(stats["anime_metadata_count"], 1)
        self.assertEqual(stats["parsed_files_count"], 1)


class TestMetadataStorage(unittest.TestCase):
    """Test cases for MetadataStorage class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.storage = MetadataStorage(
            cache_max_size=10, cache_max_memory_mb=1, enable_cache=True, enable_db=True
        )

        # Override database URL for testing
        self.storage.db = DatabaseManager(f"sqlite:///{self.temp_db.name}")
        self.storage.db.initialize()

    def tearDown(self):
        """Clean up after tests."""
        self.storage.clear_cache()
        if self.storage.db:
            self.storage.db.close()
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_storage_initialization(self) -> None:
        """Test storage initialization."""
        self.assertTrue(self.storage.enable_cache)
        self.assertTrue(self.storage.enable_db)
        self.assertIsNotNone(self.storage.cache)
        self.assertIsNotNone(self.storage.db)

    def test_store_tmdb_metadata(self) -> None:
        """Test storing TMDB metadata."""
        anime = TMDBAnime(tmdb_id=1, title="Test Anime", overview="Test overview")

        result = self.storage.store_tmdb_metadata(anime)
        self.assertTrue(result)

        # Verify it's in cache
        cached = self.storage.cache.get("tmdb:1")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.tmdb_id, 1)

    def test_get_tmdb_metadata_cache_hit(self) -> None:
        """Test getting TMDB metadata from cache."""
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")
        self.storage.store_tmdb_metadata(anime)

        result = self.storage.get_tmdb_metadata(1)
        self.assertIsNotNone(result)
        self.assertEqual(result.tmdb_id, 1)
        self.assertEqual(result.title, "Test Anime")

    def test_get_tmdb_metadata_cache_miss(self) -> None:
        """Test getting TMDB metadata from database on cache miss."""
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")

        # Store directly in database (bypass cache)
        self.storage.db.create_anime_metadata(anime)

        # Clear cache to simulate cache miss
        self.storage.clear_cache()

        result = self.storage.get_tmdb_metadata(1)
        self.assertIsNotNone(result)
        self.assertEqual(result.tmdb_id, 1)
        self.assertEqual(result.title, "Test Anime")

        # Verify it's now in cache
        cached = self.storage.cache.get("tmdb:1")
        self.assertIsNotNone(cached)

    def test_store_parsed_file(self) -> None:
        """Test storing parsed file."""
        parsed_info = ParsedAnimeInfo(title="Test Anime", season=1, episode=1)

        file_path = "/path/to/test.mkv"
        result = self.storage.store_parsed_file(
            file_path=file_path,
            filename="test.mkv",
            file_size=1024,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            parsed_info=parsed_info,
            tmdb_id=1,
        )

        self.assertTrue(result)

    def test_get_parsed_file(self) -> None:
        """Test getting parsed file."""
        parsed_info = ParsedAnimeInfo(title="Test Anime")
        file_path = "/path/to/test.mkv"

        self.storage.store_parsed_file(
            file_path=file_path,
            filename="test.mkv",
            file_size=1024,
            created_at=datetime.now(),
            modified_at=datetime.now(),
            parsed_info=parsed_info,
        )

        result = self.storage.get_parsed_file(file_path)
        self.assertIsNotNone(result)
        self.assertEqual(result["file_path"], file_path)
        self.assertEqual(result["parsed_info"].title, "Test Anime")

    def test_sync_cache_to_db(self) -> None:
        """Test syncing cache to database."""
        # Add some data to cache
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")
        self.storage.cache.put("tmdb:1", anime)

        # Sync to database
        synced_count = self.storage.sync_cache_to_db()
        self.assertGreater(synced_count, 0)

        # Verify it's in database
        result = self.storage.db.get_anime_metadata(1)
        self.assertIsNotNone(result)
        self.assertEqual(result.title, "Test Anime")

    def test_get_stats(self) -> None:
        """Test getting storage statistics."""
        # Add some data
        anime = TMDBAnime(tmdb_id=1, title="Test Anime")
        self.storage.store_tmdb_metadata(anime)

        stats = self.storage.get_stats()
        self.assertIn("cache_hits", stats)
        self.assertIn("cache_misses", stats)
        self.assertIn("db_hits", stats)
        self.assertIn("db_misses", stats)
        self.assertIn("total_requests", stats)
        self.assertIn("sync_operations", stats)


class TestCacheDBIntegration(unittest.TestCase):
    """Integration tests for cache-DB synchronization."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()

        self.storage = MetadataStorage(
            cache_max_size=100, cache_max_memory_mb=10, enable_cache=True, enable_db=True
        )

        # Override database URL for testing
        self.storage.db = DatabaseManager(f"sqlite:///{self.temp_db.name}")
        self.storage.db.initialize()

    def tearDown(self):
        """Clean up after tests."""
        self.storage.clear_cache()
        if self.storage.db:
            self.storage.db.close()
        Path(self.temp_db.name).unlink(missing_ok=True)

    def test_end_to_end_workflow(self) -> None:
        """Test complete end-to-end workflow."""
        # Create TMDB metadata
        anime = TMDBAnime(
            tmdb_id=1,
            title="Attack on Titan",
            overview="Humanity fights against Titans",
            genres=["Action", "Drama"],
            networks=["NHK"],
        )

        # Store metadata
        self.assertTrue(self.storage.store_tmdb_metadata(anime))

        # Create parsed file
        parsed_info = ParsedAnimeInfo(
            title="Attack on Titan", season=1, episode=1, resolution="1080p", video_codec="H264"
        )

        self.assertTrue(
            self.storage.store_parsed_file(
                file_path="/path/to/attack_on_titan_s01e01.mkv",
                filename="attack_on_titan_s01e01.mkv",
                file_size=1024 * 1024 * 500,  # 500MB
                created_at=datetime.now(),
                modified_at=datetime.now(),
                parsed_info=parsed_info,
                tmdb_id=1,
            )
        )

        # Retrieve metadata (should hit cache)
        retrieved_anime = self.storage.get_tmdb_metadata(1)
        self.assertIsNotNone(retrieved_anime)
        self.assertEqual(retrieved_anime.title, "Attack on Titan")

        # Retrieve file info (should hit cache)
        retrieved_file = self.storage.get_parsed_file("/path/to/attack_on_titan_s01e01.mkv")
        self.assertIsNotNone(retrieved_file)
        self.assertEqual(retrieved_file["parsed_info"].title, "Attack on Titan")

        # Get files by TMDB ID
        files = self.storage.get_files_by_tmdb_id(1)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["parsed_info"].title, "Attack on Titan")

        # Check statistics
        stats = self.storage.get_stats()
        self.assertGreater(stats["cache_hits"], 0)
        self.assertGreater(stats["sync_operations"], 0)

    def test_concurrent_access(self) -> None:
        """Test concurrent access to storage system."""
        import threading

        results = []
        errors = []

        def worker(worker_id):
            try:
                # Each worker creates and retrieves data
                anime = TMDBAnime(tmdb_id=worker_id, title=f"Anime {worker_id}")
                self.storage.store_tmdb_metadata(anime)

                retrieved = self.storage.get_tmdb_metadata(worker_id)
                results.append((worker_id, retrieved is not None))

            except Exception as e:
                errors.append((worker_id, str(e)))

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations succeeded
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 10)

        for worker_id, success in results:
            self.assertTrue(success, f"Worker {worker_id} failed")


if __name__ == "__main__":
    unittest.main()
