"""
Test CLI context management system.

This test ensures that the context management system works correctly
with ContextVar and provides proper type safety.
"""

import pytest
from pydantic import ValidationError

from anivault.cli.common.context import (
    CliContext,
    LogLevel,
    clear_cli_context,
    get_cli_context,
    set_cli_context,
)


def test_cli_context_creation() -> None:
    """Test that CliContext can be created with default values."""
    context = CliContext()

    assert context.verbose == 0
    assert context.log_level == LogLevel.INFO
    assert context.json_output is False


def test_cli_context_custom_values() -> None:
    """Test that CliContext can be created with custom values."""
    context = CliContext(verbose=2, log_level=LogLevel.DEBUG, json_output=True)

    assert context.verbose == 2
    assert context.log_level == LogLevel.DEBUG
    assert context.json_output is True


def test_cli_context_validation() -> None:
    """Test that CliContext validates input values."""
    # Test negative verbose value
    with pytest.raises(ValidationError):
        CliContext(verbose=-1)

    # Test invalid log level
    with pytest.raises(ValidationError):
        CliContext(log_level="INVALID")


def test_cli_context_is_verbose() -> None:
    """Test the is_verbose method."""
    context_normal = CliContext(verbose=0)
    context_verbose = CliContext(verbose=1)
    context_very_verbose = CliContext(verbose=3)

    assert not context_normal.is_verbose()
    assert context_verbose.is_verbose()
    assert context_very_verbose.is_verbose()


def test_cli_context_get_effective_log_level() -> None:
    """Test the get_effective_log_level method."""
    # Normal mode - should return specified log level
    context_info = CliContext(log_level=LogLevel.INFO)
    assert context_info.get_effective_log_level() == "INFO"

    context_warning = CliContext(log_level=LogLevel.WARNING)
    assert context_warning.get_effective_log_level() == "WARNING"

    # Verbose mode - should force DEBUG
    context_verbose = CliContext(verbose=1, log_level=LogLevel.INFO)
    assert context_verbose.get_effective_log_level() == "DEBUG"

    context_verbose_warning = CliContext(verbose=2, log_level=LogLevel.WARNING)
    assert context_verbose_warning.get_effective_log_level() == "DEBUG"


def test_context_var_operations() -> None:
    """Test ContextVar operations."""
    # Clear any existing context
    clear_cli_context()

    # Test setting and getting context
    context = CliContext(verbose=1, json_output=True)
    set_cli_context(context)

    retrieved_context = get_cli_context()
    assert retrieved_context.verbose == 1
    assert retrieved_context.json_output is True
    assert retrieved_context.log_level == LogLevel.INFO


def test_get_cli_context_without_set() -> None:
    """Test that get_cli_context raises error when context is not set."""
    clear_cli_context()

    with pytest.raises(RuntimeError, match="CLI context has not been initialized"):
        get_cli_context()


def test_log_level_enum() -> None:
    """Test that LogLevel enum works correctly."""
    assert LogLevel.DEBUG.value == "DEBUG"
    assert LogLevel.INFO.value == "INFO"
    assert LogLevel.WARNING.value == "WARNING"
    assert LogLevel.ERROR.value == "ERROR"
    assert LogLevel.CRITICAL.value == "CRITICAL"

    # Test that enum values can be used in CliContext
    context = CliContext(log_level=LogLevel.DEBUG)
    assert context.log_level == LogLevel.DEBUG
    assert context.log_level.value == "DEBUG"
