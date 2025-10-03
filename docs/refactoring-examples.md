# 리팩터링 예제 가이드

이 문서는 AniVault 프로젝트에서 실제로 적용된 리팩터링 사례들을 통해 코드 품질 개선 방법을 보여줍니다. Before/After 코드 비교를 통해 구체적인 개선점을 명확히 하고, 단계별 리팩터링 과정을 설명합니다.

## 목차

1. [매직 값 제거 예제](#매직-값-제거-예제)
2. [함수 분리 예제](#함수-분리-예제)
3. [에러 처리 개선 예제](#에러-처리-개선-예제)
4. [단계별 리팩터링 과정](#단계별-리팩터링-과정)
5. [테스트 작성 방법](#테스트-작성-방법)
6. [검증 방법](#검증-방법)

## 매직 값 제거 예제

### 예제 1: CLI 메시지 상수화

#### Before: 매직 문자열 사용

```python
# ❌ BAD: 매직 문자열 하드코딩
def display_scan_results(results: List[Dict[str, Any]]) -> None:
    """스캔 결과를 표시합니다."""
    if not results:
        print("[red]Error during scan: No files found[/red]")  # ❌ 매직 문자열
        return

    print("[green]Scan completed successfully[/green]")  # ❌ 매직 문자열
    print(f"[blue]Found {len(results)} files[/blue]")  # ❌ 매직 문자열

    for result in results:
        if result.get('confidence', 0) < 0.8:  # ❌ 매직 넘버
            print(f"[yellow]Low confidence match: {result['confidence']:.2f}[/yellow]")  # ❌ 매직 문자열
        else:
            print(f"[green]High confidence match: {result['filename']}[/green]")  # ❌ 매직 문자열
```

#### After: 상수 사용

```python
# ✅ GOOD: 상수 사용
from anivault.shared.constants.cli import (
    ERROR_SCAN_MESSAGE,
    SUCCESS_SCAN_MESSAGE,
    WARNING_LOW_CONFIDENCE,
    DEFAULT_CONFIDENCE_THRESHOLD
)

def display_scan_results(results: List[Dict[str, Any]]) -> None:
    """스캔 결과를 표시합니다."""
    if not results:
        print(ERROR_SCAN_MESSAGE.format(e="No files found"))
        return

    print(SUCCESS_SCAN_MESSAGE)
    print(f"[blue]Found {len(results)} files[/blue]")

    for result in results:
        confidence = result.get('confidence', 0)
        if confidence < DEFAULT_CONFIDENCE_THRESHOLD:
            print(WARNING_LOW_CONFIDENCE.format(confidence=confidence))
        else:
            print(f"[green]High confidence match: {result['filename']}[/green]")
```

### 예제 2: 파일 형식 상수화

#### Before: 매직 문자열 사용

```python
# ❌ BAD: 매직 문자열 하드코딩
def is_video_file(filename: str) -> bool:
    """비디오 파일인지 확인합니다."""
    video_extensions = ['.mkv', '.mp4', '.avi', '.mov', '.wmv']  # ❌ 매직 문자열
    return any(filename.lower().endswith(ext) for ext in video_extensions)

def is_subtitle_file(filename: str) -> bool:
    """자막 파일인지 확인합니다."""
    subtitle_extensions = ['.srt', '.ass', '.vtt', '.sub']  # ❌ 매직 문자열
    return any(filename.lower().endswith(ext) for ext in subtitle_extensions)

def process_file(filename: str) -> None:
    """파일을 처리합니다."""
    if is_video_file(filename):
        process_video(filename)
    elif is_subtitle_file(filename):
        process_subtitle(filename)
    else:
        print(f"[yellow]Unsupported file type: {filename}[/yellow]")  # ❌ 매직 문자열
```

#### After: 상수 사용

```python
# ✅ GOOD: 상수 사용
from anivault.shared.constants.file_formats import (
    SUPPORTED_VIDEO_EXTENSIONS,
    SUBTITLE_EXTENSIONS
)

def is_video_file(filename: str) -> bool:
    """비디오 파일인지 확인합니다."""
    return any(filename.lower().endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS)

def is_subtitle_file(filename: str) -> bool:
    """자막 파일인지 확인합니다."""
    return any(filename.lower().endswith(ext) for ext in SUBTITLE_EXTENSIONS)

def process_file(filename: str) -> None:
    """파일을 처리합니다."""
    if is_video_file(filename):
        process_video(filename)
    elif is_subtitle_file(filename):
        process_subtitle(filename)
    else:
        print(f"[yellow]Unsupported file type: {filename}[/yellow]")
```

## 함수 분리 예제

### 예제 1: CLI 핸들러 분리

#### Before: 거대한 함수

```python
# ❌ BAD: 모든 것을 하는 거대한 함수
def handle_organize_command(args: Any) -> int:
    """organize 명령어를 처리합니다."""
    # 1. 로깅 설정
    logger = logging.getLogger(__name__)
    logger.info("Starting organize command")

    # 2. 콘솔 설정
    console = Console()

    # 3. 디렉토리 검증
    directory = args.directory
    if not os.path.exists(directory):
        console.print(f"[red]Directory not found: {directory}[/red]")
        return 1

    if not os.path.isdir(directory):
        console.print(f"[red]Path is not a directory: {directory}[/red]")
        return 1

    # 4. 스캔된 파일 가져오기
    scan_file = os.path.join(directory, "scan_results.json")
    if not os.path.exists(scan_file):
        console.print(f"[red]Scan results not found: {scan_file}[/red]")
        return 1

    try:
        with open(scan_file, 'r', encoding='utf-8') as f:
            scanned_files = json.load(f)
    except Exception as e:
        console.print(f"[red]Error reading scan results: {e}[/red]")
        return 1

    # 5. 파일 정리 계획 생성
    organize_plan = []
    for file_info in scanned_files:
        if file_info.get('tmdb_data'):
            series_name = file_info['tmdb_data']['name']
            season = file_info['tmdb_data'].get('season_number', 1)
            episode = file_info.get('episode', '01')
            quality = file_info.get('quality', 'Unknown')

            new_name = f"{series_name} S{season:02d}E{episode:02d} {quality}.mkv"
            organize_plan.append({
                'old_path': file_info['path'],
                'new_name': new_name,
                'series_name': series_name
            })

    # 6. 파일 정리 실행
    success_count = 0
    for plan_item in organize_plan:
        try:
            old_path = plan_item['old_path']
            new_name = plan_item['new_name']
            new_path = os.path.join(directory, new_name)

            if os.path.exists(new_path):
                console.print(f"[yellow]File already exists: {new_path}[/yellow]")
                continue

            shutil.move(old_path, new_path)
            console.print(f"[green]Moved: {os.path.basename(old_path)} -> {new_name}[/green]")
            success_count += 1

        except Exception as e:
            console.print(f"[red]Error moving file: {e}[/red]")
            continue

    # 7. 결과 출력
    console.print(f"[green]Organization completed: {success_count} files moved[/green]")
    logger.info(f"Organization completed: {success_count} files moved")
    return 0
```

#### After: 책임별 함수 분리

```python
# ✅ GOOD: 책임별 함수 분리
from anivault.shared.constants.system import (
    CLI_INFO_COMMAND_STARTED,
    CLI_INFO_COMMAND_COMPLETED,
)
from anivault.shared.errors import (
    ApplicationError,
    InfrastructureError,
    ErrorCode,
    ErrorContext,
)

def handle_organize_command(args: Any) -> int:
    """organize 명령어를 처리합니다 - 오케스트레이션."""
    logger = logging.getLogger(__name__)
    logger.info(CLI_INFO_COMMAND_STARTED.format(command="organize"))

    try:
        console = _setup_organize_console()
        directory = _validate_organize_directory(args, console)
        if directory is None:
            return 1

        scanned_files = _get_scanned_files(args, directory, console)
        if not scanned_files:
            return 0

        plan = _generate_organization_plan(scanned_files)
        return _execute_organization_plan(plan, args, console)

    except ApplicationError as e:
        _handle_application_error(e, console)
        return 1
    except InfrastructureError as e:
        _handle_infrastructure_error(e, console)
        return 1
    except Exception as e:
        _handle_unexpected_error(e, console)
        return 1

def _setup_organize_console() -> Console:
    """organize 명령어용 콘솔 설정 - 단일 책임: 콘솔 설정."""
    return Console()

def _validate_organize_directory(args: Any, console: Console) -> Optional[str]:
    """organize 디렉토리 검증 - 단일 책임: 디렉토리 검증."""
    directory = args.directory

    if not os.path.exists(directory):
        console.print(f"[red]Directory not found: {directory}[/red]")
        return None

    if not os.path.isdir(directory):
        console.print(f"[red]Path is not a directory: {directory}[/red]")
        return None

    return directory

def _get_scanned_files(args: Any, directory: str, console: Console) -> List[Dict[str, Any]]:
    """스캔된 파일 정보 가져오기 - 단일 책임: 파일 정보 로딩."""
    scan_file = os.path.join(directory, "scan_results.json")

    if not os.path.exists(scan_file):
        console.print(f"[red]Scan results not found: {scan_file}[/red]")
        return []

    try:
        with open(scan_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise InfrastructureError(
            ErrorCode.FILE_READ_ERROR,
            f"Error reading scan results: {e}",
            ErrorContext(file_path=scan_file, operation="read_scan_results"),
            original_error=e
        ) from e

def _generate_organization_plan(scanned_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """파일 정리 계획 생성 - 단일 책임: 계획 생성."""
    plan = []

    for file_info in scanned_files:
        if not file_info.get('tmdb_data'):
            continue

        series_name = file_info['tmdb_data']['name']
        season = file_info['tmdb_data'].get('season_number', 1)
        episode = file_info.get('episode', '01')
        quality = file_info.get('quality', 'Unknown')

        new_name = f"{series_name} S{season:02d}E{episode:02d} {quality}.mkv"
        plan.append({
            'old_path': file_info['path'],
            'new_name': new_name,
            'series_name': series_name
        })

    return plan

def _execute_organization_plan(plan: List[Dict[str, Any]], args: Any, console: Console) -> int:
    """파일 정리 계획 실행 - 단일 책임: 계획 실행."""
    success_count = 0

    for plan_item in plan:
        try:
            result = _move_file(plan_item, args.directory, console)
            if result:
                success_count += 1
        except Exception as e:
            console.print(f"[red]Error moving file: {e}[/red]")
            continue

    console.print(f"[green]Organization completed: {success_count} files moved[/green]")
    return 0

def _move_file(plan_item: Dict[str, Any], directory: str, console: Console) -> bool:
    """파일 이동 - 단일 책임: 파일 이동."""
    old_path = plan_item['old_path']
    new_name = plan_item['new_name']
    new_path = os.path.join(directory, new_name)

    if os.path.exists(new_path):
        console.print(f"[yellow]File already exists: {new_path}[/yellow]")
        return False

    shutil.move(old_path, new_path)
    console.print(f"[green]Moved: {os.path.basename(old_path)} -> {new_name}[/green]")
    return True

def _handle_application_error(error: ApplicationError, console: Console) -> None:
    """애플리케이션 에러 처리 - 단일 책임: 애플리케이션 에러 처리."""
    console.print(f"[red]Application error: {error.message}[/red]")
    logger = logging.getLogger(__name__)
    logger.error(
        "Application error in organize command",
        extra={"context": error.context, "error_code": error.code},
    )

def _handle_infrastructure_error(error: InfrastructureError, console: Console) -> None:
    """인프라 에러 처리 - 단일 책임: 인프라 에러 처리."""
    console.print(f"[red]Infrastructure error: {error.message}[/red]")
    logger = logging.getLogger(__name__)
    logger.error(
        "Infrastructure error in organize command",
        extra={"context": error.context, "error_code": error.code},
    )

def _handle_unexpected_error(error: Exception, console: Console) -> None:
    """예상치 못한 에러 처리 - 단일 책임: 예상치 못한 에러 처리."""
    console.print(f"[red]Unexpected error: {error}[/red]")
    logger = logging.getLogger(__name__)
    logger.exception("Unexpected error in organize command")
```

### 예제 2: 파일 처리 로직 분리

#### Before: 복잡한 파일 처리 함수

```python
# ❌ BAD: 복잡한 파일 처리 함수
def process_anime_file(file_path: str, api_key: str) -> Dict[str, Any]:
    """애니메이션 파일을 처리합니다."""
    # 1. 파일 검증
    if not os.path.exists(file_path):
        return {"error": "File not found", "success": False}

    if not os.path.isfile(file_path):
        return {"error": "Path is not a file", "success": False}

    # 2. 파일명 파싱
    filename = os.path.basename(file_path)
    try:
        parsed = anitopy.parse(filename)
        if not parsed:
            return {"error": "Failed to parse filename", "success": False}
    except Exception as e:
        return {"error": f"Parsing error: {e}", "success": False}

    # 3. TMDB API 호출
    series_name = parsed.get('anime_title', '')
    if not series_name:
        return {"error": "No series name found", "success": False}

    try:
        response = requests.get(
            "https://api.themoviedb.org/3/search/tv",
            params={
                'api_key': api_key,
                'query': series_name,
                'language': 'ko-KR'
            },
            timeout=30
        )
        response.raise_for_status()
        tmdb_data = response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"TMDB API error: {e}", "success": False}

    # 4. 결과 반환
    return {
        "success": True,
        "file_path": file_path,
        "parsed": parsed,
        "tmdb_data": tmdb_data,
        "series_name": series_name
    }
```

#### After: 책임별 함수 분리

```python
# ✅ GOOD: 책임별 함수 분리
from anivault.shared.constants.api import DEFAULT_REQUEST_TIMEOUT
from anivault.shared.errors import (
    create_file_not_found_error,
    create_validation_error,
    create_api_error,
    create_parsing_error,
)

def process_anime_file(file_path: str, api_key: str) -> Dict[str, Any]:
    """애니메이션 파일을 처리합니다 - 오케스트레이션."""
    try:
        _validate_file_path(file_path)
        parsed = _parse_anime_filename(file_path)
        tmdb_data = _fetch_tmdb_data(parsed['anime_title'], api_key)

        return {
            "success": True,
            "file_path": file_path,
            "parsed": parsed,
            "tmdb_data": tmdb_data,
            "series_name": parsed['anime_title']
        }
    except AniVaultError as e:
        return {"error": e.message, "success": False, "error_code": e.code}

def _validate_file_path(file_path: str) -> None:
    """파일 경로 검증 - 단일 책임: 파일 경로 검증."""
    if not os.path.exists(file_path):
        raise create_file_not_found_error(
            file_path=file_path,
            operation="process_anime_file"
        )

    if not os.path.isfile(file_path):
        raise create_validation_error(
            message="Path is not a file",
            field="file_path",
            operation="process_anime_file"
        )

def _parse_anime_filename(file_path: str) -> Dict[str, Any]:
    """애니메이션 파일명 파싱 - 단일 책임: 파일명 파싱."""
    filename = os.path.basename(file_path)

    try:
        parsed = anitopy.parse(filename)
        if not parsed:
            raise create_parsing_error(
                message="Failed to parse filename",
                file_path=file_path,
                operation="parse_anime_filename"
            )

        if not parsed.get('anime_title'):
            raise create_validation_error(
                message="No series name found in filename",
                field="anime_title",
                operation="parse_anime_filename"
            )

        return parsed
    except Exception as e:
        if isinstance(e, AniVaultError):
            raise
        raise create_parsing_error(
            message=f"Parsing error: {e}",
            file_path=file_path,
            operation="parse_anime_filename",
            original_error=e
        ) from e

def _fetch_tmdb_data(series_name: str, api_key: str) -> Dict[str, Any]:
    """TMDB 데이터 가져오기 - 단일 책임: API 호출."""
    try:
        response = requests.get(
            "https://api.themoviedb.org/3/search/tv",
            params={
                'api_key': api_key,
                'query': series_name,
                'language': 'ko-KR'
            },
            timeout=DEFAULT_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise create_api_error(
            message=f"TMDB API error: {e}",
            operation="fetch_tmdb_data",
            original_error=e
        ) from e
```

## 에러 처리 개선 예제

### 예제 1: 일반 Exception에서 구조적 에러 처리로 개선

#### Before: 일반 Exception 사용

```python
# ❌ BAD: 일반 Exception 사용
def process_file(file_path: str) -> str:
    """파일을 처리합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return ""
    except PermissionError:
        print(f"Permission denied: {file_path}")
        return ""
    except Exception as e:
        print(f"Unexpected error: {e}")
        return ""
```

#### After: 구조적 에러 처리

```python
# ✅ GOOD: 구조적 에러 처리
from anivault.shared.errors import (
    create_file_not_found_error,
    create_permission_denied_error,
    InfrastructureError,
    ErrorCode,
    ErrorContext,
)

def process_file(file_path: str) -> str:
    """파일을 처리합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError as e:
        raise create_file_not_found_error(
            file_path=file_path,
            operation="process_file",
            original_error=e
        ) from e
    except PermissionError as e:
        raise create_permission_denied_error(
            path=file_path,
            operation="process_file",
            original_error=e
        ) from e
    except Exception as e:
        raise InfrastructureError(
            ErrorCode.FILE_READ_ERROR,
            f"Unexpected error reading file: {file_path}",
            ErrorContext(file_path=file_path, operation="process_file"),
            original_error=e
        ) from e
```

### 예제 2: 에러 컨텍스트 활용

#### Before: 컨텍스트 없는 에러 처리

```python
# ❌ BAD: 컨텍스트 없는 에러 처리
def call_tmdb_api(query: str, api_key: str) -> Dict[str, Any]:
    """TMDB API를 호출합니다."""
    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/search/tv",
            params={"api_key": api_key, "query": query},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("API timeout")
        raise
    except requests.exceptions.RequestException as e:
        print(f"API error: {e}")
        raise
```

#### After: 컨텍스트 포함 에러 처리

```python
# ✅ GOOD: 컨텍스트 포함 에러 처리
from anivault.shared.errors import (
    InfrastructureError,
    ErrorCode,
    ErrorContext,
)

def call_tmdb_api(query: str, api_key: str) -> Dict[str, Any]:
    """TMDB API를 호출합니다."""
    context = ErrorContext(
        operation="call_tmdb_api",
        additional_data={
            "query": query,
            "api_key_length": len(api_key),
            "endpoint": "search/tv"
        }
    )

    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/search/tv",
            params={"api_key": api_key, "query": query},
            timeout=DEFAULT_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout as e:
        raise InfrastructureError(
            ErrorCode.TMDB_API_TIMEOUT,
            f"TMDB API timeout for query: {query}",
            context,
            original_error=e
        ) from e
    except requests.exceptions.RequestException as e:
        raise InfrastructureError(
            ErrorCode.TMDB_API_CONNECTION_ERROR,
            f"TMDB API connection failed for query: {query}",
            context,
            original_error=e
        ) from e
```

## 단계별 리팩터링 과정

### 1단계: 리팩터링 계획 수립

#### 분석 단계
1. **현재 코드 분석**
   - 함수 길이 측정
   - 매직 값 식별
   - 에러 처리 패턴 분석
   - 책임 분리 가능성 검토

2. **개선 목표 설정**
   - 함수 길이 80줄 이하
   - 매직 값 0개
   - 구조적 에러 처리 적용
   - 단일 책임 원칙 준수

3. **리팩터링 계획 수립**
   - 함수 분리 계획
   - 상수 추출 계획
   - 에러 처리 개선 계획
   - 테스트 계획

### 2단계: 단계별 실행

#### Step 1: 매직 값 제거
```python
# 1. 매직 값 식별
magic_values = detect_magic_values()

# 2. 상수 정의
# src/anivault/shared/constants/example.py
DEFAULT_TIMEOUT = 30
DEFAULT_CONFIDENCE_THRESHOLD = 0.8
SUPPORTED_EXTENSIONS = ['.mkv', '.mp4', '.avi']

# 3. 상수 사용
from anivault.shared.constants.example import (
    DEFAULT_TIMEOUT,
    DEFAULT_CONFIDENCE_THRESHOLD,
    SUPPORTED_EXTENSIONS
)
```

#### Step 2: 함수 분리
```python
# 1. 거대 함수 식별
long_functions = validate_function_length()

# 2. 책임별 함수 분리
def original_function():
    # 오케스트레이션만 담당
    result1 = _step1_function()
    result2 = _step2_function(result1)
    return _step3_function(result2)

def _step1_function():
    # 단일 책임: 첫 번째 단계
    pass

def _step2_function(input_data):
    # 단일 책임: 두 번째 단계
    pass

def _step3_function(input_data):
    # 단일 책임: 세 번째 단계
    pass
```

#### Step 3: 에러 처리 개선
```python
# 1. 일반 Exception 식별
# 2. 구체적인 에러 클래스 사용
# 3. 컨텍스트 정보 추가
# 4. 사용자 친화적 메시지 제공
```

### 3단계: 검증

#### 자동 검증
```bash
# 품질 검증 실행
python scripts/validate_code_quality.py
python scripts/detect_magic_values.py
python scripts/check_duplicates.py
python scripts/validate_function_length.py
python scripts/validate_error_handling.py
```

#### 수동 검증
- 코드 가독성 검토
- 비즈니스 로직 정확성 검토
- 테스트 커버리지 검토

## 테스트 작성 방법

### 단위 테스트 작성

#### Before: 테스트 없는 코드
```python
# ❌ BAD: 테스트 없는 코드
def calculate_confidence_score(match_data: Dict[str, Any]) -> float:
    """매칭 신뢰도 점수를 계산합니다."""
    if not match_data:
        return 0.0

    base_score = 0.5
    if match_data.get('exact_match'):
        base_score += 0.3
    if match_data.get('year_match'):
        base_score += 0.2

    return min(base_score, 1.0)
```

#### After: 테스트 포함 코드
```python
# ✅ GOOD: 테스트 포함 코드
def calculate_confidence_score(match_data: Dict[str, Any]) -> float:
    """매칭 신뢰도 점수를 계산합니다."""
    if not match_data:
        return 0.0

    base_score = 0.5
    if match_data.get('exact_match'):
        base_score += 0.3
    if match_data.get('year_match'):
        base_score += 0.2

    return min(base_score, 1.0)

# 테스트 코드
import pytest
from unittest.mock import patch

class TestCalculateConfidenceScore:
    """calculate_confidence_score 함수 테스트."""

    def test_empty_match_data(self):
        """빈 매칭 데이터 테스트."""
        result = calculate_confidence_score({})
        assert result == 0.0

    def test_none_match_data(self):
        """None 매칭 데이터 테스트."""
        result = calculate_confidence_score(None)
        assert result == 0.0

    def test_base_score_only(self):
        """기본 점수만 있는 경우 테스트."""
        match_data = {"title": "Test"}
        result = calculate_confidence_score(match_data)
        assert result == 0.5

    def test_exact_match(self):
        """정확한 매칭이 있는 경우 테스트."""
        match_data = {"exact_match": True}
        result = calculate_confidence_score(match_data)
        assert result == 0.8

    def test_year_match(self):
        """연도 매칭이 있는 경우 테스트."""
        match_data = {"year_match": True}
        result = calculate_confidence_score(match_data)
        assert result == 0.7

    def test_both_matches(self):
        """정확한 매칭과 연도 매칭이 모두 있는 경우 테스트."""
        match_data = {"exact_match": True, "year_match": True}
        result = calculate_confidence_score(match_data)
        assert result == 1.0

    def test_max_score_cap(self):
        """최대 점수 제한 테스트."""
        match_data = {
            "exact_match": True,
            "year_match": True,
            "extra_bonus": True
        }
        result = calculate_confidence_score(match_data)
        assert result == 1.0
```

### 통합 테스트 작성

```python
# tests/integration/test_file_processing.py
import pytest
from unittest.mock import patch, Mock
from anivault.core.processor import process_anime_file

class TestFileProcessingIntegration:
    """파일 처리 통합 테스트."""

    @patch('anivault.core.processor.requests.get')
    def test_process_anime_file_success(self, mock_get):
        """애니메이션 파일 처리 성공 테스트."""
        # Given
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": [{"name": "Test Anime"}]}
        mock_get.return_value = mock_response

        # When
        result = process_anime_file("test.mkv", "test_api_key")

        # Then
        assert result["success"] is True
        assert "parsed" in result
        assert "tmdb_data" in result

    @patch('anivault.core.processor.anitopy.parse')
    def test_process_anime_file_parsing_error(self, mock_parse):
        """파일명 파싱 에러 테스트."""
        # Given
        mock_parse.return_value = None

        # When
        result = process_anime_file("test.mkv", "test_api_key")

        # Then
        assert result["success"] is False
        assert "error" in result
        assert "parsing" in result["error"].lower()

    @patch('anivault.core.processor.requests.get')
    def test_process_anime_file_api_error(self, mock_get):
        """TMDB API 에러 테스트."""
        # Given
        mock_get.side_effect = requests.exceptions.RequestException("API Error")

        # When
        result = process_anime_file("test.mkv", "test_api_key")

        # Then
        assert result["success"] is False
        assert "error" in result
        assert "api" in result["error"].lower()
```

### 테스트 커버리지 측정

```bash
# 테스트 커버리지 실행
pytest --cov=src/anivault --cov-report=html --cov-report=term

# 특정 모듈 커버리지
pytest --cov=src/anivault/core/processor --cov-report=html

# 커버리지 기준 설정
pytest --cov=src/anivault --cov-fail-under=80
```

## 검증 방법

### 리팩터링 후 기능 검증

#### 1. 단위 테스트 실행
```bash
# 모든 테스트 실행
pytest

# 특정 모듈 테스트
pytest tests/core/test_processor.py

# 상세 출력
pytest -v
```

#### 2. 통합 테스트 실행
```bash
# 통합 테스트 실행
pytest tests/integration/

# 특정 시나리오 테스트
pytest tests/integration/test_file_processing.py::TestFileProcessingIntegration::test_process_anime_file_success
```

### 성능 검증

#### 1. 성능 벤치마크
```python
# tests/performance/test_processor_performance.py
import time
import pytest
from anivault.core.processor import process_anime_file

@pytest.mark.performance
def test_process_anime_file_performance():
    """파일 처리 성능 테스트."""
    start_time = time.time()

    # 성능 테스트 실행
    result = process_anime_file("test.mkv", "test_api_key")

    end_time = time.time()
    execution_time = end_time - start_time

    # 성능 기준 검증 (1초 이내)
    assert execution_time < 1.0
    assert result["success"] is True
```

#### 2. 메모리 사용량 검증
```python
# tests/performance/test_memory_usage.py
import psutil
import pytest
from anivault.core.processor import process_anime_file

@pytest.mark.performance
def test_memory_usage():
    """메모리 사용량 테스트."""
    process = psutil.Process()
    memory_before = process.memory_info().rss

    # 메모리 집약적 작업 실행
    result = process_anime_file("test.mkv", "test_api_key")

    memory_after = process.memory_info().rss
    memory_used = memory_after - memory_before

    # 메모리 사용량 기준 검증 (100MB 이하)
    assert memory_used < 100 * 1024 * 1024
    assert result["success"] is True
```

### 코드 품질 검증

#### 1. 자동화 도구 실행
```bash
# 종합 품질 검증
python scripts/validate_code_quality.py

# 개별 검증
python scripts/detect_magic_values.py
python scripts/check_duplicates.py
python scripts/validate_function_length.py
python scripts/validate_error_handling.py
```

#### 2. 품질 점수 확인
```bash
# 품질 점수 계산
python scripts/calculate_quality_score.py

# 목표: 80점 이상
```

#### 3. 코드 리뷰
- 동료 리뷰 진행
- 체크리스트 기반 검토
- 개선 사항 도출

---

이 리팩터링 예제 가이드를 통해 AniVault 프로젝트의 코드 품질을 지속적으로 개선할 수 있습니다. 각 예제는 실제 프로젝트에서 적용된 패턴을 바탕으로 작성되었으며, 단계별로 따라하면 효과적인 리팩터링을 수행할 수 있습니다.
