# AniVault

AniVault는 TMDB API를 활용한 애니메이션 파일 자동 정리 시스템입니다.

## 기능

- 애니메이션 파일 자동 인식 및 파싱
- TMDB API를 통한 메타데이터 수집 (한국어 제목 지원)
- 자동 파일 정리 및 이름 변경
- **Enhanced Organize**: 파일명 유사성 기반 그룹핑, 해상도별 분류, 자막 파일 자동 매칭
- Windows 단일 실행파일(.exe) 지원

## 설치

```bash
pip install -e .
```

### 의존성 검증

프로젝트의 모든 의존성이 올바르게 설치되었는지 확인하려면:

```bash
python scripts/validate_dependencies.py
```

이 도구는 `pyproject.toml`에 정의된 모든 의존성(메인 및 개발 의존성)이 현재 환경에 올바르게 설치되었는지 검증합니다.

## 사용법

AniVault는 **Typer 기반의 현대적인 CLI**를 사용합니다. 타입 안전성, 자동 도움말 생성, 셸 완성 지원을 제공합니다:

```bash
anivault --help
```

### CLI 특징

- **타입 안전성**: 모든 옵션과 인수에 타입 힌트 적용
- **자동 도움말**: 명령어와 옵션에 대한 상세한 도움말 자동 생성
- **셸 완성 지원**: Bash, Zsh, Fish, PowerShell에서 명령어 완성 지원
- **JSON 출력**: `--json-output` 옵션으로 머신 리더블한 출력
- **구조화된 로깅**: 여러 로그 레벨과 상세한 디버깅 정보

### 주요 명령어

- `python -m anivault scan <directory>` - 애니메이션 파일 스캔
- `python -m anivault match <directory>` - TMDB와 매칭
- `python -m anivault organize <directory>` - 파일 정리
- `python -m anivault run <directory>` - 전체 워크플로우 실행
- `python -m anivault log list` - 작업 로그 확인
- `python -m anivault rollback <timestamp>` - 작업 되돌리기

### 공통 옵션

- `--verbose` - 상세 출력 (여러 번 사용 가능)
- `--log-level <level>` - 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--json-output` - JSON 형식으로 출력
- `--version` - 버전 정보 표시

## Workflow and Recovery

AniVault는 안전한 파일 정리를 위한 완전한 워크플로우를 제공합니다. 다음 단계를 따라 애니메이션 파일을 안전하게 정리할 수 있습니다:

### 1. 미리보기 (Dry Run)

실제 파일을 이동하기 전에 계획된 작업을 미리 확인할 수 있습니다:

```bash
anivault organize /path/to/anime --dry-run
```

이 명령은 파일을 실제로 이동하지 않고 어떤 변경사항이 발생할지 보여줍니다.

### 2. 파일 정리 실행

미리보기에 만족하면 실제 정리를 실행합니다:

```bash
anivault organize /path/to/anime
```

시스템이 변경사항을 보여주고 확인을 요청합니다. `--yes` 플래그를 사용하여 확인 프롬프트를 건너뛸 수 있습니다.

### 3. 작업 기록 확인

이전에 실행한 모든 정리 작업의 기록을 볼 수 있습니다:

```bash
anivault log list
```

이 명령은 타임스탬프와 함께 모든 작업 로그를 표시합니다.

### 4. 작업 되돌리기 (Rollback)

필요한 경우 이전 정리 작업을 되돌릴 수 있습니다:

```bash
anivault rollback YYYYMMDD_HHMMSS --dry-run
```

먼저 `--dry-run`으로 되돌리기 계획을 확인한 후, 실제 되돌리기를 실행할 수 있습니다:

```bash
anivault rollback YYYYMMDD_HHMMSS
```

### 안전한 워크플로우 예시

```bash
# 1. 먼저 미리보기로 확인
python -m anivault organize ./anime_files --dry-run

# 2. 문제없으면 실제 정리 실행
python -m anivault organize ./anime_files

# 3. 나중에 작업 기록 확인
python -m anivault log list

# 4. 필요시 되돌리기 (먼저 미리보기)
python -m anivault rollback 20241201_143022 --dry-run

