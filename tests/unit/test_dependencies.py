"""Test dependency compatibility and imports."""

import sys

import pytest


def test_click_import():
    """Test Click CLI framework import."""
    import click

    assert hasattr(click, "command")
    assert hasattr(click, "option")
    assert hasattr(click, "argument")


def test_tmdbv3api_import():
    """Test TMDB API client import."""
    import tmdbv3api

    assert hasattr(tmdbv3api, "TMDb")
    assert hasattr(tmdbv3api, "TV")
    assert hasattr(tmdbv3api, "Movie")


def test_anitopy_import():
    """Test anitopy file parsing import."""
    import anitopy

    assert hasattr(anitopy, "parse")
    assert callable(anitopy.parse)


def test_rich_import():
    """Test Rich UI library import."""
    import rich
    from rich.console import Console
    from rich.progress import Progress

    assert hasattr(rich, "print")
    assert hasattr(Console, "__init__")
    assert hasattr(Progress, "__init__")


def test_cryptography_import():
    """Test cryptography library import."""
    from cryptography.fernet import Fernet

    assert hasattr(Fernet, "generate_key")
    assert hasattr(Fernet, "__init__")


def test_parse_import():
    """Test parse library import."""
    import parse

    assert hasattr(parse, "parse")
    assert callable(parse.parse)


def test_requests_import():
    """Test requests library import."""
    import requests

    assert hasattr(requests, "get")
    assert hasattr(requests, "post")
    assert callable(requests.get)


def test_tomli_import():
    """Test TOML parsing library import."""
    if sys.version_info >= (3, 11):
        import tomllib

        assert hasattr(tomllib, "load")
    else:
        import tomli

        assert hasattr(tomli, "load")


def test_tomli_w_import():
    """Test TOML writing library import."""
    import tomli_w

    assert hasattr(tomli_w, "dump")
    assert callable(tomli_w.dump)


def test_pytest_import():
    """Test pytest framework import."""
    import pytest

    assert hasattr(pytest, "fixture")
    assert hasattr(pytest, "mark")


def test_ruff_import():
    """Test Ruff linter import."""
    import ruff

    # Ruff is primarily a CLI tool, test basic import
    assert ruff is not None


def test_mypy_import():
    """Test mypy type checker import."""
    import mypy

    # mypy is primarily a CLI tool, test basic import
    assert mypy is not None


def test_pyinstaller_import():
    """Test PyInstaller bundler import."""
    import PyInstaller

    assert hasattr(PyInstaller, "__version__")


def test_hypothesis_import():
    """Test Hypothesis property-based testing import."""
    import hypothesis
    from hypothesis import given
    from hypothesis import strategies as st

    assert hasattr(hypothesis, "settings")
    assert callable(given)
    assert hasattr(st, "text")


def test_pytest_httpx_import():
    """Test pytest-httpx plugin import."""
    import pytest_httpx

    assert hasattr(pytest_httpx, "HTTPXMock")


def test_pytest_mock_import():
    """Test pytest-mock plugin import."""
    import pytest_mock

    assert hasattr(pytest_mock, "MockFixture")


def test_pytest_cov_import():
    """Test pytest-cov plugin import."""
    import pytest_cov

    assert hasattr(pytest_cov, "plugin")


def test_pre_commit_import():
    """Test pre-commit hook framework import."""
    import pre_commit

    # pre-commit is primarily a CLI tool, test basic import
    assert pre_commit is not None


def test_anitopy_parsing_functionality():
    """Test anitopy parsing with sample anime filename."""
    import anitopy

    # Test with a typical anime filename
    sample_filename = "Attack on Titan S01E01 [1080p] [Subs].mkv"
    result = anitopy.parse(sample_filename)

    assert isinstance(result, dict)
    assert "anime_title" in result
    assert "episode_number" in result
    assert "file_extension" in result


def test_cryptography_functionality():
    """Test cryptography key generation and encryption."""
    from cryptography.fernet import Fernet

    # Generate a key
    key = Fernet.generate_key()
    assert isinstance(key, bytes)
    assert len(key) == 44  # Base64 encoded 32-byte key

    # Create Fernet instance
    f = Fernet(key)
    assert f is not None

    # Test encryption/decryption
    test_data = b"test data"
    encrypted = f.encrypt(test_data)
    decrypted = f.decrypt(encrypted)
    assert decrypted == test_data


def test_rich_console_functionality():
    """Test Rich console functionality."""
    from rich.console import Console

    console = Console()
    assert console is not None

    # Test basic print functionality (capture output)
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        console.print("Hello, World!")

    output = f.getvalue()
    assert "Hello, World!" in output


def test_click_command_creation():
    """Test Click command creation."""
    import click

    @click.command()
    @click.option("--name", default="World", help="Name to greet")
    def hello(name: str) -> None:
        """Simple hello command."""
        click.echo(f"Hello, {name}!")

    # Test command exists and has expected attributes
    assert hasattr(hello, "name")
    assert hasattr(hello, "params")
    assert hasattr(hello, "callback")


def test_tmdbv3api_initialization():
    """Test TMDB API client initialization."""
    import tmdbv3api

    # Test TMDb class initialization
    tmdb = tmdbv3api.TMDb()
    assert tmdb is not None

    # Test TV and Movie classes
    tv = tmdbv3api.TV()
    movie = tmdbv3api.Movie()

    assert tv is not None
    assert movie is not None


if __name__ == "__main__":
    pytest.main([__file__])
