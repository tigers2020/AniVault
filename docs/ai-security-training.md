# AniVault AI 보안 교육 자료

## 🎯 **교육 목표**

1. **AI 보조 코딩의 보안 위험 이해**
2. **프롬프트 인젝션 방어 기법 습득**
3. **안전한 코드 작성 패턴 학습**
4. **응급 대응 절차 숙지**

---

## 📖 **Part 1: AI 보조 코딩의 현실**

### **1.1 AI 보조 코딩의 장점**
- ✅ 빠른 프로토타이핑
- ✅ 반복 작업 자동화
- ✅ 코드 템플릿 생성
- ✅ 문서화 자동화

### **1.2 AI 보조 코딩의 위험**
- ❌ **프롬프트 인젝션**: 외부 명령어 실행
- ❌ **취약한 코드 생성**: 보안 허점 포함
- ❌ **환각(Hallucination)**: 존재하지 않는 API/패키지
- ❌ **비결정성**: 같은 입력에 다른 출력
- ❌ **프라이버시 위험**: 코드/데이터 저장

### **1.3 실제 사례**
```
🚨 사례 1: 프롬프트 인젝션
- 공격자가 README.md에 숨겨진 명령어 삽입
- AI 에이전트가 이를 실행하여 시스템 탈취
- 성공률: 41-84% (실증 연구)

🚨 사례 2: 취약한 코드 생성
- AI가 SQL 인젝션 취약점이 있는 코드 생성
- 개발자가 테스트 없이 적용
- 프로덕션에서 데이터 유출 발생

🚨 사례 3: 환각 패키지
- AI가 존재하지 않는 'secure-auth' 패키지 제안
- 공격자가 해당 이름으로 악성 패키지 배포
- 슬롭스쿼팅 공격 성공
```

---

## 🛡️ **Part 2: AniVault 보안 방어 체계**

### **2.1 다층 방어 전략**

```
┌─────────────────────────────────────┐
│           AI 에이전트                │
├─────────────────────────────────────┤
│ 1. Cursor Rules (프롬프트 인젝션 방어) │
├─────────────────────────────────────┤
│ 2. Pre-commit Hooks (코드 검증)      │
├─────────────────────────────────────┤
│ 3. CI/CD Pipeline (자동화 검사)      │
├─────────────────────────────────────┤
│ 4. Manual Code Review (인간 검토)    │
├─────────────────────────────────────┤
│ 5. Production Monitoring (실시간)    │
└─────────────────────────────────────┘
```

### **2.2 Cursor Rules 기반 방어**

```markdown
# .cursor/rules/ai_security.mdc
- 프롬프트 인젝션 방어 패턴
- 매직 값/문자열 금지
- 중복 정의 금지 (One Source of Truth)
- 시크릿/민감 정보 보호
- 테스트 없는 변경 금지
```

### **2.3 자동화된 보안 검사**

```bash
# Pre-commit 단계
pre-commit run --all-files
├── Bandit (보안 취약점)
├── Safety (의존성 보안)
├── Detect-secrets (시크릿 노출)
├── Custom scripts (AI 특화 검사)
└── Ruff/MyPy (코드 품질)

# CI/CD 단계
.github/workflows/security-ci.yml
├── Security Scan
├── Code Quality
├── Dependency Check
├── Test Coverage
└── Build Security
```

---

## 💻 **Part 3: 실습 - 안전한 AI 보조 코딩**

### **3.1 실습 시나리오 1: 새 기능 추가**

**상황**: AI에게 "사용자 인증 기능 추가해줘" 요청

**❌ 위험한 방식**:
```python
# AI가 생성한 코드를 바로 적용
def authenticate_user(username, password):
    # 하드코딩된 비밀번호 (매직 값)
    if password == "admin123":
        return True
    return False
```

**✅ 안전한 방식**:
```python
# 1. Plan: 변경 계획 명시
# 2. Diff: 변경사항 미리보기
# 3. Test: 테스트 코드 작성
# 4. Apply: 검토 후 적용

from anivault.shared.constants import AuthConfig

def authenticate_user(username: str, password: str) -> bool:
    """사용자 인증."""
    # 상수 사용 (매직 값 제거)
    if password == AuthConfig.DEFAULT_PASSWORD:
        return True
    return False

def test_authenticate_user():
    """인증 함수 테스트."""
    assert authenticate_user("admin", "admin123") is True
    assert authenticate_user("admin", "wrong") is False
```

