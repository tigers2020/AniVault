"""Simple consolidated tests."""

import pytest
from typer.testing import CliRunner
from anivault.cli.typer_app import app


class TestSimple:
    """Simple consolidated tests."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_app_help(self) -> None:
        """Test main app help."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.stdout

    def test_scan_help(self) -> None:
        """Test scan command help."""
        result = self.runner.invoke(app, ["scan", "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.stdout

    def test_match_help(self) -> None:
        """Test match command help."""
        result = self.runner.invoke(app, ["match", "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.stdout

    def test_organize_help(self) -> None:
        """Test organize command help."""
        result = self.runner.invoke(app, ["organize", "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.stdout

    def test_run_help(self) -> None:
        """Test run command help."""
        result = self.runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.stdout

    def test_invalid_command(self) -> None:
        """Test invalid command."""
        result = self.runner.invoke(app, ["invalid"])
        assert result.exit_code != 0

    def test_missing_args(self) -> None:
        """Test missing required arguments."""
        result = self.runner.invoke(app, ["scan"])
        assert result.exit_code != 0
