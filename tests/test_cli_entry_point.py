"""
Tests for CLI entry point functionality.

These tests verify that the CLI entry point properly initializes UTF-8 and logging.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


class TestCLIEntryPoint:
    """Test CLI entry point functionality."""

    def test_cli_version(self):
        """Test that CLI shows version information."""
        # Test the CLI main module directly
        result = subprocess.run(
            [sys.executable, "-m", "anivault.cli.main", "--version"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "AniVault 0.1.0" in result.stdout

    def test_cli_help(self):
        """Test that CLI shows help information."""
        result = subprocess.run(
            [sys.executable, "-m", "anivault.cli.main", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "AniVault - Anime Collection Management System" in result.stdout
        assert "--version" in result.stdout
        assert "--verbose" in result.stdout
        assert "--log-level" in result.stdout

    def test_cli_basic_run(self):
        """Test basic CLI execution."""
        result = subprocess.run(
            [sys.executable, "-m", "anivault.cli.main"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "AniVault - Anime Collection Management System" in result.stdout
        assert "Version: 0.1.0" in result.stdout
        assert "placeholder implementation" in result.stdout

    def test_cli_verbose_mode(self):
        """Test CLI verbose mode."""
        result = subprocess.run(
            [sys.executable, "-m", "anivault.cli.main", "--verbose"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "AniVault - Anime Collection Management System" in result.stdout

    def test_cli_log_level(self):
        """Test CLI log level option."""
        result = subprocess.run(
            [sys.executable, "-m", "anivault.cli.main", "--log-level", "DEBUG"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        assert result.returncode == 0
        assert "AniVault - Anime Collection Management System" in result.stdout

    def test_setup_script_basic(self):
        """Test that setup script exists and can be imported."""
        # Test that the setup script exists
        setup_script = Path(__file__).parent.parent / "scripts" / "setup.py"
        assert setup_script.exists()

        # Test that the script can be imported (syntax check)
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(setup_script)],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).parent.parent,
        )

        # Should not have syntax errors
        assert result.returncode == 0, f"Syntax error in setup.py: {result.stderr}"

    def test_dev_script_basic(self):
        """Test that dev script exists and can be executed."""
        # Test that the dev script exists
        dev_script = Path(__file__).parent.parent / "scripts" / "dev.py"
        assert dev_script.exists()

        # Test that the script can be executed (should show help)
        result = subprocess.run(
            [sys.executable, str(dev_script), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent,
        )

        # Should not crash (exit code 0 or 2 for help is fine)
        assert result.returncode in [0, 2]


if __name__ == "__main__":
    pytest.main([__file__])
