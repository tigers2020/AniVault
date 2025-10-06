# TMDB 캐시 DB 스키마 설계

## 📋 **설계 원칙**

김지유의 **"영수증 드리븐 개발"** 원칙에 따라 실제 TMDB API 응답(28개 엔드포인트)을 분석하여 설계했습니다.

### **핵심 발견사항**
- **목록형 응답**: 24/28 (86%) - 공통 구조 (page, results, total_pages, total_results)
- **상세형 응답**: 4/28 (14%) - 엔드포인트마다 다른 복잡한 구조 (33-36개 필드)
- **중첩 구조**: 모든 응답에 객체/배열이 중첩되어 있음

### **설계 결정**
✅ **Generic Key-Value Store** 채택:
1. TMDB API의 모든 엔드포인트에 호환
2. 스키마 변경 없이 새 엔드포인트 추가 가능
3. API 응답 구조 변경에 완전 독립적
4. 구현 단순, 성능 우수

---

## 🗄️ **SQLite 스키마**

### **1. 메인 캐시 테이블 (tmdb_cache)**

```sql
-- 메인 캐시 테이블
CREATE TABLE tmdb_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- ===========================
    -- 캐시 키 정보
    -- ===========================
    cache_key TEXT NOT NULL UNIQUE,      -- 원본 키 (예: "search:tv:attack on titan:lang=ko")
    key_hash TEXT NOT NULL UNIQUE,       -- SHA-256 해시 (빠른 조회용)
    
    -- ===========================
    -- 캐시 타입 (확장 가능)
    -- ===========================
    cache_type TEXT NOT NULL,            -- "search", "details", "discover", "trending" 등
    endpoint_category TEXT,              -- "movie", "tv", "person", "season" 등 (옵션)
    
    -- ===========================
    -- 실제 데이터 (JSON BLOB)
    -- ===========================
    response_data TEXT NOT NULL,         -- JSON 형태로 저장된 API 응답 전체
    
    -- ===========================
    -- TTL 및 메타데이터
    -- ===========================
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,                -- NULL이면 영구 캐시
    
    -- ===========================
    -- 통계 및 분석용 (선택)
    -- ===========================
    hit_count INTEGER DEFAULT 0,         -- 캐시 히트 카운트
    last_accessed_at TIMESTAMP,          -- 마지막 액세스 시간
    response_size INTEGER,               -- 응답 크기 (바이트)
    
    -- ===========================
    -- 인덱스
    -- ===========================
    CHECK (length(cache_key) > 0),
    CHECK (length(key_hash) = 64),       -- SHA-256은 64자
    CHECK (cache_type IN ('search', 'details', 'discover', 'trending', 'popular', 
                          'recommendations', 'similar', 'now_playing', 'upcoming', 
                          'top_rated', 'on_the_air', 'airing_today'))
);

-- 인덱스
CREATE INDEX idx_key_hash ON tmdb_cache(key_hash);
CREATE INDEX idx_cache_type ON tmdb_cache(cache_type);
CREATE INDEX idx_endpoint_category ON tmdb_cache(endpoint_category);
CREATE INDEX idx_expires_at ON tmdb_cache(expires_at);
CREATE INDEX idx_last_accessed ON tmdb_cache(last_accessed_at);

-- Write-Ahead Logging 활성화 (동시성 개선)
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
```

---

## 🔑 **캐시 키 생성 전략**

### **포맷**
```
{endpoint}:{category}:{params}
```

### **예시**

| API 호출 | 캐시 키 | 설명 |
|---------|---------|------|
| `movie.search("Attack on Titan")` | `search:movie:attack on titan:lang=ko` | 영화 검색 |
| `tv.details(1429)` | `details:tv:1429:lang=ko` | TV 상세 정보 |
| `movie.popular()` | `popular:movie:page=1:lang=ko` | 인기 영화 |
| `discover.discover_movies({'genre': 16})` | `discover:movie:genre=16:sort=popularity.desc` | 애니메이션 발견 |
| `season.details(1429, 1)` | `details:season:tv_id=1429:season=1` | 시즌 상세 |

### **키 생성 함수**

```python
import hashlib
from typing import Dict, Any

def generate_cache_key(
    endpoint: str,
    category: str,
    params: Dict[str, Any]
) -> tuple[str, str]:
    """범용 캐시 키 생성.
    
    Args:
        endpoint: API 엔드포인트 (예: "search", "details")
        category: 리소스 카테고리 (예: "movie", "tv")
        params: 쿼리 파라미터
    
    Returns:
        (cache_key, key_hash) 튜플
    """
    # 1. 파라미터 정렬 및 문자열화
    sorted_params = sorted(params.items())
    param_str = ":".join(f"{k}={v}" for k, v in sorted_params)
    
    # 2. 캐시 키 생성
    cache_key = f"{endpoint}:{category}:{param_str}"
    
    # 3. SHA-256 해시 생성
    key_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    
    return cache_key, key_hash
```

