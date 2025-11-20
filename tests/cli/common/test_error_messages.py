"""Tests for CLI error messages module."""

from __future__ import annotations

from pathlib import Path

import orjson
import pytest

from anivault.cli.common.error_messages import (
    ErrorMessageContext,
    build_console_message,
    build_json_payload,
    build_log_context,
    get_message_catalog,
    mask_sensitive_paths,
)
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)


class TestErrorMessageContext:
    """Tests for ErrorMessageContext dataclass."""

    def test_create_context_with_application_error(self) -> None:
        """Test creating context with ApplicationError."""
        error = ApplicationError(
            ErrorCode.FILE_NOT_FOUND,
            "Test file not found",
            ErrorContext(operation="test_op"),
        )

        context = ErrorMessageContext(
            error=error,
            operation="scan_files",
            command_name="scan",
        )

        assert context.error == error
        assert context.operation == "scan_files"
        assert context.command_name == "scan"
        assert context.additional_data == {}

    def test_create_context_with_additional_data(self) -> None:
        """Test creating context with additional data."""
        error = InfrastructureError(
            ErrorCode.NETWORK_ERROR,
            "Network connection failed",
        )

        context = ErrorMessageContext(
            error=error,
            operation="fetch_metadata",
            command_name="match",
            additional_data={"retry_count": 3},
        )

        assert context.additional_data == {"retry_count": 3}


class TestBuildConsoleMessage:
    """Tests for build_console_message function."""

    def test_application_error_message(self) -> None:
        """Test console message for ApplicationError."""
        error = ApplicationError(
            ErrorCode.FILE_NOT_FOUND,
            "Test file not found",
            ErrorContext(
                operation="scan",
                additional_data={"file_path": "/home/user/test.mkv"},
            ),
        )

        context = ErrorMessageContext(
            error=error,
            operation="scan_files",
            command_name="scan",
        )

        message = build_console_message(context)

        assert "Application error during scan_files" in message
        assert "Test file not found" in message
        assert "~/test.mkv" in message  # Path should be masked
        assert "💡" in message  # Recovery hint should be present

    def test_infrastructure_error_message(self) -> None:
        """Test console message for InfrastructureError."""
        error = InfrastructureError(
            ErrorCode.NETWORK_ERROR,
            "Network timeout",
            ErrorContext(operation="fetch"),
        )

        context = ErrorMessageContext(
            error=error,
            operation="fetch_metadata",
            command_name="match",
        )

        message = build_console_message(context)

        assert "Infrastructure error during fetch_metadata" in message
        assert "Network timeout" in message

    def test_unexpected_error_message(self) -> None:
        """Test console message for unexpected Exception."""
        error = RuntimeError("Something went wrong")

        context = ErrorMessageContext(
            error=error,
            operation="process_files",
            command_name="organize",
        )

        message = build_console_message(context)

        assert "Unexpected error during process_files" in message
        assert "Something went wrong" in message


class TestBuildJsonPayload:
    """Tests for build_json_payload function."""

    def test_json_payload_structure(self) -> None:
        """Test JSON payload structure."""
        error = ApplicationError(
            ErrorCode.VALIDATION_ERROR,
            "Invalid input",
            ErrorContext(operation="validate"),
        )

        context = ErrorMessageContext(
            error=error,
            operation="validate_input",
            command_name="scan",
        )

        payload_bytes = build_json_payload(context)
        payload = orjson.loads(payload_bytes)

        assert payload["success"] is False
        assert payload["command"] == "scan"
        assert "Invalid input" in payload["errors"]
        assert payload["data"]["error_code"] == ErrorCode.VALIDATION_ERROR
        assert payload["data"]["operation"] == "validate_input"

    def test_json_payload_with_masked_paths(self) -> None:
        """Test JSON payload masks sensitive paths."""
        error = ApplicationError(
            ErrorCode.FILE_NOT_FOUND,
            "File not found",
            ErrorContext(
                operation="scan",
                additional_data={"file_path": "/home/user/private/video.mkv"},
            ),
        )

        context = ErrorMessageContext(
            error=error,
            operation="scan_files",
            command_name="scan",
        )

        payload_bytes = build_json_payload(context)
        payload = orjson.loads(payload_bytes)

        # Path in context should be masked
        context_data = payload["data"]["context"]
        assert "~/private/video.mkv" in context_data["additional_data"]["file_path"]

    def test_json_payload_utf8_encoding(self) -> None:
        """Test JSON payload handles UTF-8 characters."""
        error = ApplicationError(
            ErrorCode.PARSING_ERROR,
            "파일명 파싱 실패",  # Korean characters
        )

        context = ErrorMessageContext(
            error=error,
            operation="parse",
            command_name="scan",
        )

        payload_bytes = build_json_payload(context)
        payload = orjson.loads(payload_bytes)

        assert "파일명 파싱 실패" in payload["errors"]