# 5. 실제 되돌리기 실행
python -m anivault rollback 20241201_143022
```

### Enhanced Organize 워크플로우

새로운 Enhanced Organize 기능을 사용한 고급 파일 정리:

```bash
# 1. Enhanced Organize 미리보기
python -m anivault organize ./anime_files --enhanced --dry-run --destination ./organized

# 2. 실제 Enhanced Organize 실행
python -m anivault organize ./anime_files --enhanced --destination ./organized

# 3. 유사성 임계값 조정하여 재실행
python -m anivault organize ./anime_files --enhanced --similarity-threshold 0.8 --destination ./organized
```

#### Enhanced Organize 기능

- **파일명 유사성 기반 그룹핑**: 비슷한 파일명을 가진 파일들을 자동으로 그룹화
- **해상도별 분류**: 최고 해상도 파일과 저해상도 파일을 자동으로 분리
- **자막 파일 자동 매칭**: 비디오 파일과 연관된 자막 파일을 자동으로 찾아서 함께 이동
- **한국어 제목 지원**: TMDB API를 통해 한국어 제목으로 폴더 구조 생성
- **지능형 경로 생성**: `destination/한국어제목/Season ##/` 구조로 자동 정리

### 상세 명령어 예시

#### 파일 정리 명령어

```bash
# 기본 정리 (확인 프롬프트 포함)
python -m anivault organize /path/to/anime

# 미리보기만 실행 (실제 변경 없음)
python -m anivault organize /path/to/anime --dry-run

# 확인 프롬프트 없이 바로 실행
python -m anivault organize /path/to/anime --yes

# 출력 디렉토리 지정
python -m anivault organize /path/to/anime --destination /organized/anime

# Enhanced Organize (새로운 기능)
python -m anivault organize /path/to/anime --enhanced --destination /organized/anime

# Enhanced Organize 미리보기
python -m anivault organize /path/to/anime --enhanced --dry-run --destination /organized/anime

# 유사성 임계값 조정 (0.0-1.0, 기본값: 0.7)
python -m anivault organize /path/to/anime --enhanced --similarity-threshold 0.8
```

#### 로그 관리 명령어

```bash
# 모든 작업 로그 목록 보기
python -m anivault log list
```

예상 출력:
```
Available operation logs:
20241201_143022  - 15 files organized
20241201_142015  - 8 files organized
20241130_164530  - 23 files organized
```

#### 되돌리기 명령어

```bash
# 되돌리기 미리보기 (실제 변경 없음)
python -m anivault rollback 20241201_143022 --dry-run

# 되돌리기 실행 (확인 프롬프트 포함)
python -m anivault rollback 20241201_143022

# 확인 프롬프트 없이 바로 되돌리기
python -m anivault rollback 20241201_143022 --yes
```

#### 스캔 명령어

```bash
# 현재 디렉토리 스캔 (기본 설정)
python -m anivault scan .

# 특정 디렉토리 스캔 (사용자 정의 옵션)
python -m anivault scan /path/to/anime --recursive --output results.json

# 자막 파일 제외하고 스캔 (빠른 처리)
python -m anivault scan /path/to/anime --no-include-subtitles

# 디버깅을 위한 상세 출력
python -m anivault scan /path/to/anime --verbose

# JSON 형식으로 결과 저장
python -m anivault scan /path/to/anime --output scan_results.json

# JSON 형식으로 콘솔 출력
python -m anivault scan /path/to/anime --json
```

#### 다른 유용한 명령어

```bash
# 전체 도움말 보기
python -m anivault --help

# 특정 명령어 도움말 보기
python -m anivault scan --help
python -m anivault organize --help
python -m anivault log --help
python -m anivault rollback --help

# 시스템 구성 요소 검증
python -m anivault verify --all
```

## 설정

AniVault는 TOML 설정 파일과 환경 변수를 통해 구성할 수 있습니다.

### 설정 파일

기본 설정 파일은 `config/config.toml`에 위치합니다:

