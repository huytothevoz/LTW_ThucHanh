# Start local web process. Keep this terminal open while using CrawlInsight.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
$Python = Join-Path $Root '.venv/Scripts/python.exe'
if (-not (Test-Path $Python)) { throw 'Missing .venv. Run scripts/setup_windows.ps1 first.' }
Write-Host 'Starting http://127.0.0.1:5000/ (or FLASK_PORT if set)' -ForegroundColor Cyan
& $Python app.py
