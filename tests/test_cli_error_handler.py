"""
Tests for CLI error handling utilities.

This module tests the CLI error handling system, including error formatting,
exception mapping, and consistent output generation.
"""

import json
import logging
import sys
from io import BytesIO
from unittest.mock import patch

from anivault.cli.common.error_handler import (
    format_json_output,
    handle_cli_error,
    handle_specific_exceptions,
    log_cli_operation_error,
    log_cli_operation_success,
)
from anivault.shared.errors import (
    ApplicationError,
    CliError,
    ErrorCode,
    InfrastructureError,
    create_cli_error,
    create_cli_output_error,
)


class TestFormatJsonOutput:
    """Test JSON output formatting."""

    def test_format_json_output_success(self):
        """Test successful JSON output formatting."""
        result = format_json_output(
            success=True,
            command="test",
            data={"count": 5},
        )

        data = json.loads(result.decode("utf-8"))
        assert data["success"] is True
        assert data["command"] == "test"
        assert data["data"]["count"] == 5
        assert "errors" not in data

    def test_format_json_output_with_errors(self):
        """Test JSON output formatting with errors."""
        result = format_json_output(
            success=False,
            command="test",
            errors=["Error 1", "Error 2"],
            data={"error_code": "TEST_ERROR"},
        )

        data = json.loads(result.decode("utf-8"))
        assert data["success"] is False
        assert data["command"] == "test"
        assert data["errors"] == ["Error 1", "Error 2"]
        assert data["data"]["error_code"] == "TEST_ERROR"

    def test_format_json_output_minimal(self):
        """Test minimal JSON output formatting."""
        result = format_json_output(
            success=True,
            command="test",
        )

        data = json.loads(result.decode("utf-8"))
        assert data["success"] is True
        assert data["command"] == "test"
        assert "errors" not in data
        assert "data" not in data


class TestHandleCliError:
    """Test CLI error handling."""

    def test_handle_cli_error_with_cli_error(self, capsys):
        """Test handling CliError instances."""
        cli_error = create_cli_error("Test CLI error", "test-command")

        exit_code = handle_cli_error(cli_error, "test-command", json_output=False)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Test CLI error" in captured.err

    def test_handle_cli_error_with_application_error(self, capsys):
        """Test handling ApplicationError instances."""
        app_error = ApplicationError(
            ErrorCode.APPLICATION_ERROR,
            "Test application error",
        )

        exit_code = handle_cli_error(app_error, "test-command", json_output=False)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Application error: Test application error" in captured.err

    def test_handle_cli_error_with_infrastructure_error(self, capsys):
        """Test handling InfrastructureError instances."""
        infra_error = InfrastructureError(
            ErrorCode.INFRASTRUCTURE_ERROR,
            "Test infrastructure error",
        )

        exit_code = handle_cli_error(infra_error, "test-command", json_output=False)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Infrastructure error: Test infrastructure error" in captured.err

    def test_handle_cli_error_with_file_system_error(self, capsys):
        """Test handling file system errors."""
        fs_error = FileNotFoundError("File not found")

        exit_code = handle_cli_error(fs_error, "test-command", json_output=False)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "File system error: File not found" in captured.err

    def test_handle_cli_error_with_data_processing_error(self, capsys):
        """Test handling data processing errors."""
        data_error = ValueError("Invalid value")

        exit_code = handle_cli_error(data_error, "test-command", json_output=False)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Data processing error: Invalid value" in captured.err

    def test_handle_cli_error_with_keyboard_interrupt(self, capsys):
        """Test handling keyboard interrupt."""
        kb_error = KeyboardInterrupt()

        exit_code = handle_cli_error(kb_error, "test-command", json_output=False)

        assert exit_code == 130
        captured = capsys.readouterr()
        assert "Command interrupted by user" in captured.err

    def test_handle_cli_error_with_json_output(self):
        """Test handling errors with JSON output."""
        cli_error = create_cli_error("Test CLI error", "test-command")

        # Mock sys.stdout.buffer.write to capture JSON output
        mock_buffer = BytesIO()
        original_write = sys.stdout.buffer.write

        def mock_write(data):
            mock_buffer.write(data)
            return len(data)

        try:
            sys.stdout.buffer.write = mock_write
            exit_code = handle_cli_error(cli_error, "test-command", json_output=True)

            assert exit_code == 1
            output_data = json.loads(mock_buffer.getvalue().decode("utf-8"))
            assert output_data["success"] is False
            assert output_data["command"] == "test-command"
            assert "Test CLI error" in output_data["errors"][0]
            assert output_data["data"]["error_code"] == "CLI_UNEXPECTED_ERROR"
        finally:
            sys.stdout.buffer.write = original_write

    def test_handle_cli_error_json_output_failure(self, capsys):
        """Test handling JSON output failure."""
        cli_error = create_cli_error("Test CLI error", "test-command")

        # Mock json.dumps to raise an exception
        with patch("json.dumps", side_effect=Exception("JSON serialization failed")):
            exit_code = handle_cli_error(cli_error, "test-command", json_output=True)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Test CLI error" in captured.err
        assert "JSON output failed" in captured.err


