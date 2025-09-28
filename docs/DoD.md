# Definition of Done (DoD) - AniVault v3 CLI

## Overview
이 문서는 AniVault v3 CLI 개발에서 "완료(Done)"의 기준을 정의합니다. **단일 실행파일(.exe) 1개**의 **CLI 앱** v1.0을 목표로 하며, 모든 개발 작업은 다음 기준을 만족해야 합니다.

### 핵심 원칙
- **계약 고정**: 파괴적 변경 금지, 머신리더블 출력 표준화
- **안전 기본값**: 드라이런 기본, 명시적 플래그 필요
- **현장 장애 포인트 선제차단**: Windows 특이점, 네트워크 문제 대응

## 일반적인 완료 기준

### 1. 기능 요구사항 충족
- [ ] **CLI 명령어 완성**: `run/scan/match/organize/cache/settings/status` 모든 명령 구현
- [ ] **계약 고정 준수**: 옵션/출력 필드가 v1.0까지 동결됨
- [ ] **머신리더블 출력**: `--json` 출력이 JSON Lines (NDJSON) 형식으로 표준화됨
- [ ] **종료 코드 테이블 고정**: `0=성공`, `10=부분성공(스킵/권한 등)`, `1=치명적실패`, `2=TMDB키없음/잘못됨`, `3=계약위반(JSON 스키마 불일치)`, `4=권한오류(대량)`, `5=디스크Full`, `6=계획충돌`, `7=캐시오염`
- [ ] **NDJSON 스키마 CI 검증**: `tools/validate_ndjson.py`로 `--json` 출력이 `schemas/cli_event.schema.json`에 **100% 일치**해야 통과
- [ ] **계약 위반 탐지의 '하드 실패'**: `--json` NDJSON 이벤트의 **필수 키 누락/타입 불일치**는 **종료코드=3**로 즉시 종료(부분성공 처리 금지)
- [ ] **Plan 파일 DoD**: `--plan` 생성은 **임시파일→fsync→원자적 rename** 절차 필수, `--from-plan --apply` 시 **사전 Dry-Run diff** 출력(적용 건수/충돌 건수/스킵 사유 요약), `schemas/plan.schema.json` 준수 실패 시 **종료코드=3**로 즉시 종료
- [ ] **JSON 캐시**: 모든 캐시 관련 언급은 **JSON 캐시**로 명확히 표기

### 2. 코드 품질
- [ ] **코딩 표준 준수**
  - [ ] Ruff 린터 통과 (Black 대체)
  - [ ] 타입 힌트 적용 (mypy 통과)
  - [ ] Google/NumPy 스타일 docstring 작성
  - [ ] UTF-8 전역 인코딩 준수
- [ ] **함수 설계**
  - [ ] 함수 길이 50라인 이하
  - [ ] 단일 책임 원칙 준수
  - [ ] 입력 검증 로직 구현 (경계값 처리)
  - [ ] 적절한 예외 처리 (구체적 예외 타입)
- [ ] **CLI 아키텍처 원칙**
  - [ ] Click 기반 명령 구조
  - [ ] 서비스 계층 분리 (TMDB, 캐시, 로깅)
  - [ ] 의존성 주입 적용
  - [ ] 계층 간 느슨한 결합

### 3. 테스트 커버리지
- [ ] **단위 테스트**
  - [ ] 핵심 비즈니스 로직 100% 커버리지
  - [ ] pytest 통과
  - [ ] 모킹을 통한 외부 의존성 격리 (TMDB API, 파일 시스템)
  - [ ] 경계값 및 예외 케이스 테스트
- [ ] **통합 테스트**
  - [ ] 컴포넌트 간 상호작용 테스트
  - [ ] TMDB API 연동 테스트 (429 시나리오 포함)
  - [ ] 캐시 시스템 연동 테스트
- [ ] **CLI 테스트**
  - [ ] Click 명령어 테스트
  - [ ] JSON 출력 형식 검증
  - [ ] 에러 코드 응답 테스트
- [ ] **현실 파괴 테스트**
  - [ ] **파일명 퍼저**: 이모지/한자/RTL/NFC/NFD/말미 공백·점
  - [ ] **FS 에러 주입**: 권한거부·락·디스크 Full·경로 너무 김
