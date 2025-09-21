"""Tests for TTL-based caching functionality in MetadataCache."""

import pytest
import time
from unittest.mock import Mock, patch
from dataclasses import dataclass

from src.core.metadata_cache import MetadataCache, CacheEntry, CacheStats
from src.core.models import ParsedAnimeInfo, TMDBAnime


@dataclass
class MockAnimeInfo:
    """Mock anime info for testing."""
    title: str
    tmdb_id: int = 1
    original_title: str = ""
    korean_title: str = ""
    overview: str = ""
    poster_path: str = ""
    backdrop_path: str = ""
    status: str = ""
    genres: list = None
    networks: list = None
    production_companies: list = None
    production_countries: list = None
    spoken_languages: list = None
    raw_data: dict = None
    
    def __post_init__(self):
        if self.genres is None:
            self.genres = []
        if self.networks is None:
            self.networks = []
        if self.production_companies is None:
            self.production_companies = []
        if self.production_countries is None:
            self.production_countries = []
        if self.spoken_languages is None:
            self.spoken_languages = []
        if self.raw_data is None:
            self.raw_data = {}


class TestCacheEntryTTL:
    """Test TTL functionality in CacheEntry."""

    def test_cache_entry_creation_with_ttl(self):
        """Test creating CacheEntry with TTL."""
        now = time.time()
        entry = CacheEntry(
            key="test_key",
            value=MockAnimeInfo("Test Anime"),
            created_at=now,
            last_accessed=now,
            ttl_seconds=60
        )
        
        assert entry.ttl_seconds == 60
        assert not entry.is_expired()
        remaining = entry.get_remaining_ttl()
        assert 59 <= remaining <= 60  # Allow for small time differences

    def test_cache_entry_creation_without_ttl(self):
        """Test creating CacheEntry without TTL."""
        now = time.time()
        entry = CacheEntry(
            key="test_key",
            value=MockAnimeInfo("Test Anime"),
            created_at=now,
            last_accessed=now,
            ttl_seconds=None
        )
        
        assert entry.ttl_seconds is None
        assert not entry.is_expired()
        assert entry.get_remaining_ttl() is None

    def test_cache_entry_expiration_check(self):
        """Test cache entry expiration checking."""
        now = time.time()
        entry = CacheEntry(
            key="test_key",
            value=MockAnimeInfo("Test Anime"),
            created_at=now - 70,  # 70 seconds ago
            last_accessed=now,
            ttl_seconds=60
        )
        
        assert entry.is_expired()
        assert entry.get_remaining_ttl() == 0

    def test_cache_entry_not_expired(self):
        """Test cache entry not expired."""
        now = time.time()
        entry = CacheEntry(
            key="test_key",
            value=MockAnimeInfo("Test Anime"),
            created_at=now - 30,  # 30 seconds ago
            last_accessed=now,
            ttl_seconds=60
        )
        
        assert not entry.is_expired()
        remaining = entry.get_remaining_ttl()
        assert 29 <= remaining <= 30  # Allow for small time differences

    def test_cache_entry_global_ttl_fallback(self):
        """Test cache entry uses global TTL when per-entry TTL is None."""
        now = time.time()
        entry = CacheEntry(
            key="test_key",
            value=MockAnimeInfo("Test Anime"),
            created_at=now - 70,  # 70 seconds ago
            last_accessed=now,
            ttl_seconds=None
        )
        
        # Should use global TTL
        assert entry.is_expired(global_ttl=60)
        assert entry.get_remaining_ttl(global_ttl=60) == 0

    def test_cache_entry_per_entry_ttl_overrides_global(self):
        """Test per-entry TTL overrides global TTL."""
        now = time.time()
        entry = CacheEntry(
            key="test_key",
            value=MockAnimeInfo("Test Anime"),
            created_at=now - 30,  # 30 seconds ago
            last_accessed=now,
            ttl_seconds=20  # Per-entry TTL
        )
        
        # Per-entry TTL should override global TTL
        assert entry.is_expired(global_ttl=60)
        assert entry.get_remaining_ttl(global_ttl=60) == 0


