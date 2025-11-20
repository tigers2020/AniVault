"""Failure-First tests for rollback_handler helper functions.

Tests for failure cases in rollback helper functions.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from anivault.cli.helpers.rollback import (
    generate_rollback_plan,
    load_rollback_log,
)
from anivault.shared.errors import ApplicationError, ErrorCode, InfrastructureError


class TestLoadRollbackLogFailures:
    """load_rollback_log() 실패 케이스 테스트."""

    def test_missing_log_id_raises_error(self) -> None:
        """로그 ID 없을 때 ApplicationError 발생."""
        # Given
        log_id = "1234567890"

        with patch("anivault.cli.helpers.rollback.OperationLogManager") as mock_log_mgr:
            from anivault.core.log_manager import LogFileNotFoundError

            mock_log_mgr.return_value.get_log_by_id.side_effect = LogFileNotFoundError(
                Path("/fake/log.log")
            )

            # When & Then: 로그 파일 없을 때 ApplicationError
            with pytest.raises(ApplicationError) as exc_info:
                load_rollback_log(log_id)

            assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND

    def test_log_file_not_found_raises_error(self) -> None:
        """로그 파일 없을 때 ApplicationError 발생."""
        # Given
        log_id = "nonexistent_log"

        with patch("anivault.cli.helpers.rollback.OperationLogManager") as mock_log_mgr:
            from anivault.core.log_manager import LogFileNotFoundError

            mock_log_mgr.return_value.get_log_by_id.side_effect = LogFileNotFoundError(
                Path("/fake/log.log")
            )

            # When & Then
            with pytest.raises(ApplicationError) as exc_info:
                load_rollback_log(log_id)

            assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND

    def test_log_file_access_error_raises_infrastructure_error(self) -> None:
        """로그 파일 액세스 에러 시 InfrastructureError 발생."""
        # Given
        log_id = "test_log"

        with patch("anivault.cli.helpers.rollback.OperationLogManager") as mock_log_mgr:
            mock_log_mgr.return_value.get_log_by_id.side_effect = OSError(
                "Permission denied"
            )

            # When & Then
            with pytest.raises(InfrastructureError) as exc_info:
                load_rollback_log(log_id)

            assert exc_info.value.code == ErrorCode.FILE_ACCESS_ERROR


class TestGenerateRollbackPlanFailures:
    """generate_rollback_plan() 실패 케이스 테스트."""

    def test_invalid_log_file_raises_error(self) -> None:
        """잘못된 로그 파일 형식 시 ApplicationError 발생."""
        # Given
        invalid_log_path = Path("/fake/invalid_log.json")

        with patch("anivault.cli.helpers.rollback.RollbackManager") as mock_rb_mgr:
            mock_rb_mgr.return_value.generate_rollback_plan.return_value = None

            # When & Then
            with pytest.raises(ApplicationError) as exc_info:
                generate_rollback_plan(invalid_log_path)

            assert exc_info.value.code == ErrorCode.DATA_PROCESSING_ERROR

    def test_corrupted_log_file_raises_error(self) -> None:
        """손상된 로그 파일 읽기 시 InfrastructureError 발생."""
        # Given
        log_path = Path("/fake/corrupted.json")

        with patch("anivault.cli.helpers.rollback.RollbackManager") as mock_rb_mgr:
            mock_rb_mgr.return_value.generate_rollback_plan.side_effect = OSError(
                "Cannot read file"
            )

            # When & Then
            with pytest.raises(InfrastructureError) as exc_info:
                generate_rollback_plan(log_path)

            assert exc_info.value.code == ErrorCode.FILE_READ_ERROR


# Note: _collect_rollback_data was removed and integrated into _handle_json_output
# JSON output functionality is now tested through integration tests
