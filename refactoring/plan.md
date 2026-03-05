---
name: AniVault Refactoring Plan
overview: AniVault 프로젝트의 실무 기준 리팩토링 플랜으로, God Module/Function 해소, 의존성 단방향화, 점진적 Clean Architecture 적용을 포함합니다.
todos: []
isProject: false
---

# AniVault 리팩토링 플랜 (실무 기준)

## 0. 리팩토링 전 전제

| 체크  | 항목     | 현재 상태                                            |
| --- | ------ | ------------------------------------------------ |
| [ ] | 기능 명확성 | CLI/GUI 스캔→매칭→정리 파이프라인                           |
| [ ] | 기준 버전  | `feature/algorithm-improvement` 브랜치              |
| [ ] | 실행 테스트 | `pytest tests/` + `anivault scan/match/organize` |

**권장**: 리팩토링 전 `git tag refactor-baseline` 생성

---

## 1. 현 상태 분석 (Inventory)

### 1-1. 파일 구조 요약

```
src/anivault/
├── cli/           # CLI 진입점 (typer_app, handlers, helpers)
├── config/        # 설정 로더, 검증, 모델
├── core/          # 도메인 로직 (matching, pipeline, file_grouper, parser, organizer)
├── gui_v2/        # PySide6 GUI
├── security/      # 암호화, 권한
├── services/      # TMDB, enricher, rate_limiter, cache
├── shared/        # constants(20+), models, protocols, types, utils
├── utils/         # encoding, logging, resource_path
└── containers.py  # DI (dependency-injector)
```

### 1-2. God Module 식별 (400줄 이상)

| 순위  | 파일                                                                           | LOC | 위험도    | 유형           |
| --- | ---------------------------------------------------------------------------- | --- | ------ | ------------ |
| 1   | title_matcher.py                                                             | 843 | High   | God Module   |
| 2   | subtitle_matcher.py                                                          | 828 | High   | God Module   |
| 3   | scanner.py                                                                   | 755 | High   | God Module   |
| 4   | collector.py                                                                 | 710 | High   | God Module   |
| 5   | grouping_engine.py                                                          | 669 | High   | God Module   |
| 6   | shared/errors.py                                                             | 631 | Medium | 중복/카탈로그      |
| 7   | cli/helpers/match.py                                                         | 553 | High   | God Function |
| 8   | typer_app.py                                                                 | 481 | Medium | God Module   |
| 9   | shared/constants/cli.py                                                      | 403 | Medium | 범용 쓰레기통      |

### 1-3. 의존성 흐름

- **순환 import 대응**: `lazy import`, `config/__init__.py` loader 직접 참조, `detect_circular_imports` CI 훅
- **Protocol 기반 DI**: TMDBClientProtocol 존재
- **핫스팟**: `cli/helpers/match.py` 27개 import, `run_handler.py` 19개 import

---

## 2. 리팩토링 대상 우선순위 보고서

### Phase 0: 준비 (행동 변경 없음)

| 작업                                      | 목적          |
| --------------------------------------- | ----------- |
| `git tag refactor-baseline`             | 롤백 기준점      |
| `pytest -q --tb=short` 전체 통과 확인         | 회귀 기준       |
| `scripts/detect_circular_imports.py` 실행 | 현재 순환 여부 파악 |

### Phase 1: God Function 해소 (우선순위 High)

| 대상                                                              | 전략                                                                                     | 예상 diff  |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------- |
| cli/helpers/match.py                                            | 함수 분리: `_format_match_table`, `_build_match_stats` → `cli/helpers/match_formatters.py` | +80, -60 |
| cli/helpers/organize.py                                         | 동일 패턴 적용                                                                               | +50, -40 |
| cli/helpers/scan.py                                              | 동일 패턴 적용                                                                               | +40, -30 |

**규칙**: 함수 20~30줄 이하, 인자 3개 이하

### Phase 2: God Module 분리 (우선순위 High)

| 대상                                                                           | 전략           | 세부                                                                           |
| ---------------------------------------------------------------------------- | ------------ | ---------------------------------------------------------------------------- |
| title_matcher.py                                                            | 책임 분리        | `_scoring_logic` → `title_scorer.py`, `_index_build` → `title_indexer.py`    |
| subtitle_matcher.py                                                          | 책임 분리        | `_hash_compute` → `subtitle_hash.py`, `_index_build` → `subtitle_indexer.py` |
| scanner.py                                                                   | Collector 패턴 | `_filter_files`, `_collect_metadata` → 별도 함수/클래스                             |

### Phase 3: shared/constants 정리 (우선순위 Medium)

| 현상                                                                   | 대응                                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `shared/constants/` 20+ 파일                                           | 도메인별 그룹화: `constants/matching/`, `constants/cli/`, `constants/pipeline/`    |
| shared/constants/cli.py 403줄                                         | `CLIFormatting`, `CLIMessages` → `cli/formatting.py`, `cli/messages.py`로 이동 |

### Phase 4: shared/errors 카탈로그화 (우선순위 Medium)

| 현상                                                     | 대응                                                                                                            |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| shared/errors.py 631줄                                 | `ErrorCode` + `ErrorContext` 패턴으로 재구성                                                                     |

---

## 3. Clean Architecture 적용 방향 (Serin 스타일)

### 3-1. 현재 vs 목표 구조

- **현재**: CLI/GUI → Core/Services/Shared (양방향 의존)
- **목표**: CLI/GUI → UseCases → Entities/Interfaces ← infrastructure

### 3-2. 점진적 마이그레이션

| 단계     | 작업                                                          | 영향 범위                                |
| ------ | ----------------------------------------------------------- | ------------------------------------ |
| Step 1 | `domain/entities/` 생성, `FileMetadata`, `ParsingResult` 등 이동 | shared/models → domain/entities      |
| Step 2 | `domain/interfaces/` 확장, `TMDBClientProtocol` 등 정리          | shared/protocols → domain/interfaces |
| Step 3 | `app/use_cases/` 생성, `MatchUseCase`, `OrganizeUseCase` 추출   | cli/helpers + core/pipeline          |
| Step 4 | `infrastructure/` 명시화, tmdb, cache, db 분리                   | services/ → infrastructure/          |

### 3-3. 의존성 규칙

- **domain**: 외부 의존성 없음
- **app**: domain만 import
- **infrastructure**: domain interfaces 구현
- **cli/gui**: app use_cases만 호출

---

## 4. 점진적 리팩토링 전략

| Phase   | 내용                    | 테스트                  | 롤백                  |
| ------- | --------------------- | -------------------- | ------------------- |
| Phase 0 | 파일 이동만 (로직 변경 없음)     | import 테스트           | git revert          |
| Phase 1 | 함수 분리 (cli/helpers)   | pytest unit          | 1 commit            |
| Phase 2 | God Module 분리 (core)  | pytest + integration | 1 commit per module |
| Phase 3 | constants 재구성         | import 테스트           | 1 commit            |
| Phase 4 | errors 카탈로그화          | test_errors.py       | 1 commit            |
| Phase 5 | Clean Architecture 도입 | 전체 회귀                | 점진적 PR              |

---

## 5. 완료 기준 체크리스트

- 기능 동일 (scan/match/organize 동작 불변)
- import 구조 단순화 (순환 import 0)
- 중복 제거 (DRY)
- `ruff=0`, `mypy=0`, `pytest=0f`
- "다시 봐도 이해됨" (함수 30줄 이하, 모듈 400줄 이하)
