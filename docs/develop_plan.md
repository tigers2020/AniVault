Role: 기술 PM

다음은 제로에서 시작·**단일 실행파일(.exe) 1개**·**TMDB 레이트리밋 준수**·**JSON 캐시**·**파일 로거**·**UTF-8 전제**·**스레드 필수** 조건을 반영한 **AniVault v3 CLI 개발 계획서**입니다.
(레이트리밋 근거: TMDB는 2019.12 이후 레거시 한도(10초당 40요청)를 비활성화했지만, **상한 ~50 rps 수준(커뮤니티 관찰치)**으로 과도한 벌크 스크레이핑 방지를 위해 **429 수신 시 `Retry-After` 우선 존중**을 요구합니다. 정책은 변동 가능. ([The Movie Database (TMDB)][1]))

---

# 0) Tree of Thought 협업 진행 (CLI 한정)

**1단계 — 각 전문가 1차 제안**

* **전문가 A · 제품기획**
  "**CLI→API→GUI** 원칙 유지하되, 이번 문서는 **CLI만**. 사용자 스토리는 '**한 줄 명령으로 스캔→매칭→정리**'가 끝난다. **단일 exe**는 W2에 콘솔 전용 번들 POC로 검증. 기본 명령은 `scan`, `match`, `organize`, `run`(일괄 플로우), `cache`, `settings`."
* **전문가 B · 아키텍트**
  "GUI 없이도 **스레드 파이프라인**(Scan→Parse→Match→Organize)은 동일. **레이트리밋 상태머신**과 **토큰버킷**은 CLI 전면. **JSON 캐시**는 q_norm+locale 키 정규화+TTL. CLI는 **프로세스 안전 종료/재시작(resume)** 지원."
* **전문가 C · QA/DevOps**
  "**UTF-8 절대값**, **파일 로거 회전** 필수. 테스트는 **E2E·계약 테스트(가짜 TMDB)** + **하드 레이트리밋 시뮬**. **Nuitka or PyInstaller onefile**로 콘솔 앱 번들. 매 스프린트 **스모크**와 **벤치** 자동화."

**2단계 — 상호 보정**

* A: "`run`은 초심자에 유용. 고급 사용자는 단계별 명령을 쓸 수 있게 **공통 옵션**(입출력 루트, dry-run, 언어, 동시성, rate-limit)을 통일."
* B: "동시성은 `--max-workers`와 **TMDB 동시요청 세마포어**를 분리. 429 수신 시 `Throttle→CacheOnly` 전이 포함."
* C: "**단일 exe**는 콘솔 모드로 우선. 로그는 `logs/`에 등급별. **클린 VM 실행**을 DoD로 못 박자."

**3단계 — 탈락 검토 & 합의**

* 이견 없음. 세 전문가는 "**CLI 중심**으로 위 원칙을 고정"에 합의.
  ⇒ **최종 해법**: **CLI 단일 exe**를 목표로, **스레드 파이프라인 + 레이트리밋 상태머신 + JSON 캐시 + 파일 로거(UTF-8)** 를 12주 안착.

---

# 1) 목표 & 제약(변하지 않는 것)

* **핵심 목표**: **Windows 단일 실행파일(.exe) 1개**의 **CLI 앱** v1.0 (GUI는 무관)
* **호환성**: Windows 10/11 (주 타겟)
* **불변 제약**

  1. 제로에서 시작, 2) **단일 exe**(별도 설치 無), 3) **TMDB 레이트리밋 준수(429 존중, ~50 rps 가이드, 정책 변동 대응)**,
  4. **JSON 캐시(UTF-8)**, 5) **파일 로거(레벨 분리·회전·UTF-8)**, 6) **UTF-8 전역**, 7) **스레드 필수**, 8) **계약 고정(파괴적 변경 금지)**

---

# 2) 기술 스택 & 핵심 라이브러리

## 🏗️ 핵심 인프라 라이브러리

### CLI 프레임워크
* **Click 8.1.0** (1순위, 권장)
  * 직관적인 데코레이터 기반 CLI
  * 자동 도움말 생성, 타입 검증
  * PyInstaller 호환성 우수

