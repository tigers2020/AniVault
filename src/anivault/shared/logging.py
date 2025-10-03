"""
구조적 로깅 시스템 for AniVault.

이 모듈은 에러 발생 시 컨텍스트 정보를 포함하여 구조화된 로그를 기록하는
헬퍼 함수들을 제공합니다.
"""

from __future__ import annotations

import json
import logging
import logging.config
from datetime import datetime, timezone
from typing import Any

from anivault.shared.errors import AniVaultError, ErrorContext


class StructuredFormatter(logging.Formatter):
    """
    JSON 형태로 구조화된 로그를 출력하는 포맷터.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        로그 레코드를 JSON 형태로 포맷팅합니다.

        Args:
            record: 로깅 레코드

        Returns:
            JSON 형태로 포맷팅된 로그 문자열
        """
        return self.format_log(record)

    def format_log(self, record: logging.LogRecord) -> str:
        """
        로그 레코드를 JSON 형태로 포맷팅합니다.

        Args:
            record: 로깅 레코드

        Returns:
            JSON 형태로 포맷팅된 로그 문자열
        """
        return self.format_record(record)

    def format_record(self, record: logging.LogRecord) -> str:
        """
        로그 레코드를 JSON 형태로 포맷팅합니다.

        Args:
            record: 로깅 레코드

        Returns:
            JSON 형태로 포맷팅된 로그 문자열
        """
        # 기본 로그 정보
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 추가 컨텍스트 정보가 있으면 포함
        if hasattr(record, "error_code"):
            log_entry["error_code"] = record.error_code

        if hasattr(record, "context"):
            log_entry["context"] = record.context

        if hasattr(record, "operation"):
            log_entry["operation"] = record.operation

        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms

        if hasattr(record, "result_info"):
            log_entry["result_info"] = record.result_info

        # 예외 정보가 있으면 포함
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_structured_logger(
    name: str = "anivault",
    level: str = "INFO",
    log_file: str | None = None,
) -> logging.Logger:
    """
    구조화된 로깅을 위한 로거를 설정합니다.

    Args:
        name: 로거 이름 (기본값: "anivault")
        level: 로그 레벨 (기본값: "INFO")
        log_file: 로그 파일 경로 (선택사항)

    Returns:
        설정된 로거 인스턴스
    """
    # 로거 생성
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정되어 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()

    # 로그 레벨 설정
    logger.setLevel(getattr(logging, level.upper()))

    # 포맷터 생성
    formatter = StructuredFormatter()

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 설정 (선택사항)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 부모 로거로의 전파 방지 (중복 로그 방지)
    logger.propagate = False

    return logger


def log_operation_error(
    logger: logging.Logger,
    error: AniVaultError,
    operation: str | None = None,
    context: (dict[str, Any] | ErrorContext) | None = None,
    additional_context: (dict[str, Any] | ErrorContext) | None = None,
) -> None:
    """
    AniVaultError 객체를 받아 구조화된 에러 로그를 기록합니다.

    Args:
        logger: 로거 인스턴스
        error: AniVaultError 객체
        operation: 작업 이름 (선택사항)
        context: 추가 컨텍스트 정보 (선택사항)
    """
    # 컨텍스트 정보 준비
    context_dict: dict[str, Any] = {}

    # 에러의 기본 컨텍스트 정보 추가
    if error.context:
        context_dict.update(error.context.to_dict())

    # 추가 컨텍스트 정보 병합
    if context:
        if hasattr(context, "to_dict"):
            context_dict.update(context.to_dict())
        else:
            context_dict.update(context)

    # additional_context 정보 병합
    if additional_context:
        if isinstance(additional_context, ErrorContext):
            context_dict.update(additional_context.to_dict())
        else:
            context_dict.update(additional_context)

    # 로그 레코드 생성
    logger.error(
        error.message,
        extra={
            "error_code": error.code.name,
            "context": context_dict,
            "operation": (
                operation or error.context.operation if error.context else None
            ),
        },
        exc_info=error.original_error is not None,
    )


def log_operation_success(
    logger: logging.Logger,
    operation: str,
    duration_ms: float,
    result_info: dict[str, Any] | None = None,
    context: (dict[str, Any] | ErrorContext) | None = None,
    additional_context: (dict[str, Any] | ErrorContext) | None = None,
) -> None:
    """
    성공적인 작업에 대한 정보 로그를 기록합니다.

    Args:
        logger: 로거 인스턴스
        operation: 작업 이름
        duration_ms: 소요 시간 (밀리초)
        result_info: 결과 정보 (선택사항)
        context: 컨텍스트 정보 (선택사항)
    """
    # 컨텍스트를 딕셔너리로 변환
    context_dict: dict[str, Any] = {}
    if context:
        context_dict = context.to_dict() if hasattr(context, "to_dict") else context

    # additional_context 정보 병합
    if additional_context:
        if isinstance(additional_context, ErrorContext):
            context_dict.update(additional_context.to_dict())
        else:
            context_dict.update(additional_context)

    logger.info(
        "Operation '%s' completed successfully",
        operation,
        extra={
            "operation": operation,
            "duration_ms": duration_ms,
            "result_info": result_info or {},
            "context": context_dict,
        },
    )


