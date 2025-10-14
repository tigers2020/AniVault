# 🚀 AniVault 시작하기

프로젝트를 처음 시작하는 개발자를 위한 완전한 가이드입니다.

## 📋 사전 요구사항

### 필수 소프트웨어
- **Python 3.10+**: [다운로드](https://www.python.org/downloads/)
- **Git**: [다운로드](https://git-scm.com/downloads)
- **TMDB API Key**: [발급받기](https://www.themoviedb.org/settings/api)

### 권장 도구
- **VS Code**: Python 개발에 최적화된 IDE
- **PowerShell 7+**: Windows에서 개발 시 권장

## 🔧 개발 환경 설정

### 1. 저장소 클론
```bash
git clone https://github.com/tigers2020/AniVault.git
cd AniVault
```

### 2. 가상환경 생성
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치
```bash
# 개발 의존성 포함 설치
pip install -e ".[dev]"

# 의존성 목록 확인
pip list
```

### 4. 환경 변수 설정
```bash
# .env 파일 생성
cp env.template .env

# .env 파일 편집
# TMDB_API_KEY=your-api-key-here
```

### 5. Pre-commit 훅 설치
```bash
pre-commit install
```

## 🧪 개발 도구 설정

### VS Code 설정
`.vscode/settings.json` 파일을 생성하고 다음 내용을 추가하세요:

```json
{
    "python.defaultInterpreterPath": "./venv/Scripts/python.exe",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

### 코드 품질 도구
```bash
# 포맷팅
black src/

# 린팅
ruff check src/

# 타입 체킹
mypy src/

# 보안 스캔
bandit -r src/
```

## ✅ 설치 확인

### 1. 테스트 실행
```bash
# 모든 테스트 실행
pytest tests/

# 특정 모듈 테스트
pytest tests/unit/

# 커버리지 포함
pytest --cov=src/anivault tests/
```

### 2. CLI 명령 확인
```bash
# 도움말 확인
anivault --help

# 버전 확인
anivault --version
```

### 3. 품질 검사
```bash
# 모든 품질 검사 실행
black src/ && ruff check src/ && mypy src/ && pytest tests/
```

## 📚 다음 단계

### 아키텍처 이해
1. [아키텍처 가이드](./architecture.md)를 읽고 전체 시스템 구조를 파악하세요.
2. 핵심 컴포넌트와 데이터 플로우를 이해하세요.

### 첫 번째 기여
1. [개발 워크플로우](./development.md)를 읽고 개발 프로세스를 이해하세요.
2. [코드 품질 가이드](./code-quality.md)를 참고하여 코딩 표준을 익히세요.
3. Good first issue를 찾아 첫 번째 PR을 제출하세요.

### TMDB 연동
1. [TMDB API 가이드](./tmdb-api.md)를 읽고 API 설정을 완료하세요.
2. 캐싱 및 Rate Limiting 전략을 이해하세요.

## 🐛 문제 해결

### 가상환경 활성화 오류
**Windows PowerShell 실행 정책 오류:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 의존성 설치 오류
**pip 업그레이드:**
```bash
python -m pip install --upgrade pip
```

### TMDB API 키 오류
1. `.env` 파일에 API 키가 올바르게 설정되었는지 확인
2. 환경 변수가 로드되는지 확인: `python -c "from anivault.core.settings import Settings; print(Settings().tmdb_api_key)"`

## 💡 팁과 요령

### 개발 모드 실행
```bash
# 상세 로그와 함께 실행
anivault --verbose scan /path/to/anime

# 디버그 모드
anivault --log-level DEBUG scan /path/to/anime
```

### 빠른 피드백 루프
```bash
# 변경사항 감지 및 자동 테스트
pytest-watch tests/
```

### 코드 품질 자동화
```bash
# Pre-commit 수동 실행
pre-commit run --all-files
```

## 📞 도움 받기

- **버그 리포트**: [GitHub Issues](https://github.com/tigers2020/AniVault/issues)
- **질문**: [GitHub Discussions](https://github.com/tigers2020/AniVault/discussions)
- **문서**: [프로젝트 문서](../README.md)

---

**환영합니다!** 🎉 AniVault 커뮤니티에 참여하신 것을 환영합니다.

