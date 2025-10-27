"""Test scan command handler functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from anivault.cli.scan_handler import handle_scan_command
from anivault.shared.types.cli import ScanOptions, CLIDirectoryPath
from anivault.shared.constants import CLIDefaults


class TestScanHandler:
    """Test scan command handler."""

    def test_scan_success_returns_zero(self, tmp_path: Path) -> None:
        """Test successful scan returns exit code 0."""
        # Given
        test_dir = tmp_path / "test_scan"
        test_dir.mkdir()

        # Create test files
        (test_dir / "anime1.mkv").touch()
        (test_dir / "anime2.mp4").touch()

        options = ScanOptions(
            directory=CLIDirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            json_output=False
        )

        # Mock the scan pipeline and CLI context
        with patch("anivault.cli.scan_handler.run_scan_pipeline") as mock_pipeline, \
             patch("anivault.cli.scan_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = []
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_scan_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_scan_empty_directory_returns_zero(self, tmp_path: Path) -> None:
        """Test scanning empty directory returns exit code 0."""
        # Given
        test_dir = tmp_path / "empty_dir"
        test_dir.mkdir()

        options = ScanOptions(
            directory=CLIDirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            json_output=False
        )

        # Mock the scan pipeline and CLI context
        with patch("anivault.cli.scan_handler.run_scan_pipeline") as mock_pipeline, \
             patch("anivault.cli.scan_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = []
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_scan_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_scan_pipeline_failure_returns_error(self, tmp_path: Path) -> None:
        """Test scan pipeline failure returns error code."""
        # Given
        test_dir = tmp_path / "test_scan"
        test_dir.mkdir()

        options = ScanOptions(
            directory=CLIDirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            json_output=False
        )

        # Mock the scan pipeline to fail and CLI context
        with patch("anivault.cli.scan_handler.run_scan_pipeline") as mock_pipeline, \
             patch("anivault.cli.scan_handler.get_cli_context") as mock_context:
            mock_pipeline.side_effect = Exception("Scan failed")
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When/Then - expect ApplicationError to be raised
            with pytest.raises(Exception):  # ApplicationError is raised
                handle_scan_command(options)

            mock_pipeline.assert_called_once()

    def test_scan_with_json_output(self, tmp_path: Path) -> None:
        """Test scan with JSON output enabled."""
        # Given
        test_dir = tmp_path / "test_scan"
        test_dir.mkdir()

        options = ScanOptions(
            directory=CLIDirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            json_output=True
        )

        # Mock the scan pipeline and CLI context
        with patch("anivault.cli.scan_handler.run_scan_pipeline") as mock_pipeline, \
             patch("anivault.cli.scan_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = 0
            mock_context.return_value.is_json_output_enabled.return_value = True

            # When
            result = handle_scan_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_scan_with_recursive_disabled(self, tmp_path: Path) -> None:
        """Test scan with recursive disabled."""
        # Given
        test_dir = tmp_path / "test_scan"
        test_dir.mkdir()

        options = ScanOptions(
            directory=CLIDirectoryPath(path=test_dir),
            recursive=False,
            include_subtitles=True,
            include_metadata=True,
            json_output=False
        )

        # Mock the scan pipeline and CLI context
        with patch("anivault.cli.scan_handler.run_scan_pipeline") as mock_pipeline, \
             patch("anivault.cli.scan_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = []
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_scan_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_scan_with_subtitles_disabled(self, tmp_path: Path) -> None:
        """Test scan with subtitles disabled."""
        # Given
        test_dir = tmp_path / "test_scan"
        test_dir.mkdir()

        options = ScanOptions(
            directory=CLIDirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=False,
            include_metadata=True,
            json_output=False
        )

        # Mock the scan pipeline and CLI context
        with patch("anivault.cli.scan_handler.run_scan_pipeline") as mock_pipeline, \
             patch("anivault.cli.scan_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = []
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_scan_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()

    def test_scan_with_metadata_disabled(self, tmp_path: Path) -> None:
        """Test scan with metadata disabled."""
        # Given
        test_dir = tmp_path / "test_scan"
        test_dir.mkdir()

        options = ScanOptions(
            directory=CLIDirectoryPath(path=test_dir),
            recursive=True,
            include_subtitles=True,
            include_metadata=False,
            json_output=False
        )

        # Mock the scan pipeline and CLI context
        with patch("anivault.cli.scan_handler.run_scan_pipeline") as mock_pipeline, \
             patch("anivault.cli.scan_handler.get_cli_context") as mock_context:
            mock_pipeline.return_value = []
            mock_context.return_value.is_json_output_enabled.return_value = False

            # When
            result = handle_scan_command(options)

            # Then
            assert result == CLIDefaults.EXIT_SUCCESS
            mock_pipeline.assert_called_once()
