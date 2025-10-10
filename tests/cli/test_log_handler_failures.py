"""Failure-First tests for log_handler helper functions.

Tests for failure cases in log helper functions.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.cli.helpers.log import collect_log_list_data
from anivault.shared.errors import ApplicationError, ErrorCode, InfrastructureError


class TestCollectLogListDataFailures:
    """collect_log_list_data() 실패 케이스 테스트."""

    def test_os_error_raises_infrastructure_error(self) -> None:
        """OSError 발생 시 InfrastructureError로 래핑."""
        # Given
        log_dir = Path("/fake/log/dir")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", side_effect=OSError("Permission denied")):
                # When & Then
                with pytest.raises(InfrastructureError) as exc_info:
                    collect_log_list_data(log_dir)

                assert exc_info.value.code == ErrorCode.FILE_ACCESS_ERROR

    def test_value_error_raises_application_error(self) -> None:
        """ValueError 발생 시 ApplicationError로 래핑."""
        # Given
        log_dir = Path("/fake/log/dir")

        # Mock file with stat() that raises ValueError
        mock_file = Mock(spec=Path)
        mock_file.suffix = ".log"
        mock_file.name = "test.log"
        mock_file.stat.side_effect = ValueError("Invalid data")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", return_value=[mock_file]):
                # When & Then
                with pytest.raises(ApplicationError) as exc_info:
                    collect_log_list_data(log_dir)

                assert exc_info.value.code == ErrorCode.DATA_PROCESSING_ERROR

    def test_no_logs_returns_empty_dict(self) -> None:
        """로그 없을 때 빈 dict 반환 (graceful)."""
        # Given
        log_dir = Path("/tmp/empty_logs_test")
        log_dir.mkdir(parents=True, exist_ok=True)

        try:
            # When
            result = collect_log_list_data(log_dir)

            # Then: graceful - 빈 리스트 반환
            assert result is not None
            assert isinstance(result, dict)
            assert result["log_files"] == []
            assert result["total_files"] == 0
        finally:
            # Cleanup
            if log_dir.exists():
                log_dir.rmdir()


# Note: collect_log_list_data는 graceful degradation 원칙을 따름
# 로그 파일이 없는 경우는 정상 상황이므로 빈 dict 반환
