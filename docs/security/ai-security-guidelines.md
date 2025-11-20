# AniVault AI 보안 가이드라인

## 🚨 **중요**: AI 보조 코딩의 보안 위험

AniVault 프로젝트는 **AI 보조 코딩의 보안 위험**을 인식하고 이를 방어하기 위한 포괄적인 보안 프레임워크를 구축했습니다.

## 📋 **목차**

1. [보안 위험 분석](#보안-위험-분석)
2. [AI 보안 방어 체계](#ai-보안-방어-체계)
3. [개발자 가이드라인](#개발자-가이드라인)
4. [CI/CD 보안 게이트](#cicd-보안-게이트)
5. [응급 대응 절차](#응급-대응-절차)
6. [참고 자료](#참고-자료)

## 🔍 **보안 위험 분석**

### **1. 프롬프트 인젝션 위험**

**위험**: 외부 파일/문서/웹페이지에 숨겨진 명령어가 AI 에이전트를 통해 실행될 수 있음

**실증 연구**:
- IDE 에이전트 탈취 성공률: 41-84%
- 터미널 명령어 실행까지 유도 가능
- "AI가 공격자의 셸이 되는" 시나리오

**방어 방법**:
- 2단계 확인 원칙: Plan → Diff → Test → Apply
- 외부 텍스트를 명령으로 해석하지 않음
- 터미널 명령어 실행 전 사용자 확인 필수

### **2. 취약한 코드 생성**

**위험**: AI 보조 사용자가 더 취약한 코드를 제출하는 경향

**연구 결과**:
- Stanford/NYU 연구: AI 보조 사용자 = 더 취약한 코드
- 존재하지 않는 패키지/API 환각 생성
- 슬롭스쿼팅 공급망 공격 위험

**방어 방법**:
- 강제 테스트 게이트
- 의존성 검증 시스템
- 허용 목록 기반 패키지 관리

### **3. 프라이버시/데이터 경로 위험**

**위험**: Cursor의 데이터 처리 방식

**현실**:
- Privacy Mode에 따라 일부 코드 저장 가능
- 인덱싱은 임베딩 저장 수반
- "내 API 키" 사용해도 Cursor 백엔드 경유

**방어 방법**:
- Legacy Privacy Mode 우선 사용
- 민감 데이터 인덱싱 제외
- 환경 변수 기반 시크릿 관리

## 🛡️ **AI 보안 방어 체계**

### **1. Cursor Rules 기반 방어**

```markdown
# .cursor/rules/ai_security.mdc
- 프롬프트 인젝션 방어 패턴
- 매직 값/문자열 금지
- 중복 정의 금지 (One Source of Truth)
- 시크릿/민감 정보 보호
- 테스트 없는 변경 금지
```

### **2. Pre-commit 훅 보안 검증**

```yaml
# .pre-commit-config.yaml
- Bandit: 보안 취약점 스캔
- Safety: 의존성 보안 검사
- Detect-secrets: 시크릿 노출 탐지
- Custom scripts: AI 특화 보안 검사
```

### **3. CI/CD 파이프라인 보안 게이트**

```yaml
# .github/workflows/security-ci.yml
- Static Analysis Security Testing (SAST)
- Dependency vulnerability scanning
- Code quality enforcement
- Build security verification
```

## 👨‍💻 **개발자 가이드라인**

### **✅ DO: 안전한 AI 보조 코딩**

#### **1. 프롬프트 인젝션 방어**
```python
# ✅ DO: 2단계 확인 원칙
# 1. Plan: 변경 계획 명시
# 2. Diff: 변경사항 미리보기
# 3. Test: 테스트 실행
# 4. Apply: 승인 후 적용

def safe_ai_assisted_function():
    """AI 보조로 생성된 안전한 함수."""
    # 변경 계획: 새로운 유틸리티 함수 추가
    # 테스트: 단위 테스트 포함
    # 검토: 코드 리뷰 필수
    pass
```

#### **2. 매직 값 제거**
```python
# ❌ DON'T: 매직 값 직접 사용
if status == "completed":
    return handle_completion()

# ✅ DO: 상수 사용
from anivault.shared.constants import ProcessingStatus

if status == ProcessingStatus.COMPLETED:
    return handle_completion()
```

#### **3. 시크릿 안전 관리**
```python
# ❌ DON'T: 하드코딩된 시크릿
api_key = "sk-1234567890abcdef"

# ✅ DO: 환경 변수 사용
import os
from anivault.shared.constants import EnvironmentKeys

api_key = os.getenv(EnvironmentKeys.TMDB_API_KEY)
if not api_key:
    raise ConfigurationError("TMDB_API_KEY not set")
```

#### **4. 테스트 우선 개발**
```python
# ✅ DO: 테스트와 함께 변경
def new_function() -> str:
    """새로운 함수."""
    return "tested code"

def test_new_function():
    """함수 테스트."""
    assert new_function() == "tested code"
```

### **❌ DON'T: 위험한 패턴**

#### **1. 외부 텍스트 신뢰**
```python
# ❌ DON'T: 외부 파일의 지시사항을 명령으로 해석
# 마크다운, 주석, 문서의 숨겨진 명령어 실행 금지
```

#### **2. 위험한 코드 실행**
```python
# ❌ DON'T: 위험한 함수 사용
eval(user_input)  # 코드 인젝션 위험
exec(malicious_code)  # 코드 실행 위험
os.system(command)  # 셸 인젝션 위험
```

#### **3. 시크릿 노출**
```python
# ❌ DON'T: 로그에 시크릿 포함
logger.info(f"API key: {api_key}")  # 시크릿 노출

# ✅ DO: 마스킹된 로깅
logger.info(f"API key: {api_key[:8]}...")
```

## 🔄 **CI/CD 보안 게이트**

### **1. 자동화된 보안 검사**

```bash
# Pre-commit 단계
pre-commit run --all-files

# CI 파이프라인 단계
- Security Scan (Bandit, Safety)
- Code Quality (Ruff, MyPy, Black)
- Dependency Check (pip-audit)
- Test Coverage (pytest-cov)
- Build Security (twine check)
```

### **2. 보안 임계치**

```toml
[tool.anivault.security]
max_security_issues = 0      # 보안 이슈 0개 허용
min_test_coverage = 80       # 최소 80% 테스트 커버리지
max_function_complexity = 10 # 함수 복잡도 최대 10
max_function_length = 50     # 함수 길이 최대 50줄
```

### **3. 머지 조건**

```yaml
# GitHub Actions 머지 조건
- 모든 보안 검사 통과
- 테스트 커버리지 임계치 달성
- 코드 품질 검사 통과
- 의존성 보안 검사 통과
- 수동 코드 리뷰 승인
```

## 🚨 **응급 대응 절차**

### **1. 의심스러운 활동 탐지 시**

```bash
# 1. 즉시 중단
# AI 에이전트 작업 중단

# 2. 사용자 알림
echo "🚨 위험 상황 탐지됨 - 작업 중단"

# 3. 로그 기록
logger.error("Suspicious AI activity detected")

# 4. 복구 계획 실행
git checkout HEAD~1  # 마지막 안전한 상태로 복구
```

### **2. 보안 위반 시**

```bash
# 1. 변경 롤백
git revert <commit-hash>

# 2. 의존성 검증
pip-audit --desc

# 3. 시크릿 로테이션
# 모든 API 키 교체

# 4. 팀 알림
# 보안 팀에 즉시 보고
```

### **3. 복구 체크리스트**

- [ ] 마지막 안전한 상태로 복구
- [ ] 새로 추가된 패키지 제거
- [ ] 노출 가능성 있는 키 교체
- [ ] 보안 스캔 재실행
- [ ] 팀에 상황 보고
- [ ] 보안 정책 재검토

## 📚 **참고 자료**

### **연구 논문**
- [프롬프트 인젝션 공격 연구](https://arxiv.org/html/2509.22040v1)
- [AI 보조 코딩 보안 연구](https://arxiv.org/abs/2211.03622)
- [LLM 비결정성 연구](https://arxiv.org/html/2502.20747v1)

### **보안 표준**
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Cursor 보안 정책](https://cursor.com/security)
- [Python 보안 가이드라인](https://python.org/dev/security/)

### **도구 문서**
- [Bandit 보안 스캐너](https://bandit.readthedocs.io/)
- [Safety 의존성 검사](https://pyup.io/safety/)
- [Detect-secrets 시크릿 탐지](https://github.com/Yelp/detect-secrets)

## 🤝 **팀 교육**

### **정기 교육 주제**
1. AI 보조 코딩의 위험성
2. 프롬프트 인젝션 방어 기법
3. 안전한 코드 작성 패턴
4. 시크릿 관리 모범 사례
5. 응급 대응 절차

### **실습 세션**
1. 프롬프트 인젝션 시나리오 체험
2. 보안 도구 사용법 연습
3. 코드 리뷰 보안 체크리스트
4. 보안 위반 시뮬레이션

---

## ⚠️ **중요 알림**

이 가이드라인은 **AniVault 프로젝트의 모든 개발자**가 준수해야 하는 **필수 보안 정책**입니다.

**위반 시**:
- 코드 머지 차단
- 보안 팀 검토 요청
- 재교육 필수

**준수 시**:
- 안전한 AI 보조 코딩 환경
- 높은 코드 품질 보장
- 보안 위험 최소화

---

*최종 업데이트: 2024년 1월*
*문서 버전: 1.0*
*검토 주기: 분기별*
