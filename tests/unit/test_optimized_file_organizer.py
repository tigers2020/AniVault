"""Tests for OptimizedFileOrganizer."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from src.anivault.core.organizer.file_organizer import OptimizedFileOrganizer
from src.anivault.core.models import ScannedFile, FileOperation, OperationType
from src.anivault.core.parser.models import ParsingResult, ParsingAdditionalInfo
from src.anivault.core.log_manager import OperationLogManager


class TestOptimizedFileOrganizer:
    """Test cases for OptimizedFileOrganizer."""

    @pytest.fixture
    def mock_log_manager(self):
        """Create a mock OperationLogManager."""
        return Mock(spec=OperationLogManager)

    @pytest.fixture
    def mock_settings(self):
        """Create a mock Settings object."""
        settings = Mock()
        settings.app = Mock()
        settings.app.destination_folder = Path("/test/destination")
        return settings

    @pytest.fixture
    def organizer(self, mock_log_manager, mock_settings):
        """Create OptimizedFileOrganizer instance."""
        return OptimizedFileOrganizer(mock_log_manager, mock_settings)

    @pytest.fixture
    def sample_scanned_file(self):
        """Create a sample ScannedFile for testing."""
        metadata = ParsingResult(
            title="Test Anime",
            episode=1,
            season=1,
            year=2023,
            quality="1080p",
            source="BluRay",
            confidence=0.9
        )
        return ScannedFile(
            file_path=Path("/test/source/test_anime_s01e01.mkv"),
            metadata=metadata,
            file_size=1024*1024*1024,  # 1GB

        )

    def test_initialization(self, mock_log_manager, mock_settings):
        """Test OptimizedFileOrganizer initialization."""
        organizer = OptimizedFileOrganizer(mock_log_manager, mock_settings)

        assert organizer.log_manager == mock_log_manager
        assert organizer.settings == mock_settings
        assert organizer._file_cache is not None
        assert len(organizer._file_cache) == 0

    def test_initialization_without_settings(self, mock_log_manager):
        """Test initialization without settings."""
        organizer = OptimizedFileOrganizer(mock_log_manager, None)

        assert organizer.log_manager == mock_log_manager
        # Settings should be loaded from default configuration
        assert organizer.settings is not None
        assert organizer._file_cache is not None

    def test_add_file(self, organizer, sample_scanned_file):
        """Test adding a file to the organizer."""
        organizer.add_file(sample_scanned_file)

        # Check that file was added to cache
        key = ("Test Anime", 1)
        cached_files = organizer._file_cache.get(key)
        assert cached_files is not None
        assert len(cached_files) == 1
        assert cached_files[0] == sample_scanned_file

    def test_add_file_without_metadata(self, organizer):
        """Test adding file without metadata."""
        # Create a ParsingResult with minimal data instead of None
        minimal_metadata = ParsingResult(
            title="Unknown",
            episode=None,
            season=None,
            year=None,
            release_group=None,
            confidence=0.0,
            parser_used="unknown",
            additional_info=ParsingAdditionalInfo()
        )

        file_without_metadata = ScannedFile(
            file_path=Path("/test/source/no_metadata.mkv"),
            metadata=minimal_metadata,
            file_size=1024,

        )

        organizer.add_file(file_without_metadata)

        # Should use default values
        key = ("Unknown", 0)
        cached_files = organizer._file_cache.get(key)
        assert cached_files is not None
        assert len(cached_files) == 1

    def test_add_duplicate_file(self, organizer, sample_scanned_file):
        """Test adding duplicate files."""
        # Add same file twice
        organizer.add_file(sample_scanned_file)
        organizer.add_file(sample_scanned_file)

        key = ("Test Anime", 1)
        cached_files = organizer._file_cache.get(key)
        assert cached_files is not None
        assert len(cached_files) == 2
        assert cached_files[0] == sample_scanned_file
        assert cached_files[1] == sample_scanned_file

    def test_find_duplicates_empty(self, organizer):
        """Test finding duplicates in empty organizer."""
        duplicates = organizer.find_duplicates()
        assert duplicates == []

    def test_find_duplicates_no_duplicates(self, organizer, sample_scanned_file):
        """Test finding duplicates when there are none."""
        organizer.add_file(sample_scanned_file)

        duplicates = organizer.find_duplicates()
        assert duplicates == []

    def test_find_duplicates_with_duplicates(self, organizer):
        """Test finding actual duplicates."""
        # Create two files with same title and episode
        file1 = ScannedFile(
            file_path=Path("/test/source/file1.mkv"),
            metadata=ParsingResult(title="Same Anime", episode=1),
            file_size=1024,

        )
        file2 = ScannedFile(
            file_path=Path("/test/source/file2.mkv"),
            metadata=ParsingResult(title="Same Anime", episode=1),
            file_size=2048,

        )

        organizer.add_file(file1)
        organizer.add_file(file2)

        duplicates = organizer.find_duplicates()
        assert len(duplicates) == 1
        assert len(duplicates[0]) == 2
        assert file1 in duplicates[0]
        assert file2 in duplicates[0]

    def test_generate_plan_empty(self, organizer):
        """Test generating plan with no files."""
        plan = organizer.generate_plan([])
        assert plan == []

    def test_generate_plan_with_files(self, organizer, sample_scanned_file):
        """Test generating organization plan."""
        organizer.add_file(sample_scanned_file)

        plan = organizer.generate_plan([sample_scanned_file])

        assert len(plan) == 1
        operation = plan[0]
        # Check if it's a FileOperation-like object
        assert hasattr(operation, 'operation_type')
        assert hasattr(operation, 'source_path')
        assert hasattr(operation, 'destination_path')
        assert operation.operation_type == OperationType.MOVE
        assert operation.source_path == sample_scanned_file.file_path

    def test_generate_plan_with_duplicates(self, organizer):
        """Test generating plan with duplicate files."""
        # Create duplicate files
        file1 = ScannedFile(
            file_path=Path("/test/source/file1.mkv"),
            metadata=ParsingResult(title="Duplicate Anime", episode=1),
            file_size=1024,

        )
        file2 = ScannedFile(
            file_path=Path("/test/source/file2.mkv"),
            metadata=ParsingResult(title="Duplicate Anime", episode=1),
            file_size=2048,

        )

        organizer.add_file(file1)
        organizer.add_file(file2)

        plan = organizer.generate_plan([file1, file2])

        # Should have operations for both files
        assert len(plan) == 2

        # Check that operations are for different files
        source_paths = {op.source_path for op in plan}
        assert file1.file_path in source_paths
        assert file2.file_path in source_paths

    def test_organize_dry_run(self, organizer, sample_scanned_file):
        """Test organize with dry_run=True."""
        organizer.add_file(sample_scanned_file)

        result = organizer.organize([sample_scanned_file], dry_run=True)

        # Should return FileOperation objects
        assert len(result) == 1
        operation = result[0]
        # Check if it's a FileOperation-like object
        assert hasattr(operation, 'operation_type')
        assert hasattr(operation, 'source_path')
        assert hasattr(operation, 'destination_path')

    def test_organize_execute(self, organizer, sample_scanned_file):
        """Test organize with dry_run=False."""
        # Mock the executor
        mock_executor = Mock()
        mock_executor.execute_batch.return_value = [Mock()]
        organizer._executor = mock_executor

        organizer.add_file(sample_scanned_file)

        result = organizer.organize([sample_scanned_file], dry_run=False)

        # Should call executor and return OperationResult objects
        mock_executor.execute_batch.assert_called_once()
        assert len(result) == 1

    def test_select_best_file_single(self, organizer, sample_scanned_file):
        """Test selecting best file when there's only one."""
        best_file = organizer._select_best_file([sample_scanned_file])
        assert best_file == sample_scanned_file

    def test_select_best_file_multiple(self, organizer):
        """Test selecting best file from multiple options."""
        # Create files with different qualities
        file1 = ScannedFile(
            file_path=Path("/test/source/file1.mkv"),
            metadata=ParsingResult(title="Test", episode=1, quality="720p"),
            file_size=1024,

        )
        file2 = ScannedFile(
            file_path=Path("/test/source/file2.mkv"),
            metadata=ParsingResult(title="Test", episode=1, quality="1080p"),
            file_size=2048,

        )

        best_file = organizer._select_best_file([file1, file2])

        # Should select the higher quality file
        assert best_file == file2

    def test_build_organization_path(self, organizer, sample_scanned_file):
        """Test building organization path."""
        path = organizer._build_organization_path(sample_scanned_file)

        # Should return a Path object
        assert isinstance(path, Path)
        # Should contain the title (sanitized)
        assert "Test_Anime" in str(path)
        # Should contain the original filename
        assert sample_scanned_file.file_path.name in str(path)

    def test_invalid_scanned_file(self, organizer):
        """Test handling invalid ScannedFile."""
        invalid_file = Mock()
        invalid_file.file_path = None
        invalid_file.metadata = None

        with pytest.raises(AttributeError):
            organizer.add_file(invalid_file)

    def test_file_with_none_episode(self, organizer):
        """Test handling file with None episode."""
        file_with_none_episode = ScannedFile(
            file_path=Path("/test/source/no_episode.mkv"),
            metadata=ParsingResult(title="No Episode", episode=None),
            file_size=1024,

        )

        organizer.add_file(file_with_none_episode)

        # Should use 0 as default episode
        key = ("No Episode", 0)
        cached_files = organizer._file_cache.get(key)
        assert cached_files is not None
        assert len(cached_files) == 1