### HTTP 클라이언트 (TMDB API)
* **tmdbv3api 1.9.0** (1순위, 권장)
  * TMDB API 전용 Python 라이브러리
  * 라이브러리 차원의 자동 레이트리밋은 제공하지 않으므로, 내부 `tmdb_client`에서 **토큰버킷(기본 35 rps)**, **429 시 `Retry-After` 준수 + 지수 백오프**, **동시요청 세마포어**를 구현
  * PyInstaller 호환, 간편한 사용법
  * 예시: `tv.search("Attack on Titan")`, `tv.details(tv_id)`
* **httpx 0.25.0** (2순위, 폴백)
  * async/sync 모두 지원, 직접 구현 시 사용
  * 미들웨어/어댑터로 레이트리밋, 재시도 로직을 우리가 구현
  * **폴백 전략**: tmdbv3api 이슈 시 추상화 레이어를 통해 빠른 전환

## 📁 파일 처리 & 파싱

### 애니메이션 파일명 파싱
* **anitopy 2.1.1** (필수, MPL-2.0)
  * 애니메이션 파일명 파싱 특화
  * C++ 확장으로 빠름
  * ⚠️ PyInstaller 호환성 W1에서 반드시 검증 필요
* **parse 1.20.0** (폴백 파서)
  * 순수 Python, 패턴 매칭
  * anitopy 실패 시 백업

### CLI UX & 진행률 표시
* **rich 14.1.0**
  * 아름다운 CLI UI (프로그레스 바, 컬러링)
  * 실시간 통계 테이블, 에러 출력 포매팅

## 🗄️ 캐시 & 데이터 처리

### 설정 파일
* **tomli 2.0.0** (Python < 3.11)
* **tomli-w 1.0.0** (쓰기 지원)
* Python 3.11+에서는 내장 tomllib 사용

## 🔐 보안 & 암호화

### API 키 암호화
* **cryptography 41.0.0**
  * Fernet 대칭 암호화
  * PIN 기반 키 저장, 크로스 플랫폼 지원

## 🧪 테스트 & 개발

### 테스트 프레임워크
* **pytest 7.4.0** + **pytest-cov 4.1.0** (커버리지)
* **pytest-mock 3.11.0** (목킹)
* **pytest-httpx 0.21.0** (HTTP 요청 목킹)
* **hypothesis 6.88.0** (속성 기반 테스트, 파일명 퍼징)
* **pytest-vcr 1.0.2** (VCR 스타일 HTTP 레코딩)

### 코드 품질
* **ruff 0.1.0** (린팅 + 포매팅, Black 대체)
* **mypy 1.6.0** (타입 체킹)
* **pre-commit 3.5.0** (Git 훅)

## 📦 패키징 & 배포

### 단일 실행파일 생성
* **PyInstaller 6.16.0** (1순위, 권장)
* **Nuitka 1.8.4** (2순위, 백업)

## ⚠️ 주의사항

**1. PyInstaller 호환성 검증 필수**
* `anitopy` (C 확장)
* `cryptography` (네이티브 라이브러리)
* `tmdbv3api` (requests 기반, 안정적)
* W1-W2에서 반드시 번들링 테스트

**2. 의존성 최소화 원칙**
* 단일 exe 크기 최소화
* 필수가 아닌 기능은 선택사항으로

---

# 3) 아키텍처(CLI 편성)

* **패키징**: 우선 **PyInstaller `--onefile --console`** → 실패 시 **Nuitka onefile** 콘솔 앱.
  임시 디렉토리 풀림 허용. (복잡한 의존성에서 PyInstaller가 더 안정적)
* **모듈 레이어**

  * `core/` : 스캔·파싱·매칭·정리(파일 I/O) 파이프라인
  * `services/` : TMDB 클라이언트, 캐시/키링, 설정
  * `cli/` : `click` 기반 커맨드 집합 (데코레이터 기반, 자동 도움말, 타입 검증)
  * `utils/` : 로깅, rate-limit(토큰버킷), 상태머신, 공통 DTO
* **스레드 파이프라인**

  * `ScanParsePool → MatchOrganizePool` (각 `ThreadPoolExecutor`)
  * 단계 간 **bounded queue** + 백프레셔(대기/드롭 정책 선택 가능)
