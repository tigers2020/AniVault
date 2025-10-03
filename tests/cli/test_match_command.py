"""Tests for match command in Typer CLI."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from anivault.cli.typer_app import app


class TestMatchCommand:
    """Test cases for the match command."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_match_command_help(self) -> None:
        """Test that match command shows help."""
        result = self.runner.invoke(app, ["match", "--help"])
        assert result.exit_code == 0
        assert "Match anime files against TMDB database" in result.output
        assert "--recursive" in result.output
        assert "--include-subtitles" in result.output
        assert "--include-metadata" in result.output
        assert "--output" in result.output

    def test_match_command_with_nonexistent_directory(self) -> None:
        """Test match command with nonexistent directory."""
        result = self.runner.invoke(app, ["match", "/nonexistent/directory"])
        assert result.exit_code != 0
        assert "does not exist" in result.output or "Invalid value" in result.output

    @patch("anivault.cli.match_handler.handle_match_command")
    def test_match_command_success(self, mock_handler: Mock) -> None:
        """Test successful match command execution."""
        mock_handler.return_value = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["match", temp_dir])
            assert result.exit_code == 0
            mock_handler.assert_called_once()

    @patch("anivault.cli.match_handler.handle_match_command")
    def test_match_command_with_options(self, mock_handler: Mock) -> None:
        """Test match command with various options."""
        mock_handler.return_value = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(
                app,
                [
                    "match",
                    temp_dir,
                    "--no-recursive",
                    "--no-include-subtitles",
                    "--no-include-metadata",
                ],
            )
            assert result.exit_code == 0
            mock_handler.assert_called_once()

    @patch("anivault.cli.match_handler.handle_match_command")
    def test_match_command_with_output_file(self, mock_handler: Mock) -> None:
        """Test match command with output file."""
        mock_handler.return_value = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "output.json"
            result = self.runner.invoke(
                app,
                ["match", temp_dir, "--output", str(output_file)],
            )
            assert result.exit_code == 0
            mock_handler.assert_called_once()

    @patch("anivault.cli.match_handler.handle_match_command")
    def test_match_command_failure(self, mock_handler: Mock) -> None:
        """Test match command failure."""
        mock_handler.return_value = 1

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["match", temp_dir])
            assert result.exit_code == 1

    @patch("anivault.cli.match_handler.handle_match_command")
    def test_match_command_json_output(self, mock_handler: Mock) -> None:
        """Test match command with JSON output."""
        mock_handler.return_value = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(
                app,
                ["--json-output", "match", temp_dir],
            )
            assert result.exit_code == 0
            mock_handler.assert_called_once()

    def test_match_command_arguments_validation(self) -> None:
        """Test that match command validates arguments correctly."""
        # Test with file instead of directory
        with tempfile.NamedTemporaryFile() as temp_file:
            result = self.runner.invoke(app, ["match", temp_file.name])
            assert result.exit_code != 0

    @patch("anivault.cli.match_handler.handle_match_command")
    def test_match_command_mock_args_structure(self, mock_handler: Mock) -> None:
        """Test that the mock args object has the correct structure."""
        mock_handler.return_value = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["match", temp_dir])
            assert result.exit_code == 0

            # Verify the mock args object was created with correct attributes
            call_args = mock_handler.call_args[0][0]  # First positional argument
            assert hasattr(call_args, "directory")
            assert hasattr(call_args, "recursive")
            assert hasattr(call_args, "include_subtitles")
            assert hasattr(call_args, "include_metadata")
            assert hasattr(call_args, "output")
            assert hasattr(call_args, "json")
            assert hasattr(call_args, "verbose")
