"""
Integration tests for CLI error handling.

This module tests the CLI error handling system integration,
focusing on the error handler utility functions.
"""

import json
import logging
import sys
from io import BytesIO
from unittest.mock import patch

from anivault.cli.common.error_handler import handle_cli_error
from anivault.shared.errors import (
    ApplicationError,
    ErrorCode,
    create_cli_error,
)


class TestCliErrorHandlingIntegration:
    """Integration tests for CLI error handling."""

    def test_handle_cli_error_integration_text_output(self, capsys):
        """Test CLI error handling with text output."""
        cli_error = create_cli_error("Integration test error", "test-command")

        exit_code = handle_cli_error(cli_error, "test-command", json_output=False)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Integration test error" in captured.err

    def test_handle_cli_error_integration_json_output(self):
        """Test CLI error handling with JSON output."""
        cli_error = create_cli_error("Integration test error", "test-command")

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
            assert "Integration test error" in output_data["errors"][0]
            assert output_data["data"]["error_code"] == "CLI_UNEXPECTED_ERROR"
        finally:
            sys.stdout.buffer.write = original_write

    def test_handle_cli_error_with_application_error(self, capsys):
        """Test handling ApplicationError in CLI context."""
        app_error = ApplicationError(
            ErrorCode.APPLICATION_ERROR,
            "Application integration error",
        )

        exit_code = handle_cli_error(app_error, "test-command", json_output=False)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Application error: Application integration error" in captured.err

    def test_handle_cli_error_with_keyboard_interrupt(self, capsys):
        """Test handling KeyboardInterrupt in CLI context."""
        keyboard_interrupt = KeyboardInterrupt()

        exit_code = handle_cli_error(keyboard_interrupt, "test-command", json_output=False)

        assert exit_code == 130  # Standard exit code for SIGINT
        captured = capsys.readouterr()
        assert "Command interrupted by user" in captured.err

    def test_handle_cli_error_with_file_not_found_error(self, capsys):
        """Test handling FileNotFoundError in CLI context."""
        file_error = FileNotFoundError("File not found")

        exit_code = handle_cli_error(file_error, "test-command", json_output=False)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "File system error: File not found" in captured.err

    def test_handle_cli_error_with_value_error(self, capsys):
        """Test handling ValueError in CLI context."""
        value_error = ValueError("Invalid value")

        exit_code = handle_cli_error(value_error, "test-command", json_output=False)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "Data processing error: Invalid value" in captured.err

    def test_handle_cli_error_logging_integration(self, caplog):
        """Test that error handling properly logs errors."""
        cli_error = create_cli_error("Logging test error", "test-command")

        with caplog.at_level(logging.ERROR):
            handle_cli_error(cli_error, "test-command", json_output=False)

        assert "CLI error in test-command: Logging test error" in caplog.text

    def test_handle_cli_error_json_serialization_failure(self, capsys):
        """Test handling JSON serialization failures."""
        cli_error = create_cli_error("JSON test error", "test-command")

        # Mock json.dumps to raise an exception
        with patch("json.dumps", side_effect=Exception("JSON serialization failed")):
            exit_code = handle_cli_error(cli_error, "test-command", json_output=True)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "JSON test error" in captured.err
        assert "JSON output failed" in captured.err