* **레이트리밋 상태머신**

  * 상태: `Normal ↔ Throttle ↔ CacheOnly ↔ SleepThenResume`
  * 트리거: `HTTP 429`, `Retry-After`, 지연 P95 상승
  * 행동: **`Retry-After` 우선 존중**, 지수 백오프, 동시성 축소, 캐시 우선, 배치 휴면
* **JSON 캐시**

  * 경로: `cache/objects/{tmdb_id}.json`, `cache/search/{qhash}.json`
  * 키: `q_norm`(정규화된 쿼리), `ttl`, `created_at`, `schema_version`
    * 정규화 알고리즘: 소문자화 → 기본 정리 → 연도 힌트 추가 (불용어 제거/정렬 제외로 매칭 정확도 보장)
* **로깅(UTF-8)**

  * `logs/app.log`(앱 전체 로그), `network.log`(TMDB 통신 전용)
  * `TimedRotatingFileHandler`(일 단위), 보존일 N

---

# 4) CLI 명령 설계

* `run` : 스캔→파싱→매칭→정리 전체 플로우(기본 진입점)
  예) `anivault.exe run --src D:\Anime --dst E:\Library --lang ko-KR --dry-run`
* `scan` : 대상 파일 나열(+ 확장자 필터, 동시성)
* `match` : 캐시 우선→TMDB 검색/상세 조회→캐시 적재
* `organize` : 네이밍 스키마 적용, 이동/복사, 충돌 규칙, 롤백 로그 (**기본 드라이런**, 실제 변경은 `--apply` 필요)
  * 기본 패턴: `{title_ascii_or_native} ({year}) S{season:02d}{episode_token}.{ext}`
  * 멀티에피소드: `episode_token` = `E{ep_start:02d}-E{ep_end:02d}`
  * 스페셜: `Season 00` 고정
  * 다국어 처리: `--lang` → TMDB `translations` → 영어 폴백
* `cache` : 조회/삭제/워밍업/적중률 통계
* `settings` : TMDB 키 세팅(ENV 우선), 기본 스레드·토큰버킷 파라미터 보기/변경
  * 설정 파일 우선순위: 1) 환경변수 → 2) `{exe_dir}/anivault.toml` → 3) `{user_home}/.anivault/config.toml`
* `status` : 마지막 작업 스냅샷/메트릭 출력
* 공통 옵션(모든 명령 공통):
  `--lang`, `--max-workers`, `--tmdb-concurrency`(세마포어), `--rate`(토큰/초),
  `--dry-run`, `--resume`, `--log-level`, `--no-color`, `--json`(머신리더블 출력)
* **안전 기본값**: `organize`와 `run`은 **기본 드라이런**이며, 실제 변경은 `--apply`가 요구됨
* **계획 파일**: `--plan out\plan.json` → 사용자 검토 후 `anivault.exe organize --from-plan out\plan.json --apply`

**CLI UX 예시 (실시간 + 요약 출력)**

```
$ anivault.exe run --src D:\Anime --dst E:\Vault --lang ja-JP --rate 35 --tmdb-concurrency 4
[INFO] Scanning: 12,483 files found | ████████████░░░░ 75% (9.3k/s)
[INFO] Parsing: 11,891/12,483 files | Parse fail 1.9% | ████████████████ 100%
[WARN] 429 detected → Throttle(1.6s) → Retry-After: 2
[INFO] Matching: 8,234/11,891 files | Cache hit 88% | ████████░░░░░░░░ 69%
[INFO] Organizing: 11,902 files (dry-run) | ████████████████ 100%
[INFO] Final: Match@1 91.3% (@3 96.7%) | Metrics: logs/app.log; cache: cache/index.json
```

---

# 5) KPI (CLI 관점)

* **스캔 스루풋** P95 ≥ **120k 경로/분** (목표, 실제 테스트 결과에 따라 조정 가능)
  * 측정 환경: Windows 10/11, SSD, 디렉토리 깊이 ≤5단계, 파일당 평균 10KB
  * AV 제외, 백그라운드 프로세스 최소화
  * **대용량 처리**: 제너레이터 기반 스트리밍, 메모리 사용량 ≤500MB (목표, 실제 테스트 결과에 따라 조정)
  * **호환성**: Windows 10/11 최적화, Windows 7/8 기본 지원 (성능 제한 가능)
  * **현실성**: 네트워크 드라이브나 깊은 디렉토리 구조에서는 성능 저하 예상