- [ ] **캐시 부패/마이그레이션**: 손상 JSON → `cache/quarantine/` 격리 후 자동 복구, `schema_version` 상향 마이그레이터 테스트
- [ ] **캐시 용량 상한 & 누수 방지**: `--cache-max-bytes` 기본 512MB, 초과 시 **LRU+TTL 우선 삭제** DoD, 손상 캐시 파일 자동 격리 후 재생성 **테스트 케이스** 포함
- [ ] **장시간(>3h) 스트레스**: 메모리/핸들 누수 0
- [ ] **NDJSON 스키마 회귀**: 샘플 로그/메트릭을 스키마로 검증
- [ ] **NDJSON 부분쓰기/깨짐 라인 복구** 테스트
- [ ] **로그 로테이션 상한 초과** 시 파일 삭제 동작 검증
- [ ] **성능 테스트**
  - [ ] 벤치마크 스크립트 실행
  - [ ] **스캔**: **최소** 60k 경로/분(P95) / **목표** 120k 경로/분(P95)
  - [ ] **메모리**: 300k 파일 시 **≤600MB**(최소) / **≤500MB**(목표)
  - [ ] **로그 off / info / debug** 3단계에서 처리율 차이 측정(오버헤드 ≤ 5%)
  - [ ] **토큰버킷 테스트**
    - [ ] 속도 제한 정확성 검증
    - [ ] 동시성 제어 테스트
    - [ ] 멀티프로세스 안전성 테스트
  - [ ] **TMDB API 테스트**
    - [ ] Retry-After 헤더 파싱 (초/HTTP-date)
    - [ ] 지수 백오프 로직 검증
    - [ ] 429 시나리오 자동 회복 테스트
    - [ ] **TMDB 스텁·VCR 기본 정책**: **네트워크 없는 테스트가 기본**, TMDB 통합 테스트는 VCR 카세트 또는 로컬 스텁 전용 조합만 사용, CI에서 외부 네트워크 시도는 실패로 간주

### 4. 문서화
- [ ] **코드 문서화**
  - [ ] 모든 public 함수/클래스에 docstring
  - [ ] 복잡한 로직에 인라인 주석
  - [ ] 타입 힌트로 인터페이스 명확화
- [ ] **CLI 문서화**
  - [ ] 명령어 도움말 및 예시
  - [ ] `--version`, `status --diag` 사용법과 출력 샘플 문서화
  - [ ] 사용자 가이드 업데이트
  - [ ] 개발자 가이드 작성
- [ ] **아키텍처 문서**
  - [ ] ADR 업데이트 (필요시)
  - [ ] 설계 문서 동기화
  - [ ] JSON Schema 문서화

### 5. 성능 및 품질
- [ ] **성능 기준 (최소/목표 이원화)**
  - [ ] **스캔**: **최소** 60k 경로/분(P95) / **목표** 120k 경로/분(P95)
  - [ ] **메모리**: 300k 파일 시 **≤600MB**(최소) / **≤500MB**(목표)
  - [ ] **로그 I/O 오버헤드**: 처리율 저하 **≤5%**(최대)
  - [ ] 파싱 실패율 ≤ 3%
  - [ ] TMDB 매칭 정확도 @1 ≥ 90%, @3 ≥ 96%
  - [ ] 2회차 JSON 캐시 적중률 ≥ 90%
  - [ ] Rate Limiter: 35 rps 기본 속도 달성
- [ ] **안전 기본값·멱등성**
  - [ ] **파괴적 작업 보호 레일**: `run/organize`는 **기본 드라이런**, 변경에는 `--apply` 필수
  - [ ] **롤백 로그**: 실제 이동이 발생한 모든 작업에 `rollback.jsonl` 생성(경로 전/후, 타임스탬프, 해시)
  - [ ] **Resume 멱등성**: 체크포인트 + **Deterministic ID**(상대경로+stat+해시)로 재시작 시 중복처리 0
- [ ] **안정성**
  - [ ] 메모리 누수 없음
  - [ ] 예외 상황 복구 가능
  - [ ] 장시간 실행 안정성 검증 (>3h 스트레스 테스트)
  - [ ] Resume 재시작 시 중복 처리 없음
- [ ] **보안**
  - [ ] 입력 데이터 검증
  - [ ] 파일 시스템 접근 권한 검사
  - [ ] TMDB API 키 보안 처리
  - [ ] **민감정보 마스킹**: TMDB 키·사용자 홈경로
  - [ ] **Secrets/라이선스/취약점 스캔** CI 게이트: `gitleaks` 또는 `trufflehog`, `pip-audit`(또는 Safety), `pip-licenses` 결과를 릴리스에 포함
  - [ ] **QueueHandler + TimedRotating**(일 단위, **크기 상한** 병행) 로깅
