# AI 코드 생성 가이드라인

이 문서는 AI를 활용한 코드 생성 시 AniVault 프로젝트의 품질 기준을 준수하는 방법을 안내합니다. AI가 생성하는 코드가 팀의 개발 표준을 만족하고 유지보수 가능한 품질을 갖추도록 돕는 것을 목표로 합니다.

## 목차

1. [AI 코드 생성 시 준수사항](#ai-코드-생성-시-준수사항)
2. [품질 검증 체크리스트](#품질-검증-체크리스트)
3. [자동화 도구 사용법](#자동화-도구-사용법)
4. [프롬프트 작성 가이드](#프롬프트-작성-가이드)
5. [코드 리뷰 프로세스](#코드-리뷰-프로세스)
6. [팀 협업 가이드라인](#팀-협업-가이드라인)
7. [지속적 개선 방법](#지속적-개선-방법)

## AI 코드 생성 시 준수사항

### 핵심 원칙

AI가 코드를 생성할 때는 다음 4가지 핵심 원칙을 반드시 준수해야 합니다:

1. **One Source of Truth**: 중복 정의 금지, 중앙 상수 사용
2. **매직 값 제거**: 하드코딩된 값 상수화
3. **함수 단일 책임**: 하나의 명확한 책임만 가진 함수
4. **구조적 에러 처리**: AniVaultError 기반 에러 처리

### 필수 컨텍스트 제공

AI에게 코드 생성을 요청할 때는 다음 정보를 반드시 포함해야 합니다:

#### 1. 프로젝트 컨텍스트
```
AniVault 프로젝트에서 작업 중입니다. 다음 원칙을 준수해주세요:
- One Source of Truth: src/anivault/shared/constants/에서 상수 import
- 매직 값 금지: 모든 하드코딩된 값은 상수로 추출
- 함수 단일 책임: 80줄 이하, 하나의 명확한 책임
- 구조적 에러 처리: AniVaultError, ErrorCode, ErrorContext 사용
```

#### 2. 기존 코드 패턴 참조
```
기존 코드 패턴을 참조하세요:
- 상수: anivault.shared.constants에서 import
- 에러 처리: anivault.shared.errors의 AniVaultError 사용
- 로깅: 구조적 로깅 패턴 적용
- 타입 힌트: 모든 함수에 타입 힌트 필수
```

#### 3. 구체적인 요구사항
```
구현해야 할 기능:
- [구체적인 기능 설명]
- [입력/출력 형식]
- [에러 처리 요구사항]
- [성능 요구사항]
```

### 금지사항

AI 코드 생성 시 다음 사항은 절대 금지됩니다:

#### ❌ 절대 금지
- 중복 정의 (여러 파일에서 동일한 타입/상수 정의)
- 매직 값 사용 (하드코딩된 문자열, 숫자)
- 일반 Exception 사용
- 80줄 초과 함수
- 타입 힌트 누락
- 독스트링 누락

#### ❌ 예시
```python
# ❌ BAD: 금지된 패턴들
def bad_function():
    if status == "completed":  # ❌ 매직 문자열
        return handle_completion()

    for i in range(3):  # ❌ 매직 넘버
        try:
            # 작업
            pass
        except Exception:  # ❌ 일반 Exception
            pass  # ❌ 예외 삼키기
```

## 품질 검증 체크리스트

### 자동 검증 항목

AI가 생성한 코드는 다음 자동화 도구로 검증해야 합니다:

#### 1. One Source of Truth 준수 확인
```bash
# 중복 정의 검사
python scripts/check_duplicates.py

# 매직 값 탐지
python scripts/detect_magic_values.py
```

**검증 기준:**
- [ ] 중복 정의 0개
- [ ] 매직 값 0개
- [ ] 모든 상수가 shared/constants에서 import

#### 2. 함수 단일 책임 원칙 확인
```bash
# 함수 길이 검사
python scripts/validate_function_length.py
```

**검증 기준:**
- [ ] 모든 함수가 80줄 이하
- [ ] 각 함수가 하나의 명확한 책임
- [ ] 계층이 적절히 분리됨

#### 3. 에러 처리 패턴 확인
```bash
# 에러 처리 검증
python scripts/validate_error_handling.py
```

**검증 기준:**
- [ ] 일반 Exception 사용 없음
- [ ] AniVaultError 계층 사용
- [ ] ErrorContext 포함
- [ ] 사용자 친화적 메시지 제공

#### 4. 코드 품질 종합 검증
```bash
# 종합 품질 검증
python scripts/validate_code_quality.py
```

**검증 기준:**
- [ ] 품질 점수 80점 이상
- [ ] 모든 자동화 도구 통과
- [ ] 테스트 코드 포함

### 수동 검증 항목

자동화 도구로 검증할 수 없는 항목들:

#### 1. 비즈니스 로직 정확성
- [ ] 요구사항을 정확히 구현했는가?
- [ ] 엣지 케이스를 고려했는가?
- [ ] 성능 요구사항을 만족하는가?

#### 2. 코드 가독성
- [ ] 변수명이 의미 있는가?
- [ ] 함수명이 기능을 명확히 표현하는가?
- [ ] 주석이 적절한가?

#### 3. 테스트 커버리지
- [ ] 단위 테스트가 포함되어 있는가?
- [ ] 통합 테스트가 필요한가?
- [ ] 에러 케이스가 테스트되었는가?

## 자동화 도구 사용법

### Pre-commit 훅 설정

AI가 생성한 코드를 커밋하기 전에 자동으로 검증합니다:

```bash
# Pre-commit 설치
pip install pre-commit

# 훅 설정
pre-commit install

# 수동 실행
pre-commit run --all-files
```

### CI/CD 파이프라인 연동

GitHub Actions를 통한 자동 검증:

```yaml
# .github/workflows/ai-code-quality.yml
name: AI Code Quality Check

on: [push, pull_request]

jobs:
  ai-quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run AI quality checks
        run: |
          echo "🔍 Running AI Code Quality Validation..."
          python scripts/validate_code_quality.py
          python scripts/detect_magic_values.py
          python scripts/check_duplicates.py
          python scripts/validate_function_length.py
          python scripts/validate_error_handling.py
          echo "✅ AI Code Quality validation passed!"

      - name: Calculate quality score
        run: |
          python scripts/calculate_quality_score.py
```

### 품질 점수 계산

```python
# scripts/calculate_quality_score.py
def calculate_ai_quality_score() -> int:
    """AI 생성 코드 품질 점수 계산 (0-100)."""
    score = 100

    # 매직 값 감점 (각 5점)
    magic_values = detect_magic_values()
    score -= len(magic_values) * 5

    # 중복 정의 감점 (각 10점)
    duplicates = check_duplicates()
    score -= len(duplicates) * 10

    # 긴 함수 감점 (각 3점)
    long_functions = validate_function_length()
    score -= len(long_functions) * 3

    # 에러 처리 미흡 감점 (각 5점)
    error_issues = validate_error_handling()
    score -= len(error_issues) * 5

    # 타입 힌트 누락 감점 (각 2점)
    missing_type_hints = check_type_hints()
    score -= len(missing_type_hints) * 2

    return max(0, score)

def get_quality_grade(score: int) -> str:
    """품질 점수에 따른 등급 반환."""
    if score >= 90:
        return "A+ (우수)"
    elif score >= 80:
        return "A (양호)"
    elif score >= 70:
        return "B (보통)"
    elif score >= 60:
        return "C (개선 필요)"
    else:
        return "D (품질 불량)"
```

## 프롬프트 작성 가이드

### 효과적인 프롬프트 구조

AI에게 코드 생성을 요청할 때는 다음 구조를 따르세요:

#### 1. 컨텍스트 설정
```
AniVault 프로젝트에서 [기능명]을 구현해야 합니다.
프로젝트의 품질 기준을 준수해주세요:
- One Source of Truth: src/anivault/shared/constants/에서 상수 import
- 매직 값 금지: 모든 하드코딩된 값은 상수로 추출
- 함수 단일 책임: 80줄 이하, 하나의 명확한 책임
- 구조적 에러 처리: AniVaultError, ErrorCode, ErrorContext 사용
```

#### 2. 구체적인 요구사항
```
구현해야 할 기능:
- 입력: [구체적인 입력 형식]
- 출력: [구체적인 출력 형식]
- 에러 처리: [구체적인 에러 케이스]
- 성능: [성능 요구사항]
```

#### 3. 기존 코드 참조
```
기존 코드 패턴을 참조하세요:
- [관련 파일 경로]의 [함수명] 함수
- [관련 파일 경로]의 [클래스명] 클래스
- [관련 파일 경로]의 [에러 처리 패턴]
```

#### 4. 검증 요구사항
```
생성된 코드는 다음을 포함해야 합니다:
- 타입 힌트
- Google 스타일 독스트링
- 단위 테스트
- 에러 처리
- 로깅
```

### 프롬프트 예시

#### ✅ 좋은 프롬프트 예시
```
AniVault 프로젝트에서 파일 메타데이터 검증 기능을 구현해야 합니다.

프로젝트의 품질 기준을 준수해주세요:
- One Source of Truth: src/anivault/shared/constants/에서 상수 import
- 매직 값 금지: 모든 하드코딩된 값은 상수로 추출
- 함수 단일 책임: 80줄 이하, 하나의 명확한 책임
- 구조적 에러 처리: AniVaultError, ErrorCode, ErrorContext 사용

구현해야 할 기능:
- 입력: 파일 경로 (str)
- 출력: 검증 결과 (Dict[str, Any])
- 에러 처리: 파일 없음, 권한 없음, 형식 오류
- 성능: 1초 이내 처리

기존 코드 패턴을 참조하세요:
- src/anivault/shared/errors.py의 AniVaultError 계층
- src/anivault/shared/constants/file_formats.py의 파일 형식 상수
- src/anivault/core/parser.py의 파일 파싱 패턴

생성된 코드는 다음을 포함해야 합니다:
- 타입 힌트
- Google 스타일 독스트링
- 단위 테스트
- 에러 처리
- 로깅
```

#### ❌ 나쁜 프롬프트 예시
```
파일 검증 함수 만들어줘
```

### 프롬프트 개선 방법

#### 1. 구체성 향상
- **Before**: "에러 처리해줘"
- **After**: "AniVaultError를 사용하여 파일 없음, 권한 없음, 형식 오류를 각각 다른 에러 코드로 처리해주세요"

#### 2. 컨텍스트 제공
- **Before**: "함수 만들어줘"
- **After**: "src/anivault/core/parser.py의 parse_anime_filename 함수와 유사한 패턴으로 구현해주세요"

#### 3. 검증 기준 명시
- **Before**: "테스트 포함해줘"
- **After**: "pytest를 사용하여 성공 케이스, 실패 케이스, 엣지 케이스를 모두 테스트하는 단위 테스트를 포함해주세요"

## 코드 리뷰 프로세스

### AI 생성 코드 리뷰 체크리스트

#### 1. 품질 기준 준수
- [ ] One Source of Truth 준수
- [ ] 매직 값 제거
- [ ] 함수 단일 책임 원칙
- [ ] 구조적 에러 처리

#### 2. 자동화 도구 통과
- [ ] validate_code_quality.py 통과
- [ ] detect_magic_values.py 통과
- [ ] check_duplicates.py 통과
- [ ] validate_function_length.py 통과
- [ ] validate_error_handling.py 통과

#### 3. 코드 품질
- [ ] 타입 힌트 포함
- [ ] 독스트링 포함
- [ ] 테스트 코드 포함
- [ ] 로깅 포함

#### 4. 비즈니스 로직
- [ ] 요구사항 정확히 구현
- [ ] 엣지 케이스 고려
- [ ] 성능 요구사항 만족

### 리뷰 프로세스

#### 1단계: 자동 검증
```bash
# 자동화 도구 실행
python scripts/validate_code_quality.py
python scripts/detect_magic_values.py
python scripts/check_duplicates.py
python scripts/validate_function_length.py
python scripts/validate_error_handling.py

# 품질 점수 계산
python scripts/calculate_quality_score.py
```

#### 2단계: 수동 검토
- 코드 가독성 검토
- 비즈니스 로직 정확성 검토
- 테스트 커버리지 검토

#### 3단계: 피드백 제공
- 개선 사항 명시
- 구체적인 수정 방향 제시
- 재검증 요구

#### 4단계: 승인/거부
- 품질 기준 충족 시 승인
- 미충족 시 수정 요구

## 팀 협업 가이드라인

### AI 코드 생성 정책

#### 1. 사용 범위
- **허용**: 반복적인 코드, 유틸리티 함수, 테스트 코드
- **제한**: 핵심 비즈니스 로직, 복잡한 알고리즘
- **금지**: 보안 관련 코드, 성능 크리티컬 코드

#### 2. 검증 의무
- **생성자**: 자동화 도구 실행 필수
- **리뷰어**: 체크리스트 기반 검토
- **승인자**: 최종 품질 검증

#### 3. 문서화 의무
- AI 생성 코드는 주석에 생성 도구 명시
- 프롬프트와 결과를 문서화
- 학습된 패턴을 팀에 공유

### 품질 기준 통일

#### 1. 팀 교육
- **신입 개발자**: AI 코드 생성 가이드라인 교육
- **경험 개발자**: 정기적인 가이드라인 업데이트
- **AI 사용자**: 프롬프트 작성법 교육

#### 2. 도구 표준화
- 모든 팀원이 동일한 자동화 도구 사용
- 품질 점수 기준 통일 (80점 이상)
- 리뷰 프로세스 표준화

#### 3. 지속적 개선
- 월간 품질 메트릭 분석
- 분기별 가이드라인 업데이트
- 연간 교육 및 워크샵

### 협업 도구

#### 1. PR 템플릿
```markdown
## AI 생성 코드 정보
- 생성 도구: [ChatGPT/Claude/기타]
- 프롬프트: [프롬프트 요약]
- 품질 점수: [점수]/100

## 품질 검증 결과
- [ ] validate_code_quality.py 통과
- [ ] detect_magic_values.py 통과
- [ ] check_duplicates.py 통과
- [ ] validate_function_length.py 통과
- [ ] validate_error_handling.py 통과

## 변경 사항
- [구체적인 변경 사항]

## 테스트
- [ ] 단위 테스트 추가/수정
- [ ] 통합 테스트 추가/수정
- [ ] 성능 테스트 추가/수정
```

#### 2. 코드 리뷰 체크리스트
- [ ] AI 코드 생성 가이드라인 준수
- [ ] 자동화 도구 통과
- [ ] 품질 점수 80점 이상
- [ ] 테스트 커버리지 충족
- [ ] 문서화 완료

## 지속적 개선 방법

### 품질 메트릭 수집

#### 1. 자동 수집
```python
# scripts/collect_quality_metrics.py
def collect_ai_quality_metrics():
    """AI 생성 코드 품질 메트릭 수집."""
    metrics = {
        "total_ai_generated_files": count_ai_generated_files(),
        "quality_scores": calculate_quality_scores(),
        "common_issues": identify_common_issues(),
        "improvement_areas": identify_improvement_areas()
    }
    return metrics
```

#### 2. 수동 수집
- 코드 리뷰 피드백
- 개발자 설문조사
- 품질 개선 아이디어

### 가이드라인 업데이트

#### 1. 월간 리뷰
- 품질 메트릭 분석
- 공통 이슈 식별
- 가이드라인 개선점 도출

#### 2. 분기별 업데이트
- 새로운 패턴 반영
- 도구 개선사항 적용
- 팀 교육 자료 업데이트

#### 3. 연간 전면 검토
- 가이드라인 전체 검토
- 새로운 기술 반영
- 팀 표준 재정립

### 학습 및 공유

#### 1. 성공 사례 공유
- 우수한 AI 생성 코드 사례
- 효과적인 프롬프트 패턴
- 품질 개선 노하우

#### 2. 실패 사례 학습
- 공통 실패 패턴 분석
- 개선 방안 도출
- 예방책 마련

#### 3. 지식 베이스 구축
- FAQ 작성
- 베스트 프랙티스 정리
- 트러블슈팅 가이드

---

이 가이드라인을 통해 AI가 생성하는 코드의 품질을 보장하고, 팀의 개발 효율성을 높일 수 있습니다. 질문이나 개선 사항이 있으면 언제든지 팀에 공유해주세요.
