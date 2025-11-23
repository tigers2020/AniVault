# AniVault venv activation script for PowerShell
# Usage: . .\activate.ps1  (note the dot and space before the script)
# Or: & .\activate.ps1

$ErrorActionPreference = "Stop"

$venvPath = Join-Path $PSScriptRoot "venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (-not (Test-Path $activateScript)) {
    Write-Host "❌ Virtual environment not found at: $venvPath" -ForegroundColor Red
    Write-Host "💡 Create it with: python -m venv venv" -ForegroundColor Yellow
    return
}

Write-Host "🔧 Activating AniVault virtual environment..." -ForegroundColor Green

# Execute activation script in current scope
. $activateScript

if ($?) {
    Write-Host "✅ Virtual environment activated!" -ForegroundColor Green
    Write-Host "📍 Project: AniVault" -ForegroundColor Cyan
    Write-Host "🐍 Python: $(python --version)" -ForegroundColor Cyan
} else {
    Write-Host "❌ Failed to activate virtual environment" -ForegroundColor Red
    Write-Host "💡 Try: . .\activate.ps1  (with dot and space)" -ForegroundColor Yellow
}
