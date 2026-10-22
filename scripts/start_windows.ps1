# Start Laravel locally. Keep this terminal open while using CrawlInsight.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
if (-not (Get-Command php -ErrorAction SilentlyContinue)) { throw 'PHP 8.2+ is required.' }
if (-not (Test-Path 'vendor/autoload.php')) { throw 'Missing vendor dependencies. Run scripts/setup_windows.ps1 first.' }
if (-not (Test-Path '.env')) { throw 'Missing .env. Run scripts/setup_windows.ps1 first.' }
Write-Host 'Starting Laravel at http://127.0.0.1:8000/' -ForegroundColor Cyan
& php artisan serve --host=127.0.0.1 --port=8000
