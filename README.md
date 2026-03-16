# AniVault

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/tigers2020/AniVault/workflows/CI/badge.svg)](https://github.com/tigers2020/AniVault/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> **⚠️ 법적 고지**: 이 도구는 개인 라이브러리 정리 전용입니다. 합법적으로 소유한 콘텐츠만 사용하세요.

TMDB API를 활용한 애니메이션 파일 자동 정리 시스템입니다.

## 🚀 빠른 시작

### 0. 가상 환경 활성화 (권장)

프로젝트 루트에서 다음 명령어로 venv를 활성화하세요:

**PowerShell:**
```powershell
# 방법 1: 점과 공백 사용 (현재 셸에서 실행)
. .\activate.ps1

# 방법 2: 직접 실행
& .\activate.ps1
```

**CMD:**
```cmd
activate.bat
```

**수동 활성화:**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

> 💡 **VS Code 사용자**: `.vscode/settings.json`에 이미 자동 활성화가 설정되어 있습니다. VS Code 터미널을 열면 자동으로 venv가 활성화됩니다.
>
> 💡 **처음 사용 시**: `.\setup-venv.ps1`을 실행하여 환경을 확인하세요.

### 1. 설치
```bash
pip install -e .
```

### 2. 환경 설정
```bash
cp env.template .env
# .env 파일에서 TMDB_API_KEY 설정
```

### 3. 사용법 (3단계)
```bash
# 1. 스캔: 애니메이션 파일 발견 및 파싱
anivault scan /path/to/anime

# 2. 매칭: TMDB와 메타데이터 매칭
anivault match /path/to/anime

# 3. 정리: 파일 자동 정리
anivault organize /path/to/anime --dry-run  # 미리보기
anivault organize /path/to/anime            # 실제 정리
```

**또는 한 번에 실행:**
```bash
anivault run /path/to/anime
```

## ✨ 주요 기능

- 🎯 **자동 인식**: 애니메이션 파일 자동 파싱 (anitopy 기반)
- 🌐 **TMDB 연동**: 한국어 제목 지원, 메타데이터 자동 수집
- 📁 **스마트 정리**: 해상도별 분류, 자막 파일 자동 매칭
- 💾 **고성능 캐시**: SQLite WAL 모드, 오프라인 지원
- 🔄 **롤백 지원**: 모든 작업 기록 및 되돌리기 기능
- 🖥️ **GUI 지원**: PySide6 기반 사용자 인터페이스 (라이트/다크 테마)

## 📋 CLI 명령어

### 기본 명령어
```bash
anivault scan <directory>     # 파일 스캔
anivault match <directory>    # TMDB 매칭
anivault organize <directory> # 파일 정리
anivault run <directory>      # 전체 워크플로우
```

### 유틸리티 명령어
```bash
anivault log list                    # 작업 로그 확인
anivault rollback <timestamp>        # 작업 되돌리기
anivault verify <directory>          # 정리 결과 검증
```

### 공통 옵션
```bash
--dry-run          # 미리보기 모드
--yes              # 확인 프롬프트 건너뛰기
--verbose          # 상세 출력
--json-output      # JSON 형식 출력
--log-level LEVEL  # 로그 레벨 설정
```

## 🔧 고급 기능

### Enhanced Organize
- 파일명 유사성 기반 그룹핑
- 해상도별 자동 분류 (메타데이터·파일명 우선, 없으면 동영상 파일 검사)
- 자막 파일 자동 매칭
- 배치 처리 지원

해상도가 파일명/메타데이터에서 나오지 않을 때, **ffmpeg(ffprobe)** 가 설치되어 있으면 동영상 파일을 직접 검사해 해상도를 채웁니다. ffprobe가 없어도 기존처럼 "unknown"으로 표시되며 오류는 발생하지 않습니다.

### 캐시 시스템
- TMDB API 응답 캐싱 (24시간 TTL)
- SQLite WAL 모드로 동시성 보장
- 오프라인 모드 지원
- 캐시 무효화 및 관리

### 보안 및 성능
- TMDB API 레이트 리밋 준수
- 지수 백오프 재시도
- 민감한 데이터 로그 마스킹
- 멀티스레딩 지원

## 📚 상세 문서

### 시작하기
- **[개발 가이드](docs/development/DEVELOPMENT_GUIDE.md)** - 환경 설정부터 첫 번째 커밋까지
- **[Pre-commit 설정](docs/guides/pre-commit-setup.md)** - 코드 품질 검사 훅 설치 및 사용
- **[문서 인덱스](docs/protocols/README.md)** - 프로토콜 및 문서 목록

### 주요 문서
- [아키텍처](docs/architecture/ARCHITECTURE_ANIVAULT.md) - 전체 시스템 구조
- [프로토콜·문서 목록](docs/protocols/README.md) - 프로토콜 및 개발 프로세스 인덱스
- [API 문서](docs/api/linked_hash_table_api.md) - LinkedHashTable API 등

### 코드 구조 정책
- **공용 상수/타입/에러:** owner 있는 상수는 소유 계층(CLI/GUI/domain/infrastructure)으로 두고, 앱 전역 공용(전역 예외·타입 alias·극소수 상수·직렬화 유틸)만 **common**(whitelist)에 둡니다. common 신규 추가 시 review 필수. [구조 단순화](docs/architecture/usecase-migration/s0-baseline/README.md) 참조.
- **CLI/GUI:** **application use case만 호출**하고, use case가 반환한 결과(DTO/Result)만 표시합니다. handler는 옵션 파싱·use case 호출·결과 렌더링만 담당하며, 비즈니스 로직을 구현하지 않습니다.

## 🛠️ 개발

### 개발 환경 설정
```bash
git clone https://github.com/tigers2020/AniVault.git
cd AniVault
pip install -e ".[dev]"  # Install with development dependencies
pre-commit install      # Install pre-commit hooks
```

### Pre-commit Hooks

커밋 전 자동으로 코드 품질 검사를 수행합니다:

```bash
# Hook 설치
pre-commit install

# 모든 파일 검사
pre-commit run --all-files

# Hook 업데이트
pre-commit autoupdate
```

**포함된 검사 항목:**
- ✅ Ruff (린터 & 포맷터)
- ✅ MyPy (타입 검사)
- ✅ Bandit (보안 검사)
- ✅ Pytest (빠른 단위 테스트)
- ✅ 순환 import 검사

**검증 방법:** `pre-commit run --all-files` 실행 시 전체 검사 통과 여부 확인.

자세한 내용은 [Pre-commit 설정 가이드](docs/guides/pre-commit-setup.md)를 참조하세요.

### 테스트 실행
```bash
pytest tests/
ruff check src/
mypy src/
bandit -r src/
```

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

기여하기 전에 [CONTRIBUTING.md](CONTRIBUTING.md)를 읽어주세요.

## 📞 지원

- 🐛 버그 리포트: [Issues](https://github.com/tigers2020/AniVault/issues)
- 💡 기능 요청: [Discussions](https://github.com/tigers2020/AniVault/discussions)
- 📧 이메일: [프로젝트 페이지](https://github.com/tigers2020/AniVault)

---

**AniVault** - 애니메이션 컬렉션을 깔끔하게 정리하세요! 🎌
