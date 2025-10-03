# 기여 가이드라인

AniVault 프로젝트에 기여해주셔서 감사합니다! 이 문서는 프로젝트에 기여하는 방법과 개발 표준을 안내합니다.

## 목차

1. [기여 방법](#기여-방법)
2. [개발 환경 설정](#개발-환경-설정)
3. [코드 스타일 가이드](#코드-스타일-가이드)
4. [품질 검증 절차](#품질-검증-절차)
5. [PR 생성 프로세스](#pr-생성-프로세스)
6. [PR 템플릿](#pr-템플릿)
7. [AI 코드 생성 가이드라인](#ai-코드-생성-가이드라인)
8. [문서화 가이드라인](#문서화-가이드라인)

## 기여 방법

### 1. 이슈 생성

버그 리포트나 기능 요청을 위해 이슈를 생성해주세요:

- **버그 리포트**: 명확한 재현 단계와 예상 동작을 포함해주세요
- **기능 요청**: 사용 사례와 기대 효과를 설명해주세요
- **문서 개선**: 구체적인 개선 사항을 제시해주세요

### 2. 포크 및 브랜치 생성

```bash
# 저장소 포크 후 클론
git clone https://github.com/your-username/AniVault.git
cd AniVault

# 기능 브랜치 생성
git checkout -b feature/your-feature-name
# 또는
git checkout -b fix/your-bug-fix
```

### 3. 개발 환경 설정

#### 필수 요구사항

- Python 3.8 이상
- Git
- Pre-commit 훅

#### 환경 설정

```bash
# 저장소 클론
git clone https://github.com/your-username/AniVault.git
cd AniVault

# 가상환경 생성 및 활성화
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Pre-commit 훅 설정
# Windows
scripts\setup-pre-commit.bat
# Linux/macOS
chmod +x scripts/setup-pre-commit.sh
./scripts/setup-pre-commit.sh
```

#### 개발 도구 설정

```bash
# IDE 설정 (VSCode 권장)
# .vscode/settings.json에 다음 설정 추가:
{
    "python.defaultInterpreterPath": "./venv/Scripts/python.exe",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"]
}
```

## 코드 스타일 가이드

### 핵심 원칙

AniVault는 다음 4가지 핵심 원칙을 엄격히 준수합니다:

#### 1. One Source of Truth (단일 진실의 원천)

```python
# ❌ BAD: 중복 정의
# file1.py
class Product:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

# file2.py
class Product:  # ❌ 중복 정의!
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

# ✅ GOOD: 중앙 집중식 정의
# src/anivault/shared/types.py
@dataclass
class Product:
    id: str
    name: str

# 다른 파일에서 import
from anivault.shared.types import Product
```

#### 2. 매직 값 제거 (Magic Values Elimination)

```python
# ❌ BAD: 매직 값 사용
def process_file(filename: str) -> bool:
    if filename.endswith('.mkv'):  # ❌ 매직 문자열
        return True
    return False

# ✅ GOOD: 상수 사용
from anivault.shared.constants.file_formats import SUPPORTED_VIDEO_EXTENSIONS

def process_file(filename: str) -> bool:
    return any(filename.endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS)
```

#### 3. 함수 단일 책임 원칙 (Single Responsibility Principle)

```python
# ❌ BAD: 거대한 함수
def process_anime_file(file_path: str, api_key: str) -> Dict[str, Any]:
    """모든 것을 하는 거대한 함수"""
    # 파일 검증
    # 파일명 파싱
    # API 호출
    # 결과 처리
    # 에러 처리
    # 로깅
    # ... 100줄 이상

# ✅ GOOD: 책임별 함수 분리
def process_anime_file(file_path: str, api_key: str) -> Dict[str, Any]:
    """애니메이션 파일 처리 - 오케스트레이션"""
    try:
        _validate_file_path(file_path)
        parsed = _parse_anime_filename(file_path)
        tmdb_data = _fetch_tmdb_data(parsed['anime_title'], api_key)
        return _create_result(file_path, parsed, tmdb_data)
    except AniVaultError as e:
        return _handle_error(e)

def _validate_file_path(file_path: str) -> None:
    """파일 경로 검증 - 단일 책임"""
    # 검증 로직

def _parse_anime_filename(file_path: str) -> Dict[str, Any]:
    """파일명 파싱 - 단일 책임"""
    # 파싱 로직

def _fetch_tmdb_data(series_name: str, api_key: str) -> Dict[str, Any]:
    """TMDB 데이터 가져오기 - 단일 책임"""
    # API 호출 로직
```

#### 4. 구조적 에러 처리 (Structured Error Handling)

```python
# ❌ BAD: 일반 Exception 사용
def process_file(file_path: str) -> str:
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:  # ❌ 일반 Exception
        print(f"Error: {e}")
        return ""

# ✅ GOOD: 구조적 에러 처리
from anivault.shared.errors import (
    create_file_not_found_error,
    InfrastructureError,
    ErrorCode,
    ErrorContext,
)

def process_file(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError as e:
        raise create_file_not_found_error(
            file_path=file_path,
            operation="process_file",
            original_error=e
        ) from e
    except Exception as e:
        raise InfrastructureError(
            ErrorCode.FILE_READ_ERROR,
            f"Unexpected error reading file: {file_path}",
            ErrorContext(file_path=file_path, operation="process_file"),
            original_error=e
        ) from e
```

### 코딩 스타일

#### Python 스타일 가이드

- **PEP 8** 준수
- **Black** 포맷터 사용 (line-length=88)
- **isort** import 정렬
- **Google/NumPy 스타일** 독스트링

#### 타입 힌트

```python
# ✅ GOOD: 완전한 타입 힌트
from typing import List, Dict, Optional, Union
from pathlib import Path

def process_files(
    file_paths: List[Path],
    callback: Optional[callable] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """파일들을 처리합니다.

    Args:
        file_paths: 처리할 파일 경로 목록
        callback: 각 파일 처리 후 호출할 콜백 함수

    Returns:
        시리즈별로 그룹화된 파일 정보 딕셔너리

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        ValueError: 파일 형식이 지원되지 않을 때
    """
    pass
```

#### 독스트링 가이드라인

```python
def calculate_confidence_score(
    match_data: Dict[str, Any],
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> float:
    """매칭 신뢰도 점수를 계산합니다.

    Args:
        match_data: 매칭 데이터 딕셔너리
        threshold: 신뢰도 임계값 (기본값: DEFAULT_CONFIDENCE_THRESHOLD)

    Returns:
        계산된 신뢰도 점수 (0.0 ~ 1.0)

    Raises:
        ValueError: match_data가 None이거나 threshold가 유효하지 않을 때

    Example:
        >>> match_data = {"exact_match": True, "year_match": True}
        >>> score = calculate_confidence_score(match_data)
        >>> print(f"Confidence: {score:.2f}")
    """
    pass
```

## 품질 검증 절차

### 1. 자동화 도구 실행

PR 생성 전에 다음 검증을 모두 통과해야 합니다:

```bash
# 1. 코드 포맷팅 검사
black --check src/
isort --check-only src/

# 2. 린팅 검사
flake8 src/
mypy src/

# 3. 보안 검사
bandit -r src/

# 4. 커스텀 품질 검증
python scripts/validate_code_quality.py src/
python scripts/detect_magic_values.py src/
python scripts/check_duplicates.py src/
python scripts/validate_function_length.py src/
python scripts/validate_error_handling.py src/
```

### 2. 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 특정 모듈 테스트
pytest tests/core/test_processor.py

# 커버리지 포함 테스트
pytest --cov=src/anivault --cov-report=html --cov-report=term

# 성능 테스트
pytest tests/performance/
```

### 3. Pre-commit 훅

모든 커밋 전에 자동으로 실행되는 검증:

```bash
# Pre-commit 훅 수동 실행
pre-commit run --all-files

# 특정 훅만 실행
pre-commit run black
pre-commit run flake8
pre-commit run mypy
```

### 4. 품질 점수 기준

- **최소 요구사항**: 80점 이상
- **권장 수준**: 90점 이상
- **우수 수준**: 95점 이상

```bash
# 품질 점수 확인
python scripts/calculate_quality_score.py
```

## PR 생성 프로세스

### 1. 브랜치 준비

```bash
# 최신 main 브랜치와 동기화
git checkout main
git pull origin main

# 기능 브랜치로 이동
git checkout feature/your-feature-name

# main 브랜치와 병합
git merge main
```

### 2. 커밋 메시지 작성

[Conventional Commits](https://www.conventionalcommits.org/) 규칙을 따릅니다:

```bash
# 기능 추가
git commit -m "feat(processor): add confidence score calculation"

# 버그 수정
git commit -m "fix(parser): handle empty filename gracefully"

# 문서 업데이트
git commit -m "docs(readme): add code quality standards section"

# 리팩터링
git commit -m "refactor(organize): separate file validation logic"

# 테스트 추가
git commit -m "test(processor): add unit tests for confidence calculation"
```

### 3. PR 생성

1. GitHub에서 Pull Request 생성
2. PR 템플릿 작성
3. 관련 이슈 연결
4. 리뷰어 지정

### 4. PR 검토 과정

1. **자동 검증**: CI/CD 파이프라인 통과 확인
2. **코드 리뷰**: 동료 개발자 리뷰
3. **품질 검증**: 코드 품질 기준 준수 확인
4. **테스트 검증**: 테스트 커버리지 및 통과율 확인
5. **승인**: 최소 1명의 승인 필요

## PR 템플릿

```markdown
## 변경 사항 요약

이 PR에서 수행한 주요 변경 사항을 간단히 설명해주세요.

## 변경 유형

- [ ] 버그 수정 (기존 기능의 버그 수정)
- [ ] 새로운 기능 (새로운 기능 추가)
- [ ] 리팩터링 (기능 변경 없이 코드 개선)
- [ ] 문서 업데이트 (문서만 변경)
- [ ] 테스트 추가/수정 (테스트 코드만 변경)
- [ ] 기타 (위에 해당하지 않는 변경)

## 관련 이슈

- Closes #이슈번호
- Related to #이슈번호

## 변경 사항 상세

### 추가된 기능
- 기능 1
- 기능 2

### 수정된 기능
- 수정 사항 1
- 수정 사항 2

### 제거된 기능
- 제거 사항 1
- 제거 사항 2

## 테스트

### 테스트 케이스
- [ ] 단위 테스트 추가/수정
- [ ] 통합 테스트 추가/수정
- [ ] 성능 테스트 추가/수정

### 테스트 실행 결과
```bash
# 테스트 실행 명령어와 결과
pytest tests/
```

## 품질 검증

### 자동화 도구 실행 결과
```bash
# 품질 검증 명령어와 결과
python scripts/validate_code_quality.py src/
```

### 코드 품질 기준 준수
- [ ] One Source of Truth 원칙 준수
- [ ] 매직 값 제거 완료
- [ ] 함수 단일 책임 원칙 적용
- [ ] 구조적 에러 처리 적용
- [ ] 타입 힌트 완전 적용
- [ ] 독스트링 작성 완료

## 체크리스트

- [ ] 코드가 프로젝트의 코딩 스타일을 준수합니다
- [ ] 자체 검토를 완료했습니다
- [ ] 코드에 적절한 주석을 추가했습니다
- [ ] 변경 사항에 해당하는 문서를 업데이트했습니다
- [ ] 내 변경 사항은 새로운 경고를 생성하지 않습니다
- [ ] 새로운 테스트를 추가했으며, 기존 테스트를 통과합니다
- [ ] 새로운 기능이나 버그 수정에 대한 테스트를 추가했습니다
- [ ] 새로운 의존성을 추가하지 않았습니다

## 추가 정보

리뷰어가 알아야 할 추가 정보가 있다면 여기에 작성해주세요.
```

## AI 코드 생성 가이드라인

### AI 사용 시 준수사항

AI를 활용한 코드 생성 시에는 다음 가이드라인을 준수해야 합니다:

#### 1. 컨텍스트 제공

AI에게 코드 생성을 요청할 때는 다음 정보를 반드시 포함해야 합니다:

```
AniVault 프로젝트에서 작업 중입니다. 다음 원칙을 준수해주세요:

- One Source of Truth: src/anivault/shared/constants/에서 상수 import
- 매직 값 금지: 모든 하드코딩된 값은 상수로 추출
- 함수 단일 책임: 80줄 이하, 하나의 명확한 책임
- 구조적 에러 처리: AniVaultError, ErrorCode, ErrorContext 사용
- 타입 힌트: 모든 함수에 완전한 타입 힌트 적용
- 독스트링: Google/NumPy 스타일 독스트링 작성
```

#### 2. 품질 검증

AI가 생성한 코드는 반드시 다음 검증을 통과해야 합니다:

```bash
# 품질 검증 실행
python scripts/validate_code_quality.py src/
python scripts/detect_magic_values.py src/
python scripts/check_duplicates.py src/
python scripts/validate_function_length.py src/
python scripts/validate_error_handling.py src/
```

#### 3. 테스트 작성

AI가 생성한 코드에는 반드시 테스트를 작성해야 합니다:

```python
# 단위 테스트 예제
import pytest
from unittest.mock import Mock, patch
from anivault.core.processor import process_anime_file

class TestProcessAnimeFile:
    """process_anime_file 함수 테스트."""

    def test_success(self):
        """성공 케이스 테스트."""
        # Given
        file_path = "test.mkv"
        api_key = "test_key"

        # When
        result = process_anime_file(file_path, api_key)

        # Then
        assert result["success"] is True

    def test_file_not_found(self):
        """파일이 존재하지 않는 경우 테스트."""
        # Given
        file_path = "nonexistent.mkv"
        api_key = "test_key"

        # When & Then
        with pytest.raises(FileNotFoundError):
            process_anime_file(file_path, api_key)
```

### AI 코드 생성 체크리스트

- [ ] One Source of Truth 원칙 준수 확인
- [ ] 매직 값 제거 확인
- [ ] 함수 단일 책임 원칙 적용 확인
- [ ] 구조적 에러 처리 적용 확인
- [ ] 타입 힌트 완전 적용 확인
- [ ] 독스트링 작성 확인
- [ ] 테스트 코드 작성 확인
- [ ] 품질 검증 통과 확인

## 문서화 가이드라인

### 1. 코드 문서화

#### 독스트링 작성

```python
def calculate_confidence_score(
    match_data: Dict[str, Any],
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> float:
    """매칭 신뢰도 점수를 계산합니다.

    이 함수는 파일명 매칭 결과를 바탕으로 신뢰도 점수를 계산합니다.
    정확한 매칭, 연도 매칭, 품질 매칭 등의 요소를 종합적으로 고려합니다.

    Args:
        match_data: 매칭 데이터 딕셔너리
            - exact_match (bool): 정확한 매칭 여부
            - year_match (bool): 연도 매칭 여부
            - quality_match (bool): 품질 매칭 여부
        threshold: 신뢰도 임계값 (기본값: DEFAULT_CONFIDENCE_THRESHOLD)
            이 값보다 높은 점수만 유효한 매칭으로 간주됩니다.

    Returns:
        계산된 신뢰도 점수 (0.0 ~ 1.0)
        1.0에 가까울수록 높은 신뢰도를 의미합니다.

    Raises:
        ValueError: match_data가 None이거나 threshold가 유효하지 않을 때
        TypeError: match_data가 딕셔너리가 아닐 때

    Example:
        >>> match_data = {
        ...     "exact_match": True,
        ...     "year_match": True,
        ...     "quality_match": False
        ... }
        >>> score = calculate_confidence_score(match_data, 0.8)
        >>> print(f"Confidence: {score:.2f}")
        Confidence: 0.85

    Note:
        이 함수는 내부적으로 가중치를 사용하여 각 매칭 요소의
        중요도를 조정합니다. 정확한 매칭이 가장 높은 가중치를 가집니다.
    """
    pass
```

#### 인라인 주석

```python
def process_anime_file(file_path: str, api_key: str) -> Dict[str, Any]:
    """애니메이션 파일을 처리합니다."""
    try:
        # 1. 파일 경로 검증
        _validate_file_path(file_path)

        # 2. 파일명 파싱 (anitopy 사용)
        parsed = _parse_anime_filename(file_path)

        # 3. TMDB API 호출 (한국어 설정)
        tmdb_data = _fetch_tmdb_data(parsed['anime_title'], api_key)

        # 4. 결과 생성 및 반환
        return _create_result(file_path, parsed, tmdb_data)

    except AniVaultError as e:
        # 구조적 에러 처리: AniVaultError를 그대로 재전파
        return _handle_error(e)
```

### 2. README 문서화

#### 프로젝트 개요

```markdown
# AniVault

AniVault는 TMDB API를 활용한 애니메이션 파일 자동 정리 시스템입니다.

## 주요 기능

- 🎬 **자동 파일 인식**: 애니메이션 파일 자동 인식 및 파싱
- 🔍 **메타데이터 수집**: TMDB API를 통한 상세 정보 수집
- 📁 **자동 정리**: 지능적인 파일 정리 및 이름 변경
- 🖥️ **Windows 지원**: 단일 실행파일(.exe) 제공
```

#### 설치 및 사용법

```markdown
## 설치

```bash
# 개발 환경
pip install -e .

# 프로덕션 환경
pip install anivault
```

## 사용법

```bash
# 도움말 보기
anivault --help

# 파일 스캔
anivault scan /path/to/anime/files

# 파일 정리
anivault organize /path/to/anime/files
```
```

### 3. API 문서화

#### 함수 시그니처

```python
def process_anime_file(
    file_path: str,
    api_key: str,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    timeout: int = DEFAULT_REQUEST_TIMEOUT
) -> Dict[str, Any]:
    """애니메이션 파일을 처리합니다.

    Args:
        file_path: 처리할 애니메이션 파일 경로
        api_key: TMDB API 키
        confidence_threshold: 신뢰도 임계값 (기본값: 0.8)
        timeout: API 요청 타임아웃 (기본값: 30초)

    Returns:
        처리 결과 딕셔너리:
        - success (bool): 처리 성공 여부
        - file_path (str): 원본 파일 경로
        - parsed (dict): 파싱된 파일 정보
        - tmdb_data (dict): TMDB API 응답 데이터
        - series_name (str): 시리즈 이름

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        ValidationError: 파일 형식이 지원되지 않을 때
        APIError: TMDB API 호출 실패 시
    """
    pass
```

### 4. 변경 로그 작성

#### CHANGELOG.md

```markdown
# 변경 로그

이 파일은 AniVault 프로젝트의 모든 중요한 변경 사항을 기록합니다.

## [Unreleased]

### Added
- 새로운 기능 1
- 새로운 기능 2

### Changed
- 변경된 기능 1
- 변경된 기능 2

### Fixed
- 수정된 버그 1
- 수정된 버그 2

### Removed
- 제거된 기능 1
- 제거된 기능 2

## [1.0.0] - 2024-01-01

### Added
- 초기 릴리스
- 기본 파일 스캔 기능
- TMDB API 연동
- 자동 파일 정리 기능
```

---

이 가이드라인을 따라 기여해주시면 AniVault 프로젝트의 품질을 유지하고 모든 팀원이 일관된 개발 경험을 할 수 있습니다. 추가 질문이 있으시면 이슈를 생성하거나 팀에 문의해주세요.
