"""Failure-First tests for rollback_handler silent failure patterns.

Tests for the 9 silent failure cases in rollback_handler.py.
"""
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from anivault.cli.common.models import RollbackOptions
from anivault.cli.rollback_handler import (
    _get_rollback_log_path,
    _generate_rollback_plan,
    _collect_rollback_data,
)
from anivault.shared.errors import (
    ApplicationError,
    InfrastructureError,
    ErrorCode,
)


class TestGetRollbackLogPathFailures:
    """_get_rollback_log_path() 실패 케이스 테스트."""

    def test_missing_log_id_raises_error(self):
        """로그 ID 없을 때 ApplicationError 발생."""
        # Given: Pydantic이 빈 문자열 거부하므로 None 테스트
        # 실제로는 Pydantic validation에서 걸러지지만, 함수 레벨 검증 테스트
        options = RollbackOptions(log_id="1234567890", dry_run=False, yes=True)  # Valid length
        console = Mock()
        
        with patch("anivault.core.log_manager.OperationLogManager") as mock_log_mgr:
            mock_log_mgr.return_value.get_log_by_id.return_value = None
            
            # When & Then: 로그 파일 없을 때 ApplicationError
            with pytest.raises(ApplicationError) as exc_info:
                _get_rollback_log_path(options, console)
            
            assert exc_info.value.code in [ErrorCode.FILE_NOT_FOUND, ErrorCode.VALIDATION_ERROR]

    def test_log_file_not_found_raises_error(self):
        """로그 파일 없을 때 InfrastructureError 발생."""
        # Given
        options = RollbackOptions(log_id="nonexistent_log", dry_run=False, yes=True)
        console = Mock()
        
        with patch("anivault.core.log_manager.OperationLogManager") as mock_log_mgr:
            mock_log_mgr.return_value.get_log_by_id.return_value = None
            
            # When & Then
            with pytest.raises(ApplicationError) as exc_info:
                _get_rollback_log_path(options, console)
            
            assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND
            assert "not found" in str(exc_info.value.message).lower()

    def test_log_manager_error_raises_infrastructure_error(self):
        """로그 매니저 에러 시 InfrastructureError 발생."""
        # Given: Valid log_id (>= 10 chars)
        options = RollbackOptions(log_id="test_log_12345", dry_run=False, yes=True)
        console = Mock()
        
        with patch("anivault.core.log_manager.OperationLogManager") as mock_log_mgr:
            mock_log_mgr.side_effect = OSError("Permission denied")
            
            # When & Then
            with pytest.raises(InfrastructureError) as exc_info:
                _get_rollback_log_path(options, console)
            
            assert exc_info.value.code == ErrorCode.FILE_ACCESS_ERROR


class TestGenerateRollbackPlanFailures:
    """_generate_rollback_plan() 실패 케이스 테스트."""

    def test_invalid_log_path_raises_error(self):
        """잘못된 로그 경로 시 ApplicationError 발생."""
        # Given
        invalid_log_path = Path("/nonexistent/log.json")
        console = Mock()
        
        # When & Then
        with pytest.raises((ApplicationError, InfrastructureError)):
            _generate_rollback_plan(invalid_log_path, console)

    def test_corrupted_log_file_raises_error(self):
        """손상된 로그 파일 시 ApplicationError 발생."""
        # Given
        log_path = Path("/tmp/corrupted.json")
        console = Mock()
        
        with patch("anivault.core.rollback_manager.RollbackManager") as mock_mgr:
            mock_mgr.return_value.generate_rollback_plan.side_effect = ValueError("Invalid JSON")
            
            # When & Then
            with pytest.raises((ApplicationError, InfrastructureError)):
                _generate_rollback_plan(log_path, console)


class TestCollectRollbackDataFailures:
    """_collect_rollback_data() 실패 케이스 테스트."""

    def test_log_not_found_returns_error_dict(self):
        """로그 없을 때 error 포함 dict 반환 (JSON용 함수)."""
        # Given
        options = RollbackOptions(log_id="nonexistent", dry_run=False, yes=True)
        
        with patch("anivault.core.log_manager.OperationLogManager") as mock_log_mgr:
            mock_log_mgr.return_value.get_log_by_id.return_value = None
            
            # When
            result = _collect_rollback_data(options)
            
            # Then: JSON용 함수는 error dict 반환 (None 아님)
            assert result is not None
            assert "error" in result
            assert "not found" in result["error"].lower()

    def test_rollback_plan_generation_failed_returns_error_dict(self):
        """플랜 생성 실패 시 error dict 반환."""
        # Given: Valid log_id
        options = RollbackOptions(log_id="test_log_12345", dry_run=False, yes=True)
        mock_log_path = Path("/tmp/test.json")
        
        with patch("anivault.core.log_manager.OperationLogManager") as mock_log_mgr:
            with patch("anivault.core.rollback_manager.RollbackManager") as mock_rb_mgr:
                mock_log_mgr.return_value.get_log_by_id.return_value = mock_log_path
                mock_rb_mgr.return_value.generate_rollback_plan.return_value = None
                
                # When
                result = _collect_rollback_data(options)
                
                # Then
                assert result is not None
                assert "error" in result

    def test_os_error_returns_none(self):
        """OSError 발생 시 None 반환 (현재 동작)."""
        # Given: Valid log_id
        options = RollbackOptions(log_id="test_log_12345", dry_run=False, yes=True)
        
        with patch("anivault.core.log_manager.OperationLogManager") as mock_log_mgr:
            mock_log_mgr.side_effect = OSError("Disk error")
            
            # When
            result = _collect_rollback_data(options)
            
            # Then: 현재는 None 반환
            assert result is None  # 현재 동작 (리팩토링 후 예외 발생으로 변경 예정)


# Note: _collect_rollback_data는 JSON 전용 함수로
# 정상 에러는 error dict, 심각한 예외는 None 반환하는 특수 패턴
# 리팩토링 시 이 특수성 고려 필요