* **파싱 실패율** ≤ **3%**
  * anitopy + 폴백 파서 조합 기준
* **TMDB 매칭 정확도** @1 ≥ **90%**, @3 ≥ **96%**
  * 라벨드 샘플셋: 일본 애니메이션 70%, 서양 애니메이션 30% (W4에서 준비)
  * 평가 기준: 제목 완전/부분 일치, 시즌/에피소드 번호 정확도, 다국어 제목 처리
* **2회차 캐시 적중률** ≥ **90%**
  * 동일 디렉토리 재스캔 시 기준
* **복구성**: `--resume` 재시작 시 **중복 처리 없음**, 마지막 체크포인트 ≤ **30초** 손실

---

# 6) 36주 스프린트 (CLI 한정, 3개월씩 3개 페이즈)

## 📅 **Phase 1: 기반 구축 (W1-W12)**

**W1-W2 — 리포 부팅 & 품질 가드**

* `pyproject.toml`, `src/` 스켈레톤, **핵심 라이브러리 설정** (Click, tmdbv3api, anitopy, rich, cryptography)
* pre-commit(Ruff/Black/Pyright), pytest 베이스, UTF-8 강제
* **로거 회전 템플릿**, **위험 요소 집중 검증**
* **위험 요소 검증 목록**:
  * anitopy C 확장 + PyInstaller 호환성 (최우선)
  * cryptography 네이티브 라이브러리 + PyInstaller 호환성
  * **tmdbv3api 상세 검증**:
    - 실제 레이트리밋 처리 방식 확인
    - 429 에러 발생 시 Retry-After 헤더 처리 테스트
    - 장시간 실행 시 메모리 사용 패턴 확인
    - 네트워크 타임아웃 처리 검증
  * Windows 7/8/10/11에서 exe 실행 테스트
  * 대용량 SSD vs HDD 성능 차이 측정
  * TMDB API 키 발급 프로세스 검증
* **DoD**: `pytest` 통과, 로그 파일 생성/회전 시연, 모든 라이브러리 호환성 검증 완료

**W3-W4 — 콘솔 **단일 exe** 번들 POC**

* PyInstaller/Nuitka 콘솔 모드 onefile POC, **클린 VM 실행**, **위험 요소 조기 검증**
* **DoD**: `anivault-mini.exe` 실행 성공, TMDB API 실제 rate limit 확인, Windows 다양한 버전 테스트

**W5-W6 — 스캔/파싱 파이프라인(스레드) + 캐시 v1**

* 확장자 화이트리스트, 진행률, bounded queues
* `cache/search/*.json` 스키마 v1, **메모리 프로파일링 조기 테스트**
* **메모리 테스트**: 10만+ 파일에서 500MB 제한, 제너레이터/스트리밍 패턴 검증
* **DoD**: 스캔 P95 수치, 캐시 hit/miss 카운터, 메모리 사용량 검증 완료

**W7-W8 — 파싱 본/폴백 + 퍼저**

* anitopy + 폴백 파서, Hypothesis 1k 케이스 무크래시, 라벨드 샘플셋 준비
* **DoD**: 파싱 실패율 ≤3%, 매칭 정확도 평가용 샘플셋 완성

**W9-W10 — TMDB 클라이언트 + 레이트리밋 상태머신(1차)**

* 토큰버킷(기본 35 rps, TMDB 상한 ~50 rps 대비 안전 마진), 세마포어 동시요청 제한
* 429→Throttle 전이, **`Retry-After` 우선 존중**
* **DoD**: 429 시나리오 자동 회복 데모

**W11-W12 — 매칭 정확도 튜닝 + JSON 캐시 v2**

* 쿼리 정규화, 언어/연도 힌트, 캐시 TTL/버전
* **Phase 1-2 연결점**: 매칭 정확도 달성 후 organize 기능 개발 시 의존성 검증
* **DoD**: @1 ≥90%/@3 ≥96%, MVP 데모 (scan → match → organize 기본 플로우) 완성

## 🔧 **Phase 2: 핵심 기능 개발 (W13-W24)**

**W13-W14 — organize(드라이런/세이프) + 롤백 로그**

