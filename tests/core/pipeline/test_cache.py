"""Unit tests for CacheV1 class.

This module contains comprehensive tests for the file-based JSON cache
implementation with TTL support.
"""

import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from anivault.core.pipeline.cache import CacheV1


class TestCacheV1:
    """Test cases for CacheV1 class."""

    def test_init_creates_directory(self) -> None:
        """Test that CacheV1 creates the cache directory on initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "test_cache"
            cache = CacheV1(cache_dir)

            assert cache.cache_dir == cache_dir
            assert cache_dir.exists()
            assert cache_dir.is_dir()

    def test_init_existing_directory(self) -> None:
        """Test that CacheV1 works with existing directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_dir = Path(temp_dir) / "existing_cache"
            cache_dir.mkdir()

            cache = CacheV1(cache_dir)
            assert cache.cache_dir == cache_dir
            assert cache_dir.exists()

    def test_generate_key_consistency(self) -> None:
        """Test that _generate_key produces consistent results."""
        cache = CacheV1(Path("/tmp/test"))

        file_path = "/path/to/test/file.mp4"
        mtime = 1234567890.123

        key1 = cache._generate_key(file_path, mtime)
        key2 = cache._generate_key(file_path, mtime)

        assert key1 == key2
        assert len(key1) == 64  # SHA256 hash length
        assert isinstance(key1, str)

    def test_generate_key_uniqueness(self) -> None:
        """Test that _generate_key produces different keys for different inputs."""
        cache = CacheV1(Path("/tmp/test"))

        # Different file paths
        key1 = cache._generate_key("/path/to/file1.mp4", 1234567890.0)
        key2 = cache._generate_key("/path/to/file2.mp4", 1234567890.0)
        assert key1 != key2

        # Same file path, different modification times
        key3 = cache._generate_key("/path/to/file1.mp4", 1234567890.0)
        key4 = cache._generate_key("/path/to/file1.mp4", 1234567891.0)
        assert key3 != key4

    def test_set_and_get_success(self) -> None:
        """Test successful set and get operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            key = "test_key"
            data = {"title": "Test Anime", "episode": 1}
            ttl = 3600  # 1 hour

            # Set data
            cache.set(key, data, ttl)

            # Verify file was created
            cache_file = cache.cache_dir / f"{key}.json"
            assert cache_file.exists()

            # Get data
            retrieved_data = cache.get(key)
            assert retrieved_data == data

    def test_set_creates_valid_json(self) -> None:
        """Test that set creates valid JSON with correct structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            key = "test_key"
            data = {"title": "Test Anime", "episode": 1}
            ttl = 3600

            cache.set(key, data, ttl)

            cache_file = cache.cache_dir / f"{key}.json"
            with open(cache_file, encoding="utf-8") as f:
                payload = json.load(f)

            # Verify structure
            assert "data" in payload
            assert "created_at" in payload
            assert "ttl_seconds" in payload

            assert payload["data"] == data
            assert payload["ttl_seconds"] == ttl
            assert isinstance(payload["created_at"], str)

    def test_get_cache_miss(self) -> None:
        """Test get returns None for non-existent keys."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            result = cache.get("non_existent_key")
            assert result is None

    def test_get_corrupted_json(self) -> None:
        """Test get handles corrupted JSON files gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            key = "corrupted_key"
            cache_file = cache.cache_dir / f"{key}.json"

            # Write invalid JSON
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write("invalid json content")

            result = cache.get(key)
            assert result is None

    def test_get_expired_entry(self) -> None:
        """Test get returns None for expired entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            key = "expired_key"
            data = {"title": "Test Anime"}
            ttl = 1  # 1 second TTL

            # Set data
            cache.set(key, data, ttl)

            # Wait for expiration
            time.sleep(1.1)

            # Should return None due to expiration
            result = cache.get(key)
            assert result is None

    def test_get_valid_entry_before_expiration(self) -> None:
        """Test get returns data for valid, non-expired entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            key = "valid_key"
            data = {"title": "Test Anime", "episode": 1}
            ttl = 3600  # 1 hour TTL

            cache.set(key, data, ttl)

            # Should return data immediately (not expired)
            result = cache.get(key)
            assert result == data

    def test_get_no_ttl_entry(self) -> None:
        """Test get returns data for entries without TTL."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            key = "no_ttl_key"
            data = {"title": "Test Anime"}
            ttl = 0  # No TTL

            cache.set(key, data, ttl)

            result = cache.get(key)
            assert result == data

    def test_clear_removes_all_files(self) -> None:
        """Test clear removes all cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            # Create multiple cache entries
            for i in range(3):
                cache.set(f"key_{i}", {"data": i}, 3600)

            # Verify files exist
            cache_files = list(cache.cache_dir.glob("*.json"))
            assert len(cache_files) == 3

            # Clear cache
            cache.clear()

            # Verify files are removed
            cache_files = list(cache.cache_dir.glob("*.json"))
            assert len(cache_files) == 0

    def test_get_cache_info_empty_cache(self) -> None:
        """Test get_cache_info for empty cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            info = cache.get_cache_info()

            assert info["total_files"] == 0
            assert info["valid_entries"] == 0
            assert info["expired_entries"] == 0
            assert info["total_size_bytes"] == 0
            assert info["cache_directory"] == str(cache.cache_dir)

    def test_get_cache_info_with_entries(self) -> None:
        """Test get_cache_info with various cache entries."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            # Create valid entry
            cache.set("valid_key", {"data": "valid"}, 3600)

            # Create expired entry
            cache.set("expired_key", {"data": "expired"}, 1)
            time.sleep(1.1)

            # Create entry without TTL
            cache.set("no_ttl_key", {"data": "no_ttl"}, 0)

            info = cache.get_cache_info()

            assert info["total_files"] == 3
            assert info["valid_entries"] == 2  # valid_key and no_ttl_key
            assert info["expired_entries"] == 1  # expired_key
            assert info["total_size_bytes"] > 0
            assert info["cache_directory"] == str(cache.cache_dir)

    def test_get_cache_info_with_corrupted_files(self) -> None:
        """Test get_cache_info handles corrupted files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            # Create valid entry
            cache.set("valid_key", {"data": "valid"}, 3600)

            # Create corrupted file
            corrupted_file = cache.cache_dir / "corrupted_key.json"
            with open(corrupted_file, "w", encoding="utf-8") as f:
                f.write("invalid json")

            info = cache.get_cache_info()

            assert info["total_files"] == 2
            assert info["valid_entries"] == 1  # Only the valid entry
            assert (
                info["expired_entries"] == 1
            )  # The corrupted file is counted as expired

    def test_unicode_data_handling(self) -> None:
        """Test that cache handles Unicode data correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            key = "unicode_key"
            data = {
                "title": "進撃の巨人",  # Japanese characters
                "description": "A story about humanity's fight for survival",
                "characters": ["エレン", "ミカサ", "アルミン"],
            }
            ttl = 3600

            cache.set(key, data, ttl)
            retrieved_data = cache.get(key)

            assert retrieved_data == data
            assert retrieved_data["title"] == "進撃の巨人"
            assert "エレン" in retrieved_data["characters"]

    def test_large_data_handling(self) -> None:
        """Test that cache handles large data structures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))

            key = "large_data_key"
            # Create a large data structure
            data = {
                "episodes": [
                    {"episode": i, "title": f"Episode {i}"} for i in range(1000)
                ],
                "metadata": {"total_episodes": 1000, "status": "completed"},
            }
            ttl = 3600

            cache.set(key, data, ttl)
            retrieved_data = cache.get(key)

            assert retrieved_data == data
            assert len(retrieved_data["episodes"]) == 1000
            assert retrieved_data["metadata"]["total_episodes"] == 1000

    def test_concurrent_access(self) -> None:
        """Test that cache handles concurrent access safely."""
        import threading

        with tempfile.TemporaryDirectory() as temp_dir:
            cache = CacheV1(Path(temp_dir))
            results = []
            errors = []

            def worker(worker_id: int) -> None:
                """Worker function for concurrent testing."""
                try:
                    key = f"worker_{worker_id}_key"
                    data = {
                        "worker_id": worker_id,
                        "data": f"data_from_worker_{worker_id}",
                    }

                    # Set data
                    cache.set(key, data, 3600)

                    # Get data
                    retrieved = cache.get(key)
                    results.append((worker_id, retrieved))

                except Exception as e:
                    errors.append(e)

            # Start multiple threads
            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Verify no errors occurred
            assert not errors, f"Errors occurred: {errors}"

            # Verify all workers completed successfully
            assert len(results) == 5
            for worker_id, retrieved_data in results:
                assert retrieved_data["worker_id"] == worker_id
                assert retrieved_data["data"] == f"data_from_worker_{worker_id}"
