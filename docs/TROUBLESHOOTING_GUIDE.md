# 트러블슈팅 가이드: LinkedHashTable과 OptimizedFileOrganizer

## 개요

이 문서는 LinkedHashTable과 OptimizedFileOrganizer 사용 중 발생할 수 있는 일반적인 문제들과 해결 방법을 제공합니다.

## 일반적인 문제들

### 1. 성능 문제

#### 문제: 파일 추가가 느림
**증상**: `add_file()` 메서드가 예상보다 오래 걸림

**원인**:
- 대량의 파일을 한 번에 처리
- 메모리 부족으로 인한 가비지 컬렉션
- 해시 충돌이 많아 리해싱이 자주 발생

**해결책**:
```python
# 1. 배치 처리로 나누어 처리
batch_size = 100
for i in range(0, len(files), batch_size):
    batch = files[i:i + batch_size]
    for file in batch:
        organizer.add_file(file)

    # 배치 간 가비지 컬렉션
    import gc
    gc.collect()

# 2. 메모리 사용량 모니터링
import tracemalloc
tracemalloc.start()

# 작업 수행
current, peak = tracemalloc.get_traced_memory()
print(f"메모리 사용량: {current / 1024 / 1024:.2f} MB")

# 3. 테이블 상태 확인
print(f"로드 팩터: {organizer._file_cache.load_factor}")
print(f"테이블 용량: {organizer._file_cache.capacity}")
```

#### 문제: 중복 탐지가 제대로 작동하지 않음
**증상**: 중복 파일이 탐지되지 않음

**원인**:
- 메타데이터가 올바르지 않음
- 해시 키 생성 오류
- 파일이 아직 추가되지 않음

**해결책**:
```python
# 1. 메타데이터 확인
for file in scanned_files:
    print(f"Title: {file.metadata.title}")
    print(f"Episode: {file.metadata.episode}")
    print(f"Quality: {file.metadata.quality}")

# 2. 파일 추가 확인
print(f"캐시된 파일 수: {organizer.file_count}")

# 3. 중복 탐지 결과 확인
duplicates = organizer.find_duplicates()
print(f"중복 그룹 수: {len(duplicates)}")

for i, group in enumerate(duplicates):
    print(f"중복 그룹 {i+1}: {len(group)}개 파일")
    for file in group:
        print(f"  - {file.file_path.name}")
```

### 2. 메모리 문제

#### 문제: 메모리 사용량이 높음
**증상**: 메모리 사용량이 예상보다 높음

**원인**:
- 대량의 파일 데이터
- 메모리 누수
- 가비지 컬렉션 지연

**해결책**:
```python
# 1. 캐시 정리
organizer.clear_cache()

# 2. 가비지 컬렉션 강제 실행
import gc
gc.collect()

# 3. 메모리 프로파일링
import tracemalloc
tracemalloc.start()

# 작업 수행
current, peak = tracemalloc.get_traced_memory()
print(f"현재 메모리: {current / 1024 / 1024:.2f} MB")
print(f"최대 메모리: {peak / 1024 / 1024:.2f} MB")

# 4. 메모리 사용량이 높은 객체 찾기
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

#### 문제: 메모리 부족 오류
**증상**: `MemoryError` 발생

**원인**:
- 시스템 메모리 부족
- 너무 많은 파일을 한 번에 처리
- 메모리 누수

**해결책**:
```python
# 1. 배치 크기 줄이기
batch_size = 50  # 더 작은 배치 크기

# 2. 메모리 사용량 모니터링
import psutil
memory_percent = psutil.virtual_memory().percent
if memory_percent > 80:
    print("메모리 사용량이 높습니다. 배치 크기를 줄이세요.")

# 3. 스트리밍 처리
def process_files_in_batches(files, batch_size=100):
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        yield batch

        # 배치 간 메모리 정리
        import gc
        gc.collect()
```

### 3. 데이터 무결성 문제

#### 문제: 파일이 중복으로 인식되지 않음
**증상**: 같은 애니메이션의 다른 품질 버전이 중복으로 인식되지 않음

**원인**:
- 메타데이터 파싱 오류
- 제목이나 에피소드 정보가 다름
- 해시 키 생성 오류

**해결책**:
```python
# 1. 메타데이터 정규화
def normalize_title(title):
    """제목 정규화"""
    return title.strip().lower().replace(" ", "_")

def normalize_episode(episode):
    """에피소드 정규화"""
    if isinstance(episode, str):
        # "01", "1", "001" 등을 1로 정규화
        return int(episode.lstrip("0") or "0")
    return int(episode)

# 2. 정규화된 키로 해시 테이블 사용
def create_hash_key(file):
    title = normalize_title(file.metadata.title)
    episode = normalize_episode(file.metadata.episode)
    return (title, episode)