* 네이밍 스키마 v1, 충돌 규칙, 파일 이동/복사
* **롤백 범위**: 파일 이동만 (디렉토리 구조 변경 제외), 부분 실패 시 마지막 성공 지점까지 복원
* **DoD**: 드라이런 실제 변경 0, 롤백 스크립트 생성 및 검증

**W15-W16 — CLI 명령 완성(run/scan/match/organize/cache/settings/status)**

* 공통 옵션 표준화, 머신리더블 `--json` 출력, 실시간 진행률 표시
* **DoD**: `run` 한 줄로 E2E 완료, 진행률 바 및 통계 업데이트 확인

**W17-W18 — 설정/보안(TMDB 키) + 키링(폴백 암호화)**

* `anivault.toml` 설정 파일 구조, ENV 우선, 없으면 PIN 기반 대칭키(Fernet) 저장
* **DoD**: 설정 저장/복호화 E2E, `anivault.toml` 예시 문서화

**W19-W20 — 장애/오프라인 UX & CacheOnly 플로우**

* 네트워크 다운/쿼터 고갈 시 **CacheOnly** 자동 전이
* **사용자 중심 검증**:
  * 불안정한 Wi-Fi 환경에서의 재시도 로직
  * Windows Defender 실시간 보호와의 상호작용
  * 매우 긴 파일명 (260자 제한) 처리
* **DoD**: 세 모드(Online/Throttle/CacheOnly) E2E, 실제 사용 환경 테스트 통과

**W21-W22 — 성능/메모리/캐시 적중 최적화 + 벤치**

* 워커·큐 튜닝, I/O 스트리밍, 캐시 워밍업, 대용량 디렉토리 메모리 프로파일링
* **DoD**: 캐시 적중 ≥90%, 스루풋 목표 충족, 10만+ 파일에서 메모리 ≤500MB

**W23-W24 — 통합 테스트 & 버그 수정**

* E2E 테스트 스위트, 성능 벤치마크, 버그 수정
* **DoD**: 모든 기능 통합 테스트 통과, 성능 목표 달성

## 🚀 **Phase 3: 안정화 & 릴리스 (W25-W36)**

**W25-W26 — 사용자 테스트 & 피드백 수집**

* **베타 테스트 계획**:
  * 베타 테스터 규모: 50-100명
  * 모집 채널: Discord/Reddit 애니메이션 커뮤니티, GitHub 이슈
  * 테스트 시나리오: 다양한 파일 구조, 실제 애니메이션 라이브러리
  * 피드백 수집: 설문조사 + 이슈 트래킹
* **DoD**: 베타 테스트 완료, 주요 이슈 목록 정리, 사용자 만족도 ≥80%

**W27-W28 — 사용자 피드백 반영 & 개선**

* 베타 피드백 기반 기능 개선, 버그 수정, UX 개선
* **DoD**: 주요 피드백 반영 완료, 추가 기능 구현

**W29-W30 — 고급 기능 & 최적화**

* **고급 기능 우선순위**:
  1. **배치 처리 최적화** (실용성 높음)
  2. **플러그인 아키텍처** (확장성)
  3. **원격 캐시 동기화** (팀 사용)
* **DoD**: 고급 기능 구현, 성능 추가 최적화

**W31-W32 — 문서화 & 튜토리얼**

* 사용자 매뉴얼, API 문서, 튜토리얼 작성
* **DoD**: 완전한 문서화, 사용자 가이드 완성

**W33-W34 — 최종 테스트 & 품질 보증**

* 전체 시스템 테스트, 보안 검토, 성능 검증
* **DoD**: 모든 테스트 통과, 보안 검토 완료

**W35-W36 — 릴리스 준비 & 배포**

* **단일 exe** 릴리스 빌드, 릴리스 노트, 배포 준비
* **DoD**: v1.0 태그, 클린 Windows에서 exe 1개로 작동 확인, 공식 릴리스

---

# 7) 구현 규약(필수 체크)

* **UTF-8 전역**: 소스/리소스/입출력/로그/JSON 모두 `encoding="utf-8"`
* **JSON 캐시 스키마(요지)**

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
  * `q_norm`: 정규화 알고리즘 적용 결과 (단순화: 소문자화 + 기본 정리 + 연도 힌트)
  * `year_hint`: 파일명에서 추출한 연도 힌트 (선택적)
  * **정규화 예시**: "Attack on Titan (2013) S01E01" → "attack on titan 2013"
