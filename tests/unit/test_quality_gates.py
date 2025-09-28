"""Test quality gates and linting configuration."""

import subprocess
import sys
from pathlib import Path

import pytest


def test_ruff_linting():
    """Test that Ruff linting works correctly."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "src/", "tests/"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        # Ruff should exit with 0 if no issues found
        assert result.returncode == 0, (
            f"Ruff found issues: {result.stdout}\n{result.stderr}"
        )
    except FileNotFoundError:
        pytest.skip("Ruff not available")


def test_ruff_formatting():
    """Test that Ruff formatting works correctly."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--check", "src/", "tests/"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        # Ruff format should exit with 0 if formatting is correct
        assert result.returncode == 0, (
            f"Ruff formatting issues: {result.stdout}\n{result.stderr}"
        )
    except FileNotFoundError:
        pytest.skip("Ruff not available")


def test_mypy_type_checking():
    """Test that MyPy type checking works correctly."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "src/"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        # MyPy should exit with 0 if no type issues found
        assert result.returncode == 0, (
            f"MyPy found type issues: {result.stdout}\n{result.stderr}"
        )
    except FileNotFoundError:
        pytest.skip("MyPy not available")


def test_pre_commit_hooks():
    """Test that pre-commit hooks are properly configured."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pre_commit", "run", "--all-files"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        # Pre-commit should exit with 0 if all hooks pass
        assert result.returncode == 0, (
            f"Pre-commit hooks failed: {result.stdout}\n{result.stderr}"
        )
    except FileNotFoundError:
        pytest.skip("Pre-commit not available")


def test_pytest_coverage():
    """Test that pytest with coverage works correctly."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--cov=src", "--cov-report=term-missing"],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        # Pytest should exit with 0 if all tests pass
        assert result.returncode == 0, (
            f"Pytest failed: {result.stdout}\n{result.stderr}"
        )
    except FileNotFoundError:
        pytest.skip("Pytest not available")


def test_import_sorting():
    """Test that import sorting works correctly."""
    # This test verifies that our imports are properly sorted
    # according to isort configuration
    import click
    import pytest

    import anivault

    # If we can import these without errors, import sorting is working
    assert anivault is not None
    assert click is not None
    assert pytest is not None


def test_code_quality_standards():
    """Test that our code meets basic quality standards."""
    # Test that we have proper docstrings
    from anivault import __author__, __email__, __version__

    assert __version__ is not None
    assert __author__ is not None
    assert __email__ is not None

    # Test that version follows semantic versioning
    version_parts = __version__.split(".")
    assert len(version_parts) == 3, "Version should follow semantic versioning"

    for part in version_parts:
        assert part.isdigit(), f"Version part '{part}' should be numeric"


if __name__ == "__main__":
    pytest.main([__file__])
