# PowerShell 5.1+. External process failures are checked explicitly.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js 22+ is required' }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw 'npm is required' }
& npm ci
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
& node bin/openapple.js setup @args
if ($LASTEXITCODE -ne 0) { throw 'OpenApple setup failed' }
Write-Host 'Setup complete. Run node bin/openapple.js (or npm install -g . for the openapple command).'
