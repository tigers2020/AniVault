# TMDB API 가이드

AniVault의 TMDB (The Movie Database) API 통합에 관한 모든 문서입니다.

## 📚 문서 목록

### 🔑 [TMDB API 키 설정](./tmdb-setup.md)
TMDB API 키 발급 및 설정 가이드
- API 키 발급 방법
- 환경 변수 설정
- 보안 고려사항

### 🏗️ [Rate Limiting 아키텍처](./tmdb-rate-limiting-architecture.md)
TMDB API Rate Limiting 상세 아키텍처
- Token Bucket Rate Limiter
- Semaphore Manager
- Rate Limiting State Machine
- TMDB Client 통합

### ✅ [API 검증 결과](./tmdb-api-validation-results.md)
TMDB API 통합 검증 결과
- API 호출 테스트
- 성능 벤치마크
- 에러 처리 검증
- Rate Limiting 테스트

### 💾 [캐시 데이터베이스 스키마](./tmdb_cache_db_schema.md)
TMDB 캐시 SQLite 데이터베이스 스키마
- 테이블 구조
- 인덱스 전략
- TTL 관리

### ✔️ [캐시 스키마 검증](./tmdb_cache_db_schema_validation.md)
캐시 스키마 검증 결과
- 무결성 검사
- 성능 테스트
- 마이그레이션 전략

## 🚀 빠른 시작

### 1. API 키 설정
```bash
# .env 파일에 키 추가
TMDB_API_KEY=your-api-key-here
```

### 2. 캐시 확인
```bash
# 캐시 상태 확인
anivault cache status

# 캐시 정리
anivault cache clear
```

### 3. API 테스트
```python
from anivault.services.metadata_enricher import MetadataEnricher

enricher = MetadataEnricher()
result = enricher.search_movie("Anime Title", year=2020)
```

## 🔧 고급 설정

### Rate Limiting 설정
```python
# settings.py
TMDB_RATE_LIMIT = 40  # requests per 10 seconds
TMDB_MAX_RETRIES = 3
TMDB_RETRY_DELAY = 1.0
```

### 캐시 설정
```python
# Cache TTL (24시간)
TMDB_CACHE_TTL = 86400

# Cache 경로
TMDB_CACHE_PATH = ".anivault/tmdb_cache.db"
```

## 📊 성능 최적화

### 배치 요청
```python
# 여러 항목 동시 처리
results = await enricher.batch_search(titles, years)
```

### 캐시 프리로딩
```bash
# 인기 애니메이션 미리 캐싱
anivault cache preload --popular
```

## 🐛 문제 해결

### API 키 오류
- `.env` 파일 확인
- API 키 유효성 확인
- 환경 변수 로드 확인

### Rate Limit 초과
- Rate limit 설정 확인
- Retry 로직 활성화
- 배치 크기 조정

### 캐시 문제
- 캐시 파일 권한 확인
- 디스크 공간 확인
- 캐시 정리 실행

## 🔗 관련 문서

- [아키텍처 가이드](../architecture/ARCHITECTURE_ANIVAULT.md)
- [개발 가이드](../guides/development.md)
- [테스트 가이드](../testing/README.md)

---

**문서 버전**: 2.0
**최종 업데이트**: 2025-10-13
**관리자**: AniVault API 팀
