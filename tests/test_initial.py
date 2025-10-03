"""
Initial test file for AniVault project.

This module contains basic sanity tests to verify that the pytest framework
is properly configured and working correctly.
"""

from pathlib import Path

import pytest


class TestSanity:
    """Basic sanity tests to verify pytest is working."""

    def test_basic_assertion(self) -> None:
        """Basic sanity test to verify pytest is working."""
        assert True

    def test_basic_math(self) -> None:
        """Test basic mathematical operations."""
        assert 2 + 2 == 4
        assert 10 * 5 == 50
        assert 100 / 4 == 25

    def test_string_operations(self) -> None:
        """Test basic string operations."""
        assert "Hello" + " " + "World" == "Hello World"
        assert len("AniVault") == 8
        assert "anivault".upper() == "ANIVAULT"

    def test_list_operations(self) -> None:
        """Test basic list operations."""
        test_list = [1, 2, 3, 4, 5]
        assert len(test_list) == 5
        assert test_list[0] == 1
        assert test_list[-1] == 5
        assert 3 in test_list


class TestEnvironment:
    """Test environment and configuration."""

    @pytest.mark.unit
    def test_python_version(self) -> None:
        """Test that Python version meets requirements."""
        import sys

        assert sys.version_info >= (
            3,
            9,
        ), f"Python 3.9+ required, got {sys.version_info}"

    @pytest.mark.unit
    def test_imports(self) -> None:
        """Test that basic Python imports work correctly."""
        import os
        import sys
        from pathlib import Path

        assert isinstance(os.getcwd(), str)
        assert isinstance(Path.cwd(), Path)

    @pytest.mark.unit
    def test_project_structure(self) -> None:
        """Test that basic project structure exists."""
        project_root = Path(__file__).parent.parent

        # Check essential files exist
        essential_files = ["pyproject.toml", "README.md", "requirements.txt"]

        for file_name in essential_files:
            file_path = project_root / file_name
            assert file_path.exists(), f"Essential file missing: {file_name}"

        # Check directory structure
        essential_dirs = ["src", "tests", "docs"]

        for dir_name in essential_dirs:
            dir_path = project_root / dir_name
            assert dir_path.exists(), f"Essential directory missing: {dir_name}"
            assert dir_path.is_dir(), f"Path is not a directory: {dir_name}"

        # Check source structure
        src_dir = project_root / "src" / "anivault"
        assert src_dir.exists(), "Source directory missing: src/anivault"
        assert (src_dir / "__init__.py").exists(), "Package __init__.py missing"

    @pytest.mark.unit
    def test_test_structure(self) -> None:
        """Test that test structure is properly organized."""
        tests_dir = Path(__file__).parent

        # Check test directories exist
        test_dirs = ["core", "services", "shared", "benchmarks"]

        for dir_name in test_dirs:
            dir_path = tests_dir / dir_name
            if dir_path.exists():
                assert dir_path.is_dir(), f"Test path is not a directory: {dir_name}"

    @pytest.mark.unit
    def test_pytest_configuration(self) -> None:
        """Test that pytest is properly configured."""
        import pytest

        # Test that pytest is importable
        assert hasattr(pytest, "mark")
        assert hasattr(pytest, "fixture")
        assert hasattr(pytest, "parametrize")


if __name__ == "__main__":
    pytest.main([__file__])
