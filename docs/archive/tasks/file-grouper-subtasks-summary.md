# File Grouper Subtasks Expansion Summary

**날짜**: 2025-10-13  
**상태**: ✅ **완료**  
**총 서브태스크**: 39개

---

## 📊 서브태스크 분포

| Task | Title | Subtasks | Est. Hours | Complexity |
|------|-------|----------|------------|------------|
| 3 | TitleSimilarityMatcher | 5 | 14h | 9/10 |
| 4 | HashSimilarityMatcher | 4 | 9h | 7/10 |
| 5 | SeasonEpisodeMatcher | 4 | 11h | 8/10 |
| 6 | DuplicateResolver | 5 | 12h | 9/10 |
| 7 | GroupingEngine | 6 | 20h | 10/10 |
| 8 | Facade Refactoring | 5 | 12h | 9/10 |
| 9 | Backward Compatibility | 4 | 6h | 7/10 |
| 11 | Unit Tests (90%+) | 6 | 17h | 8/10 |
| **Total** | **8 tasks** | **39** | **101h** | **High** |

---

## 🎯 Critical Path (병렬 불가)

```
Task 1 (Models) → 1d
  ↓
Task 2 (Protocol) → 1d
  ↓
Task 3,4,5 (Matchers) → 3d (병렬)
  ↓
Task 7 (Engine) → 2.5d
  ↓
Task 6 (Resolver) + Task 7 → 2d (병렬)
  ↓
Task 8 (Facade) → 1.5d
  ↓
Task 9 (Compatibility) → 0.75d
  ↓
Task 11 (Tests) → 2d (병렬 with 10, 12)
```

**예상 기간**:
- **순차 실행**: 101 hours ≈ 13 working days
- **병렬 실행**: Critical path ≈ 7-8 working days

---

## 📝 Task 3: TitleSimilarityMatcher (5 subtasks)

### 3.1 - Extract title extraction logic (2h)
- **Goal**: FileGrouper 300-323 라인에서 제목 추출 로직 이동
- **Output**: `_extract_title_from_file()` private method
- **Dependencies**: None

### 3.2 - Implement similarity calculation (3h)
- **Goal**: rapidfuzz.fuzz.ratio() 사용한 유사도 계산
- **Output**: `_calculate_similarity(title1, title2) -> float`
- **Dependencies**: 3.1

### 3.3 - Implement group matching logic (4h)
- **Goal**: BaseMatcher.match() 구현, 임계값 기반 그룹화
- **Output**: `match(files) -> dict[str, list[ScannedFile]]`
- **Dependencies**: 3.2

### 3.4 - Integrate TitleQualityEvaluator (2h)
- **Goal**: 품질 평가기로 최선의 그룹명 선택
- **Output**: `quality_evaluator.select_better_title()` 통합
- **Dependencies**: 3.3

### 3.5 - Write unit tests (3h)
- **Goal**: 포괄적인 테스트 (identical, similar, dissimilar titles)
- **Output**: `test_title_matcher.py` (15+ tests)
- **Dependencies**: 3.4

---

## 📝 Task 4: HashSimilarityMatcher (4 subtasks)

### 4.1 - Extract normalization logic (3h)
- **Goal**: _group_by_normalized_hash()에서 정규화 로직 추출
- **Output**: `_normalize_title()` method (version/quality 제거)
- **Dependencies**: None

### 4.2 - Implement hash-based grouping (2h)
- **Goal**: 정규화된 해시로 그룹화
- **Output**: `match()` 구현
- **Dependencies**: 4.1

### 4.3 - Add ReDoS protection (2h)
- **Goal**: 정규식 타임아웃 보호
- **Output**: Regex pattern validation + timeout wrapper
- **Dependencies**: 4.2

### 4.4 - Write unit tests (2h)
- **Goal**: 버전/품질 차이, 해시 충돌 테스트
- **Output**: `test_hash_matcher.py` (10+ tests)
- **Dependencies**: 4.3

---

## 📝 Task 5: SeasonEpisodeMatcher (4 subtasks)

