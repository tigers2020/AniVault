# AniVault 코드 품질 가이드

이 문서는 AniVault 프로젝트의 코드 품질 기준과 개발 표준을 정의합니다. 모든 개발자와 AI가 일관된 품질의 코드를 생성하고 유지할 수 있도록 돕는 것을 목표로 합니다.

## 목차

1. [핵심 원칙](#핵심-원칙)
2. [One Source of Truth (단일 진실의 원천)](#one-source-of-truth-단일-진실의-원천)
3. [매직 값 제거](#매직-값-제거)
4. [함수 단일 책임 원칙](#함수-단일-책임-원칙)
5. [에러 처리 모범 사례](#에러-처리-모범-사례)
6. [코드 리뷰 체크리스트](#코드-리뷰-체크리스트)
7. [자동화 도구 사용법](#자동화-도구-사용법)
8. [팀 협업 가이드라인](#팀-협업-가이드라인)

## 핵심 원칙

AniVault 프로젝트는 다음 4가지 핵심 원칙을 기반으로 코드 품질을 관리합니다:

### 1. One Source of Truth (단일 진실의 원천)
- 모든 상수, 타입, 에러 코드는 **단일 위치**에서만 정의
- 중복 정의 금지
- Import를 통한 재사용 강제

### 2. 매직 값 제거 (Magic Values Elimination)
- 하드코딩된 문자열, 숫자, 상태값 금지
- 모든 값은 상수나 Enum으로 추출
- 의미 있는 이름 사용

### 3. 함수 단일 책임 원칙 (Single Responsibility Principle)
- 각 함수는 하나의 명확한 책임만 가져야 함
- 함수 길이 제한: 80줄 이하
- 계층 분리: UI, 비즈니스 로직, I/O 분리

### 4. 구조적 에러 처리 (Structured Error Handling)
- 일반 `Exception` 사용 금지
- 구체적인 에러 클래스 사용
- 컨텍스트 정보 포함
- 사용자 친화적 메시지 제공

## One Source of Truth (단일 진실의 원천)

### 원칙

모든 상수, 타입, 에러 코드는 `src/anivault/shared/` 디렉토리에서 중앙 집중식으로 관리됩니다.

### 폴더 구조

```
src/anivault/shared/
├── constants/          # 모든 상수 정의
│   ├── __init__.py    # 통합 export
│   ├── api.py         # API 관련 상수
│   ├── cli.py         # CLI 관련 상수
│   ├── file_formats.py # 파일 형식 관련 상수
│   ├── logging.py     # 로깅 관련 상수
│   ├── matching.py    # 매칭 관련 상수
│   └── system.py      # 시스템 관련 상수
├── errors.py          # 에러 클래스 정의
└── error_messages.py  # 에러 메시지 정의
```

### 올바른 사용법

#### ✅ DO: 중앙 집중식 정의

```python
# src/anivault/shared/constants/api.py
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
TMDB_API_BASE_URL = "https://api.themoviedb.org/3"

# src/anivault/shared/constants/cli.py
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_WORKERS = 4
```

#### ✅ DO: Import하여 사용

```python
# 다른 파일에서 사용
from anivault.shared.constants import (
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    DEFAULT_CONFIDENCE_THRESHOLD
)

def process_request(timeout: int = DEFAULT_TIMEOUT):
    """API 요청 처리."""
    for attempt in range(MAX_RETRIES):
        # 구현...
```

#### ❌ DON'T: 중복 정의

```python
# ❌ BAD: 여러 파일에서 동일한 상수 재정의
# file1.py
DEFAULT_TIMEOUT = 30

# file2.py
DEFAULT_TIMEOUT = 30  # ❌ 중복!
```

### 검증 방법

```bash
# 중복 정의 탐지
python scripts/check_duplicates.py

# 매직 값 탐지
python scripts/detect_magic_values.py
```

## 매직 값 제거

### 원칙

하드코딩된 문자열, 숫자, 상태값은 모두 상수로 추출하여 의미를 명확히 합니다.

### 매직 값 식별 기준

1. **문자열 리터럴**: `"pending"`, `"completed"`, `"error"`
2. **숫자 리터럴**: `30`, `0.7`, `1024`
3. **상태값**: `True`, `False` (의미가 불분명한 경우)

### 상수화 과정

#### 1단계: 매직 값 식별

```python
# ❌ BAD: 매직 값 사용
def process_file(filename: str):
    if filename.endswith('.mkv'):  # ❌ 매직 문자열
        return process_video()
    elif filename.endswith('.srt'):  # ❌ 매직 문자열
        return process_subtitle()

    if len(filename) > 255:  # ❌ 매직 넘버
        raise ValueError("Filename too long")
```

#### 2단계: 상수 정의

```python
# src/anivault/shared/constants/file_formats.py
SUPPORTED_VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi']
SUBTITLE_EXTENSIONS = ['.srt', '.ass', '.vtt']
MAX_FILENAME_LENGTH = 255
```

#### 3단계: 상수 사용

```python
# ✅ GOOD: 상수 사용
from anivault.shared.constants import (
    SUPPORTED_VIDEO_EXTENSIONS,
    SUBTITLE_EXTENSIONS,
    MAX_FILENAME_LENGTH
)

def process_file(filename: str):
    if any(filename.endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS):
        return process_video()
    elif any(filename.endswith(ext) for ext in SUBTITLE_EXTENSIONS):
        return process_subtitle()

    if len(filename) > MAX_FILENAME_LENGTH:
        raise ValueError("Filename too long")
```

### Enum 사용 패턴

상태값이나 선택지가 제한적인 경우 Enum을 사용합니다.

```python
# src/anivault/shared/constants/logging.py
from enum import Enum

class LogLevel(str, Enum):
    """로그 레벨 상수."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# 사용 예시
def setup_logger(level: LogLevel = LogLevel.INFO):
    """로거 설정."""
    # 구현...
```

## 함수 단일 책임 원칙

### 원칙

각 함수는 하나의 명확한 책임만 가져야 하며, 80줄을 초과하지 않아야 합니다.

### 함수 분리 기준

1. **기능적 분리**: 서로 다른 기능을 수행하는 코드
2. **계층적 분리**: UI, 비즈니스 로직, I/O 레이어
3. **복잡도 분리**: 복잡한 로직을 단순한 단위로 분리

### 리팩터링 예제

#### Before: 거대한 함수

```python
# ❌ BAD: 모든 것을 하는 거대한 함수
def process_anime_files(directory: str, api_key: str, output_dir: str):
    """애니메이션 파일 처리 - 모든 것을 한 번에."""
    # 1. 디렉토리 스캔
    files = []
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(('.mkv', '.mp4', '.avi')):
                files.append(os.path.join(root, filename))

    # 2. 파일 파싱
    parsed_files = []
    for file_path in files:
        try:
            parsed = anitopy.parse(os.path.basename(file_path))
            parsed_files.append({
                'path': file_path,
                'parsed': parsed,
                'series_name': parsed.get('anime_title', ''),
                'episode': parsed.get('episode_number', ''),
                'quality': parsed.get('video_quality', '')
            })
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

    # 3. TMDB API 호출
    enriched_files = []
    for file_info in parsed_files:
        try:
            response = requests.get(
                f"https://api.themoviedb.org/3/search/tv",
                params={
                    'api_key': api_key,
                    'query': file_info['series_name'],
                    'language': 'ko-KR'
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    file_info['tmdb_data'] = data['results'][0]
            enriched_files.append(file_info)
        except Exception as e:
            print(f"Error calling TMDB API: {e}")
            enriched_files.append(file_info)

    # 4. 파일 정리
    for file_info in enriched_files:
        if 'tmdb_data' in file_info:
            series_name = file_info['tmdb_data']['name']
            season = file_info['tmdb_data'].get('season_number', 1)
            episode = file_info['episode']
            quality = file_info['quality']

            new_name = f"{series_name} S{season:02d}E{episode:02d} {quality}.mkv"
            new_path = os.path.join(output_dir, new_name)

            try:
                shutil.move(file_info['path'], new_path)
                print(f"Moved: {file_info['path']} -> {new_path}")
            except Exception as e:
                print(f"Error moving file: {e}")

    return enriched_files
```

#### After: 책임별 함수 분리

```python
# ✅ GOOD: 책임별 함수 분리
from anivault.shared.constants import SUPPORTED_VIDEO_EXTENSIONS
from anivault.shared.errors import create_file_not_found_error, create_api_error

def scan_video_files(directory: str) -> List[str]:
    """비디오 파일 스캔 - 단일 책임: 파일 스캔."""
    files = []
    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            if any(filename.endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS):
                files.append(os.path.join(root, filename))
    return files

def parse_anime_filename(file_path: str) -> Dict[str, Any]:
    """애니메이션 파일명 파싱 - 단일 책임: 파일명 파싱."""
    try:
        parsed = anitopy.parse(os.path.basename(file_path))
        return {
            'path': file_path,
            'parsed': parsed,
            'series_name': parsed.get('anime_title', ''),
            'episode': parsed.get('episode_number', ''),
            'quality': parsed.get('video_quality', '')
        }
    except Exception as e:
        raise create_parsing_error(f"Failed to parse filename: {file_path}") from e

def enrich_with_tmdb_data(file_info: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """TMDB 데이터로 파일 정보 보강 - 단일 책임: API 호출."""
    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/search/tv",
            params={
                'api_key': api_key,
                'query': file_info['series_name'],
                'language': 'ko-KR'
            },
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()

        data = response.json()
        if data['results']:
            file_info['tmdb_data'] = data['results'][0]

        return file_info
    except Exception as e:
        raise create_api_error(f"TMDB API call failed for {file_info['series_name']}") from e

def organize_file(file_info: Dict[str, Any], output_dir: str) -> None:
    """파일 정리 - 단일 책임: 파일 이동."""
    if 'tmdb_data' not in file_info:
        return

    series_name = file_info['tmdb_data']['name']
    season = file_info['tmdb_data'].get('season_number', 1)
    episode = file_info['episode']
    quality = file_info['quality']

    new_name = f"{series_name} S{season:02d}E{episode:02d} {quality}.mkv"
    new_path = os.path.join(output_dir, new_name)

    try:
        shutil.move(file_info['path'], new_path)
        logger.info(f"Moved: {file_info['path']} -> {new_path}")
    except Exception as e:
        raise create_file_not_found_error(f"Failed to move file: {file_info['path']}") from e

def process_anime_files(directory: str, api_key: str, output_dir: str) -> List[Dict[str, Any]]:
    """애니메이션 파일 처리 - 오케스트레이션."""
    # 1. 파일 스캔
    files = scan_video_files(directory)

    # 2. 파일 파싱
    parsed_files = [parse_anime_filename(file_path) for file_path in files]

    # 3. TMDB 데이터 보강
    enriched_files = [enrich_with_tmdb_data(file_info, api_key) for file_info in parsed_files]

    # 4. 파일 정리
    for file_info in enriched_files:
        organize_file(file_info, output_dir)

    return enriched_files
```

### 함수 길이 제한

- **80줄 이하**: 일반적인 함수
- **50줄 이하**: 복잡한 비즈니스 로직 함수
- **20줄 이하**: 유틸리티 함수

### 계층 분리

```python
# UI Layer (CLI)
def cli_scan_command(directory: str) -> None:
    """CLI 스캔 명령어 - UI 레이어."""
    try:
        results = scan_service.scan_directory(directory)
        display_results(results)
    except AniVaultError as e:
        display_error(e)

# Service Layer (비즈니스 로직)
class ScanService:
    def scan_directory(self, directory: str) -> List[ScanResult]:
        """디렉토리 스캔 - 서비스 레이어."""
        # 비즈니스 로직 구현
        pass

# Infrastructure Layer (I/O)
class FileSystemScanner:
    def scan_files(self, directory: str) -> List[str]:
        """파일 시스템 스캔 - 인프라 레이어."""
        # 파일 시스템 접근 구현
        pass
```

## 에러 처리 모범 사례

### 원칙

AniVault는 구조적 에러 처리 시스템을 사용하여 일관되고 사용자 친화적인 에러 처리를 제공합니다.

### 에러 클래스 계층

```python
# src/anivault/shared/errors.py
AniVaultError (Base)
├── DomainError (비즈니스 로직 에러)
├── InfrastructureError (인프라 에러)
└── ApplicationError (애플리케이션 에러)
```

### 올바른 에러 처리 패턴

#### ✅ DO: 구조적 에러 처리

```python
from anivault.shared.errors import (
    create_file_not_found_error,
    create_validation_error,
    create_api_error,
    ErrorCode,
    ErrorContext
)

def process_file(file_path: str) -> ProcessedFile:
    """파일 처리 함수."""
    try:
        # 파일 존재 확인
        if not os.path.exists(file_path):
            raise create_file_not_found_error(
                file_path=file_path,
                operation="process_file"
            )

        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # 비즈니스 로직 검증
        if not content.strip():
            raise create_validation_error(
                message="File content cannot be empty",
                field="content",
                operation="process_file"
            )

        return ProcessedFile(path=file_path, content=content)

    except AniVaultError:
        # AniVault 에러는 그대로 재전파
        raise
    except Exception as e:
        # 예상치 못한 에러는 InfrastructureError로 래핑
        raise create_file_not_found_error(
            file_path=file_path,
            operation="process_file",
            original_error=e
        ) from e
```

#### ❌ DON'T: 일반 Exception 사용

```python
# ❌ BAD: 일반 Exception 사용
def bad_process_file(file_path: str):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return content
    except Exception as e:  # ❌ 너무 일반적
        print(f"Error: {e}")  # ❌ 로깅 없음
        return None  # ❌ 에러 정보 손실
```

### 에러 컨텍스트 활용

```python
def call_tmdb_api(query: str, api_key: str) -> Dict[str, Any]:
    """TMDB API 호출."""
    context = ErrorContext(
        operation="call_tmdb_api",
        additional_data={"query": query, "api_key_length": len(api_key)}
    )

    try:
        response = requests.get(
            f"{TMDB_API_BASE_URL}/search/tv",
            params={"api_key": api_key, "query": query},
            timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout as e:
        raise InfrastructureError(
            ErrorCode.TMDB_API_TIMEOUT,
            f"TMDB API timeout for query: {query}",
            context,
            original_error=e
        ) from e
    except requests.exceptions.RequestException as e:
        raise InfrastructureError(
            ErrorCode.TMDB_API_CONNECTION_ERROR,
            f"TMDB API connection failed for query: {query}",
            context,
            original_error=e
        ) from e
```

### 사용자 친화적 메시지

```python
# src/anivault/shared/error_messages.py
USER_FRIENDLY_MESSAGES = {
    ErrorCode.FILE_NOT_FOUND: "파일을 찾을 수 없습니다. 파일 경로를 확인해주세요.",
    ErrorCode.PERMISSION_DENIED: "파일 접근 권한이 없습니다. 관리자 권한으로 실행하거나 파일 권한을 확인해주세요.",
    ErrorCode.TMDB_API_TIMEOUT: "TMDB API 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.",
    ErrorCode.VALIDATION_ERROR: "입력 데이터에 문제가 있습니다. 데이터를 확인해주세요."
}

def get_user_friendly_message(error: AniVaultError) -> str:
    """사용자 친화적 에러 메시지 반환."""
    base_message = USER_FRIENDLY_MESSAGES.get(error.code, "예상치 못한 오류가 발생했습니다.")

    # 컨텍스트 정보 추가
    if error.context.file_path:
        base_message += f"\n파일: {error.context.file_path}"
    if error.context.operation:
        base_message += f"\n작업: {error.context.operation}"

    return base_message
```

## 코드 리뷰 체크리스트

### 필수 검증 항목

#### 1. One Source of Truth 준수
- [ ] 중복 정의가 없는가?
- [ ] 모든 상수가 `shared/constants/`에서 import되는가?
- [ ] 매직 값이 없는가?

#### 2. 함수 단일 책임 원칙
- [ ] 함수가 하나의 명확한 책임만 가지는가?
- [ ] 함수 길이가 80줄 이하인가?
- [ ] 계층이 적절히 분리되어 있는가?

#### 3. 에러 처리
- [ ] 일반 `Exception` 사용하지 않는가?
- [ ] 구체적인 에러 클래스를 사용하는가?
- [ ] 컨텍스트 정보가 포함되어 있는가?
- [ ] 사용자 친화적 메시지가 제공되는가?

#### 4. 코드 품질
- [ ] 타입 힌트가 모든 함수에 있는가?
- [ ] 독스트링이 Google 스타일로 작성되었는가?
- [ ] 테스트가 포함되어 있는가?
- [ ] 로깅이 적절히 사용되었는가?

### 자동화 검증

```bash
# 코드 품질 검증 실행
python scripts/validate_code_quality.py

# 매직 값 탐지
python scripts/detect_magic_values.py

# 중복 정의 검사
python scripts/check_duplicates.py

# 함수 길이 검사
python scripts/validate_function_length.py

# 에러 처리 검증
python scripts/validate_error_handling.py
```

## 자동화 도구 사용법

### Pre-commit 훅 설정

```bash
# Pre-commit 설치
pip install pre-commit

# 훅 설치
pre-commit install

# 수동 실행
pre-commit run --all-files
```

### CI/CD 파이프라인 연동

```yaml
# .github/workflows/quality-check.yml
name: Code Quality Check

on: [push, pull_request]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run quality checks
        run: |
          python scripts/validate_code_quality.py
          python scripts/detect_magic_values.py
          python scripts/check_duplicates.py
          python scripts/validate_function_length.py
          python scripts/validate_error_handling.py

      - name: Run tests
        run: pytest

      - name: Run linting
        run: |
          ruff check src/ tests/
          mypy src/
```

### 품질 점수 계산

```python
# scripts/calculate_quality_score.py
def calculate_quality_score() -> int:
    """코드 품질 점수 계산 (0-100)."""
    score = 100

    # 매직 값 감점
    magic_values = detect_magic_values()
    score -= len(magic_values) * 5

    # 중복 정의 감점
    duplicates = check_duplicates()
    score -= len(duplicates) * 10

    # 긴 함수 감점
    long_functions = validate_function_length()
    score -= len(long_functions) * 3

    # 에러 처리 미흡 감점
    error_issues = validate_error_handling()
    score -= len(error_issues) * 5

    return max(0, score)
```

## 팀 협업 가이드라인

### 코드 리뷰 프로세스

1. **작성자**: PR 생성 전 자동화 도구 실행
2. **리뷰어**: 체크리스트 기반 리뷰
3. **승인자**: 최종 품질 검증 후 승인

### PR 템플릿

```markdown
## 변경 사항
- [ ] One Source of Truth 준수
- [ ] 매직 값 제거
- [ ] 함수 단일 책임 원칙 적용
- [ ] 구조적 에러 처리 적용

## 품질 검증
- [ ] 자동화 도구 통과
- [ ] 테스트 추가/수정
- [ ] 문서 업데이트

## 체크리스트
- [ ] 코드 리뷰 체크리스트 완료
- [ ] 품질 점수 80점 이상
- [ ] 팀 가이드라인 준수
```

### 품질 기준 통일

- **신입 개발자**: 가이드라인 교육 필수
- **경험 개발자**: 정기적인 가이드라인 업데이트
- **AI 코드 생성**: 가이드라인 기반 프롬프트 사용

### 지속적 개선

1. **월간 품질 리뷰**: 품질 메트릭 분석
2. **분기별 가이드라인 업데이트**: 새로운 패턴 반영
3. **연간 교육**: 팀 전체 품질 인식 제고

---

이 가이드를 통해 AniVault 프로젝트의 모든 코드가 일관된 품질을 유지하고, 팀의 개발 효율성을 높일 수 있습니다. 질문이나 개선 사항이 있으면 언제든지 팀에 공유해주세요.
