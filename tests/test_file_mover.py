"""Tests for file movement system.

This module contains comprehensive tests for the file movement functionality,
including transactional operations, conflict resolution, and error handling.
"""

import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import (
    FileNamingError,
    MoveRollbackError,
)
from src.core.file_classifier import FileClassifier
from src.core.file_mover import FileMover, MoveOperation, MoveTransaction
from src.core.file_namer import FileNamer, NamingStrategy
from src.core.models import AnimeFile, ParsedAnimeInfo


class TestFileMover:
    """Test cases for FileMover class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def file_mover(self, temp_dir):
        """Create a FileMover instance for testing."""
        return FileMover(temp_dir=temp_dir / "temp")

    @pytest.fixture
    def test_files(self, temp_dir) -> None:
        """Create test files for movement operations."""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # Create test files
        files = []
        for i in range(3):
            file_path = source_dir / f"test_file_{i}.txt"
            file_path.write_text(f"Test content {i}")
            files.append(file_path)

        return files

    def test_move_file_success(self, file_mover, temp_dir, test_files) -> None:
        """Test successful file movement."""
        source_file = test_files[0]
        target_file = temp_dir / "target" / "moved_file.txt"

        result = file_mover.move_file(source_file, target_file)

        assert result.success
        assert result.source_path == source_file
        assert result.target_path == target_file
        assert result.operation == MoveOperation.MOVE
        assert not source_file.exists()
        assert target_file.exists()
        assert target_file.read_text() == "Test content 0"

    def test_move_file_create_directories(self, file_mover, temp_dir, test_files) -> None:
        """Test file movement with directory creation."""
        source_file = test_files[0]
        target_file = temp_dir / "new" / "nested" / "directory" / "file.txt"

        result = file_mover.move_file(source_file, target_file, create_dirs=True)

        assert result.success
        assert target_file.parent.exists()
        assert target_file.exists()

    def test_move_file_conflict_resolution(self, file_mover, temp_dir, test_files) -> None:
        """Test file movement with conflict resolution."""
        source_file = test_files[0]
        target_file = temp_dir / "target" / "conflict_file.txt"
        target_file.parent.mkdir()
        target_file.write_text("Existing content")

        result = file_mover.move_file(source_file, target_file, overwrite=False)

        assert result.success
        # Should create a new file with suffix
        assert target_file.parent.exists()
        # Original conflict file should still exist
        assert target_file.exists()
        assert target_file.read_text() == "Existing content"

    def test_move_file_overwrite(self, file_mover, temp_dir, test_files) -> None:
        """Test file movement with overwrite enabled."""
        source_file = test_files[0]
        target_file = temp_dir / "target" / "overwrite_file.txt"
        target_file.parent.mkdir()
        target_file.write_text("Original content")

        result = file_mover.move_file(source_file, target_file, overwrite=True)

        assert result.success
        assert target_file.exists()
        assert target_file.read_text() == "Test content 0"

    def test_move_file_source_not_exists(self, file_mover, temp_dir) -> None:
        """Test file movement with non-existent source."""
        source_file = temp_dir / "nonexistent.txt"
        target_file = temp_dir / "target.txt"

        result = file_mover.move_file(source_file, target_file)

        assert not result.success
        assert "does not exist" in result.error_message
        assert result.rollback_required

    def test_move_file_permission_error(self, file_mover, temp_dir, test_files) -> None:
        """Test file movement with permission error."""
        source_file = test_files[0]
        target_file = temp_dir / "target.txt"

        # Mock permission error
        with patch("os.access", return_value=False):
            result = file_mover.move_file(source_file, target_file)

        assert not result.success
        assert "permission" in result.error_message.lower()

    def test_move_file_disk_space_error(self, file_mover, temp_dir, test_files) -> None:
        """Test file movement with insufficient disk space."""
        source_file = test_files[0]
        target_file = temp_dir / "target.txt"

        # Mock disk space check to fail
        with patch("shutil.disk_usage") as mock_disk_usage:
            mock_disk_usage.return_value = MagicMock(free=0)  # No free space
            result = file_mover.move_file(source_file, target_file)

        assert not result.success
        assert "disk space" in result.error_message.lower()

    def test_move_files_batch_success(self, file_mover, temp_dir, test_files) -> None:
        """Test batch file movement."""
        target_dir = temp_dir / "batch_target"
        target_dir.mkdir()

        operations = [
            (test_files[0], target_dir / "file1.txt"),
            (test_files[1], target_dir / "file2.txt"),
            (test_files[2], target_dir / "file3.txt"),
        ]

        results = file_mover.move_files_batch(operations)

        assert len(results) == 3
        assert all(result.success for result in results)
        assert all(not source.exists() for source, _ in operations)
        assert all(target.exists() for _, target in operations)

    def test_move_files_batch_partial_failure(self, file_mover, temp_dir, test_files) -> None:
        """Test batch file movement with partial failure."""
        target_dir = temp_dir / "batch_target"
        target_dir.mkdir()

        operations = [
            (test_files[0], target_dir / "file1.txt"),
            (Path("nonexistent.txt"), target_dir / "file2.txt"),  # This will fail
            (test_files[2], target_dir / "file3.txt"),
        ]

        results = file_mover.move_files_batch(operations)

        # Should have 2 results: first success, second failure
        assert len(results) == 2
        assert results[0].success  # First operation should succeed
        assert not results[1].success  # Second operation should fail

    def test_move_anime_files_organize_by_series(self, file_mover, temp_dir) -> None:
        """Test moving anime files with series organization."""
        # Create test anime files
        source_dir = temp_dir / "anime_source"
        source_dir.mkdir()

        # Create files for different series
        series1_files = [
            source_dir / "Series1_S01E01_1080p.mkv",
            source_dir / "Series1_S01E02_1080p.mkv",
        ]
        series2_files = [source_dir / "Series2_S01E01_720p.mkv"]

        for file_path in series1_files + series2_files:
            file_path.write_text("Anime content")

        # Create AnimeFile objects
        anime_files = []
        for file_path in series1_files + series2_files:
            parsed_info = ParsedAnimeInfo(
                title="Series1" if "Series1" in file_path.name else "Series2",
                season=1,
                episode=1 if "E01" in file_path.name else 2,
            )
            anime_file = AnimeFile(
                file_path=file_path,
                filename=file_path.name,
                file_size=file_path.stat().st_size,
                file_extension=file_path.suffix,
                created_at=time.time(),
                modified_at=time.time(),
                parsed_info=parsed_info,
            )
            anime_files.append(anime_file)

        target_dir = temp_dir / "anime_target"
        results = file_mover.move_anime_files(
            anime_files, target_dir, organize_by_series=True, keep_best_quality=False
        )

        assert len(results) == 3
        assert all(result.success for result in results)

        # Check series directories were created
        series1_dir = target_dir / "Series1"
        series2_dir = target_dir / "Series2"
        assert series1_dir.exists()
        assert series2_dir.exists()

    def test_transaction_context_manager(self, file_mover, temp_dir, test_files) -> None:
        """Test transaction context manager."""
        source_file = test_files[0]
        target_file = temp_dir / "transaction_target.txt"

        with file_mover.transaction() as transaction:
            result = file_mover.move_file(source_file, target_file, transaction_id=transaction.transaction_id)
            assert result.success
            assert transaction.transaction_id in file_mover._transactions

    def test_rollback_transaction(self, file_mover, temp_dir, test_files) -> None:
        """Test transaction rollback."""
        source_file = test_files[0]
        target_file = temp_dir / "rollback_target.txt"

        # Create a transaction
        transaction_id = "test_transaction"
        file_mover._transactions[transaction_id] = MoveTransaction(
            transaction_id=transaction_id, operations=[], created_at=time.time()
        )

        # Move file
        result = file_mover.move_file(source_file, target_file, transaction_id=transaction_id)
        assert result.success

        # Rollback
        rollback_success = file_mover.rollback_transaction(transaction_id)
        assert rollback_success

        # Check that file was moved back
        assert source_file.exists()
        assert not target_file.exists()

    def test_rollback_nonexistent_transaction(self, file_mover) -> None:
        """Test rollback of non-existent transaction."""
        with pytest.raises(MoveRollbackError):
            file_mover.rollback_transaction("nonexistent_transaction")

    def test_same_filesystem_detection(self, file_mover, temp_dir, test_files) -> None:
        """Test same filesystem detection."""
        source_file = test_files[0]
        target_file = temp_dir / "same_fs_target.txt"

        # Should detect same filesystem
        is_same = file_mover._is_same_filesystem(source_file, target_file)
        assert is_same

    def test_cross_filesystem_move(self, file_mover, temp_dir, test_files) -> None:
        """Test cross-filesystem move (copy + delete)."""
        source_file = test_files[0]
        target_file = temp_dir / "cross_fs_target.txt"

        # Mock different filesystem
        with patch.object(file_mover, "_is_same_filesystem", return_value=False):
            result = file_mover.move_file(source_file, target_file)

        assert result.success
        assert not source_file.exists()
        assert target_file.exists()
        assert target_file.read_text() == "Test content 0"

    def test_file_integrity_verification(self, file_mover, temp_dir, test_files) -> None:
        """Test file integrity verification."""
        source_file = test_files[0]
        target_file = temp_dir / "integrity_target.txt"

        # Create a copy for testing
        shutil.copy2(source_file, target_file)

        # Should pass integrity check
        assert file_mover._verify_file_integrity(source_file, target_file)

        # Modify target file
        target_file.write_text("Modified content")

        # Should fail integrity check
        assert not file_mover._verify_file_integrity(source_file, target_file)

    def test_sanitize_directory_name(self, file_mover) -> None:
        """Test directory name sanitization."""
        # Test invalid characters
        assert file_mover._sanitize_directory_name("Test<Name>") == "Test_Name"
        assert file_mover._sanitize_directory_name("Test:Name") == "Test_Name"

        # Test multiple underscores
        assert file_mover._sanitize_directory_name("Test___Name") == "Test_Name"

        # Test empty name
        assert file_mover._sanitize_directory_name("") == "unnamed"
        assert file_mover._sanitize_directory_name("...") == "unnamed"


class TestFileClassifier:
    """Test cases for FileClassifier class."""

    @pytest.fixture
    def classifier(self):
        """Create a FileClassifier instance for testing."""
        return FileClassifier()

    @pytest.fixture
    def test_anime_file(self, tmp_path) -> None:
        """Create a test AnimeFile for classification."""
        file_path = tmp_path / "test_anime_1080p.mkv"
        file_path.write_text("Test content")

        parsed_info = ParsedAnimeInfo(
            title="Test Anime",
            season=1,
            episode=1,
            resolution="1080p",
            resolution_width=1920,
            resolution_height=1080,
        )

        return AnimeFile(
            file_path=file_path,
            filename=file_path.name,
            file_size=file_path.stat().st_size,
            file_extension=file_path.suffix,
            created_at=time.time(),
            modified_at=time.time(),
            parsed_info=parsed_info,
        )

    def test_classify_file_with_parsed_info(self, classifier, test_anime_file) -> None:
        """Test file classification with parsed info."""
        classification = classifier.classify_file(test_anime_file)

        assert classification.file == test_anime_file
        assert classification.width == 1920
        assert classification.height == 1080
        assert classification.quality_score > 0
        assert "1920x1080 resolution" in classification.classification_reason

    def test_classify_file_from_filename(self, classifier, tmp_path) -> None:
        """Test file classification from filename patterns."""
        file_path = tmp_path / "anime_720p_webrip.mkv"
        file_path.write_text("Test content")

        anime_file = AnimeFile(
            file_path=file_path,
            filename=file_path.name,
            file_size=file_path.stat().st_size,
            file_extension=file_path.suffix,
            created_at=time.time(),
            modified_at=time.time(),
        )

        classification = classifier.classify_file(anime_file)

        assert classification.width == 1280
        assert classification.height == 720
        assert "webrip" in classification.classification_reason.lower()

    def test_find_best_file(self, classifier, tmp_path) -> None:
        """Test finding the best file among multiple versions."""
        # Create files with different qualities
        files = []
        for resolution, size in [("1080p", 1000), ("720p", 500), ("480p", 200)]:
            file_path = tmp_path / f"anime_{resolution}.mkv"
            file_path.write_text("x" * size)  # Different file sizes

            parsed_info = ParsedAnimeInfo(title="Test Anime", resolution=resolution)

            anime_file = AnimeFile(
                file_path=file_path,
                filename=file_path.name,
                file_size=file_path.stat().st_size,
                file_extension=file_path.suffix,
                created_at=time.time(),
                modified_at=time.time(),
                parsed_info=parsed_info,
            )
            files.append(anime_file)

        best_file = classifier.find_best_file(files)

        assert best_file is not None
        assert "1080p" in best_file.filename  # Should select highest resolution

    def test_group_by_series(self, classifier, tmp_path) -> None:
        """Test grouping files by series."""
        # Create files for different series
        files = []
        for series, episode in [("Series1", 1), ("Series1", 2), ("Series2", 1)]:
            file_path = tmp_path / f"{series}_E{episode:02d}.mkv"
            file_path.write_text("Test content")

            parsed_info = ParsedAnimeInfo(title=series, episode=episode)
            anime_file = AnimeFile(
                file_path=file_path,
                filename=file_path.name,
                file_size=file_path.stat().st_size,
                file_extension=file_path.suffix,
                created_at=time.time(),
                modified_at=time.time(),
                parsed_info=parsed_info,
            )
            files.append(anime_file)

        groups = classifier.group_by_series(files)

        assert len(groups) == 2
        assert "Series1" in groups
        assert "Series2" in groups
        assert len(groups["Series1"]) == 2
        assert len(groups["Series2"]) == 1


class TestFileNamer:
    """Test cases for FileNamer class."""

    @pytest.fixture
    def namer(self):
        """Create a FileNamer instance for testing."""
        return FileNamer()

    def test_generate_safe_filename(self, namer) -> None:
        """Test safe filename generation."""
        # Test invalid characters
        safe_name = namer.generate_safe_filename("test<file>.txt")
        assert safe_name == "test_file_.txt"

        # Test empty filename
        with pytest.raises(FileNamingError):  # Should raise FileNamingError
            namer.generate_safe_filename("")

        # Test reserved names
        safe_name = namer.generate_safe_filename("CON.txt")
        assert safe_name == "_CON.txt"

    def test_resolve_conflict_numeric_suffix(self, namer, tmp_path) -> None:
        """Test conflict resolution with numeric suffix."""
        target_path = tmp_path / "test_file.txt"
        target_path.write_text("Existing content")

        result = namer.resolve_conflict(target_path, NamingStrategy.SUFFIX_NUMERIC)

        assert result.conflict_resolved
        assert result.new_name == "test_file_001.txt"
        assert result.strategy_used == NamingStrategy.SUFFIX_NUMERIC

    def test_resolve_conflict_timestamp_suffix(self, namer, tmp_path) -> None:
        """Test conflict resolution with timestamp suffix."""
        target_path = tmp_path / "test_file.txt"
        target_path.write_text("Existing content")

        result = namer.resolve_conflict(target_path, NamingStrategy.SUFFIX_TIMESTAMP)

        assert result.conflict_resolved
        assert "test_file_" in result.new_name
        assert result.strategy_used == NamingStrategy.SUFFIX_TIMESTAMP

    def test_get_available_filename(self, namer, tmp_path) -> None:
        """Test getting available filename."""
        target_path = tmp_path / "test_file.txt"
        target_path.write_text("Existing content")

        available_path = namer.get_available_filename(target_path)

        assert available_path != target_path
        assert not available_path.exists()
        assert available_path.name.startswith("test_file_")

    def test_validate_filename(self, namer) -> None:
        """Test filename validation."""
        assert namer.validate_filename("valid_file.txt")
        assert not namer.validate_filename("invalid<file>.txt")
        assert not namer.validate_filename("")

    def test_get_filename_suggestions(self, namer) -> None:
        """Test filename suggestions generation."""
        suggestions = namer.get_filename_suggestions("test_file.txt", count=3)

        assert len(suggestions) <= 3
        assert all("test_file" in suggestion for suggestion in suggestions)
        assert all(suggestion.endswith(".txt") for suggestion in suggestions)


class TestFileMovementIntegration:
    """Integration tests for file movement system."""

    def test_end_to_end_file_movement(self, tmp_path) -> None:
        """Test complete file movement workflow."""
        # Setup
        file_mover = FileMover(temp_dir=tmp_path / "temp")
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()

        # Create test files
        test_files = []
        for i in range(3):
            file_path = source_dir / f"test_{i}.txt"
            file_path.write_text(f"Content {i}")
            test_files.append(file_path)

        # Move files
        results = []
        for file_path in test_files:
            target_path = target_dir / file_path.name
            result = file_mover.move_file(file_path, target_path, create_dirs=True)
            results.append(result)

        # Verify results
        assert all(result.success for result in results)
        assert all(not source.exists() for source in test_files)
        assert all((target_dir / source.name).exists() for source in test_files)

    def test_error_recovery_and_rollback(self, tmp_path) -> None:
        """Test error recovery and rollback functionality."""
        file_mover = FileMover(temp_dir=tmp_path / "temp")
        source_dir = tmp_path / "source"
        target_dir = tmp_path / "target"
        source_dir.mkdir()

        # Create test file
        test_file = source_dir / "test.txt"
        test_file.write_text("Test content")

        # Test manual rollback
        transaction_id = "test_transaction"
        file_mover._transactions[transaction_id] = MoveTransaction(
            transaction_id=transaction_id, operations=[], created_at=time.time()
        )

        # Move file successfully
        result1 = file_mover.move_file(
            test_file, target_dir / "test.txt", create_dirs=True, transaction_id=transaction_id
        )
        assert result1.success

        # Verify file was moved
        assert not test_file.exists()
        assert (target_dir / "test.txt").exists()

        # Rollback transaction
        rollback_success = file_mover.rollback_transaction(transaction_id)
        assert rollback_success

        # Verify rollback
        assert test_file.exists()  # Original file should be restored
        assert not (target_dir / "test.txt").exists()  # Moved file should be gone
