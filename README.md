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

AniVault는 새로운 Typer 기반 CLI를 사용합니다:

```bash
anivault --help
```

### 주요 명령어

- `anivault scan <directory>` - 애니메이션 파일 스캔
- `anivault match <directory>` - TMDB와 매칭
- `anivault organize <directory>` - 파일 정리
- `anivault run <directory>` - 전체 워크플로우 실행
- `anivault log list` - 작업 로그 확인
- `anivault rollback <timestamp>` - 작업 되돌리기

### 공통 옵션

- `--verbose, -v` - 상세 출력 (여러 번 사용 가능)
- `--log-level <level>` - 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--json` - JSON 형식으로 출력
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
anivault organize ./anime_files --dry-run

# 2. 문제없으면 실제 정리 실행
anivault organize ./anime_files

# 3. 나중에 작업 기록 확인
anivault log list

# 4. 필요시 되돌리기 (먼저 미리보기)
anivault rollback 20241201_143022 --dry-run

# 5. 실제 되돌리기 실행
anivault rollback 20241201_143022
```

### Enhanced Organize 워크플로우

새로운 Enhanced Organize 기능을 사용한 고급 파일 정리:

```bash
# 1. Enhanced Organize 미리보기
anivault organize ./anime_files --enhanced --dry-run --destination ./organized

# 2. 실제 Enhanced Organize 실행
anivault organize ./anime_files --enhanced --destination ./organized

# 3. 유사성 임계값 조정하여 재실행
anivault organize ./anime_files --enhanced --similarity-threshold 0.8 --destination ./organized
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
anivault organize /path/to/anime

# 미리보기만 실행 (실제 변경 없음)
anivault organize /path/to/anime --dry-run

# 확인 프롬프트 없이 바로 실행
anivault organize /path/to/anime --yes

# 특정 확장자만 처리
anivault organize /path/to/anime --extensions .mkv .mp4

# 출력 디렉토리 지정
anivault organize /path/to/anime --output-dir /organized/anime

# Enhanced Organize (새로운 기능)
anivault organize /path/to/anime --enhanced --destination /organized/anime

# Enhanced Organize 미리보기
anivault organize /path/to/anime --enhanced --dry-run --destination /organized/anime

# 유사성 임계값 조정 (0.0-1.0, 기본값: 0.7)
anivault organize /path/to/anime --enhanced --similarity-threshold 0.8
```

#### 로그 관리 명령어

```bash
# 모든 작업 로그 목록 보기
anivault log list
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
anivault rollback 20241201_143022 --dry-run

# 되돌리기 실행 (확인 프롬프트 포함)
anivault rollback 20241201_143022

# 확인 프롬프트 없이 바로 되돌리기
anivault rollback 20241201_143022 --yes
```

#### 다른 유용한 명령어

```bash
# 전체 도움말 보기
anivault --help

# 특정 명령어 도움말 보기
anivault organize --help
anivault log --help
anivault rollback --help

# 시스템 구성 요소 검증
anivault verify --all
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

### Task Master 사용

프로젝트 초기화 후 개발을 시작하려면:

```bash
# Taskmaster 초기화 (이미 완료됨)
task-master init

# PRD 파싱하여 작업 생성
task-master parse-prd .taskmaster/docs/prd.txt

# 다음 작업 확인
task-master next
```

## 라이선스

MIT License