### 5.1 - Implement metadata extraction (3h)
- **Goal**: AnitopyParser로 시즌/에피소드 추출
- **Output**: `_extract_metadata() -> tuple[str, int, int]`
- **Dependencies**: None

### 5.2 - Implement season-based grouping (3h)
- **Goal**: 시리즈 + 시즌으로 그룹화
- **Output**: `match()` 구현, 그룹키 '{series} S{season:02d}'
- **Dependencies**: 5.1

### 5.3 - Handle edge cases (2h)
- **Goal**: 누락/모호한 메타데이터 폴백
- **Output**: 에러 핸들링 + 로깅
- **Dependencies**: 5.2

### 5.4 - Write unit tests (3h)
- **Goal**: 다양한 형식 테스트 (S01E01, 1x01, Season 1 Episode 1)
- **Output**: `test_season_matcher.py` (12+ tests)
- **Dependencies**: 5.3

---

## 📝 Task 6: DuplicateResolver (5 subtasks)

### 6.1 - Implement version extraction (2h)
- **Goal**: _v1, _v2 패턴 파싱
- **Output**: `_extract_version() -> int | None`
- **Dependencies**: None

### 6.2 - Implement quality extraction (2h)
- **Goal**: 2160p, 1080p 등 품질 태그 파싱 + 점수화
- **Output**: `_extract_quality() -> int` (numeric score)
- **Dependencies**: None

### 6.3 - Implement resolution comparison (3h)
- **Goal**: 다중 기준 비교 (버전 > 품질 > 크기)
- **Output**: `resolve_duplicates() -> ScannedFile`
- **Dependencies**: 6.1, 6.2

### 6.4 - Add configurable rules (2h)
- **Goal**: 사용자 정의 해상도 규칙
- **Output**: ResolutionConfig dataclass
- **Dependencies**: 6.3

### 6.5 - Write unit tests (3h)
- **Goal**: 버전/품질/크기 비교 테스트
- **Output**: `test_duplicate_resolver.py` (15+ tests)
- **Dependencies**: 6.4

---

## 📝 Task 7: GroupingEngine (6 subtasks) ⚠️ **가장 복잡**

### 7.1 - Design orchestration architecture (2h)
- **Goal**: Constructor + data structures 정의
- **Output**: `__init__(matchers, weights)` + validation
- **Dependencies**: None

### 7.2 - Implement matcher execution (3h)
- **Goal**: 모든 matcher 실행 + 결과 수집
- **Output**: `group_files()` 중간 결과 구조
- **Dependencies**: 7.1

### 7.3 - Implement weighted scoring (4h) ⚠️
- **Goal**: 가중치 점수 계산
- **Output**: `_calculate_weighted_score() -> dict[str, WeightedScore]`
- **Dependencies**: 7.2

### 7.4 - Implement evidence generation (3h)
- **Goal**: GroupingEvidence 생성
- **Output**: `_generate_evidence() -> GroupingEvidence`
- **Dependencies**: 7.3

### 7.5 - Implement group merging (4h)
- **Goal**: 중복 그룹 병합
- **Output**: `_merge_overlapping_groups() -> list[Group]`
- **Dependencies**: 7.4

### 7.6 - Write unit tests (4h)
- **Goal**: Mock matcher 테스트
- **Output**: `test_grouping_engine.py` (20+ tests)
- **Dependencies**: 7.5

---

## 📝 Task 8: Facade Refactoring (5 subtasks)

### 8.1 - Design Facade constructor (2h)
- **Goal**: DI 기반 constructor
- **Output**: `__init__(engine, resolver, name_manager, threshold)`
- **Dependencies**: None

### 8.2 - Implement delegation logic (3h)
- **Goal**: group_files() 위임 구현
- **Output**: engine + resolver 호출, ~50 lines
- **Dependencies**: 8.1

### 8.3 - Remove obsolete methods (2h)
- **Goal**: 구 private method 삭제
- **Output**: 534 → ~200 lines
- **Dependencies**: 8.2

### 8.4 - Update error handling (2h)
- **Goal**: ErrorContext 업데이트
- **Output**: 에러 처리 유지 + 컴포넌트 식별
- **Dependencies**: 8.3

