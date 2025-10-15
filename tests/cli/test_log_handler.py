"""Unit tests for log_handler.

Tests for the log command handler including success and failure cases.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer

from anivault.cli.log_handler import handle_log_command, log_command
from anivault.shared.constants import CLIDefaults, LogCommands
from anivault.shared.types.cli import CLIDirectoryPath, LogOptions


class TestHandleLogCommand:
    """handle_log_command() 단위 테스트."""

    @patch("anivault.cli.log_handler.print_log_list")
    @patch("anivault.cli.log_handler.get_cli_context")
    def test_list_command_success(self, mock_context: Mock, mock_print: Mock) -> None:
        """list 명령 성공 케이스."""
        # Given
        mock_context.return_value = Mock()
        mock_context.return_value.is_json_output_enabled.return_value = False
        mock_print.return_value = CLIDefaults.EXIT_SUCCESS

        options = LogOptions(
            log_command=LogCommands.LIST, log_dir=CLIDirectoryPath(path=Path("/tmp"))
        )

        mock_console = Mock()
        mock_logger = Mock()

        # When
        result = handle_log_command(
            options, console=mock_console, logger_adapter=mock_logger
        )

        # Then
        assert result == CLIDefaults.EXIT_SUCCESS
        mock_print.assert_called_once()
        mock_logger.info.assert_called()

    @patch("anivault.cli.log_handler.collect_log_list_data")
    @patch("anivault.cli.log_handler.format_json_output")
    @patch("anivault.cli.log_handler.get_cli_context")
    def test_list_command_json_output(
        self, mock_context: Mock, mock_format: Mock, mock_collect: Mock
    ) -> None:
        """list 명령 JSON 출력."""
        # Given
        mock_context.return_value = Mock()
        mock_context.return_value.is_json_output_enabled.return_value = True
        mock_collect.return_value = {"log_files": [], "total_files": 0}
        mock_format.return_value = b'{"success": true}'

        options = LogOptions(
            log_command=LogCommands.LIST, log_dir=CLIDirectoryPath(path=Path("/tmp"))
        )

        # When
        with patch("sys.stdout.buffer.write") as mock_write:
            result = handle_log_command(options)

        # Then
        assert result == CLIDefaults.EXIT_SUCCESS
        mock_collect.assert_called_once()
        mock_format.assert_called_once()

    @patch("anivault.cli.log_handler.get_cli_context")
    def test_unknown_command_error(self, mock_context: Mock) -> None:
        """알 수 없는 명령어 에러."""
        # Given
        mock_context.return_value = Mock()
        mock_context.return_value.is_json_output_enabled.return_value = False

        options = LogOptions(
            log_command="unknown", log_dir=CLIDirectoryPath(path=Path("/tmp"))
        )

        mock_console = Mock()

        # When
        result = handle_log_command(options, console=mock_console)

        # Then
        assert result == CLIDefaults.EXIT_ERROR
        mock_console.print.assert_called()

    @patch("anivault.cli.log_handler.print_log_list")
    @patch("anivault.cli.log_handler.get_cli_context")
    def test_logs_command_completion(
        self, mock_context: Mock, mock_print: Mock
    ) -> None:
        """명령 완료 로그 기록."""
        # Given
        mock_context.return_value = Mock()
        mock_context.return_value.is_json_output_enabled.return_value = False
        mock_print.return_value = CLIDefaults.EXIT_SUCCESS

        options = LogOptions(
            log_command=LogCommands.LIST, log_dir=CLIDirectoryPath(path=Path("/tmp"))
        )

        mock_logger = Mock()

        # When
        handle_log_command(options, logger_adapter=mock_logger)

        # Then
        assert mock_logger.info.call_count >= 2  # Start + Completion


class TestLogCommand:
    """log_command() CLI 진입점 테스트."""

    @patch("anivault.cli.log_handler.handle_log_command")
    def test_creates_valid_options(self, mock_handler: Mock) -> None:
        """올바른 LogOptions 생성."""
        # Given
        mock_handler.return_value = CLIDefaults.EXIT_SUCCESS
        test_dir = Path("/var/log")

        # When
        log_command(command=LogCommands.LIST, log_dir=test_dir)

        # Then
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        options = call_args[0][0]

        assert isinstance(options, LogOptions)
        assert options.log_command == LogCommands.LIST
        assert options.log_dir.path == test_dir

    @patch("anivault.cli.log_handler.handle_log_command")
    def test_exit_on_error(self, mock_handler: Mock) -> None:
        """에러 시 typer.Exit 발생."""
        # Given
        mock_handler.return_value = CLIDefaults.EXIT_ERROR

        # When & Then
        with pytest.raises(typer.Exit) as exc_info:
            log_command(command=LogCommands.LIST, log_dir=Path("/tmp"))

        assert exc_info.value.exit_code == CLIDefaults.EXIT_ERROR

    @patch("anivault.cli.log_handler.handle_log_command")
    def test_exception_handling(self, mock_handler: Mock) -> None:
        """예외 처리."""
        # Given
        mock_handler.side_effect = ValueError("Invalid log directory")

        # When & Then
        with pytest.raises(typer.Exit) as exc_info:
            log_command(command=LogCommands.LIST, log_dir=Path("/invalid"))

        assert exc_info.value.exit_code == CLIDefaults.EXIT_ERROR
