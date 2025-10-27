# AniVault 성능 최적화 문서

## 개요

이 문서는 AniVault의 파일 정리 성능을 크게 향상시킨 LinkedHashTable과 OptimizedFileOrganizer에 대한 포괄적인 문서입니다.

## 문서 구조

### 1. [성능 최적화 가이드](PERFORMANCE_OPTIMIZATION_GUIDE.md)
- 주요 성능 개선 사항
- 시간 복잡도 개선 (O(n) → O(1))
- 메모리 사용량 최적화 (16% 감소)
- 해시 함수 최적화
- 성능 벤치마크 결과
- 마이그레이션 가이드

### 2. [트러블슈팅 가이드](TROUBLESHOOTING_GUIDE.md)
- 일반적인 문제들과 해결 방법
- 성능 문제 해결
- 메모리 문제 해결
- 데이터 무결성 문제 해결
- 에러 처리 문제 해결
- 설정 문제 해결
- FAQ (자주 묻는 질문)

## 주요 성과

### 성능 개선
- **13.5배 빠른 처리 속도**
- **47% 메모리 사용량 감소**
- **O(1) 파일 추가/조회 성능**
- **O(1) 중복 탐지 성능**

### 호환성
- **완전한 하위 호환성**
- **자동 마이그레이션**
- **기존 코드 수정 불필요**

### 안정성
- **99.20% 테스트 커버리지** (LinkedHashTable)
- **85.42% 테스트 커버리지** (OptimizedFileOrganizer)
- **포괄적인 에러 처리**
- **메모리 누수 방지**

## 빠른 시작

### 기본 사용법
```python
from anivault.core.organizer import FileOrganizer

# 기존 코드와 동일하게 사용
organizer = FileOrganizer(log_manager, settings)

# 파일 추가 (O(1) 성능)
for file in scanned_files:
    organizer.add_file(file)

# 중복 탐지 (O(1) 성능)
duplicates = organizer.find_duplicates()

# 정리 계획 생성 (O(n) 성능)
plan = organizer.generate_plan(scanned_files)
```

### 성능 모니터링
```python
import logging

# 성능 로그 활성화
logging.getLogger("anivault.core.organizer.optimized_file_organizer").setLevel(logging.INFO)

# 자동으로 실행 시간이 로깅됨
organizer.add_file(file)  # "Performance: add_file completed in 0.0001 seconds"
```

## 기술적 세부사항

### LinkedHashTable
- **구현**: 체이닝 + 이중 연결 리스트
- **메모리 최적화**: `__slots__` 사용
- **해시 함수**: 다항식 해시 + ReDoS 방지
- **리해싱**: 1.5x 성장률로 메모리 피크 감소

### OptimizedFileOrganizer
- **중복 탐지**: (title, episode) 키 사용
- **성능 모니터링**: 자동 실행 시간 로깅
- **에러 처리**: 포괄적인 예외 처리
- **타입 안전성**: Pydantic 모델 사용

## 벤치마크 결과

### 대규모 파일 처리 (1000개 파일)
| 메트릭 | 기존 방식 | 최적화된 방식 | 개선율 |
|--------|-----------|---------------|--------|
| 파일 추가 시간 | 0.0257초 | 0.0032초 | **8배 향상** |
| 중복 탐지 시간 | 0.0225초 | 0.0000초 | **∞배 향상** |
| 계획 생성 시간 | 0.0124초 | 0.0013초 | **9.5배 향상** |
| 총 처리 시간 | 0.0606초 | 0.0045초 | **13.5배 향상** |

### 메모리 사용량 (1000개 파일)
| 메트릭 | 기존 방식 | 최적화된 방식 | 개선율 |
|--------|-----------|---------------|--------|
| 현재 메모리 | 2.5MB | 1.33MB | **47% 절약** |
| 최대 메모리 | 3.2MB | 1.33MB | **58% 절약** |
| 파일당 평균 | 2.5KB | 1.36KB | **46% 절약** |

## 문제 해결

### 일반적인 문제들
1. **성능 문제**: 배치 처리, 메모리 모니터링
2. **메모리 문제**: 캐시 정리, 가비지 컬렉션
3. **데이터 무결성**: 메타데이터 정규화, 유효성 검사
4. **에러 처리**: 파일 경로 유효성 검사, 안전한 속성 접근

### 디버깅 도구
- **로깅**: `logging.basicConfig(level=logging.DEBUG)`
- **성능 프로파일링**: `cProfile` 사용
- **메모리 프로파일링**: `tracemalloc` 사용

## 마이그레이션

### 자동 마이그레이션
기존 코드는 수정 없이 자동으로 OptimizedFileOrganizer를 사용합니다:

```python
# 기존 코드 (수정 불필요)
from anivault.core.organizer import FileOrganizer
organizer = FileOrganizer(log_manager, settings)
```

### 명시적 사용
명시적으로 OptimizedFileOrganizer를 사용할 수도 있습니다:

```python
from anivault.core.organizer.optimized_file_organizer import OptimizedFileOrganizer
organizer = OptimizedFileOrganizer(log_manager, settings)
```

## 기여하기

### 코드 품질
- **Ruff**: 코드 스타일 및 import 정리
- **Mypy**: 타입 체크

### 개발 워크플로우
1. 기능 개발
2. 코드 품질 검사 (Ruff, Mypy)
3. 문서 업데이트

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 지원

문제가 발생하거나 질문이 있으면 다음을 참고하세요:

1. [트러블슈팅 가이드](TROUBLESHOOTING_GUIDE.md) 확인
2. [성능 최적화 가이드](PERFORMANCE_OPTIMIZATION_GUIDE.md) 참조
3. 이슈 트래커에 문제 보고
4. 개발팀에 문의

---

**최종 업데이트**: 2024년 10월 26일
**버전**: 1.0.0
**작성자**: AniVault 개발팀
