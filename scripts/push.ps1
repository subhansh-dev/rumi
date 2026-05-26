# RUMI Git Push Script
# Strips API keys before push, restores them after.
# Usage: .\scripts\push.ps1 [-m "commit message"]

param(
    [string]$m = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$configFile = Join-Path $root "config" "api_keys.json"
$backupFile = Join-Path $root "config" "api_keys.json.bak"

# Backup real API keys
Write-Host "[push] Backing up real API keys..." -ForegroundColor Cyan
Copy-Item -LiteralPath $configFile -Destination $backupFile -Force

try {
    # Read the real config
    $config = Get-Content -LiteralPath $configFile -Raw -Encoding UTF8 | ConvertFrom-Json

    # Generate placeholder version
    $placeholder = @{
        primary_provider = $config.primary_provider
        gemini_api_key = "your-gemini-api-key-here"
        gemini_api_key_fallback = ""
        groq_api_key = "your-groq-api-key-here"
        os_system = $config.os_system
        camera_index = $config.camera_index
        telegram_bot_token = ""
        telegram_allowed_user = ""
    }

    # Write placeholder
    $placeholder | ConvertTo-Json | Set-Content -LiteralPath $configFile -Encoding UTF8 -Force

    # Stage everything including force-add of gitignored config
    Write-Host "[push] Staging files..." -ForegroundColor Cyan
    & git -C $root add -A
    & git -C $root add -f config/api_keys.json

    # Commit
    if ($m -ne "") {
        & git -C $root commit -m $m
    } else {
        Write-Host "[push] Enter commit message (or Ctrl+C to cancel):" -ForegroundColor Yellow
        $msg = Read-Host
        if ($msg -ne "") {
            & git -C $root commit -m $msg
        } else {
            & git -C $root commit --allow-empty-message -m ""
        }
    }

    # Push
    Write-Host "[push] Pushing to GitHub..." -ForegroundColor Cyan
    & git -C $root push

    Write-Host "[push] Done!" -ForegroundColor Green
}
finally {
    # ALWAYS restore keys, even if something failed
    if (Test-Path -LiteralPath $backupFile) {
        Copy-Item -LiteralPath $backupFile -Destination $configFile -Force
        Remove-Item -LiteralPath $backupFile -Force
        Write-Host "[push] API keys restored." -ForegroundColor Cyan
    }
}
