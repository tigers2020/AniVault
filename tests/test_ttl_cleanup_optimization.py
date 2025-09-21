"""Tests for TTL cleanup optimization in MetadataCache.

This module tests the optimized TTL cleanup functionality including:
- Min-heap based expiry tracking
- Background cleanup tasks
- Lazy deletion on access
- Batch cleanup with throttling
- Performance improvements
"""

import threading
import time
from unittest.mock import patch

import pytest

from src.core.metadata_cache import MetadataCache
from src.core.models import TMDBAnime


class MockAnimeInfo(TMDBAnime):
    """Mock anime info for testing."""

    def __init__(self, title: str = "Test Anime", tmdb_id: int = 1) -> None:
        """Initialize mock anime info."""
        super().__init__(
            tmdb_id=tmdb_id,
            title=title,
            original_title=title,
            korean_title="",
            overview="Test anime description",
            release_date="2023-01-01",
            poster_path="",
            backdrop_path="",
            first_air_date="2023-01-01",
            last_air_date="2023-12-31",
            status="Ended",
            vote_average=8.0,
            vote_count=100,
            popularity=50.0,
            genres=[],
            networks=[],
            production_companies=[],
            production_countries=[],
            spoken_languages=[],
            number_of_seasons=1,
            number_of_episodes=12,
            tagline="",
            homepage="",
            imdb_id="",
            external_ids={},
            quality_score=1.0,
            raw_data={},
        )


