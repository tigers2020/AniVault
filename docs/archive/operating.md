# AniVault 운영 가이드

## 🚨 장애 조사 가이드

### 로그 위치 및 확인
```bash
# 로그 디렉토리 (기본값)
~/.anivault/logs/

# 로그 파일 확인
tail -f ~/.anivault/logs/anivault.log
grep "ERROR" ~/.anivault/logs/anivault.log
```

### 디버그 모드 활성화
```bash
# 환경변수 설정
export ANIVAULT_DEBUG=true
export ANIVAULT_LOG_LEVEL=DEBUG

# 또는 CLI 옵션 사용
anivault run /path/to/anime --log-level DEBUG --verbose
```

### 일반적인 문제 해결

#### 1. TMDB API 오류
```bash
# API 키 확인
echo $TMDB_API_KEY

# 레이트 리밋 확인
anivault match /path/to/anime --verbose

# 캐시 초기화
rm -rf ~/.anivault/cache/tmdb_cache.sqlite
```

#### 2. 파일 권한 오류
```bash
# 디렉토리 권한 확인
ls -la /path/to/anime

# 실행 권한 부여
chmod +x /path/to/anime
```

#### 3. 캐시 문제
```bash
# 캐시 디렉토리 확인
ls -la ~/.anivault/cache/

# 캐시 초기화
rm -rf ~/.anivault/cache/*
```

## 🔄 롤백 절차

### 1. 작업 로그 확인
```bash
anivault log list
```

### 2. 특정 작업 롤백
```bash
# 타임스탬프로 롤백
anivault rollback 2024-01-15T10:30:00

# 최근 작업 롤백
anivault rollback latest
```

### 3. 수동 롤백 (필요시)
```bash
# 백업 파일 복원
cp ~/.anivault/backups/2024-01-15_10-30-00/* /path/to/anime/
```

## 💾 캐시 관리

### 캐시 설정
```bash
# 환경변수로 캐시 설정
export ANIVAULT_CACHE_TTL_HOURS=48
export ANIVAULT_CACHE_MAX_SIZE_MB=200
export ANIVAULT_CACHE_DIR=/custom/cache/path
```

### 캐시 상태 확인
```bash
# 캐시 크기 확인
du -sh ~/.anivault/cache/

# 캐시 내용 확인
sqlite3 ~/.anivault/cache/tmdb_cache.sqlite ".tables"
sqlite3 ~/.anivault/cache/tmdb_cache.sqlite "SELECT COUNT(*) FROM tmdb_cache;"
```

### 캐시 정리
```bash
# 오래된 캐시 삭제
find ~/.anivault/cache/ -name "*.sqlite" -mtime +7 -delete

# 전체 캐시 초기화
rm -rf ~/.anivault/cache/*
```

## 🌐 TMDB API 레이트 리밋 대응

### 레이트 리밋 설정
```bash
# 환경변수로 레이트 리밋 조정
export TMDB_RATE_LIMIT_PER_WINDOW=20  # 10초당 요청 수
export TMDB_REQUEST_TIMEOUT=60        # 타임아웃 (초)
export TMDB_MAX_RETRIES=5             # 최대 재시도 횟수
```

### 레이트 리밋 모니터링
```bash
# API 호출 로그 모니터링
grep "Rate limit" ~/.anivault/logs/anivault.log

# 재시도 로그 확인
grep "Retrying" ~/.anivault/logs/anivault.log
```

### 오프라인 모드 사용
```bash
# 캐시된 데이터만 사용
anivault match /path/to/anime --offline
```

## 🔒 보안 관리

### API 키 로테이션
```bash
# 1. 새 API 키 발급 (TMDB 웹사이트)
# 2. 환경변수 업데이트
export TMDB_API_KEY=new_api_key_here

# 3. 기존 캐시 유지 (선택사항)
# 또는 캐시 초기화
rm -rf ~/.anivault/cache/tmdb_cache.sqlite
```

### 민감한 데이터 마스킹
```bash
# 로그에서 민감한 데이터 마스킹 활성화
export ANIVAULT_LOG_MASK_SENSITIVE=true

# 로그 파일 확인
grep -v "API_KEY" ~/.anivault/logs/anivault.log
```

## 📊 성능 모니터링

### 메모리 사용량 모니터링
```bash
# 프로세스 모니터링
ps aux | grep anivault

# 메모리 사용량 확인
top -p $(pgrep anivault)
```

### 디스크 사용량 확인
```bash
# 캐시 디스크 사용량
du -sh ~/.anivault/

# 로그 디스크 사용량
du -sh ~/.anivault/logs/
```

## 🛠️ 유지보수 작업

### 정기적인 정리 작업
```bash
#!/bin/bash
# 주간 정리 스크립트

# 1. 오래된 로그 파일 삭제 (30일 이상)
find ~/.anivault/logs/ -name "*.log.*" -mtime +30 -delete

# 2. 캐시 크기 확인 및 정리
CACHE_SIZE=$(du -sm ~/.anivault/cache/ | cut -f1)
if [ $CACHE_SIZE -gt 500 ]; then
    echo "Cache size too large: ${CACHE_SIZE}MB"
    rm -rf ~/.anivault/cache/*.sqlite-wal
    rm -rf ~/.anivault/cache/*.sqlite-shm
fi

# 3. 백업 파일 정리 (90일 이상)
find ~/.anivault/backups/ -type f -mtime +90 -delete
```

### 백업 전략
```bash
# 중요한 설정 백업
tar -czf anivault-config-backup-$(date +%Y%m%d).tar.gz \
    ~/.anivault/config/ \
    ~/.env

# 캐시 백업 (선택사항)
tar -czf anivault-cache-backup-$(date +%Y%m%d).tar.gz \
    ~/.anivault/cache/
```

## 🚀 성능 최적화

### 병렬 처리 설정
```bash
# 워커 수 조정 (CPU 코어 수에 맞게)
export ANIVAULT_MAX_WORKERS=8

# 배치 크기 조정
export ANIVAULT_BATCH_SIZE=50
```

### SQLite 최적화
```bash
# WAL 모드 활성화
export ANIVAULT_CACHE_WAL_MODE=true

# 페이지 크기 최적화
sqlite3 ~/.anivault/cache/tmdb_cache.sqlite "PRAGMA page_size = 4096;"
```

## 📞 지원 및 에스컬레이션

### 로그 수집
```bash
# 문제 발생 시 로그 수집
mkdir anivault-debug-$(date +%Y%m%d-%H%M%S)
cd anivault-debug-*

# 시스템 정보 수집
uname -a > system-info.txt
python --version >> system-info.txt

# 로그 파일 복사
cp ~/.anivault/logs/*.log .

# 설정 파일 복사
cp ~/.anivault/config/* .

# 캐시 상태 확인
sqlite3 ~/.anivault/cache/tmdb_cache.sqlite ".schema" > cache-schema.txt
```

### 에스컬레이션 체크리스트
- [ ] 로그 파일 수집 완료
- [ ] 환경변수 설정 확인
- [ ] 네트워크 연결 상태 확인
- [ ] 디스크 공간 확인
- [ ] 권한 문제 확인
- [ ] API 키 유효성 확인
