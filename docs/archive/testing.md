# 테스트 전략 및 가이드

## 📋 테스트 개요

AniVault는 품질 보증을 위해 다층 테스트 전략을 사용합니다.

### 테스트 피라미드
```
    🔺 E2E Tests (소수)
   🔺🔺 Integration Tests (중간)
  🔺🔺🔺 Unit Tests (다수)
```

## 🧪 테스트 유형

### 1. 단위 테스트 (Unit Tests)
- **목적**: 개별 함수/클래스의 동작 검증
- **위치**: `tests/` 디렉토리
- **실행**: `pytest tests/`
- **커버리지 목표**: 80% 이상

### 2. 통합 테스트 (Integration Tests)
- **목적**: 모듈 간 상호작용 검증
- **위치**: `tests/integration/`
- **실행**: `pytest tests/integration/`
- **특징**: 실제 파일시스템, TMDB API 모킹

### 3. E2E 테스트 (End-to-End Tests)
- **목적**: 전체 워크플로우 검증
- **위치**: `tests/e2e/`
- **실행**: `pytest tests/e2e/`
- **특징**: Dry-run 모드, 실제 파일 조작

## 🚀 테스트 실행

### 기본 테스트 실행
```bash
# 모든 테스트 실행
pytest tests/

# 특정 테스트 파일 실행
pytest tests/core/test_file_grouper.py

# 특정 테스트 함수 실행
pytest tests/core/test_file_grouper.py::test_group_files_by_similarity
```

### 커버리지 포함 테스트
```bash
# 커버리지 리포트 생성
pytest tests/ --cov=src/anivault --cov-report=html

# 커버리지 리포트 확인
open htmlcov/index.html
```

### 병렬 테스트 실행
```bash
# 병렬 실행 (pytest-xdist 필요)
pytest tests/ -n auto

# 특정 워커 수로 실행
pytest tests/ -n 4
```

## 📊 테스트 커버리지

### 커버리지 목표
- **전체 커버리지**: 80% 이상
- **핵심 모듈**: 90% 이상
- **CLI 모듈**: 85% 이상
- **GUI 모듈**: 70% 이상

### 커버리지 확인
```bash
# 커버리지 리포트 생성
pytest tests/ --cov=src/anivault --cov-report=term-missing

# HTML 리포트 생성
pytest tests/ --cov=src/anivault --cov-report=html

# XML 리포트 생성 (CI용)
pytest tests/ --cov=src/anivault --cov-report=xml
```

## 🔧 테스트 설정

### pytest.ini 설정
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --disable-warnings
    --tb=short
    --maxfail=1
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    tmdb: Tests requiring TMDB API
```

### 테스트 마커 사용
```python
import pytest

@pytest.mark.unit
def test_file_parsing():
    """단위 테스트: 파일 파싱 기능"""
    pass

@pytest.mark.integration
def test_tmdb_integration():
    """통합 테스트: TMDB API 연동"""
    pass

@pytest.mark.e2e
def test_full_workflow():
    """E2E 테스트: 전체 워크플로우"""
    pass

@pytest.mark.slow
def test_large_dataset():
    """느린 테스트: 대용량 데이터셋"""
    pass
```

## 🏗️ 테스트 픽스처

### 공통 픽스처 (conftest.py)
```python
import pytest
import tempfile
import shutil
from pathlib import Path