# 3. 디버깅을 위한 로그 추가
import logging
logging.basicConfig(level=logging.DEBUG)

for file in scanned_files:
    key = create_hash_key(file)
    print(f"파일: {file.file_path.name}")
    print(f"원본 제목: {file.metadata.title}")
    print(f"원본 에피소드: {file.metadata.episode}")
    print(f"정규화된 키: {key}")
    print("---")
```

#### 문제: 잘못된 파일이 중복으로 인식됨
**증상**: 다른 애니메이션이 중복으로 인식됨

**원인**:
- 메타데이터 파싱 오류
- 제목 정규화 문제
- 해시 충돌

**해결책**:
```python
# 1. 메타데이터 품질 확인
def validate_metadata(file):
    """메타데이터 유효성 검사"""
    if not file.metadata:
        return False

    title = file.metadata.title
    episode = file.metadata.episode

    # 제목이 너무 짧거나 일반적인 경우 제외
    if len(title) < 3 or title.lower() in ["unknown", "untitled", "video"]:
        return False

    # 에피소드가 유효한 범위인지 확인
    if not isinstance(episode, (int, str)) or episode < 0:
        return False

    return True

# 2. 유효한 파일만 처리
valid_files = [f for f in scanned_files if validate_metadata(f)]
print(f"유효한 파일 수: {len(valid_files)} / {len(scanned_files)}")

# 3. 해시 충돌 확인
def check_hash_collisions(organizer):
    """해시 충돌 확인"""
    bucket_counts = [0] * organizer._file_cache.capacity
    collisions = 0

    for key, _ in organizer._file_cache:
        bucket_idx = hash(key) % organizer._file_cache.capacity
        bucket_counts[bucket_idx] += 1
        if bucket_counts[bucket_idx] > 1:
            collisions += 1

    print(f"해시 충돌 수: {collisions}")
    print(f"충돌률: {collisions / len(organizer._file_cache) * 100:.2f}%")
```

### 4. 에러 처리 문제

#### 문제: `ValueError: scanned_file must have a valid file_path with name`
**증상**: 파일 추가 시 ValueError 발생

**원인**:
- 파일 경로가 None이거나 빈 문자열
- 파일 경로에 name 속성이 없음

**해결책**:
```python
# 1. 파일 경로 유효성 검사
def validate_file_path(file_path):
    """파일 경로 유효성 검사"""
    if not file_path:
        return False

    if not hasattr(file_path, 'name'):
        return False

    if not file_path.name:
        return False

    return True

# 2. 유효한 파일만 처리
valid_files = []
for file in scanned_files:
    if validate_file_path(file.file_path):
        valid_files.append(file)
    else:
        print(f"유효하지 않은 파일 경로: {file.file_path}")

# 3. 안전한 파일 추가
for file in valid_files:
    try:
        organizer.add_file(file)
    except ValueError as e:
        print(f"파일 추가 실패: {file.file_path.name} - {e}")
```

#### 문제: `TypeError: 'ParsingResult' object is not subscriptable`
**증상**: 메타데이터 접근 시 TypeError 발생

**원인**:
- 메타데이터가 딕셔너리가 아닌 ParsingResult 객체
- 잘못된 속성 접근 방식

**해결책**:
```python
# 1. 올바른 속성 접근
# 잘못된 방식
# title = file.metadata['title']

# 올바른 방식
title = file.metadata.title
episode = file.metadata.episode
quality = file.metadata.quality

# 2. 안전한 속성 접근
def get_metadata_value(metadata, field, default=None):
    """안전한 메타데이터 값 접근"""
    if not metadata:
        return default

    return getattr(metadata, field, default)

title = get_metadata_value(file.metadata, 'title', 'Unknown')
episode = get_metadata_value(file.metadata, 'episode', 0)
quality = get_metadata_value(file.metadata, 'quality', 'Unknown')
```

### 5. 설정 문제

#### 문제: 설정 파일을 찾을 수 없음
**증상**: `FileNotFoundError` 또는 설정 관련 오류

**원인**:
- 설정 파일 경로 오류
- 설정 파일 권한 문제
- 설정 파일 형식 오류

**해결책**:
```python
# 1. 설정 파일 경로 확인
import os
from pathlib import Path

config_path = Path("config/settings.json")
if not config_path.exists():
    print(f"설정 파일을 찾을 수 없습니다: {config_path}")
    # 기본 설정 사용
    settings = create_default_settings()
else:
    settings = load_settings(config_path)

# 2. 설정 파일 권한 확인
if not os.access(config_path, os.R_OK):
    print(f"설정 파일 읽기 권한이 없습니다: {config_path}")

