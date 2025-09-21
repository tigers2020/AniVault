# AniVault 복원력 시스템 사용 가이드

이 문서는 AniVault 애플리케이션의 복원력 시스템 사용법을 설명합니다.

## 개요

AniVault의 복원력 시스템은 데이터베이스 장애 상황에서도 애플리케이션이 안정적으로 동작할 수 있도록 설계되었습니다. 다음과 같은 메커니즘들을 포함합니다:

- **Circuit Breaker**: 데이터베이스 작업을 보호하여 연쇄 장애를 방지
- **Retry Logic**: 일시적 오류에 대한 자동 재시도
- **Health Checks**: 데이터베이스 연결 상태 모니터링
- **Cache-Only Mode**: 데이터베이스 장애 시 캐시 전용 모드로 전환
- **Automatic Recovery**: 데이터베이스 복구 시 자동으로 정상 모드로 전환

## 초기 설정

### 1. 기본 설정

```python
from src.core.database import DatabaseManager
from src.core.metadata_cache import MetadataCache
from src.core.resilience_integration import setup_resilience_system

# 데이터베이스 매니저와 캐시 초기화
db_manager = DatabaseManager("sqlite:///anivault.db")
db_manager.initialize()

metadata_cache = MetadataCache(
    max_size=1000,
    max_memory_mb=100,
    db_manager=db_manager,
    enable_db=True
)

# 복원력 시스템 설정
setup_resilience_system(
    db_manager=db_manager,
    metadata_cache=metadata_cache,
    health_check_interval=30.0,      # 헬스 체크 간격 (초)
    health_check_timeout=5.0,        # 헬스 체크 타임아웃 (초)
    health_failure_threshold=3,      # 실패 임계값
    health_recovery_threshold=2,     # 복구 임계값
    auto_recovery_enabled=True,      # 자동 복구 활성화
    recovery_check_interval=60.0     # 복구 체크 간격 (초)
)
```

### 2. 고급 설정

```python
from src.core.database_health import create_database_health_checker
from src.core.resilience_manager import create_resilience_manager

# 커스텀 헬스 체커 생성
health_checker = create_database_health_checker(
    db_manager=db_manager,
    check_interval=15.0,             # 더 자주 체크
    timeout=3.0,                     # 더 짧은 타임아웃
    failure_threshold=2,             # 더 민감한 실패 감지
    recovery_threshold=1             # 더 빠른 복구
)

# 커스텀 복원력 매니저 생성
resilience_manager = create_resilience_manager(
    metadata_cache=metadata_cache,
    health_checker=health_checker,
    auto_recovery_enabled=True,
    recovery_check_interval=30.0     # 더 자주 복구 체크
)
```

## 사용법

### 1. 일반적인 사용

복원력 시스템이 설정되면, 기존 코드는 변경 없이 자동으로 보호됩니다:

```python
# 데이터베이스 작업은 자동으로 Circuit Breaker로 보호됩니다
anime_metadata = db_manager.create_anime_metadata(tmdb_anime)

# 캐시 작업은 자동으로 데이터베이스 상태에 따라 적응합니다
cached_data = metadata_cache.get("tmdb:123")
metadata_cache.put("tmdb:456", tmdb_anime)
```

### 2. 시스템 상태 확인

```python
from src.core.resilience_integration import get_resilience_status

# 전체 시스템 상태 확인
status = get_resilience_status()
print(f"시스템 운영 상태: {status['is_operational']}")
print(f"캐시 전용 모드: {status['cache_only_mode']}")
print(f"데이터베이스 상태: {status['health_status']}")

if status['cache_only_mode']:
    print(f"캐시 전용 모드 이유: {status['cache_only_reason']}")
```

### 3. 수동 복구 시도

```python
from src.core.resilience_integration import force_recovery_check

# 수동으로 복구 체크 및 시도
recovery_attempted = force_recovery_check()
if recovery_attempted:
    print("복구 시도가 실행되었습니다")
```

### 4. 통계 정보 확인

```python
status = get_resilience_status()

# 헬스 체크 통계
health_stats = status['health_statistics']
print(f"총 헬스 체크: {health_stats['total_checks']}")
print(f"성공률: {health_stats['success_rate']:.2%}")

# Circuit Breaker 상태
print(f"Circuit Breaker 상태: {status['circuit_breaker_state']}")

# 재시도 통계
retry_stats = status['retry_statistics']
print(f"재시도 통계: {retry_stats}")

# 캐시 통계
cache_stats = status['cache_statistics']
print(f"캐시 히트율: {cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses']):.2%}")
```

