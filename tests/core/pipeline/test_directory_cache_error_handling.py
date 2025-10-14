"""
Tests for DirectoryCacheManager error handling improvements.

This module tests the structured error handling implemented in the
DirectoryCacheManager class, ensuring that file system errors are
properly wrapped in InfrastructureError exceptions with context.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from anivault.core.pipeline.components import DirectoryCacheManager
from anivault.shared.errors import ErrorCode, InfrastructureError


class TestDirectoryCacheErrorHandling:
    """Test error handling in DirectoryCacheManager."""

    def test_load_cache_permission_error(self):
        """Test that PermissionError is properly wrapped in InfrastructureError."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "test_cache.json"

            # Create the cache file first
            cache_file.write_text("{}", encoding="utf-8")

            # Mock both exists() and open() to simulate permission error
            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "builtins.open", side_effect=PermissionError("Permission denied")
                ):
                    cache_manager = DirectoryCacheManager(cache_file)

                    with pytest.raises(InfrastructureError) as exc_info:
                        cache_manager.load_cache()

                    error = exc_info.value
                    assert error.code == ErrorCode.FILE_ACCESS_DENIED
                    assert "Permission denied reading cache file" in error.message
                    assert str(cache_file) in error.message
                    assert error.context.file_path == str(cache_file)
                    assert error.context.operation == "load_cache"
                    assert isinstance(error.original_error, PermissionError)

    def test_load_cache_os_error_graceful_fallback(self):
        """Test that OSError results in graceful fallback with warning."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "test_cache.json"

            with patch("builtins.open", mock_open()) as mock_file:
                mock_file.side_effect = OSError("Disk full")

                cache_manager = DirectoryCacheManager(cache_file)

                # Should not raise exception, should fallback gracefully
                cache_manager.load_cache()

                # Cache should be empty due to fallback
                assert cache_manager.get_cache_size() == 0

    def test_load_cache_json_decode_error_graceful_fallback(self):
        """Test that JSONDecodeError results in graceful fallback."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "test_cache.json"

            # Create corrupted JSON file
            cache_file.write_text("{invalid json}", encoding="utf-8")

            cache_manager = DirectoryCacheManager(cache_file)

            # Should not raise exception, should fallback gracefully
            cache_manager.load_cache()

            # Cache should be empty due to fallback
            assert cache_manager.get_cache_size() == 0

    def test_save_cache_permission_error(self):
        """Test that PermissionError during save is properly wrapped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "test_cache.json"

            cache_manager = DirectoryCacheManager(cache_file)
            cache_manager.load_cache()

            # Add some data to cache
            cache_manager.update_directory_data(
                "/test/path", 123.45, ["file1"], ["dir1"]
            )

            with patch("builtins.open", mock_open()) as mock_file:
                mock_file.side_effect = PermissionError("Permission denied")

                with pytest.raises(InfrastructureError) as exc_info:
                    cache_manager.save_cache()

                error = exc_info.value
                assert error.code == ErrorCode.FILE_ACCESS_DENIED
                assert "Permission denied writing cache file" in error.message
                assert str(cache_file) in error.message
                assert error.context.file_path == str(cache_file)
                assert error.context.operation == "save_cache"
                assert isinstance(error.original_error, PermissionError)

    def test_save_cache_os_error_graceful_continuation(self):
        """Test that OSError during save allows continuation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "test_cache.json"

            cache_manager = DirectoryCacheManager(cache_file)
            cache_manager.load_cache()

            # Add some data to cache
            cache_manager.update_directory_data(
                "/test/path", 123.45, ["file1"], ["dir1"]
            )

            with patch("builtins.open", mock_open()) as mock_file:
                mock_file.side_effect = OSError("Disk full")

                # Should not raise exception, should log warning and continue
                cache_manager.save_cache()

                # Cache data should still be available in memory
                assert cache_manager.get_cache_size() == 1

    def test_load_cache_file_not_exists_creates_empty_cache(self):
        """Test that non-existent cache file creates empty cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "nonexistent_cache.json"

            cache_manager = DirectoryCacheManager(cache_file)
            cache_manager.load_cache()

            # Cache should be empty
            assert cache_manager.get_cache_size() == 0

    def test_load_cache_valid_json_loads_successfully(self):
        """Test that valid JSON cache file loads successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_file = Path(temp_dir) / "test_cache.json"
            test_dir = Path(temp_dir) / "test_dir"
            test_dir.mkdir()

            # Create valid cache data using the actual test directory path
            cache_data = {
                str(test_dir.resolve()): {
                    "mtime": 123.45,
                    "files": ["file1.txt", "file2.txt"],
                    "subdirs": ["subdir1"],
                }
            }
            cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

            cache_manager = DirectoryCacheManager(cache_file)
            cache_manager.load_cache()

            # Cache should contain the data
            assert cache_manager.get_cache_size() == 1
            directory_data = cache_manager.get_directory_data(test_dir)
            assert directory_data is not None
            assert directory_data["mtime"] == 123.45
            assert directory_data["files"] == ["file1.txt", "file2.txt"]
            assert directory_data["subdirs"] == ["subdir1"]