@pytest.fixture
def temp_dir():
    """임시 디렉토리 생성"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)

@pytest.fixture
def sample_anime_files(temp_dir):
    """샘플 애니메이션 파일 생성"""
    files = [
        "Attack on Titan - S01E01 - To You, in 2000 Years.mkv",
        "Attack on Titan - S01E02 - That Day.mkv",
        "Demon Slayer - S01E01 - Cruelty.mkv"
    ]
    for file in files:
        (temp_dir / file).touch()
    return temp_dir

@pytest.fixture
def mock_tmdb_response():
    """TMDB API 응답 모킹"""
    return {
        "id": 12345,
        "title": "Attack on Titan",
        "original_title": "進撃の巨人",
        "overview": "Humanity fights for survival...",
        "poster_path": "/poster.jpg"
    }
```

## 🎯 테스트 시나리오

### CLI 테스트 시나리오
```python
def test_scan_command_basic():
    """기본 스캔 명령 테스트"""
    result = runner.invoke(app, ["scan", str(temp_dir)])
    assert result.exit_code == 0
    assert "Files found" in result.stdout

def test_scan_command_with_options():
    """옵션과 함께 스캔 명령 테스트"""
    result = runner.invoke(app, [
        "scan", str(temp_dir),
        "--recursive", "--verbose", "--json-output"
    ])
    assert result.exit_code == 0
    assert result.stdout.strip().startswith("{")

def test_organize_dry_run():
    """Dry-run 모드 테스트"""
    result = runner.invoke(app, [
        "organize", str(temp_dir), "--dry-run"
    ])
    assert result.exit_code == 0
    assert "Would organize" in result.stdout
```

### 통합 테스트 시나리오
```python
def test_scan_to_organize_workflow():
    """스캔부터 정리까지 전체 워크플로우 테스트"""
    # 1. 스캔
    scan_result = runner.invoke(app, ["scan", str(temp_dir)])
    assert scan_result.exit_code == 0

    # 2. 매칭
    match_result = runner.invoke(app, ["match", str(temp_dir)])
    assert match_result.exit_code == 0

    # 3. 정리 (Dry-run)
    organize_result = runner.invoke(app, [
        "organize", str(temp_dir), "--dry-run"
    ])
    assert organize_result.exit_code == 0
```

## 🔄 지속적 통합 (CI) 테스트

### GitHub Actions 워크플로우
```yaml
- name: Run tests
  run: |
    pytest tests/ -v --maxfail=1 --tb=short

- name: Generate coverage report
  run: |
    pytest tests/ --cov=src/anivault --cov-report=xml

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### 테스트 매트릭스
- Python 3.10, 3.11, 3.12
- Windows, macOS, Linux
- 다양한 의존성 버전

## 🐛 테스트 디버깅

### 테스트 실패 시 디버깅
```bash
# 상세한 출력으로 테스트 실행
pytest tests/ -v -s

# 특정 테스트만 실행
pytest tests/core/test_file_grouper.py::test_specific_function -v -s

# 첫 번째 실패에서 중단
pytest tests/ --maxfail=1

# 실패한 테스트만 재실행
pytest tests/ --lf
```

### 로그 확인
```bash
# 테스트 중 로그 출력
pytest tests/ --log-cli-level=DEBUG

# 로그 파일 확인
tail -f ~/.anivault/logs/anivault.log
```

## 📝 테스트 작성 가이드

### 테스트 함수 명명 규칙
```python
def test_<function_name>_<scenario>_<expected_result>():
    """테스트 설명"""
    pass

# 예시
def test_parse_filename_valid_input_returns_metadata():
    """유효한 입력에 대해 메타데이터를 반환하는지 테스트"""
    pass

def test_parse_filename_invalid_input_raises_error():
    """유효하지 않은 입력에 대해 에러를 발생시키는지 테스트"""
    pass
```

### 테스트 구조 (AAA 패턴)
```python
def test_file_grouper_groups_similar_files():
    """파일 그룹핑 기능 테스트"""
    # Arrange (준비)
    files = ["file1.mkv", "file2.mkv", "different.mkv"]
    grouper = FileGrouper()

    # Act (실행)
    groups = grouper.group_files(files)

    # Assert (검증)
    assert len(groups) == 2
    assert len(groups[0]) == 2
    assert len(groups[1]) == 1
```

## 🚨 테스트 모범 사례

### DO (권장사항)
- 테스트는 독립적이어야 함
- 테스트는 반복 가능해야 함
- 테스트는 명확하고 읽기 쉬워야 함
- 테스트는 빠르게 실행되어야 함
- 테스트는 실제 사용 사례를 반영해야 함

### DON'T (금지사항)
- 테스트 간 의존성을 만들지 마세요
- 외부 서비스에 의존하지 마세요
- 하드코딩된 값에 의존하지 마세요
- 테스트를 너무 복잡하게 만들지 마세요
- 테스트를 건너뛰지 마세요

## 📊 테스트 메트릭스

### 주요 지표
- **테스트 커버리지**: 80% 이상
- **테스트 실행 시간**: 5분 이내
- **테스트 성공률**: 99% 이상
- **테스트 안정성**: 재실행 시 동일한 결과

### 모니터링
```bash
# 테스트 실행 시간 측정
time pytest tests/

# 테스트 커버리지 트렌드 확인
pytest tests/ --cov=src/anivault --cov-report=term-missing
```

## 🆘 문제 해결

### 일반적인 문제
1. **테스트 실패**: 로그 확인, 환경 설정 검증
2. **느린 테스트**: 병렬 실행, 픽스처 최적화
3. **불안정한 테스트**: 외부 의존성 제거, 모킹 강화
4. **커버리지 부족**: 누락된 시나리오 추가

### 지원 요청
- 테스트 실패 로그
- 환경 정보
- 재현 단계
- 예상 결과 vs 실제 결과