class TestHandleSpecificExceptions:
    """Test specific exception handling."""

    def test_handle_anivault_error(self, capsys):
        """Test handling AniVaultError instances."""
        anivault_error = ApplicationError(
            ErrorCode.APPLICATION_ERROR,
            "Test AniVault error",
        )

        exit_code = handle_specific_exceptions(
            anivault_error,
            "test-command",
            json_output=False,
        )

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Test AniVault error" in captured.err

    def test_handle_file_not_found_error(self, capsys):
        """Test handling FileNotFoundError."""
        fnf_error = FileNotFoundError("File not found")

        exit_code = handle_specific_exceptions(
            fnf_error,
            "test-command",
            json_output=False,
        )

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "File not found: File not found" in captured.err

    def test_handle_permission_error(self, capsys):
        """Test handling PermissionError."""
        perm_error = PermissionError("Permission denied")

        exit_code = handle_specific_exceptions(
            perm_error,
            "test-command",
            json_output=False,
        )

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Permission denied: Permission denied" in captured.err

    def test_handle_data_processing_error(self, capsys):
        """Test handling data processing errors."""
        data_error = ValueError("Invalid value")

        exit_code = handle_specific_exceptions(
            data_error,
            "test-command",
            json_output=False,
        )

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Data processing error: Invalid value" in captured.err

    def test_handle_specific_exceptions_with_json_output(self):
        """Test handling specific exceptions with JSON output."""
        fnf_error = FileNotFoundError("File not found")

        # Mock sys.stdout.buffer.write to capture the output
        mock_buffer = BytesIO()
        original_write = sys.stdout.buffer.write

        def mock_write(data):
            mock_buffer.write(data)
            return len(data)

        try:
            sys.stdout.buffer.write = mock_write
            exit_code = handle_specific_exceptions(
                fnf_error,
                "test-command",
                json_output=True,
            )

            assert exit_code == 1
            output_data = json.loads(mock_buffer.getvalue().decode("utf-8"))
            assert output_data["success"] is False
            assert output_data["command"] == "test-command"
            assert "File not found: File not found" in output_data["errors"][0]
            assert output_data["data"]["error_code"] == "FILE_NOT_FOUND"
        finally:
            sys.stdout.buffer.write = original_write


class TestCliOperationLogging:
    """Test CLI operation logging."""

    def test_log_cli_operation_success(self, caplog, capsys):
        """Test logging successful CLI operations."""
        with caplog.at_level(logging.INFO):
            log_cli_operation_success(
                command="test-command",
                duration_ms=123.45,
                context={"files_processed": 10},
            )

        # Check both caplog and stderr output
        captured = capsys.readouterr()
        output_text = caplog.text + captured.err

        assert "CLI command 'test-command' completed successfully" in output_text
        assert "123.45ms" in output_text

    def test_log_cli_operation_success_minimal(self, caplog):
        """Test logging successful CLI operations with minimal info."""
        with caplog.at_level(logging.INFO):
            log_cli_operation_success(command="test-command")

        assert "CLI command 'test-command' completed successfully" in caplog.text

    def test_log_cli_operation_error_with_anivault_error(self, caplog):
        """Test logging CLI operation errors with AniVaultError."""
        anivault_error = ApplicationError(
            ErrorCode.APPLICATION_ERROR,
            "Test error",
        )

        with caplog.at_level(logging.ERROR):
            log_cli_operation_error(
                error=anivault_error,
                command="test-command",
                context={"file": "test.txt"},
            )

        assert "CLI command 'test-command' failed: Test error" in caplog.text
        # Check that the error was logged with proper context
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "ERROR"
        assert "context" in record.__dict__

    def test_log_cli_operation_error_with_unexpected_error(self, caplog):
        """Test logging CLI operation errors with unexpected errors."""
        unexpected_error = RuntimeError("Unexpected error")

        log_cli_operation_error(
            error=unexpected_error,
            command="test-command",
        )

        assert "CLI command 'test-command' failed with unexpected error" in caplog.text


class TestCliErrorClasses:
    """Test CLI error classes and convenience functions."""

    def test_cli_error_creation(self):
        """Test CliError creation and properties."""
        cli_error = CliError(
            ErrorCode.CLI_UNEXPECTED_ERROR,
            "Test CLI error",
            command="test-command",
            exit_code=2,
        )

        assert cli_error.code == ErrorCode.CLI_UNEXPECTED_ERROR
        assert cli_error.message == "Test CLI error"
        assert cli_error.command == "test-command"
        assert cli_error.exit_code == 2

    def test_create_cli_error(self):
        """Test create_cli_error convenience function."""
        cli_error = create_cli_error(
            message="Test error",
            command="test-command",
            operation="test-operation",
            exit_code=3,
        )

        assert isinstance(cli_error, CliError)
        assert cli_error.message == "Test error"
        assert cli_error.command == "test-command"
        assert cli_error.exit_code == 3
        assert cli_error.context.operation == "test-operation"

    def test_create_cli_output_error(self):
        """Test create_cli_output_error convenience function."""
        output_error = create_cli_output_error(
            message="Output error",
            command="test-command",
            output_type="json",
        )

        assert isinstance(output_error, CliError)
        assert output_error.message == "Output error"
        assert output_error.command == "test-command"
        assert output_error.code == ErrorCode.CLI_OUTPUT_ERROR
        assert output_error.context.additional_data["output_type"] == "json"
