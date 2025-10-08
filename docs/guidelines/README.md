# 📋 Guidelines - 가이드라인 및 표준

AniVault 프로젝트의 코딩 표준, 품질 가이드라인, 모범 사례 관련 문서들입니다.

## 📁 문서 목록

### 📝 코딩 표준 및 품질

#### [코드 품질 가이드](./code-quality-guide.md)
- **목적**: AniVault 프로젝트의 코드 품질 기준 및 가이드라인
- **대상**: 모든 개발자
- **주요 내용**:
  - 코딩 컨벤션
  - 코드 품질 기준
  - 리팩토링 가이드
  - 성능 최적화

#### [AI 코드 생성 가이드라인](./ai-code-generation-guidelines.md)
- **목적**: AI 도구를 활용한 코드 생성 시 준수해야 할 가이드라인
- **대상**: AI 어시스턴트, 개발자
- **주요 내용**:
  - AI 코드 생성 원칙
  - 품질 보증 방법
  - 검증 절차
  - 모범 사례

## 🎯 코딩 표준

### Python 코딩 컨벤션

#### 1. 코드 스타일
```python
# ✅ DO: 명확하고 읽기 쉬운 코드
def calculate_matching_score(
    candidate: MediaItem, 
    target: MediaItem
) -> float:
    """매칭 점수 계산."""
    title_similarity = jaccard_similarity(
        candidate.title, 
        target.title
    )
    year_match = 1.0 if candidate.year == target.year else 0.0
    
    return (title_similarity * 0.6 + year_match * 0.4)

# ❌ DON'T: 모호하고 읽기 어려운 코드
def calc(c, t):
    return jaccard(c.title, t.title) * 0.6 + (1 if c.year == t.year else 0) * 0.4
```

#### 2. 타입 힌트
```python
# ✅ DO: 명확한 타입 힌트
from typing import List, Optional, Dict, Any

def process_files(
    file_paths: List[str],
    options: Optional[Dict[str, Any]] = None
) -> List[ProcessedFile]:
    """파일 처리 함수."""
    pass

# ❌ DON'T: 타입 힌트 없음
def process_files(file_paths, options=None):
    pass
```

#### 3. 독스트링
```python
# ✅ DO: Google 스타일 독스트링
def match_media_files(
    source_path: str,
    target_path: str,
    algorithm: str = "default"
) -> List[MatchResult]:
    """
    미디어 파일 매칭.
    
    Args:
        source_path: 소스 파일 경로
        target_path: 타겟 파일 경로
        algorithm: 매칭 알고리즘 ('default', 'advanced')
        
    Returns:
        매칭 결과 리스트
        
    Raises:
        FileNotFoundError: 파일을 찾을 수 없을 때
        ValueError: 잘못된 알고리즘 이름일 때
        
    Example:
        >>> results = match_media_files('/movies', '/target')
        >>> print(len(results))
        10
    """
    pass
```

### 코드 품질 기준

#### 1. 함수 길이
- **최대 길이**: 50줄
- **권장 길이**: 20줄 이하
- **복잡도**: 순환 복잡도 10 이하

#### 2. 클래스 설계
- **단일 책임**: 하나의 클래스는 하나의 책임만
- **응집도**: 높은 응집도, 낮은 결합도
- **인터페이스**: 명확한 공개 인터페이스

#### 3. 에러 처리
```python
# ✅ DO: 구체적인 예외 처리
def load_config(config_path: str) -> Config:
    """설정 파일 로드."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return Config(**data)
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")
    except ValidationError as e:
        raise ConfigError(f"Invalid config: {e}")

# ❌ DON'T: 일반적인 예외 처리
def load_config(config_path: str) -> Config:
    try:
        # ... 코드 ...
        return config
    except Exception as e:
        print(f"Error: {e}")
        return None
```

## 🤖 AI 코드 생성 가이드라인

### AI 도구 활용 원칙

#### 1. 코드 생성 전 검증
```markdown
**체크리스트:**
- [ ] 기존 코드베이스 분석 완료
- [ ] 요구사항 명확히 정의
- [ ] 아키텍처 패턴 확인
- [ ] 테스트 전략 수립
```

