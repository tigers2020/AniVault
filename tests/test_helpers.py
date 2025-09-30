"""Test helper utilities for AniVault.

This module provides utility functions for generating test data,
especially for performance and stress testing scenarios.
"""

from __future__ import annotations

import random
from pathlib import Path


def create_large_test_directory(
    base_path: Path,
    num_files: int,
    extensions: list[str] | None = None,
) -> list[Path]:
    """Create a large number of test files for performance testing.

    This helper function generates a specified number of empty files
    in a given directory, useful for benchmarking and stress testing
    the file scanning and processing pipeline.

    Args:
        base_path: Directory where files will be created.
        num_files: Number of files to generate.
        extensions: List of file extensions to use. Defaults to ['.mp4', '.mkv', '.avi'].

    Returns:
        List of Path objects for the created files.
    """
    if extensions is None:
        extensions = [".mp4", ".mkv", ".avi"]

    # Ensure the base directory exists
    base_path.mkdir(parents=True, exist_ok=True)

    created_files = []

    # Create files with various anime-like names
    anime_titles = [
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

    qualities = ["1080p", "720p", "480p", "4K"]
    groups = ["SubsPlease", "Erai-raws", "HorribleSubs", "Commie"]

    for i in range(num_files):
        # Generate a realistic anime filename with unique index to avoid duplicates
        title = random.choice(anime_titles)
        season = random.randint(1, 5)
        episode = random.randint(1, 50)
        quality = random.choice(qualities)
        group = random.choice(groups)
        extension = random.choice(extensions)

        # Create filename with various patterns (include index for uniqueness)
        patterns = [
            f"[{group}] {title} - S{season:02d}E{episode:02d} [{quality}] - {i:06d}{extension}",
            f"{title}_S{season:02d}E{episode:02d}_{quality}_{i:06d}{extension}",
            f"[{group}] {title} - {episode:02d} [{quality}] - {i:06d}{extension}",
            f"{title}.{episode:02d}.{quality}.{i:06d}{extension}",
        ]

        filename = random.choice(patterns)
        file_path = base_path / filename

        # Create empty file
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

    # Remove all files
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            file_path.unlink()

    # Remove all subdirectories
    for dir_path in sorted(directory.rglob("*"), reverse=True):
        if dir_path.is_dir():
            dir_path.rmdir()

    # Remove the base directory
    if directory.exists():
        directory.rmdir()
