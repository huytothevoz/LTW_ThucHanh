# One-time non-destructive setup. Never modifies XAMPP, MySQL or other projects.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
Write-Host '=== CrawlInsight setup ===' -ForegroundColor Cyan
$Launcher = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($minor in @('-3.12', '-3.11')) {
        & py $minor --version *> $null
        if ($LASTEXITCODE -eq 0) { $Launcher = @('py', $minor); break }
    }
}
if (-not $Launcher) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw 'Python 3.11 or 3.12 not found. Install it from python.org first.'
    }
    $Launcher = @('python')
}
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    Write-Host 'Creating isolated .venv ...'
    if ($Launcher.Count -eq 2) { & $Launcher[0] $Launcher[1] -m venv .venv }
    else { & $Launcher[0] -m venv .venv }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create virtual environment.' }
}
$Python = Join-Path $Root '.venv/Scripts/python.exe'
Write-Host 'Installing Python packages into .venv ...'
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check Internet and Python version.' }
Write-Host 'Initializing empty SQLite schema (never deleting existing data)...'
& $Python -c 'from src.db import init_db; init_db()'
if ($LASTEXITCODE -ne 0) { throw 'Could not initialize SQLite database.' }
Write-Host 'Setup complete. Run scripts/start_windows.ps1 to start the website.' -ForegroundColor Green
