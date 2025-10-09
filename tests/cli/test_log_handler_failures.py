"""Failure-First tests for log_handler.py.

Stage 3.2: Test that _collect_log_list_data explicitly raises exceptions
instead of silently returning None for error conditions.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.cli.common.models import LogOptions
from anivault.cli.log_handler import _collect_log_list_data
from anivault.shared.errors import ApplicationError, ErrorCode, InfrastructureError


class TestCollectLogListDataFailures:
    """_collect_log_list_data() 실패 케이스 테스트."""

    def test_os_error_raises_infrastructure_error(self):
        """OS 에러 시 InfrastructureError 발생."""
        # Given: Mock options with log_dir
        options = Mock()
        mock_log_dir = Mock()
        mock_log_dir.path = Path("/test/logs")
        options.log_dir = mock_log_dir

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", side_effect=OSError("Disk error")):
                # When & Then
                with pytest.raises(InfrastructureError) as exc_info:
                    _collect_log_list_data(options)

                assert exc_info.value.code == ErrorCode.FILE_ACCESS_ERROR

    def test_value_error_raises_application_error(self):
        """ValueError 시 ApplicationError 발생."""
        # Given: Mock options
        options = Mock()
        mock_log_dir = Mock()
        mock_log_dir.path = Path("/test/logs")
        options.log_dir = mock_log_dir

        # Mock glob to return file, then stat() raises ValueError
        mock_file = Mock(spec=Path)
        mock_file.suffix = ".json"
        mock_file.name = "test.json"
        mock_file.stat.side_effect = ValueError("Invalid data")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", return_value=[mock_file]):
                # When & Then
                with pytest.raises(ApplicationError) as exc_info:
                    _collect_log_list_data(options)

                assert exc_info.value.code == ErrorCode.DATA_PROCESSING_ERROR

    def test_unexpected_error_raises_application_error(self):
        """예상치 못한 에러 시 ApplicationError 발생."""
        # Given: Mock options
        options = Mock()
        mock_log_dir = Mock()
        mock_log_dir.path = Path("/test/logs")
        options.log_dir = mock_log_dir

        # Mock glob to return file, then stat() raises RuntimeError
        mock_file = Mock(spec=Path)
        mock_file.suffix = ".json"
        mock_file.name = "test.json"
        mock_file.stat.side_effect = RuntimeError("Unexpected")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", return_value=[mock_file]):
                # When & Then
                with pytest.raises(ApplicationError) as exc_info:
                    _collect_log_list_data(options)

                assert exc_info.value.code == ErrorCode.APPLICATION_ERROR

    def test_valid_data_returns_dict(self):
        """유효한 데이터일 때 dict 반환."""
        # Given: Mock options and log files
        options = Mock()
        mock_log_dir = Mock()
        mock_log_dir.path = Path("/test/logs")
        options.log_dir = mock_log_dir

        # Mock log file
        mock_file = Mock(spec=Path)
        mock_file.suffix = ".json"
        mock_file.name = "test.json"
        mock_stat = Mock()
        mock_stat.st_size = 1024
        mock_stat.st_mtime = 1696320000.0
        mock_file.stat.return_value = mock_stat

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", return_value=[mock_file]):
                # When
                result = _collect_log_list_data(options)

                # Then
                assert result is not None
                assert "log_files" in result
                assert result["total_files"] == 1


# Note: _collect_log_list_data는 JSON 전용 함수
# 현재는 에러 시 None 반환하지만, 명확한 예외 발생으로 변경
