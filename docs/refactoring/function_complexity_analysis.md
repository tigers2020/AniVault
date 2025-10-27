# 고복잡도 함수 리팩토링 분석 보고서

**분석 일시**: 2025-10-15
**총 위반 건수**: 162개
**목표**: 20개 미만
**현재 달성률**: 12.3% (20/162)

---

## 📊 전체 위반 현황

### 위반 유형별 분포

| 유형 | 건수 | 비율 |
|------|------|------|
| **mixed_responsibilities** | 50 | 30.9% |
| **complexity** | 47 | 29.0% |
| **length** | 46 | 28.4% |
| **parameters** | 19 | 11.7% |

### 심각도별 분류

#### 🔴 High (CC > 15 또는 Length > 150)
- `calculate_confidence_score` (CC: 22, Length: 127)
- `group_files_by_tmdb_title` (CC: 20, Length: 126)
- `_get_anime_info` (CC: 20, Length: 110)
- `_load_env_file` (CC: 19, Length: 120)
- `group_files` (CC: 18, Length: 120)
- `_cleanup_empty_directories` (CC: 18, Length: 106)
- `_extract_metadata` (CC: 16, Length: N/A)
- `update_file_match_result` (CC: 16, Length: N/A)
- `display_scan_results` (CC: 16, Length: N/A)
- `_update_group_card_name` (CC: 15, Length: N/A)
- `__post_init__` (CC: 15, Length: N/A)
- `_create_poster_widget` (CC: 14, Length: 86)
- `run_match_pipeline` (CC: 14, Length: 147)
- `display_match_results` (CC: 14, Length: N/A)
- `handle_rollback_command` (CC: 14, Length: N/A)

**총 15개**

#### 🟡 Medium (CC 11-15 또는 Length 80-150)
- CLI 모듈: 23개
- 매칭 엔진: 8개
- SQLite 캐시: 5개
- GUI 모듈: 12개
- 기타: 18개

**총 66개**

#### 🟢 Low (CC 10-11)
- CLI 모듈: 15개
- 매칭 엔진: 3개
- SQLite 캐시: 2개
- GUI 모듈: 8개
- 기타: 10개

**총 38개**

---

## 🎯 모듈별 우선순위

### 1️⃣ CLI 모듈 (우선순위: 최상)

**위반 건수**: 62개 (38.3%)

#### 핵심 파일
- `cli/run_handler.py`: 5개 (CC: 11, Length: 108/115)
- `cli/scan_handler.py`: 4개 (Length: 88/98)
- `cli/rollback_handler.py`: 4개 (CC: 14, Length: 82)
- `cli/match_handler.py`: 2개 (Parameters: 6)
- `cli/organize_handler.py`: 2개 (Parameters: 7)
- `cli/typer_app.py`: 4개 (Length: 82/100, Parameters: 6/7/8)
- `cli/common/error_handler.py`: 3개 (CC: 11, Length: 91/124)
- `cli/common/setup_decorator.py`: 3개 (CC: 13, Length: 106)
- `cli/common/validation.py`: 2개 (CC: 13, Length: 90)
- `cli/helpers/match.py`: 3개 (CC: 14, Length: 126/147)
- `cli/helpers/organize.py`: 3개 (Length: 87)
- `cli/helpers/scan.py`: 2개 (CC: 16, Length: 106)
- `cli/helpers/verify.py`: 2개
- `cli/helpers/log.py`: 1개 (Length: 90)

**리팩토링 전략**:
- Extract Method: 긴 함수를 작은 private 메서드로 분해
- Decompose Conditional: 복잡한 조건문 단순화
- Replace Temp with Query: 임시 변수 제거

**예상 효과**: 62개 → 10개 이하

---

### 2️⃣ 매칭 엔진 모듈 (우선순위: 높음)

**위반 건수**: 28개 (17.3%)

#### 핵심 파일
- `core/matching/scoring.py`: 2개 (CC: 22, Length: 127) ⚠️ **최고 위험**
- `core/matching/engine.py`: 3개 (Length: 112, mixed_responsibilities)
- `core/matching/services/fallback_service.py`: 1개 (Length: 95)
- `core/matching/services/filter_service.py`: 1개
- `core/file_grouper/grouper.py`: 4개 (CC: 11-18, Length: 120)
- `core/file_grouper/grouping_engine.py`: 1개 (Length: 107)
- `core/file_grouper/matchers/season_matcher.py`: 1개 (CC: 16)
- `core/file_grouper/matchers/title_matcher.py`: 2개 (CC: 13, Length: 90)

**리팩토링 전략**:
- Extract Class: 여러 책임을 가진 함수를 클래스로 분리
- Extract Method: 긴 함수를 작은 메서드로 분해
- Strategy Pattern: 복잡한 로직을 전략 패턴으로 분리

