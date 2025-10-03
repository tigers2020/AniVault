"""
Tests for the organize command functionality.

These tests verify that the organize command works correctly with --dry-run flag.
"""

import subprocess
import sys
from pathlib import Path
from typing import Generator

import pytest

from tests.test_helpers import assert_file_exists, create_test_anime_file


class TestOrganizeCommand:
    """Test organize command functionality."""

    @pytest.fixture
    def test_files_dir(self, temp_dir: Path) -> Generator[Path, None, None]:
        """Create a directory with test anime files."""
        test_dir = temp_dir / "test_anime_files"
        test_dir.mkdir()

        # Create test files
        create_test_anime_file(
            test_dir, "Attack_on_Titan", 1, 1, "1080p", "TestGroup", ".mkv"
        )
        create_test_anime_file(test_dir, "One_Piece", 1, 1, "720p", "TestGroup", ".mp4")
        create_test_anime_file(test_dir, "Naruto", 1, 1, "480p", "TestGroup", ".avi")

        yield test_dir

    def test_organize_help(self) -> None:
        """Test that organize command shows help information."""
        result = subprocess.run(
            [sys.executable, "-m", "anivault.cli.main", "organize", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        # Check for key help text elements (the output includes logging, so we check for specific parts)
        assert "usage: anivault organize" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--extensions" in result.stdout
        assert "--output-dir" in result.stdout
        assert "Directory containing anime files to organize" in result.stdout

    def test_organize_dry_run_empty_directory(self, temp_dir: Path) -> None:
        """Test organize --dry-run with empty directory."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "organize",
                str(temp_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "No anime files found in the specified directory" in result.stdout

    def test_organize_dry_run_with_test_files(self, test_files_dir: Path) -> None:
        """Test organize --dry-run with test anime files."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "organize",
                str(test_files_dir),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "Found" in result.stdout
        assert "anime files" in result.stdout
        assert "dry-run" in result.stdout.lower()

    def test_organize_with_specific_extensions(self, test_files_dir: Path) -> None:
        """Test organize with specific file extensions."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "organize",
                str(test_files_dir),
                "--dry-run",
                "--extensions",
                ".mkv,.mp4",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "Found" in result.stdout

    def test_organize_with_output_directory(
        self, test_files_dir: Path, temp_dir: Path
    ) -> None:
        """Test organize with custom output directory."""
        output_dir = temp_dir / "organized"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "organize",
                str(test_files_dir),
                "--dry-run",
                "--output-dir",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "Found" in result.stdout

    def test_organize_invalid_directory(self) -> None:
        """Test organize with non-existent directory."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "organize",
                "/non/existent/directory",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "not found" in result.stderr.lower()

    def test_organize_with_workers_option(self, test_files_dir: Path) -> None:
        """Test organize with custom worker count."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "organize",
                str(test_files_dir),
                "--dry-run",
                "--workers",
                "2",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "Found" in result.stdout

    def test_organize_with_confidence_threshold(self, test_files_dir: Path) -> None:
        """Test organize with custom confidence threshold."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "organize",
                str(test_files_dir),
                "--dry-run",
                "--confidence-threshold",
                "0.8",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "Found" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__])