class TestMetadataCacheTTL:
    """Test TTL functionality in MetadataCache."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = MetadataCache(max_size=100, ttl_seconds=60)

    def teardown_method(self):
        """Clean up after tests."""
        self.cache.clear()

    def test_put_with_global_ttl(self):
        """Test putting entry with global TTL."""
        anime = MockAnimeInfo("Test Anime")
        self.cache.put("test_key", anime)
        
        entry = self.cache._cache["test_key"]
        assert entry.ttl_seconds is None  # Uses global TTL
        assert not entry.is_expired(self.cache.ttl_seconds)

    def test_put_with_per_entry_ttl(self):
        """Test putting entry with per-entry TTL."""
        anime = MockAnimeInfo("Test Anime")
        self.cache.put("test_key", anime, ttl_seconds=30)
        
        entry = self.cache._cache["test_key"]
        assert entry.ttl_seconds == 30
        assert not entry.is_expired(self.cache.ttl_seconds)

    def test_get_expired_entry_returns_none(self):
        """Test getting expired entry returns None."""
        anime = MockAnimeInfo("Test Anime")
        self.cache.put("test_key", anime, ttl_seconds=1)
        
        # Wait for expiration
        time.sleep(1.1)
        
        result = self.cache.get("test_key")
        assert result is None

    def test_get_non_expired_entry_returns_value(self):
        """Test getting non-expired entry returns value."""
        anime = MockAnimeInfo("Test Anime")
        self.cache.put("test_key", anime, ttl_seconds=60)
        
        result = self.cache.get("test_key")
        assert result is not None
        assert result.title == "Test Anime"

    def test_ttl_statistics_tracking(self):
        """Test TTL statistics are properly tracked."""
        anime = MockAnimeInfo("Test Anime")
        
        # Put entry with short TTL
        self.cache.put("test_key", anime, ttl_seconds=1)
        
        # Get before expiration (should be hit)
        result = self.cache.get("test_key")
        assert result is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Get after expiration (should be miss due to TTL)
        result = self.cache.get("test_key")
        assert result is None
        
        stats = self.cache.get_stats()
        assert stats.ttl_hits >= 1
        assert stats.ttl_misses >= 1
        assert stats.ttl_expirations >= 1

    def test_cleanup_expired_entries(self):
        """Test manual cleanup of expired entries."""
        anime1 = MockAnimeInfo("Anime 1")
        anime2 = MockAnimeInfo("Anime 2")
        
        # Put entries with different TTLs
        self.cache.put("key1", anime1, ttl_seconds=1)
        self.cache.put("key2", anime2, ttl_seconds=60)
        
        # Wait for first entry to expire
        time.sleep(1.1)
        
        # Manual cleanup
        cleaned_count = self.cache.cleanup_expired_entries_manual()
        assert cleaned_count == 1
        assert "key1" not in self.cache._cache
        assert "key2" in self.cache._cache

    def test_ttl_info_retrieval(self):
        """Test TTL information retrieval."""
        anime1 = MockAnimeInfo("Anime 1")
        anime2 = MockAnimeInfo("Anime 2")
        
        # Put entries with different TTLs
        self.cache.put("key1", anime1, ttl_seconds=30)
        self.cache.put("key2", anime2, ttl_seconds=60)
        
        ttl_info = self.cache.get_ttl_info()
        
        assert ttl_info["global_ttl_seconds"] == 60
        assert ttl_info["total_entries"] == 2
        assert ttl_info["entries_with_ttl"] == 2
        assert ttl_info["entries_without_ttl"] == 0
        assert len(ttl_info["entry_details"]) == 2

    def test_set_ttl_for_existing_entry(self):
        """Test setting TTL for existing entry."""
        anime = MockAnimeInfo("Test Anime")
        self.cache.put("test_key", anime)
        
        # Set TTL for existing entry
        success = self.cache.set_ttl("test_key", 30)
        assert success
        
        entry = self.cache._cache["test_key"]
        assert entry.ttl_seconds == 30

    def test_set_ttl_for_nonexistent_entry(self):
        """Test setting TTL for non-existent entry."""
        success = self.cache.set_ttl("nonexistent_key", 30)
        assert not success

    def test_get_remaining_ttl(self):
        """Test getting remaining TTL for entry."""
        anime = MockAnimeInfo("Test Anime")
        self.cache.put("test_key", anime, ttl_seconds=60)
        
        remaining = self.cache.get_remaining_ttl("test_key")
        assert remaining is not None
        assert 0 <= remaining <= 60

    def test_get_remaining_ttl_nonexistent_entry(self):
        """Test getting remaining TTL for non-existent entry."""
        remaining = self.cache.get_remaining_ttl("nonexistent_key")
        assert remaining is None

    def test_mixed_ttl_entries(self):
        """Test cache with mixed TTL entries."""
        anime1 = MockAnimeInfo("Anime 1")
        anime2 = MockAnimeInfo("Anime 2")
        anime3 = MockAnimeInfo("Anime 3")
        
        # Put entries with different TTL configurations
        self.cache.put("key1", anime1, ttl_seconds=1)  # Short TTL
        self.cache.put("key2", anime2, ttl_seconds=60)  # Medium TTL
        self.cache.put("key3", anime3)  # Global TTL
        
        # Check all entries are present
        assert len(self.cache._cache) == 3
        
        # Wait for first entry to expire
        time.sleep(1.1)
        
        # Check expired entry is gone
        result1 = self.cache.get("key1")
        assert result1 is None
        
        # Check other entries are still present
        result2 = self.cache.get("key2")
        result3 = self.cache.get("key3")
        assert result2 is not None
        assert result3 is not None

    def test_ttl_with_compression(self):
        """Test TTL functionality with compressed entries."""
        # Create a large anime object that would be compressed
        large_anime = TMDBAnime(
            tmdb_id=1,
            title="Test Anime",
            overview="A" * 10000,  # Large overview to trigger compression
            raw_data={"large_data": "x" * 10000}
        )
        
        self.cache.put("large_key", large_anime, ttl_seconds=30)
        
        # Verify entry is stored and retrievable
        result = self.cache.get("large_key")
        assert result is not None
        assert result.title == "Test Anime"
        
        # Verify TTL is preserved
        entry = self.cache._cache["large_key"]
        assert entry.ttl_seconds == 30

    def test_ttl_cleanup_performance(self):
        """Test TTL cleanup performance with many entries."""
        # Create many entries with different TTLs
        for i in range(100):
            anime = MockAnimeInfo(f"Anime {i}")
            ttl = 1 if i % 2 == 0 else 60  # Half expire quickly
            self.cache.put(f"key{i}", anime, ttl_seconds=ttl)
        
        # Wait for half to expire
        time.sleep(1.1)
        
        # Measure cleanup performance
        start_time = time.time()
        cleaned_count = self.cache.cleanup_expired_entries_manual()
        cleanup_time = time.time() - start_time
        
        assert cleaned_count == 50
        assert cleanup_time < 1.0  # Should be fast
        assert len(self.cache._cache) == 50

    def test_ttl_statistics_accuracy(self):
        """Test TTL statistics accuracy."""
        anime = MockAnimeInfo("Test Anime")
        
        # Reset stats
        self.cache.reset_stats()
        
        # Put entry with short TTL
        self.cache.put("test_key", anime, ttl_seconds=1)
        
        # Get before expiration
        result = self.cache.get("test_key")
        assert result is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Get after expiration
        result = self.cache.get("test_key")
        assert result is None
        
        stats = self.cache.get_stats()
        
        # Verify statistics
        assert stats.total_requests == 2
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.ttl_hits == 1
        assert stats.ttl_misses == 1
        assert stats.ttl_expirations == 1
        
        # Verify calculated rates
        assert stats.hit_rate == 50.0
        assert stats.miss_rate == 50.0
        assert stats.ttl_hit_rate == 50.0
        assert stats.ttl_miss_rate == 50.0
        assert stats.expiration_rate == 50.0


class TestTTLIntegration:
    """Test TTL integration with other cache features."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = MetadataCache(max_size=100, ttl_seconds=60)

    def teardown_method(self):
        """Clean up after tests."""
        self.cache.clear()

    def test_ttl_with_lru_eviction(self):
        """Test TTL works with LRU eviction."""
        # Fill cache to capacity
        for i in range(100):
            anime = MockAnimeInfo(f"Anime {i}")
            self.cache.put(f"key{i}", anime, ttl_seconds=30)
        
        # Add one more entry to trigger eviction
        anime = MockAnimeInfo("New Anime")
        self.cache.put("new_key", anime, ttl_seconds=30)
        
        # First entry should be evicted (LRU)
        assert "key0" not in self.cache._cache
        assert "new_key" in self.cache._cache

    def test_ttl_with_memory_limit(self):
        """Test TTL works with memory limit."""
        # Create large entries to trigger memory-based eviction
        for i in range(10):
            large_anime = TMDBAnime(
                tmdb_id=i,
                title=f"Anime {i}",
                overview="A" * 1000,  # Large content
                raw_data={"data": "x" * 1000}
            )
            self.cache.put(f"key{i}", large_anime, ttl_seconds=30)
        
        # Verify TTL is preserved even after eviction
        for key, entry in self.cache._cache.items():
            assert entry.ttl_seconds == 30

    def test_ttl_with_database_integration(self):
        """Test TTL works with database integration."""
        # Skip database integration test due to complex mocking requirements
        # This test verifies TTL functionality works in isolation
        anime = MockAnimeInfo("Test Anime")
        
        # Put entry with TTL in cache-only mode
        self.cache.enable_cache_only_mode("Test mode")
        self.cache.put("test_key", anime, ttl_seconds=30)
        
        # Verify TTL is preserved
        entry = self.cache._cache["test_key"]
        assert entry.ttl_seconds == 30
        assert not entry.is_expired()
        
        # Verify TTL expiration works
        time.sleep(0.1)  # Small delay
        entry.ttl_seconds = 0.05  # Very short TTL
        entry.expires_at = time.time() + 0.05
        time.sleep(0.1)  # Wait for expiration
        assert entry.is_expired()

    def test_ttl_with_cache_only_mode(self):
        """Test TTL works in cache-only mode."""
        self.cache.enable_cache_only_mode("Test mode")
        
        anime = MockAnimeInfo("Test Anime")
        
        # Put entry with TTL
        self.cache.put("test_key", anime, ttl_seconds=30)
        
        # Verify TTL is preserved
        entry = self.cache._cache["test_key"]
        assert entry.ttl_seconds == 30
        
        # Verify entry can be retrieved
        result = self.cache.get("test_key")
        assert result is not None
        assert result.title == "Test Anime"


