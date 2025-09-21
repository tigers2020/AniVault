# 추가 중복된 에러 로깅 패턴 발견

## 다른 파일들에서 발견된 중복 패턴들:

### 1. anime_parser.py
- `logger.error(f"Anitopy parsing failed for filename '{filename}': {e}")` (line 134)
- `logger.error(f"Error parsing filename '{filename}': {e}")` (line 184)

### 2. circuit_breaker.py
- `logger.error(f"Failed to reset circuit breaker '{name}': {e}")` (line 273)
- `logger.error(f"Operation failed: {op_name}. Error: {e}")` (line 355)

### 3. consistency_validator.py
- `logger.error(f"Error during anime metadata consistency validation: {e}")` (line 142)
- `logger.error(f"Error during parsed files consistency validation: {e}")` (line 213)

### 4. file_mover.py
- `logger.error(f"File move failed: {source_path} -> {target_path}: {e}")` (line 165)
- `logger.error(f"Unexpected error in batch operation: {e}")` (line 214)
- `logger.error(f"Rollback failed for transaction {transaction_id}: {e}")` (line 412)

### 5. metadata_cache.py
- `logger.error(f"Failed to store in database: {e}")` (line 223)
- `logger.error(f"Failed to delete from database: {e}")` (line 257)
- `logger.error(f"Failed to bulk store TMDB metadata: {e}")` (line 576)
- `logger.error(f"Failed to bulk store parsed files: {e}")` (line 615)
- `logger.error(f"Failed to bulk update TMDB metadata: {e}")` (line 653)
- `logger.error(f"Failed to bulk update parsed files: {e}")` (line 686)
- `logger.error(f"Failed to bulk update TMDB metadata by IDs: {e}")` (line 729)
- `logger.error(f"Failed to bulk update parsed files by paths: {e}")` (line 772)
- `logger.error(f"Failed to load from database for key {key}: {e}")` (line 816)
- `logger.error(f"Failed to delete from database for key {key}: {e}")` (line 853)

### 6. metadata_storage.py
- `logger.error(f"Failed to store TMDB metadata: {e}")` (line 115)
- `logger.error(f"Failed to retrieve TMDB metadata from database: {e}")` (line 166)
- `logger.error(f"Failed to search TMDB metadata: {e}")` (line 202)
- `logger.error(f"Failed to store parsed file: {e}")` (line 264)
- `logger.error(f"Failed to retrieve parsed file from database: {e}")` (line 336)
- `logger.error(f"Failed to get files by TMDB ID: {e}")` (line 375)
- `logger.error(f"Failed to delete parsed file: {e}")` (line 412)
- `logger.error(f"Failed to sync cache to database: {e}")` (line 460)
- `logger.error(f"Failed to calculate file hash: {e}")` (line 524)

### 7. reconciliation_strategies.py
- `logger.error(f"Error in database-wins reconciliation: {e}")` (line 159)
- `logger.error(f"Error in last-modified-wins reconciliation: {e}")` (line 186)
- `logger.error(f"Error in cache-wins reconciliation: {e}")` (line 214)
- `logger.error(f"Error updating cache from database: {e}")` (line 258)
- `logger.error(f"Error updating database from cache: {e}")` (line 281)
- `logger.error(f"Error updating anime metadata from cache: {e}")` (line 338)
- `logger.error(f"Error updating parsed file from cache: {e}")` (line 401)
- `logger.error(f"Error in timestamp reconciliation: {e}")` (line 449)

### 8. resilience_integration.py
- `logger.error(f"Failed to setup resilience system: {e}")` (line 84)
- `logger.error(f"Error during resilience system shutdown: {e}")` (line 103)
- `logger.error(f"Error getting resilience status: {e}")` (line 122)
- `logger.error(f"Error during forced recovery check: {e}")` (line 143)

### 9. file_processing_tasks.py
- `logger.error(f"File scanning failed: {e}")` (line 72)
- `logger.error(f"File grouping failed: {e}")` (line 134)
- `logger.error(f"File parsing failed: {e}")` (line 209)
- `logger.error(f"Metadata retrieval failed: {e}")` (line 302)
- `logger.error(f"Group-based metadata retrieval failed: {e}")` (line 516)
- `logger.error(f"File moving failed: {e}")` (line 725)

### 10. transaction_manager.py
- `logger.error(f"Failed to commit transaction {context.id}: {e}")` (line 199)

## 리팩토링 제안
이러한 중복 패턴들을 `error_utils.py`의 함수들로 교체하여 코드 일관성을 높이고 유지보수성을 개선할 수 있습니다.