class TestBuildLogContext:
    """Tests for build_log_context function."""

    def test_log_context_structure(self) -> None:
        """Test log context structure."""
        error = ApplicationError(
            ErrorCode.FILE_ACCESS_ERROR,
            "Cannot access file",
            ErrorContext(operation="read_file"),
        )

        context = ErrorMessageContext(
            error=error,
            operation="read_files",
            command_name="scan",
        )

        log_ctx = build_log_context(context)

        assert log_ctx["operation"] == "read_files"
        assert log_ctx["command"] == "scan"
        assert log_ctx["error_code"] == ErrorCode.FILE_ACCESS_ERROR

    def test_log_context_masks_paths(self) -> None:
        """Test log context masks sensitive paths."""
        error = InfrastructureError(
            ErrorCode.PERMISSION_DENIED,
            "Permission denied",
            ErrorContext(
                operation="write",
                additional_data={"file_path": "/home/user/secret/data.json"},
            ),
        )

        context = ErrorMessageContext(
            error=error,
            operation="write_cache",
            command_name="cache",
        )

        log_ctx = build_log_context(context)

        # Path in context should be masked
        assert "~" in log_ctx["context"]["additional_data"]["file_path"]
        assert "/home/user" not in log_ctx["context"]["additional_data"]["file_path"]

    def test_log_context_with_unexpected_error(self) -> None:
        """Test log context for unexpected exceptions."""
        error = ValueError("Invalid value")

        context = ErrorMessageContext(
            error=error,
            operation="validate",
            command_name="organize",
        )

        log_ctx = build_log_context(context)

        assert log_ctx["error_code"] == ErrorCode.CLI_UNEXPECTED_ERROR
        assert log_ctx["error_type"] == "ValueError"


class TestMaskSensitivePaths:
    """Tests for mask_sensitive_paths function."""

    def test_mask_home_directory_unix(self) -> None:
        """Test masking Unix home directory."""
        home = Path.home()
        test_path = home / "projects" / "anime" / "video.mkv"

        masked = mask_sensitive_paths(str(test_path))

        assert masked.startswith("~")
        assert "projects" in masked
        assert str(home) not in masked

    def test_mask_home_directory_windows(self) -> None:
        """Test masking Windows home directory."""
        home = Path.home()
        test_path = home / "Videos" / "anime.mkv"

        masked = mask_sensitive_paths(str(test_path))

        assert masked.startswith("~")
        assert "Videos" in masked

    def test_non_home_path_not_masked(self) -> None:
        """Test non-home paths are not masked."""
        test_path = "/var/tmp/test.mkv"

        masked = mask_sensitive_paths(test_path)

        assert masked == test_path

    def test_relative_path_not_masked(self) -> None:
        """Test relative paths are not masked."""
        test_path = "projects/anime/video.mkv"

        masked = mask_sensitive_paths(test_path)

        assert masked == test_path

    def test_invalid_path_handled(self) -> None:
        """Test invalid paths are handled gracefully."""
        invalid_path = ""

        masked = mask_sensitive_paths(invalid_path)

        assert masked == invalid_path


class TestRecoveryHints:
    """Tests for recovery hint messages."""

    def test_file_not_found_hint(self) -> None:
        """Test recovery hint for FILE_NOT_FOUND."""
        error = ApplicationError(
            ErrorCode.FILE_NOT_FOUND,
            "File not found",
        )

        context = ErrorMessageContext(
            error=error,
            operation="scan",
            command_name="scan",
        )

        message = build_console_message(context)

        assert "💡" in message
        assert "Check if the file path exists" in message

    def test_permission_denied_hint(self) -> None:
        """Test recovery hint for PERMISSION_DENIED."""
        error = ApplicationError(
            ErrorCode.PERMISSION_DENIED,
            "Permission denied",
        )

        context = ErrorMessageContext(
            error=error,
            operation="write",
            command_name="organize",
        )

        message = build_console_message(context)

        assert "💡" in message
        assert "permissions" in message.lower()

    def test_api_rate_limit_hint(self) -> None:
        """Test recovery hint for API_RATE_LIMIT."""
        error = InfrastructureError(
            ErrorCode.API_RATE_LIMIT,
            "Rate limit exceeded",
        )

        context = ErrorMessageContext(
            error=error,
            operation="fetch",
            command_name="match",
        )

        message = build_console_message(context)

        assert "💡" in message
        assert "Wait" in message


