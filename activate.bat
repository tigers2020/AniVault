@echo off
REM AniVault venv activation script for CMD
REM Usage: activate.bat

setlocal

set "VENV_PATH=%~dp0venv"
set "ACTIVATE_SCRIPT=%VENV_PATH%\Scripts\activate.bat"

if not exist "%ACTIVATE_SCRIPT%" (
    echo ❌ Virtual environment not found at: %VENV_PATH%
    echo 💡 Create it with: python -m venv venv
    exit /b 1
)

echo 🔧 Activating AniVault virtual environment...
call "%ACTIVATE_SCRIPT%"

if %ERRORLEVEL% EQU 0 (
    echo ✅ Virtual environment activated!
    echo 📍 Project: AniVault
    python --version
) else (
    echo ❌ Failed to activate virtual environment
    exit /b 1
)

endlocal