---

## 💾 **사용 예시**

### **1. 캐시 저장 (SET)**

```python
# API 호출 예시
movie = Movie()
search_results = movie.search("Attack on Titan")

# 캐시 키 생성
cache_key = "search:movie:attack on titan:lang=ko"
key_hash = hashlib.sha256(cache_key.encode()).hexdigest()

# DB에 저장
INSERT INTO tmdb_cache (
    cache_key, 
    key_hash, 
    cache_type, 
    endpoint_category,
    response_data, 
    expires_at,
    response_size
) VALUES (
    ?,  -- cache_key
    ?,  -- key_hash
    'search',
    'movie',
    ?,  -- JSON.dumps(search_results)
    datetime('now', '+30 minutes'),
    ?   -- len(response_data)
);
```

### **2. 캐시 조회 (GET)**

```python
# 캐시 키로 조회
SELECT response_data 
FROM tmdb_cache 
WHERE key_hash = ? 
  AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
LIMIT 1;

# 조회 성공 시 통계 업데이트
UPDATE tmdb_cache 
SET hit_count = hit_count + 1,
    last_accessed_at = CURRENT_TIMESTAMP
WHERE key_hash = ?;
```

### **3. 만료된 캐시 정리 (PURGE)**

```python
# 만료된 항목 삭제
DELETE FROM tmdb_cache 
WHERE expires_at IS NOT NULL 
  AND expires_at < CURRENT_TIMESTAMP;

# 오래된 항목 삭제 (LRU)
DELETE FROM tmdb_cache 
WHERE id IN (
    SELECT id 
    FROM tmdb_cache 
    ORDER BY last_accessed_at ASC 
    LIMIT 1000
);
```

---

## 📊 **통계 쿼리**

### **캐시 현황**

```sql
-- 타입별 캐시 개수
SELECT 
    cache_type,
    endpoint_category,
    COUNT(*) as count,
    SUM(response_size) as total_size_bytes,
    AVG(hit_count) as avg_hits
FROM tmdb_cache
GROUP BY cache_type, endpoint_category
ORDER BY count DESC;
```

### **히트율 분석**

```sql
-- 캐시 히트율 상위 10개
SELECT 
    cache_key,
    cache_type,
    hit_count,
    created_at,
    last_accessed_at
FROM tmdb_cache
ORDER BY hit_count DESC
LIMIT 10;
```

### **만료 예정 캐시**

```sql
-- 1시간 내 만료 예정
SELECT 
    cache_key,
    cache_type,
    expires_at,
    (expires_at - CURRENT_TIMESTAMP) as time_remaining
FROM tmdb_cache
WHERE expires_at IS NOT NULL
  AND expires_at BETWEEN CURRENT_TIMESTAMP AND datetime('now', '+1 hour')
ORDER BY expires_at ASC;
```

---

## 🔄 **마이그레이션 계획 (JSONCacheV2 → SQLiteCacheDB)**

### **Phase 1: 병렬 운영**
1. SQLiteCacheDB 구현 (Task #1)
2. 기존 JSONCacheV2와 병렬로 캐싱
3. 히트율/성능 비교

### **Phase 2: 점진적 전환**
1. 새 캐시는 SQLite에만 저장
2. 기존 JSON 캐시 읽기 지원 유지
3. 사용자에게 영향 없음

### **Phase 3: 완전 전환**
1. TMDBClient에서 SQLiteCacheDB만 사용
2. 기존 JSON 캐시 파일 정리
3. JSONCacheV2 deprecated 처리

---

## 🎯 **장점 요약**

### **1. 범용성**
- ✅ TMDB API의 모든 엔드포인트 호환
- ✅ 새 엔드포인트 추가 시 코드 변경 최소
- ✅ API 응답 구조 변경에 독립적

### **2. 성능**
- ⚡ 단일 테이블 조회로 충분
- ⚡ 인덱스 최적화 단순
- ⚡ JOIN 없음, 빠른 조회

### **3. 동시성**
- 🔄 WAL 모드로 동시 읽기/쓰기 가능
- 🔄 파일 락 문제 없음
- 🔄 멀티스레드 안전

### **4. 확장성**
- 📈 필요 시 메타데이터 테이블 추가 가능
- 📈 통계 필드로 분석 가능
- 📈 점진적 개선 가능

### **5. 유지보수성**
- 🛠️ 구현 단순, 버그 최소
- 🛠️ 테스트 용이
- 🛠️ 명확한 인터페이스

---

## 📝 **참고자료**

- **실제 API 응답**: `scripts/tmdb_api_responses/`
- **응답 요약**: `scripts/tmdb_api_responses/_summary.json`
- **TMDB API 문서**: https://developers.themoviedb.org/3/
- **tmdbv3api 라이브러리**: https://github.com/AnthonyBloomer/tmdbv3api

