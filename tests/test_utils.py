"""
Test utilities and helper functions for AniVault tests.

This module provides common utilities that can be used across different
test modules to reduce code duplication and improve maintainability.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

import pytest


class TestDataGenerator:
    """Generate test data for various scenarios."""

    @staticmethod
    def create_anime_metadata(
        title: str = "Test Anime",
        season: int = 1,
        episode: int = 1,
        quality: str = "1080p",
        group: str = "TestGroup",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create sample anime metadata."""
        metadata = {
            "title": title,
            "season": season,
            "episode": episode,
            "quality": quality,
            "group": group,
            "file_size": 1024 * 1024,  # 1MB
            "duration": 1440,  # 24 minutes
            "format": "mkv",
            "parsed": True,
            **kwargs,
        }
        return metadata

    @staticmethod
    def create_tmdb_response(
        title: str = "Test Anime", id: int = 12345, **kwargs: Any
    ) -> Dict[str, Any]:
        """Create sample TMDB API response."""
        response = {
            "id": id,
            "name": title,
            "first_air_date": "2020-01-01",
            "overview": "A test anime series",
            "popularity": 85.5,
            "vote_average": 8.5,
            "genres": [{"id": 16, "name": "Animation"}],
            **kwargs,
        }
        return response


class MockFactory:
    """Factory for creating common mock objects."""

    @staticmethod
    def create_file_system_mock(
        files: List[str], directories: List[str] = None
    ) -> Mock:
        """Create a mock file system with specified files and directories."""
        if directories is None:
            directories = []

        mock_fs = Mock()
        mock_fs.exists.return_value = True
        mock_fs.is_file.return_value = True
        mock_fs.is_dir.return_value = False
        mock_fs.iterdir.return_value = [Path(f) for f in files]

        def mock_path(path_str: str) -> Mock:
            path_mock = Mock()
            path_mock.exists.return_value = path_str in files or path_str in directories
            path_mock.is_file.return_value = path_str in files
            path_mock.is_dir.return_value = path_str in directories
            path_mock.name = Path(path_str).name
            path_mock.suffix = Path(path_str).suffix
            path_mock.stem = Path(path_str).stem
            return path_mock

        mock_fs.side_effect = mock_path
        return mock_fs

    @staticmethod
    def create_logger_mock() -> Mock:
        """Create a mock logger."""
        logger = Mock()
        logger.debug = Mock()
        logger.info = Mock()
        logger.warning = Mock()
        logger.error = Mock()
        logger.critical = Mock()
        return logger

    @staticmethod
    def create_cache_mock() -> Mock:
        """Create a mock cache."""
        cache = Mock()
        cache.get.return_value = None
        cache.set.return_value = True
        cache.delete.return_value = True
        cache.clear.return_value = True
        cache.exists.return_value = False
        return cache


