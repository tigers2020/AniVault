# TMDB Rate Limit State Machine (보강·정리·가지치기 버전)

## 0) Tree of Thought 협업 진행 (요약)

* **전문가 A·제품기획**: "상태 수를 과도하게 늘리진 말되, **플래핑 방지**와 **운영 가시성**을 보강하자."
* **전문가 B·아키텍트**: "**연속 횟수**만으로 전이하지 말고 **슬라이딩 윈도 에러비율** + **회로차단기(HalfOpen)** 를 추가하자. **전역(프로세스/멀티프로세스) 토큰버킷** 명확화."
* **전문가 C·QA/DevOps**: "테스트는 **Retry-After 파싱·시계스큐**, **Full Jitter 백오프**, **429/5xx/네트워크오류** 분리 검증. **메트릭/로그 키** 표준화."

**합의**: **상태 4개( Normal / Throttle / Sleep / CacheOnly ) + HalfOpen(회복탐색)**, **슬라이딩 윈도 에러비율 도입**, **전역 토큰버킷**, **관측성 스펙** 추가.

## 개요

AniVault CLI는 TMDB API의 레이트리밋을 준수하기 위해 **탄력적 상태머신** 기반의 레이트리밋 처리를 구현합니다. **에러비율+회로차단** 기반으로 폭주 방지/회복 속도/현장 가시성을 모두 개선했습니다.

## 1) 상태 정의 (개선판)

### Normal
- **설명**: 정상적인 API 호출 상태
- **토큰버킷**: `rate_base`(기본 35 rps), `capacity = rate_base`
- **동시성**: `sem_base`(기본 4)
- **전이 트리거**:
  * **429/5xx 비율** ≥ `p_throttle` (기본 20%) in **최근 30초/최근 300건** 중 작은 쪽 기준
  * 또는 **연속 429** ≥ `N_throttle` (기본 3)
    → **Throttle**

### Throttle
- **설명**: 429 에러 발생 후 제한 모드
- **속도**: `rate = max(5, floor(rate_base * 0.5))`
- **동시성**: `sem = max(1, floor(sem_base * 0.5))`
- **전이**:
  * **성공 응답 누적** `S_recover`(기본 10) AND **429/5xx 비율** < `p_recover`(기본 10%) → **HalfOpen**
  * **연속 429** ≥ `N_cacheonly`(기본 5) 또는 **에러비율** ≥ 60% for 5분 → **Sleep**

### Sleep
- **설명**: **API 호출 전면 일시정지**(TMDB가 `Retry-After` 시각을 주거나, 고오류 구간을 지나는 동안)
- **행동**:
  * **모든 호출 차단**, `sleep_until = now + max(retry_after, backoff_ceiling)`
  * 타이머 만료 시 → **HalfOpen**
- **전이 트리거**:
  * **수동 강제** `--offline`도 Sleep로 맵핑(ETA 0)

### HalfOpen (회로차단기 "반개방")
- **설명**: **탐색적 소량 호출**로 회복 여부 점검
- **행동**: `probe_concurrency = 1`, `probe_rate = min(3 rps, rate)`
- **전이**:
  * **성공** `S_probe_ok`(기본 5) & **에러비율** < 10% → **Normal**
  * **429/5xx** 재발 → **Sleep** (쿨다운 증가, 예: 2×)

### CacheOnly
- **설명**: **API 완전 차단**, 캐시만 사용
- **진입**:
  * 운영자가 강제 지정 또는 **지속적 고오류**로 운영 정책상 차단
- **복구**:
  * 기본은 **수동**이나, 옵션 `--auto-recover=<분>` 설정 시 **Sleep → HalfOpen → Normal** 자동 시도

> **플래핑 방지(Hysteresis)**: 상태 이동은 **동일 조건 2회 연속 만족** 시 확정.

## 2) 429/5xx/네트워크 오류 처리 규칙 (정교화)

### 1. Retry-After 우선 존중
- 초 단위와 날짜 형식 모두 지원
- **시계 스큐 보정**: 음수/과거는 `min_sleep = 1.0s`로 대체

```python
if retry_after:
    if retry_after.isdigit():
        sleep_sec = float(retry_after)
    else:
        dt = parsedate_to_datetime(retry_after)
        sleep_sec = max(0.0, (dt - datetime.utcnow()).total_seconds())

    # 시계 스큐 보정
    sleep_sec = max(1.0, sleep_sec)
```

### 2. 백오프 전략 (Full Jitter 권장)
```python
base = min(30.0, 1.5 * (2 ** (retries-1)))
sleep_sec = random.uniform(0, base)   # Full Jitter
```

### 3. 오류 분류
- **백오프 대상**: `429`, `5xx`, `ConnectTimeout`, `ReadTimeout`, `DNS/ConnectionError`
- **백오프 비대상**: `4xx` 중 `401/403/404/422` 등 **클라이언트 책임**(키/권한/리소스없음/유효하지 않은 요청) → 즉시 실패/로깅, 상태 전이에 **영향 없음**

### 4. 슬라이딩 윈도 에러비율 계산
- 윈도우: **최근 30초 또는 최근 300건 중 작은 쪽**
- 메트릭: `count_2xx, count_429, count_5xx, count_other`
- 비율: `(429 + 5xx + net_errors) / total`

## 3) 토큰버킷 & 동시성(프로세스/멀티프로세스)