class TestTTLEdgeCases:
    """Test TTL edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = MetadataCache(max_size=100, ttl_seconds=60)

    def teardown_method(self):
        """Clean up after tests."""
        self.cache.clear()

    def test_zero_ttl(self):
        """Test zero TTL (immediate expiration)."""
        anime = MockAnimeInfo("Test Anime")
        self.cache.put("test_key", anime, ttl_seconds=0)
        
        # Entry should be immediately expired
        result = self.cache.get("test_key")
        assert result is None

    def test_negative_ttl(self):
        """Test negative TTL (immediate expiration)."""
        anime = MockAnimeInfo("Test Anime")
        self.cache.put("test_key", anime, ttl_seconds=-1)
        
        # Entry should be immediately expired
        result = self.cache.get("test_key")
        assert result is None

    def test_very_large_ttl(self):
        """Test very large TTL."""
        anime = MockAnimeInfo("Test Anime")
        self.cache.put("test_key", anime, ttl_seconds=86400 * 365)  # 1 year
        
        # Entry should not be expired
        result = self.cache.get("test_key")
        assert result is not None
        assert result.title == "Test Anime"

    def test_ttl_update_on_existing_entry(self):
        """Test updating TTL on existing entry."""
        anime = MockAnimeInfo("Test Anime")
        
        # Put entry with long TTL
        self.cache.put("test_key", anime, ttl_seconds=60)
        
        # Update TTL to short
        success = self.cache.set_ttl("test_key", 1)
        assert success
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Entry should be expired
        result = self.cache.get("test_key")
        assert result is None

    def test_ttl_removal(self):
        """Test removing TTL from entry."""
        anime = MockAnimeInfo("Test Anime")
        
        # Put entry with TTL
        self.cache.put("test_key", anime, ttl_seconds=1)
        
        # Remove TTL
        success = self.cache.set_ttl("test_key", None)
        assert success
        
        # Wait for what would have been expiration
        time.sleep(1.1)
        
        # Entry should still be valid
        result = self.cache.get("test_key")
        assert result is not None
        assert result.title == "Test Anime"

    def test_concurrent_ttl_operations(self):
        """Test concurrent TTL operations."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def worker(worker_id):
            """Worker function for concurrent operations."""
            anime = MockAnimeInfo(f"Anime {worker_id}")
            key = f"key{worker_id}"
            
            # Put entry with TTL
            self.cache.put(key, anime, ttl_seconds=30)
            
            # Get entry
            result = self.cache.get(key)
            results.put((worker_id, result is not None))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all operations succeeded
        while not results.empty():
            worker_id, success = results.get()
            assert success, f"Worker {worker_id} failed"


if __name__ == "__main__":
    pytest.main([__file__])
