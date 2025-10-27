# LinkedHashTable 사용 가이드

**AniVault LinkedHashTable**은 파일 조직화 작업에 최적화된 고성능 해시 테이블 구현입니다. 이 가이드는 LinkedHashTable의 사용법, 모범 사례, 그리고 기존 `dict`와의 차이점을 설명합니다.

---

## 📋 목차

1. [개요](#개요)
2. [기본 사용법](#기본-사용법)
3. [dict와의 차이점](#dict와의-차이점)
4. [성능 특성](#성능-특성)
5. [모범 사례](#모범-사례)
6. [마이그레이션 가이드](#마이그레이션-가이드)
7. [고급 사용법](#고급-사용법)
8. [문제 해결](#문제-해결)

---

## 🎯 개요

LinkedHashTable은 다음과 같은 특징을 가진 고성능 해시 테이블입니다:

- **O(1) 평균 시간 복잡도**: put, get, remove 연산
- **삽입 순서 유지**: 예측 가능한 반복 순서
- **메모리 최적화**: `__slots__`를 활용한 메모리 효율성
- **타입 안전성**: Generic 타입 지원
- **자동 리해싱**: 1.5x 성장 인수로 메모리 피크 최소화

### 주요 용도
- 파일 메타데이터 저장 및 관리
- 해상도 분석 결과 캐싱
- 순서가 중요한 키-값 쌍 저장
- 대용량 데이터 처리 시 메모리 효율성 요구

---

## 🚀 기본 사용법

### 1. 기본 생성 및 사용

```python
from anivault.core.data_structures.linked_hash_table import LinkedHashTable

# 기본 생성
table = LinkedHashTable()

# 값 추가
table.put("file1", {"size": 1024, "type": "video"})
table.put("file2", {"size": 2048, "type": "audio"})

# 값 조회
value = table.get("file1")
print(value)  # {'size': 1024, 'type': 'video'}

# 크기 확인
print(len(table))  # 2
print(table.size)  # 2 (property)
```

### 2. 순서 유지 확인

```python
# 삽입 순서가 유지됨
for key, value in table:
    print(f"{key}: {value}")

# 출력:
# file1: {'size': 1024, 'type': 'video'}
# file2: {'size': 2048, 'type': 'audio'}
```

### 3. 값 업데이트

```python
# 기존 키 업데이트
old_value = table.put("file1", {"size": 2048, "type": "video"})
print(old_value)  # {'size': 1024, 'type': 'video'}

# 순서는 유지됨 (업데이트는 순서를 변경하지 않음)
for key, value in table:
    print(f"{key}: {value}")
```

### 4. 값 제거

```python
# 값 제거
removed_value = table.remove("file1")
print(removed_value)  # {'size': 2048, 'type': 'video'}

# 존재 확인
print("file1" in table)  # False
print(table.get("file1"))  # None
```

---

## 🔄 dict와의 차이점

### 1. API 차이점

| 연산 | dict | LinkedHashTable |
|------|------|-----------------|
| **값 추가/업데이트** | `d[key] = value` | `table.put(key, value)` |
| **값 조회** | `d[key]` 또는 `d.get(key)` | `table.get(key)` |
| **값 제거** | `del d[key]` 또는 `d.pop(key)` | `table.remove(key)` |
| **존재 확인** | `key in d` | `key in table` |
| **크기 확인** | `len(d)` | `len(table)` 또는 `table.size` |

### 2. 동작 차이점

```python
# dict 사용
d = {}
d["a"] = 1
d["b"] = 2
d["a"] = 3  # 업데이트

# LinkedHashTable 사용
table = LinkedHashTable()
table.put("a", 1)
table.put("b", 2)
table.put("a", 3)  # 업데이트, 순서 유지
```

### 3. 순서 보장

```python
# dict (Python 3.7+): 삽입 순서 보장
d = {"a": 1, "b": 2, "c": 3}
d["a"] = 4  # 업데이트해도 순서 유지

# LinkedHashTable: 명시적 순서 보장
table = LinkedHashTable()
table.put("a", 1)
table.put("b", 2)
table.put("c", 3)
table.put("a", 4)  # 업데이트해도 순서 유지
```

---

## ⚡ 성능 특성

### 1. 시간 복잡도

| 연산 | 평균 | 최악 |
|------|------|------|
| **put(key, value)** | O(1) | O(n) |
| **get(key)** | O(1) | O(n) |
| **remove(key)** | O(1) | O(n) |
| **iteration** | O(n) | O(n) |

### 2. 메모리 효율성

- **`__slots__` 사용**: 메모리 오버헤드 최소화
- **1.5x 성장 인수**: 메모리 피크 최소화
- **다중 연결 구조**: 삽입 순서 유지를 위한 추가 포인터

### 3. 성능 벤치마크

```python
import time
from anivault.core.data_structures.linked_hash_table import LinkedHashTable

# 성능 테스트
def benchmark_operations():
    table = LinkedHashTable()

    # 삽입 성능
    start = time.time()
    for i in range(10000):
        table.put(f"key_{i}", f"value_{i}")
    insert_time = time.time() - start

    # 조회 성능
    start = time.time()
    for i in range(10000):
        table.get(f"key_{i}")
    get_time = time.time() - start

    print(f"Insert: {insert_time:.4f}s")
    print(f"Get: {get_time:.4f}s")
```

---

## 📚 모범 사례

### 1. 적절한 초기 용량 설정

```python
# 예상되는 데이터 크기에 맞게 초기 용량 설정
expected_size = 1000
table = LinkedHashTable(initial_capacity=expected_size)

# 리해싱을 줄여 성능 향상
for i in range(expected_size):
    table.put(f"key_{i}", f"value_{i}")
```

### 2. 타입 힌트 활용

```python
from typing import Dict, List
from anivault.core.data_structures.linked_hash_table import LinkedHashTable

# 명시적 타입 지정
file_metadata: LinkedHashTable[str, Dict[str, any]] = LinkedHashTable()

# 타입 안전성 확보
file_metadata.put("video.mp4", {
    "size": 1024,
    "duration": 120,
    "resolution": "1080p"
})
```

### 3. None 값 처리

```python
# LinkedHashTable.get()은 키가 없으면 None 반환
value = table.get("nonexistent_key")
if value is not None:
    print(f"Found: {value}")
else:
    print("Key not found")

# dict.get()과 동일한 패턴 사용
value = table.get("nonexistent_key", "default_value")
```

### 4. 대용량 데이터 처리

```python
def process_large_dataset(file_list: List[str]) -> LinkedHashTable[str, Dict]:
    """대용량 파일 리스트 처리"""
    # 적절한 초기 용량 설정
    table = LinkedHashTable(initial_capacity=len(file_list))

    for file_path in file_list:
        metadata = extract_metadata(file_path)
        table.put(file_path, metadata)

    return table
```

---

## 🔧 마이그레이션 가이드

### 1. dict에서 LinkedHashTable로 마이그레이션

#### Before (dict 사용)
```python
def analyze_files(files: List[str]) -> Dict[str, FileInfo]:
    results = {}

    for file_path in files:
        info = parse_file(file_path)
        results[file_path] = info

    return results
```

#### After (LinkedHashTable 사용)
```python
from anivault.core.data_structures.linked_hash_table import LinkedHashTable

def analyze_files(files: List[str]) -> LinkedHashTable[str, FileInfo]:
    results = LinkedHashTable(initial_capacity=len(files))

    for file_path in files:
        info = parse_file(file_path)
        results.put(file_path, info)

    return results
```

### 2. 반복문 마이그레이션

#### Before
```python
# dict 반복
for key, value in results.items():
    process_item(key, value)

# dict 키만 반복
for key in results:
    process_key(key)

# dict 값만 반복
for value in results.values():
    process_value(value)
```

#### After
```python
# LinkedHashTable 반복 (순서 보장)
for key, value in results:
    process_item(key, value)

# 키만 반복
for key, _ in results:
    process_key(key)

# 값만 반복
for _, value in results:
    process_value(value)
```

### 3. 조건부 처리 마이그레이션

#### Before
```python
# dict에서 키 존재 확인 후 처리
if "special_key" in results:
    special_value = results["special_key"]
    process_special(special_value)
```

#### After
```python
# LinkedHashTable에서 키 존재 확인 후 처리
if "special_key" in results:
    special_value = results.get("special_key")
    if special_value is not None:  # None 체크 추가
        process_special(special_value)
```

---

## 🔬 고급 사용법

### 1. 커스텀 해시 함수 활용

```python
# LinkedHashTable은 (title, episode) 튜플에 최적화됨
table = LinkedHashTable()

# 애니메이션 파일 메타데이터 저장
table.put(("Attack on Titan", 1), {"resolution": "1080p", "size": 1024})
table.put(("Attack on Titan", 2), {"resolution": "1080p", "size": 1024})
table.put(("One Piece", 1), {"resolution": "720p", "size": 512})

# 순서가 유지됨
for (title, episode), metadata in table:
    print(f"{title} Episode {episode}: {metadata}")
```

### 2. 성능 모니터링

```python
def monitor_performance(table: LinkedHashTable):
    """LinkedHashTable 성능 모니터링"""
    print(f"Capacity: {table.capacity}")
    print(f"Size: {table.size}")
    print(f"Load Factor: {table.load_factor:.2f}")

    # 로드 팩터가 높으면 리해싱이 자주 발생할 수 있음
    if table.load_factor > 0.7:
        print("Warning: High load factor detected")
```

### 3. 메모리 효율적인 대용량 처리

```python
def process_files_in_batches(file_list: List[str], batch_size: int = 1000):
    """배치 단위로 파일 처리하여 메모리 효율성 향상"""
    results = LinkedHashTable(initial_capacity=batch_size)

    for i in range(0, len(file_list), batch_size):
        batch = file_list[i:i + batch_size]

        # 배치 처리
        for file_path in batch:
            metadata = extract_metadata(file_path)
            results.put(file_path, metadata)

        # 배치 완료 후 처리
        yield results

        # 메모리 정리
        results.clear()
```

---

## 🐛 문제 해결

### 1. 일반적인 문제

#### 문제: `get()` 메서드가 None 반환
```python
# 문제 상황
value = table.get("nonexistent_key")
if value:  # None은 falsy이므로 이 조건은 False
    process_value(value)

# 해결책
value = table.get("nonexistent_key")
if value is not None:  # 명시적 None 체크
    process_value(value)
```

#### 문제: 순서가 예상과 다름
```python
# 문제 상황: 업데이트가 순서를 변경할 수 있음
table.put("a", 1)
table.put("b", 2)
table.put("a", 3)  # 업데이트

# 해결책: LinkedHashTable은 업데이트 시 순서를 유지함
for key, value in table:
    print(f"{key}: {value}")
# 출력: a: 3, b: 2 (삽입 순서 유지)
```

### 2. 성능 문제

#### 문제: 느린 삽입 성능
```python
# 문제: 작은 초기 용량으로 인한 빈번한 리해싱
table = LinkedHashTable(initial_capacity=10)  # 너무 작음

# 해결책: 예상 크기에 맞는 초기 용량 설정
expected_size = 10000
table = LinkedHashTable(initial_capacity=expected_size)
```

#### 문제: 높은 메모리 사용량
```python
# 문제: 높은 로드 팩터로 인한 메모리 낭비
table = LinkedHashTable(load_factor=0.9)  # 너무 높음

# 해결책: 적절한 로드 팩터 설정
table = LinkedHashTable(load_factor=0.7)  # 권장값
```

### 3. 디버깅 팁

```python
def debug_table(table: LinkedHashTable):
    """LinkedHashTable 디버깅 정보 출력"""
    print(f"Table state: {table}")
    print(f"Capacity: {table.capacity}")
    print(f"Size: {table.size}")
    print(f"Load factor: {table.load_factor:.2f}")

    # 모든 키-값 쌍 출력
    print("Contents:")
    for i, (key, value) in enumerate(table):
        print(f"  {i}: {key} -> {value}")
```

---

## 📖 추가 자료

### 관련 문서
- [LinkedHashTable API 문서](../api/linked_hash_table.md)
- [성능 벤치마크 결과](../performance/linkedhashtable_benchmarks.md)
- [마이그레이션 체크리스트](../migration/checklist.md)

### 예제 코드
- [파일 조직화 예제](../examples/file_organization.py)
- [해상도 분석 예제](../examples/resolution_analysis.py)
- [성능 테스트 예제](../examples/performance_tests.py)

### 지원
- 이슈 리포트: [GitHub Issues](https://github.com/anivault/issues)
- 개발팀 문의: [개발팀 연락처](../contact/development.md)

---

**문서 버전**: 1.0
**최종 업데이트**: 2025-01-26
**작성자**: AniVault 개발팀
