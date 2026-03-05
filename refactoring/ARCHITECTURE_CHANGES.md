# AniVault 리팩토링 아키텍처 변경사항

> Phase 0~2 완료 시점 기준 (2025-02-01)

---

## 1. Phase 1: God Function 해소

### cli/helpers 구조 변경

| 기존 | 변경 후 |
|------|---------|
| match.py (553줄) | match.py + **match_formatters.py** + **format_utils.py** |
| organize.py | organize.py + **organize_formatters.py** |
| scan.py | scan.py + **scan_formatters.py** (re-export) |

**추가 모듈**
- `cli/helpers/format_utils.py` - 공통 포맷 유틸리티
- `cli/helpers/match_formatters.py` - 매칭 결과 포맷팅/통계
- `cli/helpers/organize_formatters.py` - 정리 결과 포맷팅
- `cli/helpers/scan_formatters.py` - 스캔 결과 포맷팅 (`collect_scan_data`, `display_scan_results`)

---

## 2. Phase 2: God Module 분리

### core/file_grouper/matchers

| 기존 | 변경 후 |
|------|---------|
| title_matcher.py (843줄) | title_matcher.py + **title_index.py** |

**추가 모듈**
- `core/file_grouper/matchers/title_index.py` - `TitleIndex`, `MAX_TITLE_LENGTH`

### core (루트)

| 기존 | 변경 후 |
|------|---------|
| subtitle_matcher.py (828줄) | subtitle_matcher.py + **subtitle_hash.py** + **subtitle_index.py** |

**추가 모듈**
- `core/subtitle_hash.py` - `calculate_file_hash`, `HASH_CHUNK_SIZE`
- `core/subtitle_index.py` - `SubtitleIndex`, `SubtitleIndexCache`, `CachedSubtitleIndex`

**통합**
- `services/index_state_manager.py` - `calculate_file_hash` → `subtitle_hash`에서 import

### core/pipeline/components

| 기존 | 변경 후 |
|------|---------|
| scanner.py (755줄) | scanner.py + **scan_filters.py** |

**추가 모듈**
- `core/pipeline/components/scan_filters.py` - Collector 패턴 필터 로직
  - `has_valid_extension`, `should_include_file`, `should_skip_directory`
  - `filter_directories_in_place`, `process_file_entry`

---

## 3. Import 경로 (하위 호환)

| 대상 | 경로 | 비고 |
|------|------|------|
| TitleIndex | `file_grouper.matchers.title_matcher` 또는 `title_index` | re-export 유지 |
| calculate_file_hash | `core.subtitle_hash` | index_state_manager 통합 |
| DirectoryScanner | `pipeline.components.scanner` | 변경 없음 |
| collect_scan_data | `cli.helpers.scan` | scan.py re-export |

---

## 4. Phase 3: shared/constants 정리 ✅

### 3-1. cli 분리 (shared 내부)

| 모듈 | 내용 |
|------|------|
| `shared/constants/cli/formatting.py` | `CLIFormatting` |
| `shared/constants/cli/messages.py` | `CLIMessages` |
| `shared/constants/cli/config.py` | WorkerConfig, QueueConfig, CLIOptions, CLIHelp, CLIDefaults 등 |

### 3-2. 도메인별 그룹화

| 패키지 | 내용 |
|--------|------|
| `shared/constants/matching/` | matching.py → matching/__init__.py |
| `shared/constants/cli/` | cli.py, cli_formatting.py, cli_messages.py 통합 |
| `shared/constants/pipeline/` | system.pipeline re-export |

**권장 import 경로**
- `from anivault.shared.constants.matching import MatchingAlgorithm`
- `from anivault.shared.constants.cli import CLIDefaults`
- `from anivault.shared.constants.pipeline import Pipeline`

---

## 5. Phase 4·5 완료 및 이후 보완

- **Phase 4**: shared/errors 카탈로그화 — 완료
- **Phase 5**: Clean Architecture 도입 — 완료 (domain, app, infrastructure)
- **이후 보완** (God Module 후속):
  - `core/pipeline/utils/result_converters.py`: `dict_to_file_metadata` (collector에서 추출)
  - `core/file_grouper/grouping_weights.py`: `get_default_weights_from_config` (grouping_engine에서 추출)
  - `scripts/detect_circular_imports.py`: 순환 import 검증 스크립트 추가
