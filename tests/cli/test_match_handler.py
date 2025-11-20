"""Unit tests for match_handler.

Tests for the match command handler including success and failure cases.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import typer

from anivault.cli.common.models import DirectoryPath, MatchOptions
from anivault.cli.match_handler import handle_match_command, match_command
from anivault.shared.constants import CLIDefaults


class TestHandleMatchCommand:
    """handle_match_command() 단위 테스트."""

    @patch("anivault.cli.match_handler.asyncio.run")
    @patch("anivault.cli.match_handler.run_match_pipeline")
    def test_success_returns_zero(
        self, mock_pipeline: Mock, mock_asyncio_run: Mock
    ) -> None:
        """성공 시 exit code 0 반환."""
        # Given
        mock_pipeline_result = 0
        mock_asyncio_run.return_value = mock_pipeline_result

        options = MatchOptions(
            directory=DirectoryPath(path=Path("/fake/dir")),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            output=None,
            json_output=False,
            verbose=False,
        )

        mock_console = Mock()
        mock_logger = Mock()

        # When
        result = handle_match_command(
            options, console=mock_console, logger_adapter=mock_logger
        )

        # Then
        assert result == CLIDefaults.EXIT_SUCCESS
        mock_logger.info.assert_called()
        mock_asyncio_run.assert_called_once()

    @patch("anivault.cli.match_handler.asyncio.run")
    @patch("anivault.cli.match_handler.run_match_pipeline")
    def test_failure_returns_error_code(
        self, mock_pipeline: Mock, mock_asyncio_run: Mock
    ) -> None:
        """실패 시 non-zero exit code 반환."""
        # Given
        mock_pipeline_result = 1
        mock_asyncio_run.return_value = mock_pipeline_result

        options = MatchOptions(
            directory=DirectoryPath(path=Path("/fake/dir")),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            output=None,
            json_output=False,
            verbose=False,
        )

        mock_console = Mock()
        mock_logger = Mock()

        # When
        result = handle_match_command(
            options, console=mock_console, logger_adapter=mock_logger
        )

        # Then
        assert result == CLIDefaults.EXIT_ERROR
        mock_logger.error.assert_called_once()

    @patch("anivault.cli.match_handler.asyncio.run")
    @patch("anivault.cli.match_handler.run_match_pipeline")
    def test_logs_command_start_and_completion(
        self, mock_pipeline: Mock, mock_asyncio_run: Mock
    ) -> None:
        """명령 시작/완료 로그 기록."""
        # Given
        mock_asyncio_run.return_value = 0

        options = MatchOptions(
            directory=DirectoryPath(path=Path("/fake/dir")),
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            output=None,
            json_output=False,
            verbose=False,
        )

        mock_logger = Mock()

        # When
        handle_match_command(options, logger_adapter=mock_logger)

        # Then
        assert mock_logger.info.call_count >= 2  # Start + Completion
        call_args_list = [str(call) for call in mock_logger.info.call_args_list]
        assert any("started" in str(call).lower() for call in call_args_list)
        assert any("completed" in str(call).lower() for call in call_args_list)


class TestMatchCommand:
    """match_command() CLI 진입점 테스트."""

    @patch("anivault.cli.match_handler.handle_match_command")
    @patch("anivault.cli.match_handler.get_cli_context")
    def test_creates_valid_options(
        self, mock_context: Mock, mock_handler: Mock
    ) -> None:
        """올바른 MatchOptions 생성."""
        # Given
        mock_context.return_value = Mock(verbose=0)
        mock_handler.return_value = CLIDefaults.EXIT_SUCCESS

        test_dir = Path("/test/anime")

        # When
        match_command(
            directory=test_dir,
            recursive=True,
            include_subtitles=True,
            include_metadata=True,
            output_file=None,
            json_output=False,
        )

        # Then
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        options = call_args[0][0]

        assert isinstance(options, MatchOptions)
        assert options.directory.path == test_dir
        assert options.recursive is True
        assert options.include_subtitles is True

    @patch("anivault.cli.match_handler.handle_match_command")
    @patch("anivault.cli.match_handler.get_cli_context")
    def test_exit_on_error(self, mock_context: Mock, mock_handler: Mock) -> None:
        """에러 시 typer.Exit 발생."""
        # Given
        mock_context.return_value = Mock(verbose=0)
        mock_handler.return_value = CLIDefaults.EXIT_ERROR

        # When & Then
        with pytest.raises(typer.Exit) as exc_info:
            match_command(
                directory=Path("/test"),
                recursive=True,
                include_subtitles=True,
                include_metadata=True,
                output_file=None,
                json_output=False,
            )

        assert exc_info.value.exit_code == CLIDefaults.EXIT_ERROR

    @patch("anivault.cli.match_handler.handle_match_command")
    @patch("anivault.cli.match_handler.get_cli_context")
    def test_validation_error_handling(
        self, mock_context: Mock, mock_handler: Mock
    ) -> None:
        """Validation 에러 처리."""
        # Given
        mock_context.return_value = Mock(verbose=0)
        mock_handler.side_effect = ValueError("Invalid directory")

        # When & Then
        with pytest.raises(typer.Exit) as exc_info:
            match_command(
                directory=Path("/invalid"),
                recursive=True,
                include_subtitles=True,
                include_metadata=True,
                output_file=None,
                json_output=False,
            )

        assert exc_info.value.exit_code == 1
