"""
Tests for the FileOrganizer class.

These tests verify the file organization functionality, including error handling
for various filesystem operations.
"""

import logging
from pathlib import Path
from typing import Generator
from unittest.mock import Mock, patch

import pytest

from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, OperationType, ScannedFile
from anivault.core.organizer import FileOrganizer


class TestFileOrganizer:
    """Test FileOrganizer functionality."""

    @pytest.fixture
    def temp_organizer(self, temp_dir: Path) -> Generator[FileOrganizer, None, None]:
        """Create a FileOrganizer instance for testing."""
        log_manager = OperationLogManager(temp_dir)
        organizer = FileOrganizer(log_manager=log_manager)
        yield organizer

    @pytest.fixture
    def sample_file_operations(self, temp_dir: Path) -> list[FileOperation]:
        """Create sample file operations for testing."""
        source_file = temp_dir / "test_anime.mkv"
        source_file.write_text("test content")

        dest_file = temp_dir / "Anime" / "Test Series" / "Season 01" / "test_anime.mkv"

        return [
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=source_file,
                destination_path=dest_file,
            )
        ]

    @pytest.fixture
    def multiple_file_operations(self, temp_dir: Path) -> list[FileOperation]:
        """Create multiple file operations for testing error scenarios."""
        operations = []

        # Create source files
        for i in range(3):
            source_file = temp_dir / f"test_anime_{i}.mkv"
            source_file.write_text(f"test content {i}")

            dest_file = (
                temp_dir
                / "Anime"
                / f"Test Series {i}"
                / "Season 01"
                / f"test_anime_{i}.mkv"
            )

            operations.append(
                FileOperation(
                    operation_type=OperationType.MOVE,
                    source_path=source_file,
                    destination_path=dest_file,
                )
            )

        return operations

    def test_execute_plan_success(
        self, temp_organizer: FileOrganizer, sample_file_operations: list[FileOperation]
    ) -> None:
        """Test successful execution of file operations."""
        moved_files = temp_organizer.execute_plan(
            sample_file_operations, "test_operation"
        )

        assert len(moved_files) == 1
        source_path, dest_path = moved_files[0]
        assert source_path == str(sample_file_operations[0].source_path)
        assert dest_path == str(sample_file_operations[0].destination_path)

        # Verify file was actually moved
        assert not Path(source_path).exists()
        assert Path(dest_path).exists()

    def test_execute_plan_file_not_found_error(
        self,
        temp_organizer: FileOrganizer,
        temp_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling of FileNotFoundError during file operations."""
        # Create operation with non-existent source file
        non_existent_source = temp_dir / "non_existent.mkv"
        dest_file = temp_dir / "Anime" / "Test Series" / "test_anime.mkv"

        operations = [
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=non_existent_source,
                destination_path=dest_file,
            )
        ]

        with caplog.at_level(logging.ERROR):
            moved_files = temp_organizer.execute_plan(operations, "test_operation")

        assert len(moved_files) == 0
        assert "An unexpected IO error occurred for" in caplog.text
        assert str(non_existent_source) in caplog.text

    @patch("anivault.core.organizer.shutil.move")
    def test_execute_plan_file_exists_error(
        self,
        mock_move,
        temp_organizer: FileOrganizer,
        temp_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling of FileExistsError during file operations."""
        # Create source file
        source_file = temp_dir / "test_anime.mkv"
        source_file.write_text("test content")

        # Create destination file that already exists
        dest_file = temp_dir / "existing_anime.mkv"
        dest_file.write_text("existing content")

        # Mock shutil.move to raise FileExistsError
        mock_move.side_effect = FileExistsError("File already exists")

        operations = [
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=source_file,
                destination_path=dest_file,
            )
        ]

        with caplog.at_level(logging.ERROR):
            moved_files = temp_organizer.execute_plan(operations, "test_operation")

        assert len(moved_files) == 0
        assert "File already exists at destination, skipping:" in caplog.text
        assert str(dest_file) in caplog.text

    @patch("anivault.core.organizer.shutil.move")
    def test_execute_plan_io_error(
        self,
        mock_move,
        temp_organizer: FileOrganizer,
        temp_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling of IOError during file operations."""
        # Create source file
        source_file = temp_dir / "test_anime.mkv"
        source_file.write_text("test content")

        # Create destination in a non-writable location (simulated)
        dest_file = temp_dir / "readonly" / "test_anime.mkv"

        # Mock shutil.move to raise IOError
        mock_move.side_effect = IOError("Permission denied")

        operations = [
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=source_file,
                destination_path=dest_file,
            )
        ]

        with caplog.at_level(logging.ERROR):
            moved_files = temp_organizer.execute_plan(operations, "test_operation")

        assert len(moved_files) == 0
        assert "An unexpected IO error occurred for" in caplog.text
        assert str(source_file) in caplog.text

    @patch("anivault.core.organizer.shutil.move")
    def test_execute_plan_mixed_errors(
        self,
        mock_move,
        temp_organizer: FileOrganizer,
        multiple_file_operations: list[FileOperation],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling of mixed error scenarios in a single plan."""

        # Configure mock to raise different errors for different calls
        def side_effect(*args, **kwargs):
            if "test_anime_0" in args[0]:
                return  # Success for first file
            elif "test_anime_1" in args[0]:
                raise FileNotFoundError("Source file not found")
            elif "test_anime_2" in args[0]:
                raise FileExistsError("File already exists")
            else:
                raise IOError("Permission denied")

        mock_move.side_effect = side_effect

        with caplog.at_level(logging.ERROR):
            moved_files = temp_organizer.execute_plan(
                multiple_file_operations, "test_operation"
            )

        # Should have one successful move and two errors
        assert len(moved_files) == 1
        assert mock_move.call_count == 3

        # Check that appropriate error messages were logged
        assert "Source file not found, skipping:" in caplog.text
        assert "File already exists at destination, skipping:" in caplog.text

    def test_execute_plan_continues_after_errors(
        self,
        temp_organizer: FileOrganizer,
        temp_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that execute_plan continues processing after encountering errors."""
        operations = []

        # Create one successful operation
        success_source = temp_dir / "success.mkv"
        success_source.write_text("success content")
        success_dest = temp_dir / "Anime" / "Success Series" / "success.mkv"

        operations.append(
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=success_source,
                destination_path=success_dest,
            )
        )

        # Create one operation that will fail
        fail_source = temp_dir / "fail.mkv"  # This file doesn't exist
        fail_dest = temp_dir / "Anime" / "Fail Series" / "fail.mkv"

        operations.append(
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=fail_source,
                destination_path=fail_dest,
            )
        )

        # Create another successful operation
        success2_source = temp_dir / "success2.mkv"
        success2_source.write_text("success2 content")
        success2_dest = temp_dir / "Anime" / "Success2 Series" / "success2.mkv"

        operations.append(
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=success2_source,
                destination_path=success2_dest,
            )
        )

        with caplog.at_level(logging.ERROR):
            moved_files = temp_organizer.execute_plan(operations, "test_operation")

        # Should have 2 successful moves and 1 error
        assert len(moved_files) == 2
        assert "An unexpected IO error occurred for" in caplog.text

        # Verify both successful files were moved
        assert not success_source.exists()
        assert success_dest.exists()
        assert not success2_source.exists()
        assert success2_dest.exists()

    def test_execute_plan_empty_plan(self, temp_organizer: FileOrganizer) -> None:
        """Test execution of empty plan."""
        moved_files = temp_organizer.execute_plan([], "test_operation")
        assert len(moved_files) == 0

    def test_execute_plan_no_log_flag(
        self, temp_organizer: FileOrganizer, sample_file_operations: list[FileOperation]
    ) -> None:
        """Test execution with no_log flag."""
        with patch.object(temp_organizer.log_manager, "save_plan") as mock_save:
            moved_files = temp_organizer.execute_plan(
                sample_file_operations, "test_operation", no_log=True
            )

            # Should still move files but not save log
            assert len(moved_files) == 1
            mock_save.assert_not_called()

    @patch("builtins.print")
    def test_execute_plan_log_save_failure(
        self,
        mock_print,
        temp_organizer: FileOrganizer,
        sample_file_operations: list[FileOperation],
    ) -> None:
        """Test handling of log save failure."""
        with patch.object(
            temp_organizer.log_manager,
            "save_plan",
            side_effect=Exception("Log save failed"),
        ):
            moved_files = temp_organizer.execute_plan(
                sample_file_operations, "test_operation"
            )

            # Should still move files but print the warning
            assert len(moved_files) == 1
            mock_print.assert_called_with(
                "Warning: Failed to save operation log: Log save failed"
            )

    def test_validate_operation_source_not_exists(
        self, temp_organizer: FileOrganizer, temp_dir: Path
    ) -> None:
        """Test validation of operation with non-existent source file."""
        non_existent_source = temp_dir / "non_existent.mkv"
        dest_file = temp_dir / "test_anime.mkv"

        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=non_existent_source,
            destination_path=dest_file,
        )

        with pytest.raises(OSError, match="Source file does not exist"):
            temp_organizer._validate_operation(operation)

    def test_validate_operation_source_not_file(
        self, temp_organizer: FileOrganizer, temp_dir: Path
    ) -> None:
        """Test validation of operation where source is not a file."""
        # Create a directory instead of a file
        source_dir = temp_dir / "test_dir"
        source_dir.mkdir()

        dest_file = temp_dir / "test_anime.mkv"

        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=source_dir,
            destination_path=dest_file,
        )

        with pytest.raises(OSError, match="Source path is not a file"):
            temp_organizer._validate_operation(operation)

    def test_ensure_destination_directory(
        self, temp_organizer: FileOrganizer, temp_dir: Path
    ) -> None:
        """Test destination directory creation."""
        dest_file = temp_dir / "deep" / "nested" / "path" / "test_anime.mkv"

        # Directory should not exist initially
        assert not dest_file.parent.exists()

        temp_organizer._ensure_destination_directory(dest_file)

        # Directory should be created
        assert dest_file.parent.exists()
        assert dest_file.parent.is_dir()

    def test_execute_file_operation_copy(
        self, temp_organizer: FileOrganizer, temp_dir: Path
    ) -> None:
        """Test copy operation."""
        source_file = temp_dir / "test_anime.mkv"
        source_file.write_text("test content")

        # Ensure destination directory exists
        dest_dir = temp_dir / "Anime" / "Test Series"
        dest_dir.mkdir(parents=True)
        dest_file = dest_dir / "test_anime_copy.mkv"

        operation = FileOperation(
            operation_type=OperationType.COPY,
            source_path=source_file,
            destination_path=dest_file,
        )

        result = temp_organizer._execute_file_operation(operation)

        assert result is not None
        source_path, dest_path = result
        assert source_path == str(source_file)
        assert dest_path == str(dest_file)

        # Both source and destination should exist after copy
        assert source_file.exists()
        assert dest_file.exists()


if __name__ == "__main__":
    pytest.main([__file__])