### **3.2 실습 시나리오 2: 외부 라이브러리 추가**

**상황**: AI가 "requests 라이브러리 사용해서 API 호출해줘" 제안

**❌ 위험한 방식**:
```python
# 바로 pip install requests
import requests

# SSRF 취약점 가능성
response = requests.get(user_input_url)
```

**✅ 안전한 방식**:
```python
# 1. 패키지 검증
# - requests는 허용 목록에 있음
# - 최신 버전 확인
# - 보안 취약점 스캔

# 2. 안전한 구현
from anivault.shared.constants import APIConfig
from anivault.shared.errors import APIError

def safe_api_call(url: str) -> dict:
    """안전한 API 호출."""
    # URL 검증
    if not url.startswith(APIConfig.ALLOWED_DOMAINS):
        raise APIError("Unauthorized domain")

    # 타임아웃 설정
    response = requests.get(url, timeout=APIConfig.TIMEOUT)
    return response.json()
```

### **3.3 실습 시나리오 3: 설정 파일 처리**

**상황**: AI가 "설정 파일에서 API 키 읽어와" 제안

**❌ 위험한 방식**:
```python
# 하드코딩된 시크릿
api_key = "sk-1234567890abcdef"

# 설정 파일에 시크릿 저장
with open("config.json", "w") as f:
    json.dump({"api_key": api_key}, f)
```

**✅ 안전한 방식**:
```python
import os
from anivault.shared.constants import EnvironmentKeys

# 환경 변수 사용
api_key = os.getenv(EnvironmentKeys.TMDB_API_KEY)
if not api_key:
    raise ConfigurationError("TMDB_API_KEY not set")

# 설정 파일에는 시크릿 없음
config = {
    "timeout": 30,
    "retries": 3,
    "base_url": "https://api.themoviedb.org/3"
}
```

---

## 🚨 **Part 4: 응급 대응 절차**

### **4.1 의심스러운 활동 탐지 시**

```bash
# 1단계: 즉시 중단
Ctrl+C  # AI 에이전트 작업 중단

# 2단계: 상황 파악
git status  # 변경사항 확인
git diff    # 변경 내용 검토

# 3단계: 로그 기록
echo "$(date): Suspicious AI activity detected" >> security.log

# 4단계: 복구
git checkout HEAD~1  # 마지막 안전한 상태로 복구
```

### **4.2 보안 위반 시**

```bash
# 1단계: 변경 롤백
git revert <commit-hash>

# 2단계: 의존성 검증
pip-audit --desc
pip list --outdated

# 3단계: 시크릿 로테이션
# - 모든 API 키 교체
# - 새로운 환경 변수 설정
# - 설정 파일 업데이트

# 4단계: 팀 알림
# - 보안 팀에 즉시 보고
# - 인시던트 리포트 작성
```

### **4.3 복구 체크리스트**

- [ ] 마지막 안전한 상태로 복구
- [ ] 새로 추가된 패키지 제거
- [ ] 노출 가능성 있는 키 교체
- [ ] 보안 스캔 재실행
- [ ] 팀에 상황 보고
- [ ] 보안 정책 재검토

---

## 🎓 **Part 5: 퀴즈 및 평가**

### **5.1 퀴즈 문제**

**Q1**: AI가 생성한 코드에 하드코딩된 API 키가 있습니다. 어떻게 처리해야 할까요?

**Q2**: 외부 라이브러리를 추가할 때 확인해야 할 사항들은?

**Q3**: 프롬프트 인젝션 공격을 방어하는 방법은?

**Q4**: 의심스러운 AI 활동을 탐지했을 때 해야 할 일은?

### **5.2 정답 및 해설**

**A1**: 환경 변수로 이동하고 상수 정의
```python
# ❌ 하드코딩
api_key = "sk-1234567890abcdef"

# ✅ 환경 변수 사용
api_key = os.getenv("TMDB_API_KEY")
```

