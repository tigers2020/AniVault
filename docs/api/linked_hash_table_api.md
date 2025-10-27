# LinkedHashTable API 문서

**AniVault LinkedHashTable**의 완전한 API 참조 문서입니다.

---

## 📋 목차

1. [클래스 개요](#클래스-개요)
2. [생성자](#생성자)
3. [주요 메서드](#주요-메서드)
4. [속성](#속성)
5. [특수 메서드](#특수-메서드)
6. [사용 예제](#사용-예제)
7. [성능 특성](#성능-특성)
8. [에러 처리](#에러-처리)

---

## 🎯 클래스 개요

### LinkedHashTable

```python
class LinkedHashTable(Generic[K, V]):
    """Hash table that maintains insertion order with O(1) operations.

    This implementation uses chaining for collision resolution and maintains
    insertion order using a doubly linked list overlay. It is specifically
    optimized for file organization workloads with memory efficiency and
    polynomial hash functions for better distribution.

    Features:
    - O(1) average time complexity for put, get, remove operations
    - Maintains insertion order for deterministic iteration
    - Memory-optimized using __slots__ for reduced memory footprint
    - Polynomial hash function with ReDoS prevention
    - Automatic rehashing with 1.5x growth factor
    - Generic type support for keys and values
    """
```

### HashNode

```python
class HashNode(Generic[K, V]):
    """Hash table node with chaining and doubly linked list support.

    This node serves dual purposes:
    1. Chaining: next_in_bucket links nodes in the same hash bucket
    2. Order maintenance: prev_in_order and next_in_order maintain insertion order

    Optimized for memory efficiency using __slots__.
    """
```

---

## 🏗️ 생성자

### LinkedHashTable.__init__

```python
def __init__(self, initial_capacity: int = 64, load_factor: float = 0.8) -> None
```

**설명**: LinkedHashTable 인스턴스를 생성합니다.

**매개변수**:
- `initial_capacity` (int, 기본값: 64): 해시 테이블의 초기 버킷 수
- `load_factor` (float, 기본값: 0.8): 리해싱 전 최대 로드 팩터 (0.0 ~ 1.0)

**예외**:
- `ValueError`: initial_capacity가 양수가 아닌 경우
- `ValueError`: load_factor가 0.0 ~ 1.0 범위를 벗어난 경우

**예제**:
```python
# 기본 설정으로 생성
table = LinkedHashTable()

# 커스텀 설정으로 생성
table = LinkedHashTable(initial_capacity=128, load_factor=0.7)
```

---

## 🔧 주요 메서드

### put

```python
def put(self, key: K, value: V) -> V | None
```

**설명**: 키-값 쌍을 삽입하거나 업데이트합니다.

**매개변수**:
- `key` (K): 삽입/업데이트할 키
- `value` (V): 키와 연결할 값

**반환값**:
- `V | None`: 키가 이미 존재했다면 이전 값, 그렇지 않으면 None

**시간 복잡도**: O(1) 평균, O(n) 최악

**예제**:
```python
table = LinkedHashTable()

# 새 키 삽입
result = table.put("file1", {"size": 1024})
print(result)  # None

# 기존 키 업데이트
result = table.put("file1", {"size": 2048})
print(result)  # {"size": 1024}
```

### get

```python
def get(self, key: K) -> V | None
```

**설명**: 주어진 키에 대한 값을 조회합니다.

**매개변수**:
- `key` (K): 조회할 키

**반환값**:
- `V | None`: 키와 연결된 값, 키가 없으면 None

**시간 복잡도**: O(1) 평균, O(n) 최악

**예제**:
```python
table = LinkedHashTable()
table.put("file1", {"size": 1024})

# 키 조회
value = table.get("file1")
print(value)  # {"size": 1024}

# 존재하지 않는 키 조회
value = table.get("nonexistent")
print(value)  # None
```

### remove

```python
def remove(self, key: K) -> V | None
```

**설명**: 주어진 키의 키-값 쌍을 제거합니다.

**매개변수**:
- `key` (K): 제거할 키

**반환값**:
- `V | None`: 제거된 값, 키가 없으면 None

**시간 복잡도**: O(1) 평균, O(n) 최악

**예제**:
```python
table = LinkedHashTable()
table.put("file1", {"size": 1024})

# 키 제거
removed = table.remove("file1")
print(removed)  # {"size": 1024}

# 존재하지 않는 키 제거
removed = table.remove("nonexistent")
print(removed)  # None
```

### clear

```python
def clear(self) -> None
```

**설명**: 테이블의 모든 키-값 쌍을 제거합니다.

**예제**:
```python
table = LinkedHashTable()
table.put("file1", {"size": 1024})
table.put("file2", {"size": 2048})

print(len(table))  # 2

table.clear()
print(len(table))  # 0
```

---

## 📊 속성

### size

```python
@property
def size(self) -> int
```

**설명**: 테이블에 저장된 키-값 쌍의 수를 반환합니다.

**반환값**: `int` - 현재 요소 수

**예제**:
```python
table = LinkedHashTable()
table.put("file1", {"size": 1024})
table.put("file2", {"size": 2048})

print(table.size)  # 2
```

### capacity

```python
@property
def capacity(self) -> int
```

**설명**: 테이블의 현재 용량(버킷 수)을 반환합니다.

**반환값**: `int` - 현재 용량

**예제**:
```python
table = LinkedHashTable(initial_capacity=128)
print(table.capacity)  # 128
```

### load_factor

```python
@property
def load_factor(self) -> float
```

**설명**: 테이블의 현재 로드 팩터를 반환합니다.

**반환값**: `float` - 현재 로드 팩터

**예제**:
```python
table = LinkedHashTable(load_factor=0.7)
print(table.load_factor)  # 0.7
```

---

## 🎭 특수 메서드

### __len__

```python
def __len__(self) -> int
```

**설명**: 테이블의 크기를 반환합니다. `len(table)`과 동일합니다.

**반환값**: `int` - 테이블 크기

**예제**:
```python
table = LinkedHashTable()
table.put("file1", {"size": 1024})
table.put("file2", {"size": 2048})

print(len(table))  # 2
```

### __contains__

```python
def __contains__(self, key: K) -> bool
```

**설명**: 키가 테이블에 존재하는지 확인합니다. `key in table`과 동일합니다.

**매개변수**:
- `key` (K): 확인할 키

**반환값**: `bool` - 키가 존재하면 True, 그렇지 않으면 False

**예제**:
```python
table = LinkedHashTable()
table.put("file1", {"size": 1024})

print("file1" in table)  # True
print("file2" in table)  # False
```

### __iter__

```python
def __iter__(self) -> Iterator[tuple[K, V]]
```

**설명**: 삽입 순서대로 키-값 쌍을 반복합니다.

**반환값**: `Iterator[tuple[K, V]]` - 키-값 쌍의 반복자

**예제**:
```python
table = LinkedHashTable()
table.put("file1", {"size": 1024})
table.put("file2", {"size": 2048})

for key, value in table:
    print(f"{key}: {value}")
# 출력:
# file1: {"size": 1024}
# file2: {"size": 2048}
```

### __str__

```python
def __str__(self) -> str
```

**설명**: 테이블의 문자열 표현을 반환합니다.

**반환값**: `str` - 테이블의 문자열 표현

**예제**:
```python
table = LinkedHashTable()
table.put("file1", {"size": 1024})
table.put("file2", {"size": 2048})

print(str(table))
# 출력: LinkedHashTable([('file1', {'size': 1024}), ('file2', {'size': 2048})])
```

### __repr__

```python
def __repr__(self) -> str
```

**설명**: 테이블의 상세한 문자열 표현을 반환합니다.

**반환값**: `str` - 테이블의 상세한 문자열 표현

**예제**:
```python
table = LinkedHashTable(initial_capacity=128, load_factor=0.7)
table.put("file1", {"size": 1024})

print(repr(table))
# 출력: LinkedHashTable(capacity=128, size=1, load_factor=0.7)
```

---

## 💡 사용 예제

### 1. 기본 사용법

```python
from anivault.core.data_structures.linked_hash_table import LinkedHashTable

# 테이블 생성
table = LinkedHashTable()

# 값 추가
table.put("video1.mp4", {"size": 1024, "duration": 120})
table.put("audio1.mp3", {"size": 512, "duration": 180})

# 값 조회
video_info = table.get("video1.mp4")
print(video_info)  # {"size": 1024, "duration": 120}

# 순서 유지 확인
for filename, info in table:
    print(f"{filename}: {info}")
```

### 2. 파일 메타데이터 관리

```python
def manage_file_metadata(files: list[str]) -> LinkedHashTable[str, dict]:
    """파일 메타데이터를 관리하는 함수"""
    metadata_table = LinkedHashTable(initial_capacity=len(files))

    for file_path in files:
        # 파일 메타데이터 추출
        metadata = {
            "size": get_file_size(file_path),
            "modified": get_modified_time(file_path),
            "type": get_file_type(file_path)
        }

        metadata_table.put(file_path, metadata)

    return metadata_table

# 사용 예제
files = ["video1.mp4", "audio1.mp3", "document1.pdf"]
metadata = manage_file_metadata(files)

# 메타데이터 조회
for file_path, info in metadata:
    print(f"{file_path}: {info['size']} bytes, {info['type']}")
```

### 3. 해상도 분석 결과 저장

```python
def store_resolution_analysis(results: list[tuple[str, str, str]]) -> LinkedHashTable[tuple[str, int], dict]:
    """해상도 분석 결과를 저장하는 함수"""
    analysis_table = LinkedHashTable()

    for title, episode, resolution in results:
        key = (title, int(episode))
        value = {
            "resolution": resolution,
            "analyzed_at": time.time(),
            "confidence": 0.95
        }

        analysis_table.put(key, value)

    return analysis_table

# 사용 예제
results = [
    ("Attack on Titan", "1", "1080p"),
    ("Attack on Titan", "2", "1080p"),
    ("One Piece", "1", "720p")
]

analysis = store_resolution_analysis(results)

# 분석 결과 조회
for (title, episode), info in analysis:
    print(f"{title} Episode {episode}: {info['resolution']}")
```

---

## ⚡ 성능 특성

### 시간 복잡도

| 연산 | 평균 | 최악 | 설명 |
|------|------|------|------|
| `put(key, value)` | O(1) | O(n) | 해시 충돌 시 체인 탐색 |
| `get(key)` | O(1) | O(n) | 해시 충돌 시 체인 탐색 |
| `remove(key)` | O(1) | O(n) | 해시 충돌 시 체인 탐색 |
| `clear()` | O(1) | O(1) | 모든 포인터 초기화 |
| `__iter__()` | O(n) | O(n) | 모든 요소 순회 |
| `__len__()` | O(1) | O(1) | 크기 필드 반환 |

### 공간 복잡도

| 구성 요소 | 공간 복잡도 | 설명 |
|-----------|-------------|------|
| **버킷 배열** | O(capacity) | 해시 테이블의 기본 구조 |
| **노드** | O(n) | 저장된 키-값 쌍 수에 비례 |
| **연결 포인터** | O(n) | 삽입 순서 유지를 위한 포인터 |

### 메모리 효율성

- **`__slots__` 사용**: 메모리 오버헤드 최소화
- **1.5x 성장 인수**: 메모리 피크 최소화
- **다중 연결 구조**: 삽입 순서 유지를 위한 추가 포인터

---

## 🚨 에러 처리

### ValueError

```python
# 잘못된 초기 용량
try:
    table = LinkedHashTable(initial_capacity=0)
except ValueError as e:
    print(f"Error: {e}")  # Initial capacity must be positive

# 잘못된 로드 팩터
try:
    table = LinkedHashTable(load_factor=1.5)
except ValueError as e:
    print(f"Error: {e}")  # Load factor must be between 0.0 and 1.0
```

### None 값 처리

```python
table = LinkedHashTable()

# 존재하지 않는 키 조회
value = table.get("nonexistent")
if value is not None:
    print(f"Found: {value}")
else:
    print("Key not found")

# 존재하지 않는 키 제거
removed = table.remove("nonexistent")
if removed is not None:
    print(f"Removed: {removed}")
else:
    print("Key not found")
```

### 타입 안전성

```python
from typing import Dict, List

# 명시적 타입 지정
file_metadata: LinkedHashTable[str, Dict[str, any]] = LinkedHashTable()

# 타입 안전성 확보
file_metadata.put("video.mp4", {
    "size": 1024,
    "duration": 120,
    "resolution": "1080p"
})
```

---

## 📚 추가 자료

### 관련 문서
- [LinkedHashTable 사용 가이드](../guides/linkedhashtable_usage_guide.md)
- [성능 개선 리포트](../reports/linkedhashtable_performance_improvement_report.md)
- [마이그레이션 가이드](../migration/checklist.md)

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
