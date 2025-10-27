"""Test match command handler functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from anivault.cli.match_handler import handle_match_command
from anivault.cli.common.models import MatchOptions, DirectoryPath
from anivault.shared.constants import CLIDefaults


class TestMatchHandler:
    """Test match command handler."""

    def test_match_success_returns_zero(self, tmp_path: Path) -> None:
        """Test successful match returns exit code 0."""
        # Given
        test_dir = tmp_path / "test_match"
        test_dir.mkdir()

        # Create test files
        (test_dir / "anime1.mkv").touch()
        (test_dir / "anime2.mp4").touch()

        options = MatchOptions(
            directory=DirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            output=None,
            json_output=False,
            verbose=False
        )

        # Mock the match pipeline and CLI context
        with patch("anivault.cli.match_handler.run_match_pipeline") as mock_pipeline, \
             patch("anivault.cli.match_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_match_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_match_empty_directory_returns_zero(self, tmp_path: Path) -> None:
        """Test matching empty directory returns exit code 0."""
        # Given
        test_dir = tmp_path / "empty_dir"
        test_dir.mkdir()

        options = MatchOptions(
            directory=DirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            output=None,
            json_output=False,
            verbose=False
        )

        # Mock the match pipeline and CLI context
        with patch("anivault.cli.match_handler.run_match_pipeline") as mock_pipeline, \
             patch("anivault.cli.match_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_match_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_match_pipeline_failure_returns_error(self, tmp_path: Path) -> None:
        """Test match pipeline failure returns error code."""
        # Given
        test_dir = tmp_path / "test_match"
        test_dir.mkdir()

        options = MatchOptions(
            directory=DirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            output=None,
            json_output=False,
            verbose=False
        )

        # Mock the match pipeline to fail and CLI context
        with patch("anivault.cli.match_handler.run_match_pipeline") as mock_pipeline, \
             patch("anivault.cli.match_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = 1
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_match_command(options)

            # Then
            assert result == 1
            mock_pipeline.assert_called_once()

    def test_match_with_json_output(self, tmp_path: Path) -> None:
        """Test match with JSON output enabled."""
        # Given
        test_dir = tmp_path / "test_match"
        test_dir.mkdir()

        options = MatchOptions(
            directory=DirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            output=None,
            json_output=True,
            verbose=False
        )

        # Mock the match pipeline and CLI context
        with patch("anivault.cli.match_handler.run_match_pipeline") as mock_pipeline, \
             patch("anivault.cli.match_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = True

            # When
            result = handle_match_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_match_with_recursive_disabled(self, tmp_path: Path) -> None:
        """Test match with recursive disabled."""
        # Given
        test_dir = tmp_path / "test_match"
        test_dir.mkdir()

        options = MatchOptions(
            directory=DirectoryPath(path=test_dir),
            recursive=False,
            include_subtitles=True,
            include_metadata=True,
            output=None,
            json_output=False,
            verbose=False
        )

        # Mock the match pipeline and CLI context
        with patch("anivault.cli.match_handler.run_match_pipeline") as mock_pipeline, \
             patch("anivault.cli.match_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_match_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_match_with_subtitles_disabled(self, tmp_path: Path) -> None:
        """Test match with subtitles disabled."""
        # Given
        test_dir = tmp_path / "test_match"
        test_dir.mkdir()

        options = MatchOptions(
            directory=DirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=False,
            include_metadata=True,
            output=None,
            json_output=False,
            verbose=False
        )

        # Mock the match pipeline and CLI context
        with patch("anivault.cli.match_handler.run_match_pipeline") as mock_pipeline, \
             patch("anivault.cli.match_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_match_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_match_with_metadata_disabled(self, tmp_path: Path) -> None:
        """Test match with metadata disabled."""
        # Given
        test_dir = tmp_path / "test_match"
        test_dir.mkdir()

        options = MatchOptions(
            directory=DirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=False,
            output=None,
            json_output=False,
            verbose=False
        )

        # Mock the match pipeline and CLI context
        with patch("anivault.cli.match_handler.run_match_pipeline") as mock_pipeline, \
             patch("anivault.cli.match_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_match_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_match_with_verbose_enabled(self, tmp_path: Path) -> None:
        """Test match with verbose output enabled."""
        # Given
        test_dir = tmp_path / "test_match"
        test_dir.mkdir()

        options = MatchOptions(
            directory=DirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            output=None,
            json_output=False,
            verbose=True
        )

        # Mock the match pipeline and CLI context
        with patch("anivault.cli.match_handler.run_match_pipeline") as mock_pipeline, \
             patch("anivault.cli.match_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_match_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()
