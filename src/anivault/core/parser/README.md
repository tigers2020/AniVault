# Anime Filename Parser

애니메이션 파일명을 파싱하여 제목, 에피소드, 시즌, 품질 등의 메타데이터를 추출하는 파서 시스템입니다.

## 아키텍처 개요

파서 시스템은 다음과 같은 계층 구조로 설계되었습니다:

```
AnimeFilenameParser (메인 인터페이스)
├── AnitopyParser (주요 파서)
│   └── anitopy 라이브러리 래핑
└── FallbackParser (폴백 파서)
    └── Regex 기반 패턴 매칭
```

### 핵심 컴포넌트

#### 1. ParsingResult 데이터 모델 (`models.py`)

모든 파서의 표준 출력 형식입니다.

```python
@dataclass
class ParsingResult:
    title: str                          # 애니메이션 제목
    episode: int | None = None          # 에피소드 번호
    season: int | None = None           # 시즌 번호
    quality: str | None = None          # 해상도 (1080p, 720p 등)
    source: str | None = None           # 출처 (BluRay, WEB-DL 등)
    codec: str | None = None            # 비디오 코덱
    audio: str | None = None            # 오디오 코덱
    release_group: str | None = None    # 릴리스 그룹
    confidence: float = 0.0             # 신뢰도 (0.0-1.0)
    parser_used: str = "unknown"        # 사용된 파서
    other_info: dict[str, Any] = ...    # 기타 정보
```

#### 2. AnimeFilenameParser (메인 파서)

두 파싱 전략을 통합한 메인 인터페이스입니다.

**파싱 전략:**
1. **Primary**: AnitopyParser로 먼저 시도
2. **Fallback**: 결과가 불충분하면 FallbackParser 사용
3. **Best Result**: 더 나은 결과를 반환

#### 3. AnitopyParser (주요 파서)

`anitopy` 라이브러리를 래핑하여 표준 `ParsingResult` 형식으로 변환합니다.

**특징:**
- 고정밀도 파싱 (대부분의 표준 형식 처리)
- 자동 메타데이터 추출
- 신뢰도 점수 자동 계산

#### 4. FallbackParser (폴백 파서)

Regex 기반 파싱으로 anitopy가 실패한 경우를 처리합니다.

**지원 패턴:**
- `[Group] Title - Episode [Quality]`
- `Title S##E##`
- `Title - ##`
- `Title EP##`
- `Title_##`
- `Title.##`

## 사용 방법

### 기본 사용

```python
from anivault.core.parser import AnimeFilenameParser

# 파서 초기화
parser = AnimeFilenameParser()

# 파일명 파싱
filename = "[SubsPlease] Jujutsu Kaisen - 24 (1080p) [E82B1F6A].mkv"
result = parser.parse(filename)

# 결과 확인
print(f"Title: {result.title}")          # "Jujutsu Kaisen"
print(f"Episode: {result.episode}")      # 24
print(f"Quality: {result.quality}")      # "1080p"
print(f"Confidence: {result.confidence}") # 0.92
print(f"Parser: {result.parser_used}")   # "anitopy"
```

### 배치 처리

```python
filenames = [
    "[HorribleSubs] One Piece - 1000 [720p].mkv",
    "Attack on Titan S02E05.mkv",
    "Demon Slayer - 26 [1080p].mp4",
]

parser = AnimeFilenameParser()

for filename in filenames:
    result = parser.parse(filename)
    if result.is_valid():
        print(f"{result.title} - Ep {result.episode}")
```

### 검증 및 신뢰도 확인

```python
result = parser.parse(filename)

# 결과 유효성 검증
if result.is_valid():
    print("✅ Valid result")

# 에피소드 정보 확인
if result.has_episode_info():
    print(f"Episode: {result.episode}")

# 신뢰도 확인
if result.confidence >= 0.8:
    print("🎯 High confidence")
elif result.confidence >= 0.5:
    print("⚠️  Medium confidence")
else:
    print("❌ Low confidence")
```

## 성능 특징

### 벤치마크 결과

- **처리 속도**: 2,783 files/sec (목표: 1,000 files/sec)
- **평균 처리 시간**: 0.359ms per file
- **정확도**: 100% (120개 실세계 테스트 케이스)
- **견고성**: 900+ Hypothesis 퍼징 테스트 통과

### 최적화 특징

1. **Pre-compiled Regex**: FallbackParser의 모든 정규표현식 사전 컴파일
2. **Lazy Loading**: anitopy 없어도 fallback으로 동작
3. **Early Exit**: Primary parser 성공 시 fallback 건너뜀
4. **Efficient Type Conversion**: 최소한의 문자열 변환

## 테스트 커버리지

```
src/anivault/core/parser/
├── models.py              100% coverage (11 tests)
├── anitopy_parser.py       87% coverage (20 tests)
├── fallback_parser.py      96% coverage (30 tests)
└── anime_parser.py         89% coverage (27 tests)

Total: 88 unit tests + 9 property tests (Hypothesis)
```

## 에러 처리

파서는 모든 입력에 대해 안전하게 동작합니다:

```python
# 빈 문자열
result = parser.parse("")
assert isinstance(result, ParsingResult)

# 잘못된 형식
result = parser.parse("random_garbage.txt")
assert result.confidence < 0.5

# 예외 발생하지 않음
try:
    result = parser.parse(any_string)
except Exception:
    assert False, "Parser should never crash"
```

## 확장 및 커스터마이징

### 새로운 Regex 패턴 추가

`FallbackParser`에 패턴을 추가하려면:

```python
# src/anivault/core/parser/fallback_parser.py

PATTERNS: list[Pattern[str]] = [
    # ... 기존 패턴들 ...

    # 새 패턴 추가
    re.compile(
        r"^(?P<title>.+?)\s+Episode\s+(?P<episode>\d+)",
        re.IGNORECASE
    ),
]
```

### 신뢰도 계산 커스터마이징

`_calculate_confidence` 메서드를 수정하여 신뢰도 계산 로직을 조정할 수 있습니다.

## 참고 자료

- [anitopy 라이브러리](https://github.com/igorcmoura/anitopy)
- [Hypothesis 테스팅](https://hypothesis.readthedocs.io/)
- [Python Regex 문서](https://docs.python.org/3/library/re.html)

## 라이선스

MIT License