class TestMessageCatalog:
    """Tests for message catalog (i18n foundation)."""

    def test_get_default_catalog(self) -> None:
        """Test getting default (English) message catalog."""
        catalog = get_message_catalog()

        assert catalog["application_error_prefix"] == "Application error during"
        assert catalog["hint_prefix"] == "💡"

    def test_get_english_catalog_explicit(self) -> None:
        """Test getting English catalog explicitly."""
        catalog = get_message_catalog("en")

        assert "application_error_prefix" in catalog
        assert "infrastructure_error_prefix" in catalog

    def test_get_unknown_locale_fallback(self) -> None:
        """Test unknown locale falls back to English."""
        catalog = get_message_catalog("unknown")

        assert catalog == get_message_catalog("en")


class TestIntegration:
    """Integration tests for error message module."""

    def test_full_error_flow_application_error(self) -> None:
        """Test complete error flow for ApplicationError."""
        # Create error with full context
        error = ApplicationError(
            ErrorCode.FILE_NOT_FOUND,
            "Video file not found",
            ErrorContext(
                operation="scan_directory",
                additional_data={
                    "file_path": "/home/user/anime/episode01.mkv",
                    "expected_size": 1024 * 1024,
                },
            ),
        )

        context = ErrorMessageContext(
            error=error,
            operation="scan_files",
            command_name="scan",
            additional_data={"retry": False},
        )

        # Build all outputs
        console_msg = build_console_message(context)
        json_payload = build_json_payload(context)
        log_ctx = build_log_context(context)

        # Verify console message
        assert "Application error" in console_msg
        assert "Video file not found" in console_msg
        assert "~" in console_msg  # Path masked

        # Verify JSON payload
        payload_dict = orjson.loads(json_payload)
        assert payload_dict["success"] is False
        assert payload_dict["command"] == "scan"
        assert payload_dict["data"]["error_code"] == ErrorCode.FILE_NOT_FOUND

        # Verify log context
        assert log_ctx["operation"] == "scan_files"
        assert log_ctx["error_code"] == ErrorCode.FILE_NOT_FOUND
        assert "file_path" in log_ctx["context"]["additional_data"]

    def test_full_error_flow_infrastructure_error(self) -> None:
        """Test complete error flow for InfrastructureError."""
        error = InfrastructureError(
            ErrorCode.NETWORK_ERROR,
            "Connection timeout",
            ErrorContext(
                operation="fetch_metadata",
                additional_data={"url": "https://api.themoviedb.org"},
            ),
        )

        context = ErrorMessageContext(
            error=error,
            operation="fetch_tmdb",
            command_name="match",
        )

        # Build all outputs
        console_msg = build_console_message(context)
        json_payload = build_json_payload(context)
        log_ctx = build_log_context(context)

        # All outputs should contain error info
        assert "Infrastructure error" in console_msg
        assert "Connection timeout" in console_msg

        payload_dict = orjson.loads(json_payload)
        assert payload_dict["data"]["error_code"] == ErrorCode.NETWORK_ERROR

        assert log_ctx["error_code"] == ErrorCode.NETWORK_ERROR

    def test_full_error_flow_unexpected_error(self) -> None:
        """Test complete error flow for unexpected Exception."""
        error = RuntimeError("Unexpected runtime error")

        context = ErrorMessageContext(
            error=error,
            operation="process_data",
            command_name="organize",
        )

        # Build all outputs
        console_msg = build_console_message(context)
        json_payload = build_json_payload(context)
        log_ctx = build_log_context(context)

        # Unexpected errors should be handled gracefully
        assert "Unexpected error" in console_msg
        assert "Unexpected runtime error" in console_msg

        payload_dict = orjson.loads(json_payload)
        assert payload_dict["data"]["error_code"] == ErrorCode.CLI_UNEXPECTED_ERROR

        assert log_ctx["error_type"] == "RuntimeError"
