# 🧪 Testing - 테스트 및 품질 보증

AniVault 프로젝트의 테스트 전략, 성능 벤치마크, 품질 보증 관련 문서들입니다.

## 📁 문서 목록

### 📊 성능 및 벤치마크

#### [성능 벤치마크 결과](./performance-baseline-results.md)
- **목적**: AniVault의 성능 기준선 및 벤치마크 결과
- **대상**: 성능 엔지니어, 개발자
- **주요 내용**:
  - 파일 스캔 성능
  - 매칭 알고리즘 성능
  - 메모리 사용량
  - CPU 사용률

#### [테스트 최적화 요약](./test-optimization-summary.md)
- **목적**: 테스트 성능 최적화 결과 및 개선 사항
- **대상**: QA 엔지니어, 개발자
- **주요 내용**:
  - 테스트 실행 시간 최적화
  - 테스트 커버리지 개선
  - 자동화 테스트 전략
  - CI/CD 통합

## 🎯 테스트 전략

### 테스트 피라미드

#### 1. 단위 테스트 (Unit Tests)
- **목적**: 개별 함수/클래스의 정확성 검증
- **도구**: pytest
- **커버리지**: 90% 이상
- **담당자**: 최로건 (QA 전문가)

```python
# 예시: 매칭 알고리즘 단위 테스트
def test_matching_algorithm():
    """매칭 알고리즘 정확성 테스트."""
    candidate = MediaItem("Movie A", 2020, ["Action"])
    target = MediaItem("Movie A", 2020, ["Action"])

    score = calculate_matching_score(candidate, target)
    assert score == 1.0  # 완벽한 매칭
```

#### 2. 통합 테스트 (Integration Tests)
- **목적**: 컴포넌트 간 상호작용 검증
- **도구**: pytest + requests
- **커버리지**: 80% 이상
- **담당자**: 최로건 (QA 전문가)

```python
# 예시: TMDB API 통합 테스트
def test_tmdb_api_integration():
    """TMDB API 통합 테스트."""
    enricher = MetadataEnricher()
    result = enricher.enrich_metadata("Movie Title", 2020)

    assert result.title == "Movie Title"
    assert result.year == 2020
    assert result.tmdb_id is not None
```

#### 3. 시스템 테스트 (System Tests)
- **목적**: 전체 시스템의 end-to-end 검증
- **도구**: pytest + subprocess
- **커버리지**: 70% 이상
- **담당자**: 최로건 (QA 전문가)

```python
# 예시: CLI 전체 워크플로우 테스트
def test_full_workflow():
    """전체 워크플로우 시스템 테스트."""
    result = subprocess.run([
        "anivault", "scan", "--path", "test_data/",
        "--match", "--organize"
    ], capture_output=True, text=True)

    assert result.returncode == 0
    assert "Processing completed" in result.stdout
```

### 성능 테스트

#### 1. 부하 테스트 (Load Testing)
- **목적**: 대용량 데이터 처리 성능 검증
- **시나리오**: 1000개 이상 파일 처리
- **지표**: 처리 시간, 메모리 사용량, CPU 사용률
- **담당자**: 사토 미나 (알고리즘 전문가)

#### 2. 스트레스 테스트 (Stress Testing)
- **목적**: 시스템 한계점 파악
- **시나리오**: 메모리 부족, 디스크 공간 부족
- **지표**: 시스템 안정성, 복구 능력
- **담당자**: 김지유 (데이터 품질 전문가)

#### 3. 내구성 테스트 (Endurance Testing)
- **목적**: 장시간 실행 안정성 검증
- **시나리오**: 24시간 연속 실행
- **지표**: 메모리 누수, 성능 저하
- **담당자**: 윤도현 (백엔드 전문가)

## 🛠️ 테스트 도구 및 환경

### 테스트 프레임워크
```python
# pytest 설정
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "--disable-warnings"
]
```

### 테스트 커버리지
```python
# pytest-cov 설정
[tool.coverage.run]
source = ["src/anivault"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
```

### 자동화 테스트
```yaml
# GitHub Actions 워크플로우
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ --cov=src/anivault
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## 📊 품질 지표

### 테스트 커버리지
- **단위 테스트**: 90% 이상
- **통합 테스트**: 80% 이상
- **시스템 테스트**: 70% 이상
- **전체 커버리지**: 85% 이상

### 성능 지표
- **파일 스캔**: 1000개 파일/분 이상
- **매칭 정확도**: 95% 이상
- **메모리 사용량**: 500MB 이하
- **시작 시간**: 3초 이내

### 안정성 지표
- **테스트 통과율**: 100%
- **회귀 테스트**: 0개 실패
- **성능 회귀**: 5% 이내
- **메모리 누수**: 0개

## 🔄 지속적 개선

### 테스트 자동화
- **CI/CD 통합**: 모든 PR에 자동 테스트 실행
- **성능 모니터링**: 성능 회귀 자동 감지
- **보안 스캔**: 보안 취약점 자동 검사
- **품질 게이트**: 품질 기준 미달 시 배포 차단

### 테스트 최적화
- **병렬 실행**: 테스트 병렬화로 실행 시간 단축
- **선택적 실행**: 변경된 코드만 테스트
- **캐싱**: 테스트 데이터 캐싱으로 중복 작업 제거
- **모킹**: 외부 의존성 모킹으로 테스트 안정성 향상

### 품질 보증
- **코드 리뷰**: 모든 코드 변경에 리뷰 필수
- **정적 분석**: 코드 품질 자동 검사
- **동적 분석**: 런타임 보안 검사
- **의존성 검사**: 외부 라이브러리 보안 검사

---

**문서 버전**: 1.0
**최종 업데이트**: 2024-01-XX
**관리자**: AniVault QA팀 (최로건)
