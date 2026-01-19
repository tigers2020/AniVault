# AniVault venv 활성화 스크립트 (실행 정책 우회 버전)
# 이 스크립트는 실행 정책과 무관하게 venv를 활성화합니다.

param(
    [switch]$Help
)

if ($Help) {
    Write-Host "AniVault venv 활성화 스크립트" -ForegroundColor Green
    Write-Host ""
    Write-Host "사용법:" -ForegroundColor Cyan
    Write-Host "  .\activate-venv.ps1          # venv 활성화" -ForegroundColor White
    Write-Host "  .\activate-venv.ps1 -Help    # 도움말 표시" -ForegroundColor White
    Write-Host ""
    exit 0
}

$venvPath = Join-Path $PSScriptRoot "venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (-not (Test-Path $activateScript)) {
    Write-Host "❌ venv가 없습니다. 먼저 venv를 생성하세요:" -ForegroundColor Red
    Write-Host "   python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# 실행 정책을 우회하여 스크립트 실행
Write-Host "🔧 venv 활성화 중..." -ForegroundColor Cyan

# 방법 1: Bypass로 임시 실행
$originalPolicy = Get-ExecutionPolicy -Scope Process
try {
    Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force | Out-Null
    & $activateScript
} catch {
    Write-Host "❌ venv 활성화 실패: $_" -ForegroundColor Red
    Set-ExecutionPolicy -ExecutionPolicy $originalPolicy -Scope Process -Force | Out-Null
    exit 1
} finally {
    Set-ExecutionPolicy -ExecutionPolicy $originalPolicy -Scope Process -Force | Out-Null
}

Write-Host "✅ venv 활성화 완료!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Python 직접 사용:" -ForegroundColor Cyan
Write-Host "   venv\Scripts\python.exe run_gui.py" -ForegroundColor White
