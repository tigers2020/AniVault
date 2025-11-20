"""Failure-First tests for organize_handler.py.

Stage 2.3: Test that functions explicitly raise exceptions instead of
silently returning None or False for error conditions.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.cli.common.models import OrganizeOptions
from anivault.cli.helpers.organize import (
    collect_organize_data,
    confirm_organization,
)
from anivault.shared.errors import ApplicationError, ErrorCode, InfrastructureError


# NOTE: _validate_organize_directory is now handled by @setup_handler decorator
# These tests are obsolete but kept for reference
class TestValidateOrganizeDirectoryFailures:
    """_validate_organize_directory() 실패 케이스 테스트 (OBSOLETE - now in setup_decorator)."""

    @pytest.mark.skip(reason="Function moved to setup_handler decorator")
    def test_directory_not_found_raises_error(self) -> None:
        """디렉토리가 존재하지 않을 때 ApplicationError 발생."""
        pass

    @pytest.mark.skip(reason="Function moved to setup_handler decorator")
    def test_permission_denied_raises_error(self) -> None:
        """디렉토리 접근 권한 없을 때 InfrastructureError 발생."""
        pass

    @pytest.mark.skip(reason="Function moved to setup_handler decorator")
    def test_valid_directory_returns_path(self) -> None:
        """유효한 디렉토리일 때 Path 반환."""
        pass


class TestConfirmOrganizationFailures:
    """_confirm_organization() 실패 케이스 테스트."""

    def test_keyboard_interrupt_returns_false(self) -> None:
        """KeyboardInterrupt 발생 시 False 반환 (현재 동작)."""
        # Given
        console = Mock()

        with patch("rich.prompt.Confirm.ask") as mock_ask:
            mock_ask.side_effect = KeyboardInterrupt()

            # When
            result = confirm_organization(console)

            # Then: 현재는 False 반환 (리팩토링 후에도 유지)
            assert result is False

    def test_user_cancels_returns_false(self) -> None:
        """사용자가 취소할 때 False 반환."""
        # Given
        console = Mock()

        with patch("rich.prompt.Confirm.ask") as mock_ask:
            mock_ask.return_value = False

            # When
            result = confirm_organization(console)

            # Then
            assert result is False

    def test_user_confirms_returns_true(self) -> None:
        """사용자가 확인할 때 True 반환."""
        # Given
        console = Mock()

        with patch("rich.prompt.Confirm.ask") as mock_ask:
            mock_ask.return_value = True

            # When
            result = confirm_organization(console)

            # Then
            assert result is True


class TestCollectOrganizeDataFailures:
    """_collect_organize_data() 실패 케이스 테스트."""

    def test_invalid_file_size_logs_warning(self) -> None:
        """잘못된 파일 크기는 경고 로그 후 스킵 (현재: pass)."""
        # Given: Mock operation objects
        operation1 = Mock()
        operation1.source_file.file_path = Path("/test/file1.mkv")
        operation1.target_file.file_path = Path("/test/output/file1.mkv")
        operation1.success = True
        operation1.error_message = None
        # Invalid file size
        operation1.source_file.file_size = "invalid"

        operation2 = Mock()
        operation2.source_file.file_path = Path("/test/file2.mkv")
        operation2.target_file.file_path = Path("/test/output/file2.mkv")
        operation2.success = True
        operation2.error_message = None
        operation2.source_file.file_size = 1000

        operations_data = [operation1, operation2]
        is_dry_run = False
        operation_id = "test_op"

        # When
        result = collect_organize_data(
            operations_data,
            options=Mock(),
            is_dry_run=is_dry_run,
            operation_id=operation_id,
        )

        # Then: 현재는 silently skip (pass)
        assert result is not None
        assert "organize_summary" in result
        # invalid는 스킵되고 1000만 카운트 (현재 동작)


# Note: _validate_organize_directory는 현재 3개 위치에서 return None
# 리팩토링 후에는 명확한 예외 발생으로 변경
# _confirm_organization의 KeyboardInterrupt는 정상적인 사용자 취소이므로 False 반환 유지
# _collect_organize_data의 exception swallowing은 로깅 추가 필요
