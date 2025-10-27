"""Test organize command handler functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from anivault.cli.organize_handler import handle_organize_command
from anivault.shared.types.cli import OrganizeOptions, CLIDirectoryPath
from anivault.shared.constants import CLIDefaults


class TestOrganizeHandler:
    """Test organize command handler."""

    def test_organize_success_returns_zero(self, tmp_path: Path) -> None:
        """Test successful organize returns exit code 0."""
        # Given
        test_dir = tmp_path / "test_organize"
        test_dir.mkdir()

        # Create test files
        (test_dir / "anime1.mkv").touch()
        (test_dir / "anime2.mp4").touch()

        options = OrganizeOptions(
            directory=CLIDirectoryPath(path=test_dir),
            dry_run=False,
            yes=True,
            enhanced=False,
            destination="Anime",
            extensions="mkv,mp4,avi",
            json_output=False
        )

        # Mock the organize pipeline and CLI context
        with patch("anivault.cli.organize_handler.get_scanned_files") as mock_get_files, \
             patch("anivault.cli.organize_handler.generate_organization_plan") as mock_generate_plan, \
             patch("anivault.cli.organize_handler.execute_organization_plan") as mock_execute, \
             patch("anivault.cli.organize_handler.get_cli_context") as mock_context:

            # Setup mocks
            mock_files = [Mock(), Mock()]
            mock_plan = [Mock(), Mock()]
            mock_get_files.return_value = mock_files
            mock_generate_plan.return_value = mock_plan
            mock_execute.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_organize_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_get_files.assert_called_once()
            mock_generate_plan.assert_called_once()
            mock_execute.assert_called_once()

    def test_organize_empty_directory_returns_zero(self, tmp_path: Path) -> None:
        """Test organizing empty directory returns exit code 0."""
        # Given
        test_dir = tmp_path / "empty_dir"
        test_dir.mkdir()

        options = OrganizeOptions(
            directory=CLIDirectoryPath(path=test_dir),
            dry_run=False,
            yes=True,
            enhanced=False,
            destination="Anime",
            extensions="mkv,mp4,avi",
            json_output=False
        )

        # Mock the organize pipeline and CLI context
        with patch("anivault.cli.organize_handler.get_scanned_files") as mock_get_files, \
             patch("anivault.cli.organize_handler.get_cli_context") as mock_context:

            # Setup mocks for empty directory
            mock_get_files.return_value = []
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_organize_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_get_files.assert_called_once()
            # Note: generate_organization_plan is not called for empty directory

    def test_organize_execution_failure_returns_error(self, tmp_path: Path) -> None:
        """Test organize execution failure returns error code."""
        # Given
        test_dir = tmp_path / "test_organize"
        test_dir.mkdir()

        options = OrganizeOptions(
            directory=CLIDirectoryPath(path=test_dir),
            dry_run=False,
            yes=True,
            enhanced=False,
            destination="Anime",
            extensions="mkv,mp4,avi",
            json_output=False
        )

        # Mock the organize pipeline to fail and CLI context
        with patch("anivault.cli.organize_handler.get_scanned_files") as mock_get_files, \
             patch("anivault.cli.organize_handler.generate_organization_plan") as mock_generate_plan, \
             patch("anivault.cli.organize_handler.execute_organization_plan") as mock_execute, \
             patch("anivault.cli.organize_handler.get_cli_context") as mock_context:

            # Setup mocks
            mock_files = [Mock(), Mock()]
            mock_plan = [Mock(), Mock()]
            mock_get_files.return_value = mock_files
            mock_generate_plan.return_value = mock_plan
            mock_execute.return_value = 1  # Execution failure
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_organize_command(options)

            # Then
            assert result == 1
            mock_get_files.assert_called_once()
            mock_generate_plan.assert_called_once()
            mock_execute.assert_called_once()

    def test_organize_with_dry_run(self, tmp_path: Path) -> None:
        """Test organize with dry run enabled."""
        # Given
        test_dir = tmp_path / "test_organize"
        test_dir.mkdir()

        options = OrganizeOptions(
            directory=CLIDirectoryPath(path=test_dir),
            dry_run=True,
            yes=False,  # Cannot use --dry-run with --yes
            enhanced=False,
            destination="Anime",
            extensions="mkv,mp4,avi",
            json_output=False
        )

        # Mock the organize pipeline and CLI context
        with patch("anivault.cli.organize_handler.get_scanned_files") as mock_get_files, \
             patch("anivault.cli.organize_handler.generate_organization_plan") as mock_generate_plan, \
             patch("anivault.cli.organize_handler.execute_organization_plan") as mock_execute, \
             patch("anivault.cli.organize_handler.get_cli_context") as mock_context:

            # Setup mocks
            mock_files = [Mock(), Mock()]
            mock_plan = [Mock(), Mock()]
            mock_get_files.return_value = mock_files
            mock_generate_plan.return_value = mock_plan
            mock_execute.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_organize_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_get_files.assert_called_once()
            mock_generate_plan.assert_called_once()
            mock_execute.assert_called_once()

    def test_organize_with_enhanced_mode(self, tmp_path: Path) -> None:
        """Test organize with enhanced mode enabled."""
        # Given
        test_dir = tmp_path / "test_organize"
        test_dir.mkdir()

        options = OrganizeOptions(
            directory=CLIDirectoryPath(path=test_dir),
            dry_run=False,
            yes=True,
            enhanced=True,
            destination="Anime",
            extensions="mkv,mp4,avi",
            json_output=False
        )

        # Mock the organize pipeline and CLI context
        with patch("anivault.cli.organize_handler.get_scanned_files") as mock_get_files, \
             patch("anivault.cli.organize_handler.generate_enhanced_organization_plan") as mock_generate_enhanced, \
             patch("anivault.cli.organize_handler.execute_organization_plan") as mock_execute, \
             patch("anivault.cli.organize_handler.get_cli_context") as mock_context:

            # Setup mocks
            mock_files = [Mock(), Mock()]
            mock_plan = [Mock(), Mock()]
            mock_get_files.return_value = mock_files
            mock_generate_enhanced.return_value = mock_plan
            mock_execute.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_organize_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_get_files.assert_called_once()
            mock_generate_enhanced.assert_called_once()
            mock_execute.assert_called_once()

    def test_organize_with_json_output(self, tmp_path: Path) -> None:
        """Test organize with JSON output enabled."""
        # Given
        test_dir = tmp_path / "test_organize"
        test_dir.mkdir()

        options = OrganizeOptions(
            directory=CLIDirectoryPath(path=test_dir),
            dry_run=False,
            yes=True,
            enhanced=False,
            destination="Anime",
            extensions="mkv,mp4,avi",
            json_output=True
        )

        # Mock the organize pipeline and CLI context
        with patch("anivault.cli.organize_handler.get_scanned_files") as mock_get_files, \
             patch("anivault.cli.organize_handler.generate_organization_plan") as mock_generate_plan, \
             patch("anivault.cli.organize_handler.execute_organization_plan") as mock_execute, \
             patch("anivault.cli.organize_handler.get_cli_context") as mock_context:

            # Setup mocks
            mock_files = [Mock(), Mock()]
            mock_plan = [Mock(), Mock()]
            mock_get_files.return_value = mock_files
            mock_generate_plan.return_value = mock_plan
            mock_execute.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = True

            # When
            result = handle_organize_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_get_files.assert_called_once()
            mock_generate_plan.assert_called_once()
            mock_execute.assert_called_once()

    def test_organize_with_custom_destination(self, tmp_path: Path) -> None:
        """Test organize with custom destination."""
        # Given
        test_dir = tmp_path / "test_organize"
        test_dir.mkdir()

        options = OrganizeOptions(
            directory=CLIDirectoryPath(path=test_dir),
            dry_run=False,
            yes=True,
            enhanced=False,
            destination="CustomAnime",
            extensions="mkv,mp4,avi",
            json_output=False
        )

        # Mock the organize pipeline and CLI context
        with patch("anivault.cli.organize_handler.get_scanned_files") as mock_get_files, \
             patch("anivault.cli.organize_handler.generate_organization_plan") as mock_generate_plan, \
             patch("anivault.cli.organize_handler.execute_organization_plan") as mock_execute, \
             patch("anivault.cli.organize_handler.get_cli_context") as mock_context:

            # Setup mocks
            mock_files = [Mock(), Mock()]
            mock_plan = [Mock(), Mock()]
            mock_get_files.return_value = mock_files
            mock_generate_plan.return_value = mock_plan
            mock_execute.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_organize_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_get_files.assert_called_once()
            mock_generate_plan.assert_called_once()
            mock_execute.assert_called_once()

    def test_organize_with_custom_extensions(self, tmp_path: Path) -> None:
        """Test organize with custom file extensions."""
        # Given
        test_dir = tmp_path / "test_organize"
        test_dir.mkdir()

        options = OrganizeOptions(
            directory=CLIDirectoryPath(path=test_dir),
            dry_run=False,
            yes=True,
            enhanced=False,
            destination="Anime",
            extensions="mkv,mp4,avi,mov",
            json_output=False
        )

        # Mock the organize pipeline and CLI context
        with patch("anivault.cli.organize_handler.get_scanned_files") as mock_get_files, \
             patch("anivault.cli.organize_handler.generate_organization_plan") as mock_generate_plan, \
             patch("anivault.cli.organize_handler.execute_organization_plan") as mock_execute, \
             patch("anivault.cli.organize_handler.get_cli_context") as mock_context:

            # Setup mocks
            mock_files = [Mock(), Mock()]
            mock_plan = [Mock(), Mock()]
            mock_get_files.return_value = mock_files
            mock_generate_plan.return_value = mock_plan
            mock_execute.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_organize_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_get_files.assert_called_once()
            mock_generate_plan.assert_called_once()
            mock_execute.assert_called_once()
