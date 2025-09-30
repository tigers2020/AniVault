# AniVault v3 CLI 개발 계획서

## 프로젝트 개요

**AniVault v3 CLI**는 Windows 환경에서 동작하는 단일 실행파일(.exe) 기반의 콘솔 애플리케이션입니다. TMDB API를 활용한 애니메이션 파일 자동 정리 시스템으로, 사용자의 애니메이션 파일을 자동으로 인식하고 정리합니다.

## 핵심 목표

- **Windows 단일 실행파일(.exe) 1개**의 CLI 앱 v1.0
- **TMDB 레이트리밋 준수** (429 시 `Retry-After` 존중, ~50 rps 가이드)
- **JSON 캐시** (UTF-8, TTL 기반)
- **파일 로거** (레벨 분리, 회전, UTF-8)
- **UTF-8 전역** 처리
- **스레드 필수** (Producer-Consumer 패턴)

## 기술 스택

### 핵심 라이브러리
- **CLI Framework**: Click 8.1.0
- **UI/Display**: Rich 14.1.0, prompt_toolkit 3.0.48
- **File Parsing**: anitopy 2.1.1, parse 1.20.0 (fallback)
- **API Client**: tmdbv3api 1.9.0
- **Security**: cryptography 41.0.0
- **Packaging**: PyInstaller 6.16.0

### 개발 도구
- **Testing**: pytest 7.4.0, hypothesis 6.88.0
- **Code Quality**: ruff, mypy, pre-commit
- **Configuration**: tomli/tomli-w

## 아키텍처

### 모듈 구조
```
src/
├── core/           # 스캔·파싱·매칭·정리 파이프라인
├── services/       # TMDB 클라이언트, 캐시/키링, 설정
├── cli/           # Click 기반 커맨드 집합
├── ui/            # TUI 기반 사용자 인터페이스
└── utils/         # 로깅, rate-limit, 상태머신, 공통 DTO
```

### 스레드 파이프라인
- `ScanParsePool → MatchOrganizePool` (각 `ThreadPoolExecutor`)
- 단계 간 **bounded queue** + 백프레셔
- **레이트리밋 상태머신**: `Normal ↔ Throttle ↔ CacheOnly ↔ SleepThenResume`

### JSON 캐시
- 경로: `cache/objects/{tmdb_id}.json`, `cache/search/{qhash}.json`
- 키: `q_norm`(정규화된 쿼리), `ttl`, `created_at`, `schema_version`

## CLI 명령 설계

### TUI 기반 명령 (권장)
- `ui`: TUI 모드 진입 (기본 진입점)
- 홈 화면: Run Wizard, Profiles, Settings, Tools, Exit
- Run Wizard: 단계별 설정 → 실행 → 결과 확인

### CLI 기반 명령 (고급 사용자)
- `run`: 스캔→파싱→매칭→정리 전체 플로우
- `scan`: 대상 파일 나열
- `match`: TMDB 데이터 매칭
- `organize`: 파일 정리 및 이동 (기본 드라이런)
- `profile`: 프로필 관리
- `cache`: 캐시 관리
- `settings`: 환경설정
- `status`: 마지막 작업 스냅샷

## 36주 개발 로드맵

### 📅 **Phase 1: 기반 구축 (W1-W12)**

#### ✅ **W1-W2 — 리포 부팅 & 품질 가드** (완료)
- `pyproject.toml`, `src/` 스켈레톤, 핵심 라이브러리 설정
- pre-commit(Ruff/Black/Pyright), pytest 베이스, UTF-8 강제
- **위험 요소 검증**: anitopy C 확장, cryptography, tmdbv3api, PyInstaller 호환성
- **DoD**: `pytest` 통과, 로그 파일 생성/회전 시연, 모든 라이브러리 호환성 검증

#### ✅ **W3-W4 — 콘솔 단일 exe 번들 POC** (완료)
- PyInstaller/Nuitka 콘솔 모드 onefile POC, 클린 VM 실행
- **DoD**: `anivault-mini.exe` 실행 성공, TMDB API 실제 rate limit 확인

#### ✅ **W5-W6 — 스캔/파싱 파이프라인(스레드) + 캐시 v1** (완료)
- **Producer-Consumer 패턴**: Scanner → ParserWorker → 결과 수집
- **Bounded Queues**: 메모리 효율적 처리, 오버플로우 방지
- **Backpressure 정책**: 'wait' 정책으로 안정성 확보
- **DoD**: 스캔 P95 수치, 캐시 hit/miss 카운터, 메모리 사용량 검증

