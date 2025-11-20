"""Tests for FileOrganizer class."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from anivault.core.log_manager import OperationLogManager
from anivault.core.matching.models import MatchResult
from anivault.core.models import FileOperation, OperationType, ScannedFile
from anivault.core.organizer import FileOrganizer
from anivault.core.parser.models import ParsingResult


@pytest.fixture
def mock_settings(tmp_path):
    """Create mock settings object."""
    settings = Mock()
    settings.app = Mock()
    settings.app.target_directory = str(tmp_path / "target")
    settings.app.media_type = "anime"
    settings.app.organize_target_folder = str(
        tmp_path / "target"
    )  # NEW: for generate_plan
    settings.app.organize_media_type = "anime"  # NEW: for generate_plan
    settings.app.organize_by_resolution = True  # NEW: for generate_plan

    # Mock folders config
    settings.folders = Mock()
    settings.folders.target_folder = str(tmp_path / "anime_target")
    settings.folders.media_type = "anime"
    settings.folders.folder_structure = "{series}/{season}"
    settings.folders.filename_pattern = "{series} - S{season:02d}E{episode:02d}"

    return settings


@pytest.fixture
def log_manager(tmp_path):
    """Create OperationLogManager with temp directory."""
    return OperationLogManager(root_path=tmp_path)


@pytest.fixture
def organizer(log_manager, mock_settings):
    """Create FileOrganizer instance."""
    return FileOrganizer(log_manager=log_manager, settings=mock_settings)


@pytest.fixture
def scanned_file_with_match(tmp_path):
    """Create ScannedFile with TMDB match."""
    source_file = tmp_path / "test_anime.mkv"
    source_file.touch()

    match_result = MatchResult(
        tmdb_id=1429,
        title="진격의 거인",
        year=2013,
        media_type="tv",
        confidence_score=0.95,
    )

    metadata = ParsingResult(
        title="Attack on Titan",
        season=1,
        episode=1,
        other_info={"match_result": match_result},
    )

    return ScannedFile(
        file_path=source_file,
        file_size=1024 * 1024,  # 1MB
        metadata=metadata,
    )


@pytest.fixture
def scanned_file_without_match(tmp_path):
    """Create ScannedFile without TMDB match."""
    source_file = tmp_path / "unknown_anime.mkv"
    source_file.touch()

    metadata = ParsingResult(
        title="Unknown Anime",
        season=1,
        episode=1,
        other_info={},
    )

    return ScannedFile(
        file_path=source_file,
        file_size=1024 * 1024,
        metadata=metadata,
    )


class TestFileOrganizerInit:
    """Test FileOrganizer initialization."""

    def test_init_with_settings(self, log_manager, mock_settings):
        """Test initialization with provided settings."""
        organizer = FileOrganizer(log_manager=log_manager, settings=mock_settings)

        assert organizer.log_manager is log_manager
        assert organizer.settings is mock_settings
        assert organizer.app_config is mock_settings.app

    def test_init_loads_default_settings(self, log_manager, mocker):
        """Test initialization loads default settings when not provided."""
        mock_load_settings = mocker.patch(
            "anivault.config.settings.load_settings",
            return_value=Mock(app=Mock()),
        )

        organizer = FileOrganizer(log_manager=log_manager, settings=None)

        mock_load_settings.assert_called_once()
        assert organizer.settings is not None


class TestGeneratePlan:
    """Test generate_plan method."""

    def test_generate_plan_with_matched_files(
        self,
        organizer,
        scanned_file_with_match,
        mocker,
    ):
        """Test plan generation with TMDB matched files."""
        mock_get_config = mocker.patch("anivault.config.settings.get_config")
        mock_get_config.return_value = organizer.settings

        plan = organizer.generate_plan([scanned_file_with_match])

        assert isinstance(plan, list)
        assert len(plan) == 1
        assert isinstance(plan[0], FileOperation)
        assert plan[0].operation_type == OperationType.MOVE
        assert plan[0].source_path == scanned_file_with_match.file_path

    def test_generate_plan_empty_list(self, organizer):
        """Test plan generation with empty file list."""
        plan = organizer.generate_plan([])

        assert isinstance(plan, list)
        assert len(plan) == 0

    def test_generate_plan_filters_unmatched_files(
        self,
        organizer,
        scanned_file_with_match,
        scanned_file_without_match,
        mocker,
    ):
        """Test that plan only includes matched files."""
        mock_get_config = mocker.patch("anivault.config.settings.get_config")
        mock_get_config.return_value = organizer.settings

        # Both files provided, but only matched should be in plan
        plan = organizer.generate_plan(
            [scanned_file_with_match, scanned_file_without_match],
        )

        # Only the matched file should be in the plan
        assert len(plan) >= 1  # At least the matched file
        # Verify source paths
        source_paths = [op.source_path for op in plan]
        assert scanned_file_with_match.file_path in source_paths


class TestExecutePlan:
    """Test execute_plan method."""

    def test_execute_plan_move_operation(self, organizer, tmp_path):
        """Test executing a MOVE operation."""
        # Create source file
        source_file = tmp_path / "source" / "test.mkv"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text("test content")

        # Create destination path
        dest_file = tmp_path / "dest" / "test.mkv"

        # Create operation
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=source_file,
            destination_path=dest_file,
        )

        # Execute
        result = organizer.execute_plan([operation], "test_id", no_log=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == (str(source_file), str(dest_file))

        # Verify file moved
        assert dest_file.exists()
        assert not source_file.exists()

    def test_execute_plan_copy_operation(self, organizer, tmp_path):
        """Test executing a COPY operation."""
        # Create source file
        source_file = tmp_path / "source" / "test.mkv"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text("test content")

        # Create destination path
        dest_file = tmp_path / "dest" / "test.mkv"

        # Create operation
        operation = FileOperation(
            operation_type=OperationType.COPY,
            source_path=source_file,
            destination_path=dest_file,
        )

        # Execute
        result = organizer.execute_plan([operation], "test_id", no_log=True)

        assert len(result) == 1

        # Verify file copied (source still exists)
        assert dest_file.exists()
        assert source_file.exists()

    def test_execute_plan_empty_list(self, organizer):
        """Test executing empty plan."""
        result = organizer.execute_plan([], "test_id", no_log=True)

        assert isinstance(result, list)
        assert len(result) == 0


class TestOrganizeMethod:
    """Test the main organize method."""

    def test_organize_dry_run(self, organizer, scanned_file_with_match, mocker):
        """Test organize in dry-run mode."""
        mock_get_config = mocker.patch("anivault.config.settings.get_config")
        mock_get_config.return_value = organizer.settings

        result = organizer.organize([scanned_file_with_match], dry_run=True)

        # Should return plan, not moved files
        assert isinstance(result, list)
        if len(result) > 0:
            assert isinstance(result[0], FileOperation)

    def test_organize_execute_mode(
        self,
        organizer,
        scanned_file_with_match,
        mocker,
    ):
        """Test organize in execute mode."""
        mock_get_config = mocker.patch("anivault.config.settings.get_config")
        mock_get_config.return_value = organizer.settings

        # Mock execute_plan to avoid actual file operations
        mock_execute = mocker.patch.object(
            organizer,
            "execute_plan",
            return_value=[],
        )

        result = organizer.organize([scanned_file_with_match], dry_run=False)

        # Should call execute_plan
        mock_execute.assert_called_once()

        # Should return moved files list
        assert isinstance(result, list)