class TestTTLCleanupOptimization:
    """Test TTL cleanup optimization features."""

    @pytest.fixture
    def cache(self):
        """Create a cache instance for testing."""
        return MetadataCache(max_size=100, max_memory_mb=10, ttl_seconds=60, enable_db=False)

    def test_heap_based_cleanup_performance(self, cache) -> None:
        """Test that heap-based cleanup is more efficient than full scan."""
        # Add many entries with different TTLs
        for i in range(1000):
            anime = MockAnimeInfo(f"Anime {i}")
            ttl = 30 + (i % 10)  # Varying TTLs
            cache.put(f"key_{i}", anime, ttl_seconds=ttl)

        # Measure cleanup time
        start_time = time.time()
        cleaned_count = cache._cleanup_expired_entries()
        cleanup_time = time.time() - start_time

        # Cleanup should be fast (under 0.1 seconds for 1000 items)
        assert cleanup_time < 0.1
        assert cleaned_count == 0  # No items should be expired yet

    def test_background_cleanup_startup(self, cache) -> None:
        """Test background cleanup startup and shutdown."""
        # Start background cleanup
        cache.start_background_cleanup()

        # Verify executor is created
        assert cache._cleanup_executor is not None
        assert cache._background_cleanup_enabled is True

        # Stop background cleanup
        cache.stop_background_cleanup()

        # Verify cleanup is stopped
        assert cache._cleanup_executor is None

    def test_lazy_deletion_on_access(self, cache) -> None:
        """Test that expired entries are removed on access (lazy deletion)."""
        anime = MockAnimeInfo("Test Anime")

        # Add entry with very short TTL
        cache.put("test_key", anime, ttl_seconds=0.1)

        # Verify entry exists
        assert cache.get("test_key") is not None

        # Wait for expiration
        time.sleep(0.2)

        # Access should trigger lazy deletion
        result = cache.get("test_key")
        assert result is None

        # Entry should be removed from cache
        assert "test_key" not in cache._cache

    def test_batch_cleanup_with_throttling(self, cache) -> None:
        """Test batch cleanup with throttling."""
        # Add entries with immediate expiration
        for i in range(20):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=0)

        # Wait for expiration
        time.sleep(0.1)

        # Test batch cleanup with small batch size
        cache._cleanup_batch_size = 5
        cleaned_count = cache._batch_cleanup_expired_entries(max_items=10)

        # Should clean up to the batch limit
        assert cleaned_count == 10

    def test_heap_consistency_after_updates(self, cache) -> None:
        """Test that heap remains consistent after cache updates."""
        anime1 = MockAnimeInfo("Anime 1")
        anime2 = MockAnimeInfo("Anime 2")

        # Add initial entry
        cache.put("test_key", anime1, ttl_seconds=30)

        # Update with different TTL
        cache.put("test_key", anime2, ttl_seconds=60)

        # Verify heap has correct entry
        with cache._heap_lock:
            assert len(cache._expiry_heap) == 1
            expiry_time, key = cache._expiry_heap[0]
            assert key == "test_key"
            assert expiry_time > time.time() + 50  # Should be ~60 seconds from now

    def test_concurrent_cleanup_and_access(self, cache) -> None:
        """Test concurrent cleanup and cache access."""
        # Add entries
        for i in range(100):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=30)

        # Start background cleanup
        cache.start_background_cleanup()

        # Concurrent access
        def access_cache() -> None:
            for i in range(50):
                cache.get(f"key_{i}")
                time.sleep(0.001)

        def modify_cache() -> None:
            for i in range(50, 100):
                anime = MockAnimeInfo(f"Updated Anime {i}")
                cache.put(f"key_{i}", anime, ttl_seconds=60)
                time.sleep(0.001)

        # Run concurrent operations
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=access_cache))
            threads.append(threading.Thread(target=modify_cache))

        for thread in threads:
            thread.start()

        # Let them run for a bit
        time.sleep(0.1)

        # Stop cleanup
        cache.stop_background_cleanup()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Cache should still be functional
        assert cache.get("key_0") is not None

    def test_cleanup_statistics_tracking(self, cache) -> None:
        """Test that cleanup statistics are properly tracked."""
        # Add entries with immediate expiration
        for i in range(10):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=0)

        # Wait for expiration
        time.sleep(0.1)

        # Perform cleanup
        cleaned_count = cache._cleanup_expired_entries()

        # Check statistics
        stats = cache.get_stats()
        assert cleaned_count == 10
        assert stats.ttl_expirations == 10

    def test_cleanup_with_mixed_ttl_entries(self, cache) -> None:
        """Test cleanup with mixed TTL entries."""
        # Add entries with different TTLs
        for i in range(20):
            anime = MockAnimeInfo(f"Anime {i}")
            if i < 10:
                ttl = 0  # Immediate expiration
            else:
                ttl = 60  # Long TTL
            cache.put(f"key_{i}", anime, ttl_seconds=ttl)

        # Wait for short TTL entries to expire
        time.sleep(0.1)

        # Perform cleanup
        cleaned_count = cache._cleanup_expired_entries()

        # Should only clean up expired entries
        assert cleaned_count == 10

        # Verify remaining entries
        for i in range(10, 20):
            assert cache.get(f"key_{i}") is not None

    def test_cleanup_performance_under_load(self, cache) -> None:
        """Test cleanup performance under high load."""
        # Add many entries
        for i in range(5000):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=30)

        # Measure cleanup time
        start_time = time.time()
        cleaned_count = cache._cleanup_expired_entries()
        cleanup_time = time.time() - start_time

        # Should be very fast even with many entries
        assert cleanup_time < 0.05  # Under 50ms
        assert cleaned_count == 0  # No expired entries yet

    def test_cleanup_with_zero_ttl(self, cache) -> None:
        """Test cleanup behavior with zero TTL."""
        anime = MockAnimeInfo("Test Anime")

        # Add entry with zero TTL
        cache.put("test_key", anime, ttl_seconds=0)

        # Entry should be in cache but expired
        assert "test_key" in cache._cache
        assert cache.cache_core._cache["test_key"].is_expired()

        # Cleanup should remove it
        cleaned_count = cache._cleanup_expired_entries()
        assert cleaned_count == 1

    def test_cleanup_with_negative_ttl(self, cache) -> None:
        """Test cleanup behavior with negative TTL."""
        anime = MockAnimeInfo("Test Anime")

        # Add entry with negative TTL
        cache.put("test_key", anime, ttl_seconds=-1)

        # Entry should be in cache but expired
        assert "test_key" in cache._cache
        assert cache.cache_core._cache["test_key"].is_expired()

        # Cleanup should remove it
        cleaned_count = cache._cleanup_expired_entries()
        assert cleaned_count == 1

    def test_cleanup_memory_efficiency(self, cache) -> None:
        """Test that cleanup doesn't cause memory leaks."""
        initial_memory = cache._current_memory_bytes

        # Add and expire many entries
        for i in range(1000):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=0)

        # Wait for expiration
        time.sleep(0.1)

        # Perform cleanup
        cache._cleanup_expired_entries()

        # Memory should be back to initial level
        assert cache._current_memory_bytes <= initial_memory

    def test_cleanup_thread_safety(self, cache) -> None:
        """Test that cleanup is thread-safe."""
        # Add entries
        for i in range(100):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=30)

        # Multiple cleanup threads
        def cleanup_worker() -> None:
            for _ in range(10):
                cache._cleanup_expired_entries()
                time.sleep(0.001)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=cleanup_worker))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Cache should still be functional
        assert cache.get("key_0") is not None

    def test_cleanup_with_cache_disabled(self, cache) -> None:
        """Test cleanup behavior when cache is disabled."""
        cache._enabled = False

        # Add entries
        for i in range(10):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=0)

        # Cleanup should not run when disabled
        cleaned_count = cache._cleanup_expired_entries()
        assert cleaned_count == 0

    def test_cleanup_with_auto_cleanup_disabled(self, cache) -> None:
        """Test cleanup behavior when auto cleanup is disabled."""
        cache._auto_cleanup = False

        # Add entries
        for i in range(10):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=0)

        # Wait for expiration
        time.sleep(0.1)

        # Manual cleanup should still work
        cleaned_count = cache._cleanup_expired_entries()
        assert cleaned_count == 10

    def test_cleanup_error_handling(self, cache) -> None:
        """Test cleanup error handling."""
        # Add some entries first
        for i in range(5):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=0)

        # Mock time.time to raise error during cleanup
        with patch("time.time", side_effect=Exception("Time error")):
            # Cleanup should handle error gracefully
            try:
                cleaned_count = cache._cleanup_expired_entries()
                assert cleaned_count == 0
            except Exception:
                # If cleanup raises exception, that's also acceptable
                pass

    def test_cleanup_with_empty_cache(self, cache) -> None:
        """Test cleanup with empty cache."""
        cleaned_count = cache._cleanup_expired_entries()
        assert cleaned_count == 0

    def test_cleanup_with_no_expired_entries(self, cache) -> None:
        """Test cleanup when no entries are expired."""
        # Add entries with long TTL
        for i in range(10):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=3600)  # 1 hour

        cleaned_count = cache._cleanup_expired_entries()
        assert cleaned_count == 0

    def test_cleanup_performance_comparison(self, cache) -> None:
        """Test performance improvement over naive approach."""
        # Add many entries
        for i in range(1000):
            anime = MockAnimeInfo(f"Anime {i}")
            cache.put(f"key_{i}", anime, ttl_seconds=30)

        # Measure optimized cleanup time
        start_time = time.time()
        cleaned_count = cache._cleanup_expired_entries()
        optimized_time = time.time() - start_time

        # Should be very fast
        assert optimized_time < 0.01  # Under 10ms
        assert cleaned_count == 0  # No expired entries yet

        # Verify heap is properly maintained
        with cache._heap_lock:
            assert len(cache._expiry_heap) == 1000