**예상 효과**: 28개 → 5개 이하

---

### 3️⃣ SQLite 캐시 모듈 (우선순위: 중간)

**위반 건수**: 12개 (7.4%)

#### 핵심 파일
- `services/sqlite_cache/cache_db.py`: 2개 (Length: 96, mixed_responsibilities)
- `services/sqlite_cache/operations/query.py`: 2개 (CC: 12, Length: 123)
- `services/sqlite_cache_db.py`: 2개 (Length: 86, mixed_responsibilities)
- `services/tmdb_client.py`: 4개 (Parameters: 6, CC: 11, mixed_responsibilities)
- `services/enricher.py`: 2개 (Parameters: 7, mixed_responsibilities)

**리팩토링 전략**:
- Extract Method: 긴 함수를 작은 메서드로 분해
- Repository Pattern: 데이터 접근 로직 분리

**예상 효과**: 12개 → 3개 이하

---

### 4️⃣ GUI 모듈 (우선순위: 중간)

**위반 건수**: 34개 (21.0%)

#### 핵심 파일
- `gui/controllers/organize_controller.py`: 2개 (Length: 156, CC: 11) ⚠️ **높은 위험**
- `gui/controllers/scan_controller.py`: 3개 (CC: 20, Length: 106/126)
- `gui/controllers/tmdb_controller.py`: 1개
- `gui/dialogs/organize_preview_dialog.py`: 3개 (CC: 13, Length: 85/148)
- `gui/dialogs/settings_dialog.py`: 1개
- `gui/handlers/organize_event_handler.py`: 1개 (Parameters: 8)
- `gui/handlers/tmdb_event_handler.py`: 1개 (Parameters: 7)
- `gui/themes/path_resolver.py`: 1개 (Length: 81)
- `gui/themes/qss_loader.py`: 3개 (Length: 99/101)
- `gui/themes/theme_manager.py`: 1개 (CC: 11)
- `gui/widgets/anime_detail_popup.py`: 2개 (CC: 17, Length: 92)
- `gui/widgets/group_card_widget.py`: 5개 (CC: 11-20, Length: 86-120)
- `gui/widgets/group_grid_view.py`: 1개 (CC: 15)
- `gui/workers/organize_worker.py`: 3개 (CC: 11-18, Length: 96-106)
- `gui/workers/tmdb_matching_worker.py`: 1개 (Length: 87)
- `gui/main_window.py`: 1개
- `gui/models.py`: 1개 (CC: 16)

**리팩토링 전략**:
- Extract Method: 긴 함수를 작은 메서드로 분해
- Decompose Conditional: 복잡한 조건문 단순화
- View Model Pattern: UI 로직과 비즈니스 로직 분리

**예상 효과**: 34개 → 8개 이하

---

### 5️⃣ 기타 모듈 (우선순위: 낮음)

**위반 건수**: 26개 (16.0%)

#### 핵심 파일
- `config/auto_scanner.py`: 2개 (Parameters: 7)
- `config/loader.py`: 3개 (CC: 19, Length: 120)
- `core/benchmark.py`: 1개 (Length: 111)
- `core/filter.py`: 1개 (CC: 11)
- `core/normalization.py`: 2개 (CC: 12)
- `core/resolution_detector.py`: 2개 (CC: 13, Length: 84)
- `core/statistics.py`: 1개 (Parameters: 6)
- `core/pipeline/components/collector.py`: 3개 (CC: 11, Length: 81/118)
- `core/pipeline/components/parallel_scanner.py`: 4개 (CC: 11-12, Length: 99)
- `core/pipeline/components/parser.py`: 2개 (Parameters: 6)
- `core/pipeline/components/scanner.py`: 2개 (Parameters: 12, CC: 13)
- `core/pipeline/domain/orchestrator.py`: 2개 (Length: 123/148)
- `core/organizer/executor.py`: 1개 (Length: 85)
- `security/keyring.py`: 2개 (CC: 11-12)
- `services/rate_limiter.py`: 1개 (Length: 95)
- `services/semaphore_manager.py`: 2개 (CC: 12, Length: 82)
- `services/metadata_enricher/fetcher.py`: 2개 (Length: 81/175)
- `services/metadata_enricher/scoring/engine.py`: 1개 (Length: 113)
- `shared/cache_utils.py`: 1개 (Length: 87)
- `shared/errors.py`: 2개 (Parameters: 7)
- `shared/logging.py`: 4개 (Parameters: 6-7)
- `shared/metadata_models.py`: 1개 (CC: 15)
- `utils/logging_config.py`: 2개 (Length: 81, Parameters: 9)

**리팩토링 전략**:
- Extract Method: 긴 함수를 작은 메서드로 분해
- Extract Class: 여러 책임을 가진 함수를 클래스로 분리