```toml
[tmdb]
api_key = "your_tmdb_api_key_here"
base_url = "https://api.themoviedb.org/3"
timeout = 30
retry_attempts = 3
retry_delay = 1.0
rate_limit_delay = 0.25

[logging]
level = "INFO"
format = "json"

[cache]
enabled = true
ttl_hours = 24
max_size_mb = 100
```

### 환경 변수

`.env` 파일을 사용하여 환경 변수를 설정할 수 있습니다:

```bash
# .env 파일
TMDB_API_KEY=your_tmdb_api_key_here
TMDB_BASE_URL=https://api.themoviedb.org/3
LOG_LEVEL=DEBUG
```

### 설정 우선순위

1. **명령줄 인수** (최우선)
2. **환경 변수**
3. **TOML 설정 파일**
4. **기본값**

### 시스템 검증

설정이 올바르게 되었는지 확인하려면:

```bash
# TMDB API 연결 테스트
python -m anivault verify --tmdb

# 모든 시스템 구성 요소 검증
python -m anivault verify --all
```

### 셸 완성 설정

AniVault는 Typer의 자동 완성 기능을 통해 다양한 셸에서 명령어 완성을 지원합니다:

#### 자동 설치 (권장)
```bash
# 현재 셸에 자동으로 완성 설정
python -m anivault --install-completion
```

#### 수동 설치

**Bash/Zsh:**
```bash
# Bash 완성 스크립트 생성 및 설치
python -m anivault --show-completion bash > ~/.bash_completion.d/anivault
echo "source ~/.bash_completion.d/anivault" >> ~/.bashrc

# Zsh 완성 스크립트 생성 및 설치
python -m anivault --show-completion zsh > ~/.zsh_completion.d/_anivault
echo "source ~/.zsh_completion.d/_anivault" >> ~/.zshrc
```

**PowerShell (Windows):**
```powershell
# PowerShell 완성 스크립트 생성
python -m anivault --show-completion powershell > anivault-completion.ps1

# PowerShell 프로필에 추가
echo "Invoke-Expression (Get-Content anivault-completion.ps1 -Raw)" >> $PROFILE
```

**Fish:**
```bash
# Fish 완성 스크립트 생성
python -m anivault --show-completion fish > ~/.config/fish/completions/anivault.fish
```

## 개발

### 개발 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Pre-commit 훅 설정
# Windows
scripts\setup-pre-commit.bat

# Linux/macOS
chmod +x scripts/setup-pre-commit.sh
./scripts/setup-pre-commit.sh
```

### CLI 아키텍처

AniVault는 **Typer 기반의 현대적인 CLI**를 사용합니다:

- **메인 앱**: `src/anivault/cli/typer_app.py`
- **진입점**: `pyproject.toml`의 `[project.scripts]` 섹션
- **핸들러**: 각 명령어별로 분리된 핸들러 모듈
- **공통 옵션**: `src/anivault/cli/common/options.py`
- **컨텍스트**: `src/anivault/cli/common/context.py`

#### CLI 명령어 구조

```
src/anivault/cli/
├── typer_app.py          # 메인 Typer 앱
├── scan_handler.py       # scan 명령어 핸들러
├── match_handler.py      # match 명령어 핸들러
├── organize_handler.py   # organize 명령어 핸들러
├── run_handler.py        # run 명령어 핸들러
├── verify_handler.py     # verify 명령어 핸들러
├── log_handler.py        # log 명령어 핸들러
├── rollback_handler.py   # rollback 명령어 핸들러
└── common/
    ├── options.py        # 공통 옵션 정의
    ├── context.py        # CLI 컨텍스트 관리
    ├── models.py         # Pydantic 모델 정의
    └── validation.py     # 입력 검증 로직
```

#### 통합 테스트

CLI 기능은 `tests/integration/test_typer_cli.py`에서 포괄적으로 테스트됩니다:

- 기본 CLI 명령어 동작
- 성능 벤치마크
- 설정 로딩 및 검증
- 에러 처리 및 복구

#### 새로운 CLI 명령어 추가하기

새로운 Typer 명령어를 추가하려면:

1. **핸들러 파일 생성**: `src/anivault/cli/new_command_handler.py`
2. **명령어 함수 구현**: 핸들러에서 실제 비즈니스 로직 처리
3. **Typer 앱에 등록**: `src/anivault/cli/typer_app.py`에 명령어 추가
4. **공통 옵션 활용**: `src/anivault/cli/common/options.py`의 옵션 재사용
5. **테스트 작성**: `tests/cli/`에 테스트 추가

예시:
```python
# new_command_handler.py
def new_command(
    directory: Path = typer.Argument(..., help="Directory to process"),
    option: bool = typer.Option(False, "--option", help="Some option"),
) -> None:
    """새로운 명령어 설명."""
    # 비즈니스 로직 구현
    pass

