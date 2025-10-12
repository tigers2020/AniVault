"""Tests for setup_decorator module."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from anivault.cli.common.models import DirectoryPath
from anivault.cli.common.setup_decorator import setup_handler
from anivault.shared.errors import ApplicationError, ErrorCode


class TestSetupHandlerDecorator:
    """Tests for setup_handler decorator."""

    def test_basic_setup_without_requirements(self) -> None:
        """Test basic setup with no special requirements."""

        @setup_handler()
        def simple_handler(options: Mock, **kwargs: Any) -> str:
            # Verify logger_adapter was injected
            assert "logger_adapter" in kwargs
            assert isinstance(kwargs["logger_adapter"], logging.LoggerAdapter)
            return "success"

        options = Mock()
        result = simple_handler(options)
        assert result == "success"

    def test_requires_directory_validation(self) -> None:
        """Test directory validation when requires_directory=True."""
        with tempfile.TemporaryDirectory() as temp_dir:

            @setup_handler(requires_directory=True)
            def handler_with_dir(options: Mock, **kwargs: Any) -> str:
                # Directory should be validated
                return "success"

            options = Mock()
            options.directory = DirectoryPath(path=Path(temp_dir))

            result = handler_with_dir(options)
            assert result == "success"

    def test_requires_directory_validation_fails(self) -> None:
        """Test directory validation failure."""

        @setup_handler(requires_directory=True)
        def handler_with_dir(options: Mock, **kwargs: Any) -> str:
            return "success"

        options = Mock()
        options.directory = Mock()
        options.directory.path = Path("/nonexistent/directory")

        with pytest.raises(ApplicationError) as exc_info:
            handler_with_dir(options)

        assert exc_info.value.code == ErrorCode.DIRECTORY_NOT_FOUND

    def test_supports_json_skip_console(self) -> None:
        """Test that console is not created in JSON mode."""

        @setup_handler(supports_json=True, require_console=True)
        def json_handler(options: Mock, **kwargs: Any) -> dict[str, Any]:
            # Console should be None in JSON mode
            return {
                "console_injected": "console" in kwargs,
                "console_value": kwargs.get("console"),
            }

        options = Mock()
        options.json_output = True

        result = json_handler(options)
        assert result["console_injected"] is False or result["console_value"] is None

    def test_require_console_creates_console(self) -> None:
        """Test that console is created when require_console=True."""

        @setup_handler(require_console=True)
        def console_handler(options: Mock, **kwargs: Any) -> bool:
            # Console should be injected
            return "console" in kwargs and kwargs["console"] is not None

        options = Mock()
        options.json_output = False

        result = console_handler(options)
        assert result is True

    def test_normalize_extensions_list(self) -> None:
        """Test extension normalization."""

        @setup_handler()
        def handler_with_extensions(options: Mock, **kwargs: Any) -> Any:
            return options.extensions

        options = Mock()
        options.extensions = "mkv,MP4,avi"

        result = handler_with_extensions(options)
        assert result == [".mkv", ".mp4", ".avi"]

    def test_allow_dry_run_validation(self) -> None:
        """Test dry-run option validation."""

        @setup_handler(allow_dry_run=True)
        def dry_run_handler(options: Mock, **kwargs: Any) -> str:
            return "success"

        # Valid: dry-run without yes
        options = Mock()
        options.dry_run = True
        options.yes = False
        options.json_output = False
        options.verbose = False

        result = dry_run_handler(options)
        assert result == "success"

    def test_allow_dry_run_validation_fails_with_yes(self) -> None:
        """Test that dry-run with yes flag fails validation."""

        @setup_handler(allow_dry_run=True)
        def dry_run_handler(options: Mock, **kwargs: Any) -> str:
            return "success"

        options = Mock()
        options.dry_run = True
        options.yes = True
        options.json_output = False  # Add to avoid json+verbose check
        options.verbose = False  # Add to avoid json+verbose check

        with pytest.raises(ApplicationError) as exc_info:
            dry_run_handler(options)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "dry-run" in exc_info.value.message

    def test_json_with_verbose_validation_fails(self) -> None:
        """Test that JSON with verbose fails validation."""

        @setup_handler(allow_dry_run=True, supports_json=True)
        def json_handler(options: Mock, **kwargs: Any) -> str:
            return "success"

        options = Mock()
        options.json_output = True
        options.verbose = True
        options.dry_run = False
        options.yes = False

        with pytest.raises(ApplicationError) as exc_info:
            json_handler(options)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "mutually exclusive" in exc_info.value.message

    def test_logger_adapter_injection(self) -> None:
        """Test that LoggerAdapter is properly injected."""

        @setup_handler()
        def logging_handler(options: Mock, **kwargs: Any) -> Any:
            return kwargs["logger_adapter"]

        options = Mock()
        result = logging_handler(options)

        assert isinstance(result, logging.LoggerAdapter)
        assert "command" in result.extra
        assert "operation" in result.extra

    def test_combined_requirements(self) -> None:
        """Test decorator with multiple requirements."""
        with tempfile.TemporaryDirectory() as temp_dir:

            @setup_handler(
                requires_directory=True,
                supports_json=True,
                allow_dry_run=True,
                require_console=True,
            )
            def full_handler(options: Mock, **kwargs: Any) -> dict[str, Any]:
                return {
                    "console": kwargs.get("console"),
                    "logger_adapter": kwargs.get("logger_adapter"),
                    "directory": str(options.directory.path),
                }

            options = Mock()
            options.directory = DirectoryPath(path=Path(temp_dir))
            options.json_output = False
            options.dry_run = False
            options.yes = False
            options.verbose = False

            result = full_handler(options)

            assert result["console"] is not None
            assert result["logger_adapter"] is not None
            assert temp_dir in result["directory"]


class TestExtractOptions:
    """Tests for _extract_options helper."""

    def test_extract_from_args(self) -> None:
        """Test extracting options from positional arguments."""
        from anivault.cli.common.setup_decorator import _extract_options

        options = Mock()
        options.directory = "/test"

        result = _extract_options((options, "other"), {})
        assert result == options

    def test_extract_from_kwargs(self) -> None:
        """Test extracting options from keyword arguments."""
        from anivault.cli.common.setup_decorator import _extract_options

        options = Mock()
        options.json_output = True

        result = _extract_options((), {"options": options})
        assert result == options

    def test_extract_fallback_first_arg(self) -> None:
        """Test fallback to first argument."""
        from anivault.cli.common.setup_decorator import _extract_options

        first_arg = Mock()

        result = _extract_options((first_arg,), {})
        assert result == first_arg

    def test_extract_raises_when_no_args(self) -> None:
        """Test error when no arguments provided."""
        from anivault.cli.common.setup_decorator import _extract_options

        with pytest.raises(ValueError, match="No options object found"):
            _extract_options((), {})
