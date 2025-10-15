# PySide6 GUI 타입 안전성 가이드

> **작성일**: 2025-01-14
> **프로젝트**: AniVault
> **대상**: PySide6 GUI 개발자

## 📋 목차

1. [빠른 시작](#빠른-시작)
2. [PySide6 Signal 타입 힌트](#pyside6-signal-타입-힌트)
3. [QThread 워커 타입 힌트](#qthread-워커-타입-힌트)
4. [일반적인 타입 오류 해결](#일반적인-타입-오류-해결)
5. [마이그레이션 가이드](#마이그레이션-가이드)

---

## 빠른 시작

### 전제 조건

```bash
# PySide6 6.5.0+ 설치
pip install "PySide6>=6.5.0"

# PySide6 타입 스텁 설치
pip install PySide6-stubs
```

### pyproject.toml 설정

```toml
[tool.mypy]
python_version = "3.9"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# PySide6 플러그인 활성화
plugins = ["PySide6-stubs"]
```

### 기본 패턴

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from PySide6.QtWidgets import QPushButton

class MyWidget(QWidget):
    """타입 안전한 위젯 예시."""

    # Signal 정의 (클래스 레벨)
    value_changed: Signal = Signal(int)  # int 하나
    data_ready: Signal = Signal(str, bool)  # str, bool 두 개

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.button: Optional[QPushButton] = None
```

---

## PySide6 Signal 타입 힌트

### Signal 선언 패턴

PySide6의 Signal은 **`Signal(type)`** 형식을 사용합니다 (제네릭 `Signal[T]`가 아님).

#### ✅ 올바른 패턴

```python
from PySide6.QtCore import QObject, Signal

class DataModel(QObject):
    """Signal 타입 힌트 예시."""

    # 매개변수 없음
    started: Signal = Signal()

    # 단일 매개변수
    progress: Signal = Signal(int)  # int 값
    message: Signal = Signal(str)  # str 값

    # 복수 매개변수
    file_processed: Signal = Signal(int, str)  # (progress%, filename)

    # 복잡한 객체
    data_ready: Signal = Signal(object)  # 실제로는 FileMetadata 등
```

#### ❌ 잘못된 패턴

```python
# ❌ 제네릭 형식 사용 불가
progress: Signal[int] = Signal()  # 타입 오류!

# ❌ 타입 어노테이션 누락
progress = Signal(int)  # mypy에서 Signal로 인식 안 됨

# ❌ Signal() 호출 결과 할당
progress: Signal = Signal(int)()  # 불필요한 호출
```

### 복잡한 객체 전달

커스텀 객체를 Signal로 전달할 때는 `Signal(object)`를 사용하고 주석으로 실제 타입을 명시합니다.

```python
from anivault.shared.metadata_models import FileMetadata

class TMDBMatchingWorker(QObject):
    """TMDB 매칭 워커."""

    # object로 선언하되 주석으로 실제 타입 명시
    file_matched: Signal = Signal(object)  # Emits FileMetadata object
    matching_finished: Signal = Signal(list)  # Emits list[FileMetadata]

    def emit_result(self, result: FileMetadata) -> None:
        """결과 전송."""
        self.file_matched.emit(result)  # 타입 안전
```

**이유**: PySide6의 Signal은 내부적으로 Qt 메타 객체 시스템을 사용하므로, Python 타입 시스템과 완전히 호환되지 않습니다. `Signal(object)`를 사용하면 모든 Python 객체를 전달할 수 있습니다.

### Signal 연결 타입 힌트

```python
from typing import Callable

class MainWindow(QMainWindow):
    """메인 윈도우."""

    def __init__(self) -> None:
        super().__init__()
        self.worker = TMDBMatchingWorker()

        # Signal 연결 (타입 체크됨)
        self.worker.file_matched.connect(self._on_file_matched)
        self.worker.matching_finished.connect(self._on_matching_finished)

    def _on_file_matched(self, metadata: object) -> None:
        """파일 매칭 완료 핸들러.

        Args:
            metadata: FileMetadata 객체 (Signal(object)로 전달됨)
        """
        # 타입 단언 또는 isinstance 체크
        if isinstance(metadata, FileMetadata):
            print(f"Matched: {metadata.title}")

    def _on_matching_finished(self, results: object) -> None:
        """매칭 완료 핸들러.

        Args:
            results: list[FileMetadata] (Signal(list)로 전달됨)
        """
        # 리스트로 타입 단언
        from typing import cast
        result_list = cast(list[FileMetadata], results)
        print(f"Total: {len(result_list)}")
```

### ✅ 체크리스트

- [ ] Signal 선언 시 `Signal = Signal(type)` 형식 사용
- [ ] 복잡한 객체는 `Signal(object)` + 주석으로 실제 타입 명시
- [ ] Signal 핸들러 매개변수 타입이 Signal 선언과 일치
- [ ] 복수 매개변수는 순서대로 타입 지정 (예: `Signal(int, str)`)

---

## QThread 워커 타입 힌트

### 기본 워커 패턴

QThread 워커는 `QObject`를 상속하고, Signal로 메인 스레드와 통신합니다.

```python
from typing import Optional
from PySide6.QtCore import QObject, Signal

class FileScannerWorker(QObject):
    """파일 스캔 워커 (백그라운드 스레드)."""

    # Signals (메인 스레드로 전송)
    scan_started: Signal = Signal()
    file_found: Signal = Signal(object)  # Emits FileItem object
    scan_progress: Signal = Signal(int)  # Emits progress percentage (0-100)
    scan_finished: Signal = Signal(list)  # Emits list[FileItem]
    scan_error: Signal = Signal(str)  # Emits error message
    scan_cancelled: Signal = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """초기화.

        Args:
            parent: 부모 QObject (Optional for Python 3.9+ compat)
        """
        super().__init__(parent)
        self._cancelled = False
        self._current_directory: Optional[Path] = None

    def scan_directory(self, directory: str) -> None:
        """디렉토리 스캔 (백그라운드에서 실행).

        Args:
            directory: 스캔할 디렉토리 경로
        """
        self.scan_started.emit()

        try:
            # 스캔 로직...
            items: list[FileItem] = []
            # ...
            self.scan_finished.emit(items)
        except Exception as e:
            self.scan_error.emit(str(e))

    def cancel(self) -> None:
        """스캔 취소."""
        self._cancelled = True
```

### 컨트롤러-워커 연결 패턴

```python
from PySide6.QtCore import QObject, QThread

class ScanController(QObject):
    """스캔 컨트롤러 (메인 스레드)."""

    # 컨트롤러 자체 Signal
    scan_started: Signal = Signal()
    scan_progress: Signal = Signal(int)
    scan_finished: Signal = Signal(list)  # list[FileItem]
    scan_error: Signal = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # 워커와 스레드 생성
        self._worker: Optional[FileScannerWorker] = None
        self._thread: Optional[QThread] = None

    def start_scan(self, directory: str) -> None:
        """스캔 시작."""
        # 기존 작업 정리
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

        # 새 워커와 스레드 생성
        self._worker = FileScannerWorker()
        self._thread = QThread()

        # 워커를 스레드로 이동
        self._worker.moveToThread(self._thread)

        # Signal 연결 (워커 → 컨트롤러)
        self._worker.scan_started.connect(self._on_scan_started)
        self._worker.scan_progress.connect(self._on_scan_progress)
        self._worker.scan_finished.connect(self._on_scan_finished)
        self._worker.scan_error.connect(self._on_scan_error)

        # 스레드 시작 시 워커 실행
        self._thread.started.connect(
            lambda: self._worker.scan_directory(directory) if self._worker else None
        )

        # 정리 Signal
        self._worker.scan_finished.connect(self._thread.quit)
        self._worker.scan_error.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)

        # 스레드 시작
        self._thread.start()

    def _on_scan_started(self) -> None:
        """워커 스캔 시작 이벤트."""
        self.scan_started.emit()

    def _on_scan_progress(self, progress: int) -> None:
        """워커 진행률 업데이트."""
        self.scan_progress.emit(progress)

    def _on_scan_finished(self, items: object) -> None:
        """워커 스캔 완료."""
        # list[FileItem]으로 타입 캐스팅
        from typing import cast
        file_items = cast(list[FileItem], items)
        self.scan_finished.emit(file_items)

    def _on_scan_error(self, error_msg: str) -> None:
        """워커 에러 처리."""
        self.scan_error.emit(error_msg)

    def _cleanup_thread(self) -> None:
        """스레드 정리."""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
```

### Python 3.9 호환성

**중요**: Python 3.10+의 `X | Y` 유니온 구문은 Python 3.9에서 지원되지 않습니다.

#### ❌ Python 3.10+ 전용

```python
def __init__(self, parent: QObject | None = None) -> None:
    pass
```

#### ✅ Python 3.9 호환

```python
from typing import Optional

def __init__(self, parent: Optional[QObject] = None) -> None:
    pass
```

### Forward References

순환 import를 방지하려면 `TYPE_CHECKING`과 문자열 타입 힌트를 사용합니다.

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from PySide6.QtCore import QObject
    from anivault.gui.main_window import MainWindow

class MyController(QObject):
    """컨트롤러."""

    def __init__(self, main_window: MainWindow, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._main_window = main_window
```

### ✅ 체크리스트

- [ ] 워커 클래스는 `QObject` 상속
- [ ] `__init__` 매개변수는 `Optional[QObject]` (Python 3.9 호환)
- [ ] Signal 선언은 클래스 레벨
- [ ] 워커는 `moveToThread()`로 별도 스레드로 이동
- [ ] 정리 로직 (quit, wait, deleteLater) 포함
- [ ] TYPE_CHECKING으로 순환 import 방지

---

## 일반적인 타입 오류 해결

### 1. "X | Y syntax requires Python 3.10"

**오류 메시지**:
```
error: X | Y syntax for unions requires Python 3.10  [syntax]
```

**원인**: Python 3.9에서 `|` 유니온 구문 사용

**해결**:
```python
# ❌ Before
def process(data: str | None) -> int | float:
    pass

# ✅ After
from typing import Optional, Union

def process(data: Optional[str]) -> Union[int, float]:
    pass
```

### 2. "Missing type annotation"

**오류 메시지**:
```
error: Missing type annotation  [var-annotated]
```

**원인**: 클래스 변수나 인스턴스 변수에 타입 힌트 누락

**해결**:
```python
# ❌ Before
class MyWidget(QWidget):
    def __init__(self):
        self.count = 0  # 타입 추론 안 됨

# ✅ After
class MyWidget(QWidget):
    def __init__(self) -> None:
        self.count: int = 0
```

### 3. "Skipping analyzing module (missing stubs)"

**오류 메시지**:
```
error: Skipping analyzing "PySide6.QtCore": module is installed, but missing library stubs or py.typed marker  [import-untyped]
```

**해결**:
```bash
# PySide6-stubs 설치
pip install PySide6-stubs
```

또는 특정 import에 대해서만:
```python
from PySide6.QtCore import QObject  # type: ignore[import-untyped]
```

### 4. "Argument has incompatible type"

**오류 메시지**:
```
error: Argument 1 has incompatible type "dict[str, list[ScannedFile]]"; expected "dict[str, list[FileItem]]"  [arg-type]
```

**원인**: 호환되지만 다른 타입 전달

**해결**:
```python
from typing import cast

# 타입 캐스팅으로 명시적 변환
grouped_dict = {
    group.title: cast(list[FileItem], group.files)
    for group in grouped_files
}
```

또는 Forward reference:
```python
grouped_dict = {
    group.title: cast("list[FileItem]", group.files)
    for group in grouped_files
}
```

### 5. "object has no attribute"

**오류 메시지**:
```
error: "object" has no attribute "title"  [attr-defined]
```

**원인**: Signal에서 `object` 타입으로 전달된 객체의 속성 접근

**해결**:
```python
# Option 1: 타입 힌트 명시
from typing import Optional
from anivault.core.matching.models import MatchResult

match_result: Optional[MatchResult] = group_match_result.get("match_result")  # type: ignore[assignment]

if match_result:
    title = match_result.title  # OK!

# Option 2: isinstance 체크
if isinstance(match_result, MatchResult):
    title = match_result.title  # OK!
```

### 6. "Unused type: ignore comment"

**오류 메시지**:
```
error: Unused "type: ignore" comment  [unused-ignore]
```

**원인**: 더 이상 필요 없는 `type: ignore` 주석

**해결**:
```python
# ❌ Before
from anivault.gui.widgets.group_view import (
    GroupView,  # type: ignore[import-untyped]
)

# ✅ After (한 줄로)
from anivault.gui.widgets.group_view import GroupView  # type: ignore[import-untyped]
```

### ✅ 체크리스트

- [ ] Python 3.9 호환: `Optional[]`, `Union[]` 사용
- [ ] 모든 변수에 타입 힌트 추가
- [ ] PySide6-stubs 설치 확인
- [ ] Signal(object) 전달 시 타입 캐스팅
- [ ] 불필요한 type: ignore 제거

---

## 마이그레이션 가이드

### 단계별 마이그레이션

#### Phase 1: 환경 설정 (1일)

1. **의존성 업데이트**
   ```bash
   pip install "PySide6>=6.5.0" PySide6-stubs
   ```

2. **pyproject.toml 설정**
   ```toml
   [tool.mypy]
   python_version = "3.9"
   strict = true

   # 기존 GUI 모듈 제외 제거
   # exclude = ["src/anivault/gui/"]  # ← 삭제
   ```

3. **베이스라인 확인**
   ```bash
   mypy --strict src/anivault/gui/ 2>&1 | tee mypy-baseline.txt
   ```

#### Phase 2: 핵심 모듈 (1주)

우선순위 순서로 진행:

1. **models.py** - 데이터 구조
2. **state_model.py** - 애플리케이션 상태
3. **workers/** - QThread 워커
4. **controllers/** - 비즈니스 로직

각 모듈마다:
```bash
# 1. 타입 힌트 추가
# 2. mypy 검사
mypy --strict src/anivault/gui/models.py

# 3. 테스트 실행
pytest tests/gui/test_models.py

# 4. 다음 모듈로
```

#### Phase 3: UI 컴포넌트 (1주)

5. **widgets/** - UI 위젯
6. **dialogs/** - 다이얼로그
7. **managers/** - 매니저
8. **handlers/** - 이벤트 핸들러

#### Phase 4: 통합 및 검증 (3일)

9. **전체 검사**
   ```bash
   mypy --strict src/anivault/gui/
   ```

10. **회귀 테스트**
    ```bash
    pytest tests/gui/ -v
    ```

11. **수동 GUI 테스트**
    - 스캔 기능
    - TMDB 매칭
    - 미리보기
    - 정리 기능

### 마이그레이션 체크리스트

#### 모듈별

- [ ] `__future__` import 추가
- [ ] TYPE_CHECKING import 분리
- [ ] 모든 함수에 반환 타입 추가
- [ ] 모든 매개변수에 타입 추가
- [ ] 클래스 변수 타입 선언
- [ ] Signal 타입 정의
- [ ] Optional[QObject] 부모 매개변수

#### 프로젝트 전체

- [ ] mypy --strict 0 오류
- [ ] pytest 모든 테스트 통과
- [ ] 수동 GUI 테스트 통과
- [ ] Python 3.9 호환성 확인
- [ ] 문서 업데이트

### 일반적인 패턴 변환

#### Signal 선언

```python
# Before
class MyWorker(QObject):
    progress = Signal(int)

# After
class MyWorker(QObject):
    progress: Signal = Signal(int)
```

#### 생성자

```python
# Before
def __init__(self, parent=None):
    super().__init__(parent)

# After
from typing import Optional

def __init__(self, parent: Optional[QObject] = None) -> None:
    super().__init__(parent)
```

#### Signal 핸들러

```python
# Before
def on_progress(self, value):
    print(value)

# After
def on_progress(self, value: int) -> None:
    print(value)
```

### 점진적 적용 전략

대규모 프로젝트의 경우:

1. **새 코드부터**: 새로 작성하는 모든 코드에 타입 힌트 적용
2. **핫스팟 우선**: 자주 수정되는 모듈 먼저
3. **하향식**: 상위 레벨(컨트롤러) → 하위 레벨(위젯)
4. **테스트 커버리지**: 타입 힌트 추가 전 테스트 작성
5. **리뷰 강화**: PR에서 타입 힌트 필수 체크

### 성공 기준

- ✅ `mypy --strict src/anivault/gui/`: 0 errors
- ✅ `pytest tests/gui/`: 205+ passed
- ✅ Python 3.9 호환성 유지
- ✅ 기능 회귀 없음
- ✅ 문서화 완료

---

## 참고 자료

- [PySide6 공식 문서](https://doc.qt.io/qtforpython/)
- [mypy 문서](https://mypy.readthedocs.io/)
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [AniVault 프로젝트 구조](../architecture/README.md)

---

**마지막 업데이트**: 2025-01-14
**작성자**: AniVault Development Team
