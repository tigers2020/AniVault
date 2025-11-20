"""Unit tests for FileOperationExecutor service.

This module tests file operation execution with validation,
error handling, and security checks (path traversal prevention).

# ruff: noqa: ERA001
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.core.log_manager import OperationLogManager
from anivault.core.models import FileOperation, OperationType, ScannedFile
from anivault.core.organizer.executor import FileOperationExecutor
from anivault.core.parser.models import ParsingResult

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_log_manager() -> Mock:
    """Create mock OperationLogManager."""
    log_manager = Mock(spec=OperationLogManager)
    log_manager.save_plan = Mock()
    return log_manager


@pytest.fixture
def mock_settings() -> Mock:
    """Create mock settings object."""
    settings = Mock()
    settings.app = Mock()
    settings.app.organize_target_folder = "/tmp/target"  # noqa: S108 - Test fixture
    settings.app.organize_media_type = "TV"
    settings.app.organize_by_resolution = True
    return settings


@pytest.fixture
def executor(mock_log_manager: Mock, mock_settings: Mock) -> FileOperationExecutor:
    """Create FileOperationExecutor instance with mocked dependencies."""
    return FileOperationExecutor(
        log_manager=mock_log_manager,
        settings=mock_settings,
    )


@pytest.fixture
def temp_source_file(tmp_path: Path) -> Path:
    """Create a temporary source file for testing."""
    source_file = tmp_path / "source" / "test_anime.mkv"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("fake video content")
    return source_file


@pytest.fixture
def temp_dest_path(tmp_path: Path) -> Path:
    """Create a temporary destination path."""
    return tmp_path / "dest" / "organized" / "test_anime.mkv"


@pytest.fixture
def file_operation(temp_source_file: Path, temp_dest_path: Path) -> FileOperation:
    """Create a FileOperation for testing."""
    return FileOperation(
        operation_type=OperationType.MOVE,
        source_path=temp_source_file,
        destination_path=temp_dest_path,
    )


@pytest.fixture
def scanned_file(temp_source_file: Path) -> ScannedFile:
    """Create a ScannedFile for subtitle matching tests."""
    metadata = ParsingResult(
        title="Test Anime",
        quality="1080p",
    )
    return ScannedFile(
        file_path=temp_source_file,
        metadata=metadata,
        file_size=1024000,
        last_modified=1640995200.0,
    )


# ============================================================================
# Basic Execution Tests (Subtask 8.2)
# ============================================================================


class TestBasicExecution:
    """Tests for basic file operation execution."""

    @pytest.mark.parametrize(
        "operation_type",
        [OperationType.MOVE, OperationType.COPY],
    )
    def test_execute_operation_success(
        self,
        executor: FileOperationExecutor,
        temp_source_file: Path,
        temp_dest_path: Path,
        operation_type: OperationType,
    ) -> None:
        """Test successful file operation execution."""
        # Given: A valid file operation
        operation = FileOperation(
            operation_type=operation_type,
            source_path=temp_source_file,
            destination_path=temp_dest_path,
        )

        # When: Executing the operation
        result = executor.execute(operation, dry_run=False)

        # Then: Operation succeeds
        assert result.success is True
        assert result.skipped is False
        assert result.source_path == str(temp_source_file)
        assert result.destination_path == str(temp_dest_path)
        assert temp_dest_path.exists()

    def test_execute_dry_run(
        self,
        executor: FileOperationExecutor,
        file_operation: FileOperation,
    ) -> None:
        """Test dry-run mode skips actual execution."""
        # When: Executing in dry-run mode
        result = executor.execute(file_operation, dry_run=True)

        # Then - Operation is skipped
        assert result.success is True
        assert result.skipped is True
        assert result.message == "Dry-run: validation passed"

        # And: Destination file is NOT created
        assert not file_operation.destination_path.exists()


# ============================================================================
# Validation Tests (Subtask 8.4)
# ============================================================================


class TestValidation:
    """Tests for operation validation."""

    def test_validate_source_not_exists(
        self,
        executor: FileOperationExecutor,
        tmp_path: Path,
    ) -> None:
        """Test validation fails when source doesn't exist."""
        # Given: Operation with non-existent source
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=tmp_path / "nonexistent.mkv",
            destination_path=tmp_path / "dest.mkv",
        )

        # When/Then: Execution raises FileNotFoundError
        with pytest.raises(FileNotFoundError, match="Source file does not exist"):
            executor.execute(operation, dry_run=False)

    def test_validate_source_is_directory(
        self,
        executor: FileOperationExecutor,
        tmp_path: Path,
    ) -> None:
        """Test validation fails when source is a directory."""
        # Given: Operation with directory as source
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()

        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=source_dir,
            destination_path=tmp_path / "dest.mkv",
        )

        # When/Then: Execution raises OSError
        with pytest.raises(OSError, match="Source path is not a file"):
            executor.execute(operation, dry_run=False)


