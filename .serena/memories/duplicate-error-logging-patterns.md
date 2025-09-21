# 중복된 에러 로깅 패턴 발견

## 문제점
`src/core/database.py`에서 다음과 같은 중복된 에러 로깅 패턴이 발견됨:

1. `logger.error(f"Failed to get anime metadata: {e}")` (line 588)
2. `logger.error(f"Failed to search anime metadata: {e}")` (line 602)
3. `logger.error(f"Failed to get parsed file: {e}")` (line 674)
4. `logger.error(f"Failed to get parsed files by metadata: {e}")` (line 683)
5. `logger.error(f"Failed to get database stats: {e}")` (line 719)
6. `logger.error(f"Failed to bulk insert anime metadata: {e}")` (line 776)
7. `logger.error(f"Failed to bulk insert parsed files: {e}")` (line 840)
8. `logger.error(f"Failed to bulk upsert anime metadata: {e}")` (line 910)
9. `logger.error(f"Failed to bulk update anime metadata: {e}")` (line 946)
10. `logger.error(f"Failed to bulk update parsed files: {e}")` (line 982)
11. `logger.error(f"Failed to bulk update anime metadata by TMDB IDs: {e}")` (line 1024)
12. `logger.error(f"Failed to bulk update parsed files by file paths: {e}")` (line 1075)
13. `logger.error(f"Schema validation failed: {e}")` (line 1113)
14. `logger.error(f"Failed to validate table {table_name}: {e}")` (line 1158)
15. `logger.error(f"Failed to check schema version: {e}")` (line 1241)

## 리팩토링 제안
공통 에러 로깅 유틸리티 함수를 만들어 중복을 제거하고 일관성을 높일 수 있음.

## 추가 발견사항
- `logger.error(f"Failed to initialize database: {e}")` (line 474) - 초기화 에러
- `logger.error(f"Missing tables: {missing_tables}")` (line 1101) - 스키마 에러
- `logger.error(f"Table {table_name} missing columns: {missing_columns}")` (line 1138) - 스키마 에러