### 기본 설정
- **기본 속도**: 35 rps (TMDB 상한 ~50 rps 대비 안전 마진)
- **용량**: 속도와 동일 (35 토큰)
- **동시성**: 4개 요청

### 프로세스/멀티프로세스 처리
- **프로세스 전역** 단일 버킷(스레드 세이프)
- **멀티프로세스 실행**(사용자가 여러 CLI를 병렬로 돌릴 수 있음) 시 선택사항:
  * **파일락 기반 공유 버킷**(예: `%ProgramData%/AniVault/ratelimit.lock` + mmap/csv)
  * 또는 **"프로세스당 rate_cap = floor(rate_base / N)"**를 문서화

## 4) 운영 중 핫패치 변수(확장)

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

## 5) 복구 로직(개선)

### Normal 복귀 조건
- **Throttle → HalfOpen**: 성공 `S_recover`(10) & 에러비율<10%
- **HalfOpen → Normal**: `S_probe_ok`(5) 성공시, 이후 **속도 램핑**:
  * 5분마다 `rate = min(rate_base, rate * 1.1)`
- **CacheOnly**: 기본 수동. `--auto-recover=15m` 설정 시 **15분 주기**로 `Sleep→HalfOpen` 시도

## 6) 관측성(Observability) 스펙

### 로그 키 표준
```
ts=UTC_ISO lvl=INFO comp=ratelimiter state=Throttle
event=429 sleep=1.8s consec429=3 err_rate_30s=0.24 rate=18rps sem=2
```

- 필수 키: `state, event, sleep, consec429, err_rate_30s, rate, sem, retry_after`
- 전이 로그:
```
ts=... lvl=INFO comp=ratelimiter event=state_transition from=Throttle to=HalfOpen reason=success_window_ok
```

### 메트릭(파일 or stdout NDJSON)
- 카운터: `requests_total{code}`, `cache_hits_total`, `cache_miss_total`
- 게이지: `rate_current`, `concurrency_current`, `err_rate_30s`
- 히스토그램: `latency_ms`, `sleep_ms`

## 7) 테스트 시나리오(보강)

### 1. Retry-After(초/HTTP-date) + 시계스큐
- 과거시각, 미래시각, 잘못된 포맷
- `Retry-After: 2` 헤더 포함 → 2초 대기 후 성공 응답 확인

### 2. Full Jitter 검증
- 평균·표준편차 범위 내 수렴

### 3. 슬라이딩 윈도
- 총 50건 중 11건 오류(22%) → Throttle 진입 확인

### 4. HalfOpen 프로빙
- `5/5` 성공 → Normal 복귀
- `1/3` 실패 → Sleep 재진입

### 5. 네트워크 오류 분리
- DNS/ConnectTimeout 비율 상승 → Throttle 진입
- 404는 비대상

### 6. 멀티프로세스
- 두 개 CLI 동시 실행 → rate 분배 문서대로 수렴

### 7. 장시간 테스트(>3h)
- 메모리/핸들 누수 0, 로그 용량 상한 준수

## 8) 코드 스케치(요지)

```python
class RateLimiter:
    def __init__(self, rate_base=35.0, capacity=35, sem_base=4):
        self.state = "Normal"     # Normal|Throttle|Sleep|HalfOpen|CacheOnly
        self.bucket = TokenBucket(rate_base, capacity)
        self.sem = Semaphore(sem_base)
        self.win = SlidingWindow(max_age=30.0, max_count=300)

    def before_request(self):
        if self.state in ("Sleep", "CacheOnly"):
            raise RateLimitBlocked(self.state)
        self.bucket.consume(1)       # blocks until token available
        if self.state == "HalfOpen":
            self.sem = Semaphore(1)
            self.bucket.set_rate(min(3.0, self.bucket.rate))

    def after_response(self, resp_or_exc):
        code, retry_after = classify(resp_or_exc)
        self.win.add(code)

        if is_backoff_target(code):
            sleep = compute_retry_after_or_jitter(retry_after, self.win.consec_429)
            time.sleep(sleep)

        self._maybe_transition(code)

    def _maybe_transition(self, code):
        err_ratio = self.win.error_ratio()
        # ... 전이 규칙 구현 (상술한 임계값/히스테리시스 적용)
```

## 9) ASCII 상태도

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

## 10) 가지치기(삭제/수정 권고)

- **"연속 3회/5회"만으로 전이** → **보조 기준**으로 내리고, **슬라이딩 윈도 에러비율**을 **주 기준**으로 승격
- **CacheOnly는 수동 복구만** → 기본 수동 유지하되, **옵션 `--auto-recover`** 추가
- **상태 3개(Normal/Throttle/CacheOnly)만** → **Sleep/HalfOpen** 추가로 플래핑/회복성 개선
- 문서 상 **"~50 rps"는 커뮤니티 관찰치**로 남기되, 전술 파라미터는 **운영변수(ENV/CLI)** 로만 노출

## 참고사항

- TMDB는 2019.12 이후 레거시 10초/40요청 제한 비활성화
- 현재 정책: 429 존중, ~50 rps 가이드라인 (커뮤니티 관찰치)
- 정책 변동 가능성에 대비한 유연한 파라미터 설계

### 한 줄 결론

**연속오류** 중심의 단순 FSM에서 **에러비율+회로차단** 기반의 **탄력적 FSM**으로 업데이트하자. 이렇게 하면 **폭주 방지/회복 속도/현장 가시성**이 모두 올라간다.
