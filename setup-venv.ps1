# Setup script to configure automatic venv activation
# This script helps set up automatic venv activation for AniVault project

Write-Host "🔧 AniVault venv 자동 활성화 설정" -ForegroundColor Green
Write-Host ""

$projectRoot = $PSScriptRoot
$venvPath = Join-Path $projectRoot "venv"

# Check if venv exists
if (-not (Test-Path $venvPath)) {
    Write-Host "❌ venv가 없습니다. 생성 중..." -ForegroundColor Yellow
    python -m venv venv
    if (-not $?) {
        Write-Host "❌ venv 생성 실패" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ venv 생성 완료" -ForegroundColor Green
}

# Check PowerShell execution policy
$executionPolicy = Get-ExecutionPolicy
Write-Host "📋 현재 PowerShell 실행 정책: $executionPolicy" -ForegroundColor Cyan

if ($executionPolicy -eq "Restricted") {
    Write-Host "⚠️  실행 정책이 Restricted입니다. 스크립트 실행을 위해 변경이 필요합니다." -ForegroundColor Yellow
    Write-Host "💡 다음 명령어로 변경하세요:" -ForegroundColor Yellow
    Write-Host "   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor White
    Write-Host ""
}

Write-Host "✅ 설정 완료!" -ForegroundColor Green
Write-Host ""
Write-Host "📖 사용 방법:" -ForegroundColor Cyan
Write-Host "   1. PowerShell에서: . .\activate.ps1" -ForegroundColor White
Write-Host "   2. CMD에서: activate.bat" -ForegroundColor White
Write-Host "   3. VS Code: 자동으로 활성화됩니다 (이미 설정됨)" -ForegroundColor White
Write-Host ""