def log_operation_start(
    logger: logging.Logger,
    operation: str,
    context: dict[str, Any] | None = None,
) -> None:
    """
    작업 시작 시점 로그를 기록합니다.

    Args:
        logger: 로거 인스턴스
        operation: 작업 이름
        context: 컨텍스트 정보 (선택사항)
    """
    logger.info(
        "Starting operation '%s'",
        operation,
        extra={
            "operation": operation,
            "context": context or {},
        },
    )


def log_validation_error(
    logger: logging.Logger,
    field: str,
    value: Any,
    reason: str,
    context: dict[str, Any] | None = None,
) -> None:
    """
    데이터 검증 실패에 대한 로그를 기록합니다.

    Args:
        logger: 로거 인스턴스
        field: 검증 실패한 필드명
        value: 검증 실패한 값
        reason: 실패 이유
        context: 컨텍스트 정보 (선택사항)
    """
    validation_context = {
        "field": field,
        "value": str(value),
        "reason": reason,
    }

    if context:
        validation_context.update(context)

    logger.warning(
        "Validation failed for field '%s': %s",
        field,
        reason,
        extra={
            "error_code": "VALIDATION_ERROR",
            "context": validation_context,
            "operation": "validation",
        },
    )


def log_api_call(
    logger: logging.Logger,
    endpoint: str,
    method: str = "GET",
    status_code: int | None = None,
    duration_ms: float | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """
    API 호출에 대한 로그를 기록합니다.

    Args:
        logger: 로거 인스턴스
        endpoint: API 엔드포인트
        method: HTTP 메서드 (기본값: "GET")
        status_code: HTTP 상태 코드 (선택사항)
        duration_ms: 소요 시간 (밀리초, 선택사항)
        context: 컨텍스트 정보 (선택사항)
    """
    api_context: dict[str, Any] = {
        "endpoint": endpoint,
        "method": method,
    }

    if status_code:
        api_context["status_code"] = status_code
    if duration_ms:
        api_context["duration_ms"] = duration_ms
    if context:
        api_context.update(context)

    level = logging.INFO
    message = f"API call to {endpoint}"

    if status_code:
        if status_code >= 400:
            level = logging.ERROR
            message += f" failed with status {status_code}"
        else:
            message += f" succeeded with status {status_code}"

    logger.log(
        level,
        message,
        extra={
            "operation": "api_call",
            "context": api_context,
        },
    )


def log_file_operation(
    logger: logging.Logger,
    operation: str,
    source_path: str,
    destination_path: str | None = None,
    success: bool = True,
    error_message: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """
    파일 작업에 대한 로그를 기록합니다.

    Args:
        logger: 로거 인스턴스
        operation: 파일 작업 유형 (move, copy, delete 등)
        source_path: 원본 파일 경로
        destination_path: 대상 파일 경로 (선택사항)
        success: 작업 성공 여부
        error_message: 에러 메시지 (실패 시)
        context: 컨텍스트 정보 (선택사항)
    """
    file_context = {
        "operation": operation,
        "source_path": source_path,
    }

    if destination_path:
        file_context["destination_path"] = destination_path
    if context:
        file_context.update(context)

    if success:
        logger.info(
            "File operation '%s' completed successfully",
            operation,
            extra={
                "operation": "file_operation",
                "context": file_context,
            },
        )
    else:
        logger.error(
            "File operation '%s' failed: %s",
            operation,
            error_message,
            extra={
                "error_code": "FILE_OPERATION_FAILED",
                "operation": "file_operation",
                "context": file_context,
            },
        )


# 전역 로거 인스턴스 (기본 설정)
_default_logger = setup_structured_logger()


def get_default_logger() -> logging.Logger:
    """
    기본 설정된 로거 인스턴스를 반환합니다.

    Returns:
        기본 로거 인스턴스
    """
    return _default_logger


# 편의 함수들 (기본 로거 사용)
def log_error(error: AniVaultError, operation: str | None = None) -> None:
    """기본 로거를 사용하여 에러를 기록합니다."""
    log_operation_error(_default_logger, error, operation)


def log_success(
    operation: str,
    duration_ms: float,
    result_info: dict[str, Any] | None = None,
) -> None:
    """기본 로거를 사용하여 성공 로그를 기록합니다."""
    log_operation_success(_default_logger, operation, duration_ms, result_info)


def log_start(operation: str, context: dict[str, Any] | None = None) -> None:
    """기본 로거를 사용하여 시작 로그를 기록합니다."""
    log_operation_start(_default_logger, operation, context)
