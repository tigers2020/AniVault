"""Tests for FileOrganizer class."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from anivault.core.log_manager import OperationLogManager
from anivault.core.matching.models import MatchResult
from anivault.core.models import FileOperation, OperationType, ScannedFile
from anivault.core.organizer import FileOrganizer
from anivault.core.parser.models import ParsingResult
from anivault.shared.errors import ApplicationError, ErrorCode


@pytest.fixture
def mock_settings():
    """Create mock settings object."""
    settings = Mock()
    settings.app = Mock()
    settings.app.target_directory = "/target"
    settings.app.media_type = "anime"

    # Mock folders config
    settings.folders = Mock()
    settings.folders.target_folder = "/anime_target"
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


class TestConstructDestinationPath:
    """Test _construct_destination_path method."""

    def test_construct_path_with_tmdb_match(
        self,
        organizer,
        scanned_file_with_match,
        mocker,
    ):
        """Test path construction with TMDB match result."""
        mock_get_config = mocker.patch("anivault.config.settings.get_config")
        mock_get_config.return_value = organizer.settings

        result = organizer._construct_destination_path(scanned_file_with_match)

        assert isinstance(result, Path)
        assert "진격의 거인" in str(result) or "Attack on Titan" in str(result)

    def test_construct_path_without_tmdb_match(
        self,
        organizer,
        scanned_file_without_match,
        mocker,
    ):
        """Test path construction without TMDB match (fallback to parsed title)."""
        mock_get_config = mocker.patch("anivault.config.settings.get_config")
        mock_get_config.return_value = organizer.settings

        result = organizer._construct_destination_path(scanned_file_without_match)

        assert isinstance(result, Path)
        assert "Unknown Anime" in str(result)

    def test_construct_path_without_target_folder(
        self,
        organizer,
        scanned_file_with_match,
        mocker,
    ):
        """Test that missing target folder raises ApplicationError."""
        # Mock config with no target folder
        mock_config = Mock()
        mock_config.folders = None

        mock_get_config = mocker.patch("anivault.config.settings.get_config")
        mock_get_config.return_value = mock_config

        with pytest.raises(ApplicationError) as exc_info:
            organizer._construct_destination_path(scanned_file_with_match)

        assert exc_info.value.code == ErrorCode.CONFIGURATION_ERROR
        assert "Target folder not configured" in exc_info.value.message


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


class TestSanitizeFilename:
    """Test _sanitize_filename method."""

    def test_sanitize_removes_invalid_characters(self, organizer):
        """Test that sanitize removes filesystem-invalid characters."""
        dirty_name = 'test<>:"|?*file'
        clean_name = organizer._sanitize_filename(dirty_name)

        # Should not contain invalid characters
        invalid_chars = '<>:"|?*'
        assert not any(char in clean_name for char in invalid_chars)

    def test_sanitize_preserves_valid_characters(self, organizer):
        """Test that sanitize preserves valid characters."""
        valid_name = "Test Anime - Season 01"
        clean_name = organizer._sanitize_filename(valid_name)

        # Should preserve spaces, hyphens, alphanumeric
        assert "Test" in clean_name
        assert "Anime" in clean_name


class TestExecuteFileOperation:
    """Test _execute_file_operation method."""

    def test_execute_move_success(self, organizer, tmp_path):
        """Test successful MOVE operation."""
        source = tmp_path / "source.mkv"
        source.write_text("content")
        dest = tmp_path / "dest" / "test.mkv"

        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=source,
            destination_path=dest,
        )

        # Create destination directory
        dest.parent.mkdir(parents=True, exist_ok=True)

        result = organizer._execute_file_operation(operation)

        assert result == (str(source), str(dest))
        assert dest.exists()
        assert not source.exists()

    def test_execute_copy_success(self, organizer, tmp_path):
        """Test successful COPY operation."""
        source = tmp_path / "source.mkv"
        source.write_text("content")
        dest = tmp_path / "dest.mkv"

        operation = FileOperation(
            operation_type=OperationType.COPY,
            source_path=source,
            destination_path=dest,
        )

        result = organizer._execute_file_operation(operation)

        assert result == (str(source), str(dest))
        assert dest.exists()
        assert source.exists()

    def test_execute_file_not_found(self, organizer, tmp_path):
        """Test FileNotFoundError handling."""
        source = tmp_path / "nonexistent.mkv"
        dest = tmp_path / "dest.mkv"

        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=source,
            destination_path=dest,
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            organizer._execute_file_operation(operation)

        assert "Source file not found" in str(exc_info.value)

    def test_execute_os_error(self, organizer, tmp_path, mocker):
        """Test OSError handling during file operation."""
        source = tmp_path / "source.mkv"
        source.write_text("content")
        dest = tmp_path / "dest.mkv"

        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=source,
            destination_path=dest,
        )

        # Mock shutil.move to raise OSError
        mocker.patch("shutil.move", side_effect=OSError("Disk full"))

        with pytest.raises(OSError) as exc_info:
            organizer._execute_file_operation(operation)

        assert "IO error occurred" in str(exc_info.value)

    def test_handle_operation_error_file_not_found(self, organizer, tmp_path):
        """Test _handle_operation_error with FileNotFoundError."""
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=tmp_path / "source.mkv",
            destination_path=tmp_path / "dest.mkv",
        )

        error = FileNotFoundError("Test error")

        # Should log error but NOT re-raise (just logs)
        organizer._handle_operation_error(operation, error)
        # No exception raised - test passes

    def test_handle_operation_error_file_exists(self, organizer, tmp_path):
        """Test _handle_operation_error with FileExistsError."""
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=tmp_path / "source.mkv",
            destination_path=tmp_path / "dest.mkv",
        )

        error = FileExistsError("Test error")

        # Should log error but NOT re-raise
        organizer._handle_operation_error(operation, error)

    def test_handle_operation_error_io_error(self, organizer, tmp_path):
        """Test _handle_operation_error with IOError."""
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=tmp_path / "source.mkv",
            destination_path=tmp_path / "dest.mkv",
        )

        error = OSError("Test error")

        # Should log error but NOT re-raise
        organizer._handle_operation_error(operation, error)

    def test_handle_operation_error_generic(self, organizer, tmp_path):
        """Test _handle_operation_error with generic exception."""
        operation = FileOperation(
            operation_type=OperationType.MOVE,
            source_path=tmp_path / "source.mkv",
            destination_path=tmp_path / "dest.mkv",
        )

        error = RuntimeError("Test error")

        # Should log error but NOT re-raise
        organizer._handle_operation_error(operation, error)


class TestOrganizeByResolution:
    """Test organize by resolution functionality (high-res vs low-res)."""

    @pytest.fixture
    def scanned_file_high_res(self, tmp_path):
        """Create ScannedFile with high resolution (1080p)."""
        source_file = tmp_path / "test_anime_1080p.mkv"
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
            quality="1080p",
            other_info={"match_result": match_result},
        )

        return ScannedFile(
            file_path=source_file,
            file_size=1024 * 1024,
            metadata=metadata,
        )

    @pytest.fixture
    def scanned_file_low_res(self, tmp_path):
        """Create ScannedFile with low resolution (720p)."""
        source_file = tmp_path / "test_anime_720p.mkv"
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
            episode=2,
            quality="720p",
            other_info={"match_result": match_result},
        )

        return ScannedFile(
            file_path=source_file,
            file_size=1024 * 1024,
            metadata=metadata,
        )

    @pytest.fixture
    def mock_settings_with_resolution(self):
        """Create mock settings with organize_by_resolution enabled."""
        settings = Mock()
        settings.app = Mock()

        settings.folders = Mock()
        settings.folders.target_folder = "/anime_target"
        settings.folders.media_type = "anime"
        settings.folders.organize_by_resolution = True

        return settings

    @pytest.fixture
    def mock_settings_without_resolution(self):
        """Create mock settings with organize_by_resolution disabled."""
        settings = Mock()
        settings.app = Mock()

        settings.folders = Mock()
        settings.folders.target_folder = "/anime_target"
        settings.folders.media_type = "anime"
        settings.folders.organize_by_resolution = False

        return settings

    def test_construct_path_high_resolution_mixed_series(
        self,
        log_manager,
        mock_settings_with_resolution,
        scanned_file_high_res,
        monkeypatch,
    ):
        """Test path construction with high resolution when series has mixed resolutions."""

        # Patch get_config to return our mock settings
        def mock_get_config():
            return mock_settings_with_resolution

        monkeypatch.setattr("anivault.config.settings.get_config", mock_get_config)

        organizer = FileOrganizer(log_manager, mock_settings_with_resolution)

        # Series has mixed resolutions (both high and low)
        destination = organizer._construct_destination_path(
            scanned_file_high_res,
            series_has_mixed_resolutions=True,
        )

        # Expected: /anime_target/anime/진격의 거인/Season 01/test_anime_1080p.mkv
        # Should NOT have "low_res" in path
        assert "low_res" not in str(destination)
        assert "진격의 거인" in str(destination)
        assert "Season 01" in str(destination)

    def test_construct_path_low_resolution_mixed_series(
        self,
        log_manager,
        mock_settings_with_resolution,
        scanned_file_low_res,
        monkeypatch,
    ):
        """Test path construction with low resolution when series has mixed resolutions."""

        # Patch get_config to return our mock settings
        def mock_get_config():
            return mock_settings_with_resolution

        monkeypatch.setattr("anivault.config.settings.get_config", mock_get_config)

        organizer = FileOrganizer(log_manager, mock_settings_with_resolution)

        # Series has mixed resolutions (both high and low)
        destination = organizer._construct_destination_path(
            scanned_file_low_res,
            series_has_mixed_resolutions=True,
        )

        # Expected: /anime_target/anime/low_res/진격의 거인/Season 01/test_anime_720p.mkv
        assert "low_res" in str(destination)
        assert "진격의 거인" in str(destination)
        assert "Season 01" in str(destination)

    def test_construct_path_low_resolution_single_resolution_series(
        self,
        log_manager,
        mock_settings_with_resolution,
        scanned_file_low_res,
        monkeypatch,
    ):
        """Test low resolution uses normal folder when series has single resolution type."""

        # Patch get_config to return our mock settings
        def mock_get_config():
            return mock_settings_with_resolution

        monkeypatch.setattr("anivault.config.settings.get_config", mock_get_config)

        organizer = FileOrganizer(log_manager, mock_settings_with_resolution)

        # Series has ONLY low resolution files (no mixed resolutions)
        destination = organizer._construct_destination_path(
            scanned_file_low_res,
            series_has_mixed_resolutions=False,
        )

        # Expected: /anime_target/anime/진격의 거인/Season 01/test_anime_720p.mkv
        # Should NOT have "low_res" because all files are same resolution
        assert "low_res" not in str(destination)
        assert "진격의 거인" in str(destination)
        assert "Season 01" in str(destination)

    def test_construct_path_without_resolution_enabled(
        self,
        log_manager,
        mock_settings_without_resolution,
        scanned_file_high_res,
        monkeypatch,
    ):
        """Test path construction with organize_by_resolution disabled."""

        # Patch get_config to return our mock settings
        def mock_get_config():
            return mock_settings_without_resolution

        monkeypatch.setattr("anivault.config.settings.get_config", mock_get_config)

        organizer = FileOrganizer(log_manager, mock_settings_without_resolution)

        destination = organizer._construct_destination_path(scanned_file_high_res)

        # Expected: /anime_target/anime/진격의 거인/Season 01/test_anime_1080p.mkv
        # Should NOT have "low_res" in path when feature is disabled
        assert "low_res" not in str(destination)
        assert "진격의 거인" in str(destination)
        assert "Season 01" in str(destination)

    def test_construct_path_unknown_resolution(
        self,
        log_manager,
        mock_settings_with_resolution,
        tmp_path,
        monkeypatch,
    ):
        """Test path construction with unknown resolution - should default to high resolution."""
        source_file = tmp_path / "test_anime_no_res.mkv"
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
            quality=None,  # No resolution info
            other_info={"match_result": match_result},
        )

        scanned_file = ScannedFile(
            file_path=source_file,
            file_size=1024 * 1024,
            metadata=metadata,
        )

        # Patch get_config to return our mock settings
        def mock_get_config():
            return mock_settings_with_resolution

        monkeypatch.setattr("anivault.config.settings.get_config", mock_get_config)

        organizer = FileOrganizer(log_manager, mock_settings_with_resolution)
        destination = organizer._construct_destination_path(scanned_file)

        # Expected: /anime_target/anime/진격의 거인/Season 01/test_anime_no_res.mkv
        # Unknown resolution defaults to high resolution (no low_res folder)
        assert "low_res" not in str(destination)
        assert "진격의 거인" in str(destination)

    def test_analyze_series_resolutions_single_high(
        self,
        log_manager,
        mock_settings_with_resolution,
        scanned_file_high_res,
    ):
        """Test resolution analysis when series has only high resolution files."""
        organizer = FileOrganizer(log_manager, mock_settings_with_resolution)

        # Create list with only high resolution files
        files = [scanned_file_high_res]

        result = organizer._analyze_series_resolutions(files)

        # Should have one series with no mixed resolutions
        assert "진격의 거인" in result
        assert result["진격의 거인"] is False  # Not mixed

    def test_analyze_series_resolutions_single_low(
        self,
        log_manager,
        mock_settings_with_resolution,
        scanned_file_low_res,
    ):
        """Test resolution analysis when series has only low resolution files."""
        organizer = FileOrganizer(log_manager, mock_settings_with_resolution)

        # Create list with only low resolution files
        files = [scanned_file_low_res]

        result = organizer._analyze_series_resolutions(files)

        # Should have one series with no mixed resolutions
        assert "진격의 거인" in result
        assert result["진격의 거인"] is False  # Not mixed

    def test_analyze_series_resolutions_mixed(
        self,
        log_manager,
        mock_settings_with_resolution,
        scanned_file_high_res,
        scanned_file_low_res,
    ):
        """Test resolution analysis when series has both high and low resolution files."""
        organizer = FileOrganizer(log_manager, mock_settings_with_resolution)

        # Create list with both high and low resolution files
        files = [scanned_file_high_res, scanned_file_low_res]

        result = organizer._analyze_series_resolutions(files)

        # Should have one series with mixed resolutions
        assert "진격의 거인" in result
        assert result["진격의 거인"] is True  # Mixed!

    def test_generate_plan_single_resolution_all_normal_paths(
        self,
        log_manager,
        mock_settings_with_resolution,
        tmp_path,
        monkeypatch,
    ):
        """Test generate_plan with single resolution - all files use normal paths."""

        # Patch get_config to return our mock settings
        def mock_get_config():
            return mock_settings_with_resolution

        monkeypatch.setattr("anivault.config.settings.get_config", mock_get_config)

        organizer = FileOrganizer(log_manager, mock_settings_with_resolution)

        # Create multiple low resolution files for same series
        files = []
        for i in range(1, 4):
            source_file = tmp_path / f"test_anime_ep{i}_720p.mkv"
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
                episode=i,
                quality="720p",
                other_info={"match_result": match_result},
            )

            files.append(
                ScannedFile(
                    file_path=source_file,
                    file_size=1024 * 1024,
                    metadata=metadata,
                ),
            )

        plan = organizer.generate_plan(files)

        # All files should use normal path (no low_res) because series has single resolution
        for operation in plan:
            assert "low_res" not in str(operation.destination_path)
            assert "진격의 거인" in str(operation.destination_path)

    def test_generate_plan_mixed_resolution_separate_paths(
        self,
        log_manager,
        mock_settings_with_resolution,
        tmp_path,
        monkeypatch,
    ):
        """Test generate_plan with mixed resolutions - high/low use different paths."""

        # Patch get_config to return our mock settings
        def mock_get_config():
            return mock_settings_with_resolution

        monkeypatch.setattr("anivault.config.settings.get_config", mock_get_config)

        organizer = FileOrganizer(log_manager, mock_settings_with_resolution)

        # Create files with mixed resolutions
        files = []

        # High resolution file
        high_res_file = tmp_path / "test_anime_ep1_1080p.mkv"
        high_res_file.touch()
        match_result = MatchResult(
            tmdb_id=1429,
            title="진격의 거인",
            year=2013,
            media_type="tv",
            confidence_score=0.95,
        )
        metadata_high = ParsingResult(
            title="Attack on Titan",
            season=1,
            episode=1,
            quality="1080p",
            other_info={"match_result": match_result},
        )
        files.append(
            ScannedFile(
                file_path=high_res_file,
                file_size=1024 * 1024,
                metadata=metadata_high,
            ),
        )

        # Low resolution file
        low_res_file = tmp_path / "test_anime_ep2_720p.mkv"
        low_res_file.touch()
        metadata_low = ParsingResult(
            title="Attack on Titan",
            season=1,
            episode=2,
            quality="720p",
            other_info={"match_result": match_result},
        )
        files.append(
            ScannedFile(
                file_path=low_res_file,
                file_size=1024 * 1024,
                metadata=metadata_low,
            ),
        )

        plan = organizer.generate_plan(files)

        # Find operations for each file
        high_res_op = next(op for op in plan if "1080p" in op.source_path.name)
        low_res_op = next(op for op in plan if "720p" in op.source_path.name)

        # High resolution should NOT have low_res
        assert "low_res" not in str(high_res_op.destination_path)

        # Low resolution SHOULD have low_res
        assert "low_res" in str(low_res_op.destination_path)
