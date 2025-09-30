"""Tests for test helper utilities."""

from __future__ import annotations

import pytest
from pathlib import Path

from tests.test_helpers import create_large_test_directory, cleanup_test_directory


class TestCreateLargeTestDirectory:
    """Test suite for create_large_test_directory helper."""

    def test_creates_correct_number_of_files(self, tmp_path: Path) -> None:
        """Test that the helper creates the specified number of files."""
        # Given
        num_files = 100
        test_dir = tmp_path / "test_files"

        # When
        created_files = create_large_test_directory(test_dir, num_files)

        # Then
        assert len(created_files) == num_files
        assert test_dir.exists()
        assert all(f.exists() for f in created_files)

    def test_creates_directory_if_not_exists(self, tmp_path: Path) -> None:
        """Test that the helper creates the base directory if it doesn't exist."""
        # Given
        test_dir = tmp_path / "non_existent" / "nested" / "dir"
        num_files = 10

        # When
        created_files = create_large_test_directory(test_dir, num_files)

        # Then
        assert test_dir.exists()
        assert len(created_files) == num_files

    def test_uses_default_extensions(self, tmp_path: Path) -> None:
        """Test that default extensions are used when none provided."""
        # Given
        test_dir = tmp_path / "test_files"
        num_files = 50
        default_extensions = {".mp4", ".mkv", ".avi"}

        # When
        created_files = create_large_test_directory(test_dir, num_files)

        # Then
        extensions_used = {f.suffix for f in created_files}
        assert extensions_used.issubset(default_extensions)
        assert len(extensions_used) > 0  # At least one extension was used

    def test_uses_custom_extensions(self, tmp_path: Path) -> None:
        """Test that custom extensions are used when provided."""
        # Given
        test_dir = tmp_path / "test_files"
        num_files = 30
        custom_extensions = [".ts", ".m2ts"]

        # When
        created_files = create_large_test_directory(
            test_dir,
            num_files,
            extensions=custom_extensions,
        )

        # Then
        extensions_used = {f.suffix for f in created_files}
        assert extensions_used == set(custom_extensions)

    def test_creates_realistic_anime_filenames(self, tmp_path: Path) -> None:
        """Test that created files have realistic anime-like filenames."""
        # Given
        test_dir = tmp_path / "test_files"
        num_files = 20

        # When
        created_files = create_large_test_directory(test_dir, num_files)

        # Then
        # All files should have names with typical anime patterns
        for file_path in created_files:
            filename = file_path.name
            # Check for common patterns like episode numbers, quality tags, etc.
            has_pattern = (
                "E" in filename  # Episode marker
                or "S" in filename  # Season marker
                or "p" in filename  # Quality marker (720p, 1080p, etc.)
                or "K" in filename  # Quality marker (4K, 8K, etc.)
                or "[" in filename  # Group tag
            )
            assert has_pattern, f"Filename '{filename}' lacks expected anime patterns"

    def test_files_are_empty(self, tmp_path: Path) -> None:
        """Test that created files are empty."""
        # Given
        test_dir = tmp_path / "test_files"
        num_files = 10

        # When
        created_files = create_large_test_directory(test_dir, num_files)

        # Then
        for file_path in created_files:
            assert file_path.stat().st_size == 0

    def test_handles_large_numbers(self, tmp_path: Path) -> None:
        """Test that the helper can handle large numbers of files."""
        # Given
        test_dir = tmp_path / "test_files"
        num_files = 1000  # Larger number for stress test

        # When
        created_files = create_large_test_directory(test_dir, num_files)

        # Then
        assert len(created_files) == num_files
        assert all(f.exists() for f in created_files)


class TestCleanupTestDirectory:
    """Test suite for cleanup_test_directory helper."""

    def test_removes_all_files(self, tmp_path: Path) -> None:
        """Test that cleanup removes all files."""
        # Given
        test_dir = tmp_path / "test_cleanup"
        created_files = create_large_test_directory(test_dir, 50)
        assert all(f.exists() for f in created_files)

        # When
        cleanup_test_directory(test_dir)

        # Then
        assert not test_dir.exists()

    def test_handles_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test that cleanup handles non-existent directories gracefully."""
        # Given
        test_dir = tmp_path / "non_existent_dir"
        assert not test_dir.exists()

        # When/Then - Should not raise an error
        cleanup_test_directory(test_dir)

    def test_removes_subdirectories(self, tmp_path: Path) -> None:
        """Test that cleanup removes nested subdirectories."""
        # Given
        test_dir = tmp_path / "test_nested"
        sub_dir_1 = test_dir / "sub1"
        sub_dir_2 = test_dir / "sub2"

        create_large_test_directory(sub_dir_1, 10)
        create_large_test_directory(sub_dir_2, 10)

        # When
        cleanup_test_directory(test_dir)

        # Then
        assert not test_dir.exists()
        assert not sub_dir_1.exists()
        assert not sub_dir_2.exists()