#### 2. 생성된 코드 검증
```markdown
**검증 항목:**
- [ ] 타입 힌트 포함
- [ ] 독스트링 작성
- [ ] 에러 처리 포함
- [ ] 테스트 케이스 작성
- [ ] 성능 영향 분석
```

#### 3. 품질 보증
```bash
# 자동 검증 도구 실행
black src/                    # 코드 포맷팅
ruff check src/              # 린팅
mypy src/                    # 타입 체킹
pytest tests/                # 테스트 실행
bandit -r src/               # 보안 스캔
```

### AI 코드 생성 모범 사례

#### 1. 점진적 개발
```python
# 1단계: 기본 구조
def calculate_score(candidate, target):
    """기본 점수 계산."""
    pass

# 2단계: 타입 힌트 추가
def calculate_score(candidate: MediaItem, target: MediaItem) -> float:
    """기본 점수 계산."""
    pass

# 3단계: 구현 추가
def calculate_score(candidate: MediaItem, target: MediaItem) -> float:
    """기본 점수 계산."""
    title_sim = jaccard_similarity(candidate.title, target.title)
    year_match = 1.0 if candidate.year == target.year else 0.0
    return title_sim * 0.6 + year_match * 0.4

# 4단계: 에러 처리 추가
def calculate_score(candidate: MediaItem, target: MediaItem) -> float:
    """기본 점수 계산."""
    if not candidate or not target:
        raise ValueError("Both candidate and target must be provided")
    
    title_sim = jaccard_similarity(candidate.title, target.title)
    year_match = 1.0 if candidate.year == target.year else 0.0
    return title_sim * 0.6 + year_match * 0.4
```

#### 2. 테스트 우선 개발
```python
# 테스트 케이스 먼저 작성
def test_calculate_score():
    """점수 계산 테스트."""
    candidate = MediaItem("Movie A", 2020, ["Action"])
    target = MediaItem("Movie A", 2020, ["Action"])
    
    score = calculate_score(candidate, target)
    assert score == 1.0  # 완벽한 매칭

# 구현 후 테스트 실행
pytest tests/test_matching.py::test_calculate_score
```

#### 3. 문서화 우선
```python
# 독스트링 먼저 작성
def process_media_files(
    file_paths: List[str],
    options: ProcessingOptions
) -> List[ProcessedFile]:
    """
    미디어 파일 처리.
    
    Args:
        file_paths: 처리할 파일 경로 리스트
        options: 처리 옵션
        
    Returns:
        처리된 파일 리스트
        
    Raises:
        FileNotFoundError: 파일을 찾을 수 없을 때
        ProcessingError: 처리 중 오류 발생 시
    """
    # 구현...
```

## 📊 품질 지표

### 코드 품질 지표
- **린터 경고**: 0개
- **타입 체크**: 100% 통과
- **테스트 커버리지**: 80% 이상
- **코드 복잡도**: 10 이하

### AI 코드 생성 품질
- **자동 검증 통과율**: 100%
- **수동 리뷰 필요**: 최소화
- **성능 회귀**: 5% 이내
- **보안 취약점**: 0개

### 지속적 개선
- **코드 리뷰**: 모든 변경사항 리뷰
- **정적 분석**: 자동화된 품질 검사
- **성능 모니터링**: 지속적인 성능 측정
- **피드백 루프**: 개발자 피드백 수집

## 🔄 가이드라인 개선

### 정기 검토
- **분기별**: 가이드라인 효과성 평가
- **프로젝트 완료 시**: 개선점 도출
- **연간**: 전체 가이드라인 재검토

### 피드백 수집
- **개발자 피드백**: 가이드라인 사용 경험
- **품질 지표**: 코드 품질 메트릭
- **AI 도구 피드백**: AI 생성 코드 품질

### 지속적 학습
- **모범 사례**: 성공 사례 수집
- **실패 사례**: 문제 상황 분석
- **도구 개선**: AI 도구 활용법 개선

---

**문서 버전**: 1.0  
**최종 업데이트**: 2024-01-XX  
**관리자**: AniVault 품질팀