- [ ] **로그 로테이션 상한 2중화**: **시간기반 + 크기기반 동시 상한**(예: 일 단위 + 파일당 20MB × N개), 상한 초과 시 **가장 오래된 파일 삭제**가 동작하는지 테스트 케이스 포함
- [ ] **NDJSON/메트릭 파일 무결성**: 각 라인 끝 **LF 보장**, 깨진 라인(부분 쓰기) 검출 시 자동 격리(`logs/quarantine/…`) + 다음 라인부터 복구

### 6. 빌드 및 배포
- [ ] **빌드 검증**
  - [ ] CI/CD 파이프라인 통과
  - [ ] **Windows 10/11 한정** 빌드 성공
  - [ ] 의존성 버전 호환성 확인
- [ ] **단일 실행파일 패키징**
  - [ ] **PyInstaller --onefile --console** 빌드 성공
  - [ ] **클린 Windows 10/11** VM에서 실행 OK
  - [ ] anitopy, cryptography 네이티브 모듈 번들링 검증
  - [ ] **앱 매니페스트**에 `longPathAware=true` 포함, CI에서 서명/매니페스트 검사 스텝 통과
  - [ ] **SmartScreen/AV** 오탐 점검(화이트리스트 지침 문서화)
  - [ ] **재현가능 빌드** 문서화(파이썬/의존성 핀, 빌드 환경 고정, 해시 공개)
  - [ ] UPX 미사용 (AV 오탐 회피)
- [ ] **배포 준비**
  - [ ] **SBOM(CycloneDX)** 동봉
  - [ ] 코드서명 (선택사항)
  - [ ] 릴리스 산출물: `anivault.exe`, `LICENSES/`, `schemas/`, `docs/`, `CHANGELOG.md`, `SBOM.json`, `THIRD_PARTY_LICENSES.json`, `SHA256SUMS`
  - [ ] **보안 릴리스 산출물**: `THIRD_PARTY_LICENSES.json`과 **SBOM 해시**를 릴리스 아티팩트에 포함
  - [ ] **SmartScreen/AV 가이드**: 릴리스 노트에 **서명/미서명별 SmartScreen 대응**, AV 오탐 시 **제외 경로 가이드**(logs/cache만 예외) 고정 문구 추가
  - [ ] 릴리스 노트 작성
  - [ ] 버전 태그 생성

### 7. 코드 리뷰
- [ ] **리뷰 완료**
  - [ ] 최소 1명의 동료 리뷰 완료
  - [ ] 리뷰 피드백 반영
  - [ ] 보안 취약점 검사 통과
- [ ] **승인**
  - [ ] 기술 리드 승인
  - [ ] 아키텍처 원칙 준수 확인
  - [ ] 성능 기준 달성 확인

## 기능별 완료 기준

### CLI 명령어 기능
- [ ] **run**: 스캔→파싱→매칭→정리 전체 플로우
- [ ] **scan**: 대상 파일 나열 (확장자 필터, 동시성)
- [ ] **match**: 캐시 우선→TMDB 검색/상세 조회→캐시 적재
- [ ] **organize**: 네이밍 스키마 적용, 이동/복사, 충돌 규칙 (기본 드라이런)
- [ ] **cache**: 조회/삭제/워밍업/적중률 통계
- [ ] **settings**: TMDB 키 세팅, 기본 파라미터 보기/변경
- [ ] **status**: 마지막 작업 스냅샷/메트릭 출력
- [ ] **버전/빌드 가시성 명령**: `anivault.exe --version` 출력에 **app 버전, git commit, 빌드UTC, PyInstaller 버전, Python 런타임** 포함
- [ ] **진단 덤프 명령**: `anivault.exe status --diag`가 **환경 요약(경로 권한, long-path 지원, 캐시 용량, 로그 폴더, 설정오버라이드)**을 NDJSON으로 덤프

### 파일 스캐닝 기능
- [ ] 재귀적 디렉토리 탐색 (`os.scandir`, `iterdir`)
- [ ] 파일 메타데이터 추출
- [ ] 확장자 화이트리스트 필터링
- [ ] 진행률 표시 (Rich Progress)
- [ ] 중단/재개 기능 (Resume)
- [ ] **테스트 재현성**: 퍼저/샘플링/백오프 Jitter에 **RNG seed 고정** 옵션(`ANIVAULT_TEST_SEED`) 제공, CI는 항상 고정 seed로 실행(재현 가능한 실패 보장)

