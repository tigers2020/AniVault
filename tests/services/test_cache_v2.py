"""Tests for the Cache v2 system."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from anivault.services.cache_v2 import CacheEntry, JSONCacheV2
from anivault.shared.errors import DomainError, InfrastructureError

# Check if orjson is available
try:
    import orjson

    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False

# Skip all tests if orjson is not installed
pytestmark = pytest.mark.skipif(not ORJSON_AVAILABLE, reason="orjson not installed")


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def cache_v2(temp_cache_dir):
    """Create a JSONCacheV2 instance for testing."""
    return JSONCacheV2(temp_cache_dir)


class TestCacheEntry:
    """Test the CacheEntry Pydantic model."""

    def test_cache_entry_creation(self):
        """Test creating a CacheEntry with valid data."""
        entry = CacheEntry(
            data={"title": "Test Anime", "year": 2023},
            created_at="2023-01-01T00:00:00+00:00",
            cache_type="search",
            key_hash="abc123",
        )

        assert entry.data == {"title": "Test Anime", "year": 2023}
        assert entry.created_at == "2023-01-01T00:00:00+00:00"
        assert entry.cache_type == "search"
        assert entry.key_hash == "abc123"
        assert entry.expires_at is None

    def test_cache_entry_with_expiration(self):
        """Test creating a CacheEntry with expiration."""
        entry = CacheEntry(
            data={"title": "Test Anime"},
            created_at="2023-01-01T00:00:00+00:00",
            expires_at="2023-01-02T00:00:00+00:00",
            cache_type="search",
            key_hash="abc123",
        )

        assert entry.expires_at == "2023-01-02T00:00:00+00:00"

    def test_cache_entry_validation(self):
        """Test CacheEntry validation with invalid data."""
        with pytest.raises(ValueError):
            CacheEntry(
                data="invalid",  # Should be dict
                created_at="2023-01-01T00:00:00+00:00",
                cache_type="search",
                key_hash="abc123",
            )


class TestJSONCacheV2Initialization:
    """Test JSONCacheV2 initialization."""

    def test_initialization_with_path(self, temp_cache_dir):
        """Test initialization with Path object."""
        cache = JSONCacheV2(temp_cache_dir)

        assert cache.cache_dir == temp_cache_dir
        assert cache.search_dir == temp_cache_dir / "search"
        assert cache.details_dir == temp_cache_dir / "details"
        assert cache.search_dir.exists()
        assert cache.details_dir.exists()

    def test_initialization_with_string(self, temp_cache_dir):
        """Test initialization with string path."""
        cache = JSONCacheV2(str(temp_cache_dir))

        assert cache.cache_dir == temp_cache_dir
        assert cache.search_dir == temp_cache_dir / "search"
        assert cache.details_dir == temp_cache_dir / "details"

    def test_initialization_creates_directories(self, temp_cache_dir):
        """Test that initialization creates necessary directories."""
        cache_dir = temp_cache_dir / "new_cache"
        cache = JSONCacheV2(cache_dir)

        assert cache_dir.exists()
        assert (cache_dir / "search").exists()
        assert (cache_dir / "details").exists()

    def test_initialization_without_orjson(self):
        """Test initialization fails without orjson."""
        with patch("anivault.services.cache_v2.orjson", None):
            with pytest.raises(
                InfrastructureError, match="orjson library is not installed"
            ):
                JSONCacheV2("/tmp/test")


class TestJSONCacheV2FilePathGeneration:
    """Test file path generation methods."""

    def test_generate_file_path_search(self, cache_v2):
        """Test generating file path for search cache."""
        path = cache_v2._generate_file_path("test key", "search")

        assert path.parent == cache_v2.search_dir
        assert path.suffix == ".json"
        assert len(path.stem) == 64  # SHA-256 hash length

    def test_generate_file_path_details(self, cache_v2):
        """Test generating file path for details cache."""
        path = cache_v2._generate_file_path("test key", "details")

        assert path.parent == cache_v2.details_dir
        assert path.suffix == ".json"
        assert len(path.stem) == 64  # SHA-256 hash length

    def test_generate_file_path_invalid_type(self, cache_v2):
        """Test generating file path with invalid cache type."""
        with pytest.raises(DomainError, match="Invalid cache_type"):
            cache_v2._generate_file_path("test key", "invalid")

    def test_generate_file_path_key_normalization(self, cache_v2):
        """Test that keys are normalized before hashing."""
        path1 = cache_v2._generate_file_path("Test Key", "search")
        path2 = cache_v2._generate_file_path("test key", "search")
        path3 = cache_v2._generate_file_path("  TEST KEY  ", "search")

        assert path1 == path2 == path3


class TestJSONCacheV2Set:
    """Test the set method."""

    def test_set_basic_data(self, cache_v2):
        """Test setting basic data without TTL."""
        data = {"title": "Test Anime", "year": 2023}
        cache_v2.set("test_key", data, "search")

        # Verify file was created
        cache_file = cache_v2._generate_file_path("test_key", "search")
        assert cache_file.exists()

    def test_set_with_ttl(self, cache_v2):
        """Test setting data with TTL."""
        data = {"title": "Test Anime"}
        cache_v2.set("test_key", data, "search", ttl_seconds=3600)

        # Verify file was created
        cache_file = cache_v2._generate_file_path("test_key", "search")
        assert cache_file.exists()

    def test_set_different_cache_types(self, cache_v2):
        """Test setting data in different cache types."""
        data = {"title": "Test Anime"}

        cache_v2.set("search_key", data, "search")
        cache_v2.set("details_key", data, "details")

        search_file = cache_v2._generate_file_path("search_key", "search")
        details_file = cache_v2._generate_file_path("details_key", "details")

        assert search_file.exists()
        assert details_file.exists()

    def test_set_invalid_cache_type(self, cache_v2):
        """Test setting data with invalid cache type."""
        data = {"title": "Test Anime"}

        with pytest.raises(DomainError, match="Invalid cache_type"):
            cache_v2.set("test_key", data, "invalid")


class TestJSONCacheV2Get:
    """Test the get method."""

    def test_get_cache_hit(self, cache_v2):
        """Test getting data from cache (hit)."""
        data = {"title": "Test Anime", "year": 2023}
        cache_v2.set("test_key", data, "search")

        result = cache_v2.get("test_key", "search")
        assert result == data

    def test_get_cache_miss(self, cache_v2):
        """Test getting data from cache (miss)."""
        result = cache_v2.get("nonexistent_key", "search")
        assert result is None

    def test_get_different_cache_types(self, cache_v2):
        """Test getting data from different cache types."""
        search_data = {"title": "Search Result"}
        details_data = {"title": "Details Result"}

        cache_v2.set("test_key", search_data, "search")
        cache_v2.set("test_key", details_data, "details")

        search_result = cache_v2.get("test_key", "search")
        details_result = cache_v2.get("test_key", "details")

        assert search_result == search_data
        assert details_result == details_data

    def test_get_expired_entry(self, cache_v2):
        """Test getting expired cache entry."""
        data = {"title": "Test Anime"}
        # Set with very short TTL
        cache_v2.set("test_key", data, "search", ttl_seconds=0)

        # Wait a moment and try to get
        import time

        time.sleep(0.1)

        result = cache_v2.get("test_key", "search")
        assert result is None

    def test_get_invalid_cache_type(self, cache_v2):
        """Test getting data with invalid cache type."""
        with pytest.raises(DomainError, match="Invalid cache_type"):
            cache_v2.get("test_key", "invalid")

    def test_get_corrupted_file(self, cache_v2):
        """Test getting data from corrupted cache file."""
        # Create a corrupted cache file
        cache_file = cache_v2._generate_file_path("test_key", "search")
        cache_file.write_text("invalid json content")

        result = cache_v2.get("test_key", "search")
        assert result is None
        # File should be deleted
        assert not cache_file.exists()


class TestJSONCacheV2Delete:
    """Test the delete method."""

    def test_delete_existing_entry(self, cache_v2):
        """Test deleting an existing cache entry."""
        data = {"title": "Test Anime"}
        cache_v2.set("test_key", data, "search")

        result = cache_v2.delete("test_key", "search")
        assert result is True

        # Verify entry is gone
        get_result = cache_v2.get("test_key", "search")
        assert get_result is None

    def test_delete_nonexistent_entry(self, cache_v2):
        """Test deleting a nonexistent cache entry."""
        result = cache_v2.delete("nonexistent_key", "search")
        assert result is False

    def test_delete_invalid_cache_type(self, cache_v2):
        """Test deleting with invalid cache type."""
        with pytest.raises(DomainError, match="Invalid cache_type"):
            cache_v2.delete("test_key", "invalid")


class TestJSONCacheV2Clear:
    """Test the clear method."""

    def test_clear_all(self, cache_v2):
        """Test clearing all cache entries."""
        # Add some entries
        cache_v2.set("search_key", {"data": "search"}, "search")
        cache_v2.set("details_key", {"data": "details"}, "details")

        deleted_count = cache_v2.clear()
        assert deleted_count == 2

        # Verify entries are gone
        assert cache_v2.get("search_key", "search") is None
        assert cache_v2.get("details_key", "details") is None

    def test_clear_search_only(self, cache_v2):
        """Test clearing only search cache entries."""
        # Add entries to both cache types
        cache_v2.set("search_key", {"data": "search"}, "search")
        cache_v2.set("details_key", {"data": "details"}, "details")

        deleted_count = cache_v2.clear("search")
        assert deleted_count == 1

        # Verify only search entry is gone
        assert cache_v2.get("search_key", "search") is None
        assert cache_v2.get("details_key", "details") is not None

    def test_clear_details_only(self, cache_v2):
        """Test clearing only details cache entries."""
        # Add entries to both cache types
        cache_v2.set("search_key", {"data": "search"}, "search")
        cache_v2.set("details_key", {"data": "details"}, "details")

        deleted_count = cache_v2.clear("details")
        assert deleted_count == 1

        # Verify only details entry is gone
        assert cache_v2.get("search_key", "search") is not None
        assert cache_v2.get("details_key", "details") is None

    def test_clear_invalid_cache_type(self, cache_v2):
        """Test clearing with invalid cache type."""
        with pytest.raises(DomainError, match="Invalid cache_type"):
            cache_v2.clear("invalid")


class TestJSONCacheV2GetCacheInfo:
    """Test the get_cache_info method."""

    def test_get_cache_info_empty(self, cache_v2):
        """Test getting cache info for empty cache."""
        info = cache_v2.get_cache_info()

        assert info["total_files"] == 0
        assert info["valid_entries"] == 0
        assert info["expired_entries"] == 0
        assert info["total_size_bytes"] == 0
        assert "cache_directory" in info

    def test_get_cache_info_with_entries(self, cache_v2):
        """Test getting cache info with entries."""
        # Add some entries
        cache_v2.set("search_key", {"data": "search"}, "search")
        cache_v2.set("details_key", {"data": "details"}, "details")

        info = cache_v2.get_cache_info()

        assert info["total_files"] == 2
        assert info["valid_entries"] == 2
        assert info["expired_entries"] == 0
        assert info["total_size_bytes"] > 0

    def test_get_cache_info_specific_type(self, cache_v2):
        """Test getting cache info for specific cache type."""
        # Add entries to both types
        cache_v2.set("search_key", {"data": "search"}, "search")
        cache_v2.set("details_key", {"data": "details"}, "details")

        search_info = cache_v2.get_cache_info("search")
        details_info = cache_v2.get_cache_info("details")

        assert search_info["total_files"] == 1
        assert search_info["cache_type"] == "search"
        assert details_info["total_files"] == 1
        assert details_info["cache_type"] == "details"

    def test_get_cache_info_invalid_type(self, cache_v2):
        """Test getting cache info with invalid cache type."""
        with pytest.raises(DomainError, match="Invalid cache_type"):
            cache_v2.get_cache_info("invalid")


class TestJSONCacheV2PurgeExpired:
    """Test the purge_expired method."""

    def test_purge_expired_no_expired(self, cache_v2):
        """Test purging when no expired entries exist."""
        # Add non-expired entries
        cache_v2.set("search_key", {"data": "search"}, "search")
        cache_v2.set("details_key", {"data": "details"}, "details")

        purged_count = cache_v2.purge_expired()
        assert purged_count == 0

    def test_purge_expired_with_expired(self, cache_v2):
        """Test purging expired entries."""
        # Add expired entries
        cache_v2.set("expired_key", {"data": "expired"}, "search", ttl_seconds=0)
        cache_v2.set("valid_key", {"data": "valid"}, "search", ttl_seconds=3600)

        # Wait a moment for expiration
        import time

        time.sleep(0.1)

        purged_count = cache_v2.purge_expired()
        assert purged_count == 1

        # Verify expired entry is gone, valid entry remains
        assert cache_v2.get("expired_key", "search") is None
        assert cache_v2.get("valid_key", "search") is not None

    def test_purge_expired_specific_type(self, cache_v2):
        """Test purging expired entries for specific cache type."""
        # Add expired entries to both types
        cache_v2.set("expired_search", {"data": "expired"}, "search", ttl_seconds=0)
        cache_v2.set("expired_details", {"data": "expired"}, "details", ttl_seconds=0)

        # Wait for expiration
        import time

        time.sleep(0.1)

        purged_count = cache_v2.purge_expired("search")
        assert purged_count == 1

        # Verify only search expired entry is gone
        assert cache_v2.get("expired_search", "search") is None
        assert cache_v2.get("expired_details", "details") is None

    def test_purge_expired_invalid_type(self, cache_v2):
        """Test purging with invalid cache type."""
        with pytest.raises(DomainError, match="Invalid cache_type"):
            cache_v2.purge_expired("invalid")


class TestJSONCacheV2Integration:
    """Integration tests for the complete cache system."""

    def test_full_workflow(self, cache_v2):
        """Test complete cache workflow."""
        # Set data
        search_data = {"results": [{"title": "Anime 1"}, {"title": "Anime 2"}]}
        details_data = {"title": "Anime 1", "overview": "Great anime"}

        cache_v2.set("search:attack on titan", search_data, "search", ttl_seconds=3600)
        cache_v2.set("details:12345", details_data, "details", ttl_seconds=7200)

        # Get data
        retrieved_search = cache_v2.get("search:attack on titan", "search")
        retrieved_details = cache_v2.get("details:12345", "details")

        assert retrieved_search == search_data
        assert retrieved_details == details_data

        # Get cache info
        info = cache_v2.get_cache_info()
        assert info["total_files"] == 2
        assert info["valid_entries"] == 2

        # Delete one entry
        deleted = cache_v2.delete("search:attack on titan", "search")
        assert deleted is True

        # Verify deletion
        assert cache_v2.get("search:attack on titan", "search") is None
        assert cache_v2.get("details:12345", "details") is not None

    def test_key_normalization_consistency(self, cache_v2):
        """Test that key normalization is consistent across operations."""
        data = {"title": "Test Anime"}

        # Set with different key formats
        cache_v2.set("  Test Key  ", data, "search")

        # Get with different key formats - should all work
        assert cache_v2.get("test key", "search") == data
        assert cache_v2.get("TEST KEY", "search") == data
        assert cache_v2.get("  test key  ", "search") == data

        # Delete with different key format
        deleted = cache_v2.delete("Test Key", "search")
        assert deleted is True

        # Verify deletion
        assert cache_v2.get("test key", "search") is None
