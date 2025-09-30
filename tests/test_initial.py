"""
Initial test file for AniVault project.

This module contains basic sanity tests to verify that the pytest framework
is properly configured and working correctly.
"""

import pytest


def test_sanity():
    """Basic sanity test to verify pytest is working."""
    assert True


def test_basic_math():
    """Test basic mathematical operations."""
    assert 2 + 2 == 4
    assert 10 * 5 == 50
    assert 100 / 4 == 25


def test_string_operations():
    """Test basic string operations."""
    assert "Hello" + " " + "World" == "Hello World"
    assert len("AniVault") == 8
    assert "anivault".upper() == "ANIVAULT"


def test_list_operations():
    """Test basic list operations."""
    test_list = [1, 2, 3, 4, 5]
    assert len(test_list) == 5
    assert test_list[0] == 1
    assert test_list[-1] == 5
    assert 3 in test_list


@pytest.mark.unit
def test_imports():
    """Test that basic Python imports work correctly."""
    import sys
    import os
    from pathlib import Path

    assert sys.version_info >= (3, 9)
    assert isinstance(os.getcwd(), str)
    assert isinstance(Path.cwd(), Path)


@pytest.mark.unit
def test_project_structure():
    """Test that basic project structure exists."""
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    # Check essential files exist
    assert (project_root / "pyproject.toml").exists()
    assert (project_root / "README.md").exists()
    assert (project_root / "src").exists()
    assert (project_root / "tests").exists()

    # Check source structure
    assert (project_root / "src" / "anivault").exists()
    assert (project_root / "src" / "anivault" / "__init__.py").exists()


if __name__ == "__main__":
    pytest.main([__file__])