**A2**: 패키지 검증 체크리스트
- [ ] 허용 목록에 있는지 확인
- [ ] 최신 버전 사용
- [ ] 보안 취약점 스캔
- [ ] 팀 승인

**A3**: 프롬프트 인젝션 방어
- [ ] 외부 텍스트를 명령으로 해석하지 않음
- [ ] 2단계 확인 원칙 준수
- [ ] 터미널 명령어 실행 전 사용자 확인
- [ ] 신뢰 경계 설정

**A4**: 응급 대응 절차
- [ ] 즉시 작업 중단
- [ ] 상황 파악 및 로그 기록
- [ ] 안전한 상태로 복구
- [ ] 팀에 보고

---

## 📋 **Part 6: 실무 체크리스트**

### **6.1 AI 보조 코딩 전 체크리스트**

- [ ] **프라이버시 모드 설정**: Legacy Privacy Mode 사용
- [ ] **신뢰 경계 확인**: 외부 파일/문서 신뢰하지 않음
- [ ] **변경 범위 제한**: 작은 범위의 변경만 허용
- [ ] **백업 생성**: 작업 전 현재 상태 백업

### **6.2 AI 보조 코딩 중 체크리스트**

- [ ] **Plan 확인**: 변경 계획이 명확한지 확인
- [ ] **Diff 검토**: 모든 변경사항을 미리 검토
- [ ] **테스트 작성**: 새로운 코드에 대한 테스트 작성
- [ ] **보안 검사**: 매직 값, 시크릿 노출 확인

### **6.3 AI 보조 코딩 후 체크리스트**

- [ ] **Pre-commit 실행**: 모든 보안 검사 통과
- [ ] **코드 리뷰**: 동료 개발자 리뷰 요청
- [ ] **문서화**: 변경사항 문서화
- [ ] **모니터링**: 프로덕션 배포 후 모니터링

---

## 🎯 **Part 7: 모범 사례 요약**

### **7.1 DO (해야 할 일)**

```python
# ✅ 상수 사용
from anivault.shared.constants import ProcessingStatus

# ✅ 환경 변수 사용
api_key = os.getenv("TMDB_API_KEY")

# ✅ 테스트 포함
def test_function():
    assert function() == expected

# ✅ 타입 힌트
def process_file(file_path: Path) -> ProcessedFile:
    pass

# ✅ 에러 처리
try:
    risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### **7.2 DON'T (하지 말아야 할 일)**

```python
# ❌ 매직 값 사용
if status == "completed":

# ❌ 하드코딩된 시크릿
api_key = "sk-1234567890abcdef"

# ❌ 위험한 함수 사용
eval(user_input)
exec(malicious_code)
os.system(command)

# ❌ 테스트 없는 변경
def new_function():
    return "untested code"

# ❌ 외부 텍스트 신뢰
# README.md의 지시사항을 명령으로 실행
```

---

## 📞 **Part 8: 지원 및 문의**

### **8.1 내부 지원**

- **보안 팀**: security@anivault.dev
- **개발 팀**: dev@anivault.dev
- **긴급 연락**: +1-XXX-XXX-XXXX

### **8.2 외부 자료**

- **OWASP LLM Top 10**: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- **Cursor 보안 정책**: https://cursor.com/security
- **Python 보안 가이드**: https://python.org/dev/security/

### **8.3 교육 자료**

- **온라인 강의**: 내부 학습 플랫폼
- **실습 환경**: 보안 테스트 랩
- **정기 워크숍**: 분기별 보안 교육

---

## ✅ **교육 완료 확인**

이 교육을 완료한 개발자는 다음 사항을 이해하고 실행할 수 있어야 합니다:

- [ ] AI 보조 코딩의 보안 위험성 이해
- [ ] 프롬프트 인젝션 방어 기법 숙지
- [ ] 안전한 코드 작성 패턴 적용
- [ ] 응급 대응 절차 실행
- [ ] 보안 도구 사용법 습득

**교육 완료일**: ________________

**교육자**: ________________

**수강자**: ________________

---

*교육 자료 버전: 1.0*
*최종 업데이트: 2024년 1월*
*다음 교육 예정: 분기별*