class TestFileManager:
    """Manage test files and directories."""

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize with optional base directory."""
        self.base_dir = base_dir or Path(tempfile.gettempdir()) / "anivault_tests"
        self.created_files: List[Path] = []
        self.created_dirs: List[Path] = []

    def create_test_file(
        self, filename: str, content: str = "test content", subdir: Optional[str] = None
    ) -> Path:
        """Create a test file with content."""
        if subdir:
            file_path = self.base_dir / subdir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            file_path = self.base_dir / filename

        file_path.write_text(content, encoding="utf-8")
        self.created_files.append(file_path)
        return file_path

    def create_test_directory(self, dirname: str) -> Path:
        """Create a test directory."""
        dir_path = self.base_dir / dirname
        dir_path.mkdir(parents=True, exist_ok=True)
        self.created_dirs.append(dir_path)
        return dir_path

    def create_json_file(
        self, filename: str, data: Dict[str, Any], subdir: Optional[str] = None
    ) -> Path:
        """Create a JSON file with data."""
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return self.create_test_file(filename, content, subdir)

    def cleanup(self) -> None:
        """Clean up all created files and directories."""
        import shutil

        for file_path in self.created_files:
            if file_path.exists():
                file_path.unlink()

        for dir_path in reversed(self.created_dirs):
            if dir_path.exists():
                shutil.rmtree(dir_path)

        if self.base_dir.exists() and not any(self.base_dir.iterdir()):
            self.base_dir.rmdir()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


class AssertionHelpers:
    """Helper functions for common test assertions."""

    @staticmethod
    def assert_file_exists(file_path: Path, message: str = None) -> None:
        """Assert that a file exists."""
        if message is None:
            message = f"Expected file to exist: {file_path}"
        assert file_path.exists(), message

    @staticmethod
    def assert_file_not_exists(file_path: Path, message: str = None) -> None:
        """Assert that a file doesn't exist."""
        if message is None:
            message = f"Expected file to not exist: {file_path}"
        assert not file_path.exists(), message

    @staticmethod
    def assert_directory_empty(directory: Path, message: str = None) -> None:
        """Assert that a directory is empty."""
        if message is None:
            message = f"Expected directory to be empty: {directory}"
        files = list(directory.iterdir())
        assert len(files) == 0, f"{message}. Found: {files}"

    @staticmethod
    def assert_json_equals(file_path: Path, expected_data: Dict[str, Any]) -> None:
        """Assert that a JSON file contains expected data."""
        assert file_path.exists(), f"JSON file does not exist: {file_path}"

        actual_data = json.loads(file_path.read_text(encoding="utf-8"))
        assert actual_data == expected_data, f"JSON data mismatch in {file_path}"

    @staticmethod
    def assert_contains_substring(
        text: str, substring: str, message: str = None
    ) -> None:
        """Assert that text contains a substring."""
        if message is None:
            message = f"Expected '{substring}' to be in text"
        assert substring in text, f"{message}. Text: {text}"


@pytest.fixture
def test_file_manager(temp_dir: Path) -> TestFileManager:
    """Provide a test file manager for the current test."""
    manager = TestFileManager(temp_dir)
    yield manager
    manager.cleanup()


@pytest.fixture
def sample_anime_metadata() -> Dict[str, Any]:
    """Provide sample anime metadata."""
    return TestDataGenerator.create_anime_metadata()


@pytest.fixture
def sample_tmdb_response() -> Dict[str, Any]:
    """Provide sample TMDB API response."""
    return TestDataGenerator.create_tmdb_response()


@pytest.fixture
def mock_file_system() -> Mock:
    """Provide a mock file system."""
    return MockFactory.create_file_system_mock([])


@pytest.fixture
def mock_logger() -> Mock:
    """Provide a mock logger."""
    return MockFactory.create_logger_mock()


@pytest.fixture
def mock_cache() -> Mock:
    """Provide a mock cache."""
    return MockFactory.create_cache_mock()


# Performance testing utilities
class PerformanceTimer:
    """Context manager for timing code execution."""

    def __init__(self, name: str = "operation"):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        import time

        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time

        self.end_time = time.time()
        duration = self.end_time - self.start_time
        print(f"{self.name} took {duration:.3f} seconds")

    @property
    def duration(self) -> float:
        """Get the duration of the operation."""
        if self.start_time is None or self.end_time is None:
            raise RuntimeError("Timer not started or not finished")
        return self.end_time - self.start_time


# Memory testing utilities
def get_memory_usage() -> int:
    """Get current memory usage in bytes."""
    import os

    import psutil

    process = psutil.Process(os.getpid())
    return process.memory_info().rss


def assert_memory_usage_under(limit_mb: int) -> None:
    """Assert that memory usage is under the specified limit."""
    memory_bytes = get_memory_usage()
    memory_mb = memory_bytes / (1024 * 1024)
    assert (
        memory_mb < limit_mb
    ), f"Memory usage {memory_mb:.1f}MB exceeds limit {limit_mb}MB"
