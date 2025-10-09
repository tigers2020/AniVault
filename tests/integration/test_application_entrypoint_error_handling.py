"""
Integration tests for application entrypoint error handling.

These tests verify that the application properly handles various error scenarios
at the entrypoint level, ensuring consistent error reporting and exit codes.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from anivault.cli.common.error_handler import handle_cli_error
from anivault.shared.constants import CLIDefaults
from anivault.shared.errors import (
    AniVaultError,
    ApplicationError,
    CliError,
    ErrorCode,
    InfrastructureError,
)


class TestApplicationEntrypointErrorHandling:
    """Test application entrypoint error handling scenarios."""

    def test_handle_cli_error_with_anivault_error(self):
        """Test handling of AniVaultError at entrypoint."""
        # Given
        original_error = ApplicationError(
            code=ErrorCode.APPLICATION_ERROR,
            message="Test application error",
            original_error=ValueError("Original error"),
        )
        command = "test-command"

        # When
        exit_code = handle_cli_error(original_error, command)

        # Then
        assert exit_code == CLIDefaults.EXIT_ERROR

    def test_handle_cli_error_with_infrastructure_error(self):
        """Test handling of InfrastructureError at entrypoint."""
        # Given
        original_error = InfrastructureError(
            code=ErrorCode.FILE_NOT_FOUND,
            message="File not found: /path/to/file",
        )
        command = "scan-command"

        # When
        exit_code = handle_cli_error(original_error, command)

        # Then
        assert exit_code == CLIDefaults.EXIT_ERROR

    def test_handle_cli_error_with_standard_exception(self):
        """Test handling of standard Python exceptions."""
        # Given
        original_error = FileNotFoundError("File not found")
        command = "test-command"

        # When
        exit_code = handle_cli_error(original_error, command)

        # Then
        assert exit_code == CLIDefaults.EXIT_ERROR

    def test_handle_cli_error_with_keyboard_interrupt(self):
        """Test handling of KeyboardInterrupt."""
        # Given
        original_error = KeyboardInterrupt()
        command = "test-command"

        # When
        exit_code = handle_cli_error(original_error, command)

        # Then
        assert exit_code == 130  # Standard exit code for SIGINT

    def test_handle_cli_error_with_json_output(self):
        """Test error handling with JSON output format."""
        # Given
        original_error = ApplicationError(
            code=ErrorCode.APPLICATION_ERROR,
            message="Test application error",
        )
        command = "test-command"

        # When
        with patch("sys.stdout") as mock_stdout:
            exit_code = handle_cli_error(original_error, command, json_output=True)

        # Then
        assert exit_code == CLIDefaults.EXIT_ERROR
        # Verify JSON output was written
        mock_stdout.buffer.write.assert_called()

    def test_handle_cli_error_with_json_output_failure(self):
        """Test error handling when JSON output fails."""
        # Given
        original_error = ApplicationError(
            code=ErrorCode.APPLICATION_ERROR,
            message="Test application error",
        )
        command = "test-command"

        # When
        with patch(
            "sys.stdout.buffer.write", side_effect=Exception("JSON write failed")
        ):
            with patch("sys.stderr") as mock_stderr:
                exit_code = handle_cli_error(original_error, command, json_output=True)

        # Then
        assert exit_code == CLIDefaults.EXIT_ERROR
        # Verify fallback to stderr
        mock_stderr.write.assert_called()

    def test_handle_cli_error_with_cli_error(self):
        """Test handling of CliError."""
        # Given
        original_error = CliError(
            code=ErrorCode.CLI_COMMAND_FAILED,
            message="CLI command failed",
            command="test-command",
            exit_code=42,
        )
        command = "test-command"

        # When
        exit_code = handle_cli_error(original_error, command)

        # Then
        assert exit_code == 42  # Custom exit code from CliError

    def test_handle_cli_error_with_data_processing_error(self):
        """Test handling of data processing errors."""
        # Given
        original_error = ValueError("Invalid data format")
        command = "parse-command"

        # When
        exit_code = handle_cli_error(original_error, command)

        # Then
        assert exit_code == CLIDefaults.EXIT_ERROR

    def test_handle_cli_error_with_unexpected_error(self):
        """Test handling of unexpected error types."""
        # Given
        original_error = RuntimeError("Unexpected runtime error")
        command = "test-command"

        # When
        exit_code = handle_cli_error(original_error, command)

        # Then
        assert exit_code == CLIDefaults.EXIT_ERROR

    def test_handle_cli_error_logging_context(self):
        """Test that error logging includes proper context."""
        # Given
        original_error = ApplicationError(
            code=ErrorCode.APPLICATION_ERROR,
            message="Test application error",
        )
        command = "test-command"

        # When
        with patch("anivault.cli.common.error_handler.logger") as mock_logger:
            handle_cli_error(original_error, command)

        # Then
        # Verify exception was logged with context
        mock_logger.exception.assert_called_once()
        call_args = mock_logger.exception.call_args
        assert "CLI error in %s: %s" in call_args[0][0]  # Format string pattern
        assert "context" in call_args[1]["extra"]

    def test_handle_cli_error_keyboard_interrupt_logging(self):
        """Test that KeyboardInterrupt is logged as warning, not exception."""
        # Given
        original_error = KeyboardInterrupt()
        command = "test-command"

        # When
        with patch("anivault.cli.common.error_handler.logger") as mock_logger:
            handle_cli_error(original_error, command)

        # Then
        # Verify warning was logged, not exception
        mock_logger.warning.assert_called_once()
        mock_logger.exception.assert_not_called()

    def test_handle_cli_error_text_output(self):
        """Test error handling with text output format."""
        # Given
        original_error = ApplicationError(
            code=ErrorCode.APPLICATION_ERROR,
            message="Test application error",
        )
        command = "test-command"

        # When
        with patch("sys.stderr") as mock_stderr:
            exit_code = handle_cli_error(original_error, command, json_output=False)

        # Then
        assert exit_code == CLIDefaults.EXIT_ERROR
        # Verify error message was written to stderr (with prefix from error handler)
        mock_stderr.write.assert_called_with(
            "Error: Application error: Test application error\n"
        )

    def test_handle_cli_error_structured_context(self):
        """Test that structured context is properly created."""
        # Given
        original_error = FileNotFoundError("File not found")
        command = "test-command"

        # When
        with patch("anivault.cli.common.error_handler.logger") as mock_logger:
            handle_cli_error(original_error, command)

        # Then
        # Verify structured context was created
        call_args = mock_logger.exception.call_args
        context = call_args[1]["extra"]["context"]
        assert context["command"] == "test-command"
        assert context["error_type"] == "FileNotFoundError"
        assert context["error_category"] == "file_system"
        assert context["json_output"] is False

    def test_handle_cli_error_with_original_error_preservation(self):
        """Test that original errors are properly preserved."""
        # Given
        original_error = ValueError("Original error")
        wrapped_error = ApplicationError(
            code=ErrorCode.APPLICATION_ERROR,
            message="Wrapped error",
            original_error=original_error,
        )
        command = "test-command"

        # When
        with patch("anivault.cli.common.error_handler.logger") as mock_logger:
            handle_cli_error(wrapped_error, command)

        # Then
        # Verify original error information is preserved
        call_args = mock_logger.exception.call_args
        context = call_args[1]["extra"]["context"]
        assert context["error_code"] == ErrorCode.APPLICATION_ERROR.value