### 메타데이터 매칭 기능
- [ ] anitopy 파싱 + 폴백 파서
- [ ] TMDB API 연동 (레이트리밋 준수)
- [ ] 쿼리 정규화 알고리즘
- [ ] 매칭 결과 검증
- [ ] 멀티에피소드/스페셜 처리

### 캐싱 시스템
- [ ] **JSON 캐시** 기반 영구 캐시 (TTL, 스키마 버전)
- [ ] 인덱스 파일 (`cache/index.jsonl`)
- [ ] LRU + TTL 동시 적용
- [ ] **캐시 부패/마이그레이션**: 손상 JSON → `cache/quarantine/` 격리 후 자동 복구, `schema_version` 상향 마이그레이터 테스트
- [ ] 스키마 마이그레이션

### Windows 특이점 처리
- [ ] **Long Path** 자동 처리(`\\?\`), 260자 초과 케이스 테스트
- [ ] **예약어/금지문자 치환 규칙** 문서화 및 테스트(CON/PRN/NUL, `< > : " | ? *`)
- [ ] **UNC/네트워크 드라이브** 감지 시 경고 및 스루풋 저하 안내
- [ ] **I/O 페이싱 옵션**: `--io-pace-limit`로 HDD/AV 간섭 완화
- [ ] UAC 권한 처리

### Rate Limiting 시스템 (FSM DoD)
- [ ] **상태 5종 구현**: `Normal / Throttle / Sleep / HalfOpen / CacheOnly` + **히스테리시스**(동일조건 2회 연속 시 전이 확정)
- [ ] **슬라이딩 윈도 에러비율**: 최근 30초(또는 최근 300건) 에러비율 기준을 전이 판단에 사용
- [ ] **Retry-After(초/HTTP-date)** 우선 + **시계 스큐 보정**(음수→최소 1s)
- [ ] **Full Jitter 백오프**: 최대 30s
- [ ] **멀티프로세스 지침** 명시: 공유 토큰버킷(파일락) **또는** 프로세스별 `rate_cap=floor(rate_base/N)` 문서화
- [ ] **로그 키 표준**(키=값): `state,event,sleep,consec429,err_rate_30s,rate,sem,retry_after` 필수
- [ ] **메트릭 파일(NDJSON)**: `requests_total{code}`, `cache_hits/miss`, `err_rate_30s`, `latency_ms` 기록
- [ ] **토큰버킷 구현**
  - [ ] 기본 35 rps 속도 제한
  - [ ] 동시성 세마포어 (기본 4)
  - [ ] 멀티프로세스 안전성

## 품질 게이트

### 코드 품질 게이트
```bash
# 모든 명령이 성공해야 함
ruff check src/ tests/
mypy src/
pytest --cov=src --cov-fail-under=70
```

### 성능 게이트
```bash
# 벤치마크 실행
python bench/bench_scan.py --file-count=300000
python bench/bench_match.py --file-count=300000

# 성능 기준 확인 (최소/목표 이원화)
# - 스캔: 최소 60k 경로/분(P95) / 목표 120k 경로/분(P95)
# - 메모리: 300k 파일 시 ≤600MB(최소) / ≤500MB(목표)
# - 로그 I/O 오버헤드: 처리율 저하 ≤5%(최대)
# - 파싱 실패율 ≤ 3%
# - TMDB 매칭 정확도 @1 ≥ 90%, @3 ≥ 96%
# - 2회차 JSON 캐시 적중률 ≥ 90%
```

### CLI 특화 게이트
```bash
# CLI 명령어 테스트
python tests/test_cli_commands.py --test-all-commands

# 테스트 시나리오 확인
# - JSON 출력 형식 검증
# - 에러 코드 응답 테스트
# - 계약 고정 준수 확인
```

### 보안 게이트
```bash
# 보안 검사
bandit -r src/
safety check

# 민감정보 마스킹 확인
python tests/test_logging_security.py
```

### 계약/스키마 검증
```bash
python tools/validate_ndjson.py \
  --schema schemas/cli_event.schema.json \
  artifacts/pipeline.ndjson
```

### 보안/공급망
```bash
gitleaks detect --no-banner
pip-audit -r requirements.txt
pip-licenses --format=json --output-file dist/THIRD_PARTY_LICENSES.json
# SBOM 무결성
sha256sum dist/SBOM.json > dist/SBOM.json.sha256
```

### 레이트리밋 E2E
```bash
pytest tests/ratelimit \
  -k "retry_after_httpdate or jitter_backoff or sliding_window or halfopen_probe"
```

## 예외 상황

### 긴급 수정 (Hotfix)
- [ ] 최소한의 테스트 커버리지 (핵심 기능만)
- [ ] 빠른 코드 리뷰 (1명)
- [ ] 사후 포괄적 테스트 추가
- [ ] 보안 검사 우선 실행

### 실험적 기능 (Experimental)
- [ ] 기능 플래그로 제어
- [ ] 사용자 피드백 수집
- [ ] 성능 모니터링 강화
- [ ] 롤백 계획 수립

## 검증 체크리스트

### 개발자 자체 검증
- [ ] 로컬에서 모든 테스트 통과
- [ ] 성능 벤치마크 실행
- [ ] 메모리 누수 검사
- [ ] 사용자 시나리오 테스트
- [ ] **Rate Limiting 검증**
  - [ ] 상태머신 전이 로직 수동 테스트
  - [ ] 토큰버킷 속도 제한 검증
  - [ ] 429 에러 시나리오 테스트
  - [ ] 멀티프로세스 환경에서 동작 확인
  - [ ] 로그 및 메트릭 출력 검증

### QA 검증
- [ ] 수동 테스트 실행
- [ ] 다양한 환경에서 테스트
- [ ] 사용자 경험 검증
- [ ] 성능 기준 달성 확인

### 프로덕션 배포 전
- [ ] 스테이징 환경 테스트
- [ ] 백업 및 롤백 계획 수립
- [ ] 모니터링 설정
- [ ] 사용자 통지 준비

## 지속적 개선

### DoD 개선 프로세스
1. **정기 리뷰**: 분기별 DoD 기준 검토
2. **피드백 수집**: 개발팀 및 QA팀 피드백
3. **기준 업데이트**: 새로운 요구사항 반영
4. **도구 개선**: 자동화 도구 및 스크립트 개선

### 품질 지표 모니터링
- [ ] 코드 커버리지 추이
- [ ] 버그 발견율 및 해결 시간
- [ ] 성능 지표 변화
- [ ] 사용자 만족도
- [ ] **Rate Limiting 품질 지표**
  - [ ] 상태 전이 빈도 및 패턴
  - [ ] 429 에러 발생률 및 복구 시간
  - [ ] 토큰버킷 효율성 (사용률 vs 제한률)
  - [ ] 멀티프로세스 환경에서의 안정성
  - [ ] 로그 및 메트릭 수집 품질

---

---

## Rate Limiting 시스템 참고사항

### 환경변수 설정
```bash
# 속도/용량/세마포어
ANIVAULT_RATE_BASE=35.0
ANIVAULT_BUCKET_CAP=35
ANIVAULT_CONCURRENCY=4

# 전이 임계값
ANIVAULT_P_THROTTLE=0.20
ANIVAULT_P_RECOVER=0.10
ANIVAULT_N_THROTTLE=3
ANIVAULT_N_CACHEONLY=5

# Sleep/Probe
ANIVAULT_SLEEP_MIN=2.0
ANIVAULT_SLEEP_MAX=300.0
ANIVAULT_PROBE_SUCCESS=5

# 회로차단 쿨다운 배수
ANIVAULT_COOLDOWN_FACTOR=2.0
```

### 로그 형식 예시
```
ts=2024-01-01T12:00:00Z lvl=INFO comp=ratelimiter state=Throttle
event=429 sleep=1.8s consec429=3 err_rate_30s=0.24 rate=18rps sem=2 retry_after=1.5s
```

### 상태 전이 다이어그램
```
   +---------+          +-----------+           +---------+
   | Normal  | --(err)->| Throttle  |--(cool)-> |HalfOpen |
   +----+----+          +-----+-----+           +----+----+
        ^                     |                      |
        |     (5xx/429↑)     |(429 폭주/5m>60%)     |(probe ok)
        |                     v                      |
        |                +----+----+                 |
        +-----------------|  Sleep  |<--(probe fail)-+
                         +----+----+
                              |
                              v
                        +-----+------+
                        | CacheOnly  |
                        +------------+
```

---

**마지막 업데이트**: 2025-01-27 (배포 기준일과 동일한 UTC 날짜)
**버전**: 1.2
**승인자**: 기술 리드
**변경사항**: CLI 계약 고정, 레이트리밋 FSM, 보안/공급망 검증 강화