## 운영 모니터링

### 1. 로그 모니터링

복원력 시스템은 상세한 로그를 제공합니다:

```bash
# 헬스 체크 로그
grep "Database health check" logs/anivault.log

# Circuit Breaker 상태 변경
grep "Circuit breaker" logs/anivault.log

# 캐시 전용 모드 전환
grep "Cache-only mode" logs/anivault.log

# 복구 시도
grep "Recovery" logs/anivault.log
```

### 2. 메트릭 수집

```python
import time
from src.core.resilience_integration import get_resilience_status

def collect_metrics():
    """메트릭 수집 함수"""
    status = get_resilience_status()

    metrics = {
        'timestamp': time.time(),
        'is_operational': status['is_operational'],
        'cache_only_mode': status['cache_only_mode'],
        'health_status': status['health_status'],
        'cache_hit_rate': (
            status['cache_statistics']['hits'] /
            (status['cache_statistics']['hits'] + status['cache_statistics']['misses'])
            if (status['cache_statistics']['hits'] + status['cache_statistics']['misses']) > 0
            else 0
        ),
        'total_failures': status['total_failures'],
        'total_recoveries': status['total_recoveries']
    }

    return metrics

# 주기적으로 메트릭 수집
metrics = collect_metrics()
```

## 장애 시나리오

### 1. 데이터베이스 연결 끊김

```
1. 헬스 체크가 실패를 감지
2. Circuit Breaker가 열림 (OPEN 상태)
3. 캐시 전용 모드로 자동 전환
4. 데이터베이스 작업이 캐시에서만 처리됨
5. 사용자에게 경고 메시지 표시
```

### 2. 데이터베이스 복구

```
1. 헬스 체크가 성공을 감지
2. Circuit Breaker가 반열림 (HALF_OPEN) 상태로 전환
3. 테스트 요청 성공 시 정상 (CLOSED) 상태로 복구
4. 캐시 전용 모드에서 정상 모드로 전환
5. 데이터베이스 동기화 재개
```

### 3. 일시적 네트워크 문제

```
1. 데이터베이스 작업 실패
2. Retry Logic이 지수 백오프로 재시도
3. 일정 횟수 재시도 후 Circuit Breaker 열림
4. 네트워크 복구 시 자동 복구
```

## 설정 튜닝

### 1. 민감도 조정

더 민감한 장애 감지를 원하는 경우:

```python
setup_resilience_system(
    db_manager=db_manager,
    metadata_cache=metadata_cache,
    health_check_interval=10.0,      # 더 자주 체크
    health_failure_threshold=2,      # 더 낮은 임계값
    health_recovery_threshold=1      # 더 빠른 복구
)
```

### 2. 안정성 우선 설정

더 안정적인 동작을 원하는 경우:

```python
setup_resilience_system(
    db_manager=db_manager,
    metadata_cache=metadata_cache,
    health_check_interval=60.0,      # 덜 자주 체크
    health_failure_threshold=5,      # 더 높은 임계값
    health_recovery_threshold=3      # 더 신중한 복구
)
```

## 종료 시 정리

```python
from src.core.resilience_integration import shutdown_resilience_system

# 애플리케이션 종료 시
shutdown_resilience_system()
```

## 주의사항

1. **캐시 전용 모드**: 데이터베이스가 복구될 때까지 새로운 데이터는 캐시에만 저장됩니다.
2. **메모리 사용량**: 캐시 전용 모드에서는 메모리 사용량이 증가할 수 있습니다.
3. **데이터 일관성**: 캐시 전용 모드에서는 최신 데이터가 데이터베이스와 동기화되지 않을 수 있습니다.
4. **복구 시간**: 네트워크 상태에 따라 자동 복구 시간이 달라질 수 있습니다.

## 문제 해결

### 1. 복원력 시스템이 작동하지 않는 경우

```python
# 시스템 상태 확인
status = get_resilience_status()
print("시스템 상태:", status)

# 수동 복구 시도
force_recovery_check()
```

### 2. 캐시 전용 모드에서 벗어나지 못하는 경우

```python
# 데이터베이스 연결 수동 확인
from src.core.database_health import get_database_health_status
print("데이터베이스 상태:", get_database_health_status())

# 수동으로 캐시 전용 모드 비활성화
metadata_cache.disable_cache_only_mode()
```

### 3. 성능 문제가 있는 경우

```python
# 헬스 체크 간격 증가
# Circuit Breaker 설정 조정
# 캐시 크기 최적화
```

이 가이드를 통해 AniVault의 복원력 시스템을 효과적으로 사용할 수 있습니다.
