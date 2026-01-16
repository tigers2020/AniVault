# AniVault GUI Launcher (PowerShell)
# This script runs the AniVault GUI application.

# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "========================================"
Write-Host "   AniVault GUI Launcher"
Write-Host "========================================"
Write-Host ""

# Set current directory to script directory
Set-Location -Path $PSScriptRoot

# Determine Python command
$PythonCmd = "python"
if (Test-Path "venv\Scripts\python.exe") {
    $PythonCmd = "venv\Scripts\python.exe"
    Write-Host "[INFO] Using virtual environment."
} else {
    Write-Host "[INFO] Using system Python."
}

# Check if Python is installed
try {
    $null = & $PythonCmd --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
} catch {
    Write-Host "[ERROR] Python is not installed."
    Write-Host "[INFO] Please install Python 3.11 or higher."
    Write-Host "   https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check and auto-install required Python packages
Write-Host "[CHECK] Checking dependencies..."

# Check if requirements.txt exists
if (-not (Test-Path "requirements.txt")) {
    Write-Host "[ERROR] requirements.txt file not found."
    Write-Host "[INFO] Please run this script from the project root directory."
    Read-Host "Press Enter to exit"
    exit 1
}

# Check and upgrade pip
Write-Host "[INFO] Checking pip upgrade..."
& $PythonCmd -m pip install --upgrade pip --quiet 2>&1 | Out-Null

# Use Python script for dependency checking (with debug logging)
Write-Host "[CHECK] Checking dependencies..."
& $PythonCmd check_dependencies.py $PythonCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Dependency check or installation failed."
    Write-Host "[INFO] Please check the output above for details."
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host ""

# Launch GUI application
Write-Host "[RUN] Starting AniVault GUI..."
Write-Host ""

# Execute with Python path
& $PythonCmd run_gui.py

# Check execution result
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Error occurred while running GUI application."
    Write-Host "[INFO] Error code: $LASTEXITCODE"
    Write-Host ""
    Write-Host "[HELP] Troubleshooting:"
    Write-Host "   1. Check Python version (3.11 or higher required)"
    Write-Host "   2. Verify required packages are installed"
    Write-Host "   3. Ensure you are running from project directory"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "[OK] AniVault GUI exited normally."
Read-Host "Press Enter to exit"