#### ✅ **W7 — 디렉토리 스캔 최적화 (Generator/Streaming)** (완료)
- **메모리 효율적 디렉토리 스캔**: os.scandir() 기반 Generator/Streaming 패턴
- **메모리 프로파일링**: 100k+ 파일에서 메모리 사용량 ≤500MB 검증
- **DoD**: 메모리 사용량 ≤500MB, 대용량 디렉토리 처리 안정성 검증

#### ✅ **W8 — 파싱 본/폴백 + 퍼저** (완료)
- **anitopy + 폴백 파서**: UnifiedFilenameParser로 통합된 파싱 시스템
- **Hypothesis 퍼징 테스트**: 1k+ 케이스 무크래시, 통계 일관성 검증
- **실세계 데이터셋**: 90개 라벨드 파일명으로 정확도 평가 시스템
- **DoD**: 파싱 실패율 ≤3%, 매칭 정확도 평가용 샘플셋 완성

#### ✅ **W9-W10 — TMDB 클라이언트 + 레이트리밋 상태머신** (완료)
- **토큰버킷 알고리즘**: 기본 35 rps 속도 제한, 스레드 안전한 토큰 관리
- **세마포어 동시성 제어**: 기본 4개 동시 요청 제한
- **429 복구 메커니즘**: `Retry-After` 헤더 우선 존중, 토큰버킷 리셋 로직
- **DoD**: 429 시나리오 자동 회복 데모 완성

#### ✅ **W11-W12 — 매칭 정확도 튜닝 + JSON 캐시 v2** (완료)
- **쿼리 정규화 시스템**: 파일명에서 불필요한 정보 제거, 유니코드 정규화
- **매칭 엔진**: 다단계 매칭 전략, 신뢰도 기반 매칭, 폴백 전략
- **캐시 v2 시스템**: TTL 지원, 태그 기반 캐시 관리, 자동 만료 처리
- **DoD**: @1 ≥90%/@3 ≥96%, MVP 데모 (scan → match → organize 기본 플로우) 완성

### 🔧 **Phase 2: 핵심 기능 개발 (W13-W24)**

#### **W13-W14 — organize(드라이런/세이프) + 롤백 로그**
- 네이밍 스키마 v1, 충돌 규칙, 파일 이동/복사
- **롤백 범위**: 파일 이동만 (디렉토리 구조 변경 제외)
- **DoD**: 드라이런 실제 변경 0, 롤백 스크립트 생성 및 검증

#### **W15-W16 — CLI 명령 완성**
- 공통 옵션 표준화, 머신리더블 `--json` 출력, 실시간 진행률 표시
- **DoD**: `run` 한 줄로 E2E 완료, 진행률 바 및 통계 업데이트 확인

#### **W17-W18 — 설정/보안(TMDB 키) + 키링**
- `anivault.toml` 설정 파일 구조, ENV 우선, PIN 기반 대칭키(Fernet) 저장
- **DoD**: 설정 저장/복호화 E2E, `anivault.toml` 예시 문서화

#### **W19-W20 — 장애/오프라인 UX & CacheOnly 플로우**
- 네트워크 다운/쿼터 고갈 시 **CacheOnly** 자동 전이
- **DoD**: 세 모드(Online/Throttle/CacheOnly) E2E, 실제 사용 환경 테스트 통과

#### **W21-W22 — 성능/메모리/캐시 적중 최적화 + 벤치**
- 워커·큐 튜닝, I/O 스트리밍, 캐시 워밍업, 대용량 디렉토리 메모리 프로파일링
- **DoD**: 캐시 적중 ≥90%, 스루풋 목표 충족, 10만+ 파일에서 메모리 ≤500MB

#### **W23-W24 — 통합 테스트 & 버그 수정**
- E2E 테스트 스위트, 성능 벤치마크, 버그 수정
- **DoD**: 모든 기능 통합 테스트 통과, 성능 목표 달성

### 🚀 **Phase 3: 안정화 & 릴리스 (W25-W36)**

#### **W25-W26 — 사용자 테스트 & 피드백 수집**
- 베타 테스트 계획: 50-100명 규모, Discord/Reddit 커뮤니티 모집
- **DoD**: 베타 테스트 완료, 주요 이슈 목록 정리, 사용자 만족도 ≥80%

#### **W27-W28 — 사용자 피드백 반영 & 개선**
- 베타 피드백 기반 기능 개선, 버그 수정, UX 개선
- **DoD**: 주요 피드백 반영 완료, 추가 기능 구현

#### **W29-W30 — 고급 기능 & 최적화**
- 배치 처리 최적화, 플러그인 아키텍처, 원격 캐시 동기화
- **DoD**: 고급 기능 구현, 성능 추가 최적화

