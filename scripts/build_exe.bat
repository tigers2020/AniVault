@echo off
REM Build script for AniVault Windows executable
REM This script runs the Python build script with appropriate settings

echo ========================================
echo AniVault Build Script
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

REM Run the build script
python build.py --clean %*

if errorlevel 1 (
    echo.
    echo ========================================
    echo Build FAILED
    echo ========================================
    exit /b 1
) else (
    echo.
    echo ========================================
    echo Build SUCCEEDED
    echo ========================================
    echo.
    echo The executable can be found in the dist\ folder
    echo.
)

exit /b 0