# ============================================================================
# Error Handling Tests (Subtask 8.3)
# ============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @patch("anivault.core.organizer.executor.shutil.move")
    def test_file_exists_error(
        self,
        mock_move: Mock,
        executor: FileOperationExecutor,
        temp_source_file: Path,
        temp_dest_path: Path,
    ) -> None:
        """Test handling of FileExistsError."""
        # Given: shutil.move raises FileExistsError
        mock_move.side_effect = FileExistsError(
            f"File already exists: {temp_dest_path}"
        )

        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=temp_source_file,
            destination_path=temp_dest_path,
        )

        # When/Then: Execution raises FileExistsError
        with pytest.raises(FileExistsError, match="File already exists"):
            executor.execute(operation, dry_run=False)

    @patch("anivault.core.organizer.executor.shutil.move")
    def test_permission_error(
        self,
        mock_move: Mock,
        executor: FileOperationExecutor,
        temp_source_file: Path,
        temp_dest_path: Path,
    ) -> None:
        """Test handling of PermissionError."""
        # Given: shutil.move raises PermissionError
        mock_move.side_effect = PermissionError("Permission denied")

        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=temp_source_file,
            destination_path=temp_dest_path,
        )

        # When/Then: Execution raises OSError (PermissionError is subclass of OSError)
        with pytest.raises(OSError, match="IO error occurred during move"):
            executor.execute(operation, dry_run=False)

    @patch("anivault.core.organizer.executor.shutil.copy2")
    def test_copy_os_error(
        self,
        mock_copy: Mock,
        executor: FileOperationExecutor,
        temp_source_file: Path,
        temp_dest_path: Path,
    ) -> None:
        """Test handling of OSError during copy."""
        # Given: shutil.copy2 raises OSError
        mock_copy.side_effect = OSError("Disk full or I/O error")

        operation = FileOperation(
            operation_type=OperationType.COPY,
            source_path=temp_source_file,
            destination_path=temp_dest_path,
        )

        # When/Then: Execution raises OSError
        with pytest.raises(OSError, match="IO error occurred during copy"):
            executor.execute(operation, dry_run=False)


# ============================================================================
# Path Traversal Prevention Tests (Subtask 8.4)
# ============================================================================


class TestPathTraversalPrevention:
    """Tests for path traversal security checks."""

    def test_path_traversal_detected(
        self,
        executor: FileOperationExecutor,
        temp_source_file: Path,
        tmp_path: Path,
    ) -> None:
        """Test path traversal attempt is blocked."""
        # Given: Operation with path traversal in destination
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=temp_source_file,
            destination_path=tmp_path / ".." / ".." / "escape" / "file.mkv",
        )

        # When/Then: Execution raises ValueError
        with pytest.raises(ValueError, match="Path traversal detected"):
            executor.execute(operation, dry_run=False)

    def test_path_traversal_in_middle(
        self,
        executor: FileOperationExecutor,
        temp_source_file: Path,
        tmp_path: Path,
    ) -> None:
        """Test path traversal in middle of path is blocked."""
        # Given: Operation with path traversal in middle of path
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=temp_source_file,
            destination_path=tmp_path
            / "good"
            / ".."
            / ".."
            / ".."
            / "escape"
            / "file.mkv",
        )

        # When/Then: Execution raises ValueError
        with pytest.raises(ValueError, match="Path traversal detected"):
            executor.execute(operation, dry_run=False)

    def test_destination_directory_created(
        self,
        executor: FileOperationExecutor,
        temp_source_file: Path,
        tmp_path: Path,
    ) -> None:
        """Test destination directory is automatically created."""
        # Given: Operation with non-existent destination directory
        dest_path = tmp_path / "new" / "nested" / "dir" / "file.mkv"
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=temp_source_file,
            destination_path=dest_path,
        )

        # When: Executing the operation
        result = executor.execute(operation, dry_run=False)

        # Then: Directory is created and operation succeeds
        assert result.success is True
        assert dest_path.parent.exists()
        assert dest_path.parent.is_dir()


# ============================================================================
# Batch Execution Tests (Subtask 8.2)
# ============================================================================


class TestBatchExecution:
    """Tests for batch operation execution."""

    def test_execute_batch_success(
        self,
        executor: FileOperationExecutor,
        tmp_path: Path,
    ) -> None:
        """Test successful batch execution."""
        # Given: Multiple valid operations
        operations = []
        for i in range(3):
            source = tmp_path / "source" / f"file_{i}.mkv"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(f"content {i}")

            dest = tmp_path / "dest" / f"file_{i}.mkv"

            operations.append(
                FileOperation(
                    operation_type=OperationType.MOVE,
                    source_path=source,
                    destination_path=dest,
                )
            )

        # When: Executing batch
        results = executor.execute_batch(
            operations=operations,
            dry_run=False,
            operation_id="test_batch_001",
            no_log=True,
        )

        # Then: All operations succeed
        assert len(results) == 3
        assert all(r.success for r in results)
        assert all(not r.skipped for r in results)

    def test_execute_batch_continues_on_error(
        self,
        executor: FileOperationExecutor,
        tmp_path: Path,
    ) -> None:
        """Test batch execution continues after individual failures."""
        # Given: Mix of valid and invalid operations
        operations = []

        # Valid operation 1
        source1 = tmp_path / "source" / "file_1.mkv"
        source1.parent.mkdir(parents=True, exist_ok=True)
        source1.write_text("content 1")
        operations.append(
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=source1,
                destination_path=tmp_path / "dest" / "file_1.mkv",
            )
        )

        # Invalid operation (source doesn't exist)
        operations.append(
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=tmp_path / "nonexistent.mkv",
                destination_path=tmp_path / "dest" / "file_2.mkv",
            )
        )

        # Valid operation 2
        source3 = tmp_path / "source" / "file_3.mkv"
        source3.write_text("content 3")
        operations.append(
            FileOperation(
                operation_type=OperationType.MOVE,
                source_path=source3,
                destination_path=tmp_path / "dest" / "file_3.mkv",
            )
        )

        # When: Executing batch
        results = executor.execute_batch(
            operations=operations,
            dry_run=False,
            operation_id="test_batch_002",
            no_log=True,
        )

        # Then: Valid operations succeed, invalid fails
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True


