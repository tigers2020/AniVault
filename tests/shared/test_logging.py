"""
구조적 로깅 시스템 테스트.

이 모듈은 src/anivault/shared/logging.py의 구조적 로깅 기능을 테스트합니다.
"""

import json
import logging
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from anivault.shared.errors import (
    AniVaultError,
    ApplicationError,
    DomainError,
    ErrorCode,
    ErrorContext,
    InfrastructureError,
)
from anivault.shared.logging import (
    StructuredFormatter,
    get_default_logger,
    log_api_call,
    log_error,
    log_file_operation,
    log_operation_error,
    log_operation_start,
    log_operation_success,
    log_start,
    log_success,
    log_validation_error,
    setup_structured_logger,
)


class TestStructuredFormatter:
    """StructuredFormatter 테스트."""

    def test_format_basic_log_record(self):
        """기본 로그 레코드 포맷팅 테스트."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert "timestamp" in log_data

    def test_format_log_record_with_extra_fields(self):
        """추가 필드가 포함된 로그 레코드 포맷팅 테스트."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )

        # extra 필드 추가
        record.error_code = "FILE_NOT_FOUND"
        record.operation = "file_processing"
        record.context = {"file_path": "/test/file.txt"}

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["error_code"] == "FILE_NOT_FOUND"
        assert log_data["operation"] == "file_processing"
        assert log_data["context"] == {"file_path": "/test/file.txt"}

    def test_format_log_record_with_exception(self):
        """예외 정보가 포함된 로그 레코드 포맷팅 테스트."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Exception occurred",
                args=(),
                exc_info=sys.exc_info(),  # 실제 예외 정보 전달
            )

            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            assert "exception" in log_data
            assert "ValueError: Test exception" in log_data["exception"]


class TestSetupStructuredLogger:
    """로거 설정 테스트."""

    def test_setup_logger_basic(self):
        """기본 로거 설정 테스트."""
        logger = setup_structured_logger("test_logger", "DEBUG")

        assert logger.name == "test_logger"
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 1  # 콘솔 핸들러만
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_setup_logger_with_file(self, tmp_path):
        """파일 핸들러가 포함된 로거 설정 테스트."""
        log_file = tmp_path / "test.log"
        logger = setup_structured_logger("test_logger", "INFO", str(log_file))

        assert len(logger.handlers) == 2  # 콘솔 + 파일 핸들러
        assert any(isinstance(h, logging.FileHandler) for h in logger.handlers)

    def test_setup_logger_no_duplicate_handlers(self):
        """중복 핸들러 방지 테스트."""
        logger = setup_structured_logger("test_logger")
        initial_handler_count = len(logger.handlers)

        # 다시 설정해도 핸들러가 중복되지 않아야 함
        setup_structured_logger("test_logger")
        assert len(logger.handlers) == initial_handler_count

    def test_get_default_logger(self):
        """기본 로거 반환 테스트."""
        logger = get_default_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "anivault"


class TestLogOperationError:
    """에러 로깅 테스트."""

    def test_log_operation_error_basic(self):
        """기본 에러 로깅 테스트."""
        logger = Mock(spec=logging.Logger)
        error = ApplicationError(
            ErrorCode.CONFIGURATION_ERROR,
            "Configuration failed",
            context=ErrorContext(
                operation="load_config", additional_data={"key": "api_key"}
            ),
        )

        log_operation_error(logger, error)

        # error 메서드가 호출되었는지 확인
        logger.error.assert_called_once()
        call_args = logger.error.call_args

        assert call_args[0][0] == "Configuration failed"  # 메시지
        assert call_args[1]["extra"]["error_code"] == "CONFIGURATION_ERROR"
        assert call_args[1]["extra"]["context"]["key"] == "api_key"
        assert call_args[1]["extra"]["operation"] == "load_config"

    def test_log_operation_error_with_additional_context(self):
        """추가 컨텍스트가 포함된 에러 로깅 테스트."""
        logger = Mock(spec=logging.Logger)
        error = InfrastructureError(
            ErrorCode.FILE_NOT_FOUND,
            "File not found",
            context=ErrorContext(file_path="/test.txt"),
        )
        additional_context = {"user_id": "123", "session_id": "abc"}

        log_operation_error(
            logger,
            error,
            operation="file_processing",
            additional_context=additional_context,
        )

        call_args = logger.error.call_args
        context = call_args[1]["extra"]["context"]

        assert context["file_path"] == "/test.txt"
        assert context["user_id"] == "123"
        assert context["session_id"] == "abc"
        assert call_args[1]["extra"]["operation"] == "file_processing"

    def test_log_operation_error_with_original_exception(self):
        """원본 예외가 포함된 에러 로깅 테스트."""
        logger = Mock(spec=logging.Logger)
        original_exc = FileNotFoundError("Original error")
        error = InfrastructureError(
            ErrorCode.FILE_NOT_FOUND, "File not found", original_error=original_exc
        )

        log_operation_error(logger, error)

        call_args = logger.error.call_args
        assert call_args[1]["exc_info"] is True


class TestLogOperationSuccess:
    """성공 로깅 테스트."""

    def test_log_operation_success_basic(self):
        """기본 성공 로깅 테스트."""
        logger = Mock(spec=logging.Logger)

        log_operation_success(logger, "file_processing", 1500.5)

        logger.info.assert_called_once()
        call_args = logger.info.call_args

        assert "completed successfully" in call_args[0][0]
        assert call_args[1]["extra"]["operation"] == "file_processing"
        assert call_args[1]["extra"]["duration_ms"] == 1500.5

    def test_log_operation_success_with_result_info(self):
        """결과 정보가 포함된 성공 로깅 테스트."""
        logger = Mock(spec=logging.Logger)
        result_info = {"files_processed": 10, "total_size": "1.2GB"}
        context = {"source_dir": "/input", "target_dir": "/output"}

        log_operation_success(logger, "batch_processing", 5000.0, result_info, context)

        call_args = logger.info.call_args
        assert call_args[1]["extra"]["result_info"] == result_info
        assert call_args[1]["extra"]["context"] == context


class TestLogOperationStart:
    """시작 로깅 테스트."""

    def test_log_operation_start_basic(self):
        """기본 시작 로깅 테스트."""
        logger = Mock(spec=logging.Logger)

        log_operation_start(logger, "file_scanning")

        logger.info.assert_called_once()
        call_args = logger.info.call_args

        assert "Starting operation" in call_args[0][0]
        assert call_args[1]["extra"]["operation"] == "file_scanning"

    def test_log_operation_start_with_context(self):
        """컨텍스트가 포함된 시작 로깅 테스트."""
        logger = Mock(spec=logging.Logger)
        context = {"directory": "/test", "recursive": True}

        log_operation_start(logger, "directory_scan", context)

        call_args = logger.info.call_args
        assert call_args[1]["extra"]["context"] == context


class TestLogValidationError:
    """검증 에러 로깅 테스트."""

    def test_log_validation_error_basic(self):
        """기본 검증 에러 로깅 테스트."""
        logger = Mock(spec=logging.Logger)

        log_validation_error(logger, "email", "invalid-email", "Invalid format")

        logger.warning.assert_called_once()
        call_args = logger.warning.call_args

        assert "Validation failed for field 'email'" in call_args[0][0]
        assert call_args[1]["extra"]["error_code"] == "VALIDATION_ERROR"
        assert call_args[1]["extra"]["context"]["field"] == "email"
        assert call_args[1]["extra"]["context"]["value"] == "invalid-email"
        assert call_args[1]["extra"]["context"]["reason"] == "Invalid format"


class TestLogApiCall:
    """API 호출 로깅 테스트."""

    def test_log_api_call_success(self):
        """성공한 API 호출 로깅 테스트."""
        logger = Mock(spec=logging.Logger)

        log_api_call(logger, "/api/movies", "GET", 200, 150.5)

        logger.log.assert_called_once()
        call_args = logger.log.call_args

        assert call_args[0][0] == logging.INFO  # level
        assert "API call to /api/movies" in call_args[0][1]  # message
        assert "succeeded with status 200" in call_args[0][1]
        assert call_args[1]["extra"]["context"]["status_code"] == 200
        assert call_args[1]["extra"]["context"]["duration_ms"] == 150.5

    def test_log_api_call_failure(self):
        """실패한 API 호출 로깅 테스트."""
        logger = Mock(spec=logging.Logger)

        log_api_call(logger, "/api/movies", "POST", 500, 2000.0)

        logger.log.assert_called_once()
        call_args = logger.log.call_args

        assert call_args[0][0] == logging.ERROR  # level
        assert "API call to /api/movies" in call_args[0][1]  # message
        assert "failed with status 500" in call_args[0][1]
        assert call_args[1]["extra"]["context"]["status_code"] == 500


class TestLogFileOperation:
    """파일 작업 로깅 테스트."""

    def test_log_file_operation_success(self):
        """성공한 파일 작업 로깅 테스트."""
        logger = Mock(spec=logging.Logger)

        log_file_operation(logger, "move", "/source/file.txt", "/dest/file.txt", True)

        logger.info.assert_called_once()
        call_args = logger.info.call_args

        assert "File operation 'move' completed successfully" in call_args[0][0]
        assert call_args[1]["extra"]["context"]["operation"] == "move"
        assert call_args[1]["extra"]["context"]["source_path"] == "/source/file.txt"
        assert call_args[1]["extra"]["context"]["destination_path"] == "/dest/file.txt"

    def test_log_file_operation_failure(self):
        """실패한 파일 작업 로깅 테스트."""
        logger = Mock(spec=logging.Logger)

        log_file_operation(
            logger,
            "copy",
            "/source/file.txt",
            "/dest/file.txt",
            False,
            "Permission denied",
        )

        logger.error.assert_called_once()
        call_args = logger.error.call_args

        assert "File operation 'copy' failed: Permission denied" in call_args[0][0]
        assert call_args[1]["extra"]["error_code"] == "FILE_OPERATION_FAILED"


class TestConvenienceFunctions:
    """편의 함수 테스트."""

    def test_log_error_convenience_function(self):
        """편의 함수를 사용한 에러 로깅 테스트."""
        with patch("anivault.shared.logging._default_logger") as mock_logger:
            error = DomainError(ErrorCode.VALIDATION_ERROR, "Validation failed")

            log_error(error, "data_validation")

            mock_logger.error.assert_called_once()

    def test_log_success_convenience_function(self):
        """편의 함수를 사용한 성공 로깅 테스트."""
        with patch("anivault.shared.logging._default_logger") as mock_logger:
            log_success("data_processing", 2000.0, {"records": 100})

            mock_logger.info.assert_called_once()

    def test_log_start_convenience_function(self):
        """편의 함수를 사용한 시작 로깅 테스트."""
        with patch("anivault.shared.logging._default_logger") as mock_logger:
            log_start("file_processing", {"mode": "batch"})

            mock_logger.info.assert_called_once()


class TestLoggingIntegration:
    """로깅 시스템 통합 테스트."""

    def test_full_logging_workflow(self, tmp_path):
        """전체 로깅 워크플로우 테스트."""
        log_file = tmp_path / "integration_test.log"
        logger = setup_structured_logger("integration_test", "INFO", str(log_file))

        # 1. 작업 시작 로그
        log_operation_start(logger, "batch_processing", {"files": 10})

        # 2. 중간 검증 에러 로그
        log_validation_error(
            logger, "filename", "invalid@file.txt", "Contains invalid characters"
        )

        # 3. API 호출 로그
        log_api_call(logger, "/api/metadata", "GET", 200, 150.0)

        # 4. 파일 작업 로그
        log_file_operation(logger, "move", "/temp/file.txt", "/final/file.txt", True)

        # 5. 최종 성공 로그
        log_operation_success(logger, "batch_processing", 5000.0, {"processed": 10})

        # 로그 파일 내용 확인
        with open(log_file, "r", encoding="utf-8") as f:
            log_lines = f.readlines()

        assert len(log_lines) == 5  # 5개의 로그 항목

        # 각 로그가 JSON 형태인지 확인
        for line in log_lines:
            log_data = json.loads(line.strip())
            assert "timestamp" in log_data
            assert "level" in log_data
            assert "message" in log_data
            assert "logger" in log_data

    @pytest.mark.parametrize(
        "error_class,error_code",
        [
            (DomainError, ErrorCode.VALIDATION_ERROR),
            (InfrastructureError, ErrorCode.FILE_NOT_FOUND),
            (ApplicationError, ErrorCode.CONFIGURATION_ERROR),
        ],
    )
    def test_error_logging_with_different_error_types(self, error_class, error_code):
        """다양한 에러 타입에 대한 로깅 테스트."""
        logger = Mock(spec=logging.Logger)
        error = error_class(error_code, f"Test {error_class.__name__} message")

        log_operation_error(logger, error)

        call_args = logger.error.call_args
        assert call_args[1]["extra"]["error_code"] == error_code.name
