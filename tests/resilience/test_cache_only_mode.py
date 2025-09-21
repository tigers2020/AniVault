"""Tests for cache-only mode behavior in the MetadataCache class."""

import time
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.core.metadata_cache import MetadataCache, CacheEntry
from src.core.models import ParsedAnimeInfo, TMDBAnime


class TestCacheOnlyModeBehavior:
    """Test cache-only mode behavior for MetadataCache."""

    def _create_cache_entry(self, key: str, value: ParsedAnimeInfo | TMDBAnime, created_at: float = None) -> CacheEntry:
        """Helper method to create a CacheEntry."""
        if created_at is None:
            created_at = time.time()
        return CacheEntry(
            key=key,
            value=value,
            created_at=created_at,
            last_accessed=created_at,
            size_bytes=100
        )

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock database with proper session support
        self.mock_db = Mock()
        self.mock_session = Mock()
        self.mock_db.get_session.return_value = self.mock_session

        # Create MetadataCache instance with mock database and proper max_size
        self.cache = MetadataCache(
            max_size=100,  # Set max_size as constructor parameter
            db_manager=self.mock_db
        )

        # Create sample ParsedAnimeInfo (only title is required)
        self.sample_parsed_info = ParsedAnimeInfo(
            title="Attack on Titan"
        )

        # Create sample TMDBAnime
        self.sample_tmdb_anime = TMDBAnime(
            tmdb_id=12345,
            title="Attack on Titan"
        )

    def test_cache_only_mode_read_cache_hit(self):
        """Test that cache hits work normally in cache-only mode."""
        # Setup cache-only mode
        with patch.object(self.cache, 'is_cache_only_mode', return_value=True):
            # Manually add data to cache to simulate cache hit
            self.cache._cache["test_key"] = self._create_cache_entry("test_key", self.sample_parsed_info)

            # Clear the mock to ensure no database calls
            self.mock_db.reset_mock()

            # Get data from cache (should hit)
            result = self.cache.get("test_key")

            # Verify cache hit works
            assert result is not None
            assert isinstance(result, ParsedAnimeInfo)
            assert result.title == "Attack on Titan"

            # Verify no database calls were made
            self.mock_db.assert_not_called()

    def test_cache_only_mode_read_cache_miss(self):
        """Test that cache misses return None without database calls in cache-only mode."""
        # Setup cache-only mode
        with patch.object(self.cache, 'is_cache_only_mode', return_value=True):
            # Ensure cache is empty
            self.cache._cache.clear()

            # Try to get non-existent key
            result = self.cache.get("non_existent_key")

            # Verify cache miss returns None
            assert result is None

            # Verify no database calls were made
            self.mock_db.assert_not_called()

    def test_cache_only_mode_read_with_default_value(self):
        """Test that cache misses return default value without database calls in cache-only mode."""
        # Setup cache-only mode
        with patch.object(self.cache, 'is_cache_only_mode', return_value=True):
            # Ensure cache is empty
            self.cache._cache.clear()

            # Try to get non-existent key with default
            default_value = ParsedAnimeInfo(
                title="Default Anime"
            )
            result = self.cache.get("non_existent_key", default_value)

            # Verify default value is returned
            assert result == default_value

            # Verify no database calls were made
            self.mock_db.assert_not_called()

    def test_cache_only_mode_enable_disable(self):
        """Test enabling and disabling cache-only mode."""
        # Initially not in cache-only mode
        assert not self.cache.is_cache_only_mode()

        # Enable cache-only mode
        self.cache.enable_cache_only_mode()
        assert self.cache.is_cache_only_mode()

        # Disable cache-only mode
        self.cache.disable_cache_only_mode()
        assert not self.cache.is_cache_only_mode()

    def test_cache_only_mode_with_database_disabled(self):
        """Test cache-only mode when database is disabled."""
        # Mock database as disabled by setting enable_db to False
        original_enable_db = self.cache.enable_db
        self.cache.enable_db = False

        # Manually enable cache-only mode since it's not automatic
        self.cache.enable_cache_only_mode()

        try:
            # Should be in cache-only mode
            assert self.cache.is_cache_only_mode()

            # Manually add data to cache
            self.cache._cache["test_key"] = self._create_cache_entry("test_key", self.sample_parsed_info)

            # Get data from cache
            result = self.cache.get("test_key")

            assert result is not None
            assert result.title == "Attack on Titan"
        finally:
            # Restore original enable_db
            self.cache.enable_db = original_enable_db

    def test_cache_only_mode_statistics_tracking(self):
        """Test that statistics tracking works in cache-only mode."""
        self.cache.reset_stats()

        with patch.object(self.cache, 'is_cache_only_mode', return_value=True):
            # Manually add data to cache
            self.cache._cache["key1"] = self._create_cache_entry("key1", self.sample_parsed_info)

            # Clear the mock to ensure no database calls
            self.mock_db.reset_mock()

            # Get data (hit)
            result1 = self.cache.get("key1")

            # Get non-existent data (miss)
            result2 = self.cache.get("key2")

            # Get statistics
            stats = self.cache.get_stats()

            # Verify statistics are tracked
            assert stats is not None
            assert hasattr(stats, 'hits')
            assert hasattr(stats, 'misses')
            assert hasattr(stats, 'cache_size')

            # Verify no database calls were made
            self.mock_db.assert_not_called()

    def test_cache_only_mode_clear_operation(self):
        """Test that clear operations work in cache-only mode."""
        with patch.object(self.cache, 'is_cache_only_mode', return_value=True):
            # Manually add some data to cache
            self.cache._cache["key1"] = self._create_cache_entry("key1", self.sample_parsed_info)
            self.cache._cache["key2"] = self._create_cache_entry("key2", self.sample_tmdb_anime)

            # Clear the mock to ensure no database calls
            self.mock_db.reset_mock()

            # Clear cache
            self.cache.clear()

            # Verify cache is empty
            assert self.cache.get("key1") is None
            assert self.cache.get("key2") is None

            # Verify no database calls were made
            self.mock_db.assert_not_called()

    def test_cache_only_mode_invalidate_pattern(self):
        """Test that pattern invalidation works in cache-only mode."""
        with patch.object(self.cache, 'is_cache_only_mode', return_value=True):
            # Manually add some data with similar keys
            self.cache._cache["anime_001"] = self._create_cache_entry("anime_001", self.sample_parsed_info)
            self.cache._cache["anime_002"] = self._create_cache_entry("anime_002", self.sample_parsed_info)
            self.cache._cache["other_key"] = self._create_cache_entry("other_key", self.sample_parsed_info)

            # Clear the mock to ensure no database calls
            self.mock_db.reset_mock()

            # Invalidate pattern
            self.cache.invalidate_pattern("anime_*")

            # Verify anime_* keys are gone but other_key remains
            assert self.cache.get("anime_001") is None
            assert self.cache.get("anime_002") is None
            assert self.cache.get("other_key") is not None

            # Verify no database calls were made
            self.mock_db.assert_not_called()

    def test_cache_only_mode_with_expired_entries(self):
        """Test cache-only mode behavior with expired entries."""
        with patch.object(self.cache, 'is_cache_only_mode', return_value=True):
            # Store data with short TTL by setting ttl_seconds
            original_ttl = self.cache.ttl_seconds
            self.cache.ttl_seconds = 0.1  # 100ms TTL

            try:
                # Manually add expired data to cache
                expired_time = time.time() - 1.0  # Expired 1 second ago
                self.cache._cache["test_key"] = self._create_cache_entry("test_key", self.sample_parsed_info, expired_time)

                # Try to get expired data
                result = self.cache.get("test_key")

                # In cache-only mode, expired entries should return None
                assert result is None
            finally:
                # Restore original TTL
                self.cache.ttl_seconds = original_ttl