#### **W31-W32 — 문서화 & 튜토리얼**
- 사용자 매뉴얼, API 문서, 튜토리얼 작성
- **DoD**: 완전한 문서화, 사용자 가이드 완성

#### **W33-W34 — 최종 테스트 & 품질 보증**
- 전체 시스템 테스트, 보안 검토, 성능 검증
- **DoD**: 모든 테스트 통과, 보안 검토 완료

#### **W35-W36 — 릴리스 준비 & 배포**
- **단일 exe** 릴리스 빌드, 릴리스 노트, 배포 준비
- **DoD**: v1.0 태그, 클린 Windows에서 exe 1개로 작동 확인, 공식 릴리스

## 성능 요구사항

- **메모리 사용량**: 500MB 이하
- **처리 속도**: 100k+ 파일 처리 가능
- **API 효율성**: 레이트리밋 준수
- **에러율**: 5% 이하 파싱 실패율
- **스캔 스루풋**: P95 ≥ 120k 경로/분
- **TMDB 매칭 정확도**: @1 ≥ 90%, @3 ≥ 96%
- **캐시 적중률**: 2회차 ≥ 90%

## 구현 규약

### UTF-8 전역
- 소스/리소스/입출력/로그/JSON 모두 `encoding="utf-8"`

### JSON 캐시 스키마
```json
{
  "schema_version": 1,
  "created_at": "2025-09-27T16:00:00Z",
  "ttl_sec": 2592000,
  "key": {
    "q_norm": "evangelion 1995",
    "lang": "ko-KR",
    "year_hint": 1995
  },
  "data": {...},
  "source": "tmdb:search/tv"
}
```

### 레이트리밋 준수
- **토큰버킷**: 기본 35 rps (TMDB 상한 ~50 rps 대비 안전 마진)
- **429**: 즉시 `Throttle` 전이 → **`Retry-After` 우선 존중**
- **회로차단기**: 5분 이상 429/5xx 비율 >60% 시 CacheOnly

### 스레드 정책
- CPU계(파싱)와 I/O계(스캔/네트워크/정리) 분리 튜닝
- TMDB 호출은 **세마포어**로 동시요청 상한

## CLI 사용 예시

### TUI 기반 사용 (권장)
```bash
anivault.exe ui
# 홈 화면 → Run Wizard → 경로/옵션 설정 → 드라이런 실행
```

### CLI 기반 사용 (고급 사용자)
```bash
# 첫 실행 (키 설정 & 드라이런)
anivault.exe settings set --tmdb-key %TMDB_KEY%
anivault.exe run --src D:\Anime --dst E:\Vault --dry-run --lang ko-KR --rate 35

# 계획 파일 생성 및 실행
anivault.exe organize --src D:\Anime --dst E:\Vault --plan out\plan.json
anivault.exe organize --from-plan out\plan.json --apply

# 실행 재개
anivault.exe run --resume
```

## 리스크 & 대응

| 리스크 | 징후 | 대응 |
|--------|------|------|
| onefile 번들 실패 | 콘솔 실행 즉시 ImportError | W2 POC로 조기 확인, PyInstaller↔Nuitka 스위치 |
| 429 급증/정책 변경 | 매칭 지연 급등, 실패율 증가 | 상태머신 파라미터 설정화, 핫패치/환경변수로 조정 |
| 로그 I/O 병목 | 디스크 쓰기 대기, 속도 저하 | 비동기 큐잉/버퍼, 로그 레벨 동적 하향 |
| 캐시 오염/스키마 충돌 | 매칭률 급락 | schema_version 엄격, 무효화/TTL·워밍업 루틴 |

## 개발 순서 검증

이 개발 계획서의 순서는 **매우 논리적이고 체계적**입니다:

1. **의존성 검증 우선** (W1-W2): anitopy, cryptography 등 C 확장 라이브러리의 PyInstaller 호환성
2. **단일 exe 검증** (W3-W4): 번들링이 안 되면 프로젝트 자체가 불가능
3. **핵심 파이프라인** (W5-W6): 스캔→파싱→매칭→정리의 기본 흐름
4. **성능 최적화** (W7): 메모리 효율성, 대용량 처리
5. **정확도 향상** (W8): 파싱 정확도, 매칭 정확도
6. **안정성** (W9-W12): 레이트리밋 준수, 에러 복구

이 순서는 **점진적 복잡성 증가**와 **위험 요소 조기 해결**에 초점을 맞춘 훌륭한 전략입니다.

---

## 📋 문서 업데이트 이력

**2025-01-27 (v1.0)**
- AniVault v3 CLI 개발 계획서 초기 작성
- 36주 로드맵 정의 및 개발 순서 검증
- 기술 스택, 아키텍처, 성능 요구사항 명시