# typer_app.py에 추가
@app.command("new-command")
def new_command_typer(
    directory: Path = typer.Argument(...),
    option: bool = typer.Option(False, "--option"),
) -> None:
    """새로운 명령어 설명."""
    new_command(directory, option)
```

### 코드 품질 기준

AniVault는 엄격한 코드 품질 기준을 유지합니다. 자세한 내용은 [코드 품질 가이드](docs/code-quality-guide.md)를 참조하세요.

#### 핵심 원칙

1. **One Source of Truth (단일 진실의 원천)**
   - 모든 상수, 타입, 에러 코드는 `src/anivault/shared/`에서 중앙 관리
   - 중복 정의 금지, Import를 통한 재사용 강제

2. **매직 값 제거 (Magic Values Elimination)**
   - 하드코딩된 문자열, 숫자, 상태값 금지
   - 모든 값은 상수나 Enum으로 추출

3. **함수 단일 책임 원칙 (Single Responsibility Principle)**
   - 각 함수는 하나의 명확한 책임만 가져야 함
   - 함수 길이 제한: 80줄 이하

4. **구조적 에러 처리 (Structured Error Handling)**
   - `AniVaultError` 기반 에러 처리 시스템 사용
   - 일반 `Exception` 사용 금지
   - 컨텍스트 정보 포함

#### AI 코드 생성 가이드라인

AI를 활용한 코드 생성 시에는 [AI 코드 생성 가이드라인](docs/ai-code-generation-guidelines.md)을 참조하세요.

#### 리팩터링 예제

실제 리팩터링 사례와 개선 방법은 [리팩터링 예제](docs/refactoring-examples.md)를 참조하세요.

### 코드 품질 검증

AniVault는 자동화된 코드 품질 검증 시스템을 사용합니다:

#### 개별 검증 스크립트

```bash
# 매직 값 탐지
python scripts/validate_magic_values.py src/

# 함수 길이 및 복잡도 검증
python scripts/validate_function_length.py src/

# 에러 처리 패턴 검증
python scripts/validate_error_handling.py src/

# 통합 코드 품질 검증
python scripts/validate_code_quality.py src/
```

#### Pre-commit 훅

모든 커밋 전에 자동으로 실행되는 검증:

- 코드 포맷팅 (Black, isort)
- 린팅 (Flake8, MyPy)
- 보안 검사 (Bandit)
- 커스텀 코드 품질 검증

#### CI/CD 파이프라인

GitHub Actions를 통한 자동 검증:

- 다중 Python 버전 테스트 (3.8-3.11)
- 코드 품질 검증
- 보안 스캔
- 테스트 커버리지 측정
- 의존성 취약점 검사

### Shell Completion 사용법

설치 후 탭 키를 사용하여 명령어와 옵션을 자동 완성할 수 있습니다:

```bash
# 명령어 자동 완성
python -m anivault <TAB>
# scan, match, organize, run, log, rollback, verify

# 옵션 자동 완성
python -m anivault scan --<TAB>
# --recursive, --include-subtitles, --include-metadata, --output, --json, --help

# 파일 경로 자동 완성
python -m anivault scan /path/to/<TAB>
```

### Task Master 사용

프로젝트 초기화 후 개발을 시작하려면:

```bash
# Taskmaster 초기화 (이미 완료됨)
task-master init

# PRD 파싱하여 작업 생성
task-master parse-prd .taskmaster/docs/prd.txt

# 다음 작업 확인
task-master next

# 현재 태스크 목록 보기
task-master list

# 특정 태스크 상세 보기
task-master show <task-id>
```

## 라이선스

MIT License