### 8.5 - Write integration tests (3h)
- **Goal**: 기존 테스트 통과 검증
- **Output**: 통합 테스트 추가
- **Dependencies**: 8.4

---

## 📝 Task 9: Backward Compatibility (4 subtasks)

### 9.1 - Update __init__.py exports (1h)
- **Goal**: 하위 호환 import
- **Output**: `__init__.py` exports
- **Dependencies**: None

### 9.2 - Implement compatibility function (1h)
- **Goal**: group_similar_files() 함수 유지
- **Output**: 호환성 wrapper function
- **Dependencies**: 9.1

### 9.3 - Test CLI and GUI imports (2h)
- **Goal**: organize.py, scan_controller.py 검증
- **Output**: Import 테스트 통과
- **Dependencies**: 9.2

### 9.4 - Document migration guide (2h)
- **Goal**: 마이그레이션 가이드 작성
- **Output**: docs/MIGRATION.md 업데이트
- **Dependencies**: 9.3

---

## 📝 Task 11: Unit Tests (6 subtasks)

### 11.1 - Create test structure (2h)
- **Goal**: 테스트 디렉토리 + fixtures
- **Output**: conftest.py + test structure
- **Dependencies**: None

### 11.2 - Write tests for models and matchers (4h)
- **Goal**: models + 3 matchers 테스트
- **Output**: 4개 test files
- **Dependencies**: 11.1

### 11.3 - Write tests for Resolver and Engine (4h)
- **Goal**: DuplicateResolver + GroupingEngine
- **Output**: 2개 test files
- **Dependencies**: 11.2

### 11.4 - Write integration tests (3h)
- **Goal**: FileGrouper facade 통합 테스트
- **Output**: test_grouper_facade.py
- **Dependencies**: 11.3

### 11.5 - Verify existing tests (2h)
- **Goal**: test_file_grouper.py 100% 통과
- **Output**: 회귀 0건
- **Dependencies**: 11.4

### 11.6 - Measure coverage (2h)
- **Goal**: 90%+ 커버리지 확인
- **Output**: pytest-cov HTML report
- **Dependencies**: 11.5

---

## 🎯 성공 지표

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| 서브태스크 생성 | 35-40개 | ✅ 39개 생성 |
| 의존성 검증 | 순환 없음 | ✅ validate_dependencies 통과 |
| 예상 시간 | 7-8일 (병렬) | ✅ 7-8일 예상 |
| 상세도 | 구체적 구현 지침 | ✅ 각 서브태스크 details 포함 |
| 테스트 포함 | 각 모듈 테스트 | ✅ 테스트 서브태스크 8개 |

---

## 📈 다음 단계

### Option A: 즉시 개발 시작 (권장)
```bash
task-master next
# → Task 1: Define grouping models and evidence structures
```

**시작하기 좋은 이유**:
- Task 1, 2는 단순함 (의존성 없음)
- 서브태스크 확장 완료로 명확한 가이드 제공
- Critical path 시작점

### Option B: 벤치마크 먼저 (선택)
```bash
# 기존 구현 성능 측정
# Task 10 먼저 실행 (baseline 확보)
```

---

## 💡 구현 팁

### 병렬 작업 가능 구간
1. **Task 3,4,5 (Matchers)**: 독립적, 동시 구현 가능
2. **Task 6 (Resolver) + Task 7 (Engine)**: 일부 병렬 가능 (Task 7.1-7.3)
3. **Task 10 (Benchmark) + Task 11 (Tests) + Task 12 (Docs)**: 모두 병렬 가능

### 주의사항
- **Task 7 (GroupingEngine)**: 가장 복잡 (20시간), 충분한 시간 확보
- **Task 8.5 (Integration Tests)**: 기존 테스트 100% 통과 필수
- **Task 11.6 (Coverage)**: 90% 목표 달성 위해 반복 작업 필요

---

**작성**: AI Assistant (8-persona 협업)  
**승인**: ✅ All checks passed  
**준비 완료**: 개발 시작 가능 🚀

