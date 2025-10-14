# TMDB API 설정 가이드

## 📋 개요

AniVault는 The Movie Database (TMDB) API를 사용하여 애니메이션 메타데이터를 자동으로 수집합니다. 이 가이드는 TMDB API 키 설정부터 최적화까지 모든 것을 다룹니다.

## 🔑 API 키 발급

### 1. TMDB 계정 생성
1. [TMDB 웹사이트](https://www.themoviedb.org/) 방문
2. "Sign Up" 클릭하여 계정 생성
3. 이메일 인증 완료

### 2. API 키 요청
1. [API Settings](https://www.themoviedb.org/settings/api) 페이지 방문
2. "Create" 버튼 클릭
3. 애플리케이션 정보 입력:
   - **Application Name**: AniVault
   - **Application Summary**: Anime file organization tool
   - **Application URL**: https://github.com/tigers2020/AniVault
4. API 키 복사 및 안전한 곳에 저장

## ⚙️ 환경 설정

### 1. 환경변수 설정
```bash
# .env 파일 생성
cp env.template .env

# API 키 설정
echo "TMDB_API_KEY=your_api_key_here" >> .env
```

### 2. 설정 검증
```bash
# API 연결 테스트
anivault match /path/to/anime --dry-run
```

## 📊 레이트 리밋 관리

### TMDB API 제한사항
- **일반 사용자**: 40 requests per 10 seconds
- **일일 한도**: 10,000 requests per day
- **제한 초과 시**: 429 HTTP 상태 코드 반환

### 레이트 리밋 설정
```bash
# .env 파일에서 설정
TMDB_RATE_LIMIT_PER_WINDOW=40    # 10초당 요청 수
TMDB_REQUEST_TIMEOUT=30          # 요청 타임아웃 (초)
TMDB_MAX_RETRIES=3               # 최대 재시도 횟수
TMDB_BACKOFF_BASE=1              # 백오프 기본 지연 (초)
```

### 레이트 리밋 모니터링
```bash
# API 호출 로그 확인
grep "Rate limit" ~/.anivault/logs/anivault.log

# 재시도 로그 확인
grep "Retrying" ~/.anivault/logs/anivault.log
```

## 💾 캐시 전략

### 캐시 설정
```bash
# 캐시 TTL 설정 (시간)
ANIVAULT_CACHE_TTL_HOURS=24

# 캐시 최대 크기 (MB)
ANIVAULT_CACHE_MAX_SIZE_MB=100

# 캐시 디렉토리
ANIVAULT_CACHE_DIR=~/.anivault/cache

# WAL 모드 활성화 (동시성 향상)
ANIVAULT_CACHE_WAL_MODE=true
```

### 캐시 관리
```bash
# 캐시 상태 확인
sqlite3 ~/.anivault/cache/tmdb_cache.sqlite "SELECT COUNT(*) FROM tmdb_cache;"

# 캐시 초기화
rm -rf ~/.anivault/cache/tmdb_cache.sqlite*

# 캐시 백업
cp ~/.anivault/cache/tmdb_cache.sqlite ~/.anivault/cache/backup_$(date +%Y%m%d).sqlite
```

## 🔄 오프라인 모드

### 오프라인 모드 사용
```bash
# 캐시된 데이터만 사용
anivault match /path/to/anime --offline
```

### 오프라인 모드 제한사항
- 새로운 애니메이션은 매칭되지 않음
- 캐시된 데이터만 사용 가능
- 메타데이터 업데이트 불가

## 🛠️ 고급 설정

### 프록시 설정
```bash
# HTTP 프록시 설정
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=https://proxy.example.com:8080

# 또는 .env 파일에 추가
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=https://proxy.example.com:8080
```

### 사용자 정의 헤더
```bash
# User-Agent 설정
export TMDB_USER_AGENT="AniVault/1.0.0 (https://github.com/tigers2020/AniVault)"
```

### 지역별 설정
```bash
# 한국어 우선 설정
export TMDB_LANGUAGE=ko-KR
export TMDB_REGION=KR
```

## 🚨 에러 처리

### 일반적인 에러와 해결방법

#### 1. API 키 오류 (401 Unauthorized)
```bash
# API 키 확인
echo $TMDB_API_KEY

# API 키 재설정
export TMDB_API_KEY=your_new_api_key_here
```

#### 2. 레이트 리밋 초과 (429 Too Many Requests)
```bash
# 재시도 간격 증가
export TMDB_BACKOFF_BASE=5

# 요청 빈도 감소
export TMDB_RATE_LIMIT_PER_WINDOW=20
```

#### 3. 네트워크 오류
```bash
# 타임아웃 증가
export TMDB_REQUEST_TIMEOUT=60

# 재시도 횟수 증가
export TMDB_MAX_RETRIES=5
```

### 디버그 모드
```bash
# 상세 로그 활성화
export ANIVAULT_LOG_LEVEL=DEBUG
export ANIVAULT_DEBUG=true

# API 호출 로그 확인
tail -f ~/.anivault/logs/anivault.log | grep "TMDB"
```

## 📈 성능 최적화

### 배치 처리 설정
```bash
# 배치 크기 조정
export ANIVAULT_BATCH_SIZE=50

# 동시 요청 수 조정
export ANIVAULT_MAX_WORKERS=4
```

### 캐시 최적화
```bash
# SQLite 최적화
sqlite3 ~/.anivault/cache/tmdb_cache.sqlite "
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = MEMORY;
"
```

## 🔒 보안 고려사항

### API 키 보안
- API 키를 코드에 하드코딩하지 마세요
- 환경변수나 설정 파일을 사용하세요
- API 키를 로그에 기록하지 않도록 주의하세요

### 로그 마스킹
```bash
# 민감한 데이터 마스킹 활성화
export ANIVAULT_LOG_MASK_SENSITIVE=true
```

### 키 로테이션
```bash
# 정기적인 API 키 로테이션 (권장: 6개월마다)
# 1. 새 API 키 발급
# 2. 환경변수 업데이트
# 3. 기존 캐시 유지 (선택사항)
```

## 📊 모니터링 및 알림

### API 사용량 모니터링
```bash
# 일일 API 호출 수 확인
grep "TMDB API call" ~/.anivault/logs/anivault.log | wc -l

# 에러율 확인
grep "ERROR.*TMDB" ~/.anivault/logs/anivault.log | wc -l
```

### 알림 설정
```bash
# API 키 만료 알림 (수동 설정 필요)
# TMDB에서 API 키 상태를 정기적으로 확인하세요
```

## 🆘 문제 해결

### 진단 명령어
```bash
# API 연결 테스트
curl -H "Authorization: Bearer $TMDB_API_KEY" \
     "https://api.themoviedb.org/3/configuration"

# 캐시 상태 확인
sqlite3 ~/.anivault/cache/tmdb_cache.sqlite ".schema"

# 로그 분석
grep -E "(ERROR|WARNING|TMDB)" ~/.anivault/logs/anivault.log
```

### 지원 요청 시 제공할 정보
- AniVault 버전
- Python 버전
- 운영체제 정보
- API 키 발급 날짜
- 에러 로그
- 캐시 상태

## 📚 추가 자료

- [TMDB API 문서](https://developers.themoviedb.org/3/getting-started/introduction)
- [TMDB API 포럼](https://www.themoviedb.org/talk/category/504795851c29526b50016d8)
- [AniVault GitHub Issues](https://github.com/tigers2020/AniVault/issues)
