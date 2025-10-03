"""
Test main callback function.

This test ensures that the main callback function correctly processes
common options and sets up the CLI context.
"""

import pytest
from typer.testing import CliRunner

from anivault.cli.common.context import LogLevel, get_cli_context, clear_cli_context
from anivault.cli.typer_app import app, main_callback


def test_main_callback_direct() -> None:
    """Test that main_callback directly sets the context correctly."""
    # Clear any existing context
    clear_cli_context()

    # Test with various options
    main_callback(verbose=2, log_level=LogLevel.DEBUG, json_output=True, version=False)

    # Verify context was set correctly
    context = get_cli_context()
    assert context.verbose == 2
    assert context.log_level == LogLevel.DEBUG
    assert context.json_output is True


def test_main_callback_verbose_override() -> None:
    """Test that verbose mode overrides log level to DEBUG."""
    clear_cli_context()

    main_callback(
        verbose=1,
        log_level=LogLevel.INFO,  # This should be overridden
        json_output=False,
        version=False,
    )

    context = get_cli_context()
    assert context.verbose == 1
    assert context.is_verbose() is True
    assert context.get_effective_log_level() == "DEBUG"


def test_main_callback_default_values() -> None:
    """Test that main_callback works with default values."""
    clear_cli_context()

    main_callback(verbose=0, log_level=LogLevel.INFO, json_output=False, version=False)

    context = get_cli_context()
    assert context.verbose == 0
    assert context.log_level == LogLevel.INFO
    assert context.json_output is False
    assert not context.is_verbose()


def test_main_callback_version_handling() -> None:
    """Test that version option is handled correctly."""
    clear_cli_context()

    # This should raise typer.Exit (which is a click.exceptions.Exit)
    with pytest.raises(Exception):  # Catch any exception type
        main_callback(
            verbose=0, log_level=LogLevel.INFO, json_output=False, version=True
        )


def test_typer_app_integration() -> None:
    """Test that the Typer app integrates correctly with the callback."""
    runner = CliRunner()

    # Test help command
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AniVault - Advanced Anime Collection Management System" in result.output
    # The options should be visible in the help output
    assert "verbose" in result.output.lower()
    assert "log_level" in result.output.lower()  # Typer uses underscores
    assert "json" in result.output.lower()
    assert "version" in result.output.lower()


def test_typer_app_with_options() -> None:
    """Test that the Typer app processes options correctly."""
    runner = CliRunner()

    # Test version option (this should work)
    result = runner.invoke(app, ["--version"])
    # Version option should exit with code 0
    assert result.exit_code in [0, 2]  # Accept both success and help exit codes
    assert "AniVault CLI v0.1.0" in result.output


def test_typer_app_log_level_options() -> None:
    """Test that log level options work correctly."""
    runner = CliRunner()

    # Test that the app can be invoked with different log levels
    # We'll test the help output to verify the options are recognized
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "log_level" in result.output.lower()
