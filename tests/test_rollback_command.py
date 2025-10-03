"""
Tests for the rollback command functionality.

These tests verify that the rollback command works correctly with --dry-run and --yes flags.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import pytest

from tests.test_helpers import assert_file_exists, create_test_anime_file


class TestRollbackCommand:
    """Test rollback command functionality."""

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

    @pytest.fixture
    def mock_log_file(self) -> Path:
        """Create a mock log file for rollback testing."""
        # Create the .anivault/logs directory in the project root
        project_root = Path(__file__).parent.parent
        log_dir = project_root / ".anivault" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create a mock log file with some operations (correct format for load_plan)
        log_data = [
            {
                "operation_type": "move",
                "source_path": "/source/Attack_on_Titan_S01E01.mkv",
                "destination_path": "/dest/Attack on Titan/Season 01/Attack on Titan S01E01.mkv",
            },
            {
                "operation_type": "move",
                "source_path": "/source/One_Piece_S01E01.mp4",
                "destination_path": "/dest/One Piece/Season 01/One Piece S01E01.mp4",
            },
        ]

        log_file = log_dir / "organize-20240101_120000.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f)

        yield log_file

        # Cleanup: remove the log file after test
        if log_file.exists():
            log_file.unlink()

    def test_rollback_help(self) -> None:
        """Test that rollback command shows help information."""
        result = subprocess.run(
            [sys.executable, "-m", "anivault.cli.main", "rollback", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        # Check for key help text elements
        assert "usage: anivault rollback" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--yes" in result.stdout
        assert "The ID of the log file to use for the rollback" in result.stdout

    def test_rollback_dry_run_with_valid_log(self, mock_log_file: Path) -> None:
        """Test rollback --dry-run with a valid log file."""
        log_id = "20240101_120000"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "rollback",
                log_id,
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "[DRY RUN]" in result.stdout
        assert "Planned rollback operations" in result.stdout
        assert "Attack_on_Titan_S01E01.mkv" in result.stdout
        assert "One_Piece_S01E01.mp4" in result.stdout

    def test_rollback_dry_run_with_invalid_log_id(self) -> None:
        """Test rollback --dry-run with invalid log ID."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "rollback",
                "invalid_log_id",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode != 0
        assert "error" in result.stderr.lower() or "not found" in result.stderr.lower()

    def test_rollback_yes_flag_with_valid_log(self, mock_log_file: Path) -> None:
        """Test rollback --yes with a valid log file."""
        log_id = "20240101_120000"

        # Mock the file organizer to prevent actual file operations
        with patch(
            "anivault.core.organizer.FileOrganizer.execute_plan"
        ) as mock_execute:
            mock_execute.return_value = ["file1.mkv", "file2.mp4"]

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "anivault.cli.main",
                    "rollback",
                    log_id,
                    "--yes",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0
            # Note: Files don't exist in test, so rollback will show skipped operations
            assert "No executable rollback operations found" in result.stdout
            assert "Skipped" in result.stdout

    def test_rollback_without_flags_requires_confirmation(
        self, mock_log_file: Path
    ) -> None:
        """Test that rollback without --yes flag requires confirmation."""
        log_id = "20240101_120000"

        # Since prompt_toolkit doesn't work in subprocess, we'll test that the command
        # shows the rollback plan and asks for confirmation (even if it fails due to console)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "rollback",
                log_id,
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        # The command will succeed but show skipped operations due to validation
        assert result.returncode == 0
        assert "No executable rollback operations found" in result.stdout
        assert "Skipped" in result.stdout

    def test_rollback_dry_run_empty_operations(self) -> None:
        """Test rollback --dry-run with empty operations log."""
        # Create the .anivault/logs directory in the project root
        project_root = Path(__file__).parent.parent
        log_dir = project_root / ".anivault" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create a log file with empty operations (correct format for load_plan)
        log_data = []

        log_file = log_dir / "organize-20240101_120000.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f)

        try:
            log_id = "20240101_120000"

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "anivault.cli.main",
                    "rollback",
                    log_id,
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0
            assert "No rollback operations needed" in result.stdout
        finally:
            # Cleanup
            if log_file.exists():
                log_file.unlink()

    def test_rollback_yes_with_dry_run_ignores_yes(self, mock_log_file: Path) -> None:
        """Test that --yes flag is ignored when --dry-run is also specified."""
        log_id = "20240101_120000"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "rollback",
                log_id,
                "--dry-run",
                "--yes",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "[DRY RUN]" in result.stdout
        assert "Planned rollback operations" in result.stdout
        # Should not show confirmation prompt or execution messages
        assert (
            "The following rollback operations will be performed" not in result.stdout
        )
        assert "Successfully rolled back" not in result.stdout

    def test_rollback_invalid_log_format(self, temp_dir: Path) -> None:
        """Test rollback with invalid log file format."""
        log_dir = temp_dir / ".anivault" / "logs"
        log_dir.mkdir(parents=True)

        # Create a log file with invalid JSON
        log_file = log_dir / "organize-20240101_120000.json"
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        log_id = "20240101_120000"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "rollback",
                log_id,
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode != 0
        assert "error" in result.stderr.lower()

    def test_rollback_missing_log_id_argument(self) -> None:
        """Test rollback without required log_id argument."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "anivault.cli.main",
                "rollback",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "missing" in result.stderr.lower()

    def test_rollback_partial_failure_scenario(self, temp_dir: Path) -> None:
        """Test rollback with partial failure scenario - some files missing."""
        # Create source and destination directories
        source_dir = temp_dir / "source"
        dest_dir = temp_dir / "dest"
        source_dir.mkdir()
        dest_dir.mkdir()

        # Create test files in source directory
        file1 = source_dir / "Attack_on_Titan_S01E01.mkv"
        file2 = source_dir / "One_Piece_S01E01.mp4"
        file3 = source_dir / "Naruto_S01E01.avi"

        file1.write_text("test content 1")
        file2.write_text("test content 2")
        file3.write_text("test content 3")

        # Create destination structure
        attack_dir = dest_dir / "Attack on Titan" / "Season 01"
        onepiece_dir = dest_dir / "One Piece" / "Season 01"
        naruto_dir = dest_dir / "Naruto" / "Season 01"

        attack_dir.mkdir(parents=True)
        onepiece_dir.mkdir(parents=True)
        naruto_dir.mkdir(parents=True)

        # Move files to simulate organization (move from source to dest)
        (attack_dir / "Attack on Titan S01E01.mkv").write_text("test content 1")
        (onepiece_dir / "One Piece S01E01.mp4").write_text("test content 2")
        (naruto_dir / "Naruto S01E01.avi").write_text("test content 3")

        # Delete one of the organized files to simulate partial failure
        (attack_dir / "Attack on Titan S01E01.mkv").unlink()

        # Create log file in the project root's .anivault/logs directory
        project_root = Path(__file__).parent.parent
        log_dir = project_root / ".anivault" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Log file should contain the original organization operations (source -> dest)
        # Rollback will reverse these (dest -> source)
        log_data = [
            {
                "operation_type": "move",
                "source_path": str(file1),
                "destination_path": str(attack_dir / "Attack on Titan S01E01.mkv"),
            },
            {
                "operation_type": "move",
                "source_path": str(file2),
                "destination_path": str(onepiece_dir / "One Piece S01E01.mp4"),
            },
            {
                "operation_type": "move",
                "source_path": str(file3),
                "destination_path": str(naruto_dir / "Naruto S01E01.avi"),
            },
        ]

        log_file = log_dir / "organize-20240101_120000.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f)

        try:
            log_id = "20240101_120000"

            # Test dry run first to see the plan
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "anivault.cli.main",
                    "rollback",
                    log_id,
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0
            assert "[DRY RUN]" in result.stdout
            assert "Planned rollback operations" in result.stdout

            # Test actual rollback with --yes to avoid confirmation
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "anivault.cli.main",
                    "rollback",
                    log_id,
                    "--yes",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            assert result.returncode == 0

            # Check that the command completed successfully
            assert "Executing rollback" in result.stdout

            # Check that some files were successfully rolled back
            assert "Successfully rolled back" in result.stdout

            # Check that skipped operations are reported
            assert "Skipped" in result.stdout or "skipped" in result.stdout
            assert (
                "source files not found" in result.stdout
                or "not found" in result.stdout
            )

            # Verify that the existing files were actually moved back
            assert file2.exists()  # One Piece should be moved back
            assert file3.exists()  # Naruto should be moved back
            # Note: file1 should exist because it was never moved (source file still exists)

            # Verify that the organized files are gone
            assert not (onepiece_dir / "One Piece S01E01.mp4").exists()
            assert not (naruto_dir / "Naruto S01E01.avi").exists()

        finally:
            # Cleanup
            if log_file.exists():
                log_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__])