# 3. 설정 파일 형식 확인
import json
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
except json.JSONDecodeError as e:
    print(f"설정 파일 JSON 형식 오류: {e}")
```

## FAQ (자주 묻는 질문)

### Q1: OptimizedFileOrganizer와 기존 FileOrganizer의 차이점은 무엇인가요?

**A**: OptimizedFileOrganizer는 LinkedHashTable을 사용하여 성능을 크게 향상시킨 버전입니다. 주요 차이점:

- **성능**: O(1) 파일 추가/조회 vs O(n) 기존 방식
- **메모리**: 16% 메모리 사용량 감소
- **호환성**: 기존 API와 완전 호환
- **자동 전환**: 기존 코드 수정 없이 자동 사용

### Q2: 기존 코드를 수정해야 하나요?

**A**: 아니요. OptimizedFileOrganizer는 기존 FileOrganizer와 완전히 호환되므로 기존 코드를 수정할 필요가 없습니다. 자동으로 최적화된 버전이 사용됩니다.

### Q3: 성능이 예상보다 낮은 이유는 무엇인가요?

**A**: 가능한 원인들:

1. **메모리 부족**: 시스템 메모리가 부족하면 가비지 컬렉션이 자주 발생
2. **해시 충돌**: 해시 충돌이 많으면 리해싱이 자주 발생
3. **배치 크기**: 너무 많은 파일을 한 번에 처리
4. **디스크 I/O**: 느린 디스크로 인한 병목

### Q4: 메모리 사용량을 줄이는 방법은 무엇인가요?

**A**: 다음 방법들을 시도해보세요:

1. **캐시 정리**: `organizer.clear_cache()` 호출
2. **배치 처리**: 파일을 작은 배치로 나누어 처리
3. **가비지 컬렉션**: `gc.collect()` 호출
4. **메모리 모니터링**: `tracemalloc` 사용하여 메모리 사용량 추적

### Q5: 중복 파일이 제대로 탐지되지 않는 이유는 무엇인가요?

**A**: 가능한 원인들:

1. **메타데이터 오류**: 제목이나 에피소드 정보가 잘못됨
2. **파싱 오류**: 파일명에서 메타데이터를 올바르게 추출하지 못함
3. **정규화 문제**: 제목 정규화가 일관되지 않음
4. **파일 미추가**: 파일이 아직 organizer에 추가되지 않음

### Q6: 에러가 발생했을 때 어떻게 디버깅하나요?

**A**: 다음 단계를 따라하세요:

1. **로깅 활성화**: `logging.basicConfig(level=logging.DEBUG)`
2. **메타데이터 확인**: 파일의 메타데이터가 올바른지 확인
3. **상태 확인**: organizer의 현재 상태 확인
4. **단계별 테스트**: 각 단계를 개별적으로 테스트

### Q7: 대용량 파일 컬렉션을 처리할 때 주의사항은 무엇인가요?

**A**: 다음 사항들을 주의하세요:

1. **메모리 모니터링**: 메모리 사용량을 지속적으로 모니터링
2. **배치 처리**: 파일을 작은 배치로 나누어 처리
3. **진행 상황 표시**: 사용자에게 진행 상황을 표시
4. **에러 처리**: 개별 파일 처리 실패 시 전체 작업이 중단되지 않도록 처리

### Q8: 성능을 더 향상시킬 수 있는 방법이 있나요?

**A**: 다음 방법들을 시도해보세요:

1. **병렬 처리**: `multiprocessing` 또는 `concurrent.futures` 사용
2. **메모리 최적화**: 불필요한 데이터 제거
3. **캐싱**: 자주 사용되는 데이터 캐싱
4. **프로파일링**: 성능 병목 지점 식별

## 추가 도움말

### 로그 레벨 설정
```python
import logging

# 디버그 로그 활성화
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 특정 모듈만 디버그 로그 활성화
logging.getLogger("anivault.core.organizer.optimized_file_organizer").setLevel(logging.DEBUG)
```

### 성능 프로파일링
```python
import cProfile
import pstats

# 성능 프로파일링
profiler = cProfile.Profile()
profiler.enable()

# 작업 수행
organizer.organize(scanned_files)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # 상위 10개 함수 출력
```

### 메모리 프로파일링
```python
import tracemalloc

# 메모리 추적 시작
tracemalloc.start()

# 작업 수행
organizer.organize(scanned_files)

# 메모리 사용량 분석
current, peak = tracemalloc.get_traced_memory()
print(f"현재 메모리: {current / 1024 / 1024:.2f} MB")
print(f"최대 메모리: {peak / 1024 / 1024:.2f} MB")

# 메모리 사용량이 높은 코드 찾기
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

이 가이드를 참고하여 문제를 해결하고 성능을 최적화하세요. 추가 질문이 있으면 개발팀에 문의하세요.
