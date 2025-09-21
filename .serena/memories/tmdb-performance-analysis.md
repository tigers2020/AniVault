# TMDB 검색 성능 병목 분석 결과

## 주요 발견사항

### 1. 다중 검색 전략으로 인한 성능 저하
- `search_comprehensive` 메서드가 5개의 fallback 전략을 순차적으로 실행
- 각 전략마다 `search_multi` API 호출 발생
- 최악의 경우: 6번의 TMDB API 호출 (초기 검색 + 5개 fallback)

### 2. 과도한 로깅으로 인한 I/O 오버헤드
- `search_multi` 메서드에서 각 결과마다 상세한 JSON 로깅
- 디버그 레벨에서도 과도한 로깅 수행
- 대량 파일 처리 시 로그 I/O가 성능에 영향

### 3. 캐시 메커니즘의 비효율성
- 캐시 키 생성이 복잡 (query + language + region + include_adult)
- 캐시 히트/미스 추적이 성능에 영향
- 메모리 기반 캐시로 인한 메모리 사용량 증가

### 4. 순차적 파일 처리
- `ConcreteMetadataRetrievalTask`에서 파일별로 순차 처리
- 각 파일마다 개별 TMDB 검색 수행
- 병렬 처리가 가능함에도 불구하고 순차 실행

### 5. 품질 점수 계산의 복잡성
- `_calculate_quality_score`에서 다중 알고리즘 실행
- 유사도 계산, 연도 매칭, 언어 점수 등 복잡한 계산
- 각 검색 결과마다 품질 점수 계산 수행

### 6. 메타데이터 캐시 오류
- 성능 메트릭스에서 MetadataCache 오류 다수 발견
- 캐시 시스템의 불안정성으로 인한 재시도 증가
