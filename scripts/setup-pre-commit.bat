@echo off
REM Setup script for pre-commit hooks on Windows

echo 🔧 Setting up pre-commit hooks for AniVault...

REM Check if pre-commit is installed
where pre-commit >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 📦 Installing pre-commit...
    pip install pre-commit
)

REM Install pre-commit hooks
echo 🔗 Installing pre-commit hooks...
pre-commit install

REM Install pre-commit hooks for commit-msg
echo 🔗 Installing commit-msg hooks...
pre-commit install --hook-type commit-msg

REM Run pre-commit on all files to test
echo 🧪 Testing pre-commit hooks on all files...
pre-commit run --all-files

echo ✅ Pre-commit setup complete!
echo.
echo 📋 Available commands:
echo   pre-commit run --all-files    # Run all hooks on all files
echo   pre-commit run ^<hook-id^>      # Run specific hook
echo   pre-commit clean              # Clean pre-commit cache
echo   pre-commit uninstall          # Uninstall pre-commit hooks
echo.
echo 🎯 Pre-commit hooks will now run automatically on git commit!

pause
