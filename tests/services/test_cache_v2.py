"""Tests for cache v2 system."""

import tempfile
import time
from pathlib import Path

import pytest

from anivault.services.cache_v2 import CacheEntry, CacheV2


class TestCacheV2:
    """Test cases for CacheV2."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def cache_v2(self, temp_cache_dir):
        """Create a CacheV2 instance."""
        return CacheV2(cache_dir=temp_cache_dir, default_ttl=3600)

    def test_set_and_get(self, cache_v2):
        """Test basic set and get operations."""
        cache_v2.set("test_key", "test_value")
        result = cache_v2.get("test_key")
        assert result == "test_value"

    def test_get_nonexistent(self, cache_v2):
        """Test getting non-existent key."""
        result = cache_v2.get("nonexistent_key")
        assert result is None

    def test_set_with_ttl(self, cache_v2):
        """Test setting with custom TTL."""
        cache_v2.set("test_key", "test_value", ttl=1)

        # Should be available immediately
        result = cache_v2.get("test_key")
        assert result == "test_value"

        # Wait for expiration
        time.sleep(1.1)
        result = cache_v2.get("test_key")
        assert result is None

    def test_set_with_tags(self, cache_v2):
        """Test setting with tags."""
        cache_v2.set("test_key", "test_value", tags=["anime", "tv"])

        # Check entry has tags
        entry = cache_v2.entries["test_key"]
        assert entry.tags == ["anime", "tv"]

    def test_delete(self, cache_v2):
        """Test deleting entries."""
        cache_v2.set("test_key", "test_value")
        assert cache_v2.delete("test_key") is True
        assert cache_v2.get("test_key") is None

        # Try deleting non-existent key
        assert cache_v2.delete("nonexistent_key") is False

    def test_clear(self, cache_v2):
        """Test clearing all entries."""
        cache_v2.set("key1", "value1")
        cache_v2.set("key2", "value2")

        cache_v2.clear()
        assert len(cache_v2.entries) == 0

    def test_clear_expired(self, cache_v2):
        """Test clearing expired entries."""
        # Set entry with short TTL
        cache_v2.set("expired_key", "value", ttl=0.1)

        # Wait for expiration
        time.sleep(0.2)

        # Clear expired entries
        cleared_count = cache_v2.clear_expired()
        assert cleared_count == 1
        assert "expired_key" not in cache_v2.entries

    def test_clear_by_tag(self, cache_v2):
        """Test clearing entries by tag."""
        cache_v2.set("key1", "value1", tags=["anime"])
        cache_v2.set("key2", "value2", tags=["movie"])
        cache_v2.set("key3", "value3", tags=["anime", "tv"])

        cleared_count = cache_v2.clear_by_tag("anime")
        assert cleared_count == 2
        assert "key1" not in cache_v2.entries
        assert "key3" not in cache_v2.entries
        assert "key2" in cache_v2.entries

    def test_get_entries_by_tag(self, cache_v2):
        """Test getting entries by tag."""
        cache_v2.set("key1", "value1", tags=["anime"])
        cache_v2.set("key2", "value2", tags=["movie"])
        cache_v2.set("key3", "value3", tags=["anime", "tv"])

        anime_entries = cache_v2.get_entries_by_tag("anime")
        assert len(anime_entries) == 2

        movie_entries = cache_v2.get_entries_by_tag("movie")
        assert len(movie_entries) == 1

    def test_get_stats(self, cache_v2):
        """Test statistics retrieval."""
        # Add some entries
        cache_v2.set("key1", "value1")
        cache_v2.set("key2", "value2")

        # Access entries
        cache_v2.get("key1")
        cache_v2.get("key1")  # Hit
        cache_v2.get("nonexistent")  # Miss

        stats = cache_v2.get_stats()

        assert stats["entries_count"] == 2
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["sets"] == 2
        assert stats["hit_rate"] == 2 / 3

    def test_save_and_load_cache(self, temp_cache_dir):
        """Test saving and loading cache."""
        # Create cache and add entries
        cache_v2 = CacheV2(cache_dir=temp_cache_dir)
        cache_v2.set("key1", "value1", tags=["test"])
        cache_v2.set("key2", "value2", ttl=3600)

        # Save cache
        cache_v2.save_cache()

        # Create new cache instance and load
        new_cache = CacheV2(cache_dir=temp_cache_dir)

        # Check entries were loaded
        assert new_cache.get("key1") == "value1"
        assert new_cache.get("key2") == "value2"

        # Check tags were preserved
        entry = new_cache.entries["key1"]
        assert entry.tags == ["test"]

    def test_context_manager(self, temp_cache_dir):
        """Test context manager functionality."""
        with CacheV2(cache_dir=temp_cache_dir) as cache:
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"

        # Cache should be saved after context exit
        new_cache = CacheV2(cache_dir=temp_cache_dir)
        assert new_cache.get("key1") == "value1"

    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=time.time(),
            expires_at=time.time() + 1.0,
        )

        # Should not be expired immediately
        assert not entry.is_expired()

        # Wait for expiration
        time.sleep(1.1)
        assert entry.is_expired()

    def test_cache_entry_touch(self):
        """Test cache entry touch functionality."""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=time.time(),
            expires_at=None,
        )

        initial_count = entry.access_count
        entry.touch()

        assert entry.access_count == initial_count + 1
        assert entry.last_accessed is not None
