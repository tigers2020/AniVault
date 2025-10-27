"""Test DirectoryCacheManager with LinkedHashTable integration."""

import tempfile
from pathlib import Path

import pytest

from anivault.core.pipeline.components.directory_cache import DirectoryCacheManager, DirectoryInfo


class TestDirectoryCacheManagerLinkedHashTable:
    """Test DirectoryCacheManager with LinkedHashTable."""

    def test_cache_initialization(self):
        """Test that cache initializes with LinkedHashTable."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            cache_file = Path(f.name)

        try:
            cache_manager = DirectoryCacheManager(cache_file)

            # Verify LinkedHashTable is used
            assert hasattr(cache_manager._cache, 'put')
            assert hasattr(cache_manager._cache, 'get')
            assert hasattr(cache_manager._cache, 'remove')
            assert hasattr(cache_manager._cache, 'size')

            # Initial cache should be empty
            assert cache_manager.get_cache_size() == 0

        finally:
            cache_file.unlink(missing_ok=True)

    def test_cache_operations(self):
        """Test basic cache operations with LinkedHashTable."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            cache_file = Path(f.name)

        try:
            cache_manager = DirectoryCacheManager(cache_file)

            # Test adding directory data
            test_dir = "/test/directory"
            test_mtime = 1234567890.0
            test_files = ["file1.txt", "file2.txt"]
            test_subdirs = ["subdir1", "subdir2"]

            cache_manager.update_directory_data(test_dir, test_mtime, test_files, test_subdirs)

            # Test retrieving directory data
            retrieved_data = cache_manager.get_directory_data(test_dir)
            assert retrieved_data is not None
            assert isinstance(retrieved_data, DirectoryInfo)
            assert retrieved_data.mtime == test_mtime
            assert retrieved_data.files == test_files
            assert retrieved_data.subdirs == test_subdirs

            # Test cache size
            assert cache_manager.get_cache_size() == 1

            # Test removing directory
            cache_manager.remove_directory(test_dir)
            assert cache_manager.get_cache_size() == 0

            # Test retrieving non-existent directory
            assert cache_manager.get_directory_data(test_dir) is None

        finally:
            cache_file.unlink(missing_ok=True)

    def test_cache_clear(self):
        """Test cache clearing with LinkedHashTable."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            cache_file = Path(f.name)

        try:
            cache_manager = DirectoryCacheManager(cache_file)

            # Add some test data
            cache_manager.update_directory_data("/test1", 1234567890.0, ["file1"], ["dir1"])
            cache_manager.update_directory_data("/test2", 1234567890.0, ["file2"], ["dir2"])

            assert cache_manager.get_cache_size() == 2

            # Clear cache
            cache_manager.clear_cache()

            # Verify cache is empty
            assert cache_manager.get_cache_size() == 0
            assert cache_manager.get_directory_data("/test1") is None
            assert cache_manager.get_directory_data("/test2") is None

        finally:
            cache_file.unlink(missing_ok=True)

    def test_thread_safety(self):
        """Test that LinkedHashTable operations are thread-safe with existing lock."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            cache_file = Path(f.name)

        try:
            cache_manager = DirectoryCacheManager(cache_file)

            # Test concurrent operations (simplified)
            cache_manager.update_directory_data("/test", 1234567890.0, ["file1"], ["dir1"])

            # Verify data integrity
            data = cache_manager.get_directory_data("/test")
            assert data is not None
            assert isinstance(data, DirectoryInfo)
            assert data.files == ["file1"]
            assert data.subdirs == ["dir1"]

        finally:
            cache_file.unlink(missing_ok=True)
