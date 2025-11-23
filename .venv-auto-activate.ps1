# Auto-activate venv when entering AniVault project directory
# Add this to your PowerShell profile: $PROFILE
# Usage: Add-Content $PROFILE (Get-Content .venv-auto-activate.ps1)

function Enter-AniVaultProject {
    $projectRoot = "F:\Python_Projects\AniVault"
    $venvPath = Join-Path $projectRoot "venv"
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

    if ($PWD.Path -eq $projectRoot -or $PWD.Path.StartsWith($projectRoot)) {
        if (Test-Path $activateScript) {
            if (-not $env:VIRTUAL_ENV) {
                Write-Host "🔧 Auto-activating AniVault venv..." -ForegroundColor Green
                & $activateScript
            }
        }
    }
}

# Hook into PowerShell prompt
function global:prompt {
    Enter-AniVaultProject
    # Call original prompt
    "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
}
