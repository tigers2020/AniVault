"""
Unified logging for AniVault.

- Single bootstrap: call configure_logging() once from CLI/GUI/build entry points.
- Console: Rich handler (default) or JSON when use_json_console=True.
- File: JSON (StructuredFormatter) or plain (LogConfig.DEFAULT_FORMAT); use same
  use_json_file value everywhere so file format is consistent.
- Formatters: StructuredFormatter (JSON) and logging.Formatter(LogConfig.*) only.
  Do not add alternate formatters; keep format constants in shared.constants.logging.LogConfig.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

from anivault.shared.constants.logging import LogConfig
from anivault.shared.errors import AniVaultError, ErrorContext, ErrorContextModel


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


def _create_rich_console() -> Console:
    """
    Rich Console을 생성합니다 (커스텀 테마 포함).

    Returns:
        설정된 Rich Console 인스턴스
    """
    custom_theme = Theme(
        {
            "logging.level.debug": "cyan",
            "logging.level.info": "green",
            "logging.level.warning": "yellow",
            "logging.level.error": "red bold",
            "logging.level.critical": "red bold reverse",
            "log.time": "dim cyan",
            "log.message": "white",
            "log.path": "dim blue",
        }
    )
    return Console(theme=custom_theme, stderr=False, force_terminal=True)


def setup_structured_logger(
    name: str = "anivault",
    level: str = "INFO",
    log_file: str | None = None,
    *,
    use_rich_console: bool = True,
) -> logging.Logger:
    """
    Configure a named logger (deprecated). Use configure_logging() from entry points instead.

    This configures a single logger with propagate=False, so it does not integrate
    with the root logger used by the rest of the app. New code should rely on
    configure_logging() and logging.getLogger(__name__).

    Args:
        name: 로거 이름 (기본값: "anivault")
        level: 로그 레벨 (기본값: "INFO")
        log_file: 로그 파일 경로 (선택사항)
        use_rich_console: Rich 기반 콘솔 출력 사용 여부 (기본값: True)

    Returns:
        설정된 로거 인스턴스
    """
    # 로거 생성
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정되어 있으면 제거 (중복 방지)
    if logger.handlers:
        logger.handlers.clear()

    # 로그 레벨 설정
    log_level = getattr(logging, level.upper())
    logger.setLevel(log_level)

    # 콘솔 핸들러 설정
    if use_rich_console:
        # Rich 핸들러 사용 (예쁜 콘솔 출력)
        console = _create_rich_console()
        handler: logging.Handler = RichHandler(
            console=console,
            show_time=True,
            show_level=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
            log_time_format="[%H:%M:%S]",
        )
        handler.setLevel(log_level)
        logger.addHandler(handler)
    else:
        # 기본 JSON 포맷 핸들러 사용
        formatter = StructuredFormatter()
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # 파일 핸들러 설정 (선택사항, 항상 JSON 형식)
    if log_file:
        formatter = StructuredFormatter()
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 부모 로거로의 전파 방지 (중복 로그 방지)
    logger.propagate = False

    return logger


def configure_logging(  # pylint: disable=too-many-arguments,too-many-locals
    level: str | int = "INFO",
    log_file: str | None = None,
    log_dir: str | Path | None = None,
    *,
    use_rich: bool = True,
    use_json_console: bool = False,
    enable_file: bool = True,
    enable_console: bool = True,
    max_bytes: int | None = None,
    backup_count: int | None = None,
    use_json_file: bool = True,
) -> logging.Logger:
    """
    Single bootstrap for application logging. Call once from CLI/GUI entry points.

    Configures the root logger so that all loggers (e.g. getLogger(__name__))
    inherit the same handlers and level. Uses constants from LogConfig.

    Args:
        level: Log level (string name or logging constant).
        log_file: Log file name (e.g. "anivault.log"). Used with log_dir.
        log_dir: Directory for log files. Defaults to LogConfig.DEFAULT_LOG_DIR.
        use_rich: Use Rich console handler when enable_console is True.
        use_json_console: If True, console output is JSON (StructuredFormatter).
        enable_file: Attach a file handler (rotating).
        enable_console: Attach a console handler.
        max_bytes: Max bytes per log file before rotation. Defaults to LogConfig.MAX_BYTES.
        backup_count: Number of backup files. Defaults to LogConfig.BACKUP_COUNT.
        use_json_file: Use JSON format for file output.

    Returns:
        Configured root logger.
    """
    log_level = (
        getattr(logging, str(level).upper(), logging.INFO)
        if isinstance(level, str)
        else level
    )
    max_bytes = max_bytes if max_bytes is not None else LogConfig.MAX_BYTES
    backup_count = backup_count if backup_count is not None else LogConfig.BACKUP_COUNT
    log_dir_path = Path(log_dir) if log_dir is not None else Path(LogConfig.DEFAULT_LOG_DIR)
    log_filename = log_file or LogConfig.DEFAULT_FILE

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()

    if enable_console:
        if use_json_console:
            formatter = StructuredFormatter()
            handler: logging.Handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
        elif use_rich:
            console = _create_rich_console()
            handler = RichHandler(
                console=console,
                show_time=True,
                show_level=True,
                show_path=True,
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=False,
                log_time_format="[%H:%M:%S]",
            )
        else:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logging.Formatter(
                    LogConfig.DEFAULT_FORMAT,
                    datefmt=LogConfig.DEFAULT_DATE_FORMAT,
                )
            )
        handler.setLevel(log_level)
        root.addHandler(handler)

    if enable_file:
        log_dir_path.mkdir(parents=True, exist_ok=True)
        log_path = log_dir_path / log_filename
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding=LogConfig.DEFAULT_ENCODING,
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            StructuredFormatter() if use_json_file else logging.Formatter(LogConfig.DEFAULT_FORMAT, datefmt=LogConfig.DEFAULT_DATE_FORMAT)
        )
        root.addHandler(file_handler)

    # So get_default_logger() and log_* convenience functions use configured root
    global _default_logger  # pylint: disable=global-statement
    _default_logger = root
    return root


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
    # 컨텍스트 정보 준비 with PII masking
    context_dict: dict[str, Any] = {}

    # 에러의 기본 컨텍스트 정보 추가 (safe_dict for PII masking)
    if error.context:
        context_dict.update(error.context.safe_dict())

    # 추가 컨텍스트 정보 병합
    if context:
        if hasattr(context, "safe_dict"):
            context_dict.update(context.safe_dict())
        elif hasattr(context, "model_dump"):
            context_dict.update(context.model_dump(exclude_none=True))
        else:
            context_dict.update(context)

    # additional_context 정보 병합
    if additional_context:
        if isinstance(additional_context, ErrorContextModel):
            context_dict.update(additional_context.safe_dict())
        else:
            context_dict.update(additional_context)

    # 로그 레코드 생성
    logger.error(
        error.message,
        extra={
            "error_code": error.code.name,
            "context": context_dict,
            "operation": (operation or error.context.operation if error.context else None),
        },
        exc_info=error.original_error is not None,
    )


def log_operation_success(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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
    # 컨텍스트를 딕셔너리로 변환 with PII masking
    context_dict: dict[str, Any] = {}
    if context:
        if hasattr(context, "safe_dict"):
            context_dict = context.safe_dict()
        elif hasattr(context, "model_dump"):
            context_dict = context.model_dump(exclude_none=True)
        else:
            context_dict = context

    # additional_context 정보 병합
    if additional_context:
        if isinstance(additional_context, ErrorContextModel):
            context_dict.update(additional_context.safe_dict())
        else:
            context_dict.update(additional_context)

    logger.debug(
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
    logger.debug(
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


def log_api_call(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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


def log_file_operation(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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


# Lazy default logger: no side effect at import. Use configure_logging() from entry points first.
_default_logger: logging.Logger | None = None


def get_default_logger() -> logging.Logger:
    """
    Return the default logger. Prefer configure_logging() from CLI/GUI before using.

    If configure_logging() was not called, returns the root logger so that
    output is still visible when handlers are attached by entry points.
    """
    global _default_logger  # pylint: disable=global-statement
    if _default_logger is None:
        _default_logger = logging.getLogger("anivault")
    return _default_logger


def _default_logger_or_root() -> logging.Logger:
    """Return default logger for convenience functions; use root if not set."""
    if _default_logger is not None:
        return _default_logger
    return logging.getLogger()


# Convenience functions (use default or root logger)
def log_error(error: AniVaultError, operation: str | None = None) -> None:
    """Log error using default or root logger."""
    log_operation_error(_default_logger_or_root(), error, operation)


def log_success(
    operation: str,
    duration_ms: float,
    result_info: dict[str, Any] | None = None,
) -> None:
    """Log success using default or root logger."""
    log_operation_success(_default_logger_or_root(), operation, duration_ms, result_info)


def log_start(operation: str, context: dict[str, Any] | None = None) -> None:
    """Log operation start using default or root logger."""
    log_operation_start(_default_logger_or_root(), operation, context)
