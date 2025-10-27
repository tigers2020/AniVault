@chcp 65001 >nul 2>&1
@echo off
REM AniVault GUI Launcher
REM This batch file runs the AniVault GUI application.

echo.
echo ========================================
echo    AniVault GUI Launcher
echo ========================================
echo.

REM Set current directory to project root
cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed.
    echo Please install Python 3.11 or higher.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if required Python packages are installed
echo Checking dependencies...
python -c "import PySide6" >nul 2>&1
if %errorlevel% neq 0 (
    echo PySide6 is not installed.
    echo Please install it with:
    echo    pip install PySide6
    pause
    exit /b 1
)

python -c "import pydantic" >nul 2>&1
if %errorlevel% neq 0 (
    echo Pydantic is not installed.
    echo Please install it with:
    echo    pip install pydantic
    pause
    exit /b 1
)

echo All dependencies are installed.
echo.

REM Run GUI application
echo Starting AniVault GUI...
echo.

python -m src.anivault.gui.app

REM Check execution result
if %errorlevel% neq 0 (
    echo.
    echo Error occurred while running GUI application.
    echo Error code: %errorlevel%
    echo.
    echo Troubleshooting:
    echo    1. Check Python version (3.11+ required)
    echo    2. Verify required packages are installed
    echo    3. Make sure you're running from project directory
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo AniVault GUI exited successfully.
pause
