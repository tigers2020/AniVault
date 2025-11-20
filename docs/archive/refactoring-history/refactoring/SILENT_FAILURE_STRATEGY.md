# Silent Failure 패턴 리팩토링 전략

**작성일**: 2025-10-07
**대상**: 52개 silent failure 패턴
**우선순위**: P1 (HIGH)

---

## 문제 정의

### 현재 패턴 (안티패턴)
```python
def _get_rollback_log_path(options, console):
    """Get rollback log path."""
    try:
        # ... business logic ...
        return log_path
    except ApplicationError as e:
        console.print(f"[red]Error: {e.message}[/red]")  # UI 출력
        logger.exception("Failed to get log path")        # 로깅
        return None  # ❌ Silent failure!
```

**문제점**:
1. **이중 책임**: 헬퍼 함수가 UI 출력 + 로깅 담당
2. **타입 불안정**: `Optional[Path]` 반환으로 None 체크 필요
3. **에러 정보 손실**: 상위 호출자가 왜 실패했는지 모름
4. **테스트 어려움**: UI/로깅 의존성으로 테스트 복잡

---

## 리팩토링 전략

### 전략 1: 예외 재전파 (Recommended)

**원칙**: 헬퍼 함수는 비즈니스 로직만, 최상위 핸들러가 UI/로깅 담당

```python
# ✅ AFTER: 명확한 예외 발생
def _get_rollback_log_path(options: RollbackOptions) -> Path:
    """Get rollback log path.

    Args:
        options: Rollback options

    Returns:
        Path to rollback log

    Raises:
        ApplicationError: If log path cannot be determined
        InfrastructureError: If log file access fails
    """
    from pathlib import Path
    from anivault.core.log_manager import OperationLogManager

    # Validation
    if not options.log_id:
        raise ApplicationError(
            ErrorCode.VALIDATION_ERROR,
            "Log ID is required for rollback",
            context={"operation": "get_rollback_log_path"}
        )

    # Business logic
    log_manager = OperationLogManager(Path.cwd())
    log_path = log_manager.get_log_by_id(options.log_id)

    if not log_path.exists():
        raise InfrastructureError(
            ErrorCode.FILE_NOT_FOUND,
            f"Rollback log not found: {log_path}",
            context={"log_id": options.log_id, "path": str(log_path)}
        )

    return log_path
```

**호출자 (CLI 핸들러) 패턴**:
```python
def _run_rollback_command(options: RollbackOptions) -> int:
    """Run rollback command.

    Returns:
        Exit code (0=success, 1=error)
    """
    try:
        console = _setup_rollback_console()

        # 헬퍼 함수 호출 (예외 발생 가능)
        log_path = _get_rollback_log_path(options)
        rollback_plan = _generate_rollback_plan(log_path)

        # 실행
        return _execute_rollback_plan(rollback_plan, options, console)

    except ApplicationError as e:
        # 사용자 친화적 메시지 출력
        console.print(f"[red]❌ {e.message}[/red]")
        if e.context:
            console.print(f"[dim]Details: {e.context}[/dim]")

        # 구조화된 로깅
        logger.error(
            "Rollback command failed",
            extra={
                "error_code": e.code,
                "context": e.context,
                "message": e.message
            },
            exc_info=True
        )
        return 1

    except InfrastructureError as e:
        console.print(f"[red]❌ System error: {e.message}[/red]")
        logger.error(
            "Infrastructure error during rollback",
            extra={"error_code": e.code, "context": e.context},
            exc_info=True
        )
        return 1

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        logger.info("Rollback cancelled by user")
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        logger.exception("Unexpected error during rollback")
        return 1
```

**장점**:
- 단일 책임 원칙 준수
- 타입 안정성 향상 (None 제거)
- 테스트 용이성 증가
- 에러 정보 보존

---

### 전략 2: Result 타입 사용 (Alternative)

Rust-style Result 타입으로 성공/실패 명시적 표현:

```python
from dataclasses import dataclass
from typing import Generic, TypeVar, Union

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

@dataclass
class Ok(Generic[T]):
    """성공 결과"""
    value: T

@dataclass
class Err(Generic[E]):
    """실패 결과"""
    error: E

Result = Union[Ok[T], Err[E]]

def _get_rollback_log_path(options: RollbackOptions) -> Result[Path, ApplicationError]:
    """Get rollback log path.

    Returns:
        Result containing Path or ApplicationError
    """
    try:
        # ... business logic ...
        return Ok(log_path)
    except ApplicationError as e:
        return Err(e)
```