* **레이트리밋 준수**

  * **토큰버킷**: 기본 35 rps (TMDB 상한 ~50 rps 대비 안전 마진), CLI 옵션 `--rate`으로 조정
  * **429**: 즉시 `Throttle` 전이 → **`Retry-After` 우선 존중**, **지수 백오프**, 연속 실패 시 `CacheOnly`
  * **회로차단기**: 5분 이상 429/5xx 비율 >60% 시 CacheOnly, 10분 후 반개방
* **스레드 정책**

  * CPU계(파싱)와 I/O계(스캔/네트워크/정리) 분리 튜닝
  * TMDB 호출은 **세마포어**로 동시요청 상한
* **로깅**

  * 파일 분리: `app_info.log`, `app_warn.log`, `app_error.log`, `network.log`, `pipeline.log`
  * `QueueHandler + QueueListener`(비동기), `TimedRotatingFileHandler`(일), 보존 N, **크기 상한**(20MB × N개)
  * **머신리더블 이벤트 라인**(`UTC_ISO8601 LEVEL module:function thread event=... k=v k=v`)
  * **민감정보 마스킹**: TMDB 키, 사용자 홈 경로 prefix

---

# 8) 계약 고정 & 안전 기본값

## A. CLI 계약(Contract) 고정

* **파괴적 변경 금지 원칙**: `anivault.exe run/scan/match/organize/cache/settings/status`의 **옵션/출력 필드**를 v1.0까지 동결
* **머신리더블 출력 표준화**: `--json` 출력은 **JSON Lines (NDJSON)** 로 고정. 각 라인에 `phase`, `event`, `ts`, `fields` 포함
* **에러 코드 테이블**(고정 ID):
  * `E-TMDB-429`, `E-TMDB-KEY`, `E-FS-PERM`, `E-FS-LONGPATH`, `E-CACHE-CORRUPT`, `E-PARSE-FAIL`, `E-ORGANIZE-CONFLICT`, `E-INTERRUPTED`
* **JSON Schema**(배포물 동봉): `schemas/cli_event.schema.json`, `schemas/cache_object.schema.json`, `schemas/plan.schema.json`

## B. 안전 기본값 & Resume 불변성

* **변경 적용은 명시적 플래그**: `organize`와 `run`은 **기본 드라이런**. 실제 변경은 `--apply` 필요
* **계획파일(Plan File)** 지원: `--plan out\plan.json` → 사용자 검토 후 `anivault.exe organize --from-plan out\plan.json --apply`
* **Resume의 진짜 불변성**: 모든 작업 대상에 **Deterministic ID**(파일 경로 상대화 + inode/ctime/hash 혼합) 부여
* **처리순서 고정 + 멱등성**: 같은 입력은 같은 결과

## C. 파일·Windows 특이점 처리

* **Long Path**: Windows 10에서 `\\?\` 프리픽스 자동 사용(경로>260자)
* **예약어/금지문자**: `CON, PRN, AUX, NUL` / `< > : " | ? *` → 자동 치환 규칙(`_` 대체 + 해시 꼬리표)
* **UNC/네트워크 드라이브**: 네트워크 DFS 감지 시 경고 + 속도 저하 안내
* **UAC**: 관리자 필요 작업 없음이 원칙. 권한 오류는 스킵 + 요약 리포트
* **AV 간섭**: 대량 이동 시 **옵션 `--io-pace-limit`** 제공(분당 파일 이동 상한)

## D. 캐시 설계 보강

* **인덱스 파일**: `cache/index.jsonl`(query_hash→파일경로, hit/miss 카운트, 마지막 접근)
* **LRU + TTL** 동시 적용, **디스크 상한**(`--cache-max-bytes`, 기본 512MB)
* **원자성**: `*.json.tmp`로 쓰고 `rename()`으로 커밋
* **부패 복구**: JSON 파싱 실패 시 **격리 폴더**로 이동(`cache/quarantine/…`) 후 재생성
* **스키마 마이그레이션**: `schema_version` 차이 시 **백업 후 마이그레이터** 실행

