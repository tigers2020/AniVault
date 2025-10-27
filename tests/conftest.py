"""
Pytest configuration and shared fixtures for AniVault tests.

This module provides common fixtures and configuration that can be used
across all test modules in the project.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock

import pytest

from anivault.shared.constants import FileSystem

# Set environment variables BEFORE any imports (for CI without .env)
if "TMDB_API_KEY" not in os.environ:
    os.environ["TMDB_API_KEY"] = (
        "test_api_key_for_ci_testing_only"  # pragma: allowlist secret
    )
if "TMDB_LANGUAGE" not in os.environ:
    os.environ["TMDB_LANGUAGE"] = "ko"
if "TMDB_REGION" not in os.environ:
    os.environ["TMDB_REGION"] = "KR"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files.

    Yields:
        Path to the temporary directory.
    """
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def sample_anime_files(temp_dir: Path) -> list[Path]:
    """Create sample anime files for testing.

    Args:
        temp_dir: Temporary directory to create files in.

    Returns:
        List of created file paths.
    """
    files = []
    anime_titles = [
        "Attack_on_Titan",
        "One_Piece",
        "Naruto",
        "Demon_Slayer",
        "My_Hero_Academia",
    ]

    for i, title in enumerate(anime_titles):
        for ext in FileSystem.SUPPORTED_VIDEO_EXTENSIONS[:3]:  # Use first 3 extensions
            filename = f"{title}_S01E{i + 1:02d}_1080p{ext}"
            file_path = temp_dir / filename
            file_path.touch()
            files.append(file_path)

    return files


@pytest.fixture
def mock_tmdb_client(mocker):
    """Create a mock TMDB client for testing.

    Returns:
        Mock TMDB client instance.
    """
    mock_client = mocker.Mock()
    mock_client.search_tv.return_value = {
        "results": [
            {
                "id": 12345,
                "name": "Attack on Titan",
                "first_air_date": "2013-04-07",
                "overview": "Humanity fights for survival...",
                "popularity": 85.5,
                "vote_average": 8.5,
            },
        ],
    }
    mock_client.get_tv_details.return_value = {
        "id": 12345,
        "name": "Attack on Titan",
        "overview": "Humanity fights for survival...",
        "first_air_date": "2013-04-07",
        "last_air_date": "2023-11-05",
        "number_of_seasons": 4,
        "number_of_episodes": 87,
        "genres": [{"id": 16, "name": "Animation"}],
        "networks": [{"id": 1, "name": "NHK"}],
        "production_companies": [{"id": 1, "name": "Wit Studio"}],
    }
    return mock_client


@pytest.fixture
def mock_cache(mocker):
    """Create a mock cache for testing.

    Returns:
        Mock cache instance.
    """
    mock_cache = mocker.Mock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    mock_cache.delete.return_value = True
    mock_cache.clear.return_value = True
    return mock_cache

    """Create a mock cache for testing.

    Returns:
        Mock cache instance.
    """
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    mock_cache.delete.return_value = True
    mock_cache.clear.return_value = True
    return mock_cache


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing.

    Returns:
        Mock logger instance.
    """
    mock_logger = Mock()
    mock_logger.debug = Mock()
    mock_logger.info = Mock()
    mock_logger.warning = Mock()
    mock_logger.error = Mock()
    mock_logger.critical = Mock()
    return mock_logger


@pytest.fixture(autouse=True)
def _reset_global_state():
    """Reset global state before each test.

    This fixture runs automatically before each test to ensure
    clean state between tests.
    """
    # Reset any global state here if needed
    return
    # Cleanup after test if needed


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add unit marker to unit tests
        if "test_" in item.name and "integration" not in item.name:
            item.add_marker(pytest.mark.unit)
