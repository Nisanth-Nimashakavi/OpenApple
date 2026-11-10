# OpenApple One-Click Installer for Windows (PowerShell)
# Requires PowerShell 5.1+ (Standard in Windows 10 & Windows 11)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host " 🍎 Installing OpenApple for Windows..." -ForegroundColor Red
Write-Host " ======================================" -ForegroundColor DarkRed
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) { $ScriptDir = Get-Location }
Set-Location $ScriptDir

# 1. Detect Python
$PythonExe = ""
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = "py"
} else {
    Write-Host "❌ Error: Python is required. Please install Python 3.10+ from python.org or Microsoft Store." -ForegroundColor Red
    Exit 1
}

# 2. Install Node / Electron dependencies for smooth desktop overlay
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "⚡ Installing Electron desktop overlay dependencies..." -ForegroundColor Yellow
    npm install --no-audit
} else {
    Write-Host "ℹ️  npm not found. Python CLI and MCP server will work, but install Node.js for the smooth cursor overlay." -ForegroundColor DarkYellow
}

# 3. Install Python package
Write-Host "📦 Installing OpenApple Python package..." -ForegroundColor Cyan
& $PythonExe -m pip install -e .

# 4. Create Windows CLI launcher shim in ~/.openapple/bin
$OpenAppleBin = Join-Path $env:USERPROFILE ".openapple\bin"
if (-not (Test-Path $OpenAppleBin)) {
    New-Item -ItemType Directory -Path $OpenAppleBin -Force | Out-Null
}

$CmdShim = Join-Path $OpenAppleBin "openapple.cmd"
"@echo off
python -m openapple.cli %*
" | Set-Content -Path $CmdShim -Encoding ASCII

$ServerShim = Join-Path $OpenAppleBin "openapple-server.cmd"
"@echo off
python -m openapple.server %*
" | Set-Content -Path $ServerShim -Encoding ASCII

# Add to User PATH if not already present
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$OpenAppleBin*") {
    Write-Host "🔗 Adding $OpenAppleBin to User PATH..." -ForegroundColor DarkGray
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$OpenAppleBin", "User")
    $env:Path = "$env:Path;$OpenAppleBin"
}

# 5. Run agent configurations & health doctor
Write-Host "🤖 Configuring AI Agents (Claude, AGY, Codex)..." -ForegroundColor Green
& $PythonExe -m openapple.cli install all
& $PythonExe -m openapple.cli doctor

Write-Host "✨ OpenApple installation complete! Type 'openapple' in any terminal to spawn your floating apple." -ForegroundColor Green
Write-Host ""