# ============================================================================
# Subtitle Matching Tests (Subtask 8.2)
# ============================================================================


class TestSubtitleMatching:
    """Tests for subtitle file matching."""

    @patch("anivault.core.subtitle_matcher.SubtitleMatcher")
    def test_find_matching_subtitles(
        self,
        mock_subtitle_matcher_class: Mock,
        executor: FileOperationExecutor,
        scanned_file: ScannedFile,
        tmp_path: Path,
    ) -> None:
        """Test finding and creating operations for matching subtitles."""
        # Given: Mock subtitle matcher
        mock_matcher = Mock()
        mock_subtitle_matcher_class.return_value = mock_matcher

        # Create subtitle files
        subtitle_path = scanned_file.file_path.parent / "test_anime.srt"
        subtitle_path.write_text("subtitle content")

        mock_matcher.find_matching_subtitles.return_value = [subtitle_path]

        destination_path = tmp_path / "dest" / "test_anime.mkv"

        # When: Finding matching subtitles
        operations = executor.find_matching_subtitles(
            scanned_file,
            destination_path,
        )

        # Then: Subtitle operation is created
        assert len(operations) == 1
        assert operations[0].operation_type == OperationType.MOVE
        assert operations[0].source_path == subtitle_path
        assert (
            operations[0].destination_path == destination_path.parent / "test_anime.srt"
        )


# ============================================================================
# Logging Tests (Subtask 8.5)
# ============================================================================


class TestLogging:
    """Tests for operation logging."""

    def test_logging_disabled_when_no_log(
        self,
        executor: FileOperationExecutor,
        file_operation: FileOperation,
    ) -> None:
        """Test logging is skipped when no_log=True."""
        # When: Executing with no_log=True
        executor.execute_batch(
            operations=[file_operation],
            dry_run=False,
            operation_id="test_log_001",
            no_log=True,
        )

        # Then: Log manager is not called
        executor.log_manager.save_plan.assert_not_called()

    def test_error_handling_in_batch(
        self,
        executor: FileOperationExecutor,
        tmp_path: Path,
    ) -> None:
        """Test error cases are properly handled in batch execution."""
        # Given: Operation with non-existent source
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=tmp_path / "nonexistent.mkv",
            destination_path=tmp_path / "dest.mkv",
        )

        # When: Executing batch with error
        results = executor.execute_batch(
            operations=[operation],
            dry_run=False,
            operation_id="test_log_002",
            no_log=True,
        )

        # Then: Operation fails but batch continues
        assert len(results) == 1
        assert results[0].success is False
        assert "Source file does not exist" in results[0].message


# ============================================================================
# Destructive Scenario Tests (Additional Coverage)
# ============================================================================


class TestDestructiveScenarios:
    """Tests for destructive and edge case scenarios."""

    def test_empty_source_path(
        self,
        executor: FileOperationExecutor,
        tmp_path: Path,
    ) -> None:
        """Test handling of empty source path."""
        # Given: Operation with empty source path
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=Path(),
            destination_path=tmp_path / "dest.mkv",
        )

        # When/Then: Execution raises OSError (empty path resolves to current dir, which is not a file)
        with pytest.raises(OSError, match="Source path is not a file"):
            executor.execute(operation, dry_run=False)

    @pytest.mark.parametrize(
        "filename",
        [
            "file with spaces.mkv",
            "file_with_underscores.mkv",
            "file-with-dashes.mkv",
            "file.multiple.dots.mkv",
        ],
    )
    def test_special_characters_in_filename(
        self,
        executor: FileOperationExecutor,
        tmp_path: Path,
        filename: str,
    ) -> None:
        """Test handling of special characters in filename."""
        # Given: File with special characters
        source = tmp_path / "source" / filename
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("content")

        dest = tmp_path / "dest" / filename

        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=source,
            destination_path=dest,
        )

        # When: Executing the operation
        result = executor.execute(operation, dry_run=False)

        # Then: Operation succeeds
        assert result.success is True
        assert dest.exists()