---

# 9) 테스트/품질 게이트(클린 CLI 기준)

* **계약 테스트**: TMDB 호출은 **스텁/레코더(VCR 유사)** 로 재현성 확보
* **E2E**: `run` 한 줄로 **샘플 폴더→드라이런** 검증
* **벤치**: 스캔/매칭/정리 각 단계 시간/스루풋 메트릭
* **정적 분석**: Ruff/Black/Pyright, 커버리지 ≥70%
* **현실 파괴 테스트**:
  * **파일명 퍼저**: 이모지, 한자, RTL(아랍어), 조합문자(NFC/NFD), 공백·마침표 끝
  * **대용량**: 30만 파일 가상 트리(메모리 ≤ 600MB, 시간 제한)
  * **FS 에러 주입**: 권한거부/락/네트워크 끊김/디스크 Full
  * **리소스 누수**: `tracemalloc`/핸들 카운트, **파일디스크립터 누수** 검출
  * **TMDB 스텁**: 200/404/429/5xx/타임아웃 미믹 + `Retry-After` 변형(초/날짜 형식)
* **시나리오**: 네트워크 다운, 429 폭주, 디스크 꽉참, 권한 오류, 파일명 인코딩 오류, TMDB 키 만료, 사용자 중단(Ctrl+C)
* **에러 핸들링 전략**:
  * 파일 시스템 권한 오류: 건너뛰기 + 로그 기록
  * 불완전한 파일명: UTF-8 복구 시도 → 실패 시 건너뛰기
  * TMDB API 키 만료/쿼터 초과: 자동 CacheOnly 모드 전환
  * 사용자 중단(Ctrl+C): 안전한 종료 + 진행상황 저장
  * 중간 실패: 체크포인트 기반 재시작 지원

---

# 10) 패키징·배포 강화

* **PyInstaller 1순위** 유지. **UPX 미사용**(AV 오탐 증가)
* **SBOM 생성**: `cyclonedx-py`로 SBOM 포함
* **코드서명**(선택): Authenticode 서명 시 SmartScreen 경고 완화
* **릴리스 산출물**: `anivault.exe`, `LICENSES/`(서드파티 라이선스 동봉), `schemas/`, `docs/`, `CHANGELOG.md`, `SHA256SUMS`

---

# 11) 리스크 & 대응 (CLI 맥락)

| 리스크           | 징후                   | 대응                                        |
| ------------- | -------------------- | ----------------------------------------- |
| onefile 번들 실패 | 콘솔 실행 즉시 ImportError | **W2 POC**로 조기 확인, PyInstaller↔Nuitka 스위치 |
| 429 급증/정책 변경  | 매칭 지연 급등, 실패율 증가     | **상태머신 파라미터 설정화**, 핫패치/환경변수로 조정           |
| 로그 I/O 병목     | 디스크 쓰기 대기, 속도 저하     | 비동기 큐잉/버퍼, 로그 레벨 동적 하향                    |
| 캐시 오염/스키마 충돌  | 매칭률 급락               | `schema_version` 엄격, 무효화/TTL·워밍업 루틴       |
| TMDB 데이터 업데이트   | 오래된 정보로 매칭         | TTL 기반 자동 무효화, 수동 갱신 옵션 제공            |
| 손상된 캐시 파일       | JSON 파싱 오류            | 자동 복구 시도, 실패 시 삭제 후 재생성               |
| 캐시 버전 호환성       | schema_version 불일치     | 버전 체크 후 자동 마이그레이션 또는 재생성           |
| tmdbv3api 라이브러리 이슈 | 레이트리밋 미처리, 메모리 누수 | httpx 기반 직접 구현으로 폴백 전환                   |

---

# 12) 즉시 착수 산출물(CLI 전용)

