# 💻 Development - 개발 가이드 및 도구

AniVault 프로젝트의 개발 과정, 도구 사용법, API 가이드 관련 문서들입니다.

## 📁 문서 목록

### 🔧 개발 도구 및 가이드

#### [리팩토링 예시](./refactoring-examples.md)
- **목적**: 코드 리팩토링 모범 사례 및 예시
- **대상**: 모든 개발자
- **주요 내용**:
  - 리팩토링 패턴
  - 코드 개선 예시
  - 성능 최적화
  - 가독성 향상

#### [개발 계획](./development-plan.md)
- **목적**: 프로젝트 개발 로드맵 및 계획
- **대상**: 프로젝트 매니저, 개발자
- **주요 내용**:
  - 개발 단계별 계획
  - 마일스톤 및 데드라인
  - 리소스 할당
  - 위험 관리

#### [TMDB Rate Limiting 아키텍처](./tmdb-rate-limiting-architecture.md)
- **목적**: TMDB API 레이트 리미팅 상세 아키텍처
- **대상**: 백엔드 개발자, API 통합 담당자
- **주요 내용**:
  - Token Bucket Rate Limiter
  - Semaphore Manager
  - Rate Limiting State Machine
  - TMDB Client 통합

### 🌐 API 및 통합

#### [TMDB API 키 가이드](./tmdb-api-key-guide.md)
- **목적**: TMDB API 키 설정 및 사용 가이드
- **대상**: 개발자, 사용자
- **주요 내용**:
  - API 키 발급 방법
  - 환경 설정
  - 보안 고려사항
  - 사용 예시

#### [TMDB API 검증 결과](./tmdb-api-validation-results.md)
- **목적**: TMDB API 통합 검증 결과
- **대상**: 개발자, QA 엔지니어
- **주요 내용**:
  - API 호출 테스트 결과
  - 성능 벤치마크
  - 에러 처리 검증
  - 레이트 리미팅 테스트

## 🎯 개발 환경 설정

### 필수 도구
```bash
# Python 3.8+ 설치
python --version

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 개발 도구
```bash
# 코드 품질 도구
pip install black ruff mypy pytest

# 개발 도구
pip install pre-commit bandit safety

# 테스트 도구
pip install pytest-cov pytest-mock
```

### IDE 설정
```json
// VS Code settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

## 🛠️ 개발 워크플로우

### 1. 개발 시작
```bash
# 브랜치 생성
git checkout -b feature/new-feature

# 개발 환경 설정
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 코드 개발
```bash
# 코드 작성
# ...

# 코드 품질 검사
black src/
ruff check src/
mypy src/

# 테스트 실행
pytest tests/
```

### 3. 커밋 및 푸시
```bash
# 변경사항 스테이징
git add .

# 커밋 (Conventional Commits)
git commit -m "feat(matching): add new algorithm"

# 푸시
git push origin feature/new-feature
```

### 4. 코드 리뷰
- **자동 검사**: CI/CD 파이프라인 실행
- **동료 리뷰**: Pull Request 생성
- **품질 검증**: 코드 품질 기준 확인

## 📊 개발 품질 기준

### 코드 품질
- **린터 경고**: 0개
- **타입 체크**: 100% 통과
- **테스트 커버리지**: 80% 이상
- **코드 복잡도**: 10 이하

### 성능 기준
- **시작 시간**: 3초 이내
- **메모리 사용량**: 500MB 이하
- **API 응답 시간**: 5초 이내
- **파일 처리 속도**: 1000개/분 이상

### 보안 기준
- **보안 취약점**: 0개
- **의존성 보안**: 최신 버전 사용
- **API 키 보안**: 환경변수 사용
- **입력 검증**: 모든 사용자 입력 검증

## 🔧 개발 도구 활용

### 코드 품질 도구
```bash
# 코드 포맷팅
black src/anivault/

# 린팅
ruff check src/anivault/

# 타입 체킹
mypy src/anivault/

# 보안 스캔
bandit -r src/anivault/
```

### 테스트 도구
```bash
# 단위 테스트
pytest tests/unit/

# 통합 테스트
pytest tests/integration/

# 커버리지 측정
pytest --cov=src/anivault tests/

# 성능 테스트
pytest tests/performance/
```

### 디버깅 도구
```bash
# 로그 레벨 설정
export ANIVAULT_LOG_LEVEL=DEBUG

# 디버그 모드 실행
python -m anivault --debug scan /path/to/files

# 프로파일링
python -m cProfile -m anivault scan /path/to/files
```

## 🌐 API 개발 가이드

### TMDB API 통합
```python
# API 클라이언트 설정
from anivault.services.metadata_enricher import MetadataEnricher

enricher = MetadataEnricher(api_key="your-api-key")
result = enricher.search_movie("Movie Title", 2020)
```

### API 보안
```python
# 환경변수에서 API 키 로드
import os
from anivault.config.settings import Settings

settings = Settings()
api_key = settings.tmdb_api_key
```

### 에러 처리
```python
# API 에러 처리
try:
    result = enricher.search_movie(title, year)
except APIError as e:
    logger.error(f"API error: {e}")
    raise
except RateLimitError as e:
    logger.warning(f"Rate limit exceeded: {e}")
    # 재시도 로직
```

## 📈 성능 최적화

### 메모리 최적화
```python
# 메모리 효율적인 파일 처리
def process_files_memory_efficient(file_paths):
    """메모리 효율적인 파일 처리."""
    for file_path in file_paths:
        with open(file_path, 'r') as f:
            yield process_file(f)
```

### 캐싱 전략
```python
# 결과 캐싱
from functools import lru_cache

@lru_cache(maxsize=1000)
def expensive_calculation(data):
    """비용이 큰 계산 결과 캐싱."""
    return complex_calculation(data)
```

### 병렬 처리
```python
# 멀티프로세싱 활용
from multiprocessing import Pool

def process_files_parallel(file_paths):
    """병렬 파일 처리."""
    with Pool() as pool:
        results = pool.map(process_file, file_paths)
    return results
```

## 🔄 지속적 개선

### 코드 리뷰
- **자동 검사**: CI/CD 파이프라인
- **동료 리뷰**: Pull Request 리뷰
- **품질 게이트**: 품질 기준 미달 시 병합 차단

### 성능 모니터링
- **벤치마크**: 정기적인 성능 테스트
- **프로파일링**: 성능 병목 지점 식별
- **최적화**: 지속적인 성능 개선

### 기술 부채 관리
- **정기 검토**: 분기별 기술 부채 검토
- **리팩토링**: 지속적인 코드 개선
- **문서화**: 코드 문서화 및 주석 개선

---

**문서 버전**: 1.0  
**최종 업데이트**: 2024-01-XX  
**관리자**: AniVault 개발팀 (윤도현)
