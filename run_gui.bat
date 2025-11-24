@echo off
chcp 65001 >nul 2>&1
REM AniVault GUI execution script
REM This batch file runs the AniVault GUI application.

REM UTF-8 environment setup
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo.
echo ========================================
echo    AniVault GUI Launcher
echo ========================================
echo.

REM Set current directory to project root
cd /d "%~dp0"

REM Use virtual environment if available, otherwise use system Python
set PYTHON_CMD=python
if exist "venv\Scripts\python.exe" (
    set PYTHON_CMD=venv\Scripts\python.exe
    echo [INFO] Using virtual environment.
) else (
    echo [INFO] Using system Python.
)

REM Check if Python is installed
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed.
    echo [INFO] Please install Python 3.11 or higher.
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check and auto-install required Python packages
echo [CHECK] Checking dependencies...

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo [ERROR] requirements.txt file not found.
    echo [INFO] Please run this script from the project root directory.
    pause
    exit /b 1
)

REM Check and upgrade pip
echo [INFO] Checking pip upgrade...
%PYTHON_CMD% -m pip install --upgrade pip --quiet >nul 2>&1

REM Check core packages (quick check)
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

REM Auto-install if dependencies are missing
if %MISSING_DEPS%==1 (
    echo [INSTALL] Installing missing packages automatically...
    echo [INFO] This is only needed on first run and may take some time.
    echo.

    %PYTHON_CMD% -m pip install -r requirements.txt

    if %errorlevel% neq 0 (
        echo.
        echo [ERROR] Error occurred during package installation.
        echo [INFO] Please try running manually:
        echo    pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )

    echo.
    echo [OK] All packages installed successfully.
    echo.
) else (
    echo [OK] All dependencies verified.
    echo.
)

REM Launch GUI application
echo [RUN] Starting AniVault GUI...
echo.

REM Execute with Python path
%PYTHON_CMD% run_gui.py

REM Check execution result
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Error occurred while running GUI application.
    echo [INFO] Error code: %errorlevel%
    echo.
    echo [HELP] Troubleshooting:
    echo    1. Check Python version (3.11 or higher required)
    echo    2. Verify required packages are installed
    echo    3. Ensure you are running from project directory
    echo.
    pause
    exit /b %errorlevel%
)

echo.
echo [OK] AniVault GUI exited normally.
pause