**예상 효과**: 26개 → 5개 이하

---

## 📋 리팩토링 우선순위 매트릭스

| 우선순위 | 모듈 | 위반 건수 | 예상 감소 | 난이도 | 영향도 |
|---------|------|----------|----------|--------|--------|
| 🔴 P0 | CLI 모듈 | 62 | 52 | 중 | 높음 |
| 🟠 P1 | 매칭 엔진 | 28 | 23 | 높음 | 높음 |
| 🟡 P2 | GUI 모듈 | 34 | 26 | 중 | 중 |
| 🟢 P3 | SQLite 캐시 | 12 | 9 | 낮음 | 중 |
| ⚪ P4 | 기타 모듈 | 26 | 21 | 중 | 낮음 |

**예상 총 감소**: 162개 → 31개 (목표: 20개 미만)

---

## 🎯 리팩토링 전략

### 1. Extract Method (메서드 추출)
**대상**: 긴 함수 (Length > 80)
**방법**:
```python
# Before
def long_function():
    # 100 lines of code
    pass

# After
def long_function():
    step1()
    step2()
    step3()

def _step1():
    # 30 lines

def _step2():
    # 30 lines

def _step3():
    # 40 lines
```

### 2. Extract Class (클래스 추출)
**대상**: 여러 책임을 가진 함수 (mixed_responsibilities)
**방법**:
```python
# Before
def process_file(file_path):
    # Network logic
    # Business logic
    # UI logic
    pass

# After
class FileProcessor:
    def __init__(self):
        self.network_handler = NetworkHandler()
        self.business_logic = BusinessLogic()
        self.ui_handler = UIHandler()

    def process_file(self, file_path):
        data = self.network_handler.fetch(file_path)
        result = self.business_logic.process(data)
        self.ui_handler.display(result)
```

### 3. Decompose Conditional (조건문 분해)
**대상**: 복잡한 조건문 (CC > 10)
**방법**:
```python
# Before
def complex_function(value):
    if value > 10 and value < 20 and value % 2 == 0:
        # do something
        pass

# After
def complex_function(value):
    if _is_valid_value(value):
        # do something
        pass

def _is_valid_value(value):
    return value > 10 and value < 20 and value % 2 == 0
```

### 4. Replace Temp with Query (임시 변수 제거)
**대상**: 복잡한 계산 로직
**방법**:
```python
# Before
def calculate_total(items):
    subtotal = sum(item.price for item in items)
    tax = subtotal * 0.1
    total = subtotal + tax
    return total

# After
def calculate_total(items):
    return self._get_subtotal(items) + self._get_tax(items)

def _get_subtotal(self, items):
    return sum(item.price for item in items)

def _get_tax(self, items):
    return self._get_subtotal(items) * 0.1
```

---

## ✅ 검증 기준

### 목표 달성 조건
1. **위반 건수**: 162개 → 20개 미만
2. **CC (순환 복잡도)**: ≤ 10
3. **Length (함수 길이)**: ≤ 80 lines
4. **Parameters**: ≤ 5
5. **mixed_responsibilities**: 0개

### 품질 검증
- ✅ `ruff` 통과 (0 errors)
- ✅ `mypy` 통과 (0 errors)
- ✅ `pytest` 통과 (0 failures)
- ✅ `bandit` 통과 (0 high severity)

---

## 📅 예상 일정

| 단계 | 작업 | 예상 소요 시간 | 완료 목표 |
|------|------|---------------|----------|
| 1 | CLI 모듈 리팩토링 | 4-6시간 | 2025-10-15 |
| 2 | 매칭 엔진 리팩토링 | 3-4시간 | 2025-10-15 |
| 3 | GUI 모듈 리팩토링 | 4-5시간 | 2025-10-15 |
| 4 | SQLite 캐시 리팩토링 | 2-3시간 | 2025-10-15 |
| 5 | 기타 모듈 리팩토링 | 3-4시간 | 2025-10-15 |
| 6 | 최종 검증 | 1-2시간 | 2025-10-15 |

**총 예상 소요 시간**: 17-24시간

---

## 🚨 주의사항

### 1. 회귀 방지
- 모든 리팩토링 전후에 테스트 실행
- 기존 테스트가 실패하면 즉시 롤백
- 새로운 테스트 작성으로 기능 보장

### 2. 성능 영향 최소화
- 매칭 엔진 리팩토링 시 성능 벤치마크 수행
- 불필요한 함수 호출 최소화
- 메모리 사용량 모니터링

### 3. 코드 가독성 향상
- 명확한 함수명 사용
- 적절한 docstring 작성
- 일관된 코딩 스타일 유지

---

**다음 단계**: 서브태스크 8.2 - CLI 모듈 리팩토링 시작
