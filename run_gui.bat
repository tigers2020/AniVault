@chcp 65001 >nul 2>&1
@echo off
REM AniVault GUI 실행 스크립트
REM 이 배치 파일은 AniVault GUI 애플리케이션을 실행합니다.

REM UTF-8 환경 설정
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo.
echo ========================================
echo    AniVault GUI Launcher
echo ========================================
echo.

REM 현재 디렉터리를 프로젝트 루트로 설정
cd /d "%~dp0"

REM 가상환경이 있으면 활성화, 없으면 시스템 Python 사용
set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" (
    set PYTHON_CMD=venv\Scripts\python.exe
    echo [INFO] 가상환경을 사용합니다.
) else (
    echo [INFO] 시스템 Python을 사용합니다.
)

REM Python이 설치되어 있는지 확인
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python이 설치되어 있지 않습니다.
    echo [INFO] Python 3.11 이상을 설치해주세요.
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 필요한 Python 패키지가 설치되어 있는지 확인 및 자동 설치
echo [CHECK] 의존성 확인 중...

REM requirements.txt 파일 존재 확인
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt 파일을 찾을 수 없습니다.
    echo [INFO] 프로젝트 루트 디렉터리에서 실행해주세요.
    pause
    exit /b 1
)

REM pip 업그레이드 확인 및 설치
echo [INFO] pip 업그레이드 확인 중...
%PYTHON_CMD% -m pip install --upgrade pip --quiet >nul 2>&1

REM 핵심 패키지 확인 (빠른 체크)
%PYTHON_CMD% -c "import PySide6" >nul 2>&1
set MISSING_DEPS=0
if %errorlevel% neq 0 (
    set MISSING_DEPS=1
)

%PYTHON_CMD% -c "import pydantic" >nul 2>&1
if %errorlevel% neq 0 (
    set MISSING_DEPS=1
)

%PYTHON_CMD% -c "import dependency_injector" >nul 2>&1
if %errorlevel% neq 0 (
    set MISSING_DEPS=1
)

REM 의존성이 없으면 자동 설치
if %MISSING_DEPS%==1 (
    echo [INSTALL] 누락된 패키지를 자동으로 설치합니다...
    echo [INFO] 이 작업은 처음 실행 시에만 필요하며 시간이 걸릴 수 있습니다.
    echo.

    %PYTHON_CMD% -m pip install -r requirements.txt

    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] 패키지 설치 중 오류가 발생했습니다.
        echo [INFO] 다음 명령어를 수동으로 실행해보세요:
        echo    pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )

    echo.
    echo [OK] 모든 패키지가 성공적으로 설치되었습니다.
    echo.
) else (
    echo [OK] 모든 의존성이 확인되었습니다.
    echo.
)

REM GUI 애플리케이션 실행
echo [RUN] AniVault GUI를 시작합니다...
echo.

REM Python 경로 설정 후 실행
%PYTHON_CMD% run_gui.py

REM 실행 결과 확인
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] GUI 애플리케이션 실행 중 오류가 발생했습니다.
    echo [INFO] 오류 코드: %errorlevel%
    echo.
    echo [HELP] 문제 해결 방법:
    echo    1. Python 버전 확인 (3.11 이상 필요)
    echo    2. 필요한 패키지 설치 확인
    echo    3. 프로젝트 디렉터리에서 실행했는지 확인
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo [OK] AniVault GUI가 정상적으로 종료되었습니다.
pause