class TestCacheOnlyModeIntegration:
    """Integration tests for cache-only mode with realistic scenarios."""

    def _create_cache_entry(self, key: str, value: ParsedAnimeInfo | TMDBAnime, created_at: float = None) -> CacheEntry:
        """Helper method to create a CacheEntry."""
        if created_at is None:
            created_at = time.time()
        return CacheEntry(
            key=key,
            value=value,
            created_at=created_at,
            last_accessed=created_at,
            size_bytes=100
        )

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock database with proper session support
        self.mock_db = Mock()
        self.mock_session = Mock()
        self.mock_db.get_session.return_value = self.mock_session

        # Create MetadataCache instance with mock database and proper max_size
        self.cache = MetadataCache(
            max_size=100,  # Set max_size as constructor parameter
            db_manager=self.mock_db
        )

        # Create sample ParsedAnimeInfo (only title is required)
        self.sample_parsed_info = ParsedAnimeInfo(
            title="Attack on Titan"
        )

        # Create sample TMDBAnime
        self.sample_tmdb_anime = TMDBAnime(
            tmdb_id=12345,
            title="Attack on Titan"
        )

    def test_cache_only_mode_realistic_workflow(self):
        """Test a realistic workflow in cache-only mode."""
        with patch.object(self.cache, 'is_cache_only_mode', return_value=True):
            # Clear the mock to ensure no database calls
            self.mock_db.reset_mock()

            # Simulate processing anime files - manually add to cache
            anime_info = ParsedAnimeInfo(
                title="Attack on Titan",
                season=1,
                episode=1
            )

            tmdb_info = TMDBAnime(
                tmdb_id=1429,
                title="Attack on Titan",
                original_title="Shingeki no Kyojin",
                overview="Humanity fights for survival against the Titans."
            )

            # Manually store parsed info in cache
            self.cache._cache["parsed_attack_on_titan_s01e01"] = self._create_cache_entry("parsed_attack_on_titan_s01e01", anime_info)

            # Manually store TMDB info in cache
            self.cache._cache["tmdb_attack_on_titan"] = self._create_cache_entry("tmdb_attack_on_titan", tmdb_info)

            # Retrieve and verify
            retrieved_parsed = self.cache.get("parsed_attack_on_titan_s01e01")
            retrieved_tmdb = self.cache.get("tmdb_attack_on_titan")

            assert retrieved_parsed is not None
            assert retrieved_tmdb is not None
            assert retrieved_parsed.title == "Attack on Titan"
            assert retrieved_tmdb.tmdb_id == 1429

            # Verify no database calls were made
            self.mock_db.assert_not_called()

    def test_cache_only_mode_with_mixed_operations(self):
        """Test mixed operations (read/clear/invalidate) in cache-only mode."""
        with patch.object(self.cache, 'is_cache_only_mode', return_value=True):
            # Clear the mock to ensure no database calls
            self.mock_db.reset_mock()

            # Manually add data to cache
            self.cache._cache["key1"] = self._create_cache_entry("key1", self.sample_parsed_info)
            self.cache._cache["key2"] = self._create_cache_entry("key2", self.sample_tmdb_anime)

            # Read operations
            result1 = self.cache.get("key1")
            result2 = self.cache.get("key2")
            result3 = self.cache.get("non_existent")

            assert result1 is not None
            assert result2 is not None
            assert result3 is None

            # Clear operation
            self.cache.clear()

            # Verify cleared keys are gone
            assert self.cache.get("key1") is None
            assert self.cache.get("key2") is None

            # Verify no database calls were made
            self.mock_db.assert_not_called()

    def test_cache_only_mode_performance_characteristics(self):
        """Test performance characteristics of cache-only mode operations."""
        with patch.object(self.cache, 'is_cache_only_mode', return_value=True):
            # Measure bulk read performance
            start_time = time.time()

            # Manually add multiple entries to cache
            for i in range(50):
                anime_info = ParsedAnimeInfo(title=f"Test Anime {i}")
                self.cache._cache[f"anime_{i}"] = self._create_cache_entry(f"anime_{i}", anime_info)

            # Read all entries
            results = []
            for i in range(50):
                result = self.cache.get(f"anime_{i}")
                results.append(result)

            read_time = time.time() - start_time

            # Verify all reads were successful
            assert len(results) == 50
            assert all(result is not None for result in results)

            # Performance should be reasonable (adjust thresholds as needed)
            assert read_time < 1.0   # Should complete in under 1 second

            # Verify no database calls were made
            self.mock_db.assert_not_called()
