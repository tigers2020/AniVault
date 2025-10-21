@echo off
REM AniVault GUI 실행 배치 파일

echo Starting AniVault GUI...
python run_gui.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ AniVault GUI failed to start
    echo 💡 Make sure Python is installed and accessible
    pause
)
