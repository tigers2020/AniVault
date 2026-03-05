# God Module 후속 분석

> 작성일: 2025-02-03  
> 기준: [plan.md](plan.md) Phase 2 이후

## 1. 현황 측정

| 모듈 | LOC | 400줄 기준 | 권장 조치 |
|------|-----|------------|-----------|
| `core/pipeline/components/collector.py` | 710 | 초과 | 책임 분리 검토 |
| `core/file_grouper/grouping_engine.py` | 669 | 초과 | 전략/위임 패턴 검토 |
| `cli/typer_app.py` | 481 | 초과 | 명령별 서브모듈 검토 |

## 2. collector.py 분석

### 현재 책임
- `_dict_to_file_metadata`: 파서 결과 → FileMetadata 변환
- `ResultCollector`: 출력 큐 소비, 결과 수집, 종료 신호 처리
- 큐 폴링, 타임아웃, 에러 처리, 통계 수집

### 분리 제안
| 추출 대상 | 대상 모듈 | 내용 |
|-----------|-----------|------|
| `_dict_to_file_metadata` | `collector_converters.py` 또는 `pipeline/utils/result_converters.py` | 파서 dict → FileMetadata 변환 로직 |
| 통계/로깅 헬퍼 | 기존 `domain/statistics.py` 활용 | 통계 포맷팅 등 재사용 검토 |

### 우선순위: 중
- 변환 로직 분리는 의존성 변경 적음
- ResultCollector 자체는 스레드/큐 로직이 밀집되어 있어 단일 클래스 유지 권장

## 3. grouping_engine.py 분석

### 현재 책임
- `_get_default_weights_from_config`: 설정에서 가중치 로드
- `GroupingEngine`: 매처 조정, 가중치 검증, 그룹 생성, 증거 수집
- `_validate_weights`, `_run_matchers`, `_merge_results` 등

### 분리 제안
| 추출 대상 | 대상 모듈 | 내용 |
|-----------|-----------|------|
| `_get_default_weights_from_config` | `grouping_weights.py` 또는 config 모듈 | 설정 로딩 분리 |
| `_validate_weights` | `GroupingEngine` 내 private 유지 또는 `validators.py` | 검증 로직 |
| 매처 실행/병합 | 전략 패턴으로 위임 | `GroupingStrategy` 확장 (이미 strategies.py 존재) |

### 우선순위: 중
- `strategies.py`에 `BestMatcherStrategy` 등 이미 존재
- `GroupingEngine`이 strategy를 주입받도록 되어 있어, 전략 쪽으로 로직 이동 가능

## 4. typer_app.py 분석

### 현재 책임
- Typer 앱 초기화, 명령 등록, 공통 옵션
- scan, match, organize, run, verify, log, rollback 등 명령 라우팅

### 분리 제안
| 추출 대상 | 대상 모듈 | 내용 |
|-----------|-----------|------|
| 명령별 콜백 | `cli/commands/` 서브모듈 | `scan_command`, `match_command` 등을 각 모듈로 이동 |
| 공통 옵션 | `cli/common/options.py` | `--dry-run`, `--json` 등 |

### 우선순위: 중~낮음
- 481줄로 400 초과폭이 작음
- 명령이 이미 handler/helpers로 분리되어 있어, typer_app은 라우팅 위주

## 5. 실행 권장 순서

1. **collector**: `_dict_to_file_metadata` → `pipeline/utils/` 또는 `collector_converters.py`로 추출
2. **grouping_engine**: `_get_default_weights_from_config` → config/grouping 헬퍼로 추출
3. **typer_app**: 명령 등록을 `cli/commands/` 모듈로 분산 (선택)

## 6. 참고

- [ARCHITECTURE_CHANGES.md](ARCHITECTURE_CHANGES.md) - Phase 1~2 변경사항
- [plan.md](plan.md) - 리팩토링 플랜 원문