**단점**:
- Python에서 비표준 패턴
- 팀 학습 곡선 존재
- 패턴 매칭 부재로 사용 불편

→ **전략 1 (예외 재전파) 채택 권장**

---

## 마이그레이션 로드맵

### Phase 1: 테스트 작성 (Proof-First)
```python
# tests/cli/test_rollback_handler.py
import pytest
from anivault.cli.rollback_handler import _get_rollback_log_path
from anivault.shared.errors import ApplicationError, ErrorCode

def test_get_rollback_log_path_success():
    """롤백 로그 경로 조회 성공"""
    # Given
    options = RollbackOptions(log_id="test_log_001")

    # When
    log_path = _get_rollback_log_path(options)

    # Then
    assert log_path.exists()
    assert log_path.name == "test_log_001.json"

def test_get_rollback_log_path_missing_log_id():
    """로그 ID 없을 때 ValidationError 발생"""
    # Given
    options = RollbackOptions(log_id=None)

    # When & Then
    with pytest.raises(ApplicationError) as exc_info:
        _get_rollback_log_path(options)

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert "required" in exc_info.value.message.lower()

def test_get_rollback_log_path_file_not_found():
    """로그 파일 없을 때 FileNotFoundError 발생"""
    # Given
    options = RollbackOptions(log_id="nonexistent_log")

    # When & Then
    with pytest.raises(InfrastructureError) as exc_info:
        _get_rollback_log_path(options)

    assert exc_info.value.code == ErrorCode.FILE_NOT_FOUND
```

### Phase 2: 리팩토링 실행

**파일별 우선순위**:
1. `rollback_handler.py` (9개) - Day 1-2
2. `metadata_enricher.py` (7개) - Day 2-3
3. `organize_handler.py` (5개) - Day 3
4. `scanner.py` (3개) - Day 4
5. `sqlite_cache_db.py` (3개) - Day 4
6. 기타 (25개) - Day 5

**각 파일별 프로세스**:
1. 현재 동작 검증 테스트 작성
2. 헬퍼 함수에서 에러 처리 제거 → 예외 raise
3. 최상위 핸들러에서만 예외 catch
4. 테스트 실행 (green)
5. 커밋

### Phase 3: 검증

```bash
# 전체 테스트 실행
pytest tests/ -v --cov=src/anivault

# 에러 처리 위반 재검증
python scripts/validate_error_handling.py src/anivault

# 목표: HIGH 심각도 0개
```

---

## 실행 체크리스트

### 각 함수별 리팩토링 체크리스트
- [ ] 현재 동작을 검증하는 테스트 작성
- [ ] 함수 시그니처에서 `Optional` 제거
- [ ] 에러 케이스마다 적절한 예외 raise
- [ ] 비즈니스 로직만 남기고 UI/로깅 제거
- [ ] 독스트링에 Raises 섹션 추가
- [ ] 테스트 실행 (green)
- [ ] Pre-commit 훅 통과
- [ ] 커밋

### 전체 진행 체크리스트
- [ ] Phase 1 테스트 작성 완료 (52개 함수)
- [ ] Phase 2 리팩토링 완료 (52개 함수)
- [ ] Phase 3 검증 완료 (HIGH 0개)
- [ ] 문서 업데이트
- [ ] 팀 리뷰

---

## 예상 효과

### Before (현재)
```python
# 타입 불안정
result: Optional[Dict] = helper_function()
if result is None:
    return 1  # 왜 실패했는지 모름
```

### After (목표)
```python
# 타입 안정
try:
    result: Dict = helper_function()  # 성공하거나 예외 발생
    # ... 비즈니스 로직 ...
except SpecificError as e:
    # 명확한 에러 처리
    logger.error("Operation failed", extra={"error": e})
    return 1
```

**개선 지표**:
- 타입 안정성: 52개 Optional 제거
- 에러 추적성: 100% (모든 실패에 stack trace)
- 테스트 커버리지: +20%p 예상
- 디버깅 시간: -50%

---

**승인자**: 윤도현 (CLI), 최로건 (QA)
**검토자**: 니아 오코예 (보안), 정하림 (컴플라이언스)
