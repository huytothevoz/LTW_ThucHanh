# Set up the Laravel web backend and isolated Python crawler environment.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root

$Php = Get-Command php -ErrorAction SilentlyContinue
$Composer = Get-Command composer -ErrorAction SilentlyContinue
if (-not $Php) { throw 'PHP 8.2+ is required. Install PHP and add php.exe to PATH.' }
if (-not $Composer) { throw 'Composer is required. Install Composer and add composer.bat to PATH.' }
& php -r 'exit(PHP_VERSION_ID >= 80200 ? 0 : 1);'
if ($LASTEXITCODE -ne 0) { throw 'PHP 8.2 or newer is required.' }

if (-not (Test-Path '.env')) {
    Copy-Item '.env.example' '.env'
}
Write-Host 'Installing Laravel dependencies ...' -ForegroundColor Cyan
& composer install --no-interaction --prefer-dist
if ($LASTEXITCODE -ne 0) { throw 'Composer dependency installation failed.' }

$AppKeyLine = Get-Content '.env' | Where-Object { $_ -match '^APP_KEY=' } | Select-Object -First 1
if (-not $AppKeyLine -or $AppKeyLine -eq 'APP_KEY=') {
    & php artisan key:generate --no-interaction
    if ($LASTEXITCODE -ne 0) { throw 'Could not generate the Laravel application key.' }
}

$PythonLauncher = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($Version in @('-3.12', '-3.11')) {
        & py $Version --version *> $null
        if ($LASTEXITCODE -eq 0) { $PythonLauncher = @('py', $Version); break }
    }
}
if (-not $PythonLauncher) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw 'Python 3.11 or 3.12 is required for the crawler.'
    }
    & python -c 'import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or 3.12 is required for the crawler.' }
    $PythonLauncher = @('python')
}

if (-not (Test-Path '.venv/Scripts/python.exe')) {
    if ($PythonLauncher.Count -eq 2) { & $PythonLauncher[0] $PythonLauncher[1] -m venv .venv }
    else { & $PythonLauncher[0] -m venv .venv }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the crawler virtual environment.' }
}
$Python = Join-Path $Root '.venv/Scripts/python.exe'
& $Python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Crawler dependency installation failed.' }

$DbLine = Get-Content '.env' | Where-Object { $_ -match '^CRAWLINSIGHT_DB_PATH=' } | Select-Object -First 1
$DbValue = if ($DbLine) { ($DbLine -split '=', 2)[1].Trim().Trim('"').Trim("'") } else { '' }
if ([string]::IsNullOrWhiteSpace($DbValue)) {
    if ((Split-Path (Split-Path $Root -Parent) -Leaf) -ieq 'htdocs') {
        $DbValue = Join-Path (Split-Path (Split-Path $Root -Parent) -Parent) 'ltw-th-private-data/crawlinsight.db'
    } else {
        $DbValue = Join-Path $Root 'data/crawlinsight.db'
    }
}
if ($DbValue -eq ':memory:') {
    throw 'CRAWLINSIGHT_DB_PATH must point to a shared SQLite file; :memory: cannot be shared with the Python crawler.'
}
if (-not [System.IO.Path]::IsPathRooted($DbValue)) {
    $DbValue = Join-Path $Root $DbValue
}
$env:CRAWLINSIGHT_DB_PATH = $DbValue
Write-Host 'Initializing the shared SQLite database without deleting existing data ...'
& $Python -c 'from src.db import init_db; init_db()'
if ($LASTEXITCODE -ne 0) { throw 'Could not initialize the shared SQLite database.' }
Remove-Item Env:CRAWLINSIGHT_DB_PATH

Write-Host 'Setup complete. Run scripts/start_windows.ps1 to start Laravel.' -ForegroundColor Green