* `tools/bundle_poc/console_onefile.{cmd,py}` — 콘솔 onefile POC (W2)
* `src/cli/main.py` — Click 기반 명령 라우팅(`run/scan/match/organize/cache/settings/status`)
* `src/utils/logging_conf.py` — 멀티 파일·회전·UTF-8 설정
* `src/services/tmdb_client.py` — tmdbv3api 기반 TMDB 클라이언트, 토큰버킷+상태머신/세마포어 포함
* `src/services/tmdb_abstract.py` — TMDB 클라이언트 추상화 레이어 (tmdbv3api ↔ httpx 폴백 전환용)
* `src/cache/json_cache.py` — 키 정규화/TTL/버전/지표
* `bench/bench_scan.py`, `bench/bench_match.py` — CLI 벤치 스크립트
* `docs/policies/rate-limit-state-machine.md` — 429/Throttle/CacheOnly 플로우 설명
* `schemas/` — JSON Schema 파일들 (cli_event, cache_object, plan)
* `data/samples/labeled_dataset.json` — 매칭 정확도 평가용 라벨드 샘플셋 (W4)
* `tests/test_dependencies.py` — anitopy C 확장 호환성 검증 (W1 우선)
* `tests/e2e/test_longpath_and_multiepisode.py` — 긴 경로/멀티에피소드/권한오류 시나리오
* `pyproject.toml` — 핵심 의존성: Click, tmdbv3api, anitopy, rich, cryptography 구성 예시:

```toml
[tool.poetry.dependencies]
python = "^3.9"
click = "^8.1.7"
tmdbv3api = "==1.9.0"        # MIT, 최신 확인됨
anitopy = "^2.1.1"           # MPL-2.0
rich = "^14.1.0"
cryptography = "^41.0.0"
parse = "^1.20.0"
tomli = {version = "^2.0.0", markers = "python_version < '3.11'"}
tomli-w = "^1.0.0"
requests = "^2.32"           # 세션/리트라이 어댑터용(명시)

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-cov = "^4.1.0"
pytest-mock = "^3.11.0"
pytest-httpx = "^0.30.0"     # httpx 스텁 최신 라인
hypothesis = "^6.88.0"
ruff = "^0.6.0"
mypy = "^1.10.0"
pre-commit = "^3.7.0"
pyinstaller = "==6.16.0"     # onefile/console 우선
```

---

# 13) 예시 사용 시나리오

1. **첫 실행**(키 설정 & 드라이런)

```
anivault.exe settings set --tmdb-key %TMDB_KEY%
anivault.exe run --src D:\Anime --dst E:\Vault --dry-run --lang ko-KR --rate 35 --tmdb-concurrency 4
```

2. **계획 파일 생성 및 실행**

```
anivault.exe organize --src D:\Anime --dst E:\Vault --plan out\plan.json
# 사용자가 plan.json 검토 후
anivault.exe organize --from-plan out\plan.json --apply
```

3. **실행 재개(네트워크 이슈 후)**

```
anivault.exe run --resume
```

4. **캐시 관리/통계**

```
anivault.exe cache stats
anivault.exe cache purge --older-than 30d
```

---

## 📊 **36주 개발 로드맵 요약**

### **Phase 1 (W1-W12): 기반 구축**
- 기술 스택 검증 및 안정화
- 핵심 파이프라인 구현
- 기본 기능 프로토타입

### **Phase 2 (W13-W24): 핵심 기능 개발**
- 모든 CLI 명령어 구현
- 통합 테스트 및 성능 최적화
- 안정성 확보

### **Phase 3 (W25-W36): 안정화 & 릴리스**
- 사용자 테스트 및 피드백 반영
- 고급 기능 및 최적화
- 완전한 문서화 및 릴리스

## 🎯 **중간 마일스톤 체크포인트**

* **W12**: MVP 데모 (scan → match → organize 기본 플로우)
* **W24**: 베타 버전 (모든 기능 동작, 안정성 검증)
* **W36**: 정식 릴리스 (v1.0)

## 맺음(다음 확장 포인트)

36주 개발 기간으로 **여유로운 개발 환경**을 확보했습니다. CLI는 뼈대이자 근육이다. 여기서 확보한 **일관 옵션/상태머신/캐시/로그/스레딩**은 이후 GUI를 입혀도 그대로 재사용된다.

**Phase 3에서 추가 가능한 고급 기능들:**
- **네이밍 스키마 v2(규칙 언어화)**
- **머신리더블 리포트(JSON)**
- **대규모 워크로드 벤치 리그**
- **플러그인 아키텍처**
- **원격 캐시 동기화**

[1]: https://developer.themoviedb.org/docs/rate-limiting?utm_source=chatgpt.com "Rate Limiting"
