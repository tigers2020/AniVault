"""Test helper utilities for AniVault.

This module provides utility functions for generating test data,
especially for performance and stress testing scenarios.
"""

from __future__ import annotations

import random
import shutil
from pathlib import Path
from typing import Generator

import pytest

from anivault.shared.constants import SUPPORTED_VIDEO_EXTENSIONS

# Constants for test data generation
ANIME_TITLES = [
    "Attack_on_Titan",
    "One_Piece",
    "Naruto",
    "Demon_Slayer",
    "My_Hero_Academia",
    "Jujutsu_Kaisen",
    "Chainsaw_Man",
    "Spy_x_Family",
    "Bleach",
    "Hunter_x_Hunter",
]

QUALITIES = ["1080p", "720p", "480p", "4K"]
GROUPS = ["SubsPlease", "Erai-raws", "HorribleSubs", "Commie"]

FILENAME_PATTERNS = [
    "[{group}] {title} - S{season:02d}E{episode:02d} [{quality}] - {index:06d}{extension}",
    "{title}_S{season:02d}E{episode:02d}_{quality}_{index:06d}{extension}",
    "[{group}] {title} - {episode:02d} [{quality}] - {index:06d}{extension}",
    "{title}.{episode:02d}.{quality}.{index:06d}{extension}",
]


def create_large_test_directory(
    base_path: Path,
    num_files: int,
    extensions: list[str] | None = None,
    create_subdirs: bool = False,
    subdir_count: int = 5,
) -> list[Path]:
    """Create a large number of test files for performance testing.

    This helper function generates a specified number of empty files
    in a given directory, useful for benchmarking and stress testing
    the file scanning and processing pipeline.

    Args:
        base_path: Directory where files will be created.
        num_files: Number of files to generate.
        extensions: List of file extensions to use. Defaults to supported video extensions.
        create_subdirs: Whether to create subdirectories for files.
        subdir_count: Number of subdirectories to create if create_subdirs is True.

    Returns:
        List of Path objects for the created files.
    """
    if extensions is None:
        extensions = SUPPORTED_VIDEO_EXTENSIONS[:3]  # Use first 3 extensions

    # Ensure the base directory exists
    base_path.mkdir(parents=True, exist_ok=True)

    created_files = []
    files_per_subdir = num_files // subdir_count if create_subdirs else num_files

    for i in range(num_files):
        # Determine subdirectory if needed
        if create_subdirs:
            subdir_name = f"subdir_{i // files_per_subdir:03d}"
            subdir_path = base_path / subdir_name
            subdir_path.mkdir(exist_ok=True)
            file_dir = subdir_path
        else:
            file_dir = base_path

        # Generate a realistic anime filename with unique index to avoid duplicates
        title = random.choice(ANIME_TITLES)
        season = random.randint(1, 5)
        episode = random.randint(1, 50)
        quality = random.choice(QUALITIES)
        group = random.choice(GROUPS)
        extension = random.choice(extensions)

        # Create filename with various patterns (include index for uniqueness)
        pattern = random.choice(FILENAME_PATTERNS)
        filename = pattern.format(
            group=group,
            title=title,
            season=season,
            episode=episode,
            quality=quality,
            index=i,
            extension=extension,
        )

        file_path = file_dir / filename
        file_path.touch()
        created_files.append(file_path)

    return created_files


def cleanup_test_directory(directory: Path) -> None:
    """Remove all files and subdirectories in the test directory.

    Args:
        directory: Directory to clean up.
    """
    if not directory.exists():
        return

    # Use shutil.rmtree for more efficient cleanup
    shutil.rmtree(directory)


@pytest.fixture
def large_test_directory(
    temp_dir: Path,
) -> Generator[tuple[Path, list[Path]], None, None]:
    """Create a large test directory with many files.

    Args:
        temp_dir: Temporary directory fixture.

    Yields:
        Tuple of (directory_path, list_of_created_files).
    """
    test_dir = temp_dir / "large_test"
    files = create_large_test_directory(test_dir, 1000, create_subdirs=True)

    yield test_dir, files

    # Cleanup is handled by temp_dir fixture


def create_metadata_file(file_path: Path, metadata: dict | None = None) -> Path:
    """Create a metadata JSON file for a given video file.

    Args:
        file_path: Path to the video file.
        metadata: Metadata to write. If None, creates sample metadata.

    Returns:
        Path to the created metadata file.
    """
    import json

    if metadata is None:
        metadata = {
            "title": "Sample Anime",
            "season": 1,
            "episode": 1,
            "quality": "1080p",
            "group": "TestGroup",
            "file_size": 1024 * 1024,  # 1MB
            "duration": 1440,  # 24 minutes
            "format": file_path.suffix[1:],
            "parsed": True,
        }

    metadata_path = file_path.with_suffix(file_path.suffix + ".json")
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return metadata_path


def create_test_anime_file(
    base_path: Path,
    title: str,
    season: int = 1,
    episode: int = 1,
    quality: str = "1080p",
    group: str = "TestGroup",
    extension: str = ".mkv",
) -> Path:
    """Create a single test anime file with specific parameters.

    Args:
        base_path: Directory to create the file in.
        title: Anime title.
        season: Season number.
        episode: Episode number.
        quality: Video quality.
        group: Release group.
        extension: File extension.

    Returns:
        Path to the created file.
    """
    filename = f"[{group}] {title} - S{season:02d}E{episode:02d} [{quality}]{extension}"
    file_path = base_path / filename
    file_path.touch()
    return file_path


def assert_file_exists(file_path: Path) -> None:
    """Assert that a file exists, with helpful error message.

    Args:
        file_path: Path to check.

    Raises:
        AssertionError: If file doesn't exist.
    """
    assert file_path.exists(), f"Expected file to exist: {file_path}"


def assert_file_not_exists(file_path: Path) -> None:
    """Assert that a file doesn't exist, with helpful error message.

    Args:
        file_path: Path to check.

    Raises:
        AssertionError: If file exists.
    """
    assert not file_path.exists(), f"Expected file to not exist: {file_path}"


def assert_directory_empty(directory: Path) -> None:
    """Assert that a directory is empty, with helpful error message.

    Args:
        directory: Directory to check.

    Raises:
        AssertionError: If directory is not empty.
    """
    files = list(directory.iterdir())
    assert (
        len(files) == 0
    ), f"Expected directory to be empty, but found {len(files)} items: {files}"
