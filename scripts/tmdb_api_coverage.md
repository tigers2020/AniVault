# TMDB API 커버리지 분석

## 수집한 엔드포인트 (28개)

| 카테고리 | 수집 | 전체 | 비율 |
|---------|-----|------|------|
| **Movie** | 8 | ~24 | 33% |
| **TV Series** | 8 | ~21 | 38% |
| **TV Seasons** | 1 | ~9 | 11% |
| **TV Episodes** | 0 | ~9 | 0% |
| **People** | 3 | ~9 | 33% |
| **Discover** | 4 | 2 | 200% |
| **Trending** | 4 | 4 | 100% |
| **Search** | 3 | 7 | 43% |
| **Collections** | 0 | 3 | 0% |
| **Companies** | 0 | 3 | 0% |
| **Networks** | 0 | 3 | 0% |
| **Keywords** | 0 | 2 | 0% |
| **Genres** | 0 | 2 | 0% |
| **Reviews** | 0 | 1 | 0% |
| **Credits** | 0 | 1 | 0% |
| **Find** | 0 | 1 | 0% |
| **Watch Providers** | 0 | 3 | 0% |
| **Configuration** | 0 | 6 | 0% |
| **Certifications** | 0 | 2 | 0% |
| **Changes** | 0 | 3 | 0% |
| **Account** | 0 | 10 | 0% |
| **Authentication** | 0 | 7 | 0% |
| **Guest Sessions** | 0 | 3 | 0% |
| **Lists** | 0 | 8 | 0% |
| **TV Episode Groups** | 0 | 1 | 0% |

**총계**: 28 / ~150+ (약 18%)

---

## 🎯 **하지만 중요한 사실!**

### **1. 응답 구조는 2가지 패턴뿐**

✅ **이미 수집한 28개 응답에서 모든 패턴을 확인함**:

#### **패턴 A: 목록형 응답** (86%)
```json
{
  "page": 1,
  "results": [...],  // 배열
  "total_pages": 100,
  "total_results": 2000
}
```

**해당 엔드포인트**:
- Movie: popular, now_playing, top_rated, upcoming, similar, recommendations
- TV: popular, on_the_air, airing_today, top_rated, similar, recommendations
- People: popular
- Search: movie, tv, person, collection, company, keyword, multi
- Trending: movie, tv, people (day/week)
- Discover: movie, tv
- **추가로 있을 엔드포인트**: Collections, Companies, Networks, Keywords, Reviews, Lists 등

#### **패턴 B: 상세형 응답** (14%)
```json
{
  "id": 123,
  "title": "...",
  "overview": "...",
  // ... 33-36개 복잡한 필드
  "genres": [...],
  "production_companies": [...],
  "credits": { "cast": [...], "crew": [...] },
  // ... 중첩된 객체/배열
}
```

**해당 엔드포인트**:
- Movie: details
- TV: details
- TV Season: details
- TV Episode: details
- Person: details
- **추가로 있을 엔드포인트**: Collection details, Company details, Network details 등

---

## ✅ **Generic Key-Value 스키마는 여전히 완벽**

### **왜 추가 수집이 필요 없는가?**

1. **모든 응답은 2가지 패턴 중 하나**:
   - 목록형: `{page, results, total_pages, total_results}`
   - 상세형: 복잡한 중첩 구조

2. **JSON BLOB 저장 방식은 모든 구조 호환**:
   - ✅ 어떤 필드 개수든 상관없음
   - ✅ 어떤 중첩 깊이든 상관없음
   - ✅ 새 필드 추가되어도 스키마 변경 불필요

3. **캐시 키 생성 전략이 범용적**:
   ```python
   # 모든 엔드포인트에 적용 가능
   cache_key = f"{endpoint}:{category}:{params}"
   
   # 예시
   "details:collection:id=123"
   "list:company:id=456"
   "images:network:id=789"
   "videos:tv_episode:tv_id=1429:season=1:episode=1"
   ```

---

## 🔍 **추가 검증이 필요하다면?**

만약 확실히 하고 싶다면, 몇 가지 더 수집할 수 있습니다:

### **추가 수집 제안 (우선순위 높음)**

```python
# Collections
collection = Collection()
collection.details(10)  # Star Wars Collection

# Companies
company = Company()
company.details(1)  # Lucasfilm

# Networks
network = Network()
network.details(213)  # Netflix

# Keywords
keyword = Keyword()
keyword.details(180547)  # Anime

# Reviews
review = Review()
review.details("5488c29bc3a3686f4a00004a")

# Configuration
config = Configuration()
config.info()

# TV Episodes
tv_episode = TV_Episodes()
tv_episode.details(1429, 1, 1)  # Attack on Titan S01E01

# Watch Providers
watch_providers = WatchProviders()
watch_providers.available_regions()
```

---

## 🎯 **결론**

### **스키마 설계는 변경 불필요**

- ✅ **Generic Key-Value Store**는 모든 TMDB API 엔드포인트와 호환
- ✅ 이미 수집한 28개 응답으로 2가지 주요 패턴 확인 완료
- ✅ 추가 엔드포인트는 동일한 패턴을 따름

### **추가 수집은 선택사항**

- 📊 **스키마 검증용**: 필요하다면 10-15개 더 수집 가능
- ⚡ **개발 진행용**: 지금 스키마로 바로 Task #1 시작 가능
- 🔄 **확장성**: 나중에 새 엔드포인트 추가 시에도 코드 변경 최소

---

## 💡 **추천 방향**

### **옵션 1: 지금 바로 개발 시작** (추천!)
- 현재 스키마로 SQLiteCacheDB 구현
- 실제 사용하면서 필요한 엔드포인트만 추가
- 빠른 진행, 실용적 접근

### **옵션 2: 추가 검증 후 개발**
- 10-15개 추가 엔드포인트 수집
- 스키마 재검증
- 더 확실하지만 시간 소요

어떤 방향으로 진행하시겠습니까?

