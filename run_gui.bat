@echo off
REM AniVault GUI 실행 스크립트
REM 이 배치 파일은 AniVault GUI 애플리케이션을 실행합니다.

echo.
echo ========================================
echo    AniVault GUI Launcher
echo ========================================
echo.

REM 현재 디렉터리를 프로젝트 루트로 설정
cd /d "%~dp0"

REM Python이 설치되어 있는지 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되어 있지 않습니다.
    echo 💡 Python 3.11 이상을 설치해주세요.
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 필요한 Python 패키지가 설치되어 있는지 확인
echo 🔍 의존성 확인 중...
python -c "import PySide6" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ PySide6가 설치되어 있지 않습니다.
    echo 💡 다음 명령어로 설치해주세요:
    echo    pip install PySide6
    pause
    exit /b 1
)

python -c "import pydantic" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Pydantic이 설치되어 있지 않습니다.
    echo 💡 다음 명령어로 설치해주세요:
    echo    pip install pydantic
    pause
    exit /b 1
)

echo ✅ 모든 의존성이 확인되었습니다.
echo.

REM GUI 애플리케이션 실행
echo 🚀 AniVault GUI를 시작합니다...
echo.

python -m src.anivault.gui.app

REM 실행 결과 확인
if %errorlevel% neq 0 (
    echo.
    echo ❌ GUI 애플리케이션 실행 중 오류가 발생했습니다.
    echo 💡 오류 코드: %errorlevel%
    echo.
    echo 🔧 문제 해결 방법:
    echo    1. Python 버전 확인 (3.11 이상 필요)
    echo    2. 필요한 패키지 설치 확인
    echo    3. 프로젝트 디렉터리에서 실행했는지 확인
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo ✅ AniVault GUI가 정상적으로 종료되었습니다.
pause
